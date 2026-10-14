"""The core's host interface, `core/include/odrig_core.h`, declared for Python.

This is the only module that knows the core is a C library. Everything else uses `Core`.
"""

import collections
import ctypes
import os
import sys
from ctypes import CFUNCTYPE, POINTER, Structure, c_char, c_char_p, c_int, c_int32, c_size_t, c_uint8, c_uint16, c_uint32, c_uint64, c_void_p

from . import failure

LINE_MAX = 2048
REPLY_MAX = 1024


def library_of(platform):
    """`(file name, build command)` of the core's shared library on a system."""
    if platform == "win32":
        return "odrig_core.dll", "python core/build.py shared"
    return "libodrig_core.dylib", "make -C core shared"


LIBRARY_NAME, BUILD_COMMAND = library_of(sys.platform)

ALLOC = CFUNCTYPE(c_void_p, c_void_p, c_size_t)
OPEN = CFUNCTYPE(c_int, c_void_p, c_char_p)
READ = CFUNCTYPE(c_int32, c_void_p, POINTER(c_uint8), c_size_t)
CLOSE = CFUNCTYPE(None, c_void_p)
LOG = CFUNCTYPE(None, c_void_p, c_char_p)
WRITE_OPEN = CFUNCTYPE(c_int, c_void_p, c_char_p)
WRITE = CFUNCTYPE(c_int, c_void_p, POINTER(c_uint8), c_size_t)
WRITE_CLOSE = CFUNCTYPE(c_int, c_void_p)
RENAME = CFUNCTYPE(c_int, c_void_p, c_char_p, c_char_p)
REMOVE = CFUNCTYPE(c_int, c_void_p, c_char_p)
SPACE = CFUNCTYPE(c_int, c_void_p, POINTER(c_uint32), POINTER(c_uint32))
READ_AT = CFUNCTYPE(c_int32, c_void_p, c_char_p, c_uint32, POINTER(c_uint8), c_size_t)
DRIVE = CFUNCTYPE(c_uint32, c_void_p)
DRIVE_NAME = CFUNCTYPE(c_int, c_void_p, c_uint32, c_uint32, POINTER(c_char), c_size_t)
REPLY = CFUNCTYPE(None, c_void_p, POINTER(c_char), c_size_t, POINTER(c_char), c_size_t)


class HostRecord(Structure):
    """`odrig_host`."""

    _fields_ = [
        ("ctx", c_void_p), ("alloc", ALLOC), ("open", OPEN), ("read", READ), ("close", CLOSE), ("log", LOG),
        ("write_open", WRITE_OPEN), ("write", WRITE), ("write_close", WRITE_CLOSE), ("rename", RENAME), ("remove", REMOVE),
        ("space", SPACE), ("read_at", READ_AT), ("drive", DRIVE), ("drive_name", DRIVE_NAME),
    ]


class LegRecord(Structure):
    """`odrig_leg`."""

    _fields_ = [("leg", c_uint16), ("pin", c_uint16), ("led_count", c_uint32), ("rgb", POINTER(c_uint8))]


# Every function of the header: its result and its arguments.
FUNCTIONS = {
    "odrig_core_begin": (c_void_p, [POINTER(HostRecord)]),
    "odrig_core_poll": (c_int, [c_void_p, c_uint64]),
    "odrig_core_leg_count": (c_uint32, [c_void_p]),
    "odrig_core_leg": (c_int, [c_void_p, c_uint32, POINTER(LegRecord)]),
    "odrig_core_command": (c_size_t, [c_void_p, c_uint64, c_char_p, c_size_t, c_char_p, c_size_t]),
    "odrig_core_feed": (None, [c_void_p, c_uint64, c_char_p, c_size_t, REPLY, c_void_p]),
    "odrig_core_error": (c_char_p, [c_void_p]),
}

Leg = collections.namedtuple("Leg", "leg pin led_count")

TOO_LONG = b'"line-too-long"'
MOST_BYTES = 4294967295


def load(library_path):
    """The library with every function of the header declared, or `core-not-built`."""
    path = os.fspath(library_path)
    try:
        # By its whole path: a library named without a folder is the one in the working
        # folder, which not every system looks into for a bare name.
        library = ctypes.CDLL(os.path.abspath(path))
        for name, (result, arguments) in FUNCTIONS.items():
            function = getattr(library, name)
            function.restype = result
            function.argtypes = arguments
    except (OSError, AttributeError):
        raise failure.Failure(
            failure.CORE_NOT_BUILT, f"{path}: the core's shared library is not there or does not load; build it with `{BUILD_COMMAND}`"
        ) from None
    return library


class Core:
    """The core, started on the files a host object hands out.

    The host object has the methods `open(name)`, `read(capacity)`, `close()` and
    `log(text)` of `host.FolderHost`. When it also has `write_open`, it has the seven
    storage methods of `host.FolderHost`, and the core gets storage that can be changed;
    otherwise the core gets a host without storage. The core is used by one caller at a
    time.
    """

    def __init__(self, library_path, host):
        self._library = load(library_path)
        self._host = host
        self._blocks = []
        self._answered = []
        self._functions = (ALLOC(self._alloc), OPEN(self._open), READ(self._read), CLOSE(self._close), LOG(self._log))
        if hasattr(host, "write_open"):
            self._functions += (
                WRITE_OPEN(self._write_open), WRITE(self._write), WRITE_CLOSE(self._write_close), RENAME(self._rename),
                REMOVE(self._remove), SPACE(self._space), READ_AT(self._read_at),
            )
        else:
            self._functions += (WRITE_OPEN(), WRITE(), WRITE_CLOSE(), RENAME(), REMOVE(), SPACE(), READ_AT())
        self._functions += (DRIVE(), DRIVE_NAME())
        self._on_reply = REPLY(self._collect)
        self._record = HostRecord(None, *self._functions)
        self._reply = ctypes.create_string_buffer(REPLY_MAX)
        self._core = self._library.odrig_core_begin(ctypes.byref(self._record))
        if not self._core:
            raise failure.Failure(failure.CORE_NOT_BUILT, "the core could not start")
        legs = []
        self._rgb = []
        for index in range(self._library.odrig_core_leg_count(self._core)):
            record = LegRecord()
            if self._library.odrig_core_leg(self._core, index, ctypes.byref(record)):
                legs.append(Leg(record.leg, record.pin, record.led_count))
                self._rgb.append((ctypes.cast(record.rgb, c_void_p).value, record.led_count * 3))
        self.legs = tuple(legs)
        self.led_bytes = 3 * sum(leg.led_count for leg in legs)

    def _alloc(self, _ctx, size):
        block = ctypes.create_string_buffer(max(size, 1))
        self._blocks.append(block)
        return ctypes.addressof(block)

    def _open(self, _ctx, name):
        return self._host.open(name.decode("utf-8", "replace"))

    def _read(self, _ctx, buffer, capacity):
        data = self._host.read(capacity)
        if data is None or len(data) > capacity:
            return -1
        ctypes.memmove(buffer, data, len(data))
        return len(data)

    def _close(self, _ctx):
        self._host.close()

    def _log(self, _ctx, text):
        self._host.log(text.decode("utf-8", "replace"))

    def _write_open(self, _ctx, name):
        return self._host.write_open(name.decode("utf-8", "replace"))

    def _write(self, _ctx, data, length):
        return self._host.write(ctypes.string_at(data, length))

    def _write_close(self, _ctx):
        return self._host.write_close()

    def _rename(self, _ctx, old, new):
        return self._host.rename(old.decode("utf-8", "replace"), new.decode("utf-8", "replace"))

    def _remove(self, _ctx, name):
        return self._host.remove(name.decode("utf-8", "replace"))

    def _space(self, _ctx, free_bytes, total_bytes):
        told = self._host.space()
        if told is None:
            return -1
        free_bytes[0], total_bytes[0] = (min(max(int(value), 0), MOST_BYTES) for value in told)
        return 1

    def _read_at(self, _ctx, name, offset, buffer, capacity):
        data = self._host.read_at(name.decode("utf-8", "replace"), offset, capacity)
        if data is None or len(data) > capacity:
            return -1
        ctypes.memmove(buffer, data, len(data))
        return len(data)

    def _collect(self, _ctx, line, line_length, reply, reply_length):
        answer = ctypes.string_at(reply, reply_length)
        self._answered.append((ctypes.string_at(line, line_length), answer, TOO_LONG in answer))

    def poll(self, now_ms):
        """Asks for a refresh. True when the core produced new LED data."""
        return bool(self._library.odrig_core_poll(self._core, now_ms))

    def frame(self):
        """The LED data of the last refresh: every leg's bytes in chain order, the legs joined
        in the core's order."""
        return b"".join(ctypes.string_at(address, size) for address, size in self._rgb)

    def command(self, now_ms, line):
        """One command line in, its reply out, with the reply's newline."""
        length = self._library.odrig_core_command(self._core, now_ms, line, len(line), self._reply, REPLY_MAX)
        return self._reply.raw[:length]

    def feed(self, now_ms, data):
        """Bytes of a transport. Returns `(line, reply, cut)` for every line they finish:
        the line as the core read it, its reply, and whether the line was longer than the
        core's limit and was cut to it."""
        self._answered = []
        self._library.odrig_core_feed(self._core, now_ms, data, len(data), self._on_reply, None)
        answered, self._answered = self._answered, []
        return answered

    def error(self):
        """The reason the show is invalid, or `None` when it is valid."""
        text = self._library.odrig_core_error(self._core)
        return None if text is None else text.decode("ascii", "replace")

"""A serial port of Windows, opened without resetting what is behind it.

Windows has no `termios`. The port is reached through `kernel32`, which `ctypes` loads: no
added package is needed.
"""

import ctypes
import time
from ctypes import wintypes

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE = ctypes.c_void_p(-1).value
CLRRTS = 4
CLRDTR = 6
MAXDWORD = 0xFFFFFFFF

DEVICES = "\\\\.\\"
BAUD = 115200
DATA_BITS = 8
NO_PARITY = 0
ONE_STOP_BIT = 0
# Of the flags of the settings only "binary" is set: no flow control, and DTR and RTS
# left low when the port is opened.
BINARY = 0x0001
READ_SIZE = 4096
POLL_MILLISECONDS = 20


class DCB(ctypes.Structure):
    """The settings of a port, as `GetCommState` and `SetCommState` take them."""

    _fields_ = [
        ("DCBlength", wintypes.DWORD),
        ("BaudRate", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("wReserved", wintypes.WORD),
        ("XonLim", wintypes.WORD),
        ("XoffLim", wintypes.WORD),
        ("ByteSize", ctypes.c_ubyte),
        ("Parity", ctypes.c_ubyte),
        ("StopBits", ctypes.c_ubyte),
        ("XonChar", ctypes.c_char),
        ("XoffChar", ctypes.c_char),
        ("ErrorChar", ctypes.c_char),
        ("EofChar", ctypes.c_char),
        ("EvtChar", ctypes.c_char),
        ("wReserved1", wintypes.WORD),
    ]


class Timeouts(ctypes.Structure):
    """`COMMTIMEOUTS`: how long a read and a write may take, in milliseconds."""

    _fields_ = [
        ("ReadIntervalTimeout", wintypes.DWORD),
        ("ReadTotalTimeoutMultiplier", wintypes.DWORD),
        ("ReadTotalTimeoutConstant", wintypes.DWORD),
        ("WriteTotalTimeoutMultiplier", wintypes.DWORD),
        ("WriteTotalTimeoutConstant", wintypes.DWORD),
    ]


def kernel32():
    """The functions of Windows this module calls, with their arguments declared."""
    library = ctypes.WinDLL("kernel32", use_last_error=True)
    handle, count = wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)
    library.CreateFileW.restype = handle
    library.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, handle]
    for name, arguments in (
        ("EscapeCommFunction", [handle, wintypes.DWORD]),
        ("GetCommState", [handle, ctypes.POINTER(DCB)]),
        ("SetCommState", [handle, ctypes.POINTER(DCB)]),
        ("SetCommTimeouts", [handle, ctypes.POINTER(Timeouts)]),
        ("ReadFile", [handle, ctypes.c_void_p, wintypes.DWORD, count, ctypes.c_void_p]),
        ("WriteFile", [handle, ctypes.c_void_p, wintypes.DWORD, count, ctypes.c_void_p]),
        ("CloseHandle", [handle]),
    ):
        function = getattr(library, name)
        function.restype = wintypes.BOOL
        function.argtypes = arguments
    return library


def device(name):
    """The name Windows opens a port by. With the prefix every port is found, also those
    above COM9."""
    return name if name.startswith(DEVICES) else DEVICES + name


def refused(what):
    """The failure of a call, as Windows reports it."""
    code = ctypes.get_last_error() if hasattr(ctypes, "get_last_error") else 0
    text = ctypes.FormatError(code).strip() if code and hasattr(ctypes, "FormatError") else what
    return OSError(code, text or what)


class Port:
    """An open serial port: 115200 baud, 8 data bits, no parity, one stop bit.

    The modem lines are lowered RTS first, DTR second: DTR low while RTS is still high is
    the combination that resets the chip. The settings then written keep both low, so that
    opening the port again raises neither. A port without modem lines refuses the two
    requests, which is ignored.
    """

    def __init__(self, name, kernel=None):
        self._kernel = kernel32() if kernel is None else kernel
        self._handle = self._kernel.CreateFileW(device(name), GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
        if self._handle in (None, 0, INVALID_HANDLE, -1):
            self._handle = None
            raise refused("the port cannot be opened")
        try:
            for line in (CLRRTS, CLRDTR):
                self._kernel.EscapeCommFunction(self._handle, line)
            settings = DCB()
            settings.DCBlength = ctypes.sizeof(DCB)
            if not self._kernel.GetCommState(self._handle, ctypes.byref(settings)):
                raise refused("this is not a serial port")
            settings.BaudRate = BAUD
            settings.flags = BINARY
            settings.ByteSize = DATA_BITS
            settings.Parity = NO_PARITY
            settings.StopBits = ONE_STOP_BIT
            if not self._kernel.SetCommState(self._handle, ctypes.byref(settings)):
                raise refused("the port does not take the settings")
            self._limits(0)
        except BaseException:
            self.close()
            raise

    def _limits(self, write_milliseconds):
        """A read returns with what has arrived, after waiting a short time when nothing
        has; a write may take this long."""
        limits = Timeouts(MAXDWORD, MAXDWORD, POLL_MILLISECONDS, 0, write_milliseconds)
        if not self._kernel.SetCommTimeouts(self._handle, ctypes.byref(limits)):
            raise refused("the port does not take the time limits")

    def received(self, seconds):
        """What arrives within a length of time, in pieces as they come."""
        deadline = time.monotonic() + seconds
        buffer = ctypes.create_string_buffer(READ_SIZE)
        count = wintypes.DWORD(0)
        while time.monotonic() < deadline:
            if not self._kernel.ReadFile(self._handle, buffer, READ_SIZE, ctypes.byref(count), None):
                raise refused("the port cannot be read")
            if count.value:
                yield buffer.raw[:count.value]

    def write(self, data, seconds):
        self._limits(max(1, int(seconds * 1000)))
        deadline = time.monotonic() + seconds
        count = wintypes.DWORD(0)
        while data:
            if not self._kernel.WriteFile(self._handle, data, len(data), ctypes.byref(count), None):
                raise refused("the port cannot be written")
            data = data[count.value:]
            if data and time.monotonic() >= deadline:
                raise OSError(0, "the port takes no more bytes")

    def close(self):
        if self._handle is not None:
            self._kernel.CloseHandle(self._handle)
            self._handle = None

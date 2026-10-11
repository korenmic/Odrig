"""Helpers shared by the tests of the firmware tool."""

import collections
import contextlib
import hashlib
import io
import struct
import subprocess
import sys
from unittest import mock

from fwtool import Failure, board, cli, flasher

from . import FIRMWARE, ROOT

TOOL = FIRMWARE / "fw.py"

Result = collections.namedtuple("Result", "status out err")


def run_tool(*arguments):
    """Runs `fw.py` as a program, from the repository root."""
    done = subprocess.run([sys.executable, str(TOOL), *map(str, arguments)], cwd=ROOT, capture_output=True, text=True)
    return Result(done.returncode, done.stdout, done.stderr)


def run_main(*arguments):
    """Runs one command line of the tool in this interpreter."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = cli.main([str(argument) for argument in arguments])
        except SystemExit as stopped:
            status = stopped.code
    return Result(status, out.getvalue(), err.getvalue())


def reason_of(test, action):
    """The reason with which an action fails."""
    with test.assertRaises(Failure) as caught:
        action()
    return caught.exception.reason


def git(folder, *arguments):
    """Runs git in a folder with an identity of its own and returns what it printed."""
    command = ["git", "-C", str(folder), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", *map(str, arguments)]
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()


def repository(folder, files):
    """Makes a git repository with one commit that holds the files; returns the commit."""
    folder.mkdir(parents=True, exist_ok=True)
    git(folder, "init", "--quiet")
    for name, text in files.items():
        (folder / name).write_text(text)
        git(folder, "add", name)
    git(folder, "commit", "--quiet", "-m", "first")
    return git(folder, "rev-parse", "HEAD")


# WLED's 16 MB layout: name, type, subtype, offset, size.
LAYOUT = (
    ("nvs", 1, 0x02, 0x9000, 0x5000),
    ("otadata", 1, 0x00, 0xE000, 0x2000),
    ("app0", 0, 0x10, 0x10000, 0x300000),
    ("app1", 0, 0x11, 0x310000, 0x300000),
    ("spiffs", 1, 0x82, 0x610000, 0x9E0000),
    ("coredump", 1, 0x03, 0xFF0000, 0x10000),
)
TABLE_SIZE = 0xC00


def partition_table(layout=LAYOUT, magic=b"\xaa\x50", checksum=True):
    """A partition table as it lies in the flash: the entries, their checksum, and padding."""
    table = b""
    for name, kind, subtype, offset, size in layout:
        table += magic + struct.pack("<BBII", kind, subtype, offset, size) + name.encode().ljust(16, b"\0") + struct.pack("<I", 0)
    if checksum:
        table += b"\xeb\xeb" + b"\xff" * 14 + hashlib.md5(table).digest()
    return table.ljust(TABLE_SIZE, b"\xff")


# esptool takes a file that begins with this byte for a program image. The stand-in knows
# one program for the chip, and refuses any other file that begins with the byte, as
# esptool does, unless it is told to leave that check out.
PROGRAM_BYTE = b"\xe9"
PROGRAM = PROGRAM_BYTE + b"a program for this chip"


class RecordedEsptool:
    """Stands in for esptool: keeps the arguments of every call and serves what is read."""

    def __init__(self, table=None, flash=None, failing_verifies=0):
        self.calls = []
        self.waited = []
        self.table = partition_table() if table is None else table
        self.flash = flash or {}
        self.failing_verifies = failing_verifies
        self.wrote = []

    def __call__(self, arguments):
        self.calls.append(list(arguments))
        if "read-flash" in arguments:
            address, size, path = arguments[arguments.index("read-flash") + 1:][:3]
            address, size = int(address, 16), int(size, 16)
            content = self.table if address == 0x8000 else self.flash[address]
            with open(path, "wb") as file:
                file.write(content[:size])
        if "write-flash" in arguments:
            written = []
            for address, name in self.pairs(arguments[arguments.index("write-flash") + 1:]):
                with open(name, "rb") as file:
                    written.append((int(address, 16), name, file.read()))
            for _, name, content in written:
                if content[:1] == PROGRAM_BYTE and content[:len(PROGRAM)] != PROGRAM and "--force" not in arguments:
                    return 2, f"A fatal error occurred: '{name}' is not an ESP32-S3 image. Use the force argument to flash anyway."
            self.wrote += [(address, content) for address, _, content in written]
        if "verify-flash" in arguments and self.failing_verifies:
            self.failing_verifies -= 1
            return 2, "A fatal error occurred: Verification failed"
        return 0, "done"

    @staticmethod
    def pairs(arguments):
        words = [word for word in arguments if not word.startswith("--") and word not in ("keep", "detect")]
        return [(words[i], words[i + 1]) for i in range(0, len(words), 2)]

    def commands(self):
        """The esptool command of every call, in order."""
        names = ("read-flash", "erase-region", "write-flash", "verify-flash", "chip-id")
        return [next(word for word in call if word in names) for call in self.calls]

    def call(self, command):
        """The arguments after the command, of the one call of that command."""
        found = [call[call.index(command) + 1:] for call in self.calls if command in call]
        assert len(found) == 1, f"{len(found)} calls of {command}"
        return found[0]

    def written(self):
        """`(address, file name)` for everything the one write call writes."""
        return [(address, name.rsplit("/", 1)[-1]) for address, name in self.pairs(self.call("write-flash"))]

    def words(self):
        return [word for call in self.calls for word in call]


@contextlib.contextmanager
def no_board(esptool=None, answer="WLED 2606300", port="/dev/cu.test"):
    """Runs the tool without a board: esptool is the stand-in, the port is found, and
    whatever must answer after a restart does."""
    esptool = RecordedEsptool() if esptool is None else esptool
    if not hasattr(esptool, "waited"):
        esptool.waited = []
    answers = {name: (lambda found, wait=0: esptool.waited.append(wait) or answer) for name in board.EXPECTED}
    with mock.patch.object(flasher, "run_esptool", esptool), mock.patch.object(board, "find", lambda given=None: given or port), mock.patch.dict(board.EXPECTED, answers):
        yield esptool


@contextlib.contextmanager
def untouched_board():
    """Fails the test when the tool looks for a board or starts esptool."""
    def touched(*arguments, **named):
        raise AssertionError("the board was touched")
    with mock.patch.object(flasher, "run_esptool", touched), mock.patch.object(board, "find", touched):
        yield


DISK_VERSION_2_0 = 0x00020000
BLOCK_SIZE = 4096

# Files like the ones WLED keeps in its file system, beside an older installed show.
WLED_FILES = {
    "/cfg.json": b'{"rev":[1,0],"vid":2606300,"id":{"mdns":"wled-test","name":"WLED"}}',
    "/presets.json": b'{"0":{},"5":{"n":"hello"},"6":{"playlist":{"ps":[5,4]}}}',
    "/wsec.json": b'{"ap":{"psk":"not a real one"}}',
    "/hello.gif": bytes(range(256)) * 40,
    "/odrig/mapping.json": b"an older mapping",
    "/odrig/old.odrg": b"an older animation" * 100,
}


def storage_image(files=None, blocks=64, version=DISK_VERSION_2_0):
    """A storage image with a LittleFS file system of the given disk version."""
    from littlefs import LittleFS
    system = LittleFS(block_size=BLOCK_SIZE, block_count=blocks, disk_version=version)
    for path, content in (WLED_FILES if files is None else files).items():
        folder = path.rsplit("/", 1)[0]
        if folder:
            system.makedirs(folder, exist_ok=True)
        with system.open(path, "wb") as file:
            file.write(content)
    system.unmount()
    return bytes(system.context.buffer)


def small_layout(blocks=64):
    """WLED's layout with a storage partition of a few blocks, for images made in a test."""
    return tuple(entry if entry[0] != "spiffs" else ("spiffs", 1, 0x82, 0x610000, blocks * BLOCK_SIZE) for entry in LAYOUT)


@contextlib.contextmanager
def example_show(brightness=None):
    """The example show, packed on the two-leg mapping into a temporary folder."""
    import json
    import pathlib
    import tempfile
    from odrig import pack
    with tempfile.TemporaryDirectory() as folder:
        show = ROOT / "shows" / "example" / "show.json"
        if brightness is not None:
            changed = json.loads(show.read_text())
            changed["brightness"] = brightness
            show = pathlib.Path(folder, "show.json")
            show.write_text(json.dumps(changed))
        out = pathlib.Path(folder, "show")
        pack.pack(show, ROOT / "mapping" / "legs-2.json", ROOT / "animations", out)
        yield out


def files_of(folder):
    """The files of a folder: the content of each by its name."""
    import pathlib
    return {path.name: path.read_bytes() for path in sorted(pathlib.Path(folder).iterdir())}

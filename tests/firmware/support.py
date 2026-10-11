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


class RecordedEsptool:
    """Stands in for esptool: keeps the arguments of every call and serves what is read."""

    def __init__(self, table=None, flash=None):
        self.calls = []
        self.table = partition_table() if table is None else table
        self.flash = flash or {}

    def __call__(self, arguments):
        self.calls.append(list(arguments))
        if "read-flash" in arguments:
            address, size, path = arguments[arguments.index("read-flash") + 1:][:3]
            address, size = int(address, 16), int(size, 16)
            content = self.table if address == 0x8000 else self.flash[address]
            with open(path, "wb") as file:
                file.write(content[:size])
        return 0, "done"

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
        arguments = [word for word in self.call("write-flash") if not word.startswith("--") and word not in ("keep", "detect")]
        return [(arguments[i], arguments[i + 1].rsplit("/", 1)[-1]) for i in range(0, len(arguments), 2)]

    def words(self):
        return [word for call in self.calls for word in call]


@contextlib.contextmanager
def no_board(esptool=None, answer="WLED 2606300", port="/dev/cu.test"):
    """Runs the tool without a board: esptool is the stand-in, the port is found, and
    whatever must answer after a restart does."""
    esptool = RecordedEsptool() if esptool is None else esptool
    answers = {name: (lambda found, wait=0: answer) for name in board.EXPECTED}
    with mock.patch.object(flasher, "run_esptool", esptool), mock.patch.object(board, "find", lambda given=None: given or port), mock.patch.dict(board.EXPECTED, answers):
        yield esptool


@contextlib.contextmanager
def untouched_board():
    """Fails the test when the tool looks for a board or starts esptool."""
    def touched(*arguments, **named):
        raise AssertionError("the board was touched")
    with mock.patch.object(flasher, "run_esptool", touched), mock.patch.object(board, "find", touched):
        yield

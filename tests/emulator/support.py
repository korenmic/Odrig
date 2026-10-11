"""Helpers shared by the tests of the emulator: where things are and how shows are packed."""

import collections
import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile

from emulator import app
from odrig import pack
from tests.core.support import ReferencePlayer

from . import LIBRARY, ROOT

HEADER = ROOT / "core" / "include" / "odrig_core.h"
EXAMPLE_SHOW = ROOT / "shows" / "example" / "show.json"
TWO_LEGS = ROOT / "mapping" / "legs-2.json"
TEN_LEGS = ROOT / "mapping" / "legs-10.json"


@contextlib.contextmanager
def packed(show, mapping, sources, compressed=True):
    """A temporary folder that holds a show as `python -m odrig pack` installs it."""
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder, "show")
        pack.pack(show, mapping, sources, out, compressed=compressed)
        yield out


def example_show():
    """The example show, packed on the two-leg mapping into a temporary folder."""
    return packed(EXAMPLE_SHOW, TWO_LEGS, ROOT / "animations")


def files_of(folder):
    """The installed files of a folder: the content of each by its name."""
    return {path.name: path.read_bytes() for path in sorted(pathlib.Path(folder).iterdir()) if path.is_file()}


Result = collections.namedtuple("Result", "status out err")


def run(*argv):
    """Runs one command line of the emulator in this interpreter."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = app.main([str(argument) for argument in argv])
        except SystemExit as stopped:
            status = stopped.code
    return Result(status, out.getvalue(), err.getvalue())


def run_module(*argv, module="emulator", cwd=ROOT):
    """Runs `python -m <module>` in a fresh interpreter, from the repository root."""
    done = subprocess.run(
        [sys.executable, "-m", module, *(str(argument) for argument in argv)], cwd=cwd, capture_output=True, text=True
    )
    return Result(done.returncode, done.stdout, done.stderr)


def reference(files, ticks, commands=()):
    """What the reference player of the core's suite does with an installed file set.

    `ticks` are the times at which a refresh is asked for, and `commands` holds
    `(time, line)` in the order they are sent: each is given with its own time before the
    first tick that is not earlier, and after the last tick when none is. Returns
    `(refreshes, replies)`: for each tick `None` when no refresh was due, or each leg's
    LED data in the order of the mapping file; and the reply to each command.
    """
    player = ReferencePlayer(files)
    waiting = collections.deque(commands)
    refreshes = []
    replies = []

    def send(until):
        while waiting and (until is None or waiting[0][0] <= until):
            time, line = waiting.popleft()
            replies.append(player.command(time, line if isinstance(line, bytes) else line.encode("utf-8")))

    for now in ticks:
        send(now)
        refresh = player.poll(now)
        refreshes.append(None if refresh is None else tuple(rgb for _, rgb in refresh))
    send(None)
    return refreshes, replies

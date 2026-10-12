"""Runs the tool in a child process in which a fault of memory ends the process quietly.

A file that the tool cannot read must be refused, and a tool that is wrong about this can
end Python with a fault of memory. In a child started here such a fault ends the child with
the number of the signal as its status and writes no crash report, so that a test of the
fault shows nothing on the screen of whoever runs the suite.
"""

import subprocess
import sys

from . import support

SIGNALS = (10, 11)

PRELUDE = """
import ctypes, sys
try:
    libc = ctypes.CDLL(None)
    libc.signal.argtypes = [ctypes.c_int, ctypes.c_void_p]
    for number in %r:
        libc.signal(number, ctypes.cast(libc._exit, ctypes.c_void_p))
except (AttributeError, OSError, TypeError):
    pass
from odrig import cli
sys.exit(cli.main(sys.argv[1:]))
""" % (SIGNALS,)


def run_tool(*argv):
    """Runs `python -m odrig` with the arguments and returns `support.Result`.

    Raises `AssertionError` when a signal ended the child."""
    done = subprocess.run([sys.executable, "-c", PRELUDE, *map(str, argv)], cwd=support.ROOT, capture_output=True, text=True)
    if done.returncode in SIGNALS or -done.returncode in SIGNALS:
        raise AssertionError(f"signal {abs(done.returncode)} ended the tool: {' '.join(map(str, argv))}")
    return support.Result(done.returncode, done.stdout, done.stderr)

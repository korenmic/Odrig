"""Helpers shared by the tests: where the repository is and how a program of the package
is run."""

import collections
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

Result = collections.namedtuple("Result", "status out err")


def run_module(*argv, module):
    """Runs `python -m <module>` in a fresh interpreter, from the repository root."""
    done = subprocess.run(
        [sys.executable, "-m", module, *(str(argument) for argument in argv)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return Result(done.returncode, done.stdout, done.stderr)

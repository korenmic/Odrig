"""Helpers shared by the tests: where the repository is and how the tool is run."""

import collections
import contextlib
import io
import pathlib
import subprocess
import sys

from odrig import cli

ROOT = pathlib.Path(__file__).resolve().parents[2]

Result = collections.namedtuple("Result", "status out err")


def run(*argv):
    """Runs one command line in this interpreter."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = cli.main([str(argument) for argument in argv])
    return Result(status, out.getvalue(), err.getvalue())


def run_module(*argv, module="odrig"):
    """Runs `python -m <module>` in a fresh interpreter, from the repository root."""
    done = subprocess.run(
        [sys.executable, "-m", module, *(str(argument) for argument in argv)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return Result(done.returncode, done.stdout, done.stderr)

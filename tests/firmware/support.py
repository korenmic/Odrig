"""Helpers shared by the tests of the firmware tool."""

import collections
import contextlib
import io
import subprocess
import sys

from fwtool import Failure, cli

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

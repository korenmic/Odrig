"""Helpers of the walk-through: the fresh copy of the repository, and a command run in it."""

import collections
import contextlib
import os
import pathlib
import shutil
import signal
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Who commits in the copy. Nothing of the caller's own git settings is used or changed.
IDENTITY = ("-c", "user.name=walk-through", "-c", "user.email=walk-through@example.invalid", "-c", "commit.gpgsign=false")

# The longest a command of a page may take, in seconds.
TIME_LIMIT = 1800

# Variables of the caller that would make a command use another Python than the page's.
NOT_PASSED_ON = ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "ODRIG_PYTHON")

Done = collections.namedtuple("Done", "status output")


def git(folder, *arguments):
    """Runs git in a folder and returns what it printed."""
    command = ["git", "-C", str(folder), *IDENTITY, *map(str, arguments)]
    return subprocess.run(command, capture_output=True, check=True).stdout.decode("utf-8")


def tracked(folder):
    """The paths git tracks in a folder."""
    return {name for name in git(folder, "ls-files", "-z").split("\0") if name}


def fresh_copy(target):
    """Clones the repository into `target` and brings the clone to what a clone would hold
    if the tracked files of the working tree were committed as they are.

    Returns the paths it brought over and the paths it removed; both are empty when the
    working tree is clean. Nothing untracked and nothing git ignores reaches the copy.
    """
    subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(target)], capture_output=True, check=True)
    here, there = tracked(ROOT), tracked(target)
    changed, gone = [], sorted(there - here)
    for name in sorted(here):
        ours, theirs = ROOT / name, target / name
        if not ours.is_file():
            if name in there:
                gone.append(name)
        elif not theirs.is_file() or ours.read_bytes() != theirs.read_bytes():
            theirs.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ours, theirs)
            changed.append(name)
    if changed:
        git(target, "add", "--", *changed)
    if gone:
        git(target, "rm", "--quiet", "--", *gone)
    if changed or gone:
        git(target, "commit", "--quiet", "-m", "The tracked files as the working tree has them")
    return changed, gone


def environment():
    """The caller's environment without what would lead a command to another Python."""
    return {name: value for name, value in os.environ.items() if name not in NOT_PASSED_ON}


def run(command, folder):
    """Runs one command of a page from a folder, as a shell runs it, and returns its status
    and everything it printed. The command gets a process group of its own; when it takes
    longer than the limit, or the caller is interrupted, that group is ended."""
    process = subprocess.Popen(
        ["/bin/sh", "-c", command], cwd=folder, env=environment(), text=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=TIME_LIMIT)
    except BaseException as stopped:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        output, _ = process.communicate()
        if not isinstance(stopped, subprocess.TimeoutExpired):
            raise
        return Done(None, f"{output}\n(ended by the test after {TIME_LIMIT} seconds)")
    return Done(process.returncode, output)

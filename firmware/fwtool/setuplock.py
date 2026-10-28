"""The lock of a setup in the folder of the shared toolchains.

Two setups at once, from two checkouts, would fetch and install into the same folders. The
second waits until the first is done, and then finds most of its work there. The system
holds the lock for the process, so a setup that dies leaves nothing to clean up.
"""

import contextlib
import os
import pathlib
import time

from . import Failure

try:
    import fcntl
except ImportError:
    fcntl = None
    import msvcrt

# How long a setup waits for another one, in seconds.
WAIT = 3600


def _take(file):
    """Takes the lock of an open file without waiting. Whether it was free."""
    try:
        if fcntl is not None:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            file.seek(0)
            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return False
    return True


def _give_back(file):
    if fcntl is not None:
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)
    else:
        file.seek(0)
        msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)


@contextlib.contextmanager
def held(path, wait=WAIT, waiting=None, step=0.5):
    """Holds the lock file at `path` for the block. When another process holds it, `waiting`
    is called once and the lock taken as soon as it is free, for at most `wait` seconds."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as file:
        deadline = time.monotonic() + wait
        told = False
        while not _take(file):
            if time.monotonic() >= deadline:
                raise Failure("setup-failed", f"another setup has held {path} for more than {wait} seconds")
            if not told and waiting is not None:
                waiting()
                told = True
            time.sleep(step)
        try:
            file.seek(0)
            file.truncate()
            file.write(f"{os.getpid()}\n".encode())
            file.flush()
            yield
        finally:
            _give_back(file)

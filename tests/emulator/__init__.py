"""The suite of the emulator and the command tool.

Importing the package builds the core's shared library, so the one test command builds
what it tests: with the build script on Windows and with `make` elsewhere. When the build
fails, no test runs and the output of the build is the failure. Under `tests/run.py`, which
builds the core once before its workers start and says so with `ODRIG_CORE_BUILT`, nothing
is built; otherwise the build runs under a lock file, so that two processes that import the
package at once never write the library together.
"""

import os
import pathlib
import subprocess
import sys
import time

from emulator import binding

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "core" / "build" / binding.LIBRARY_NAME
BUILD_SCRIPT = ROOT / "core" / "build.py"
BUILD_COMMAND = [sys.executable, str(BUILD_SCRIPT), "shared"] if sys.platform == "win32" else ["make", "-C", str(ROOT / "core"), "shared"]


LOCK = ROOT / "core" / "build" / ".lock"
# How long a lock may stand before it counts as left by a process that ended without
# removing it.
LOCK_SECONDS = 600


def locked(action):
    """Runs the action while holding the lock file, waiting while another process holds it."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            handle = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - LOCK.stat().st_mtime > LOCK_SECONDS:
                    LOCK.unlink()
            except FileNotFoundError:
                pass
            time.sleep(0.2)
    try:
        os.write(handle, str(os.getpid()).encode("ascii"))
        return action()
    finally:
        os.close(handle)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass


def build_the_library():
    if os.environ.get("ODRIG_CORE_BUILT") == "1" and LIBRARY.is_file():
        return
    locked(make_the_library)


def make_the_library():
    done = subprocess.run(BUILD_COMMAND, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"`{binding.BUILD_COMMAND}` failed with status {done.returncode}:\n{done.stdout}{done.stderr}")
    if not LIBRARY.is_file():
        raise RuntimeError(f"`{binding.BUILD_COMMAND}` did not build {LIBRARY}:\n{done.stdout}{done.stderr}")


build_the_library()

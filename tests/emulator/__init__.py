"""The suite of the emulator and the command tool.

Importing the package builds the core's shared library, so the one test command builds
what it tests. When the build fails, no test runs and make's output is the failure.
"""

import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "core" / "build" / "libodrig_core.dylib"
BUILD_COMMAND = ["make", "-C", str(ROOT / "core"), "shared"]


def build_the_library():
    done = subprocess.run(BUILD_COMMAND, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"`make -C core shared` failed with status {done.returncode}:\n{done.stdout}{done.stderr}")
    if not LIBRARY.is_file():
        raise RuntimeError(f"`make -C core shared` did not build {LIBRARY}:\n{done.stdout}{done.stderr}")


build_the_library()

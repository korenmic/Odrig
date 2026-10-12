"""The suite of the emulator and the command tool.

Importing the package builds the core's shared library, so the one test command builds
what it tests: with `make` on macOS and with the build script elsewhere. When the build
fails, no test runs and the output of the build is the failure.
"""

import pathlib
import subprocess
import sys

from emulator import binding

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "core" / "build" / binding.LIBRARY_NAME
BUILD_SCRIPT = ROOT / "core" / "build.py"
BUILD_COMMAND = ["make", "-C", str(ROOT / "core"), "shared"] if sys.platform == "darwin" else [sys.executable, str(BUILD_SCRIPT), "shared"]


def build_the_library():
    done = subprocess.run(BUILD_COMMAND, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"`{binding.BUILD_COMMAND}` failed with status {done.returncode}:\n{done.stdout}{done.stderr}")
    if not LIBRARY.is_file():
        raise RuntimeError(f"`{binding.BUILD_COMMAND}` did not build {LIBRARY}:\n{done.stdout}{done.stderr}")


build_the_library()

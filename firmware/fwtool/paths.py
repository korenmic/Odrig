"""Where things are: the repository, the work folder, the shared toolchains, and the folder
no tool may write."""

import os
import pathlib

from . import Failure, host

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "firmware"
# The checkout's own work folder: its WLED copy, its builds and what it writes.
WORK = ROOT / "build" / "firmware"


def tools_folder(environ=None, root=ROOT):
    """The folder of the toolchains that checkouts share: `ODRIG_TOOLS` when it is set, else
    the checkout's own `build/`."""
    named = (os.environ if environ is None else environ).get("ODRIG_TOOLS")
    return pathlib.Path(named).expanduser().resolve() if named else root / "build"


TOOLS = tools_folder()
# The firmware tool's part of it: the Python environments, PlatformIO's folders, the caches
# and WLED's source as fetched. Without `ODRIG_TOOLS` it is the work folder itself.
SHARED = TOOLS / "firmware"
SETUP_LOCK = TOOLS / "setup.lock"

HOST_ROOT = host.tool_root(SHARED)
VENV = HOST_ROOT / "venv"
PYTHON = host.program(VENV, "python")
PIO_CORE = HOST_ROOT / "pio"
PIO_CACHE = HOST_ROOT / "pio-cache"
NPM_CACHE = SHARED / "npm-cache"
PIP_CACHE = SHARED / "pip-cache"
# WLED's source as fetched, and the checkout's copy of it, which is patched and built.
WLED_SOURCE = SHARED / "WLED"
WLED = WORK / "WLED"
STANDALONE = WORK / "standalone"
OUT = WORK / "out"
STORAGE = WORK / "storage"
BUILD_LOCK = WORK / "build.lock"

# The newer USB software, beside the build known good: its Python environment, PlatformIO's
# folder with the platform, the framework and the compilers, and the build cache.
NEWER = HOST_ROOT / "newer"
NEWER_VENV = NEWER / "venv"
NEWER_PYTHON = host.program(NEWER_VENV, "python")
NEWER_PIO_CORE = NEWER / "pio"
NEWER_PIO_CACHE = NEWER / "pio-cache"

PATCHES = FIRMWARE / "patches"
REQUIREMENTS = FIRMWARE / "requirements.txt"
NEWER_REQUIREMENTS = FIRMWARE / "requirements-newer.txt"
WIFI_SETTINGS = FIRMWARE / "wifi.json"
LIMIT_SETTINGS = FIRMWARE / "limit.json"

# The factory backup of the board. Nothing is ever written, moved or deleted in it.
PROTECTED = ROOT / "esp32-backup"


def inside(path, folder):
    """Whether a path, followed through every link, is the folder or lies in it."""
    path, folder = pathlib.Path(path).resolve(), pathlib.Path(folder).resolve()
    return path == folder or folder in path.parents


def output(path):
    """A path the tool is about to write, refused when it lies in the factory backup."""
    path = pathlib.Path(path)
    if inside(path, PROTECTED):
        raise Failure("backup-protected", f"{path} is in the factory backup, which no tool writes")
    return path

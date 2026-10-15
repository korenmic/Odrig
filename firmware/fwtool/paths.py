"""Where things are: the repository, the work folder, and the folder no tool may write."""

import pathlib

from . import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "firmware"
WORK = ROOT / "build" / "firmware"

VENV = WORK / "venv"
PYTHON = VENV / "bin" / "python"
PIO_CORE = WORK / "pio"
PIO_CACHE = WORK / "pio-cache"
NPM_CACHE = WORK / "npm-cache"
PIP_CACHE = WORK / "pip-cache"
WLED = WORK / "WLED"
STANDALONE = WORK / "standalone"
OUT = WORK / "out"
STORAGE = WORK / "storage"

# The newer USB software, beside the build known good: its Python environment, PlatformIO's
# folder with the platform, the framework and the compilers, and the build cache.
NEWER = WORK / "newer"
NEWER_VENV = NEWER / "venv"
NEWER_PYTHON = NEWER_VENV / "bin" / "python"
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

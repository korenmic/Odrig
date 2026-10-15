"""The tools in the work folder: the Python environment with PlatformIO, esptool,
littlefs-python and Node.js, and the one of the newer USB software. Every step is skipped
when its result is there."""

import hashlib
import subprocess
import sys

from . import Failure, env, paths, wled

MINIMUM_PYTHON = (3, 10)
STAMP = paths.VENV / "odrig-requirements.sha256"
NEWER_STAMP = paths.NEWER_VENV / "odrig-requirements.sha256"


def _run(what, command, newer=False):
    done = subprocess.run([str(part) for part in command], capture_output=True, text=True, env=env.child(newer=newer))
    if done.returncode != 0:
        raise Failure("setup-failed", f"{what} failed with status {done.returncode}: {(done.stdout + done.stderr).strip()[-600:]}")
    return done.stdout


def requirement_files():
    """WLED's own pinned PlatformIO and its packages first, then the tool's."""
    return [paths.WLED / "requirements.txt", paths.REQUIREMENTS]


def _wanted():
    digest = hashlib.sha256()
    for path in requirement_files():
        digest.update(path.read_bytes())
    return digest.hexdigest()


def python_environment():
    """Makes sure the work folder has WLED's source and the Python environment with every
    package of the two requirement files. Returns the steps it had to do."""
    if sys.version_info < MINIMUM_PYTHON:
        raise Failure("setup-failed", f"Python {'.'.join(map(str, MINIMUM_PYTHON))} or later is needed, this is {sys.version.split()[0]}")
    done = []
    if wled.fetch():
        done.append("fetched WLED")
    wled.check()
    if not paths.PYTHON.exists():
        paths.WORK.mkdir(parents=True, exist_ok=True)
        _run("creating the Python environment", [sys.executable, "-m", "venv", paths.VENV])
        done.append("created the Python environment")
    wanted = _wanted()
    if not STAMP.exists() or STAMP.read_text().strip() != wanted:
        for path in requirement_files():
            _run(f"pip install -r {path.name}", [paths.PYTHON, "-m", "pip", "install", "--disable-pip-version-check", "-r", path])
        STAMP.write_text(wanted + "\n")
        done.append("installed the Python packages")
    return done


def newer_environment():
    """Makes sure the work folder has the newer USB software's Python environment with
    every package of its requirement file. Returns the steps it had to do."""
    done = []
    if not paths.NEWER_PYTHON.exists():
        paths.output(paths.NEWER).mkdir(parents=True, exist_ok=True)
        _run("creating the newer software's Python environment", [sys.executable, "-m", "venv", paths.NEWER_VENV], newer=True)
        done.append("created the newer software's Python environment")
    wanted = hashlib.sha256(paths.NEWER_REQUIREMENTS.read_bytes()).hexdigest()
    if not NEWER_STAMP.exists() or NEWER_STAMP.read_text().strip() != wanted:
        command = [paths.NEWER_PYTHON, "-m", "pip", "install", "--disable-pip-version-check", "-r", paths.NEWER_REQUIREMENTS]
        _run(f"pip install -r {paths.NEWER_REQUIREMENTS.name}", command, newer=True)
        NEWER_STAMP.write_text(wanted + "\n")
        done.append("installed the newer software's Python packages")
    return done


def versions():
    """What the tools in the work folder say they are."""
    def first_line(command):
        return _run(" ".join(map(str, command[1:])), command).strip().splitlines()[0]
    return {
        "python": first_line([paths.PYTHON, "--version"]),
        "platformio": first_line([paths.PYTHON, "-m", "platformio", "--version"]),
        "node": first_line([paths.VENV / "bin" / "node", "--version"]),
        "npm": first_line([paths.VENV / "bin" / "npm", "--version"]),
        "esptool": first_line([paths.PYTHON, "-m", "esptool", "version"]),
    }


def setup():
    """The whole setup. Returns the steps done and the versions found."""
    return python_environment(), versions()

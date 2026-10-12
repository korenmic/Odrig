"""The host program of the tests: the parts of the standalone firmware that know nothing
of the chip, compiled for this computer with the checks of the compiler switched on, and
run on one case at a time."""

import functools
import json
import pathlib
import subprocess
import tempfile

from . import ROOT

SOURCES = ROOT / "firmware" / "standalone" / "src"
PROGRAM = ROOT / "tests" / "firmware" / "host" / "host.cpp"
PARTS = ("settings.cpp",)
FLAGS = ("-std=c++11", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-g")

_folder = tempfile.TemporaryDirectory()


@functools.lru_cache(maxsize=None)
def built():
    """The path of the program, compiled once for a run of the suite."""
    program = pathlib.Path(_folder.name, "host")
    command = ["c++", *FLAGS, f"-I{SOURCES}", str(PROGRAM), *(str(SOURCES / part) for part in PARTS), "-o", str(program)]
    done = subprocess.run(command, capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(f"the host program does not compile:\n{done.stderr}")
    return program


def run(mode, given):
    """Runs one case: the bytes given on standard input, the one line of JSON it prints."""
    done = subprocess.run([str(built()), mode], input=given, capture_output=True)
    if done.returncode != 0:
        raise AssertionError(f"the host program ended with status {done.returncode}: {done.stderr.decode('utf-8', 'replace')[-2000:]}")
    return json.loads(done.stdout)


def _file(label, content):
    if content is None:
        return f"{label} absent\n".encode()
    return f"{label} {len(content)}\n".encode() + content


def settings(config, secrets):
    """The settings the firmware takes from the bytes of the two files; None for a file
    that is absent. The name and the password come back as bytes."""
    found = run("settings", _file("config", config) + _file("secrets", secrets))
    found["name"] = bytes.fromhex(found["name"])
    found["password"] = bytes.fromhex(found["password"])
    return found


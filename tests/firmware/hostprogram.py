"""The host program of the tests: the parts of the standalone firmware that know nothing
of the chip, compiled for this computer with the checks of the compiler switched on, and
run on one case at a time."""

import functools
import json
import pathlib
import subprocess
import tempfile

from . import ROOT
from .compiler import compiled

SOURCES = ROOT / "firmware" / "standalone" / "src"
PROGRAM = ROOT / "tests" / "firmware" / "host" / "host.cpp"
PARTS = ("settings.cpp", "limit.cpp")

_folder = tempfile.TemporaryDirectory()


@functools.lru_cache(maxsize=None)
def built():
    """The path of the program, compiled once for a run of the suite."""
    return compiled([PROGRAM,*(SOURCES / part for part in PARTS)],pathlib.Path(_folder.name,'host'),[SOURCES])


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


def limit(maximum, outputs):
    """What the limiter does to the outputs of one refresh, each given as its bytes,
    three for an LED. The outputs come back as bytes."""
    given = f"maximum {maximum}\noutputs {len(outputs)}\n".encode()
    for output in outputs:
        given += f"{len(output) // 3}\n".encode() + output
    found = run("limit", given)
    found["outputs"] = [bytes.fromhex(output) for output in found["outputs"]]
    return found

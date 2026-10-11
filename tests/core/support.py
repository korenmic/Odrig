"""Helpers shared by the tests of the core: where things are and how the test host is run."""

import collections
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
BUILD = CORE / "build"
LIBRARY = BUILD / "libodrig_core.a"
HOST = BUILD / "odrig_host"

Result = collections.namedtuple("Result", "status out err")


def built(path):
    """The path of a file that `make -C core test` builds, or a failure that says so."""
    if not path.exists():
        raise AssertionError(f"{path} is not built; run the suite with `make -C core test`")
    return path


def host(*arguments, stdin=b""):
    """Runs the test host with these arguments and this input, and returns what it did."""
    done = subprocess.run(
        [str(built(HOST)), *(str(argument) for argument in arguments)],
        input=stdin,
        capture_output=True,
    )
    return Result(done.returncode, done.stdout.decode("ascii"), done.stderr.decode("utf-8", "replace"))


def host_lines(*arguments, stdin=b""):
    """The lines the test host prints for a run that must end well and print no complaint."""
    result = host(*arguments, stdin=stdin)
    if result.status != 0 or result.err:
        raise AssertionError(f"odrig_host {' '.join(map(str, arguments))}: status {result.status}\n{result.err}")
    return result.out.splitlines()

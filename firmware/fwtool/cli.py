"""The command line of the firmware tool: its subcommands, the error line and the exit
statuses.

Status 0 means the command did its work, 1 that it could not, with one line
`error: <reason>: <detail>` on standard error, and 2 that the command line was not
understood.
"""

import argparse
import os
import subprocess
import sys

from . import Failure, env, paths, toolchain

SUITES = {"test": "tests/firmware"}


def parser():
    made = argparse.ArgumentParser(prog="python3 firmware/fw.py", description="Builds the firmware, flashes it, installs a show and restores stock WLED.")
    commands = made.add_subparsers(dest="command", metavar="COMMAND", required=True)
    commands.add_parser("setup", help="put the tools and WLED's source into the work folder")
    commands.add_parser("test", help="run the tests that need no board")
    return made


def _setup(arguments):
    done, versions = toolchain.setup()
    for step in done:
        print(step)
    print(f"work folder: {paths.WORK}")
    for name, version in versions.items():
        print(f"{name}: {version}")
    return 0


def run_suite(folder):
    """Runs every test of a folder, found by discovery, from the repository root."""
    command = [sys.executable, "-m", "unittest", "discover", "-s", folder, "-t", "."]
    return subprocess.run(command, cwd=paths.ROOT, env=module_environment()).returncode


def _test(arguments):
    return run_suite(SUITES["test"])


ACTIONS = {"setup": _setup, "test": _test}


def module_environment():
    """The environment in which the tool's own modules and those of the repository are
    found: the repository root and `firmware/` on the module path."""
    made = env.child()
    earlier = [made["PYTHONPATH"]] if made.get("PYTHONPATH") else []
    made["PYTHONPATH"] = os.pathsep.join([str(paths.ROOT), str(paths.FIRMWARE)] + earlier)
    return made


def report(failure):
    print(f"error: {failure.reason}: {failure.detail}", file=sys.stderr)
    return 1


def main(argv=None):
    """Runs one command in this interpreter, which is the work folder's Python."""
    arguments = parser().parse_args(argv)
    try:
        return ACTIONS[arguments.command](arguments)
    except Failure as failure:
        return report(failure)


def launch(argv):
    """Checks the command line, makes sure the work folder's Python environment is there,
    and hands the command to that environment's Python."""
    parser().parse_args(argv)
    try:
        toolchain.python_environment()
    except Failure as failure:
        return report(failure)
    command = [str(paths.PYTHON), "-m", "fwtool.cli", *argv]
    return subprocess.run(command, env=module_environment()).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

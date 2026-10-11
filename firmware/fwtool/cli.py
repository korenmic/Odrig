"""The command line of the firmware tool: its subcommands, the error line and the exit
statuses.

Status 0 means the command did its work, 1 that it could not, with one line
`error: <reason>: <detail>` on standard error, and 2 that the command line was not
understood.
"""

import argparse
import os
import pathlib
import subprocess
import sys

from . import Failure, board, build, env, flasher, partitions, paths, stock, toolchain

SUITES = {"test": "tests/firmware", "test-board": "tests/board"}


def parser():
    made = argparse.ArgumentParser(prog="python3 firmware/fw.py", description="Builds the firmware, flashes it, installs a show and restores stock WLED.")
    commands = made.add_subparsers(dest="command", metavar="COMMAND", required=True)
    commands.add_parser("setup", help="put the tools and WLED's source into the work folder")
    builder = commands.add_parser("build", help="build an image: the firmware, or with --stock WLED's own environment")
    kind = builder.add_mutually_exclusive_group(required=True)
    kind.add_argument("--stock", dest="kind", action="store_const", const="stock", default="firmware", help="build WLED's own environment, unchanged")
    builder.add_argument("--verbose", action="store_true", help="show every command of the build")
    flash = commands.add_parser("flash", help="write a built image to the board over USB")
    flash.add_argument("--port", metavar="P", help="the board's USB serial port")
    flash.add_argument("--image", metavar="PATH", type=pathlib.Path, help="the image to write, with its .sha256 beside it")
    flash.add_argument("--expect", choices=sorted(board.EXPECTED), default="status", help="what must answer afterwards: the firmware's status, WLED's handshake, or the probe build")
    restore = commands.add_parser("restore-stock", help="write the stock WLED image to the board")
    restore.add_argument("--port", metavar="P", help="the board's USB serial port")
    restore.add_argument("--full", action="store_true", help="also write the stock bootloader and partition table")
    restore.add_argument("--stock-dir", metavar="DIR", type=pathlib.Path, default=stock.FOLDER, help="the folder of the stock files")
    commands.add_parser("test", help="run the tests that need no board")
    on_board = commands.add_parser("test-board", help="run the tests that need the board on USB")
    on_board.add_argument("--port", metavar="P", help="the board's USB serial port")
    return made


def _setup(arguments):
    done, versions = toolchain.setup()
    for step in done:
        print(step)
    print(f"work folder: {paths.WORK}")
    for name, version in versions.items():
        print(f"{name}: {version}")
    return 0


def _build(arguments):
    image, size = build.build(arguments.kind, arguments.verbose)
    print(f"{image}: {size} bytes, SHA-256 {build.sha256(image)}")
    return 0


def write_application(port, image, extra=(), table=None, expect="status"):
    """Puts an application image on the board and waits for what must answer.

    Only the first application partition is written and the boot selection data cleared,
    so that the board starts that partition; `extra` adds the files of a full restore.
    Without a table to go by, the board's own partition table is read and checked first.
    """
    on_port = flasher.Flasher(port)
    size = build.check_size(image)
    partitions.check(on_port.read_table() if table is None else table, size)
    on_port.erase(flasher.BOOT_SELECTION)
    regions = [flasher.APPLICATION] + ([flasher.BOOTLOADER, flasher.TABLE] if extra else [])
    on_port.write([*extra, (flasher.APPLICATION.address, image)], regions, restart=True)
    return board.EXPECTED[expect](port)


def _flash(arguments):
    image = build.checked_image(arguments.image if arguments.image is not None else build.image_path("firmware"))
    build.check_size(image)
    port = board.find(arguments.port)
    print(write_application(port, image, expect=arguments.expect))
    return 0


def _restore_stock(arguments):
    files = stock.checked(arguments.stock_dir, arguments.full)
    port = board.find(arguments.port)
    extra, table = (), None
    if arguments.full:
        extra = ((flasher.BOOTLOADER.address, files.bootloader), (flasher.TABLE.address, files.table))
        table = files.table.read_bytes()
    print(write_application(port, files.application, extra, table, expect="wled"))
    return 0


def run_suite(folder, extra=None):
    """Runs every test of a folder, found by discovery, from the repository root."""
    command = [sys.executable, "-m", "unittest", "discover", "-s", folder, "-t", "."]
    environment = module_environment()
    environment.update(extra or {})
    return subprocess.run(command, cwd=paths.ROOT, env=environment).returncode


def _test(arguments):
    return run_suite(SUITES["test"])


def _test_board(arguments):
    return run_suite(SUITES["test-board"], {board.PORT_VARIABLE: board.find(arguments.port)})


ACTIONS = {"setup": _setup, "build": _build, "flash": _flash, "restore-stock": _restore_stock, "test": _test, "test-board": _test_board}


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

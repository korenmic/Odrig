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

SUITES = {"test": "tests/firmware", "test-board": "tests/board", "test-air": "tests/air"}

# Where the suite that reaches the board over its network finds the board's address.
ADDRESS_VARIABLE = "ODRIG_BOARD_HTTP"


def _seconds(text):
    try:
        seconds = float(text)
    except ValueError:
        seconds = -1.0
    if not 0 < seconds < float("inf"):
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds above 0")
    return seconds


def parser():
    made = argparse.ArgumentParser(prog="python3 firmware/fw.py", description="Builds the firmware, flashes it, installs a show and restores stock WLED.")
    commands = made.add_subparsers(dest="command", metavar="COMMAND", required=True)
    commands.add_parser("setup", help="put the tools and WLED's source into the work folder")
    builder = commands.add_parser("build", help="build an image: the firmware, the probe build, or WLED's own environment")
    kind = builder.add_mutually_exclusive_group()
    kind.add_argument("--stock", dest="kind", action="store_const", const="stock", default="firmware", help="build WLED's own environment, unchanged")
    kind.add_argument("--probe", dest="kind", action="store_const", const="probe", help="build the probe build, which also reports measurements")
    builder.add_argument("--verbose", action="store_true", help="show every command of the build")
    flash = commands.add_parser("flash", help="write a built image to the board over USB")
    flash.add_argument("--port", metavar="P", help="the board's USB serial port")
    flash.add_argument("--image", metavar="PATH", type=pathlib.Path, help="the image to write, with its .sha256 beside it")
    flash.add_argument("--expect", choices=sorted(board.EXPECTED), default="status", help="what must answer afterwards: the firmware's status, WLED's handshake, or the probe build")
    flash.add_argument("--wait", metavar="SECONDS", type=_seconds, default=board.WAIT_SECONDS, help="how long to wait for the board's answer after its restart (default: 20)")
    restore = commands.add_parser("restore-stock", help="write the stock WLED image to the board")
    restore.add_argument("--port", metavar="P", help="the board's USB serial port")
    restore.add_argument("--full", action="store_true", help="also write the stock bootloader and partition table")
    restore.add_argument("--stock-dir", metavar="DIR", type=pathlib.Path, default=stock.FOLDER, help="the folder of the stock files")
    install = commands.add_parser("install-show", help="put a show folder into the board's storage")
    install.add_argument("dir", metavar="DIR", type=pathlib.Path, help="the folder of an installed file set")
    install.add_argument("--port", metavar="P", help="the board's USB serial port")
    install.add_argument("--no-check", action="store_true", help="install any flat folder of files, also an invalid show")
    install.add_argument("--wait", metavar="SECONDS", type=_seconds, default=board.WAIT_SECONDS, help="how long to wait for the board's reply after its restart (default: 20)")
    network = commands.add_parser("set-wifi", help="put the network's name and password from the settings file into the board's storage")
    network.add_argument("--port", metavar="P", help="the board's USB serial port")
    network.add_argument("--settings", metavar="FILE", type=pathlib.Path, help="a settings file other than firmware/wifi.json")
    network.add_argument("--wait", metavar="SECONDS", type=_seconds, default=board.WAIT_SECONDS, help="how long to wait for the board's reply after its restart (default: 20)")
    limiter = commands.add_parser("set-limit", help="put the limit on LED current from the limit file into the board's storage")
    limiter.add_argument("--port", metavar="P", help="the board's USB serial port")
    limiter.add_argument("--settings", metavar="FILE", type=pathlib.Path, help="a limit file other than firmware/limit.json")
    limiter.add_argument("--wait", metavar="SECONDS", type=_seconds, default=board.WAIT_SECONDS, help="how long to wait for the board's reply after its restart (default: 20)")
    limit_read = commands.add_parser("read-limit", help="print the limit on LED current that the board's storage holds")
    limit_read.add_argument("--port", metavar="P", help="the board's USB serial port")
    scratch = commands.add_parser("install-firmware", help="write the built firmware to the board and then the network's name and password and the limit on LED current into its storage")
    scratch.add_argument("--port", metavar="P", help="the board's USB serial port")
    scratch.add_argument("--settings", metavar="FILE", type=pathlib.Path, help="a settings file other than firmware/wifi.json")
    scratch.add_argument("--limit", metavar="FILE", type=pathlib.Path, help="a limit file other than firmware/limit.json")
    scratch.add_argument("--wait", metavar="SECONDS", type=_seconds, default=board.WAIT_SECONDS, help="how long to wait for the board's reply after each restart (default: 20)")
    read = commands.add_parser("read-show", help="copy the installed show from the board into a folder")
    read.add_argument("out", metavar="OUT", type=pathlib.Path, help="a folder that is new or empty")
    read.add_argument("--port", metavar="P", help="the board's USB serial port")
    commands.add_parser("test", help="run the tests that need no board")
    on_board = commands.add_parser("test-board", help="run the tests that need the board on USB")
    on_board.add_argument("--port", metavar="P", help="the board's USB serial port")
    on_air = commands.add_parser("test-air", help="run the tests that need the board on USB and this Mac on the board's Wi-Fi network")
    on_air.add_argument("--http", metavar="ADDRESS", required=True, help="the board's address on its network: host or host:port")
    on_air.add_argument("--port", metavar="P", help="the board's USB serial port")
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


def write_application(port, image, extra=(), table=None, expect="status", wait=board.WAIT_SECONDS):
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
    return board.EXPECTED[expect](port, wait)


def _flash(arguments):
    image = build.checked_image(arguments.image if arguments.image is not None else build.image_path("firmware"))
    build.check_size(image)
    port = board.find(arguments.port)
    print(write_application(port, image, expect=arguments.expect, wait=arguments.wait))
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


def storage_of(port):
    """esptool on the port, the board's storage region, and a file that holds the storage as
    it is now. The chip is left in its bootloader."""
    from . import storage
    on_port = flasher.Flasher(port)
    _, partition = partitions.check(on_port.read_table(), 0)
    region = flasher.storage_region(partition)
    return on_port, region, storage.from_board(on_port, region)


def write_storage(on_port, region, before, make):
    """Puts a new storage image on the board. `make` gives the new image for the one the
    board holds.

    The blocks in which the two differ are written in one call, the whole partition is
    compared with the new image, and the board is restarted. The new image is then the
    newest one the work folder keeps. When any of it fails, the new image is not kept
    and the board is restarted.
    """
    from . import storage
    new_path = None
    try:
        after = make(before)
        new_path = storage.pending(after)
        changed = storage.runs(before, after, storage.geometry(before)[1])
        pieces = []
        for number, (offset, content) in enumerate(changed):
            piece = new_path.with_name(f"{new_path.name}.run-{number}")
            piece.write_bytes(content)
            pieces.append((region.address + offset, piece))
        try:
            on_port.write(pieces, [region], restart=False, data=True)
        finally:
            for _, piece in pieces:
                piece.unlink()
        on_port.verify(region.address, new_path, [region], restart=True)
        storage.keep(new_path, region.size)
    except Failure:
        if new_path is not None:
            storage.discard(new_path)
        on_port.restart()
        raise


def _install_show(arguments):
    from . import storage
    files = storage.folder_files(arguments.dir, check=not arguments.no_check)
    port = board.find(arguments.port)
    on_port, region, before_path = storage_of(port)
    write_storage(on_port, region, before_path.read_bytes(), lambda before: storage.with_show(before, files))
    reply = board.EXPECTED["status"](port, arguments.wait)
    print(reply)
    return 0 if storage.status_error(reply) is None else 1


def store_settings(port, wait, network=None, milliamps=None):
    """Puts settings into WLED's stored settings on the board in one write: the name and
    the password of the network, the limit on LED current, or both. Restarts the board
    and prints what was set and the board's reply to `status`."""
    from . import limit, wifi

    def make(image):
        if network is not None:
            image = wifi.apply(image, network)
        if milliamps is not None:
            image = limit.apply(image, milliamps)
        return image

    on_port, region, before_path = storage_of(port)
    write_storage(on_port, region, before_path.read_bytes(), make)
    reply = board.EXPECTED["status"](port, wait)
    if network is not None:
        print(f"name: {network.name}")
        print("password: set")
    if milliamps is not None:
        print(limit.line(milliamps))
    print(reply)
    return 0


def _network(arguments):
    from . import wifi
    return wifi.read(arguments.settings if arguments.settings is not None else paths.WIFI_SETTINGS)


def _set_wifi(arguments):
    network = _network(arguments)
    return store_settings(board.find(arguments.port), arguments.wait, network=network)


def _set_limit(arguments):
    from . import limit
    milliamps = limit.read(arguments.settings if arguments.settings is not None else paths.LIMIT_SETTINGS)
    return store_settings(board.find(arguments.port), arguments.wait, milliamps=milliamps)


def _read_limit(arguments):
    from . import limit
    port = board.find(arguments.port)
    on_port, _, image_path = storage_of(port)
    try:
        found = limit.stored(image_path.read_bytes())
    finally:
        on_port.restart()
    print(limit.NOT_STORED if found is None else limit.line(found))
    return 0


def _install_firmware(arguments):
    from . import limit
    network = _network(arguments)
    milliamps = limit.read(arguments.limit if arguments.limit is not None else paths.LIMIT_SETTINGS)
    image = build.checked_image(build.image_path("firmware"))
    build.check_size(image)
    port = board.find(arguments.port)
    write_application(port, image, expect="status", wait=arguments.wait)
    return store_settings(port, arguments.wait, network=network, milliamps=milliamps)


def _read_show(arguments):
    from . import storage
    out = paths.output(arguments.out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise Failure("output-not-empty", f"{out} exists and is not an empty folder")
    port = board.find(arguments.port)
    on_port, _, image_path = storage_of(port)
    try:
        files = storage.show_of(image_path.read_bytes())
    finally:
        on_port.restart()
    storage.write_folder(out, files)
    for name in sorted(files):
        print(f"{name}: {len(files[name])} bytes")
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


def _test_air(arguments):
    return run_suite(SUITES["test-air"], {board.PORT_VARIABLE: board.find(arguments.port), ADDRESS_VARIABLE: arguments.http})


ACTIONS = {
    "setup": _setup, "build": _build, "flash": _flash, "restore-stock": _restore_stock,
    "install-show": _install_show, "set-wifi": _set_wifi, "set-limit": _set_limit, "read-limit": _read_limit,
    "install-firmware": _install_firmware, "read-show": _read_show,
    "test": _test, "test-board": _test_board, "test-air": _test_air,
}


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

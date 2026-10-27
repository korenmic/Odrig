"""The command line of the firmware tool: its subcommands, the error line and the exit
statuses.

Status 0 means the command did its work, 1 that it could not, with one line
`error: <reason>: <detail>` on standard error, and 2 that the command line was not
understood.
"""

import argparse
import contextlib
import os
import pathlib
import signal
import subprocess
import sys

from . import Failure, board, build, env, flasher, journal, partitions, paths, stock, toolchain

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
    builder.add_argument("--standalone", action="store_true", help="build the standalone firmware, which holds nothing of WLED; with --probe, its probe build")
    builder.add_argument("--stick", action="store_true", help="build the firmware for a USB stick on the software known good; with --probe, its probe build")
    builder.add_argument("--microsd", action="store_true", help="build the firmware, which reads a microSD card, and keep it as odrig-microsd.bin")
    builder.add_argument("--verbose", action="store_true", help="show every command of the build")
    flash = commands.add_parser("flash", help="write a built image to the board over USB")
    flash.add_argument("--port", metavar="P", help="the board's USB serial port")
    flash.add_argument("--image", metavar="PATH", type=pathlib.Path, help="the image to write, with its .sha256 beside it")
    flash.add_argument("--standalone", action="store_true", help="without --image, write the standalone firmware")
    flash.add_argument("--expect", choices=sorted(board.EXPECTED), default="status", help="what must answer afterwards: the firmware's status, WLED's handshake, or the probe build")
    flash.add_argument("--wait", metavar="SECONDS", type=_seconds, default=board.WAIT_SECONDS, help="how long to wait for the board's answer after its restart (default: 20)")
    bigger = commands.add_parser("big-storage", help="move a board of WLED's layout to the bigger layout, keeping its settings and no show")
    bigger.add_argument("--port", metavar="P", help="the board's USB serial port")
    bigger.add_argument("--wait", metavar="SECONDS", type=_seconds, default=board.WAIT_SECONDS, help="how long to wait for the board's reply after its restart (default: 20)")
    restore = commands.add_parser("restore-stock", help="write the stock WLED image to the board")
    restore.add_argument("--port", metavar="P", help="the board's USB serial port")
    restore.add_argument("--full", action="store_true", help="also write the stock bootloader and partition table")
    restore.add_argument("--stock-dir", metavar="DIR", type=pathlib.Path, default=stock.FOLDER, help="the folder of the stock files")
    install = commands.add_parser("install-show", help="put a show folder into the board's storage")
    install.add_argument("dir", metavar="DIR", type=pathlib.Path, help="the folder of an installed file set")
    install.add_argument("--port", metavar="P", help="the board's USB serial port")
    install.add_argument("--no-check", action="store_true", help="install any flat folder of files, also an invalid show")
    install.add_argument("--wait", metavar="SECONDS", type=_seconds, default=board.SETTLE_SECONDS, help="how long to wait after the restart for the board's reply and for it to read its animations (default: 300)")
    install.add_argument("--dry-run", action="store_true", help="say what would change and write nothing")
    install.add_argument("--keep-copies", metavar="DIR", type=pathlib.Path, help="copy every file the install removes or replaces, as the board holds it, into a folder that is new or empty, before anything is written")
    install.add_argument("--limits", action="store_true", help="also install the folder's limits.json, the budgets of the current limits; without it the board keeps its own, or none")
    recover = commands.add_parser("recover-storage", help="finish or give up a change of the board's storage that was cut")
    recover.add_argument("--port", metavar="P", help="the board's USB serial port")
    recover.add_argument("--whole", action="store_true", help="write the new image of the change whole: the last resort when storage changed since the change began")
    recover.add_argument("--wait", metavar="SECONDS", type=_seconds, default=board.WAIT_SECONDS, help="how long to wait for the board's reply after its restart (default: 20)")
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
    scratch.add_argument("--wait", metavar="SECONDS", type=_seconds, default=board.SETTLE_SECONDS, help="how long to wait after each restart for the board's reply, and after the last for it to read its animations (default: 300)")
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
    if arguments.microsd:
        kind = "microsd"
    elif arguments.standalone:
        kind = {"firmware": "standalone", "probe": "standalone-probe"}[arguments.kind]
    elif arguments.stick:
        kind = build.STICK_OF[arguments.kind]
    else:
        kind = arguments.kind
    image, size = build.build(kind, arguments.verbose)
    print(f"{image}: {size} bytes, SHA-256 {build.sha256(image)}")
    return 0


def write_application(port, image, extra=(), table=None, expect="status", wait=board.WAIT_SECONDS, regions=()):
    """Puts an application image on the board and waits for what must answer.

    Only the first application partition is written and the boot selection data cleared,
    so that the board starts that partition; `extra` adds the files of a full restore, and
    `regions` the regions beyond the bootloader and the table that they may lie in.
    Without a table to go by, the board's own partition table is read and checked first,
    and its layout is printed.
    """
    on_port = flasher.Flasher(port)
    size = build.check_size(image)
    if table is None:
        table = on_port.read_table()
        partitions.check(table, size)
        print(partitions.layout_line(table))
    else:
        partitions.check(table, size)
    on_port.erase(flasher.BOOT_SELECTION)
    allowed = [flasher.APPLICATION] + ([flasher.BOOTLOADER, flasher.TABLE, *regions] if extra else [])
    on_port.write([*extra, (flasher.APPLICATION.address, image)], allowed, restart=True)
    return board.EXPECTED[expect](port, wait)


def _flash(arguments):
    built = build.image_path("standalone" if arguments.standalone else "firmware")
    image = build.checked_image(arguments.image if arguments.image is not None else built)
    build.check_size(image)
    port = board.find(arguments.port)
    print(write_application(port, image, expect=arguments.expect, wait=arguments.wait))
    return 0


def wleds_storage(port, table):
    """On a board of the bigger layout, a storage for the layout of `table`, WLED's, that
    holds the board's settings and no show: the file and its region. The board's storage is
    kept in the work folder first, and the layout and that file are printed. None on any
    other board, also one whose table cannot be read."""
    from . import storage
    on_port = flasher.Flasher(port)
    try:
        found = partitions.parse(on_port.read_table())
    except Failure as failure:
        if failure.reason != "layout-mismatch":
            raise
        return None
    if partitions.layout_of(found) != partitions.BIGGER_NAME:
        return None
    region = flasher.storage_region(partitions.storage(found))
    print(f"layout: {partitions.BIGGER_NAME}, storage {region.size} bytes")
    before = storage.from_board(on_port, region)
    print(f"kept: {before}")
    target = flasher.storage_region(partitions.storage(partitions.parse(table)))
    return storage.pending(storage.with_settings(before.read_bytes(), target.size)), target


def _restore_stock(arguments):
    from . import storage
    files = stock.checked(arguments.stock_dir, arguments.full)
    port = board.find(arguments.port)
    extra, table, regions, made = (), None, (), None
    if arguments.full:
        extra = ((flasher.BOOTLOADER.address, files.bootloader), (flasher.TABLE.address, files.table))
        table = files.table.read_bytes()
        made = wleds_storage(port, table)
        if made is not None:
            extra += ((made[1].address, made[0]),)
            regions = (made[1],)
    try:
        print(write_application(port, files.application, extra, table, expect="wled", regions=regions))
    except Failure:
        if made is not None:
            storage.discard(made[0])
        raise
    if made is not None:
        storage.keep(made[0], made[1].size)
    return 0


def _big_storage(arguments):
    """Moves a board of WLED's layout to the bigger one. The storage of the bigger layout,
    which holds the board's settings, is made so that all it holds lies in the room of
    WLED's second firmware slot, and is written there first; only then is the new table
    written. Until that write the board has WLED's layout whole."""
    import tempfile
    from . import storage
    port = board.find(arguments.port)
    on_port = flasher.Flasher(port)
    table = on_port.read_table()
    partitions.check(table, 0)
    print(partitions.layout_line(table))
    found = partitions.parse(table)
    if found == list(partitions.BIGGER):
        on_port.restart()
        print("nothing to do: the board has the bigger layout")
        return 0
    if found != list(partitions.WLED):
        on_port.restart()
        raise Failure("layout-mismatch", "the board's partition table is not WLED's own, entry for entry; only that one is moved")
    old = flasher.storage_region(partitions.storage(found))
    new = flasher.storage_region(partitions.storage(partitions.BIGGER))
    before = storage.from_board(on_port, old)
    print(f"kept: {before}")
    room = old.address - new.address
    made = storage.with_settings(before.read_bytes(), new.size, room=room)
    with tempfile.TemporaryDirectory() as folder:
        head = pathlib.Path(folder, "storage-head.bin")
        head.write_bytes(made[:room])
        bigger = pathlib.Path(folder, "table.bin")
        bigger.write_bytes(partitions.table(partitions.BIGGER))
        try:
            on_port.write([(new.address, head)], [new], restart=False, data=True)
            on_port.verify(new.address, head, [new], restart=False)
            on_port.erase(flasher.BOOT_SELECTION)
            on_port.write([(flasher.TABLE.address, bigger)], [flasher.TABLE], restart=False)
            on_port.verify(flasher.TABLE.address, bigger, [flasher.TABLE], restart=True)
        except Failure:
            on_port.restart()
            raise
    print(board.EXPECTED["status"](port, arguments.wait))
    return 0


def storage_of(port, say=True):
    """esptool on the port, the board's storage region, and a file that holds the storage as
    it is now. The chip is left in its bootloader. With `say` the layout the board's table
    has is printed."""
    from . import storage
    on_port = flasher.Flasher(port)
    table = on_port.read_table()
    _, partition = partitions.check(table, 0)
    if say:
        print(partitions.layout_line(table))
    region = flasher.storage_region(partition)
    try:
        return on_port, region, storage.from_board(on_port, region)
    except KeyboardInterrupt:
        raise Failure("cancelled", f"cancelled by an interrupt while the board's storage was read; nothing was written{_restarted(on_port)}") from None


@contextlib.contextmanager
def held_interrupts():
    """Holds an interrupt from the keyboard while the block runs: the block is not cut,
    and the list it is given holds True for each interrupt that came."""
    came = []
    try:
        earlier = signal.signal(signal.SIGINT, lambda number, frame: came.append(True))
    except ValueError:
        # Only the main thread receives signals.
        yield came
        return
    try:
        yield came
    finally:
        signal.signal(signal.SIGINT, earlier)


def _pieces(region, new_path, found, name):
    """Files beside the new image, one for each run, and the address each goes to."""
    pieces = []
    for number, (offset, content) in enumerate(found):
        piece = new_path.with_name(f"{new_path.name}.{name}-{number}")
        piece.write_bytes(content)
        pieces.append((region.address + offset, piece))
    return pieces


def _restarted(on_port):
    """Restarts the board out of its bootloader; the words to add when it could not."""
    try:
        on_port.restart()
        return ""
    except Failure as failure:
        return f"; the board could not be restarted ({failure.detail}): restart it by its button or by its cable"


def apply_change(on_port, region, new_path, change, found):
    """Writes the runs of a change in their order and compares them, as the journal of the
    change records step by step: first the runs of free blocks, which leave the file system
    of the board as it was; then the runs of blocks in use, the commit; then the chip
    compares every written run with the new image. Each call tells esptool not to reset
    the chip, which it would do after a failure too. A failure, or an interrupt from the
    keyboard, before the commit ends with the change given up and the board restarted; in
    the commit or after it, the journal stays and the chip stays in its bootloader. Returns
    whether an interrupt came while it was held."""
    from . import storage
    pieces = _pieces(region, new_path, found.free, "free") + _pieces(region, new_path, found.in_use, "in-use")
    free, in_use = pieces[:len(found.free)], pieces[len(found.free):]
    try:
        try:
            on_port.write(free, [region], restart=False, data=True)
        except (Failure, KeyboardInterrupt) as stopped:
            journal.end()
            storage.discard(new_path)
            said = "cancelled by an interrupt" if isinstance(stopped, KeyboardInterrupt) else stopped.detail
            reason = "cancelled" if isinstance(stopped, KeyboardInterrupt) else stopped.reason
            raise Failure(reason, f"{said}; the change was not made: no block the board's file system uses was written, and the board holds its storage from before{_restarted(on_port)}") from None
        with held_interrupts() as came:
            try:
                journal.step(change, journal.STEP_COMMIT)
                on_port.write(in_use, [region], restart=False, data=True)
                journal.step(change, journal.STEP_COMPARE)
                on_port.compare(pieces, [region], restart=False)
            except Failure as failure:
                raise Failure("recovery-needed", f"{failure.detail}; the change was cut at its step {change['step']}, when the blocks the board's file system uses were being written or compared. "
                              "The board stays in its bootloader, so that it does not start on a storage it may not read; run python3 firmware/fw.py recover-storage") from None
        return bool(came)
    finally:
        for _, piece in pieces:
            piece.unlink(missing_ok=True)


def plan_line(found, block_size):
    """The line that says what a change writes: its blocks and bytes, the free ones first."""
    from . import storage
    free, in_use = storage.run_bytes(found.free), storage.run_bytes(found.in_use)
    if not free + in_use:
        return "storage: unchanged: no block to write"
    return f"storage: {(free + in_use) // block_size} blocks to write, {free + in_use} bytes: {free // block_size} free first, then {in_use // block_size} in use"


def write_storage(on_port, region, before, make, say=lambda line: None):
    """Puts a new storage image on the board. `make` gives the new image for the one the
    board holds; `say` takes the lines that tell what is written and how it ended.

    Only the blocks in which the two differ are written, in the order of `apply_change`.
    The new image is then the newest one the work folder keeps. When the new image cannot
    be made, or nothing differs, nothing is written and the board is restarted.
    """
    from . import storage
    try:
        after = make(before)
        found = storage.plan(before, after) if after != before else storage.Plan([], [])
    except (Failure, KeyboardInterrupt) as stopped:
        restarted = _restarted(on_port)
        if isinstance(stopped, KeyboardInterrupt):
            raise Failure("cancelled", f"cancelled by an interrupt before anything was written{restarted}") from None
        raise
    block_size = storage.geometry(before)[1]
    written = storage.run_bytes(found.free) + storage.run_bytes(found.in_use)
    if not written:
        on_port.restart()
        say("storage: unchanged: nothing written; the board restarts")
        return
    say(plan_line(found, block_size))
    new_path = storage.pending(after)
    change = journal.begin(region, new_path, found)
    held = apply_change(on_port, region, new_path, change, found)
    storage.keep(new_path, region.size)
    journal.end()
    restarted = _restarted(on_port)
    say(f"storage: committed: {written} bytes written and compared" + ("; an interrupt came while the change was committed and waited for it" if held else "") + (restarted or "; the board restarts"))


def show_lines(present, wanted):
    """The lines that say how the files of `/odrig` change: how many are kept, and each
    file added, replaced or removed with its bytes."""
    from . import storage
    change = storage.change_of(present, wanted)
    lines = [f"show: kept {len(change.kept)} files" + ("; nothing added, replaced or removed" if change.kept == sorted(wanted) and not change.removed else "")]
    lines += [f"show: added {name}, {len(wanted[name])} bytes" for name in change.added]
    lines += [f"show: replaced {name}, {len(wanted[name])} bytes, was {len(present[name])}" for name in change.replaced]
    lines += [f"show: removed {name}, {len(present[name])} bytes" for name in change.removed]
    return lines


def _install_show(arguments):
    from . import storage
    files = storage.folder_files(arguments.dir, check=not arguments.no_check)
    if arguments.limits:
        storage.check_limits(arguments.dir, files)
    else:
        files = {name: data for name, data in files.items() if name != storage.LIMITS_NAME}
    copies = None
    if arguments.keep_copies is not None:
        copies = paths.output(arguments.keep_copies)
        if copies.exists() and (not copies.is_dir() or any(copies.iterdir())):
            raise Failure("output-not-empty", f"{copies} exists and is not an empty folder")
    port = board.find(arguments.port)
    on_port, region, before_path = storage_of(port)
    before = before_path.read_bytes()
    try:
        present = storage.show_of(before)
        for name in storage.KEPT_NAMES:
            if name in present and name not in files:
                # The saved order and the saved playlist are the operator's choices: a
                # folder without them keeps the board's.
                files = dict(files, **{name: present[name]})
        if not arguments.limits and storage.LIMITS_NAME in present:
            # The budgets are for the supplies the board is fed from: without --limits the
            # board keeps its own, as it keeps none when it has none.
            files = dict(files, **{storage.LIMITS_NAME: present[storage.LIMITS_NAME]})
        files = storage.with_board_generation(files, present)
        for line in show_lines(present, files):
            print(line)
        if copies is not None:
            change = storage.change_of(present, files)
            storage.write_folder(copies, {name: present[name] for name in change.replaced + change.removed})
            print(f"kept copies: {len(change.replaced) + len(change.removed)} files in {copies}")
    except (Failure, KeyboardInterrupt) as stopped:
        restarted = _restarted(on_port)
        if isinstance(stopped, KeyboardInterrupt):
            raise Failure("cancelled", f"cancelled by an interrupt before anything was written{restarted}") from None
        raise
    if arguments.dry_run:
        try:
            after = storage.with_show(before, files)
            found = storage.plan(before, after) if after != before else storage.Plan([], [])
        except (Failure, KeyboardInterrupt):
            on_port.restart()
            raise
        on_port.restart()
        print(plan_line(found, storage.geometry(before)[1]))
        print("storage: dry run: nothing written; the board restarts")
        return 0
    write_storage(on_port, region, before, lambda image: storage.with_show(image, files), say=print)
    reply = board.settled(port, arguments.wait)
    print(reply)
    print(board.outcome(reply))
    return 0 if storage.status_error(reply) is None else 1


def _recover_storage(arguments):
    """Finishes or gives up the change of the board's storage that the journal names."""
    from . import storage
    change = journal.read()
    if change is None:
        print("storage: nothing to recover: no change of the board's storage is unfinished")
        return 0
    port = board.find(arguments.port)
    on_port = flasher.Flasher(port)
    table = on_port.read_table()
    _, partition = partitions.check(table, 0)
    print(partitions.layout_line(table))
    region = flasher.storage_region(partition)
    if (region.address, region.size) != (change["address"], change["size"]):
        raise Failure("layout-mismatch", f"the change was of storage at {change['address']:#x}, {change['size']} bytes, and the board's table puts it at "
                      f"{region.address:#x}, {region.size} bytes; nothing was written. The chip stays in its bootloader")
    new_path = paths.STORAGE / change["image"]
    if change["step"] == journal.STEP_FREE:
        journal.end()
        storage.discard(new_path)
        on_port.restart()
        print("storage: given up: the change was cut before its commit; the board holds its storage from before; the board restarts")
        print(board.EXPECTED["status"](port, arguments.wait))
        return 0
    if not new_path.exists():
        raise Failure("recovery-needed", f"the new image {new_path} of the change is gone; nothing was written. The chip stays in its bootloader")
    after = new_path.read_bytes()
    if len(after) != region.size:
        raise Failure("recovery-needed", f"the new image {new_path} has {len(after)} bytes and the storage {region.size}; nothing was written")
    if arguments.whole:
        found = storage.Plan([], [(0, after)])
    else:
        found = storage.Plan(*journal.runs_of(change, after))
        rest = []
        for number, (offset, length) in enumerate(journal.outside(found.free + found.in_use, region.size)):
            piece = new_path.with_name(f"{new_path.name}.rest-{number}")
            piece.write_bytes(after[offset:offset + length])
            rest.append((region.address + offset, piece))
        try:
            on_port.compare(rest, [region], restart=False)
        except Failure as failure:
            if failure.reason != "verify-failed":
                raise
            raise Failure("storage-changed", "the board's storage outside the blocks of the change is not what it was when the change began: something else wrote it since. "
                          "Nothing was written, and the chip stays in its bootloader. python3 firmware/fw.py recover-storage --whole writes the new image whole") from None
        finally:
            for _, piece in rest:
                piece.unlink(missing_ok=True)
    journal.step(change, journal.STEP_COMMIT)
    with held_interrupts():
        pieces = _pieces(region, new_path, found.free, "free") + _pieces(region, new_path, found.in_use, "in-use")
        try:
            on_port.write(pieces[:len(found.free)], [region], restart=False, data=True)
            on_port.write(pieces[len(found.free):], [region], restart=False, data=True)
            journal.step(change, journal.STEP_COMPARE)
            on_port.compare(pieces, [region], restart=False)
        except Failure as failure:
            raise Failure("recovery-needed", f"{failure.detail}; the recovery was cut and the journal stays: run python3 firmware/fw.py recover-storage again") from None
        finally:
            for _, piece in pieces:
                piece.unlink(missing_ok=True)
    storage.keep(new_path, region.size)
    journal.end()
    written = storage.run_bytes(found.free) + storage.run_bytes(found.in_use)
    on_port.restart()
    print(f"storage: committed: the change was finished: {written} bytes written and compared; the board restarts")
    print(board.EXPECTED["status"](port, arguments.wait))
    return 0


def store_settings(port, wait, network=None, milliamps=None, settled=False, say=True):
    """Puts settings into WLED's stored settings on the board in one write: the name and
    the password of the network, the limit on LED current, or both. Restarts the board
    and prints what was set and the board's reply to `status`. With `settled` that reply
    is the one the board gives once it has read every installed animation to its end.
    With `say` the layout of the board's table is printed first."""
    from . import limit, wifi

    def make(image):
        if network is not None:
            image = wifi.apply(image, network)
        if milliamps is not None:
            image = limit.apply(image, milliamps)
        return image

    on_port, region, before_path = storage_of(port, say)
    write_storage(on_port, region, before_path.read_bytes(), make)
    reply = board.settled(port, wait) if settled else board.EXPECTED["status"](port, wait)
    if network is not None:
        print(f"name: {network.name}")
        print("password: set")
    if milliamps is not None:
        print(limit.line(milliamps))
    print(reply)
    if settled:
        print(board.outcome(reply))
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
    return store_settings(port, arguments.wait, network=network, milliamps=milliamps, settled=True, say=False)


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
    "setup": _setup, "build": _build, "flash": _flash, "restore-stock": _restore_stock, "big-storage": _big_storage,
    "install-show": _install_show, "set-wifi": _set_wifi, "set-limit": _set_limit, "read-limit": _read_limit,
    "install-firmware": _install_firmware, "read-show": _read_show, "recover-storage": _recover_storage,
    "test": _test, "test-board": _test_board, "test-air": _test_air,
}


# The commands that read or write the board's flash. None of them runs while a change of the
# board's storage is unfinished: each would read a storage that may be half written, or start
# the board on it, and WLED formats a file system it cannot read.
TOUCHES_THE_BOARD = ("flash", "restore-stock", "big-storage", "install-show", "set-wifi", "set-limit", "read-limit", "install-firmware", "read-show", "test-board", "test-air")


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


def parsed(argv):
    """The arguments of a command line. What does not go together is a usage error."""
    made = parser()
    arguments = made.parse_args(argv)
    if arguments.command == "build" and arguments.microsd:
        if arguments.kind != "firmware" or arguments.stick or arguments.standalone:
            made.error("--microsd does not go with --stock, --probe, --stick or --standalone")
    if arguments.command == "build" and arguments.standalone and arguments.kind == "stock":
        made.error("--standalone does not go with --stock: the standalone firmware holds nothing of WLED")
    if arguments.command == "build" and arguments.stick and arguments.kind == "stock":
        made.error("--stick does not go with --stock: stock WLED is built on the software it comes with")
    if arguments.command == "build" and arguments.stick and arguments.standalone:
        made.error("--stick does not go with --standalone: the stick's build is of the firmware with WLED")
    return arguments


def main(argv=None):
    """Runs one command in this interpreter, which is the work folder's Python."""
    arguments = parsed(argv)
    try:
        if arguments.command in TOUCHES_THE_BOARD:
            journal.refuse_open()
        return ACTIONS[arguments.command](arguments)
    except Failure as failure:
        return report(failure)
    except KeyboardInterrupt:
        return report(Failure("cancelled", "cancelled by an interrupt"))


def launch(argv):
    """Checks the command line, makes sure the work folder's Python environment is there,
    and hands the command to that environment's Python."""
    parsed(argv)
    try:
        toolchain.python_environment()
    except Failure as failure:
        return report(failure)
    command = [str(paths.PYTHON), "-m", "fwtool.cli", *argv]
    return subprocess.run(command, env=module_environment()).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

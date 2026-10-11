"""Helpers shared by the tests that need the board: running the tool, what the board runs,
and what it says on its port."""

import collections
import contextlib
import io
import json
import pathlib
import tempfile
import time

from odrig import pack
from odrigctl import client

from fwtool import Failure, board, build, cli, paths, storage

from . import PORT, ROOT

EXAMPLE_SHOW = ROOT / "shows" / "example" / "show.json"
TWO_LEGS = ROOT / "mapping" / "legs-2.json"
TEN_LEGS = ROOT / "mapping" / "legs-10.json"
ANIMATIONS = ROOT / "animations"

# One 60-LED strip is wired, fed from the board's 3.3 V pin: no show that is installed
# may be brighter than this, and the shows the suite packs are dimmer still.
BRIGHTEST = 40
DIM = 32

Result = collections.namedtuple("Result", "status out err")

# What must answer after an image of each kind was flashed.
ANSWERS = {"probe": "probe", "stock": "wled"}

# The kind of image the suite leaves on the board.
LEFT_ON_THE_BOARD = "probe"

_running = None


def tool(*arguments):
    """Runs one command line of the firmware tool in this interpreter."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = cli.main([str(argument) for argument in arguments])
        except SystemExit as stopped:
            status = stopped.code
    return Result(status, out.getvalue(), err.getvalue())


def on_port(*arguments):
    """The same, on the board's port."""
    return tool(*arguments, "--port", PORT)


def built(kind):
    """The image of one kind, built now when the work folder does not hold it."""
    image = build.image_path(kind)
    try:
        return build.checked_image(image)
    except Failure:
        build.build(kind)
        return build.checked_image(image)


def answers(ask):
    try:
        ask(PORT, wait=1.0)
    except Failure:
        return False
    return True


def running():
    """The kind of image the board runs: `probe`, `stock`, or None when nothing known
    answers. The questions are asked in an order in which none disturbs the next."""
    global _running
    if _running is None:
        if answers(board.probe):
            _running = "probe"
        elif answers(board.handshake):
            _running = "stock"
    return _running


def flash(kind):
    """Flashes the image of one kind and waits for its answer."""
    global _running
    _running = None
    done = on_port("flash", "--image", built(kind), "--expect", ANSWERS[kind])
    if done.status != 0:
        raise AssertionError(f"flashing the {kind} image failed: {done.err}")
    _running = kind
    return done


def restore_stock():
    """Restores stock WLED and waits for its handshake."""
    global _running
    _running = None
    done = on_port("restore-stock")
    if done.status == 0:
        _running = "stock"
    return done


def ensure(kind):
    """Makes the board run the image of one kind, flashing only when it runs another."""
    if running() != kind:
        flash(kind)


def leave_the_board():
    """Puts on the board what the suite leaves there: the image and the dim example show."""
    ensure(LEFT_ON_THE_BOARD)
    with dim_show() as folder:
        if installed() != files_of(folder):
            install(folder)


@contextlib.contextmanager
def dim_show(show=EXAMPLE_SHOW, mapping=TWO_LEGS, sources=ANIMATIONS, brightness=DIM, compressed=True):
    """A temporary folder that holds a show packed with its brightness replaced."""
    with tempfile.TemporaryDirectory() as folder:
        changed = json.loads(pathlib.Path(show).read_text())
        changed["brightness"] = brightness
        dimmed = pathlib.Path(folder, "show.json")
        dimmed.write_text(json.dumps(changed))
        out = pathlib.Path(folder, "show")
        pack.pack(dimmed, mapping, sources, out, compressed=compressed)
        yield out


def files_of(folder):
    """The files of a folder: the content of each by its name."""
    return {path.name: path.read_bytes() for path in sorted(pathlib.Path(folder).iterdir())}


def brightness_of(folder):
    """The brightness a show folder starts with, or None when its show file gives none."""
    try:
        value = json.loads(pathlib.Path(folder, "show.json").read_bytes()).get("brightness")
    except (OSError, ValueError, AttributeError):
        return None
    return value if isinstance(value, int) else None


def install(folder, *extra):
    """Installs a show folder on the board. A show brighter than the wired strip allows is
    refused here, before the tool is started."""
    brightness = brightness_of(folder)
    if brightness is not None and brightness > BRIGHTEST:
        raise AssertionError(f"{folder} has brightness {brightness}; nothing above {BRIGHTEST} is installed on the board")
    return on_port("install-show", folder, *extra)


def storage_image():
    """The board's storage as it is now, whole. The board is restarted afterwards."""
    on_the_port, _, image = cli.storage_of(PORT)
    try:
        return image.read_bytes()
    finally:
        on_the_port.restart()
        wait_for_the_board()


def installed():
    """The files of the show installed on the board: the content of each by its name."""
    return storage.show_of(storage_image())


def wait_for_the_board():
    """Waits until the image the board runs answers again after a restart."""
    kind = running()
    if kind is not None:
        {"probe": board.probe, "stock": board.handshake}[kind](PORT)


def probe():
    """The probe build's report."""
    return json.loads(board.probe(PORT))


def heard(data, seconds):
    """Sends bytes, which may be none, and returns every line that arrives in a length of
    time. The board is not reset."""
    lines = []

    def keep(line):
        lines.append(line)
        return False

    with contextlib.suppress(client.Unreachable):
        client.serial_exchange(PORT, data, seconds, keep)
    return lines


def each_second(seconds, read=probe):
    """One report for each of a number of seconds in a row."""
    reports = []
    start = time.monotonic()
    for number in range(seconds):
        time.sleep(max(0.0, start + number + 1 - time.monotonic()))
        reports.append(read())
    return reports

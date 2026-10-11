"""Helpers shared by the tests that need the board: running the tool, what the board runs,
and what it says on its port."""

import collections
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import time

from emulator import recfile
from odrig import jsonframes, mapping as mapping_file, odrg, pack
from odrig.generators import dense
from odrigctl import cli as command_tool
from odrigctl import client

from fwtool import Failure, board, build, cli, flasher, paths, storage

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
ANSWERS = {"firmware": "status", "probe": "probe", "stock": "wled"}

# The kind of image the suite leaves on the board.
LEFT_ON_THE_BOARD = "firmware"

# Every command of docs/commands.md and every error code the command tool can cause on a
# valid show, with no brightness above what the wired strip allows. It begins with the
# state after power-on and asks for the status after every change.
SESSION = (
    "status",
    "brightness 20", "status",
    "play 2", "status",
    "off", "status",
    "on", "status",
    "play 1", "status",
    "play 99",
    "play abc",
    "brightness 256",
    "play " + "7" * 70,
    "brightness 0", "status",
    "brightness 40", "status",
    "play 3", "status",
)

_running = None
_installed = None


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
    """The kind of image the board runs: `probe`, `firmware`, `stock`, or None when nothing
    known answers. The questions are asked in an order in which none disturbs the next."""
    global _running
    if _running is None:
        if answers(board.probe):
            _running = "probe"
        elif answers(board.status):
            _running = "firmware"
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
    """Puts on the board what the suite leaves there: the firmware and the dim example
    show, playing as after power-on."""
    ensure(LEFT_ON_THE_BOARD)
    with dim_show() as folder:
        ensure_installed(folder)
    restart()


def ensure_installed(folder, *extra):
    """Makes the board hold a show folder, installing only when it holds something else.
    What this run installed last is remembered, so that the board is not asked again."""
    global _installed
    wanted = files_of(folder)
    if _installed is None:
        _installed = installed()
    if _installed != wanted:
        done = install(folder, *extra)
        if "error: " in done.err:
            raise AssertionError(f"installing {folder} failed: {done.out}{done.err}")


def restart():
    """Restarts the board and waits until what it runs answers again."""
    flasher.Flasher(PORT).restart()
    wait_for_the_board()


def command(port, *words, timeout=3.0):
    """Sends one command with the command tool. Returns the tool's exit status and the
    reply as it printed it, read as JSON."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = command_tool.main(["--port", str(port), "--timeout", str(timeout), *words])
        except SystemExit as stopped:
            status = stopped.code
    if status not in (0, 1):
        raise AssertionError(f"`{' '.join(words)}` on {port}: status {status}: {err.getvalue()}")
    return status, json.loads(out.getvalue())


def without_fps(reply):
    """A reply without the one member that differs between a board and an emulator."""
    return {name: value for name, value in reply.items() if name != "fps"}


def session(port, lines=SESSION):
    """Sends the lines of a session one by one. Returns, for each, the tool's exit status
    and the reply without its `fps`."""
    answers_given = []
    for line in lines:
        status, reply = command(port, *line.split(" "))
        answers_given.append((line, status, without_fps(reply)))
    return answers_given


@contextlib.contextmanager
def emulator(folder):
    """Runs the emulator on a show folder and gives the path of its serial port."""
    built = subprocess.run(["make", "-C", str(ROOT / "core"), "shared"], capture_output=True, text=True)
    if built.returncode != 0:
        raise AssertionError(f"`make -C core shared` failed:\n{built.stdout}{built.stderr}")
    with tempfile.TemporaryDirectory() as work:
        link = pathlib.Path(work, "serial")
        process = subprocess.Popen(
            [sys.executable, "-m", "emulator", str(folder), "--port", "0", "--serial-link", str(link)],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            started = [process.stdout.readline(), process.stdout.readline()]
            if not started[1].startswith("serial: "):
                raise AssertionError(f"the emulator did not start: {started} {process.stderr.read()}")
            yield link
        finally:
            process.terminate()
            process.wait(timeout=10)
            process.stdout.close()
            process.stderr.close()


def reason_in_the_emulator(folder):
    """The reason the emulator's `status` reports for a show folder, or None."""
    with emulator(folder) as link:
        return command(link, "status")[1]["error"]


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
    global _installed
    brightness = brightness_of(folder)
    if brightness is not None and brightness > BRIGHTEST:
        raise AssertionError(f"{folder} has brightness {brightness}; nothing above {BRIGHTEST} is installed on the board")
    _installed = None
    done = on_port("install-show", folder, *extra)
    if "error: " not in done.err:
        _installed = files_of(folder)
    return done


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
        board.EXPECTED[ANSWERS[kind]](PORT)


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


def legs_mapping(width, legs=10, rows_per_leg=3, pins=None):
    """The text of a mapping file: legs of some rows each, leg 1 at the top, every chain
    starting on the right, on the pins given or on pins 1, 2, 3 and so on."""
    pins = list(range(1, legs + 1)) if pins is None else list(pins)
    height = legs * rows_per_leg
    described = [
        {"leg": number + 1, "pin": pins[number], "first_led": "right",
         "rows": [height - number * rows_per_leg - row for row in range(rows_per_leg)]}
        for number in range(legs)
    ]
    return json.dumps({"version": 1, "width": width, "legs": described})


def own_colour(position):
    """A colour for the pixel at a position that no other pixel of a canvas has. The values
    are small, so that a whole canvas of them stays below what WLED's current limiter
    allows two legs."""
    return bytes([(position * 5) % 53, (position * 3) % 47, (position * 11) % 41])


@contextlib.contextmanager
def show_folder(mapping, animations, brightness=DIM, start=1):
    """A temporary show folder: a mapping, given as a path or as text, and one animation
    item for each `(name, animation bytes)`, the first one starting at power-on."""
    with tempfile.TemporaryDirectory() as work:
        folder = pathlib.Path(work, "show")
        folder.mkdir()
        text = pathlib.Path(mapping).read_text() if isinstance(mapping, pathlib.Path) else mapping
        (folder / "mapping.json").write_text(text)
        items = [{"id": number, "file": name} for number, (name, _) in enumerate(animations, 1)]
        (folder / "show.json").write_text(json.dumps({"version": 1, "brightness": brightness, "items": items, "start": start}))
        for name, content in animations:
            (folder / name).write_bytes(content)
        yield folder


def canvas_of(mapping):
    """The width and the height of the canvas of a mapping, given as a path or as text."""
    data = mapping.read_bytes() if isinstance(mapping, pathlib.Path) else mapping.encode()
    read = mapping_file.loads(data)
    return read.width, read.height


def one_frame(mapping):
    """An animation of one frame in which every pixel has a colour of its own."""
    width, height = canvas_of(mapping)
    picture = b"".join(own_colour(position) for position in range(width * height))
    return odrg.encode(jsonframes.Animation(width, height, ((1000, picture),)))


def one_frame_show(mapping=TWO_LEGS, brightness=DIM):
    """A show folder whose one item is the one-frame animation, playing from power-on."""
    return show_folder(mapping, [("frame.odrg", one_frame(mapping))], brightness)


def dense_clip(compressed, seconds=10):
    """The dense 60 x 30 clip of some seconds: a smooth full-colour field, every LED lit."""
    return odrg.encode(jsonframes.Animation(60, 30, tuple(dense.frames(60, 30, seconds))), compressed=compressed)


def recorded(folder, seconds, script=""):
    """The emulator's recording of a show folder: what the core gives every leg at every
    tick, with the timed command lines of a script given to it."""
    built = subprocess.run(["make", "-C", str(ROOT / "core"), "shared"], capture_output=True, text=True)
    if built.returncode != 0:
        raise AssertionError(f"`make -C core shared` failed:\n{built.stdout}{built.stderr}")
    with tempfile.TemporaryDirectory() as work:
        out, lines = pathlib.Path(work, "record.odrr"), pathlib.Path(work, "script.txt")
        lines.write_text(script)
        done = subprocess.run(
            [sys.executable, "-m", "emulator", str(folder), "--record", str(out), "--seconds", str(seconds), "--script", str(lines)],
            cwd=ROOT, capture_output=True, text=True,
        )
        if done.returncode != 0:
            raise AssertionError(f"the emulator did not record {folder}: {done.stderr}")
        return recfile.read(out)


def leg_bytes(recording, ms):
    """The LED bytes of each leg at the tick of a time, in the order of the legs."""
    tick = next(tick for tick in recording.ticks if tick.ms == ms)
    found, start = [], 0
    for _, _, count in recording.legs:
        found.append(tick.data[start:start + 3 * count])
        start += 3 * count
    return found

"""Helpers shared by the tests that need the board: running the tool, what the board runs,
and what it says on its port."""

import collections
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

from emulator import recfile
from odrig import jsonframes, mapping as mapping_file, odrg, pack
from odrig.generators import dense, dvd_bounce, hello_world
from odrigctl import cli as command_tool
from odrigctl import client, content

from fwtool import Failure, board, build, cli, flasher, limit, paths, storage, wifi

from . import PORT, ROOT

EXAMPLE_SHOW = ROOT / "shows" / "example" / "show.json"
TWO_LEGS = ROOT / "mapping" / "legs-2.json"
TARGET = ROOT / "mapping" / "legs-20.json"
ANIMATIONS = ROOT / "animations"

# The pins of the twenty legs of the target installation, in the order of the legs.
TARGET_PINS = tuple(range(1, 19)) + (21, 47)

# One 60-LED strip is wired, fed from the board's 3.3 V pin: no show that is installed
# may be brighter than this, and the shows the suite packs are dimmer still.
BRIGHTEST = 40
DIM = 32

Result = collections.namedtuple("Result", "status out err")

# What must answer after an image of each kind was flashed.
ANSWERS = {"firmware": "status", "probe": "probe", "stock": "wled"}

# The kind of image the suite leaves on the board.
LEFT_ON_THE_BOARD = "firmware"

# How long the board is given to answer after a restart. The core checks every file at its
# start, which takes most of a minute when storage is full of animations.
START_SECONDS = 90

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
    "play " + "7" * 2050,
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
    done = on_port("flash", "--image", built(kind), "--expect", ANSWERS[kind], "--wait", START_SECONDS)
    if done.status != 0:
        raise AssertionError(f"flashing the {kind} image failed: {done.err}")
    _running = kind
    return done


def install_firmware(*extra):
    """Runs `install-firmware` with the built firmware and remembers that the board then
    runs the firmware."""
    global _running
    _running = None
    built("firmware")
    done = on_port("install-firmware", "--wait", START_SECONDS, *extra)
    if done.status == 0:
        _running = "firmware"
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
    ensure_settings()
    restart()


def ensure_settings():
    """Makes the board's storage hold the name and the password of the settings file and
    the limit of the limit file, applying each only when storage holds something else."""
    image = storage_image()
    for held, command in ((wifi.holds(image, wifi.read()), "set-wifi"), (limit.stored(image) == limit.read(), "set-limit")):
        if not held:
            done = on_port(command, "--wait", START_SECONDS)
            if done.status != 0:
                raise AssertionError(f"{command} with the tracked file failed: {done.err}")


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


def changed_by_commands():
    """Says that commands have changed the show on the board: what this run installed
    last is no longer what the board holds, so the board is asked the next time."""
    global _installed
    _installed = None


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
def emulator(folder, *options):
    """Runs the emulator on a show folder, with more options when some are given, and
    gives the path of its serial port."""
    built = subprocess.run(["make", "-C", str(ROOT / "core"), "shared"], capture_output=True, text=True)
    if built.returncode != 0:
        raise AssertionError(f"`make -C core shared` failed:\n{built.stdout}{built.stderr}")
    with tempfile.TemporaryDirectory() as work:
        link = pathlib.Path(work, "serial")
        process = subprocess.Popen(
            [sys.executable, "-m", "emulator", str(folder), "--port", "0", "--serial-link", str(link), *(str(option) for option in options)],
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


def read_back():
    """The files of the show on the board, read now and remembered as what it holds."""
    global _installed
    _installed = None
    _installed = installed()
    return _installed


def wait_for_the_board():
    """Waits until the image the board runs answers again after a restart."""
    kind = _running
    if kind is not None:
        board.EXPECTED[ANSWERS[kind]](PORT, START_SECONDS)


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


def legs_mapping(length, legs=10, strips_per_leg=3, pins=None, columns=False):
    """The text of a mapping file: legs of some strips each, of `length` LEDs, on the pins
    given or on pins 1, 2, 3 and so on. As rows: leg 1 at the top, every chain starting on
    the right. As columns: leg 1 at the left, every chain starting at the bottom."""
    pins = list(range(1, legs + 1)) if pins is None else list(pins)
    strips = legs * strips_per_leg
    if columns:
        described = [
            {"leg": number + 1, "pin": pins[number], "first_led": "bottom",
             "columns": [number * strips_per_leg + strip + 1 for strip in range(strips_per_leg)]}
            for number in range(legs)
        ]
        return json.dumps({"version": 1, "height": length, "legs": described})
    described = [
        {"leg": number + 1, "pin": pins[number], "first_led": "right",
         "rows": [strips - number * strips_per_leg - strip for strip in range(strips_per_leg)]}
        for number in range(legs)
    ]
    return json.dumps({"version": 1, "width": length, "legs": described})


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
        data = mapping.read_bytes() if isinstance(mapping, pathlib.Path) else mapping.encode()
        (folder / "mapping.json").write_bytes(data)
        items = [{"id": number, "file": name} for number, (name, _) in enumerate(animations, 1)]
        (folder / "show.json").write_text(json.dumps({"version": 1, "brightness": brightness, "items": items, "start": start}))
        for name, content in animations:
            (folder / name).write_bytes(content)
        yield folder


@contextlib.contextmanager
def demo_show(mapping=TARGET, brightness=DIM):
    """A temporary show folder with the demo show made for a mapping, dimmed: Hello world
    and DVD bounce as their generators write them for the mapping's canvas, taking turns
    every 15 seconds from power-on."""
    width, height = canvas_of(mapping)
    animations = {
        "hello.odrg": odrg.encode(jsonframes.Animation(width, height, tuple(hello_world.frames(width, height)))),
        "dvd.odrg": odrg.encode(jsonframes.Animation(width, height, tuple(dvd_bounce.frames(width, height)))),
    }
    show = {
        "version": 1,
        "brightness": brightness,
        "items": [{"id": 1, "file": "hello.odrg"}, {"id": 2, "file": "dvd.odrg"}, {"id": 3, "cycle": [1, 2], "seconds": 15}],
        "start": 3,
    }
    with tempfile.TemporaryDirectory() as work:
        folder = pathlib.Path(work, "show")
        folder.mkdir()
        (folder / "mapping.json").write_bytes(pathlib.Path(mapping).read_bytes())
        (folder / "show.json").write_text(json.dumps(show))
        for name, content in animations.items():
            (folder / name).write_bytes(content)
        yield folder


def canvas_of(mapping):
    """The width and the height of the canvas of a mapping, given as a path or as text."""
    data = mapping.read_bytes() if isinstance(mapping, pathlib.Path) else mapping.encode()
    read = mapping_file.loads(data)
    return read.width, read.height


def one_frame(mapping, ms=1000):
    """An animation of one frame in which every pixel has a colour of its own. The frame
    lasts some milliseconds, and the core opens the file again each time it has ended."""
    width, height = canvas_of(mapping)
    picture = b"".join(own_colour(position) for position in range(width * height))
    return odrg.encode(jsonframes.Animation(width, height, ((ms, picture),)))


def one_frame_show(mapping=TWO_LEGS, brightness=DIM, ms=1000):
    """A show folder whose one item is the one-frame animation, playing from power-on."""
    return show_folder(mapping, [("frame.odrg", one_frame(mapping, ms))], brightness)


def hello_for(mapping):
    """Hello world as its generator writes it for the canvas of a mapping."""
    width, height = canvas_of(mapping)
    return odrg.encode(jsonframes.Animation(width, height, tuple(hello_world.frames(width, height))))


def dense_clip(compressed, seconds=10, width=60, height=60):
    """The dense clip of some seconds for a canvas: a smooth full-colour field, every LED
    lit."""
    return odrg.encode(jsonframes.Animation(width, height, tuple(dense.frames(width, height, seconds))), compressed=compressed)


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


# The item the tests of the content commands upload, and the name its file gets.
NEW_ITEM = 9
HELLO_NAME = "hello-bench.odrg"


def content_session(ask, restart, path):
    """The session of the content commands: an upload, what `list` and `status` say of
    it before and after a restart, its removal, and three refusals. `ask` sends one
    command with the command tool and gives the tool's status and the reply. Returns, for
    each command, its first two words, the status and the reply without `fps` and `free`,
    the two members that differ between a board and an emulator."""
    given = []

    def step(*words):
        status, reply = ask(*(str(word) for word in words))
        given.append((" ".join(str(word) for word in words[:2]), status, {name: value for name, value in reply.items() if name not in ("fps", "free")}))

    step("space")
    step("list")
    step("upload", NEW_ITEM, path)
    step("list")
    step("play", NEW_ITEM)
    step("status")
    step("space")
    restart()
    step("list")
    step("status")
    step("play", NEW_ITEM)
    step("status")
    step("remove", NEW_ITEM)
    step("list")
    step("status")
    step("space")
    step("upload", 3, path)
    step("remove", 1)
    step("remove", NEW_ITEM)
    return given


def measured_upload(session, number, name, data):
    """Uploads a file through a session of the command tool and asks for the status
    through the same session once a second meanwhile. Returns the reply that ended the
    upload; the `fps` of each status while the data was sent, under `data`, and while the
    file was checked, under `check`; and the seconds each of the two took."""
    rates = {"data": [], "check": []}
    times = {"data": 0.0, "check": 0.0}
    state = {"phase": "data", "asked": time.monotonic(), "check_began": None}

    def ask_each_second():
        if time.monotonic() - state["asked"] >= 1.0:
            state["asked"] += 1.0
            rates[state["phase"]].append(json.loads(session.exchange(b"status\n"))["fps"])

    def progress(sent, total, seconds):
        times["data"] = seconds
        ask_each_second()

    def checking():
        state["phase"] = "check"
        state["check_began"] = time.monotonic()

    def sleep(seconds):
        ask_each_second()
        time.sleep(seconds)

    reply = json.loads(content.upload(session, number, name, data, progress, checking, sleep=sleep))
    if state["check_began"] is not None:
        times["check"] = time.monotonic() - state["check_began"]
    return reply, rates, times


class Port:
    """The board's port, opened once and kept open, so that no line is lost between two
    exchanges. Opening it does not reset the board."""

    def __init__(self, port=PORT):
        self.descriptor = client._open(port)
        self.waiting = b""
        time.sleep(client.SETTLE_SECONDS)
        # A newline ends a line that an earlier program left unfinished; its reply is
        # discarded with whatever else waits.
        client._write(self.descriptor, b"\n", 1.0)
        for _ in client._received(self.descriptor, 2 * client.DISCARD_SECONDS):
            pass

    def send(self, data, seconds=5.0):
        """Writes bytes to the port in one piece."""
        client._write(self.descriptor, data, seconds)

    def lines(self, seconds):
        """The lines that arrive within a length of time, each as it is complete."""
        for piece in client._received(self.descriptor, seconds):
            self.waiting += piece
            while b"\n" in self.waiting:
                line, self.waiting = self.waiting.split(b"\n", 1)
                yield line.rstrip(b"\r")

    def line(self, accept, seconds):
        """The first line within a length of time that `accept` takes, or None."""
        for line in self.lines(seconds):
            if accept(line):
                return line
        return None

    def ask(self, data, accept=client.is_reply, seconds=5.0):
        """Sends bytes and gives the first line that `accept` takes, read as JSON."""
        self.send(data)
        line = self.line(accept, seconds)
        if line is None:
            raise AssertionError(f"no answer to {data[:40]!r} within {seconds:g} seconds")
        return json.loads(line)

    def close(self):
        os.close(self.descriptor)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

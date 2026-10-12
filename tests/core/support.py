"""Helpers shared by the tests of the core: where things are and how the test host is run."""

import base64
import bisect
import collections
import contextlib
import functools
import itertools
import json
import pathlib
import random
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from odrig import errors, jsonframes, mapping, odrg, pack, show
from odrig.generators import dense, dvd_bounce, hello_world

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
BUILD = CORE / "build"

# Windows builds the core with the build script, which writes down the toolchain it used.
# Elsewhere `make` builds it.
BY_MAKE = sys.platform != "win32"
TEST_COMMAND = "make -C core test" if BY_MAKE else "python core/build.py test"
TOOLCHAIN = BUILD / "toolchain.json"


def toolchain():
    """The toolchain the core is built with: its kind, `gnu` or `msvc`, and its programs
    `cxx`, `cc`, `ar` and `nm`. Where `make` builds, they are the ones the makefile takes
    from the path."""
    if not BY_MAKE and TOOLCHAIN.is_file():
        return json.loads(TOOLCHAIN.read_text(encoding="utf-8"))
    return {"kind": "gnu", "cxx": "c++", "cc": "cc", "ar": "ar", "nm": "nm"}


def gnu(program):
    """One program of a GNU-style toolchain, by its role. A test that needs one is skipped
    where the core is built with Microsoft's compiler, which has no such program."""
    used = toolchain()
    if used["kind"] != "gnu":
        raise unittest.SkipTest(f"the core is built with Microsoft's compiler, which has no program that takes the options of {program}")
    return used[program]


LIBRARY = BUILD / ("odrig_core.lib" if toolchain()["kind"] == "msvc" else "libodrig_core.a")
HOST = BUILD / ("odrig_host.exe" if sys.platform == "win32" else "odrig_host")

Result = collections.namedtuple("Result", "status out err")


def built(path):
    """The path of a file that the test command builds, or a failure that says so."""
    if not path.exists():
        raise AssertionError(f"{path} is not built; run the suite with `{TEST_COMMAND}`")
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


def batch(pieces):
    """The input of a `--batch` invocation: each piece after its length as four bytes."""
    return b"".join(len(piece).to_bytes(4, "little") + piece for piece in pieces)


def inflate_each(streams):
    """What the core's DEFLATE decoder makes of each stream.

    One result for each stream: `("data", output, left)`, where `left` is the number of
    bytes of input after the end of the stream, or `("rejected", reason)`.
    """
    lines = iter(host_lines("inflate", "--batch", stdin=batch(streams)))
    results = []
    for line in lines:
        word, _, rest = line.partition(" ")
        if word == "data":
            left_word, _, left = next(lines).partition(" ")
            if left_word != "left":
                raise AssertionError(f"odrig_host inflate printed {left_word!r} after data")
            results.append(("data", bytes.fromhex(rest), int(left)))
        elif word == "rejected":
            results.append(("rejected", rest))
        else:
            raise AssertionError(f"odrig_host inflate printed {line[:60]!r}")
    if len(results) != len(streams):
        raise AssertionError(f"odrig_host inflate gave {len(results)} results for {len(streams)} streams")
    return results


Decoded = collections.namedtuple("Decoded", "header records reason")
Decoded.__doc__ = """What the core's ODRG decoder makes of a file.

`header` is `(W, H, C, F, compressed)`, or `None` when the header is refused. `records` holds
`(duration, picture)` for each frame record decoded, the picture as three bytes for each
pixel. `reason` is `None` for a file read to its end, or the reason it is refused for.
"""


def _decoded(lines):
    header = None
    records = []
    for line in lines:
        word, _, rest = line.partition(" ")
        if word == "header":
            width, height, colours, frames, compressed = (int(number) for number in rest.split())
            header = (width, height, colours, frames, bool(compressed))
        elif word == "frame":
            duration, _, picture = rest.partition(" ")
            records.append((int(duration), bytes.fromhex(picture)))
        elif word == "end":
            return Decoded(header, tuple(records), None)
        elif word == "rejected":
            return Decoded(header, tuple(records), rest)
        else:
            break
    raise AssertionError("odrig_host decode printed no ending")


def decode_file(path):
    """What the core's ODRG decoder makes of a file on disk."""
    return _decoded(iter(host_lines("decode", path)))


def decode_each(files):
    """What the core's ODRG decoder makes of each of these files, given as bytes."""
    lines = iter(host_lines("decode", "--batch", stdin=batch(files)))
    results = [_decoded(lines) for _ in files]
    if next(lines, None) is not None:
        raise AssertionError(f"odrig_host decode printed more than {len(files)} results")
    return results


# Row-leg mappings beyond the tracked one: a leg that starts on the left, legs of two and
# of four rows, legs listed in another order than their numbers and their rows, one LED, and
# ten legs of three rows of 60 from the top row down, leg N on pin N.
MADE_UP_MAPPINGS = {
    "left-start": {"version": 1, "width": 7, "legs": [{"leg": 1, "pin": 4, "first_led": "left", "rows": [1, 2, 3]}]},
    "two-and-four-rows": {
        "version": 1,
        "width": 5,
        "legs": [
            {"leg": 3, "pin": 9, "first_led": "right", "rows": [6, 5]},
            {"leg": 1, "pin": 0, "first_led": "left", "rows": [4, 3, 2, 1]},
        ],
    },
    "another-order": {
        "version": 1,
        "width": 4,
        "legs": [
            {"leg": 7, "pin": 12, "first_led": "left", "rows": [2, 4]},
            {"leg": 2, "pin": 3, "first_led": "right", "rows": [1, 5, 3]},
        ],
    },
    "one-led": {"version": 1, "width": 1, "legs": [{"leg": 255, "pin": 255, "first_led": "right", "rows": [1]}]},
    "ten-row-legs": {
        "version": 1,
        "width": 60,
        "legs": [{"leg": n, "pin": n, "first_led": "right", "rows": [33 - 3 * n, 32 - 3 * n, 31 - 3 * n]} for n in range(1, 11)],
    },
}


# Column-leg mappings: a leg that starts at the top, legs of two and of four columns of 5
# LEDs, columns that are not neighbours and not in order, and one LED.
MADE_UP_COLUMN_MAPPINGS = {
    "top-start": {"version": 1, "height": 7, "legs": [{"leg": 1, "pin": 4, "first_led": "top", "columns": [1, 2, 3]}]},
    "two-and-four-columns": {
        "version": 1,
        "height": 5,
        "legs": [
            {"leg": 3, "pin": 9, "first_led": "bottom", "columns": [1, 2]},
            {"leg": 1, "pin": 0, "first_led": "top", "columns": [6, 5, 4, 3]},
        ],
    },
    "columns-apart": {
        "version": 1,
        "height": 4,
        "legs": [
            {"leg": 7, "pin": 12, "first_led": "bottom", "columns": [2, 4]},
            {"leg": 2, "pin": 3, "first_led": "top", "columns": [1, 5, 3]},
        ],
    },
    "one-led-column": {"version": 1, "height": 1, "legs": [{"leg": 255, "pin": 255, "first_led": "top", "columns": [1]}]},
}


def column_mapping_texts():
    """The made-up column-leg mappings, by name."""
    return {name: json.dumps(listed) for name, listed in MADE_UP_COLUMN_MAPPINGS.items()}


def mapping_texts():
    """The mappings the suites of the core and of the emulator play on, by name: the tracked
    files and the made-up ones of both kinds."""
    texts = {path.stem: path.read_text(encoding="utf-8") for path in sorted((ROOT / "mapping").glob("*.json"))}
    texts.update({name: json.dumps(listed) for name, listed in MADE_UP_MAPPINGS.items()})
    texts.update(column_mapping_texts())
    return texts


@contextlib.contextmanager
def installed(files):
    """A temporary folder that holds these files, given as a mapping from name to content."""
    with tempfile.TemporaryDirectory() as folder:
        for name, content in files.items():
            data = content if isinstance(content, bytes) else content.encode("utf-8")
            pathlib.Path(folder, name).write_bytes(data)
        yield folder


Run = collections.namedtuple("Run", "status core memory error legs logs opened stored lines")
Run.__doc__ = """One run of `odrig_host session`.

`core` is "ok" or "null". `memory` is `(bytes, blocks)`: what the core asked the host for
while it started. `error` is the reason the show is invalid after startup, or `None`.
`legs` holds `(leg, pin, LED count)` for each leg. `logs` are the diagnostic texts the core
gave the host while it started. `opened` holds `(name, result)` for each file the core asked
the host to open while it started, when the session has the option `--trace-files`.
`stored` holds the storage calls the core made while it started, each as the text after
`store `, when the session has the option `--trace-store`. `lines` is everything printed
after startup.
"""

# The storage of the board and the block of its file system, which the test host and the
# emulator report space by.
BOARD_STORAGE = 10354688
STORAGE_BLOCK = 4096


def free_space(files, total=BOARD_STORAGE):
    """The free bytes a host reports for these files: the total less the size of each file
    rounded up to a whole block, and not below 0."""
    used = sum(-(-len(content if isinstance(content, bytes) else content.encode("utf-8")) // STORAGE_BLOCK) * STORAGE_BLOCK for content in files.values())
    return max(0, total - used)


def _script_bytes(script):
    return "".join(f"{line}\n" for line in script).encode("ascii")


def session(folder, script=(), options=(), status=0):
    """Starts the core on a folder with the test host and gives it the lines of a script."""
    result = host("session", folder, *options, stdin=_script_bytes(script))
    if result.status != status or result.err:
        raise AssertionError(f"odrig_host session: status {result.status}, not {status}\n{result.out[-400:]}\n{result.err}")
    return _run(result.status, result.out.splitlines())


def _run(status, printed):
    """The parts of what one session printed."""
    core = None
    memory = None
    error = None
    legs = []
    logs = []
    opened = []
    stored = []
    position = 0
    for position, line in enumerate(printed):
        word, _, rest = line.partition(" ")
        if word == "log" and core is None:
            logs.append(rest)
        elif word == "open" and core is None:
            name, _, answer = rest.rpartition(" ")
            opened.append((name, int(answer)))
        elif word == "store" and core is None:
            stored.append(rest)
        elif word == "core":
            core = rest
        elif word == "memory":
            memory = tuple(int(number) for number in rest.split())
        elif word == "error":
            error = None if rest == "none" else rest
        elif word == "leg":
            legs.append(tuple(int(number) for number in rest.split()))
        else:
            break
    else:
        position = len(printed)
    lines = printed[position + 1:] if position < len(printed) and printed[position] == "ready" else printed[position:]
    return Run(status, core, memory, error, tuple(legs), tuple(logs), tuple(opened), tuple(stored), lines)


def start(files, script=(), options=(), status=0):
    """Installs the files in a temporary folder and runs a session on it."""
    with installed(files) as folder:
        return session(folder, script, options, status)


def folder_files(folder):
    """The files of a folder: the content of each by its name."""
    return {path.name: path.read_bytes() for path in sorted(pathlib.Path(folder).iterdir()) if path.is_file()}


def start_and_keep(files, script=(), options=(), status=0):
    """Installs the files in a temporary folder and runs a session on it. Returns the run
    and the files the folder holds afterwards."""
    with installed(files) as folder:
        run = session(folder, script, options, status)
        return run, folder_files(folder)


def start_each(file_sets, script=(), options=()):
    """A session for each set of files, all in one run of the test host, which holds the
    files in memory. The results are in the given order."""
    pieces = []
    for files in file_sets:
        pieces.append(str(len(files)).encode("ascii"))
        for name, content in files.items():
            pieces.append(name.encode("utf-8"))
            pieces.append(content if isinstance(content, bytes) else content.encode("utf-8"))
        pieces.append(_script_bytes(script))
    printed = iter(host_lines("session", "--batch", *options, stdin=batch(pieces)))
    runs = []
    for _ in file_sets:
        lines = []
        for line in printed:
            if line == "end":
                break
            lines.append(line)
        else:
            raise AssertionError(f"odrig_host session --batch ended after {len(runs)} of {len(file_sets)} sessions")
        runs.append(_run(0, lines))
    return runs


@functools.lru_cache(maxsize=None)
def _example_show():
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder, "show")
        pack.pack(ROOT / "shows" / "example" / "show.json", ROOT / "mapping" / "legs-2.json", ROOT / "animations", out)
        return tuple((path.name, path.read_bytes()) for path in sorted(out.iterdir()))


def example_show():
    """The installed files of the example show, packed by the converter on the two-leg mapping."""
    return dict(_example_show())


@functools.lru_cache(maxsize=None)
def _demo_show():
    target = ROOT / "mapping" / "legs-20.json"
    canvas = mapping.read(target)
    files = [("mapping.json", target.read_bytes()), ("show.json", (ROOT / "shows" / "demo-20" / "show.json").read_bytes())]
    for name, generator in (("hello.odrg", hello_world), ("dvd.odrg", dvd_bounce)):
        frames = tuple(generator.frames(canvas.width, canvas.height))
        files.append((name, odrg.encode(jsonframes.Animation(canvas.width, canvas.height, frames))))
    return tuple(files)


def demo_show():
    """The installed files of the demo show: the target file, the show file, and the two
    animations as the generators make them for the canvas of the target file."""
    return dict(_demo_show())


def show_text(items, brightness=128, start=None):
    """A show file with these items, each written as docs/show.md has it."""
    show = {"version": 1, "brightness": brightness, "items": list(items)}
    if start is not None:
        show["start"] = start
    return json.dumps(show)


def one_leg_mapping(width, height):
    """A mapping file for a canvas of this size: one leg that starts on the right at the top."""
    leg = {"leg": 1, "pin": 1, "first_led": "right", "rows": list(range(height, 0, -1))}
    return json.dumps({"version": 1, "width": width, "legs": [leg]})


def seeded_animation(seed, width, height, durations, colours=5):
    """An animation with one seeded picture for each duration, in at most `colours` colours."""
    rng = random.Random(f"{seed} {width} {height} {colours}")
    palette = [rng.randbytes(3) for _ in range(colours)]
    frames = tuple((ms, b"".join(rng.choice(palette) for _ in range(width * height))) for ms in durations)
    return jsonframes.Animation(width, height, frames)


def clip(seed, width, height, durations=(20, 20, 20), compressed=True):
    """The bytes of an ODRG file of a seeded animation."""
    return odrg.encode(seeded_animation(seed, width, height, durations), compressed=compressed)


@functools.lru_cache(maxsize=None)
def dense_clip(width, height, seconds, compressed=True):
    """The bytes of an ODRG file of the converter's dense test clip."""
    animation = jsonframes.Animation(width, height, tuple(dense.frames(width, height, seconds)))
    return odrg.encode(animation, compressed=compressed)


def upload_lines(number, name, data, piece=1500):
    """The command lines that open an upload and send a file in pieces: `upload begin` and
    one `upload data` for each piece."""
    lines = [f"upload begin {number} {name} {len(data)}"]
    for offset in range(0, len(data), piece):
        lines.append(f"upload data {offset} {base64.urlsafe_b64encode(data[offset:offset + piece]).rstrip(b'=').decode('ascii')}")
    return lines


def upload_end(data):
    """The command line that closes the upload of a file."""
    return f"upload end {zlib.crc32(data):08x}"


def show_refusal(rejection):
    """The reason text the core holds for a show file the converter's reader refuses."""
    if rejection.reason == "show-malformed":
        return "show-malformed"
    about = {
        "duplicate-id": r"two items have the id (-?[0-9]+)",
        "undefined-id": r"names the id (-?[0-9]+), which no item has",
        "nested-cycle": r"the cycle of item ([0-9]+) names item",
    }[rejection.reason]
    number = int(re.search(about, rejection.detail).group(1))
    return f"{rejection.reason} {max(-4294967295, min(4294967295, number))}"


def led_pixels(canvas, leg):
    """For LED 1, 2, ... of a leg of a mapping, the place in pixel order of the canvas pixel
    it shows.

    This is the rule of docs/mapping.md, "Where each LED is", written out once more for a
    row leg and for a column leg.
    """
    width = canvas.width
    height = canvas.height
    places = []
    if canvas.kind == mapping.ROWS:
        for n in range(1, width * len(leg.strips) + 1):
            r = (n - 1) // width
            i = (n - 1) % width
            y = leg.strips[r]
            on_the_first_side = r % 2 == 0
            starts_right = (leg.first_led == "right") == on_the_first_side
            x = width - i if starts_right else 1 + i
            places.append((y - 1) * width + (x - 1))
    else:
        for n in range(1, height * len(leg.strips) + 1):
            s = (n - 1) // height
            i = (n - 1) % height
            x = leg.strips[s]
            at_the_first_end = s % 2 == 0
            starts_at_the_bottom = (leg.first_led == "bottom") == at_the_first_end
            y = 1 + i if starts_at_the_bottom else height - i
            places.append((y - 1) * width + (x - 1))
    return places


class _Invalid(Exception):
    """The installed file set is refused, with this reason text."""


class _Clip:
    """The frames of one `.odrg` file, as the reference decoder gives them."""

    def __init__(self, records):
        self.pictures = [picture for _, picture in records]
        self.ends = list(itertools.accumulate(duration for duration, _ in records))
        self.total = self.ends[-1]

    def picture_at(self, elapsed):
        """The frame whose time span contains this time, with the animation looping."""
        return self.pictures[bisect.bisect_right(self.ends, elapsed % self.total)]


class ReferencePlayer:
    """What the core does with an installed file set, stated a second time.

    It is written from the requirements, in Python, on top of the converter's readers and
    its reference decoder, and applies the mapping rule itself. `answer` takes an input
    line of `odrig_host session` and gives the lines the test host prints for it, so a test
    compares two texts. `poll` gives the same refresh as values.
    """

    GRID = 20
    PARTS = ("upload.part", "show.part")
    PENDING = "pending.txt"
    CHUNK = 1500
    QUIET = 60000
    RESERVE = 16384
    BASE64 = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")

    def __init__(self, files, storage=BOARD_STORAGE, changeable=True):
        """`files` maps the name of each installed file to its content. `storage` is the
        total space the host reports, or None for a host that cannot tell its space.
        `changeable` says whether the host's storage can be changed."""
        self.storage = storage
        self.changeable = changeable
        self.error = None       # the reason the show is invalid, or None
        self.start = None       # the id of the `start` item of the show
        self.show_brightness = 0    # the brightness of the show file
        self.canvas = None      # the width and the height of the canvas
        self.capacity = 0       # the number of items there is room for
        self.upload = None      # the open upload
        self.had_refresh = False
        self.last_grid = None   # the grid time of the latest refresh
        # For a file whose body is refused: the frame records that decode before the one
        # that is refused, by the CRC-32 of the file. The check ends two steps later.
        # Without an entry the check is taken to end after every record the header names.
        self.sound_records = {}
        self.legs = []          # (leg number, pin, the pixel place of each LED) for each leg
        self.items = {}         # the items of the show by id
        self.clips = {}         # the frames of each file by name
        self.on = True
        self.brightness = 0
        self.playing = None     # the id of the item being played
        self.zero = None        # the time zero of that item, once a refresh has set it
        self.shown = None       # the id of the animation item the latest refresh chose
        self.t0 = None          # the power-on moment
        self.latest = None
        self.next_due = None
        self.refreshes_in = collections.Counter()   # the refreshes of each second after power-on
        self.unfinished = b""   # the bytes of a transport since the last newline
        content = {name: data if isinstance(data, bytes) else data.encode("utf-8") for name, data in files.items()}
        self.files = content    # the files of the folder by name
        if changeable:
            for name in self.PARTS:
                content.pop(name, None)
        try:
            start = self._check(content)
        except _Invalid as invalid:
            self.error = str(invalid)
        else:
            if start is not None:
                self._play(start)

    def _check(self, files):
        """Reads the installed file set in the order of the checks. Returns the `start` id."""
        if "mapping.json" not in files:
            raise _Invalid("mapping-missing")
        try:
            canvas = mapping.loads(files["mapping.json"])
        except errors.Rejection:
            raise _Invalid("mapping-malformed") from None
        self.legs = [(leg.leg, leg.pin, led_pixels(canvas, leg)) for leg in canvas.legs]
        self.canvas = (canvas.width, canvas.height)

        if "show.json" not in files:
            raise _Invalid("show-missing")
        try:
            listed = show.loads(files["show.json"])
        except errors.Rejection as rejection:
            raise _Invalid(show_refusal(rejection)) from None
        self.brightness = self.show_brightness = listed.brightness
        self.items = {item.id: item for item in listed.items}
        self.capacity = max(128, min(len(self.items) + 32, 65535), len(self.items))
        self.start = listed.start
        if self.changeable and self.PENDING in files:
            # What an interrupted change left: a file named there that no item names.
            named = show.files(listed)
            for line in files.pop(self.PENDING)[:512].split(b"\n")[:-1]:
                name = line.decode("latin-1")
                if show.FILE_NAME.fullmatch(name) and name.endswith(show.ENDING) and name not in named:
                    files.pop(name, None)

        for name in show.files(listed):
            if name not in files:
                raise _Invalid(f"file-missing {name}")
            data = files[name]
            # The header is judged first, then the size against the mapping, then the body.
            # The header alone, when it is sound, is refused as a file cut after it.
            try:
                odrg.decode(data[:16])
            except errors.Rejection as rejection:
                if len(data) < 16 or rejection.reason != "truncated":
                    raise _Invalid(f"file-malformed {name} {rejection.reason}") from None
            if struct.unpack_from("<HH", data, 6) != (canvas.width, canvas.height):
                raise _Invalid(f"size-mismatch {name}")
            try:
                self.clips[name] = _Clip(odrg.decode(data).records)
            except errors.Rejection as rejection:
                raise _Invalid(f"file-malformed {name} {rejection.reason}") from None
        return listed.start

    def _play(self, number):
        self.playing = number
        self.zero = None
        item = self.items[number]
        self.shown = number if item.cycle is None else item.cycle[0]

    def _touch(self, now):
        """Takes the timestamp of a call and gives the time the call happens at."""
        if self.t0 is None:
            self.t0 = self.latest = self.next_due = now
        self.latest = max(self.latest, now)
        # An upload on which nothing has moved for a minute is discarded.
        if self.upload is not None and self.latest - self.upload["progress"] >= self.QUIET:
            self._discard()
        return self.latest

    def _picture(self, now, grid):
        """The picture on the canvas at a refresh, or None when every LED is dark."""
        if self.error is not None or self.playing is None:
            return None
        if self.zero is None:
            self.zero = grid
        item = self.items[self.playing]
        elapsed = now - self.zero
        if item.cycle is not None:
            # Turn t shows the animation at place t mod n, with its time counted from the
            # start of the turn.
            turn, elapsed = divmod(elapsed, 1000 * item.seconds)
            item = self.items[item.cycle[turn % len(item.cycle)]]
        self.shown = item.id
        picture = self.clips[item.file].picture_at(elapsed)
        return picture if self.on else None

    def poll(self, now):
        """A request for a refresh at a timestamp.

        Returns `(leg number, LED data)` for each leg, or None when no refresh is due.
        """
        now = self._touch(now)
        if not self.legs or now < self.next_due:
            return None
        grid = self.t0 + (now - self.t0) // self.GRID * self.GRID
        self.next_due = grid + self.GRID
        self.refreshes_in[(now - self.t0) // 1000] += 1
        in_step = self.had_refresh and grid == self.last_grid + self.GRID
        self.had_refresh, self.last_grid = True, grid
        picture = self._picture(now, grid)
        # The check of an uploaded file takes one step after a refresh that followed the
        # one before it without a gap.
        if in_step and self.upload is not None and self.upload["state"] == "checking":
            self.upload["progress"] = now
            self.upload["steps"] -= 1
            if self.upload["steps"] == 0:
                self.upload["state"] = "checked"
        if picture is None:
            return [(leg, bytes(3 * len(places))) for leg, _, places in self.legs]
        sent = picture.translate(bytes((value * self.brightness + 127) // 255 for value in range(256)))
        return [(leg, b"".join(sent[3 * place:3 * place + 3] for place in places)) for leg, _, places in self.legs]

    LINE_MAX = 2048
    COMMANDS = {b"play": (1,), b"on": (0,), b"off": (0,), b"brightness": (1,), b"status": (0,), b"space": (0,), b"list": (0, 1), b"remove": (1,), b"upload": range(0, 2048)}
    RANGES = {b"play": (1, 65535), b"brightness": (0, 255), b"list": (0, 65535), b"remove": (1, 65535)}
    REPLY_MAX = 1024

    def command(self, now, line):
        """One command line, given as bytes: carries it out and returns its reply."""
        now = self._touch(now)
        if line.endswith(b"\n"):
            line = line[:-1]
        if line.endswith(b"\r"):
            line = line[:-1]
        code = self._obey(line)
        if isinstance(code, bytes):
            return code
        if code is not None:
            return b'{"ok":false,"error":"' + code.encode("ascii") + b'"}\n'
        if line == b"status":
            return self._status(now)
        if line == b"space":
            return self._space()
        if line.split(b" ")[0] == b"list":
            return self._list(int(line[5:]) if b" " in line else 0)
        return b'{"ok":true}\n'

    def _obey(self, line):
        """Carries out a command line. Returns the error code of a line that is no valid
        command, the first that applies, and changes nothing then."""
        if len(line) > self.LINE_MAX:
            return "line-too-long"
        name, *arguments = line.split(b" ")
        if name not in self.COMMANDS:
            return "unknown-command"
        if len(arguments) not in self.COMMANDS[name]:
            return "bad-argument"
        if name == b"upload":
            return self._upload(arguments)
        value = None
        if arguments:
            if not arguments[0] or arguments[0].strip(b"0123456789"):
                return "bad-argument"
            value = int(arguments[0])
            low, high = self.RANGES[name]
            if not low <= value <= high:
                return "bad-argument"
        if name == b"play":
            if self.error is not None:
                return "show-invalid"
            if value not in self.items:
                return "unknown-id"
            self._play(value)
        elif name == b"brightness":
            self.brightness = value
        elif name == b"space":
            if self.storage is None:
                return "storage-error"
        elif name == b"list":
            if self.error is not None:
                return "show-invalid"
        elif name == b"remove":
            if self.error is not None:
                return "show-invalid"
            if self.upload is not None:
                return "busy"
            if value not in self.items:
                return "unknown-id"
            if any(value in (other.cycle or ()) for other in self.items.values()):
                return "in-use"
            if not self.changeable:
                return "storage-error"
            self._remove(value)
        elif name != b"status":
            self.on = name == b"on"
        return None

    @staticmethod
    def _number(text, low, high):
        """The value of an argument written in decimal digits, or None when it is no such
        text or is outside its range."""
        if not text or text.strip(b"0123456789"):
            return None
        value = int(text)
        return value if low <= value <= high else None

    def _decoded(self, text):
        """The bytes a text stands for as base64 without padding, or None when it is not
        that, or stands for no byte or for more than a piece may have."""
        if not text or len(text) % 4 == 1 or not self.BASE64.issuperset(text):
            return None
        data = base64.urlsafe_b64decode(text + b"=" * (-len(text) % 4))
        if base64.urlsafe_b64encode(data).rstrip(b"=") != text or not 1 <= len(data) <= self.CHUNK:
            return None
        return data

    def _discard(self):
        self.files.pop("upload.part", None)
        self.upload = None

    def _judge(self, data):
        """What the check of an uploaded file finds: the steps it takes, and the reason
        the file is refused for, or None with the frames of the file."""
        if len(data) < 16:
            return 1, "truncated", None
        try:
            odrg.decode(data[:16])
        except errors.Rejection as rejection:
            if rejection.reason != "truncated":
                return 1, rejection.reason, None
        if struct.unpack_from("<HH", data, 6) != self.canvas:
            return 1, "size-mismatch", None
        try:
            records = odrg.decode(data).records
        except errors.Rejection as rejection:
            sound = self.sound_records.get(zlib.crc32(data), struct.unpack_from("<I", data, 12)[0])
            return sound + 2, rejection.reason, None
        return len(records) + 2, None, _Clip(records)

    def _upload(self, arguments):
        """The four `upload` commands. Returns an error code, a reply, or None."""
        verb = arguments[0] if arguments else b""
        if verb == b"begin":
            number = self._number(arguments[1], 1, 65535) if len(arguments) == 4 else None
            size = self._number(arguments[3], 1, 4294967295) if len(arguments) == 4 else None
            name = arguments[2].decode("latin-1") if len(arguments) == 4 else ""
            if number is None or size is None or not show.FILE_NAME.fullmatch(name) or not name.endswith(show.ENDING):
                return "bad-argument"
            if self.error is not None:
                return "show-invalid"
            if self.upload is not None:
                return "busy"
            item = self.items.get(number)
            if item is not None and item.cycle is not None:
                return "in-use"
            if any(other.file == name for other in self.items.values() if other.id != number):
                return "in-use"
            if item is None and len(self.items) >= self.capacity:
                return "no-space"
            if self.storage is not None and size + size // 256 + self.RESERVE > free_space(self.files, self.storage):
                return "no-space"
            if self.storage is None or not self.changeable:
                return "storage-error"
            self.upload = {"id": number, "name": name, "size": size, "data": b"", "state": "receiving", "progress": self.latest}
            self.files["upload.part"] = b""
            return b'{"ok":true,"chunk":1500}\n'
        if verb == b"data":
            offset = self._number(arguments[1], 0, 4294967295) if len(arguments) == 3 else None
            data = self._decoded(arguments[2]) if len(arguments) == 3 else None
            if offset is None or data is None:
                return "bad-argument"
            if self.error is not None:
                return "show-invalid"
            if self.upload is None:
                return "no-upload"
            upload = self.upload
            if offset != len(upload["data"]) or len(data) > upload["size"] - len(upload["data"]):
                return "bad-offset"
            upload["data"] += data
            upload["progress"] = self.latest
            self.files["upload.part"] = upload["data"]
            if len(upload["data"]) == upload["size"]:
                upload["state"] = "checking"
                upload["steps"], upload["reason"], upload["clip"] = self._judge(upload["data"])
            return b'{"ok":true,"received":%d}\n' % len(upload["data"])
        if verb == b"end":
            if len(arguments) != 2 or not re.fullmatch(rb"[0-9a-f]{8}", arguments[1]):
                return "bad-argument"
            if self.error is not None:
                return "show-invalid"
            if self.upload is None:
                return "no-upload"
            upload = self.upload
            if len(upload["data"]) < upload["size"]:
                return "incomplete"
            if zlib.crc32(upload["data"]) != int(arguments[1], 16):
                self._discard()
                return "bad-checksum"
            if upload["state"] == "checking":
                return "busy"
            if upload["reason"] is not None:
                self._discard()
                return b'{"ok":false,"error":"bad-file","reason":"%s"}\n' % upload["reason"].encode("ascii")
            self._install(upload)
            return None
        if verb == b"cancel" and len(arguments) == 1:
            if self.error is not None:
                return "show-invalid"
            if self.upload is None:
                return "no-upload"
            self._discard()
            return None
        return "bad-argument"

    def _install(self, upload):
        """Puts an upload whose check has passed in place: the file, and its item as a new
        last item or with the animation of the item that has its id."""
        number, name = upload["id"], upload["name"]
        self._discard()
        old = self.items.get(number)
        self.files[name] = upload["data"]
        self.clips[name] = upload["clip"]
        self.items[number] = show.Item(number, name, None, None)
        if old is not None:
            if old.file != name and all(other.file != old.file for other in self.items.values()):
                self.files.pop(old.file, None)
                self.clips.pop(old.file, None)
            played = self.items.get(self.playing)
            if played is not None and (played.id == number or number in (played.cycle or ())):
                self._play(self.playing)
        if old is None or old.file != name:
            self.files["show.json"] = self.show_text()

    def _listed(self, item, with_entries=True):
        """One item as `list` writes it."""
        if item.cycle is None:
            return json.dumps({"id": item.id, "file": item.file, "bytes": len(self.files[item.file])}, separators=(",", ":"))
        return json.dumps({"id": item.id, "cycle": list(item.cycle) if with_entries else [], "seconds": item.seconds}, separators=(",", ":"))

    def _list(self, first):
        """The reply to `list`: every item from a position on that fits into the reply."""
        items = list(self.items.values())
        head = '{"ok":true,"items":['

        def tail(position):
            return '],"next":' + (str(position) if position < len(items) else "null") + "}\n"

        text = head
        position = first
        while position < len(items):
            entry = self._listed(items[position])
            if items[position].cycle is not None and len(head) + len(entry) + len(tail(position + 1)) > self.REPLY_MAX:
                entry = self._listed(items[position], with_entries=False)
            comma = "," if position != first else ""
            if len(text) + len(comma) + len(entry) + len(tail(position + 1)) > self.REPLY_MAX:
                break
            text += comma + entry
            position += 1
        return (text + tail(position)).encode("ascii")

    def show_text(self):
        """The show file as the core writes it."""
        items = []
        for item in self.items.values():
            if item.cycle is None:
                items.append({"id": item.id, "file": item.file})
            else:
                items.append({"id": item.id, "cycle": list(item.cycle), "seconds": item.seconds})
        written = {"version": 1, "brightness": self.show_brightness, "items": items}
        if self.start is not None:
            written["start"] = self.start
        return json.dumps(written, separators=(",", ":")).encode("ascii") + b"\n"

    def _remove(self, number):
        """Takes an item out of the show, and its file out of the folder when no other
        item names it."""
        item = self.items.pop(number)
        if self.start == number:
            self.start = None
        if self.playing == number:
            self.playing = self.shown = self.zero = None
        if item.file is not None and all(other.file != item.file for other in self.items.values()):
            self.files.pop(item.file, None)
            self.clips.pop(item.file, None)
        self.files["show.json"] = self.show_text()

    def _space(self):
        animations = 0 if self.error is not None else sum(1 for item in self.items.values() if item.cycle is None)
        state = {"ok": True, "free": free_space(self.files, self.storage), "total": self.storage, "animations": animations}
        return json.dumps(state, separators=(",", ":")).encode("ascii") + b"\n"

    def _status(self, now):
        second = (now - self.t0) // 1000
        state = {
            "ok": True,
            "on": self.on,
            "brightness": self.brightness,
            "playing": self.playing,
            "animation": self.shown if self.playing is not None else None,
            "fps": self.refreshes_in[second - 1] if second >= 1 else 0,
            "error": self.error,
        }
        return json.dumps(state, separators=(",", ":")).encode("ascii") + b"\n"

    def feed(self, now, data):
        """Bytes of a transport. Returns `(line, reply)` for every line they complete: the
        line as it is handed to the host, and the reply."""
        self._touch(now)
        answered = []
        for value in data:
            if value != 0x0A:
                self.unfinished += bytes([value])
                continue
            line, self.unfinished = self.unfinished, b""
            reply = self.command(now, line)
            if line.endswith(b"\r"):
                line = line[:-1]
            answered.append((line[:self.LINE_MAX], reply))
        return answered

    def answer(self, line):
        """The lines the test host prints for one input line of a session."""
        word, _, rest = line.partition(" ")
        if word == "poll":
            refresh = self.poll(int(rest))
            if refresh is None:
                return [f"idle {rest}"]
            return [f"refresh {rest}"] + [f"data {leg} {rgb.hex()}" for leg, rgb in refresh]
        if line == "error":
            return [f"error {self.error or 'none'}"]
        if word in ("line", "linehex", "bytes"):
            time, _, given = rest.partition(" ")
            given = given.encode("ascii") if word == "line" else bytes.fromhex(given)
            if word == "bytes":
                return [printed for fed, reply in self.feed(int(time), given) for printed in (f"fed {fed.hex()}", f"reply {reply.decode('ascii')[:-1]}")]
            return [f"reply {self.command(int(time), given).decode('ascii')[:-1]}"]
        raise ValueError(f"not an input line of a session: {line!r}")

    def run(self, script):
        """The lines the test host prints for the lines of a script."""
        return [printed for line in script for printed in self.answer(line)]


def line(time, text):
    """The input line of a session that gives the core a command line as text."""
    return f"line {time} {text}"


def linehex(time, data):
    """The input line of a session that gives the core a command line as these bytes."""
    return f"linehex {time} {data.hex()}"


def fed(time, data):
    """The input line of a session that feeds the core these bytes of a transport."""
    return f"bytes {time} {data.hex()}"

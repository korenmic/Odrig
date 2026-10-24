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

from odrig import errors, jsonframes, mapping, odrg, odrgx, show
from odrig.generators import dense, dvd_bounce, hello_world

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONVERTER = ROOT / "converter" / "odrig.js"


def pack_with_the_converter(show_file, mapping_file, sources, out, compressed=True):
    """Packs a show into the folder `out` with the converter, `node converter/odrig.js pack`.
    A refusal is an error with the converter's error line."""
    argv = ["node", str(CONVERTER), "pack", "--show", str(show_file), "--mapping", str(mapping_file), "--sources", str(sources), "--out", str(out)]
    if not compressed:
        argv.append("--uncompressed")
    done = subprocess.run(argv, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"the converter did not pack {show_file}: {done.stderr.strip()}")
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


Decoded = collections.namedtuple("Decoded", "header records reason container", defaults=(None,))
Decoded.__doc__ = """What the core's reader makes of an ODRG file or an ODRGX container of frames.

`header` is `(W, H, C, F, compressed)` of the frames, or `None` when a header is refused.
`records` holds `(duration, picture)` for each frame record decoded, the picture as three
bytes for each pixel. `reason` is `None` for a file read to its end, or the reason it is
refused for. `container` is `(type, loop, payload)` of a container whose header was read,
and `None` for an ODRG file.
"""


def _decoded(lines):
    header = None
    container = None
    records = []
    for line in lines:
        word, _, rest = line.partition(" ")
        if word == "container":
            container = tuple(int(number) for number in rest.split())
        elif word == "header":
            width, height, colours, frames, compressed = (int(number) for number in rest.split())
            header = (width, height, colours, frames, bool(compressed))
        elif word == "frame":
            duration, _, picture = rest.partition(" ")
            records.append((int(duration), bytes.fromhex(picture)))
        elif word == "end":
            return Decoded(header, tuple(records), None, container)
        elif word == "rejected":
            return Decoded(header, tuple(records), rest, container)
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


_FOUND = {}


def found_in(data):
    """What the core's ODRG decoder makes of one file outside a session, kept for the
    files that were asked for before. The reference player takes from it where in a body
    a fault lies: its own decoder reads a file at once and cannot say."""
    if data not in _FOUND:
        _FOUND[data] = decode_each([data])[0]
    return _FOUND[data]


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


Run = collections.namedtuple("Run", "status core memory error legs logs opened taken stored lines")
Run.__doc__ = """One run of `odrig_host session`.

`core` is "ok" or "null". `memory` is `(bytes, blocks)`: what the core asked the host for
while it started. `error` is the reason the show is invalid after startup, or `None`.
`legs` holds `(leg, pin, LED count)` for each leg. `logs` are the diagnostic texts the core
gave the host while it started. `opened` holds `(name, result)` for each file the core asked
the host to open while it started, when the session has the option `--trace-files`.
`taken` holds `(name, bytes)` for each file the core closed while it started: how many of
its bytes the core had read, when the session has the option `--trace-reads`.
`stored` holds the storage calls the core made while it started, each as the text after
`store `, when the session has the option `--trace-store`. `lines` is everything printed
after startup.
"""

# The storage of the board and the block of its file system, which the test host and the
# emulator report space by.
BOARD_STORAGE = 13500416
STORAGE_BLOCK = 4096


def free_space(files, total=BOARD_STORAGE):
    """The free bytes a host reports for these files: the total less the size of each file
    rounded up to a whole block, and not below 0."""
    used = sum(-(-len(content if isinstance(content, bytes) else content.encode("utf-8")) // STORAGE_BLOCK) * STORAGE_BLOCK for content in files.values())
    return max(0, total - used)


def _script_bytes(script):
    return "".join(f"{line}\n" for line in script).encode("ascii")


# With this option the test host lets the check after the start end before the session.
CHECK_FIRST = "--check-first"


def session(folder, script=(), options=(), status=0, check_first=True):
    """Starts the core on a folder with the test host and gives it the lines of a script.

    The session begins with every file read to its end, as a core that has run for a
    while has them, unless `check_first` is false: then it begins as the core does after
    power-on, with the bodies of the files still to be checked."""
    options = [*options, CHECK_FIRST] if check_first else options
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
    taken = []
    stored = []
    position = 0
    for position, line in enumerate(printed):
        word, _, rest = line.partition(" ")
        if word == "log" and core is None:
            logs.append(rest)
        elif word == "open" and core is None:
            name, _, answer = rest.rpartition(" ")
            opened.append((name, int(answer)))
        elif word == "read" and core is None:
            name, _, count = rest.rpartition(" ")
            taken.append((name, int(count)))
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
    return Run(status, core, memory, error, tuple(legs), tuple(logs), tuple(opened), tuple(taken), tuple(stored), lines)


def start(files, script=(), options=(), status=0, check_first=True):
    """Installs the files in a temporary folder and runs a session on it."""
    with installed(files) as folder:
        return session(folder, script, options, status, check_first)


def folder_files(folder):
    """The files of a folder: the content of each by its name."""
    return {path.name: path.read_bytes() for path in sorted(pathlib.Path(folder).iterdir()) if path.is_file()}


def start_and_keep(files, script=(), options=(), status=0, check_first=True):
    """Installs the files in a temporary folder and runs a session on it. Returns the run
    and the files the folder holds afterwards."""
    with installed(files) as folder:
        run = session(folder, script, options, status, check_first)
        return run, folder_files(folder)


def start_each(file_sets, script=(), options=(), check_first=True):
    """A session for each set of files, all in one run of the test host, which holds the
    files in memory. The results are in the given order. `check_first` is as for one
    session."""
    options = [*options, CHECK_FIRST] if check_first else options
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
        pack_with_the_converter(ROOT / "shows" / "example" / "show.json", ROOT / "mapping" / "legs-2.json", ROOT / "animations", out)
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


def frames_payload(data):
    """The ODRG file a runtime file plays: an ODRG file itself, or a container's payload."""
    return odrgx.payload_of(data) if odrgx.is_container(data) else data


def header_fault(data, canvas):
    """The reason a reader refuses a runtime file for by its headers, as the core reads them
    before any frame record, or None: a container's header, the header of the ODRG file of
    its frames and their canvas, and last the canvas against `canvas`, as `size-mismatch`.
    A text has its canvas in the container's header alone."""
    container = None
    if odrgx.is_container(data):
        try:
            container = odrgx.read_header(data)
        except errors.Rejection as rejection:
            return rejection.reason
        if container.type != 1:
            return "size-mismatch" if (container.width, container.height) != tuple(canvas) else None
    inner = frames_payload(data)
    # The header alone, when it is sound, is refused as a file cut after it.
    try:
        odrg.decode(inner[:16])
    except errors.Rejection as rejection:
        if len(inner) < 16 or rejection.reason != "truncated":
            return rejection.reason
    width, height = struct.unpack_from("<HH", inner, 6)
    if container is not None and (width, height) != (container.width, container.height):
        return "canvas-mismatch"
    if (width, height) != tuple(canvas):
        return "size-mismatch"
    return None


def type_of(data):
    """What `list` says a runtime file holds."""
    if odrgx.is_container(data) and data[5] in odrgx.TYPE_NAMES:
        return odrgx.TYPE_NAMES[data[5]]
    return "frames"


def rendered(data, times, seed=None):
    """The pictures the core's drawing makes of a text or a clock at these times into its
    turn, a clock with a seed, by `odrig_host render`, or the reason it is refused for."""
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "drawn.odrgx"
        path.write_bytes(data)
        seeded = () if seed is None else ("--seed", str(seed))
        lines = host_lines("render", *seeded, str(path), *(str(time) for time in times))
    if lines[0].startswith("rejected "):
        return lines[0][len("rejected "):]
    return [bytes.fromhex(line.split(" ")[3]) for line in lines]


def mix(value):
    """MurmurHash3's finalizer, as the core mixes the timestamps of the refreshes and the
    seed of a clock's turn."""
    value ^= value >> 16
    value = (value * 0x85EBCA6B) & 0xFFFFFFFF
    value ^= value >> 13
    value = (value * 0xC2B2AE35) & 0xFFFFFFFF
    return value ^ (value >> 16)


def seed_of(noise, number, start):
    """The seed of the turn of a clock: the noise, the item's id and the turn's start."""
    return mix(noise ^ mix((number ^ start) & 0xFFFFFFFF)) or 1


class _Drawn:
    """A text or a clock. The reference knows the length of its loop, a text's pass or a
    clock's seconds, and takes the pictures from the core's drawing, which tests of their
    own hold to the converter's pictures."""

    AHEAD = 250

    def __init__(self, data, loop):
        self.data = data
        self.total = loop
        self.broken = None
        self.widget = type_of(data) == "widget"
        self.pictures = {}

    def picture_at(self, elapsed, seed=None):
        # A text is drawn at its time in its pass, a clock at its time in the turn.
        time = elapsed if self.widget else elapsed % self.total
        if (seed, time) not in self.pictures:
            # The times of the refreshes to come are drawn with it, 20 ms apart.
            ahead = (time + 20 * step for step in range(self.AHEAD))
            times = sorted(set(ahead) if self.widget else {later % self.total for later in ahead})
            self.pictures.update(((seed, later), picture) for later, picture in zip(times, rendered(self.data, times, seed)))
        return self.pictures[(seed, time)]


class _Clip:
    """The frames of one `.odrg` file, as the reference decoder gives them.

    Of a file with a fault in a frame record, the frames before that record, and in
    `broken` the reason the record is refused for: whoever plays the file meets the fault
    when the time comes to the end of those frames."""

    def __init__(self, records, broken=None):
        self.pictures = [picture for _, picture in records]
        self.ends = list(itertools.accumulate(duration for duration, _ in records))
        self.total = self.ends[-1] if self.ends else 0
        self.broken = broken

    def picture_at(self, elapsed):
        """The frame whose time span contains this time, with the animation looping. Of a
        file with a fault, the time lies in the frames before the fault."""
        return self.pictures[bisect.bisect_right(self.ends, elapsed if self.broken else elapsed % self.total)]


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

    def __init__(self, files, storage=BOARD_STORAGE, changeable=True, check_first=True):
        """`files` maps the name of each installed file to its content. `storage` is the
        total space the host reports, or None for a host that cannot tell its space.
        `changeable` says whether the host's storage can be changed. With `check_first`
        the check after the start has ended before the first call, as the test host's
        option of that name has it; without, the player is as after power-on."""
        self.storage = storage
        self.changeable = changeable
        self.error = None       # the reason the show is invalid, or None
        self.start = None       # the id of the `start` item of the show
        self.min_seconds = show.MIN_SECONDS     # how long an animation without `repeat` plays at least
        self.says_min_seconds = False           # the show file names that time itself
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
        # The check after the start: for each file whose body is still to be read, in the
        # order of the checks, its name, the steps left, and the reason its body is
        # refused for or None; and the refreshes in a row without a grid time left out.
        self.checks = []
        self.check_row = 0
        self.check_idle = 0     # the refreshes in a row at which the check took no step
        self.legs = []          # (leg number, pin, the pixel place of each LED) for each leg
        self.items = {}         # the items of the show by id
        self.clips = {}         # the frames of each file by name
        self.on = True
        self.brightness = 0
        self.noise = 0          # what the timestamps of the polls were mixed into
        self.seed = 0           # the seed of the latest clock's turn
        self.seed_turn = None   # that turn: the clock's id and the turn's start
        self.seed_shown = False # whether the latest refresh drew that clock, and nothing came between
        self.playing = None     # the id of the cycle being played, ALL for the playlist, or None
        self.turn = None        # while the playlist plays, the id of the animation whose turn it is
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
            # A cycle named as the start plays. Otherwise the playlist plays, from the
            # animation the start names or from its first, when the show has one.
            if start is not None and self.items[start].cycle is not None:
                self._play(start)
            elif start is not None or self._animations():
                self._play_all(start)
            if check_first:
                refused = [f"file-malformed {name} {reason}" for name, _, reason in self.checks if reason is not None]
                self.checks = []
                if refused:
                    self._fail(refused[0])

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
        self.min_seconds = listed.min_seconds
        self.says_min_seconds = "min_seconds" in json.loads(files["show.json"])
        self.items = {item.id: item for item in listed.items}
        self.capacity = max(128, min(len(self.items) + 32, 65535), len(self.items))
        self.start = listed.start
        if self.changeable and self.PENDING in files:
            # What an interrupted change left: a file named there that no item names.
            named = show.files(listed)
            for line in files.pop(self.PENDING)[:1500].split(b"\n")[:-1]:
                name = line.decode("latin-1")
                if show.FILE_NAME.fullmatch(name) and name.endswith(show.ENDINGS) and name not in named:
                    files.pop(name, None)

        for name in show.files(listed):
            if name not in files:
                raise _Invalid(f"file-missing {name}")
            data = files[name]
            # The headers are judged first, then the size against the mapping, then the body.
            fault = header_fault(data, (canvas.width, canvas.height))
            if fault == "size-mismatch":
                raise _Invalid(f"size-mismatch {name}")
            if fault is not None:
                raise _Invalid(f"file-malformed {name} {fault}")
            # The body is read after the start, while the show plays, by a check that
            # takes one step for the file, one for each frame record and one for its end.
            # A host whose storage cannot be changed has no second reader: there the
            # body is read at the start.
            steps, reason, clip = self._judge(data)
            if reason is not None and not self.changeable:
                raise _Invalid(f"file-malformed {name} {reason}")
            if reason is not None and type_of(data) != "frames":
                # Nothing of a text is played before its fault.
                clip = _Clip([], reason)
            elif reason is not None:
                # The frames before the fault can be played. A fault after the last
                # frame record is met by the check alone.
                sound = found_in(data).records
                clip = _Clip(sound, None if len(sound) == struct.unpack_from("<I", frames_payload(data), 12)[0] else reason)
            self.clips[name] = clip
            if self.changeable:
                self.checks.append([name, steps, reason])
        return listed.start

    def _fail(self, reason):
        """Makes the show invalid while it runs: nothing plays from here on."""
        self.error = reason
        self.seed_shown = False
        self.playing = self.shown = self.zero = self.turn = None
        if self.upload is not None:
            self._discard()

    ALL = "all"

    def _play(self, number):
        """Starts a cycle. An animation is not played by itself: it has its turn."""
        self.seed_shown = False
        self.playing = number
        self.zero = None
        self.shown = self.items[number].cycle[0]

    def _animations(self):
        """The ids of the animation items, in the order of the show: the playlist."""
        return [item.id for item in self.items.values() if item.cycle is None]

    def _play_all(self, number=None):
        """Starts the playlist with the turn of an animation, or of its first one."""
        self.seed_shown = False
        self.playing = self.ALL
        self.zero = None
        self.turn = self.shown = self._animations()[0] if number is None else number

    def _whole_passes(self, number, turn):
        """A longest time given to the turn of a text, rounded up to its whole passes."""
        clip = self.clips[self.items[number].file]
        if not isinstance(clip, _Drawn) or clip.widget:
            return turn
        return -(-turn // clip.total) * clip.total

    def _turn_ms(self, number):
        """How long the turn of an animation lasts: its loops, which are the show's
        `repeat` or the fewest that last `min_seconds`, cut at its `max_seconds`, or, for a
        text, at the whole pass in which that ends."""
        item = self.items[number]
        loop = self.clips[item.file].total
        loops = item.repeat if item.repeat is not None else -(-1000 * self.min_seconds // loop)
        turn = loops * loop
        if item.max_seconds is None or turn <= 1000 * item.max_seconds:
            return turn
        return self._whole_passes(number, 1000 * item.max_seconds)

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
        elapsed = now - self.zero
        if self.playing == self.ALL:
            # The turn that this moment falls into. A turn begins where the one before it
            # ended, however late the refresh comes.
            order = self._animations()
            while True:
                item = self.items[self.turn]
                clip = self.clips[item.file]
                if clip.broken:
                    # The frames before the fault are played as a first loop. The fault
                    # is met when the time comes to their end; a longest time of the
                    # turn that lies before it ends the turn first.
                    longest = None if item.max_seconds is None else 1000 * item.max_seconds
                    if clip.total <= (elapsed if longest is None else min(elapsed, longest)):
                        self._fail(f"file-malformed {item.file} {clip.broken}")
                        return None
                    if longest is None or elapsed < longest:
                        break
                    turn = longest
                else:
                    turn = self._turn_ms(self.turn)
                    if elapsed < turn:
                        break
                elapsed -= turn
                self.zero += turn
                self.turn = order[(order.index(self.turn) + 1) % len(order)]
        else:
            # Turn t of a cycle shows the animation at place t mod n, with its time
            # counted from the start of the turn. A turn is `seconds` long, a text's
            # rounded up to its whole passes.
            cycle = self.items[self.playing]
            lengths = [self._whole_passes(number, 1000 * cycle.seconds) for number in cycle.cycle]
            elapsed %= sum(lengths)
            place = 0
            while elapsed >= lengths[place]:
                elapsed -= lengths[place]
                place += 1
            item = self.items[cycle.cycle[place]]
            clip = self.clips[item.file]
            if clip.broken and clip.total <= elapsed:
                self._fail(f"file-malformed {item.file} {clip.broken}")
                return None
        self.shown = item.id
        self.seed_shown = isinstance(clip, _Drawn) and clip.widget
        if self.seed_shown:
            # A clock's turn gets its seed at its first refresh and keeps it to its end.
            start = now - elapsed
            if self.seed_turn != (item.id, start):
                self.seed = seed_of(self.noise, item.id, start)
                self.seed_turn = (item.id, start)
            picture = clip.picture_at(elapsed, self.seed)
        else:
            picture = clip.picture_at(elapsed)
        return picture if self.on else None

    def poll(self, now):
        """A request for a refresh at a timestamp.

        Returns `(leg number, LED data)` for each leg, or None when no refresh is due.
        """
        self.noise = mix(self.noise ^ (now & 0xFFFFFFFF))
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
        # The check after the start takes as many steps as refreshes have followed one
        # another without a gap and no more than 2 ms after their grid times, while the
        # last whole second had 30 refreshes or more, at most 16. At any other refresh it
        # takes none, or one when it took none at the nine refreshes before either. A
        # fault it finds makes the show invalid from this refresh on.
        if self.error is None and self.checks:
            second = (now - self.t0) // 1000
            steady = second == 0 or self.refreshes_in[second - 1] >= self.CHECK_LEAST_RATE
            on_time = in_step and now - grid <= self.CHECK_ON_TIME_MS and steady
            self.check_row = min(self.check_row + 1, self.CHECK_MOST_STEPS) if on_time else 0
            steps = self.check_row if on_time else int(self.check_idle >= self.CHECK_LONGEST_WAIT)
            self.check_idle = 0 if steps else self.check_idle + 1
            for _ in range(steps):
                check = self.checks[0]
                check[1] -= 1
                if check[1] == 0:
                    self.checks.pop(0)
                    if check[2] is not None:
                        self._fail(f"file-malformed {check[0]} {check[2]}")
                        picture = None
                    if self.error is not None or not self.checks:
                        break
        if picture is None:
            return [(leg, bytes(3 * len(places))) for leg, _, places in self.legs]
        sent = picture.translate(bytes((value * self.brightness + 127) // 255 for value in range(256)))
        return [(leg, b"".join(sent[3 * place:3 * place + 3] for place in places)) for leg, _, places in self.legs]

    CHECK_MOST_STEPS = 16
    CHECK_LONGEST_WAIT = 9
    CHECK_ON_TIME_MS = 2
    CHECK_LEAST_RATE = 30
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
        if name == b"play" and arguments == [b"all"]:
            if self.error is not None:
                return "show-invalid"
            if not self._animations():
                return "unknown-id"
            self._play_all()
            return None
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
            if self.items[value].cycle is None:
                self._play_all(value)
            else:
                self._play(value)
        elif name == b"brightness":
            self.brightness = value
        elif name == b"space":
            if self.storage is None:
                return "storage-error"
        elif name == b"list":
            if self.error is not None:
                return "show-invalid"
            if self.checks:
                return "busy"
        elif name == b"remove":
            if self.error is not None:
                return "show-invalid"
            if self.checks or self.upload is not None:
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
        fault = header_fault(data, self.canvas)
        if fault is not None:
            return 1, fault, None
        if type_of(data) != "frames":
            # The payload is read whole in one step, and the end in another.
            reason = found_in(data).reason
            return (2, reason, None) if reason is not None else (3, None, _Drawn(data, odrgx.read_header(data).loop_ms))
        try:
            records = odrg.decode(frames_payload(data)).records
        except errors.Rejection as rejection:
            sound = self.sound_records.get(zlib.crc32(data))
            if sound is None:
                sound = len(found_in(data).records)
            return sound + 2, rejection.reason, None
        if odrgx.is_container(data):
            # After the last record: the payload's length, then the loop.
            container = odrgx.read_header(data)
            if len(data) - odrgx.HEADER.size != container.payload_size:
                return len(records) + 2, "payload-size", None
            if sum(duration for duration, _ in records) != container.loop_ms:
                return len(records) + 2, "loop-mismatch", None
        return len(records) + 2, None, _Clip(records)

    def _upload(self, arguments):
        """The four `upload` commands. Returns an error code, a reply, or None."""
        verb = arguments[0] if arguments else b""
        if verb == b"begin":
            number = self._number(arguments[1], 1, 65535) if len(arguments) == 4 else None
            size = self._number(arguments[3], 1, 4294967295) if len(arguments) == 4 else None
            name = arguments[2].decode("latin-1") if len(arguments) == 4 else ""
            if number is None or size is None or not show.FILE_NAME.fullmatch(name) or not name.endswith(show.ENDINGS):
                return "bad-argument"
            if self.error is not None:
                return "show-invalid"
            if self.checks or self.upload is not None:
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
        # An item that gets another animation keeps what the show says of its turn.
        self.items[number] = show.Item(number, name, None, None, old.repeat if old else None, old.max_seconds if old else None)
        if old is not None:
            if old.file != name and all(other.file != old.file for other in self.items.values()):
                self.files.pop(old.file, None)
                self.clips.pop(old.file, None)
            if self.playing == self.ALL and self.turn == number:
                # The animation whose turn it is has another file: its turn begins again.
                self.zero = None
            played = None if self.playing == self.ALL else self.items.get(self.playing)
            if played is not None and number in played.cycle:
                self._play(self.playing)
        elif self.playing is None:
            # The show had no animation, and nothing played: the playlist starts.
            self._play_all()
        if old is None or old.file != name:
            self.files["show.json"] = self.show_text()

    def _listed(self, item, with_entries=True):
        """One item as `list` writes it."""
        if item.cycle is None:
            data = self.files[item.file]
            return json.dumps({"id": item.id, "file": item.file, "bytes": len(data), "ignored": bool(item.ignored), "type": type_of(data)}, separators=(",", ":"))
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
                turn = {name: value for name, value in (("repeat", item.repeat), ("max_seconds", item.max_seconds), ("ignored", item.ignored)) if value is not None}
                items.append({"id": item.id, "file": item.file, **turn})
            else:
                items.append({"id": item.id, "cycle": list(item.cycle), "seconds": item.seconds})
        written = {"version": 1, "brightness": self.show_brightness}
        if self.says_min_seconds:
            written["min_seconds"] = self.min_seconds
        written["items"] = items
        if self.start is not None:
            written["start"] = self.start
        return json.dumps(written, separators=(",", ":")).encode("ascii") + b"\n"

    def _remove(self, number):
        """Takes an item out of the show, and its file out of the folder when no other
        item names it."""
        order = self._animations()
        goes_on = None
        if self.playing == self.ALL and self.turn == number:
            # The playlist goes on with the animation after the one that leaves.
            goes_on = order[(order.index(number) + 1) % len(order)]
        elif self.playing == number:
            # The cycle that plays leaves: the playlist plays, from its first animation.
            goes_on = order[0]
        item = self.items.pop(number)
        if self.start == number:
            self.start = None
        if goes_on == number:
            # It was the only animation of the show.
            self.playing = self.shown = self.zero = self.turn = None
        elif goes_on is not None:
            self._play_all(goes_on)
        if item.file is not None and all(other.file != item.file for other in self.items.values()):
            self.files.pop(item.file, None)
            self.clips.pop(item.file, None)
        self.files["show.json"] = self.show_text()

    def _space(self):
        animations = 0 if self.error is not None else sum(1 for item in self.items.values() if item.cycle is None)
        state = {"ok": True, "free": free_space(self.files, self.storage), "total": self.storage, "animations": animations, "external": {"present": False, "free": None, "total": None, "read_only": True}}
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
            "width": self.canvas[0] if self.legs else None,
            "height": self.canvas[1] if self.legs else None,
            "seed": self.seed if self.seed_shown and self.error is None and self.playing is not None else None,
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

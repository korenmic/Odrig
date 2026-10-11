"""Helpers shared by the tests of the core: where things are and how the test host is run."""

import collections
import contextlib
import functools
import json
import pathlib
import random
import subprocess
import tempfile

from odrig import jsonframes, odrg, pack

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


# Mappings beyond the two tracked ones: a leg that starts on the left, legs of two and of
# four rows, legs listed in another order than their numbers and their rows, and one LED.
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
}


def mapping_texts():
    """Every mapping the suite plays on, by name: the tracked files and the made-up ones."""
    texts = {path.stem: path.read_text(encoding="utf-8") for path in sorted((ROOT / "mapping").glob("*.json"))}
    texts.update({name: json.dumps(mapping) for name, mapping in MADE_UP_MAPPINGS.items()})
    return texts


@contextlib.contextmanager
def installed(files):
    """A temporary folder that holds these files, given as a mapping from name to content."""
    with tempfile.TemporaryDirectory() as folder:
        for name, content in files.items():
            data = content if isinstance(content, bytes) else content.encode("utf-8")
            pathlib.Path(folder, name).write_bytes(data)
        yield folder


Run = collections.namedtuple("Run", "status core memory error legs logs opened lines")
Run.__doc__ = """One run of `odrig_host session`.

`core` is "ok" or "null". `memory` is `(bytes, blocks)`: what the core asked the host for
while it started. `error` is the reason the show is invalid after startup, or `None`.
`legs` holds `(leg, pin, LED count)` for each leg. `logs` are the diagnostic texts the core
gave the host while it started. `opened` holds `(name, result)` for each file the core asked
the host to open while it started, when the session has the option `--trace-files`.
`lines` is everything printed after startup.
"""


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
    position = 0
    for position, line in enumerate(printed):
        word, _, rest = line.partition(" ")
        if word == "log" and core is None:
            logs.append(rest)
        elif word == "open" and core is None:
            name, _, answer = rest.rpartition(" ")
            opened.append((name, int(answer)))
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
    return Run(status, core, memory, error, tuple(legs), tuple(logs), tuple(opened), lines)


def start(files, script=(), options=(), status=0):
    """Installs the files in a temporary folder and runs a session on it."""
    with installed(files) as folder:
        return session(folder, script, options, status)


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

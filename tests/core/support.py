"""Helpers shared by the tests of the core: where things are and how the test host is run."""

import collections
import pathlib
import subprocess

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

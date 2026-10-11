"""The Python side of the tests of the JavaScript converter: what only the Python tool has.

Started as `python converter/tests/reference.py REQUEST [ARGUMENT ...]`. A request reads
its input from standard input as JSON and writes its result to standard output as JSON.
Bytes travel as hexadecimal text, and whole numbers of any size as decimal text.
"""

import contextlib
import fractions
import hashlib
import importlib
import io
import json
import os
import sys
import tempfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from odrig import cli, errors, jsonframes, mapping, odrg  # noqa: E402


def _run(argv):
    """One command line of the Python tool, run in this interpreter: status and both streams."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = cli.main(argv)
    return [status, out.getvalue(), err.getvalue()]


def check(arguments, files):
    """What `python -m odrig check --format FORMAT case.FORMAT` gives for each file.

    The files are given as hexadecimal text. Each is written under the name `case.json` or
    `case.odrg` into an empty folder, in which the tool is run.
    """
    (kind,) = arguments
    name = f"case.{kind}"
    results = []
    before = os.getcwd()
    with tempfile.TemporaryDirectory() as folder:
        os.chdir(folder)
        try:
            for data in files:
                with open(name, "wb") as file:
                    file.write(bytes.fromhex(data))
                results.append(_run(["check", "--format", kind, name]))
        finally:
            os.chdir(before)
    return results


def sixdigits(arguments, values):
    """`format(float(n / d), ".6g")` for each pair of whole numbers `[n, d]`."""
    return [format(float(fractions.Fraction(int(n), int(d))), ".6g") for n, d in values]


def _animation(given):
    frames = tuple((int(ms), bytes.fromhex(picture)) for ms, picture in given["frames"])
    return jsonframes.Animation(int(given["width"]), int(given["height"]), frames)


def dumps(arguments, animations):
    """The bytes of `odrig.jsonframes.dumps` for each animation, merged unless `merge` is false."""
    return [jsonframes.dumps(_animation(given), merge=given.get("merge", True)).hex() for given in animations]


def milliseconds(arguments, texts):
    """The whole milliseconds the command line reads from each text of seconds, as decimal text."""
    return [str(cli._milliseconds(text)) for text in texts]


def inflate(arguments, streams):
    """zlib's verdict on each raw DEFLATE stream.

    `{"data": output, "left": bytes after the stream}` for a stream zlib takes to its end,
    else `{"reason": "bad-deflate"}` or `{"reason": "truncated"}`, as `odrig.odrg` tells
    them apart.
    """
    verdicts = []
    for stream in streams:
        inflater = zlib.decompressobj(wbits=-15)
        try:
            body = inflater.decompress(bytes.fromhex(stream)) + inflater.flush()
        except zlib.error:
            verdicts.append({"reason": "bad-deflate"})
            continue
        if not inflater.eof:
            verdicts.append({"reason": "truncated"})
        else:
            verdicts.append({"data": body.hex(), "left": len(inflater.unused_data)})
    return verdicts


def deflate(arguments, inputs):
    """One raw DEFLATE stream of zlib for each `{"data", "level", "strategy"}`."""
    strategies = {
        "default": zlib.Z_DEFAULT_STRATEGY,
        "filtered": zlib.Z_FILTERED,
        "huffman": zlib.Z_HUFFMAN_ONLY,
        "rle": zlib.Z_RLE,
        "fixed": zlib.Z_FIXED,
    }
    streams = []
    for given in inputs:
        strategy = strategies[given.get("strategy", "default")]
        deflater = zlib.compressobj(given["level"], zlib.DEFLATED, -15, zlib.DEF_MEM_LEVEL, strategy)
        streams.append((deflater.compress(bytes.fromhex(given["data"])) + deflater.flush()).hex())
    return streams


def _generated(given):
    """The animation of a generator of the Python tool on the canvas of a mapping file."""
    canvas = mapping.read(os.path.join(ROOT, given["mapping"]))
    module = importlib.import_module(f"odrig.generators.{given['generator']}")
    if "seconds" in given:
        frames = module.frames(canvas.width, canvas.height, given["seconds"])
    else:
        frames = module.frames(canvas.width, canvas.height)
    return jsonframes.Animation(canvas.width, canvas.height, tuple(frames))


def encode(arguments, sources):
    """The uncompressed and the compressed file of `odrig.odrg.encode` for each source.

    A source is an animation, or `{"generator", "mapping"}` with `"seconds"` for the dense
    clip: the animation a generator of the Python tool makes for the canvas of a mapping
    file.
    """
    files = []
    for given in sources:
        animation = _generated(given) if "generator" in given else _animation(given)
        files.append(
            {
                "uncompressed": odrg.encode(animation, compressed=False).hex(),
                "compressed": odrg.encode(animation, compressed=True).hex(),
            }
        )
    return files


def forms(arguments, cases):
    """The 64 coded records of `odrig.odrg.coded_record` for each pair of pixel buffers.

    A case is `{"old", "new", "width", "bpp"}`. The result has the records in the order of
    the search, predictors 0 to 3, plain mode before run mode, k from 0 to 7, with null for
    a form whose data is longer than the buffer, and the record `best_record` chooses.
    """
    results = []
    for given in cases:
        old, new = bytes.fromhex(given["old"]), bytes.fromhex(given["new"])
        width, bpp = given["width"], given["bpp"]
        records = []
        for predictor in range(4):
            for run in (False, True):
                for k in range(8):
                    try:
                        records.append(odrg.coded_record(old, new, width, bpp, 20, predictor, run, k).hex())
                    except ValueError:
                        records.append(None)
        results.append({"records": records, "best": odrg.best_record(old, new, width, bpp, 20).hex()})
    return results


def decode(arguments, files):
    """What `odrig.odrg.decode` gives for each file: the size, the palette size, whether the
    body is compressed, and for every frame record its duration, its mode byte and the
    SHA-256 of the picture after it; or the reason of its rejection."""
    results = []
    for data in files:
        try:
            decoded = odrg.decode(bytes.fromhex(data))
        except errors.Rejection as rejection:
            results.append({"reason": rejection.reason})
            continue
        results.append(
            {
                "width": decoded.width,
                "height": decoded.height,
                "palette": decoded.palette_size,
                "compressed": decoded.compressed,
                "records": [
                    [ms, mode, hashlib.sha256(picture).hexdigest()]
                    for (ms, picture), mode in zip(decoded.records, decoded.modes)
                ],
            }
        )
    return results


REQUESTS = {
    "check": check,
    "encode": encode,
    "forms": forms,
    "decode": decode,
    "sixdigits": sixdigits,
    "dumps": dumps,
    "milliseconds": milliseconds,
    "inflate": inflate,
    "deflate": deflate,
}


def main(argv):
    request, arguments = argv[0], argv[1:]
    given = json.load(sys.stdin)
    json.dump(REQUESTS[request](arguments, given), sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""The Python side of the tests of the JavaScript converter: what only the Python tool has.

Started as `python converter/tests/reference.py REQUEST ASKED ANSWERED [ARGUMENT ...]`. A
request reads its input from the file ASKED as JSON and writes its result into the file
ANSWERED as JSON. Bytes travel as hexadecimal text, and whole numbers of any size as
decimal text.
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
import types
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from odrig import cli, errors, jsonframes, mapping, odrg, show  # noqa: E402


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


def mappings(arguments, given):
    """The mapping files the suites of the core play on, by name: the tracked files and the
    made-up ones of both kinds, each as its text."""
    from tests.core import support

    return support.mapping_texts()


def read_mappings(arguments, files):
    """What `odrig.mapping.loads` gives for each file, or its rejection."""
    results = []
    for data in files:
        try:
            canvas = mapping.loads(bytes.fromhex(data))
        except errors.Rejection as rejection:
            results.append({"reason": rejection.reason, "detail": rejection.detail})
            continue
        results.append(
            {
                "kind": canvas.kind,
                "width": canvas.width,
                "height": canvas.height,
                "strip_length": canvas.strip_length,
                "legs": [
                    {
                        "leg": leg.leg,
                        "pin": leg.pin,
                        "first_led": leg.first_led,
                        "strips": list(leg.strips),
                        "led_count": canvas.led_count(leg),
                    }
                    for leg in canvas.legs
                ],
            }
        )
    return results


def read_shows(arguments, files):
    """What `odrig.show.loads` gives for each file, with the file names of `show.files`, or
    its rejection."""
    results = []
    for data in files:
        try:
            listed = show.loads(bytes.fromhex(data))
        except errors.Rejection as rejection:
            results.append({"reason": rejection.reason, "detail": rejection.detail})
            continue
        results.append(
            {
                "brightness": listed.brightness,
                "start": listed.start,
                "items": [
                    {"id": item.id, "file": item.file, "cycle": None if item.cycle is None else list(item.cycle), "seconds": item.seconds}
                    for item in listed.items
                ],
                "files": show.files(listed),
            }
        )
    return results


def _fraction(value):
    """A whole number given as text, or a fraction given as `[n, d]` of texts."""
    if isinstance(value, list):
        return fractions.Fraction(int(value[0]), int(value[1]))
    return fractions.Fraction(int(value))


def _refusal(rejection):
    return {"reason": rejection.reason, "detail": rejection.detail}


def rects(arguments, cases):
    """`odrig.media.source_rect` for each `[sw, sh, w, h, fit]`: left, top, width and height,
    each as `[n, d]` of texts."""
    from odrig import media

    return [[[str(value.numerator), str(value.denominator)] for value in media.source_rect(*case)] for case in cases]


def resample(arguments, cases):
    """The canvas picture `odrig.media` gives for each case, or its rejection.

    A case has `columns`, `rows`, `w` and `h`, and either `rgba` and `fits`, a source picture
    that is laid over black and fitted with each of the fits, which gives a list, or `rgb`
    and `rect`, a picture and the rectangle of it to show, its four values each a whole
    number or `[n, d]`.
    """
    import numpy

    from odrig import media

    def one(picture, rect, w, h):
        try:
            return media.resample(picture, rect, w, h).hex()
        except errors.Rejection as rejection:
            return _refusal(rejection)

    results = []
    for given in cases:
        columns, rows, w, h = given["columns"], given["rows"], given["w"], given["h"]
        if "rgba" in given:
            rgba = numpy.frombuffer(bytes.fromhex(given["rgba"]), dtype=numpy.uint8).reshape(rows, columns, 4)
            try:
                picture = media._over_black(rgba)
            except errors.Rejection as rejection:
                results.append([_refusal(rejection) for fit in given["fits"]])
                continue
            results.append([one(picture, media.source_rect(columns, rows, w, h, fit), w, h) for fit in given["fits"]])
        else:
            picture = numpy.frombuffer(bytes.fromhex(given["rgb"]), dtype=numpy.uint8).reshape(rows, columns, 3)
            results.append(one(picture, tuple(_fraction(value) for value in given["rect"]), w, h))
    return results


def ticks(arguments, cases):
    """`odrig.media.tick_pictures` on frames that have times only.

    A case has `frames`, the start and the end of each in milliseconds, `start` and
    `duration`. The result has the number of the frame that is shown at each tick, the
    frames that were fitted, in order, and how many frames were asked for; or the rejection.
    """
    from odrig import media

    results = []
    for given in cases:
        frames = [(_fraction(start), _fraction(end), number) for number, (start, end) in enumerate(given["frames"])]
        asked = []
        fitted = []

        def each():
            for frame in frames:
                asked.append(frame[2])
                yield frame

        def place(number):
            fitted.append(number)
            return number

        duration = None if given["duration"] is None else int(given["duration"])
        try:
            shown = media.tick_pictures(each(), int(given["start"]), duration, place)
        except errors.Rejection as rejection:
            results.append({**_refusal(rejection), "asked": len(asked)})
            continue
        results.append({"ticks": shown, "fitted": fitted, "asked": len(asked)})
    return results


class _FakeVideo:
    """What `odrig.media` uses of an opened video, with frames that are made up."""

    def __init__(self, frames, time_base):
        self.frames = frames
        self.asked = 0
        self.streams = types.SimpleNamespace(video=[types.SimpleNamespace(time_base=time_base)])

    def __enter__(self):
        return self

    def __exit__(self, *failure):
        return False

    def decode(self, stream):
        for pts, picture in self.frames:
            self.asked += 1
            yield types.SimpleNamespace(pts=pts, to_ndarray=lambda format, picture=picture: picture)


class _FakeGif:
    """What `odrig.media` uses of an opened GIF, with frames that are made up."""

    def __init__(self, frames):
        self.frames = frames
        self.asked = 0
        self.n_frames = len(frames)
        self.info = {}
        self.current = None

    def __enter__(self):
        return self

    def __exit__(self, *failure):
        return False

    def seek(self, number):
        self.asked += 1
        self.current = number
        delay = self.frames[number][0]
        self.info = {} if delay is None else {"duration": delay}

    def convert(self, mode):
        return self.frames[self.current][1]


def timeline(arguments, cases):
    """`odrig.media.import_media` on frames that are made up, in place of a file's.

    A case has `kind`, "video" or "gif"; `frames`, each with `width`, `height` and `rgba`,
    and with `pts`, a whole number or null, for a video, or `delay` in milliseconds or null
    for a GIF; `time_base` as `[n, d]` for a video; the canvas `width` and `height`; `fit`,
    `start` and `duration`. The libraries that open a file are replaced by stand-ins that
    hand out these frames, so everything after the decoder is the Python tool's own. The
    result has the JSON frames file of the animation and how many frames were asked for, or
    the rejection, whose detail names the file as clip.mp4 or clip.gif.
    """
    from unittest import mock

    import av
    import numpy
    import PIL.Image

    from odrig import media

    results = []
    before = os.getcwd()
    with tempfile.TemporaryDirectory() as folder:
        os.chdir(folder)
        try:
            for name in ("clip.mp4", "clip.gif"):
                open(name, "wb").close()
            for given in cases:
                pictures = [
                    numpy.frombuffer(bytes.fromhex(frame["rgba"]), dtype=numpy.uint8).reshape(frame["height"], frame["width"], 4)
                    for frame in given["frames"]
                ]
                if given["kind"] == "video":
                    name = "clip.mp4"
                    opened = _FakeVideo(
                        [(frame["pts"], picture) for frame, picture in zip(given["frames"], pictures)],
                        _fraction(given["time_base"]),
                    )
                    patch = mock.patch.object(av, "open", lambda path, opened=opened: opened)
                else:
                    name = "clip.gif"
                    opened = _FakeGif([(frame["delay"], picture) for frame, picture in zip(given["frames"], pictures)])
                    patch = mock.patch.object(PIL.Image, "open", lambda path, formats=None, opened=opened: opened)
                canvas = types.SimpleNamespace(width=given["width"], height=given["height"])
                duration = None if given["duration"] is None else int(given["duration"])
                try:
                    with patch:
                        animation = media.import_media(name, canvas, given["fit"], int(given["start"]), duration)
                except errors.Rejection as rejection:
                    results.append({**_refusal(rejection), "asked": opened.asked})
                    continue
                results.append({"file": jsonframes.dumps(animation).hex(), "ticks": len(animation.frames), "asked": opened.asked})
        finally:
            os.chdir(before)
    return results


def run(arguments, given):
    """What `python -m odrig` gives for each of the command lines of `given["commands"]`,
    run one after the other in this interpreter, in the folder `given["cwd"]`: for each its
    status, its standard output and its standard error."""
    before = os.getcwd()
    os.chdir(given["cwd"])
    try:
        return [_run(list(argv)) for argv in given["commands"]]
    finally:
        os.chdir(before)


REQUESTS = {
    "check": check,
    "mappings": mappings,
    "read_mappings": read_mappings,
    "read_shows": read_shows,
    "encode": encode,
    "forms": forms,
    "decode": decode,
    "sixdigits": sixdigits,
    "dumps": dumps,
    "milliseconds": milliseconds,
    "inflate": inflate,
    "deflate": deflate,
    "rects": rects,
    "resample": resample,
    "ticks": ticks,
    "timeline": timeline,
    "run": run,
}


def main(argv):
    request, asked, answered, arguments = argv[0], argv[1], argv[2], argv[3:]
    with open(asked, encoding="utf-8") as file:
        given = json.load(file)
    result = REQUESTS[request](arguments, given)
    with open(answered, "w", encoding="utf-8") as file:
        json.dump(result, file)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

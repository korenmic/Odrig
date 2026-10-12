"""The Python side of the tests of the JavaScript converter: what only the Python tool has.

Started as `python converter/tests/reference.py REQUEST ASKED ANSWERED [ARGUMENT ...]`. A
request reads its input from the file ASKED as JSON and writes its result into the file
ANSWERED as JSON. Bytes travel as hexadecimal text, and whole numbers of any size as
decimal text.
"""

import contextlib
import ctypes
import fractions
import hashlib
import importlib
import io
import json
import os
import signal
import sys
import tempfile
import traceback
import types
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from odrig import cli, errors, jsonframes, mapping, odrg, show  # noqa: E402


def _quiet_faults():
    """Makes a fault of memory in a library end this program quietly, with the number of the
    signal as its status, in place of a crash report on the screen of whoever sits at the
    computer. The test that asked then fails with that status."""
    try:
        libc = ctypes.CDLL(None)
        libc.signal.restype = ctypes.c_void_p
        libc.signal.argtypes = [ctypes.c_int, ctypes.c_void_p]
        leave = ctypes.cast(libc._exit, ctypes.c_void_p)
    except (OSError, AttributeError):
        return
    for name in ("SIGSEGV", "SIGBUS", "SIGILL", "SIGFPE", "SIGABRT"):
        number = getattr(signal, name, None)
        if number is not None:
            libc.signal(int(number), leave)


def _run(argv):
    """One command line of the Python tool, run in this interpreter: status and both streams.

    An `import` of a video that would end Python with a fault of memory is not run: its
    status is None and its standard error says why. An error the tool does not catch gives
    status 1 and its traceback on standard error, as it does when the tool is a program of
    its own.
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = cli.main(argv)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            status = 1
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
                "minSeconds": listed.min_seconds,
                "items": [
                    {"id": item.id, "file": item.file, "cycle": None if item.cycle is None else list(item.cycle), "seconds": item.seconds,
                     "repeat": item.repeat, "maxSeconds": item.max_seconds}
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
        self.streams = types.SimpleNamespace(video=[types.SimpleNamespace(time_base=time_base, codec_context=object())])

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


def _block(image, at, size, colour):
    """Paints a block of one colour, or of one palette index, into an image."""
    for x in range(at[0], min(image.width, at[0] + size[0])):
        for y in range(at[1], min(image.height, at[1] + size[1])):
            image.putpixel((x, y), colour)


def _palette_frames(seed_value, size, count):
    """Frames of a palette image whose index 0 is transparent: each has one or two blocks of
    a colour on a ground that is nowhere painted."""
    import random

    from PIL import Image

    from tests.converter import media_fixtures as fixtures

    rng = random.Random(seed_value)
    colours = fixtures.COLOURS
    frames = []
    for _ in range(count):
        image = Image.new("P", size, 0)
        image.putpalette([0, 0, 0] + [channel for colour in colours for channel in colour])
        for _ in range(rng.choice((1, 1, 2))):
            at = (rng.randrange(size[0]), rng.randrange(size[1]))
            block = (rng.randint(1, max(1, size[0] // 2)), rng.randint(1, max(1, size[1] // 2)))
            _block(image, at, block, rng.randint(1, len(colours)))
        frames.append(image)
    return frames


def _video(path, pictures, pts, rate, codec="mpeg4", pixels="yuv420p", sound=False, only_sound=False):
    """An mp4 or mov whose frames are the given pictures of red, green, blue and alpha, each
    at its presentation time in units of 1 / rate second."""
    import av
    import numpy

    with av.open(path, "w") as container:
        audio = None
        if sound or only_sound:
            audio = container.add_stream("aac", rate=44100)
        if not only_sound:
            height, width = pictures[0].shape[:2]
            stream = container.add_stream(codec, rate=rate)
            stream.width, stream.height, stream.pix_fmt = width, height, pixels
            stream.codec_context.time_base = 1 / fractions.Fraction(rate)
            for number, picture in zip(pts, pictures):
                frame = av.VideoFrame.from_ndarray(picture, format="rgba")
                frame.pts = number
                frame.time_base = 1 / fractions.Fraction(rate)
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        if audio is not None:
            for number in range(8):
                samples = numpy.zeros((2, 1024), dtype="float32")
                samples[0, ::16] = 0.25
                frame = av.AudioFrame.from_ndarray(samples, format="fltp", layout="stereo")
                frame.sample_rate = 44100
                frame.pts = number * 1024
                for packet in audio.encode(frame):
                    container.mux(packet)
            for packet in audio.encode():
                container.mux(packet)


def media(arguments, given):
    """Writes the media files the import tests read into the folder `given["folder"]`, with
    Pillow and PyAV, and gives their names: `gifs`, `videos`, and `skipped`, a name with
    the reason for each file that could not be made on this computer.

    The GIFs and the videos of the Python suite's import tests are among them, made by
    `tests/converter/media_fixtures.py`.
    """
    import random

    import numpy
    from PIL import Image

    from tests.converter import media_fixtures as fixtures

    folder = given["folder"]
    colours = fixtures.COLOURS
    gifs, videos, skipped = [], [], {}

    def gif(name, make):
        make(os.path.join(folder, name))
        gifs.append(name)

    def video(name, make):
        try:
            make(os.path.join(folder, name))
        except Exception as failure:  # a codec this build of PyAV does not have
            skipped[name] = f"{type(failure).__name__}: {failure}"
            with contextlib.suppress(OSError):
                os.remove(os.path.join(folder, name))
            return
        videos.append(name)

    # The GIFs of the Python suite.
    gif("clip.gif", lambda path: fixtures.write_gif(path, colours[:4], [30, 50, 70, 0]))
    gif("delays.gif", lambda path: fixtures.write_gif(path, colours[:3], [10, 20, 100]))

    def transparent(path):
        first = Image.new("RGBA", (8, 4), colours[0] + (255,))
        for x in range(4, 8):
            for y in range(4):
                first.putpixel((x, y), colours[1] + (0,))
        fixtures.save_gif(path, [first, Image.new("RGBA", (8, 4), colours[2] + (255,))], [40, 40])

    gif("transparent.gif", transparent)

    def rows(path):
        image = Image.new("RGB", (60, 6), colours[2])
        for x in range(60):
            image.putpixel((x, 0), colours[0])
        fixtures.save_gif(path, [image], [100])

    gif("rows.gif", rows)
    gif("still.gif", lambda path: Image.new("RGB", (8, 4), colours[5]).save(path))

    def corners(path):
        image = Image.new("RGB", (12, 8), colours[7])
        for at, colour in (((0, 0), colours[0]), ((11, 0), colours[1]), ((0, 7), colours[2]), ((11, 7), colours[3])):
            image.putpixel(at, colour)
        fixtures.save_gif(path, [image], [100])

    gif("corners.gif", corners)

    # A transparent index on every frame.
    def index(path):
        frames = _palette_frames(1, (12, 6), 4)
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=[40, 60, 80, 40], loop=0, transparency=0, disposal=2)

    gif("index.gif", index)

    # Later frames that are smaller than the screen: Pillow writes only the part that changed.
    def smaller(path):
        frames = []
        for number in range(5):
            image = Image.new("RGB", (16, 8), colours[9])
            _block(image, (2 + 2 * number, 1 + number), (3, 2), colours[number])
            frames.append(image)
        fixtures.save_gif(path, frames, [40, 40, 60, 60, 100])

    gif("smaller.gif", smaller)

    # One for each disposal, with a transparent index on every frame and the disposal named
    # on every frame.
    for disposal in (0, 1, 2, 3):

        def disposed(path, disposal=disposal):
            frames = _palette_frames(10 + disposal, (14, 7), 5)
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=[40, 40, 60, 40, 80], loop=0, transparency=0, disposal=disposal)

        gif(f"disposal-{disposal}.gif", disposed)

    # GIFs from seeds: pictures in a few colours, as Pillow writes them by itself, and
    # palette pictures with a transparent index and one disposal for all frames.
    for number in range(1, 41):
        rng = random.Random(8000 + number)
        size = (rng.randint(1, 20), rng.randint(1, 12))
        count = rng.randint(1, 6)
        delays = [rng.choice((0, 10, 20, 30, 40, 50, 70, 100, 250)) for _ in range(count)]

        def plain(path, rng=rng, size=size, count=count, delays=delays):
            frames = []
            ground = rng.choice(colours)
            for _ in range(count):
                image = Image.new("RGB", size, ground)
                for _ in range(rng.randint(0, 3)):
                    at = (rng.randrange(size[0]), rng.randrange(size[1]))
                    _block(image, at, (rng.randint(1, size[0]), rng.randint(1, size[1])), rng.choice(colours))
                frames.append(image)
            fixtures.save_gif(path, frames, delays)

        gif(f"plain-{number}.gif", plain)

        def indexed(path, number=number, rng=rng, size=size, count=count, delays=delays):
            frames = _palette_frames(9000 + number, size, count)
            disposal = rng.choice((1, 2, 3))
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=delays, loop=0, transparency=0, disposal=disposal)

        gif(f"indexed-{number}.gif", indexed)

    # The videos of the Python suite.
    video("clip.mp4", lambda path: fixtures.write_video(path, colours))
    video("clip.mov", lambda path: fixtures.write_video(path, colours))
    video("three.mp4", lambda path: fixtures.write_video(path, colours[:3]))
    video("one.mp4", lambda path: fixtures.write_video(path, colours[:1]))
    video("late.mp4", lambda path: fixtures.write_video(path, colours[:4], first_pts=7))
    video("late.mov", lambda path: fixtures.write_video(path, colours[:4], first_pts=7))
    video("alpha.mov", lambda path: fixtures.write_video(path, colours[:2], codec="qtrle", pixels="argb", alpha=colours[1]))

    def flat(colour, size=(64, 36)):
        picture = numpy.zeros((size[1], size[0], 4), dtype=numpy.uint8)
        picture[:, :, :3] = colour
        picture[:, :, 3] = 255
        return picture

    def ramp(number, size=(96, 54)):
        picture = numpy.zeros((size[1], size[0], 4), dtype=numpy.uint8)
        picture[:, :, 0] = numpy.linspace(0, 255, size[0], dtype=numpy.uint8)[None, :]
        picture[:, :, 1] = numpy.linspace(255, 0, size[1], dtype=numpy.uint8)[:, None]
        picture[:, :, 2] = (40 * number) % 256
        picture[:, :, 3] = 255
        return picture

    video("gaps.mp4", lambda path: _video(path, [flat(colour) for colour in colours[:7]], [0, 1, 2, 5, 6, 10, 11], 25))
    video("ntsc.mp4", lambda path: _video(path, [flat(colour) for colour in colours], list(range(10)), fractions.Fraction(30000, 1001)))
    video("sixty.mov", lambda path: _video(path, [flat(colour) for colour in colours], list(range(10)), 60))
    video("ramp.mp4", lambda path: _video(path, [ramp(number) for number in range(6)], list(range(6)), 25))
    video("tall.mp4", lambda path: _video(path, [flat(colour, (36, 64)) for colour in colours[:5]], list(range(5)), 25))
    video("h264.mp4", lambda path: _video(path, [flat(colour) for colour in colours * 2], list(range(20)), 25, codec="libx264"))
    video("sound.mp4", lambda path: _video(path, [flat(colour) for colour in colours[:5]], list(range(5)), 25, sound=True))
    video("only-sound.mp4", lambda path: _video(path, [], [], 25, only_sound=True))
    return {"gifs": gifs, "videos": videos, "skipped": skipped}


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
    "media": media,
    "run": run,
}


def main(argv):
    request, asked, answered, arguments = argv[0], argv[1], argv[2], argv[3:]
    _quiet_faults()
    with open(asked, encoding="utf-8") as file:
        given = json.load(file)
    result = REQUESTS[request](arguments, given)
    with open(answered, "w", encoding="utf-8") as file:
        json.dump(result, file)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

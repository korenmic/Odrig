"""import: reading a media file, sampling it on the 20 ms timeline and fitting it to the canvas.

This is the only module that needs third-party libraries. It loads them inside its
functions, so the rest of the tool runs with the Python standard library alone.

A source picture is a numpy array of rows x columns x 3 bytes, the top row first. A canvas
picture is `bytes` in the pixel order of docs/format.md, the bottom row first. Times are
exact fractions of milliseconds.
"""

import os
from fractions import Fraction

from . import errors, jsonframes

FITS = ("fill", "fit", "stretch")
TICK_MS = 20
SHORTEST_GIF_DELAY_MS = 10
GIF_DELAY_MS = 100


def import_media(path, mapping, fit="fill", start_ms=0, duration_ms=None):
    """The animation of a media file on the canvas of a mapping: one 20 ms frame for each tick."""
    frames = source_frames(path)
    width, height = mapping.width, mapping.height

    def place(picture):
        rows, columns = picture.shape[:2]
        return resample(picture, source_rect(columns, rows, width, height, fit), width, height)

    with errors.naming(path):
        pictures = tick_pictures(frames, start_ms, duration_ms, place)
    return jsonframes.Animation(width, height, tuple((TICK_MS, picture) for picture in pictures))


def source_frames(path):
    """`(start_ms, end_ms, picture)` for each frame of a media file, in the order they are shown.

    The reader is chosen by the ending of the file name, in any letter case. Nothing is
    decoded before the frames are asked for.
    """
    reader = _READERS.get(os.path.splitext(os.fspath(path))[1].lower())
    if reader is None:
        raise errors.Rejection(
            errors.UNSUPPORTED_MEDIA, f"{path}: the name does not end in .mp4, .mov or .gif"
        )
    if not os.path.isfile(path):
        raise errors.Rejection(errors.NOT_FOUND, f"{path}: there is no such file")
    return reader(path)


def tick_pictures(frames, start_ms, duration_ms, resample):
    """One canvas picture for each 20 ms tick of the requested part of the media.

    The first tick is at `start_ms`. A tick shows the frame that is on screen at its time:
    the last frame that starts no later. `resample` turns a source picture into a canvas
    picture and is called once for each frame that is on screen at a tick. Without a
    duration the part runs to the end of the media, which is the end of its last frame.
    """
    if start_ms < 0:
        raise errors.Rejection(errors.BAD_RANGE, "the start is negative")
    if duration_ms is not None and duration_ms <= 0:
        raise errors.Rejection(errors.BAD_RANGE, "the duration is not above 0")
    wanted = None if duration_ms is None else tick_count(duration_ms)
    stop = None if duration_ms is None else start_ms + duration_ms

    pictures = []
    length = None
    for _, end, picture in frames:
        length = end
        placed = None
        while (wanted is None or len(pictures) < wanted) and start_ms + TICK_MS * len(pictures) < end:
            if placed is None:
                placed = resample(picture)
            pictures.append(placed)
        if stop is not None and end >= stop:
            break
    if length is None:
        raise errors.Rejection(errors.UNREADABLE_MEDIA, "the file holds no picture")
    if start_ms >= length:
        raise errors.Rejection(
            errors.BAD_RANGE, f"the start of {start_ms} ms is not before the end of the media at {_ms(length)} ms"
        )
    if stop is not None and stop > length:
        raise errors.Rejection(
            errors.BAD_RANGE, f"the part ends at {stop} ms, after the end of the media at {_ms(length)} ms"
        )
    return pictures[:wanted if wanted is not None else tick_count(length - start_ms)]


def tick_count(length_ms):
    """The number of 20 ms ticks of a length: the nearest whole number, halves up, at least 1."""
    return max(1, (2 * Fraction(length_ms) + TICK_MS) // (2 * TICK_MS))


def _ms(time):
    return f"{float(time):.6g}"


def source_rect(sw, sh, w, h, fit):
    """The rectangle of the source, in source pixels, that a canvas of w x h shows.

    The result is `(left, top, width, height)` as exact fractions. Canvas pixels are square,
    so the canvas has the shape w to h. `fill` covers the canvas and cuts off the overflow
    equally on two opposite sides; `fit` shows the whole picture, with a rectangle that
    reaches beyond it equally on two sides; `stretch` shows the whole picture whatever its
    shape.
    """
    if fit not in FITS:
        raise ValueError(f"there is no fit {fit!r}")
    sw, sh = Fraction(sw), Fraction(sh)
    wider = sw * h >= sh * w
    if fit == "stretch":
        return Fraction(0), Fraction(0), sw, sh
    if (fit == "fill") == wider:
        width = sh * w / h
        return (sw - width) / 2, Fraction(0), width, sh
    height = sw * h / w
    return Fraction(0), (sh - height) / 2, sw, height


def resample(picture, rect, w, h):
    """The canvas picture of the part `rect` of a source picture.

    Every canvas pixel is the mean of the source area it covers, each source pixel weighted
    by the area they share, for each colour channel, rounded to the nearest whole number
    with halves rounded up. Area outside the picture counts as black. All of it is computed
    in whole numbers: every length is counted in units of 1 / (2 * w * h) source pixel.
    """
    import numpy

    rows, columns = picture.shape[:2]
    unit = 2 * w * h
    left, top, width, height = (Fraction(value) for value in rect)
    scaled = (left * unit, top * unit, width * unit / w, height * unit / h)
    if any(value.denominator != 1 for value in scaled):
        raise ValueError("the rectangle does not fall on the grid of 1 / (2 * w * h) source pixel")
    x0, y0, dx, dy = (int(value) for value in scaled)
    area = dx * dy
    if area <= 0:
        raise ValueError("the rectangle has no area")
    if 511 * area >= 2 ** 63:
        raise errors.Rejection(
            errors.UNREADABLE_MEDIA, f"a picture of {columns} x {rows} is too large for a canvas of {w} x {h}"
        )

    across = numpy.zeros((w, columns), dtype=numpy.int64)
    for c in range(w):
        first, weights = _shares(x0 + c * dx, dx, columns, unit)
        across[c, first:first + len(weights)] = weights

    canvas_rows = []
    for r in range(h):
        first, weights = _shares(y0 + r * dy, dy, rows, unit)
        band = picture[first:first + len(weights)].astype(numpy.int64)
        down = numpy.tensordot(numpy.array(weights, dtype=numpy.int64), band, axes=1)
        sums = across @ down
        canvas_rows.append(((2 * sums + area) // (2 * area)).astype(numpy.uint8).tobytes())
    return b"".join(reversed(canvas_rows))


def _shares(start, length, count, unit):
    """The source pixels that the slice from `start` to `start + length` covers.

    Lengths are in units of 1 / `unit` source pixel. The result is the index of the first
    pixel and, for it and each one after it, the length it shares with the slice.
    """
    end = start + length
    first = max(0, start // unit)
    last = min(count, -(-end // unit))
    weights = [min(end, (index + 1) * unit) - max(start, index * unit) for index in range(first, last)]
    return first, weights


def _gif_frames(path):
    """The frames of a GIF file, gone through once, each shown for the delay the file records."""
    import numpy
    from PIL import Image

    try:
        with Image.open(path, formats=["GIF"]) as image:
            start = Fraction(0)
            for index in range(getattr(image, "n_frames", 1)):
                image.seek(index)
                delay = image.info.get("duration", 0)
                if delay <= SHORTEST_GIF_DELAY_MS:
                    delay = GIF_DELAY_MS
                end = start + Fraction(delay)
                yield start, end, _over_black(numpy.asarray(image.convert("RGBA")))
                start = end
    except (OSError, EOFError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
        raise errors.Rejection(errors.UNREADABLE_MEDIA, f"the GIF cannot be decoded: {error}") from None


def _video_frames(path):
    """The frames of the first video stream, timed from the first of them.

    A frame is on screen until the next one starts. The last one stays for the mean interval
    between the frames, or for 20 ms when it is the only one.
    """
    import av

    try:
        with av.open(os.fspath(path)) as container:
            if not container.streams.video:
                raise errors.Rejection(errors.UNREADABLE_MEDIA, "the file has no video stream")
            stream = container.streams.video[0]
            if stream.codec_context is None:
                raise errors.Rejection(errors.UNREADABLE_MEDIA, "the video stream has no decoder")
            first = None
            held = None
            count = 0
            for frame in container.decode(stream):
                if frame.pts is None:
                    raise errors.Rejection(errors.UNREADABLE_MEDIA, "a frame has no presentation time")
                if first is None:
                    first = frame.pts
                time = (frame.pts - first) * stream.time_base * 1000
                picture = _over_black(frame.to_ndarray(format="rgba"))
                if held is not None:
                    if time < held[0]:
                        raise errors.Rejection(errors.UNREADABLE_MEDIA, "the frames are not in the order of their times")
                    yield held[0], time, held[1]
                held = (time, picture)
                count += 1
            if held is not None:
                interval = held[0] / (count - 1) if count > 1 else Fraction(TICK_MS)
                yield held[0], held[0] + interval, held[1]
    except av.error.FFmpegError as error:
        raise errors.Rejection(errors.UNREADABLE_MEDIA, f"the video cannot be decoded: {error}") from None


def _over_black(rgba):
    """A picture with an alpha channel laid over black: a transparent pixel becomes black."""
    import numpy

    if rgba.shape[0] == 0 or rgba.shape[1] == 0:
        raise errors.Rejection(errors.UNREADABLE_MEDIA, "a picture has no pixels")
    colour = rgba[..., :3]
    alpha = rgba[..., 3:]
    if alpha.min() == 255:
        return numpy.ascontiguousarray(colour)
    return ((colour.astype(numpy.uint16) * alpha + 127) // 255).astype(numpy.uint8)


_READERS = {".gif": _gif_frames, ".mp4": _video_frames, ".mov": _video_frames}

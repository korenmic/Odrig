"""import: putting the picture of a media file on the canvas.

This is the only module that needs third-party libraries. It loads them inside its
functions, so the rest of the tool runs with the Python standard library alone.

A source picture is a numpy array of rows x columns x 3 bytes, the top row first. A canvas
picture is `bytes` in the pixel order of docs/format.md, the bottom row first.
"""

from fractions import Fraction

from . import errors

FITS = ("fill", "fit", "stretch")


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

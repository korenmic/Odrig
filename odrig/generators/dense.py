"""Dense: a full-colour test clip in which every pixel is lit and changes all the time.

It is the worst case for the codec: no pixel stays the same from one 20 ms tick to the
next, and the clip has far more than 256 colours. The clip is generated when it is needed.
"""

import colorsys
import sys
from math import cos, hypot, sin

from . import run

FRAME_MS = 20
TICKS_PER_SECOND = 50
DEFAULT_SECONDS = 10


def colour(x, y, height, t):
    """The colour of canvas pixel (x, y) at time `t` in seconds."""
    u = x - 1
    w = height - y
    ax = 30 + 22 * sin(t * 0.61)
    ay = 15 + 11 * cos(t * 0.47)
    v1 = sin(u * 0.115 + t * 1.3)
    v2 = sin(u * 0.061 + w * 0.173 - t * 0.9)
    d = hypot(u - ax, (w - ay) * 1.6)
    v3 = sin(d * 0.21 - t * 2.1)
    hue = (0.5 + 0.22 * v1 + 0.22 * v2 + 0.11 * v3 + t * 0.07) % 1.0
    sat = 0.78 + 0.22 * sin(u * 0.047 - w * 0.091 + t * 0.7)
    val = 0.62 + 0.38 * sin(d * 0.13 + v2 * 1.1 + t * 1.6)
    return bytes(round(channel * 255) for channel in colorsys.hsv_to_rgb(hue, sat, val))


def frames(width, height, seconds=DEFAULT_SECONDS):
    """One frame for every 20 ms tick of `seconds` seconds."""
    result = []
    for tick in range(TICKS_PER_SECOND * seconds):
        t = tick / TICKS_PER_SECOND
        picture = b"".join(
            colour(x, y, height, t) for y in range(1, height + 1) for x in range(1, width + 1)
        )
        result.append((FRAME_MS, picture))
    return result


def _whole_seconds(text):
    seconds = int(text)
    if seconds < 1:
        raise ValueError("the length is at least 1 second")
    return seconds


def _configure(parser):
    parser.add_argument(
        "--seconds",
        type=_whole_seconds,
        default=DEFAULT_SECONDS,
        metavar="N",
        help=f"the length of the clip in whole seconds (default {DEFAULT_SECONDS})",
    )


def main(argv=None):
    return run(
        "dense",
        "Writes the dense full-colour test clip.",
        lambda width, height, arguments: frames(width, height, arguments.seconds),
        argv,
        _configure,
    )


if __name__ == "__main__":
    sys.exit(main())

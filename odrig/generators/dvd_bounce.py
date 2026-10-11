"""DVD bounce: a 2 x 2 square that crosses the canvas diagonally and turns back at every edge.

The rainbow does not move: the square shows the colours of the pixels it covers.
"""

import math
import sys

from .. import errors
from . import picture, rainbow, run

SIZE = 2
FRAME_MS = 180


def bounce(step, span):
    """The position after `step` one-pixel moves between two walls `span` apart."""
    step %= 2 * span
    return step if step <= span else 2 * span - step


def square(step, width, height):
    """The left column and the top row of the square in frame `step`."""
    return 1 + bounce(step, width - SIZE), height - bounce(step, height - SIZE)


def frames(width, height):
    if width <= SIZE or height <= SIZE:
        raise errors.Rejection(
            errors.CANVAS_TOO_SMALL,
            f"DVD bounce needs {SIZE + 1} x {SIZE + 1} and the canvas is {width} x {height}",
        )
    count = math.lcm(2 * (width - SIZE), 2 * (height - SIZE))
    result = []
    for step in range(count):
        left, top = square(step, width, height)
        pixels = {
            (x, y): rainbow.colour(x, y, width, height)
            for x in range(left, left + SIZE)
            for y in range(top - SIZE + 1, top + 1)
        }
        result.append((FRAME_MS, picture(width, height, pixels)))
    return result


def main(argv=None):
    return run("dvd_bounce", "Writes the DVD bounce animation.", lambda width, height, _: frames(width, height), argv)


if __name__ == "__main__":
    sys.exit(main())

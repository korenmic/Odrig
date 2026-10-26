"""Lines test: one white column at a time, from left to right."""

import sys

from . import picture, run

WHITE = bytes((255, 255, 255))
FRAME_MS = 200


def frames(width, height):
    """One frame per column, each with its complete column lit."""
    return [
        (FRAME_MS, picture(width, height, {(column, row): WHITE for row in range(1, height + 1)}))
        for column in range(1, width + 1)
    ]


def main(argv=None):
    return run("lines_test", "Writes the lines test animation.", lambda width, height, _: frames(width, height), argv)


if __name__ == "__main__":
    sys.exit(main())

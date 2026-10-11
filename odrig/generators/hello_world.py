"""Hello world: the words HELLO WORLD with a rainbow flowing through the letters.

The letters stand still. Their colours come from the canvas rainbow, which turns one hue
step every 20 ms frame and is back where it started after 255 frames.
"""

import sys

from .. import errors
from . import picture, rainbow, run

TEXT = "HELLO WORLD"
LETTER_GAP = 1
WORD_GAP = 4
FRAME_MS = 20

# Six rows for each letter, the top row first.
FONT = {
    "H": ("X..X", "X..X", "XXXX", "X..X", "X..X", "X..X"),
    "E": ("XXXX", "X...", "XXX.", "X...", "X...", "XXXX"),
    "L": ("X...", "X...", "X...", "X...", "X...", "XXXX"),
    "O": (".XX.", "X..X", "X..X", "X..X", "X..X", ".XX."),
    "W": ("X...X", "X...X", "X...X", "X.X.X", "XX.XX", "X...X"),
    "R": ("XXX.", "X..X", "X..X", "XXX.", "X.X.", "X..X"),
    "D": ("XXX.", "X..X", "X..X", "X..X", "X..X", "XXX."),
}
ROWS = 6


def text_cells():
    """The lit cells of the text as (column, row) from its top-left corner, and its width."""
    cells = []
    column = 0
    for word_number, word in enumerate(TEXT.split(" ")):
        if word_number:
            column += WORD_GAP - LETTER_GAP
        for letter in word:
            glyph = FONT[letter]
            for row, line in enumerate(glyph):
                cells += [(column + offset, row) for offset, mark in enumerate(line) if mark == "X"]
            column += len(glyph[0]) + LETTER_GAP
    return cells, column - LETTER_GAP


def lit_pixels(width, height):
    """The canvas pixels (x, y) of the text, centred on the canvas."""
    cells, text_width = text_cells()
    if width < text_width or height < ROWS:
        raise errors.Rejection(
            errors.CANVAS_TOO_SMALL,
            f"Hello world needs {text_width} x {ROWS} and the canvas is {width} x {height}",
        )
    left = (width - text_width) // 2
    above = (height - ROWS) // 2
    return [(left + column + 1, height - above - row) for column, row in cells]


def frames(width, height):
    lit = lit_pixels(width, height)
    result = []
    for step in range(rainbow.HUES):
        shift = (rainbow.HUES - step) % rainbow.HUES
        pixels = {(x, y): rainbow.colour(x, y, width, height, shift) for x, y in lit}
        result.append((FRAME_MS, picture(width, height, pixels)))
    return result


def main(argv=None):
    return run("hello_world", "Writes the Hello world animation.", lambda width, height, _: frames(width, height), argv)


if __name__ == "__main__":
    sys.exit(main())

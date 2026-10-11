"""Writes the small GIF that the walk-through imports: ten pictures of 40 x 30, each one
flat colour, shown for a tenth of a second each.

    python make_gif.py OUT.gif

It needs Pillow, which the Python of a set-up clone has.
"""

import sys

from PIL import Image

SIZE = (40, 30)
FRAME_MS = 100
COLOURS = (
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
    (128, 128, 128),
    (255, 128, 0),
    (0, 128, 255),
)


def write(path):
    images = [Image.new("RGB", SIZE, colour) for colour in COLOURS]
    images[0].save(path, save_all=True, append_images=images[1:], duration=FRAME_MS, loop=0)


if __name__ == "__main__":
    write(sys.argv[1])

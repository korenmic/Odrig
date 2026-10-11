"""The rainbow shared by Hello world and DVD bounce.

The rainbow is fixed to the canvas: the hue circle runs once from left to right and is
moved a little on each row, which gives diagonal bands. A shift turns the hues.
"""

import colorsys

HUES = 255

COLOURS = [
    bytes(round(channel * 255) for channel in colorsys.hsv_to_rgb(index / HUES, 1, 1))
    for index in range(HUES)
]


def colour(x, y, width, height, shift=0):
    """The rainbow colour of canvas pixel (x, y)."""
    hue = ((x - 1) / width + (height - y) / (4 * height)) % 1.0
    return COLOURS[(int(hue * HUES) + shift) % HUES]

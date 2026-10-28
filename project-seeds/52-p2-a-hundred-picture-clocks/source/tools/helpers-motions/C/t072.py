"""Tile 72, a tuning fork humming: on both sides its waves light one after another, inner,
middle, outer, then again.

The arcs are nested and their tips curl over one another, so no rectangle holds one arc
alone. Each step therefore first lends the light tones (6, 7) of the arcs that stay lit to
indices the region does not use (1, 4), hides every wave pixel left on each side, and gives
the lent tones back."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import *

entry, pic = load(72)
set_pixels(pic, [(37, 35)], 2)  # the one pixel of index 1 inside the lit region: background

LEND = [[6, 1], [7, 4]]
BACK = [[1, 6], [4, 7]]
HIDE = [[5, 3], [6, 3], [7, 3]]  # an unlit wave: the purple glow it sits in
INNER = bx(16, 20, 44, 33)       # the inner arcs of both sides (and the fork between them)
MIDDLE = bx(13, 17, 47, 37)      # the inner and middle arcs of both sides
STEP = 400
parts = [
    flicker(INNER, [LEND, [], []], STEP),
    flicker(MIDDLE, [[], LEND, []], STEP),
    flicker(bx(6, 8, 22, 43), [HIDE, HIDE, []], STEP),    # the waves on the left
    flicker(bx(36, 8, 56, 43), [HIDE, HIDE, []], STEP),   # the waves on the right
    flicker(INNER, [BACK, [], []], STEP),
    flicker(MIDDLE, [[], BACK, []], STEP),
]
save(entry, pic, motion(parts, seconds=12))

"""Tile 12, an incense spiral smoking: a brighter puff rises through the smoke in three
steps, and the ember at the top of the spiral glows brighter and dimmer."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import *

entry, pic = load(12)
PUFF = [[2, 4]]           # the smoke of a band lit: its dark grey becomes the light grey
DIM = [[4, 2], [2, 1]]    # the smoke of a band thinned
STEP = 400
parts = [
    flicker(bx(22, 11, 43, 17), [PUFF, DIM, []], STEP),   # the smoke low over the ember
    flicker(bx(22, 6, 43, 11), [[], PUFF, DIM], STEP),    # the smoke in the middle
    flicker(bx(22, 0, 43, 6), [DIM, [], PUFF], STEP),     # the smoke at the top
    flicker(bx(28, 16, 33, 20), [[[6, 7], [5, 6]], [], [[7, 6], [6, 5]]], STEP),  # the ember
]
save(entry, pic, motion(parts, seconds=12))

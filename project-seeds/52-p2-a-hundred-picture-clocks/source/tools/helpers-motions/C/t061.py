"""Tile 61, a calendar page: the day, 27, blinks slowly between black and the red of the
page's top, as the date of today."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import *

entry, pic = load(61)
RED = [[0, 3], [1, 3], [2, 3]]  # the dark of the digits becomes red
parts = [
    flicker(bx(23, 38, 40, 51), [[], RED], 1000),   # the digits 27
]
save(entry, pic, motion(parts, seconds=12))

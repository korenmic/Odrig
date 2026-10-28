"""Tile 63, a date drum: a shaded band runs down the three drums' faces, again and again,
as if they rolled."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import *

entry, pic = load(63)
SHADE = [[7, 6], [6, 5]]  # the band in shade: cream to tan, tan to brown
STEP = 400
parts = [
    flicker(bx(12, 8, 52, 17), [SHADE, [], []], STEP),    # the drums' upper band
    flicker(bx(12, 17, 52, 26), [[], SHADE, []], STEP),   # the middle band
    flicker(bx(12, 26, 52, 35), [[], [], SHADE], STEP),   # the lower band
]
save(entry, pic, motion(parts, seconds=12))

"""Tile 65, a display of the phases of the moon: its three large moons light one after
another, crescent, half, gibbous; the two that are not lit go dull."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import *

entry, pic = load(65)
D = [[7, 5], [6, 4]]  # a moon not lit: its cream and beige become greys
STEP = 800
parts = [
    flicker(bx(8, 16, 22, 34), [[], D, D], STEP),    # the crescent
    flicker(bx(23, 16, 38, 34), [D, [], D], STEP),   # the half moon
    flicker(bx(38, 16, 55, 34), [D, D, []], STEP),   # the gibbous moon
]
save(entry, pic, motion(parts, seconds=12))

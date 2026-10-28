"""Tile 62, a desk calendar: the day, TUE, blinks slowly between white and a dark brown."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import *

entry, pic = load(62)
DULL = [[7, 4], [5, 3]]  # the letters' white and their tan edges go dark brown
parts = [
    flicker(bx(20, 26, 38, 35), [[], DULL], 1000),   # the letters TUE
]
save(entry, pic, motion(parts, seconds=12))

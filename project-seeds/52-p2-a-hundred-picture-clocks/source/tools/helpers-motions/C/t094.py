"""Tile 94, a solar panel under the sun: the sun's rays flare, their grey turning to the
sun's cream, and settle, every 1.2 seconds."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import *

entry, pic = load(94)
FLARE = [[4, 7]]  # the grey of the rays becomes the sun's cream
parts = [
    flicker(bx(37, 2, 59, 25), [[], FLARE], 600),   # the sun and its rays
]
save(entry, pic, motion(parts, seconds=12))

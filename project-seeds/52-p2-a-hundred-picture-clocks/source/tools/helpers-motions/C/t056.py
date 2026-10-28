"""Tile 56, the moon in two phases: the two moons take turns, the full moon dimming slowly
while the crescent brightens, and back."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import *

entry, pic = load(56)
D1 = [[7, 6]]
D2 = [[7, 6], [6, 5]]
D3 = [[7, 6], [6, 5], [5, 4]]
FULL = [[], D1, D2, D3]        # the full moon from bright to dim
CRESCENT = [D3, D2, D1, []]    # the crescent from dim to bright
parts = [
    pulse(bx(24, 7, 58, 43), FULL),        # the full moon
    pulse(bx(6, 14, 23, 51), CRESCENT),    # the crescent
    pulse(bx(23, 43, 29, 50), CRESCENT),   # the crescent's lower tip
]
save(entry, pic, motion(parts, seconds=12))

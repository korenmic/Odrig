"""Tile 96, an atom: the six electrons on the purple orbit light two at a time, opposite
each other, each step one place further round the orbit, the places just left fading
(purple, then blue): two electrons circle it with a trail."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

entry, pic = load(96)
# the electrons on the purple orbit, round it from the top right: their boxes x0, y0, x1, y1
ELECTRONS = [(41, 6, 46, 11), (24, 13, 29, 19), (13, 30, 19, 35), (15, 46, 20, 52), (28, 40, 33, 45), (41, 28, 45, 33)]
parts = []
for k, (x0, y0, x1, y1) in enumerate(ELECTRONS):
    print(k, counts(pic, (x0, y0, x1, y1)))
    look = {k % 3: [], (k + 1) % 3: [[7, 5]], (k + 2) % 3: [[7, 4]]}
    parts.append(flicker(bx(x0, y0, x1, y1), [look[v] for v in range(3)], 250))
if __name__ == "__main__":
    save(entry, pic, motion(parts, seconds=12, frame_ms=50))

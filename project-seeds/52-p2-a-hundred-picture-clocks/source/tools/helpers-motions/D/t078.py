"""Tile 78, a drum machine: lit pads chase across the upper two rows of pads."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

entry, pic = load(78)
# the upper two rows of pads, made clean unlit pads: a top edge of 6 and a face of 4
COLS = [(7, 13), (16, 22), (24, 29), (31, 37), (39, 45), (48, 52)]
ROWS = [(32, 37), (38, 43)]
for (x0, x1) in COLS:
    for (y0, y1) in ROWS:
        fill_box(pic, (x0, y0, x1, y1), 4)
        fill_box(pic, (x0, y0, x1, y0 + 1), 6)
fill_box(pic, (13, 32, 14, 43), 2)
PHASE = [0, 1, 2, 0, 1, 2]
parts = []
for (x0, x1), ph in zip(COLS, PHASE):
    box = bx(x0, 32, x1, 43)
    lit = [[4, 5], [6, 5]] if x0 == 48 else [[4, 7], [6, 7]]
    parts.append(flicker(box, [lit if v == ph else [] for v in range(3)], 250))
if __name__ == "__main__":
    print(grid(pic, (4, 30, 56, 51)))
    save(entry, pic, motion(parts, seconds=12, frame_ms=50))

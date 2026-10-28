"""Tile 73, a music box: small notes rise from the open box, one after another."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

entry, pic = load(73)
NOTE = ["..7..",
        "..77.",
        "..7.7",
        "..7..",
        "777..",
        "776..",
        ".6..."]
SPOTS = [(26, 11), (31, 6), (36, 1)]
boxes = []
for (x0, y0) in SPOTS:
    for j, row in enumerate(NOTE):
        for i, ch in enumerate(row):
            if ch != ".":
                pic[y0 + j, x0 + i] = int(ch)
    boxes.append(bx(x0, y0, x0 + 5, y0 + 7))
for b in boxes:
    x0, y0, w, h = b
    print(b, counts(pic, (x0, y0, x0 + w, y0 + h)))
HIDE = [[7, 3], [6, 3]]
parts = []
for k, b in enumerate(boxes):
    variants = [[] if v == k else HIDE for v in range(3)]
    parts.append(flicker(b, variants, 400))
if __name__ == "__main__":
    print(grid(pic, (20, 0, 55, 20)))
    save(entry, pic, motion(parts, seconds=12, frame_ms=50))

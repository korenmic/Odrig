"""Tile 95, a zen garden with a ball: the raked rings, redrawn about the ball in three bands
(a dark groove and two of sand) that keep the grain of the picture, travel outward from
the ball: a flicker steps each band to the next."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *
import math

entry, pic = load(95)
ys, xs = numpy.nonzero(pic[15:40, 20:40] == 0)
CX, CY = xs.mean() + 20 + 0.5, ys.mean() + 15 + 0.5
print("ball", CX, CY)
PX, PY = 7.0, 5.5          # the spacing of the rings, across and up and down
SAND = (1, 3, 4, 5, 6, 7)
# each band two shades, the grain of the picture choosing between them
BANDS = [(1, 3), (4, 6), (5, 7)]
for y in range(59):
    for x in range(60):
        v = pic[y, x]
        if v not in SAND:
            continue
        rho = math.hypot((x + 0.5 - CX) / PX, (y + 0.5 - CY) / PY)
        band = int(3 * (rho % 1.0))
        grain = 0 if v in (1, 4, 5) else 1
        pic[y, x] = BANDS[band][grain]
# outward: a pixel of band c shows the colours of band c - 1, then c - 2
V1 = [[1, 5], [3, 7], [4, 1], [6, 3], [5, 4], [7, 6]]
V2 = [[1, 4], [3, 6], [4, 5], [6, 7], [5, 1], [7, 3]]
parts = [flicker(bx(0, 3, 60, 59), [[], V1, V2], 500)]
if __name__ == "__main__":
    view(pic, entry, "v095b.png", scale=10)
    save(entry, pic, motion(parts, seconds=12, frame_ms=50))

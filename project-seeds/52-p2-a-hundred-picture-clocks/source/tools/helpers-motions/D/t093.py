"""Tile 93, a water wheel: the wheel, drawn with its hub off the rim's centre, is redrawn
about one centre (the rim tan as it was, 8 brown spokes inside it) and its spokes turn;
the stream and the splash flicker."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *
import math

entry, pic = load(93)
before = pic.copy()
C = 27.5                   # the centre of pixel (27, 27), both ways
R_IN, R_OUT = 15.0, 20.5
WATER = (3, 5, 7)


def d_of(x, y):
    return math.hypot(x + 0.5 - C, y + 0.5 - C)


# the old wheel: its tan and brown around the centre, out to past its rim, becomes wall
for y in range(0, 52):
    for x in range(0, 52):
        d = d_of(x, y)
        if d <= 23 and pic[y, x] in (6, 4) and not R_IN <= d <= R_OUT:
            pic[y, x] = 1 if d > R_OUT else 0
        if d < R_IN and pic[y, x] not in WATER:
            pic[y, x] = 0
# the rim: tan, its inner edge dark; the water in front stays
for y in range(60):
    for x in range(60):
        d = d_of(x, y)
        if R_IN <= d <= R_OUT and pic[y, x] not in WATER:
            pic[y, x] = 2 if d < R_IN + 1.0 else 6
# the hub and the spokes
for y in range(60):
    for x in range(60):
        u, v = x + 0.5 - C, y + 0.5 - C
        d = math.hypot(u, v)
        if d <= 3.3:
            pic[y, x] = 6
        elif d < R_IN:
            for k in range(8):
                a = math.radians(k * 45)
                if abs(u * math.cos(a) + v * math.sin(a)) <= 1.5:
                    pic[y, x] = 4
pic[27, 27] = 2
# only the spokes are 4 in the box of the turn
BOX = bx(12, 12, 43, 43)
assert all(pic[y, x] != 4 or d_of(x, y) < R_IN for y in range(12, 43) for x in range(12, 43))

parts = [
    turn(BOX, [4], 0, [55, 55], 90),
    # the stream down the right of the wheel
    flicker(bx(44, 12, 54, 42), [[], [[5, 3], [3, 5]], [[5, 7], [7, 5]]], 100),
    # the splash where wheel and stream meet the pool
    flicker(bx(40, 39, 58, 47), [[], [[7, 5], [5, 7]]], 200),
]
if __name__ == "__main__":
    print(grid(pic, (0, 0, 60, 52)))
    view(pic, entry, "v093b.png", scale=10)
    save(entry, pic, motion(parts, seconds=12, frame_ms=50))

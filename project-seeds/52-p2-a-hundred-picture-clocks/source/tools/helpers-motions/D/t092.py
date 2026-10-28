"""Tile 92, gears: the big gear and the top gear turn about their hubs, opposite ways,
whole turns per loop so that the loop has no jump. The right gear, cut by the edge of the
picture, and the small gear, deep in the big gear's teeth, stay: turning them would tear
holes in the turning gears. The turning gears have colours of their own so that a box
holds no other gear's moving pixels: the big gear light (7) with dark edges (4), the top
gear orange (6); the others brown (5). The big gear, drawn 39 high and 35 wide, is made
round, and the top gear is moved 2 pixels up and 1 right, clear of the big gear's teeth."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *
import math

entry, pic = load(92)
# name: centre in half pixels, outer radius in pixels
GEARS = {"big": ((39, 69), 18.0), "top": ((71, 27), 10.5), "small": ((68, 102), 8.0), "right": ((105, 70), 16.0)}


def dist(x, y, centre):
    cx, cy = centre
    return math.hypot((2 * x + 1 - cx) / 2, (2 * y + 1 - cy) / 2)


owner = {}
for y in range(60):
    for x in range(60):
        best = min(GEARS, key=lambda n: dist(x, y, GEARS[n][0]) / GEARS[n][1])
        d = dist(x, y, GEARS[best][0]) / GEARS[best][1]
        if d <= 1.1:
            owner[(x, y)] = best
for (x, y), name in owner.items():
    v = pic[y, x]
    if v in (4, 5, 6, 7):
        if name == "big":
            pic[y, x] = 7 if v in (6, 7) else 4
        elif name == "top":
            pic[y, x] = 6
        else:
            pic[y, x] = 5
    else:
        pic[y, x] = 3


# the big gear is drawn 39 high and 35 wide: squashed to a circle about its hub, so
# that it turns without wobbling
(BX, BY), _ = GEARS["big"]
bcx, bcy = BX / 2, BY / 2
SQUASH = 35 / 39
before = pic.copy()
big = {(x, y) for (x, y), n in owner.items() if n == "big"}
for (x, y) in big:
    if pic[y, x] in (7, 4):
        pic[y, x] = 3
for y in range(60):
    for x in range(60):
        sy = int(math.floor(bcy + (y + 0.5 - bcy) / SQUASH))
        if 0 <= sy < 60 and (x, sy) in big and before[sy, x] in (7, 4):
            pic[y, x] = before[sy, x]
GEARS["big"] = (GEARS["big"][0], 17.6)
# the top gear: 1 right and 2 up
top = [(x, y) for (x, y), n in owner.items() if n == "top" and pic[y, x] == 6]
for (x, y) in top:
    pic[y, x] = 3
for (x, y) in top:
    pic[y - 2, x + 1] = 6
(TX, TY), TR = GEARS["top"]
GEARS["top"] = ((TX + 2, TY - 4), TR)


def box_of(name, margin=1):
    (cx, cy), r = GEARS[name]
    x0 = max(0, int(math.floor(cx / 2 - r - margin)))
    y0 = max(0, int(math.floor(cy / 2 - r - margin)))
    x1 = min(60, int(math.ceil(cx / 2 + r + margin)))
    y1 = min(60, int(math.ceil(cy / 2 + r + margin)))
    return bx(x0, y0, x1, y1)


parts = [
    turn(box_of("big"), [7, 4], 3, list(GEARS["big"][0]), 360),
    turn(box_of("top"), [6], 3, list(GEARS["top"][0]), -720),
]
for part in parts:
    print(part["box"])
if __name__ == "__main__":
    view(pic, entry, "v092b.png", scale=10)
    save(entry, pic, motion(parts, seconds=12, frame_ms=50))

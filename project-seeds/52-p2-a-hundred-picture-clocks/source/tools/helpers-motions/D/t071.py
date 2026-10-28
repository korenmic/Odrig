"""Tile 71, a metronome: the arm redrawn upright about its pivot, and swung."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

entry, pic = load(71)
orig = pic.copy()


def edge(y):
    return min(45, 38 + (y - 12) / 3)


# the arm of the picture, tilted: erase it (body behind it dark 1, the wall 4)
ax0, ay0, ax1, ay1 = 37.5, 39.0, 48.0, 11.0
for y in range(9, 40):
    for x in range(34, 52):
        # distance from the line of the arm
        dx, dy = ax1 - ax0, ay1 - ay0
        t = ((x - ax0) * dx + (y - ay0) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        dist = ((x - ax0 - t * dx) ** 2 + (y - ay0 - t * dy) ** 2) ** 0.5
        if dist > 3.2:
            continue
        v = orig[y, x]
        if x > edge(y):
            pic[y, x] = 4
        elif v in (7, 5):
            pic[y, x] = 1
# the wall right of the body: clean of the old arm's outline and shadow
for y in range(9, 39):
    for x in range(34, 55):
        if x > edge(y) and pic[y, x] != 4:
            pic[y, x] = 4
        elif 39 <= x <= edge(y) and y >= 18 and pic[y, x] in (2, 3):
            pic[y, x] = 1
# the scale in the middle of the front: grey, so that only the arm is light in the box
replace_box(pic, (26, 9, 32, 40), {7}, 5)
# the new arm: upright, 2 wide, its weight near the top
for y in range(18, 40):
    pic[y, 37] = 7
    pic[y, 38] = 7
for y in range(12, 18):
    for x in range(36, 40):
        pic[y, x] = 7
pic[11, 37] = pic[11, 38] = 7

BOX = bx(25, 9, 52, 40)
others = [(x, y) for y in range(9, 40) for x in range(25, 52) if pic[y, x] == 7 and not (36 <= x <= 39 and 11 <= y <= 39)]
print("other 7s in the box:", others)
parts = [swing(BOX, [7], 1, [76, 79], 20, 9)]
if __name__ == "__main__":
    print(grid(pic, (20, 6, 55, 42)))
    view(pic, entry, "v071.png")
    save(entry, pic, motion(parts, seconds=12, frame_ms=50))

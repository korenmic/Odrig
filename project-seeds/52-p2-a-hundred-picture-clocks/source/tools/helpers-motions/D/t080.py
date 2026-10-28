"""Tile 80, a spinner of dots: redrawn as 8 clean dots that a turn steps by exactly one
dot (45 degrees) each frame, so that every frame shows the same clean dots."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *
from rot import rotate
import math

entry, pic = load(80)
X0, Y0, X1, Y1 = 8, 9, 52, 54
# the background: one navy (1 and 2 are nearly the same) under and about the ring
pic[pic == 2] = 1
fill_box(pic, (X0, Y0, X1, Y1), 1)
CXH, CYH = 60, 62            # the centre at a pixel corner, in half pixels
R, DOT = 14.0, 3.6
cx, cy = CXH / 2, CYH / 2
# clockwise from the top: dark at the left and up, blue at the top and right, light below,
# the head (the last light) leading clockwise
COLOURS = {0: 5, 45: 5, 90: 5, 135: 7, 180: 7, 225: 7, 270: 3, 315: 3}
axis = numpy.ones((60, 60), dtype=numpy.int16)
for deg in (0, 90, 180, 270):
    a = math.radians(deg)
    dx, dy = cx + R * math.sin(a), cy - R * math.cos(a)
    for y in range(60):
        for x in range(60):
            if math.hypot(x + 0.5 - dx, y + 0.5 - dy) <= DOT:
                axis[y, x] = 10 + deg // 45
box = bx(X0, Y0, X1, Y1)
diag = rotate(axis, box, [10, 12, 14, 16], 1, [CXH, CYH], 45)
for y in range(60):
    for x in range(60):
        if axis[y, x] >= 10:
            pic[y, x] = COLOURS[(axis[y, x] - 10) * 45]
        elif diag[y, x] >= 10:
            pic[y, x] = COLOURS[((diag[y, x] - 10) * 45 + 45) % 360]
parts = [turn(box, [3, 5, 7], 1, [CXH, CYH], 3600)]
if __name__ == "__main__":
    print(grid(pic, (X0, Y0, X1, Y1)))
    save(entry, pic, motion(parts, seconds=12, frame_ms=150))

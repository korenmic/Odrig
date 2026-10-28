import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions/A")
from hg import *

entry, pic = load(79)
TOP = (24, 18, 38, 24)       # the upper glass below its light band, rows 18..23
BOTTOM = (24, 28, 37, 37)    # the lower glass, rows 28..36
# the light anti-aliasing just outside the white walls is the navy face, so that the
# levels take only what is inside the walls
for box, seed in ((TOP, (30, 19)), (BOTTOM, (33, 31))):
    m = vessel(pic, [seed], {4, 5}, box)
    for x, y, _ in strays(pic, box, [4, 5], m):
        pic[y, x] = 4
# the stream down the middle (x 30), from the neck to the bottom: white grains
for y in range(24, 37):
    pic[y, 30] = (7, 5, 4)[y % 3]
parts = [
    level(bx(8, 46, 53, 51), [6, 0, 1], 6, 1, "left", 40, 100),   # the progress bar
    level(bx(*TOP), [4, 5], 5, 4, "bottom", 67, 0),
    flicker(bx(30, 24, 31, 37), stream_variants(7, 5, 4), 100),
    level(bx(*BOTTOM), [4, 5], 5, 4, "bottom", 23, 85),
    level(bx(30, 28, 31, 37), [7], 5, 7, "bottom", 23, 85),
]
save(entry, pic, motion(parts))

import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions/A")
from hg import *

entry, pic = load(5)
# The outer edge of the glass in index 4 (the glass colour) becomes the dark outline 2,
# so that only the inside of the glass is the vessel.
set_pixels(pic, [(25, 25), (33, 25), (34, 24), (35, 23), (36, 22), (37, 36), (38, 37)], 2)
# The stream: 2 px, from the neck down into the bottom chamber.
draw_stream(pic, (29, 30), 27, 50, (5, 3, 6))
TOP = (25, 10, 43, 27)
BOTTOM = (23, 31, 44, 50)
if __name__ == "__main__":
    for b, seed in ((TOP, (30, 12)), (BOTTOM, (33, 40))):
        m = vessel(pic, [seed], {3, 4, 5, 6}, b)
        print(strays(pic, b, [3, 4, 5], m))
parts = [
    flicker(bx(29, 27, 31, 50), stream_variants(5, 3, 6), 100),
    level(bx(*TOP), [4, 5], 5, 4, "bottom", 71, 6),
    level(bx(*TOP), [3], 3, 4, "bottom", 71, 6),
    level(bx(*BOTTOM), [4], 5, 4, "bottom", 32, 85),
    level(bx(29, 31, 31, 50), [3], 5, 3, "bottom", 32, 85),
    level(bx(29, 31, 31, 50), [6], 5, 6, "bottom", 32, 85),
]
save(entry, pic, motion(parts))

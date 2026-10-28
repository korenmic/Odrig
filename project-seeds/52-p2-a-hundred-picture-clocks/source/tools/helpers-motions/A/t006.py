import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions/A")
from hg import *

entry, pic = load(6)
# dark specks in the sand become sand shading so that the levels take them
set_pixels(pic, [(14, 49), (15, 49), (13, 50), (14, 50), (15, 50), (52, 41), (51, 42), (52, 42)], 3)
IN = [3, 4, 5, 7]   # sand and dark glass; 6 (the glass's light reflections) stays
LEFT_TOP, LEFT_BOTTOM = (5, 22, 19, 34), (4, 38, 19, 51)
MID_TOP, MID_BOTTOM = (26, 18, 39, 30), (26, 34, 39, 47)
RIGHT_TOP, RIGHT_BOTTOM = (45, 18, 56, 29), (44, 33, 56, 44)
FILL = {"left": 5, "mid": 7, "right": 7}
parts = [
    # the left glass has run out: its sand goes back up while the other two run
    level(bx(*LEFT_TOP), IN, FILL["left"], 4, "bottom", 0, 67),
    level(bx(*LEFT_BOTTOM), IN, FILL["left"], 4, "bottom", 55, 8),
    level(bx(*MID_TOP), IN, FILL["mid"], 4, "bottom", 67, 9),
    level(bx(*MID_BOTTOM), IN, FILL["mid"], 4, "bottom", 47, 90),
    level(bx(*RIGHT_TOP), IN, FILL["right"], 4, "bottom", 64, 10),
    level(bx(*RIGHT_BOTTOM), IN, FILL["right"], 4, "bottom", 46, 85),
]
save(entry, pic, motion(parts, seconds=12))

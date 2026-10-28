import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions")
from lib import *

entry, pic = load(4)
# The falling stream: a 3-colour pattern down x=29 from the neck to the sand.
for y in range(29, 47):
    if pic[y, 29] in (5, 6, 7):
        pic[y, 29] = (7, 6, 5)[y % 3]
top = bx(21, 15, 40, 29)       # top chamber, rows 15..28
bottom = bx(21, 32, 40, 47)    # bottom chamber, rows 32..46
parts = [
    flicker(bx(29, 29, 30, 47), [[], [[7, 5], [6, 7], [5, 6]], [[7, 6], [6, 5], [5, 7]]], 100),
    level(top, [5, 7], 7, 5, "bottom", 72, 8),
    level(top, [6, 4], 6, 5, "bottom", 72, 8),
    level(bottom, [5], 7, 5, "bottom", 40, 92),
    level(bx(29, 32, 30, 47), [6], 7, 6, "bottom", 40, 92),
]
save(entry, pic, motion(parts))

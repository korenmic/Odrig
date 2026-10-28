import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions/A")
from hg import *

entry, pic = load(88)
# The hourglass icon between its caps (rows 29..44) is a tangle at this size: it is drawn
# again as a clean icon of the same colours, a dark outline (1) about white glass (7) with
# dark sand (2), so that its sand can fall.
K = {29: 4, 30: 4, 31: 4, 32: 3, 33: 2, 34: 1, 35: 1, 36: 1, 37: 1, 38: 2, 39: 3, 40: 4, 41: 4, 42: 4, 43: 4, 44: 4}
for y in range(29, 45):
    for x in range(23, 38):
        pic[y, x] = 6
    k = K[y]
    for x in range(30 - k, 30 + k):
        pic[y, x] = 7
    pic[y, 29 - k] = 1
    pic[y, 30 + k] = 1
# the diagonal steps of the outline joined
for y in range(30, 44):
    for x in range(23, 38):
        if pic[y, x] == 7 and (pic[y - 1, x] == 6 or pic[y + 1, x] == 6):
            pic[y, x] = 1
# sand: the lower part of the upper glass, the floor of the lower glass
for y in range(30, 36):
    for x in range(23, 38):
        if pic[y, x] == 7:
            pic[y, x] = 2
for y in range(43, 45):
    for x in range(23, 38):
        if pic[y, x] == 7:
            pic[y, x] = 2
# the stream: phases 2, 4, 5 by y % 3 at x 29..30, shown as dark grains on white
for y in range(36, 45):
    for x in (29, 30):
        pic[y, x] = (2, 4, 5)[y % 3]
grains = [[[4, 2], [5, 7]], [[2, 7], [4, 2], [5, 2]], [[4, 7], [5, 2]]]
parts = [
    level(bx(24, 29, 36, 36), [7, 2], 2, 7, "bottom", 86, 0),
    flicker(bx(29, 36, 31, 45), grains, 100),
    level(bx(24, 37, 36, 45), [7], 2, 7, "bottom", 25, 88),
]
save(entry, pic, motion(parts))

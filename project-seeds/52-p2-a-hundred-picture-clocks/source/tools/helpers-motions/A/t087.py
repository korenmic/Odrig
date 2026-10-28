import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions/A")
from hg import *

entry, pic = load(87)
# the necks (x 30) carry phases 7, 6, 5 by y % 3, shown as falling grains of sand
for y in list(range(24, 28)) + list(range(39, 43)):
    pic[y, 30] = (7, 6, 5)[y % 3]
grains = [[[6, 7], [5, 2]], [[7, 2], [6, 7], [5, 7]], [[6, 2], [5, 7]]]
parts = [
    flicker(bx(30, 24, 31, 28), grains, 100),
    flicker(bx(30, 39, 31, 43), grains, 100),
    level(bx(25, 13, 37, 24), [6, 7], 7, 6, "bottom", 64, 10),
    level(bx(25, 28, 37, 39), [6, 7], 7, 6, "bottom", 45, 64),
    level(bx(25, 43, 38, 50), [6, 7], 7, 6, "bottom", 43, 100),
]
save(entry, pic, motion(parts))

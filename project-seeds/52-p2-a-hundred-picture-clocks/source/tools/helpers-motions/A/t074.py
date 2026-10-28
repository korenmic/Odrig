import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions/A")
from hg import *

entry, pic = load(74)
# the black specks in the blue sand become sand
replace_box(pic, (20, 17, 44, 48), {0}, 4)
# the stream, wavering between x 30 and 32 in the picture, becomes a straight column at
# x 31-32 from the neck to the bottom; x 30 below the neck becomes the glass's tan
for y in range(33, 41):
    if pic[y, 30] == 4:
        pic[y, 30] = 6
# phases of the stream: 4, 6, 7 by y % 3; the flicker shows them as blue with a cream glint
for y in range(29, 48):
    for x in (31, 32):
        pic[y, x] = (4, 6, 7)[y % 3]
glint = [[[6, 4]], [[4, 7], [6, 4], [7, 4]], [[6, 7], [7, 4]]]
TOP = (20, 17, 44, 29)
BOTTOM = (26, 33, 42, 48)
parts = [
    flicker(bx(31, 29, 33, 48), glint, 100),
    level(bx(*TOP), [4, 0], 4, 6, "bottom", 62, 8),
    level(bx(*BOTTOM), [6], 4, 6, "bottom", 47, 93),
    level(bx(31, 33, 33, 48), [7], 4, 7, "bottom", 47, 93),
]
save(entry, pic, motion(parts))

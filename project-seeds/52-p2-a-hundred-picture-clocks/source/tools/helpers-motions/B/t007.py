import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions"); from lib import *
entry, pic = load(7)
# the stream down the front at x=30: a repeating 7,6,5 pattern that a 3-variant flicker moves down
for y in range(30, 59):
    pic[y, 30] = [7, 6, 5][y % 3]
down1 = [[7, 5], [6, 7], [5, 6]]
down2 = [[7, 6], [6, 5], [5, 7]]
parts = [
    # the water in the bowl runs out (water 3, the bare inside 0)
    level(bx(9, 21, 49, 27), [0, 1, 3, 4], 3, 0, "bottom", 85, 17),
    flicker(bx(30, 30, 31, 59), [[], down1, down2], 100),
]
save(entry, pic, motion(parts, seconds=12, frame_ms=50))

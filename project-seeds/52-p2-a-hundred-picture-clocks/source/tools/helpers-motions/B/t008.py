import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions"); from lib import *
entry, pic = load(8)
# the stream from the upper bowl at x=28: a repeating 7,6,3 pattern that a 3-variant flicker moves down
for y in range(28, 39):
    pic[y, 28] = [7, 6, 3][y % 3]
down1 = [[7, 3], [6, 7], [3, 6]]
down2 = [[7, 6], [6, 3], [3, 7]]
parts = [
    # the upper bowl empties (water 3 over its dark inside 1), the lower one fills
    level(bx(24, 9, 48, 14), [0, 1], 3, 1, "bottom", 90, 10),
    level(bx(3, 34, 34, 39), [0, 1], 3, 1, "bottom", 10, 90),
    flicker(bx(28, 28, 29, 39), [[], down1, down2], 100),
]
save(entry, pic, motion(parts, seconds=12, frame_ms=50))

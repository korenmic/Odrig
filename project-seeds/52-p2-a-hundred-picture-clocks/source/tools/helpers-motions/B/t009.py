import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions"); from lib import *
entry, pic = load(9)
C = [7, 4, 3]
# the tap's stream (its right column x=25) and the overflow down the side (x=30): a repeating
# 7,4,3 pattern that a 3-variant flicker moves down
for y in range(12, 26):
    pic[y, 25] = C[y % 3]
for y in range(28, 48):
    pic[y, 30] = C[y % 3]
down1 = [[7, 3], [4, 7], [3, 4]]
down2 = [[7, 4], [4, 3], [3, 7]]
parts = [
    # the pot fills: its light face turns water-blue from the bottom up
    level(bx(5, 30, 19, 46), [7], 4, 7, "bottom", 10, 95),
    flicker(bx(25, 12, 26, 26), [[], down1, down2], 100),
    flicker(bx(30, 28, 31, 48), [[], down1, down2], 100),
]
save(entry, pic, motion(parts, seconds=15, frame_ms=50))

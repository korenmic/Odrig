import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions"); from lib import *
entry, pic = load(11)
DIM = [[5, 4]]                       # the flame's edge sinks into the glow: narrower
BRIGHT = [[5, 6]]                    # the edge a step brighter: fuller
SHORT = [[4, 3], [5, 4], [6, 5]]     # the tip a ring shorter
parts = [
    # each flame wavers at its own pace
    flicker(bx(6, 17, 18, 32), [[], DIM, BRIGHT], 250),
    flicker(bx(26, 8, 39, 27), [BRIGHT, [], DIM], 200),
    flicker(bx(45, 8, 58, 23), [DIM, BRIGHT, []], 250),
    flicker(bx(6, 17, 18, 23), [[], SHORT], 300),
    flicker(bx(26, 8, 39, 14), [SHORT, []], 400),
    flicker(bx(45, 8, 58, 15), [[], SHORT], 250),
]
save(entry, pic, motion(parts, seconds=12, frame_ms=50))

import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions"); from lib import *
entry, pic = load(13)
DIM = [[5, 4]]                       # the flame's edge sinks into the glow: narrower
BRIGHT = [[5, 6]]                    # the edge a step brighter: fuller
SHORT = [[4, 3], [5, 4], [6, 5]]     # the tip a ring shorter
FADE = [[4, 3], [3, 2]]              # the smoke thinner
parts = [
    flicker(bx(26, 17, 41, 34), [[], DIM, BRIGHT], 250),
    flicker(bx(29, 15, 37, 22), [[], SHORT], 300),
    flicker(bx(26, 0, 38, 17), [[], FADE], 500),
]
save(entry, pic, motion(parts, seconds=12, frame_ms=50))

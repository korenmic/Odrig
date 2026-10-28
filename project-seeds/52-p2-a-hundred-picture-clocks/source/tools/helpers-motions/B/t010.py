import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions"); from lib import *
entry, pic = load(10)
DIM = [[5, 4]]              # the edge sinks into the halo: the flame narrower
BRIGHT = [[5, 6]]           # the edge brighter: the flame fuller
SHORT = [[5, 4], [6, 5]]    # the tip shorter
parts = [
    flicker(bx(26, 5, 36, 22), [[], DIM, BRIGHT], 250),
    flicker(bx(26, 5, 36, 11), [[], SHORT], 300),
]
save(entry, pic, motion(parts, seconds=12, frame_ms=50))

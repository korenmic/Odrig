import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions"); from lib import *
entry, pic = load(90)
# the bulb's glow breathes, once over the loop: from none to a wide warm halo and back
parts = [
    pulse(bx(8, 0, 53, 44), [
        [[2, 1], [3, 2]],
        [[2, 1]],
        [],
        [[2, 3]],
        [[2, 3], [3, 5]],
    ]),
]
save(entry, pic, motion(parts, seconds=12, frame_ms=50))

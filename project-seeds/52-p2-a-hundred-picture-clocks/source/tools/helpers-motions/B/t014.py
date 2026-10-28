import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions"); from lib import *
entry, pic = load(14)
# a blob of lava (7) leaves the bottom blob, rises through the liquid (6) into the top blob and
# sinks back. In each column two levels make a band of 7 that moves: the first fills 7 up to
# the band's top, the second turns 7 back to 6 up to the band's bottom. Three columns, the
# narrower the taller their band, round the blob.
Y0, Y1 = 20, 38
C0, C1 = 8, 90         # the blob's centre, in percent of the box from its bottom, at 0 and at L/2


def tier(x0, x1, h):
    return [level(bx(x0, Y0, x1, Y1), [6, 7], 7, 6, "bottom", C0 + h, min(100, C1 + h)),
            level(bx(x0, Y0, x1, Y1), [7], 6, 7, "bottom", max(0, C0 - h), C1 - h)]


parts = tier(26, 38, 9) + tier(28, 36, 15) + tier(30, 34, 21)
save(entry, pic, motion(parts, seconds=16, frame_ms=50))

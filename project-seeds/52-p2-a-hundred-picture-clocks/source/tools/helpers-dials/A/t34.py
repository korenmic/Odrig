import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import numpy, h, edit
e, p = edit.load(34)
SILVER = [4, 5, 7]
m = h.seg_mask(30, 30.5, 20, 24, 1.3)
m |= h.seg_mask(31, 30, 41, 24, 1.3)
m |= h.seg_mask(29.5, 32.5, 20.5, 35.5, 1.4)
m |= h.seg_mask(30.5, 33, 36.5, 33, 0.8)
m &= numpy.isin(p, SILVER)
h.inpaint(p, m, avoid=SILVER)
clock = dict(edit.DIAL)
clock["hands"] = [
    edit.hand_at("hour", 1, 62, 64, 15, 3, 3), edit.hand_at("hour", 7, 62, 64, 14, 2, 2),
    edit.hand_at("minute", 1, 62, 64, 23, 2, 4), edit.hand_at("minute", 7, 62, 64, 22, 1, 3),
]
clock["caps"] = [edit.cap_at(1, 62, 64, 2)]
print(edit.write(e, p, clock=clock))

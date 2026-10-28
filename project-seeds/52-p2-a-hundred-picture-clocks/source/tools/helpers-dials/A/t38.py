import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import numpy, h, edit
e, p = edit.load(38)
DARK = [0, 1, 2, 3, 4]
m = h.seg_mask(30, 31, 42, 19.3, 2.0)
m |= h.seg_mask(30, 30.5, 30, 31.5, 2.0)
m &= numpy.isin(p, DARK) | h.seg_mask(30, 31, 42, 19.3, 1.6)
h.inpaint_vertical(p, m)
edit.set_pixels(p, [(30, 28), (30, 29), (30, 30)], 5)
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand("hour", 0, 30, 31, 18, 2, 2), edit.hand("minute", 0, 30, 31, 28, 1, 3)]
clock["caps"] = [edit.cap(0, 30, 31, 2)]
print(edit.write(e, p, clock=clock))

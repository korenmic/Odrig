import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import numpy, h, edit
e, p = edit.load(2)
DARK = [0, 1]
m = numpy.zeros((60, 60), bool)
m[37:46, 31:50] = True
m &= numpy.isin(p, DARK)
h.inpaint(p, m, avoid=DARK)
m2 = h.seg_mask(31, 39, 49, 44.5, 2.2) & numpy.isin(p, [0, 1, 3, 5])
m2[:, :31] = False
m2[:, 50:] = False
m2[46:, :] = False
h.inpaint(p, m2, avoid=[0, 1, 3])
edit.set_pixels(p, [(40, 39)], 7)
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand("hour", 1, 28, 39, 22, 3, 0)]
clock["caps"] = []
print(edit.write(e, p, clock=clock))

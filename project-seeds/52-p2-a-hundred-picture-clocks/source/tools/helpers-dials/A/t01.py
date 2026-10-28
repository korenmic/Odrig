import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import numpy, h, edit
e, p = edit.load(1)
DARK = [0, 1]
m = numpy.zeros((60, 60), bool)
m[43:45, 15:46] = True
m[42, 38:43] = True
m[41, 38] = True
m[45, 37:39] = True
m &= numpy.isin(p, DARK)
h.inpaint(p, m, avoid=DARK)
edit.set_pixels(p, [(41, 45)], 3)
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand("hour", 0, 39, 43, 14, 3, 0)]
clock["caps"] = []
print(edit.write(e, p, clock=clock))

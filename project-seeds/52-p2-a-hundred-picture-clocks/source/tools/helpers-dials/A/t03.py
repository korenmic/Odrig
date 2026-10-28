import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import numpy, h, edit
e, p = edit.load(3)
DARK = [0, 2]
m = numpy.zeros((60, 60), bool)
m[45:48, 41:45] = True
m &= numpy.isin(p, DARK)
h.inpaint(p, m, avoid=DARK)

clock = dict(edit.DIAL)
clock["hands"] = [edit.hand("hour", 0, 42, 46, 18, 3, 0)]
clock["caps"] = []
print(edit.write(e, p, clock=clock))

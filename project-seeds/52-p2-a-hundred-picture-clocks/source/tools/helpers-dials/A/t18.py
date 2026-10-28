import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(18)
FACE = 7
h.seg_erase(p, 28, 31, 22, 28, 1.2, FACE)
h.seg_erase(p, 28, 31, 34.5, 26.5, 1.2, FACE)
h.seg_erase(p, 28, 31.5, 28, 32.5, 1.6, FACE)
print(edit.grid(p, (14, 16, 44, 46)))
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand("hour", 2, 28, 31, 13, 2, 2), edit.hand("minute", 2, 28, 31, 19, 1, 3)]
clock["caps"] = [edit.cap(2, 28, 31, 2)]
print(edit.write(e, p, clock=clock))

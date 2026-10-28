import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(17)
FACE = 7
h.seg_erase(p, 29, 35.5, 23, 31, 1.4, FACE)
h.seg_erase(p, 29.5, 35, 38.5, 30, 1.3, FACE)
h.seg_erase(p, 29.5, 36, 29.5, 37.5, 1.8, FACE)
print(edit.grid(p, (12, 20, 48, 52)))
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand("hour", 0, 29, 36, 15, 2, 2), edit.hand("minute", 0, 29, 36, 21, 1, 3)]
clock["caps"] = [edit.cap(3, 29, 36, 2)]
print(edit.write(e, p, clock=clock))

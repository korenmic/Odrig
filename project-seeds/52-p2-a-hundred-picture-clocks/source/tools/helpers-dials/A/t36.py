import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(36)
FACE = 7
h.seg_erase(p, 29.5, 31.5, 22, 26, 1.4, FACE)
h.seg_erase(p, 31, 31, 37.5, 25.8, 1.3, FACE)
h.seg_erase(p, 30, 32, 30, 33, 1.5, FACE)
edit.set_pixels(p, [(30, 30)], FACE)
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand("hour", 4, 30, 32, 16, 2, 2), edit.hand("minute", 4, 30, 32, 22, 1, 3)]
clock["caps"] = [edit.cap(2, 30, 32, 2)]
print(edit.write(e, p, clock=clock))

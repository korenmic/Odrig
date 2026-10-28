import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(20)
FACE = 7
h.seg_erase(p, 29, 36.5, 22.8, 32, 1.3, FACE)
h.seg_erase(p, 29.5, 36, 37, 31, 1.3, FACE)
h.seg_erase(p, 29, 37, 29, 37.3, 1.6, FACE)
edit.set_pixels(p, [(32, 36)], FACE)
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand("hour", 1, 29, 37, 15, 2, 2), edit.hand("minute", 1, 29, 37, 20, 1, 3)]
clock["caps"] = [edit.cap(0, 29, 37, 2)]
print(edit.write(e, p, clock=clock))

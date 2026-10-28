import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(32)
FACE = 1
h.seg_erase(p, 30, 31.2, 23, 27.3, 1.3, FACE)
h.seg_erase(p, 31, 31, 39, 25.3, 1.2, FACE)
h.seg_erase(p, 28, 32.3, 31, 32.3, 1.0, FACE)
edit.set_pixels(p, [(25, 30), (26, 31)], FACE)
edit.set_pixels(p, [(40, 25)], 6)
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand("hour", 7, 30, 31, 16, 2, 2), edit.hand("minute", 7, 30, 31, 21, 1, 3)]
clock["caps"] = [edit.cap(7, 30, 31, 2)]
print(edit.write(e, p, clock=clock))

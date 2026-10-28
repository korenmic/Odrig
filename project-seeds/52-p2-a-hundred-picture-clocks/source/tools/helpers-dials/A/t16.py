import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(16)
FACE = 7
# hour hand toward 10, minute hand toward 2, the cap
h.seg_erase(p, 30, 31, 22, 25.6, 1.3, FACE)
h.seg_erase(p, 30, 31, 41, 24.6, 1.3, FACE)
h.seg_erase(p, 30, 31.5, 30, 32.5, 2.3, FACE)
edit.set_pixels(p, [(39, 24), (33, 31), (42, 26)], FACE)
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand("hour", 2, 30, 31, 18, 2, 2), edit.hand("minute", 2, 30, 31, 25, 1, 3)]
clock["caps"] = [edit.cap(0, 30, 31, 2)]
print(edit.write(e, p, clock=clock))

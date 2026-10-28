import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(37)
FACE = 1
h.seg_erase(p, 29, 31.3, 22, 26.3, 1.3, FACE)
h.seg_erase(p, 30.5, 31, 39.6, 23.8, 1.3, FACE)
h.seg_erase(p, 29.5, 32.5, 29.5, 32.5, 1.6, FACE)
print(edit.grid(p, (10, 18, 50, 46)))
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand_at("hour", 7, 60, 64, 16, 2, 2), edit.hand_at("minute", 7, 60, 64, 22, 1, 3)]
clock["caps"] = [edit.cap_at(7, 60, 64, 2)]
print(edit.write(e, p, clock=clock))

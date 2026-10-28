import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(35)
FACE = 7
h.seg_erase(p, 28.5, 30.5, 24, 26.8, 1.3, FACE)
h.seg_erase(p, 29.5, 30.5, 34.6, 25, 1.2, FACE)
h.seg_erase(p, 28.8, 31.8, 29, 32.2, 1.6, FACE)
print(edit.grid(p, (18, 18, 42, 46)))
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand_at("hour", 1, 58, 64, 13, 2, 2), edit.hand_at("minute", 1, 58, 64, 18, 1, 3)]
clock["caps"] = [edit.cap_at(1, 58, 64, 2)]
print(edit.write(e, p, clock=clock))

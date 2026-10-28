import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(19)
FACE = 7
h.seg_erase(p, 29.5, 36.5, 37, 31.3, 1.3, FACE)
h.seg_erase(p, 29.5, 36.5, 29.5, 37, 2.1, FACE)
edit.set_pixels(p, [(34, 31), (35, 31), (33, 32), (32, 33), (28, 35)], FACE)
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand_at("hour", 2, 60, 74, 12, 2, 2), edit.hand_at("minute", 2, 60, 74, 19, 1, 3)]
clock["caps"] = [edit.cap_at(1, 60, 74, 2)]
print(edit.write(e, p, clock=clock))

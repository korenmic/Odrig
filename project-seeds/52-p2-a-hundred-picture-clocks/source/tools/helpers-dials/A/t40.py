import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(40)
FACE = 7
h.seg_erase(p, 30.3, 34.6, 30.3, 34.6, 3.0, FACE)
edit.set_pixels(p, [(30, 31)], FACE)
print(edit.grid(p, (23, 27, 39, 43)))
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand_at("hour", 1, 61, 70, 6, 2, 1), edit.hand_at("minute", 1, 61, 70, 9, 1, 2)]
clock["caps"] = [edit.cap_at(1, 61, 70, 2)]
print(edit.write(e, p, clock=clock))

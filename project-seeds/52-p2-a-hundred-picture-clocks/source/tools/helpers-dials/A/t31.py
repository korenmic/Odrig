import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(31)
FACE = 7
h.seg_erase(p, 27.5, 31, 21, 26.8, 1.4, FACE)
h.seg_erase(p, 29, 31, 36.5, 26.3, 1.3, FACE)
h.seg_erase(p, 28.5, 31.5, 28.5, 33, 1.6, FACE)
edit.set_pixels(p, [(32, 31)], FACE)
clock = dict(edit.DIAL)
clock["hands"] = [edit.hand_at("hour", 1, 57, 64, 16, 2, 2), edit.hand_at("minute", 1, 57, 64, 20, 1, 3)]
clock["caps"] = [edit.cap_at(3, 57, 64, 2)]
print(edit.write(e, p, clock=clock))

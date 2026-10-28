import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(39)
FACE = 7
h.seg_erase(p, 29.5, 29.5, 20.3, 23.3, 1.4, FACE)
h.seg_erase(p, 30.5, 29.5, 44.2, 20.5, 1.4, FACE)
h.seg_erase(p, 30, 31.5, 20, 44.3, 1.2, FACE)
h.seg_erase(p, 30, 30.5, 30, 30.5, 2.0, FACE)
edit.set_pixels(p, [(33, 30), (34, 29), (35, 29), (36, 28), (37, 27), (39, 26), (40, 25), (26, 29), (27, 30), (28, 31), (32, 31), (32, 32), (31, 33), (32, 33)], FACE)
clock = dict(edit.DIAL_WITH_SECONDS)
clock["hands"] = [edit.hand_at("hour", 0, 61, 62, 21, 2, 2), edit.hand_at("minute", 0, 61, 62, 27, 1, 3),
                  edit.hand_at("second", 3, 61, 62, 30, 1, 6)]
clock["caps"] = [edit.cap_at(0, 61, 62, 3), edit.cap_at(3, 61, 62, 2)]
print(edit.write(e, p, clock=clock))

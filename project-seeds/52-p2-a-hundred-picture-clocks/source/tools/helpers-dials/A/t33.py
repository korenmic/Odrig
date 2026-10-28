import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load(33)
FACE = 7
HAND = {2, 4, 5}
# the hour hand toward 10, bent at its leaf
h.seg_erase(p, 28.5, 31.5, 23, 28, 1.4, FACE, only=HAND)
h.seg_erase(p, 23, 28, 19, 22, 1.2, FACE, only=HAND)
# the minute hand toward 2, short of the marker at 2
h.seg_erase(p, 28.5, 31.5, 38.5, 25, 1.3, FACE, only=HAND)
# the chronograph's second hand toward half past 7
h.seg_erase(p, 28.5, 32, 19, 42.5, 1.3, FACE, only=HAND)
h.seg_erase(p, 28.5, 31.5, 28.5, 32.5, 1.6, FACE, only=HAND)
edit.set_pixels(p, [(27, 32), (27, 33), (30, 33), (27, 34), (28, 34), (29, 34), (26, 36), (21, 40), (22, 40),
                    (20, 41), (21, 42), (21, 26), (38, 25), (39, 24)], FACE)
edit.set_pixels(p, [(40, 24)], 2)
edit.set_pixels(p, [(38, 29)], 0)
# the sub-dials: top (28.5, 22.5), left (18.5, 32), right (38.5, 32), bottom (28.5, 41.5)
clock = dict(edit.DIAL_WITH_SECONDS)
clock["hands"] = [
    edit.hand_at("minute", 7, 58, 45, 6, 1, 0),
    edit.hand_at("second", 7, 38, 65, 6, 1, 0),
    edit.hand_at("hour", 7, 78, 65, 5, 1, 0, 6),
    edit.hand_at("hour", 7, 58, 83, 5, 1, 0),
    edit.hand_at("hour", 4, 58, 64, 20, 2, 2),
    edit.hand_at("minute", 4, 58, 64, 27, 1, 3),
    edit.hand_at("second", 4, 58, 64, 28, 1, 5),
]
clock["caps"] = [edit.cap_at(4, 58, 64, 2)]
print(edit.write(e, p, clock=clock))
print(edit.grid(p, (12, 16, 46, 48)))

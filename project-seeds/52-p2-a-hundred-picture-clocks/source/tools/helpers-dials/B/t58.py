import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsB")
import edit, inpaint
entry, pic = edit.load(58)
segs = [(29.5, 30, 18.5, 21), (30.5, 29.5, 40.5, 21)]
b = inpaint.band(segs, 1.8)
hub = {(x, y) for x in range(60) for y in range(60) if (x - 29.5) ** 2 + (y - 30.5) ** 2 <= 2.6 ** 2}
inpaint.fill(pic, b | hub, {0, 1, 2, 3, 5, 7}, reach=3)
b2 = inpaint.band([(29.5, 17.5, 29.5, 44)], 0.6)
inpaint.fill(pic, b2, {0, 1, 2, 3, 4, 5, 7}, reach=3)
print(edit.grid(pic, (12, 14, 50, 46)))
A = edit.hand_at
px, py = 60, 62
hands = [A("hour", 1, px, py, 20, 2, 2), A("minute", 1, px, py, 30, 2, 3), A("minute", 5, px, py, 29, 1, 2), A("second", 7, px, py, 30, 1, 20)]
clock = dict(edit.DIAL_WITH_SECONDS, hands=hands, caps=[edit.cap_at(1, px, py, 4), edit.cap_at(5, px, py, 2)])
print(edit.write(entry, pic, clock=clock))

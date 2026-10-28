import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsB")
import edit, inpaint
entry, pic = edit.load(82)
b = inpaint.band([(30, 34, 21.5, 25.5), (30, 33.5, 40.2, 21.8)], 1.3)
for (x, y) in b:
    if int(pic[y, x]) != 7:
        pic[y, x] = 7
edit.replace_disc(pic, 29.75, 33.5, 2.2, {0, 1, 2, 3, 4, 5, 6}, 7)
edit.set_pixels(pic, [(33,28),(32,29),(31,30),(29,31),(30,31),(23,25),(35,25)], 7)
A = edit.hand_at
clock = dict(edit.DIAL, hands=[A("hour", 0, 60, 67, 15, 2, 2), A("minute", 0, 60, 67, 24, 1, 3)], caps=[edit.cap_at(1, 60, 67, 2)])
print(edit.write(entry, pic, clock=clock))

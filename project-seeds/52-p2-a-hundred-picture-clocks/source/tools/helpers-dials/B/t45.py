import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(45)
edit.replace_disc(pic, 30.5, 30.5, 7.5, {0, 1, 2, 3, 4, 5, 6}, 7)
edit.set_pixels(pic, [(36,25),(37,25)], 7)
print(edit.grid(pic, (16, 16, 44, 44)))
A = edit.hand_at
clock = dict(edit.DIAL_WITH_SECONDS, hands=[A("hour", 0, 62, 62, 9, 2, 2), A("minute", 0, 62, 62, 14, 1, 3), A("second", 4, 62, 62, 15, 1, 4)], caps=[edit.cap_at(2, 62, 62, 2)])
print(edit.write(entry, pic, clock=clock))

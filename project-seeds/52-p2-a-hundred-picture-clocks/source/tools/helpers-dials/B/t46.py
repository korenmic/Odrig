import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(46)
edit.fill_box(pic, (40, 24, 45, 36), 7)
edit.set_pixels(pic, [(43,36),(44,36),(44,37),(45,37),(45,38),(46,38),(46,39)], 7)
print(edit.grid(pic, (30, 17, 53, 48)))
A = edit.hand_at
clock = dict(edit.DIAL, hands=[A("hour", 0, 84, 66, 10, 2, 2), A("minute", 0, 84, 66, 15, 1, 3)], caps=[edit.cap_at(0, 84, 66, 2)])
print(edit.write(entry, pic, clock=clock))

import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(47)
edit.fill_box(pic, (36, 25, 47, 36), 7)
edit.set_pixels(pic, [(37,24)], 7)
print(edit.grid(pic, (24, 18, 54, 50)))
A = edit.hand_at
clock = dict(edit.DIAL, hands=[A("hour", 0, 76, 67, 11, 2, 2), A("minute", 0, 76, 67, 17, 1, 3)], caps=[edit.cap_at(0, 76, 67, 3)])
print(edit.write(entry, pic, clock=clock))

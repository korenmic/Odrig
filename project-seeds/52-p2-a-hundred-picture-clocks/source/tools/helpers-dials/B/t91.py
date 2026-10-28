import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(91)
edit.set_pixels(pic, [(30,37),(33,37),(34,36),(30,38),(31,38),(32,38),(31,39),(32,39)], 7)
print(edit.grid(pic, (22, 29, 42, 49)))
A = edit.hand_at
clock = dict(edit.DIAL, hands=[A("hour", 0, 64, 78, 7, 2, 1), A("minute", 0, 64, 78, 10, 1, 2)], caps=[edit.cap_at(0, 64, 78, 2)])
print(edit.write(entry, pic, clock=clock))

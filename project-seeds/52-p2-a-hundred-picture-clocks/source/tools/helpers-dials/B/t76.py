import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(76)
edit.fill_box(pic, (29, 27, 32, 36), 7)
edit.fill_box(pic, (28, 36, 33, 40), 7)
edit.set_pixels(pic, [(32,29)], 7)
print(edit.grid(pic, (12, 18, 48, 56)))
H = edit.hand
clock = dict(edit.DIAL_WITH_SECONDS, hands=[H("second", 1, 30, 37, 21, 1, 3)], caps=[edit.cap(0, 30, 37, 2)])
print(edit.write(entry, pic, clock=clock))

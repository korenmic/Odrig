import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(43)
edit.replace_box(pic, (26, 28, 36, 42), {0, 1, 2, 3, 4, 5, 6}, 7)
edit.set_pixels(pic, [(29,42),(30,42),(29,43)], 7)
H = edit.hand
clock = dict(edit.DIAL, hands=[H("hour", 1, 30, 35, 10, 2, 3), H("minute", 1, 30, 35, 15, 1, 5)], caps=[edit.cap(0, 30, 35, 2)])
print(edit.write(entry, pic, clock=clock))

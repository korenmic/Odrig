import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(42)
edit.set_pixels(pic, [(21,27),(22,27),(23,27),(23,28),(24,28),(24,29),(25,29),(25,30),(26,30),(27,30),(25,31),(26,31),(27,31)], 7)
edit.set_pixels(pic, [(26,y) for y in range(30, 37)], 7)
edit.set_pixels(pic, [(26,29),(27,32),(28,32),(28,33)], 7)
print(edit.grid(pic, (14, 20, 40, 41)))
H = edit.hand
clock = dict(edit.DIAL, hands=[H("hour", 0, 26, 30, 9, 2, 2), H("minute", 0, 26, 30, 13, 1, 3)], caps=[edit.cap(0, 26, 30, 2)])
print(edit.write(entry, pic, clock=clock))

import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(57)
ul = [(22,24),(22,25),(23,25),(24,25),(23,26),(24,26),(25,26),(25,27),(26,27),(27,27),(26,28),(27,28),(28,28),(28,29),(29,29),(29,30),(30,30),(31,30),(32,30)]
r = [(x,31) for x in range(30,38)] + [(30,32),(32,32),(33,32),(34,32),(35,32),(36,32),(37,32)]
edit.set_pixels(pic, ul + r, 4)
edit.set_pixels(pic, [(31,32),(31,33)], 3)
print(edit.grid(pic, (18, 16, 44, 42)))
H = edit.hand
clock = dict(edit.DIAL, hands=[H("hour", 7, 31, 31, 11, 2, 2), H("minute", 7, 31, 31, 20, 1, 3)], caps=[edit.cap(7, 31, 31, 2)])
print(edit.write(entry, pic, clock=clock))

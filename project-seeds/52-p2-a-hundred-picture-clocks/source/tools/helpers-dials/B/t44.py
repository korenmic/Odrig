import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(44)
edit.replace_disc(pic, 31, 37, 4.6, {0, 1, 2, 3, 4, 5, 6}, 7)
edit.set_pixels(pic, [(34,33),(35,33),(27,34),(31,32),(31,33)], 7)
print(edit.grid(pic, (20, 26, 42, 46)))
H = edit.hand
clock = dict(edit.DIAL, hands=[H("hour", 0, 31, 37, 7, 2, 2), H("minute", 0, 31, 37, 11, 1, 3)], caps=[edit.cap(0, 31, 37, 2)])
print(edit.write(entry, pic, clock=clock))

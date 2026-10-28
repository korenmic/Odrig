import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(68)
edit.fill_box(pic, (27, 14, 33, 46), 6)
print(edit.grid(pic, (8, 8, 52, 52)))
H = edit.hand
hands = [H("minute", 3, 29, 29, 8, 3, 32), H("minute", 2, 29, 29, 30, 3, 0)]
clock = dict(edit.DIAL, hands=hands, caps=[edit.cap(1, 29, 29, 3)])
print(edit.write(entry, pic, clock=clock))

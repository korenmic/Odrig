import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(49)
edit.replace_box(pic, (22, 37, 27, 41), {0, 1, 2, 3, 4, 5, 6}, 7)
edit.set_pixels(pic, [(37,39),(39,41)], 3)
print(edit.grid(pic, (18, 33, 44, 45)))
A = edit.hand_at
side = "-side" in sys.argv
hands = [A("hour", 0, 48, 78, 4, 1, 0), A("minute", 0, 48, 78, 7, 1, 1)]
caps = []
if side:
    hands += [A("hour", 0, 76, 78, 3, 1, 0), A("minute", 0, 76, 78, 5, 1, 0)]
clock = dict(edit.DIAL, hands=hands, caps=caps)
print(edit.write(entry, pic, clock=clock))

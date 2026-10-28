import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(77)
edit.replace_box(pic, (30, 11, 35, 16), {0, 1, 2, 3, 4, 5, 6}, 7)
print(edit.grid(pic, (24, 6, 40, 22)))
A = edit.hand_at
clock = dict(edit.DIAL, hands=[A("hour", 0, 65, 28, 4, 1, 1), A("minute", 0, 65, 28, 7, 1, 1)], caps=[])
print(edit.write(entry, pic, clock=clock))

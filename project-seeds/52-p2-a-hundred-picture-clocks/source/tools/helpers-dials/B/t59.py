import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(59)
a = [(13,44),(12,45),(11,45),(9,46),(10,46),(11,46),(9,47),(10,47),(11,47),(8,48),(9,48)]
b = [(x, y) for x in (29, 30) for y in range(43, 49)] + [(28,49),(28,50),(27,51)]
c = [(x, y) for x in (49, 50) for y in range(43, 48)] + [(48,48),(49,48),(48,49),(47,50),(48,50),(47,51)]
edit.set_pixels(pic, a + b + c, 7)
print(edit.grid(pic, (0, 37, 60, 56)))
A = edit.hand_at
hands, caps = [], []
for hx, off in ((21, -5), (60, 0), (100, 3)):
    hands += [A("hour", 0, hx, 94, 6, 1, 1, off), A("minute", 0, hx, 94, 10, 1, 1, off)]
clock = dict(edit.DIAL, hands=hands, caps=caps)
print(edit.write(entry, pic, clock=clock))

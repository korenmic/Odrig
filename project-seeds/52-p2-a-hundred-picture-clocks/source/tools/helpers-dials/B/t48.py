import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(48)
edit.replace_disc(pic, 25.5, 43.5, 4.5, {0, 1, 2, 3, 4, 5, 6}, 7)
edit.set_pixels(pic, [(22,41),(23,41),(29,40),(22,47),(23,47)], 7)
print(edit.grid(pic, (16, 34, 36, 54)))
A = edit.hand_at
clock = dict(edit.DIAL, hands=[A("hour", 0, 52, 88, 5, 1, 1), A("minute", 0, 52, 88, 10, 1, 2)], caps=[edit.cap_at(0, 52, 88, 2)])
print(edit.write(entry, pic, clock=clock))

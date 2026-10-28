import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(70)
left = [(17,y) for y in range(28,36)] + [(16,30),(16,31),(15,32),(16,32),(16,33),(18,33),(19,33),(20,33),(18,32),(19,32),(20,32),(19,31),(20,31),(21,31),(20,30),(21,30),(16,34),(18,34),(16,35),(18,35),(18,36)]
right = [(x,y) for x in (40,41) for y in range(28,37)] + [(39,34),(39,35),(42,33),(43,33),(43,32),(44,32),(42,34),(42,35),(42,36)]
edit.set_pixels(pic, left + right, 7)
print(edit.grid(pic, (8, 23, 52, 47)))
A = edit.hand_at
hands = [A("hour", 0, 35, 68, 8, 2, 2, 0), A("minute", 0, 35, 68, 12, 1, 2, 0),
         A("hour", 0, 82, 70, 8, 2, 2, 2), A("minute", 0, 82, 70, 12, 1, 2, 2)]
caps = [edit.cap_at(3, 35, 68, 2), edit.cap_at(3, 82, 70, 2)]
clock = dict(edit.DIAL, hands=hands, caps=caps)
print(edit.write(entry, pic, clock=clock))

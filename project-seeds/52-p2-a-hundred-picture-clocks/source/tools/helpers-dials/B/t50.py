import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
entry, pic = edit.load(50)
boss = [(29,32),(30,32),(28,32),(29,33),(30,33),(28,33),(32,33),(28,34),(29,34),(30,34),(28,35),(31,35),(32,35)]
up = [(31,30),(31,31)]
dl = [(27,36),(28,36),(26,37),(27,37),(25,38),(26,38),(24,39),(25,39),(24,40),(25,40),(23,41),(24,41),(22,42),(23,42),(22,43)]
dr = [(31,36),(32,36),(32,37),(33,37),(33,38),(34,38),(34,39),(35,39),(34,40),(35,40),(35,41),(36,41),(36,42),(37,42),(36,43),(37,43),(37,44)]
edit.set_pixels(pic, boss + up + dl + dr, 1)
if "-dark" in sys.argv:
    edit.set_pixels(pic, [(31,32),(32,32),(31,33),(31,34),(29,35),(30,35)], 1)
edit.set_pixels(pic, [(25,41),(24,42),(25,42),(23,43),(24,43),(23,44),(23,45)], 1)
print(edit.grid(pic, (16, 26, 44, 48)))
A = edit.hand_at
H = edit.hand
px, py = 59, 66
if "-outline" in sys.argv:
    hands = [A("hour", 0, px, py, 21, 3, 3), A("minute", 0, px, py, 33, 2, 4), A("hour", 7, px, py, 20, 2, 2), A("minute", 7, px, py, 32, 1, 3)]
else:
    hands = [A("hour", 7, px, py, 20, 2, 2), A("minute", 7, px, py, 32, 1, 3)]
clock = dict(edit.DIAL, hands=hands, caps=[edit.cap_at(7, px, py, 3)])
print(edit.write(entry, pic, clock=clock))

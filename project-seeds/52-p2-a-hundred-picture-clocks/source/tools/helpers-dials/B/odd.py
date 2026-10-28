# odd.py N x0 y0 x1 y1 FACE [-w]: per row, the columns whose index is not in FACE (digits), as col:index
import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
n = int(sys.argv[1]); x0, y0, x1, y1 = map(int, sys.argv[2:6]); face = {int(c) for c in sys.argv[6]}
entry, pic = (edit.load_work(n) if "-w" in sys.argv else edit.load(n))
for y in range(y0, y1):
    print(f"{y:3d}", " ".join(f"{x}:{int(pic[y, x])}" for x in range(x0, x1) if int(pic[y, x]) not in face))

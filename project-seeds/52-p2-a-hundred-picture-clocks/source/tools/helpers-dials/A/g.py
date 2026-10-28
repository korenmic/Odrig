import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
n = int(sys.argv[1]); x0, y0, x1, y1 = (int(v) for v in sys.argv[2].split(","))
src = sys.argv[3] if len(sys.argv) > 3 else "skel"
e, p = edit.load(n) if src == "skel" else edit.load_work(n)
print("     " + " ".join(f"{x:2d}"[0] if x % 5 == 0 else " " for x in range(x0, x1)))
print("     " + " ".join(f"{x % 10}" for x in range(x0, x1)))
for y in range(y0, y1):
    print(f"{y:3d}  " + " ".join(str(int(v)) for v in p[y, x0:x1]))

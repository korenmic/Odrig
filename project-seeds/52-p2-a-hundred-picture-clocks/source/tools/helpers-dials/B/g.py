import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
n = int(sys.argv[1])
box = tuple(map(int, sys.argv[2:6])) if len(sys.argv) > 5 else None
src = "work" if "-w" in sys.argv else "skel"
entry, pic = (edit.load_work(n) if src == "work" else edit.load(n))
print(edit.hexes(entry))
print(edit.grid(pic, box))

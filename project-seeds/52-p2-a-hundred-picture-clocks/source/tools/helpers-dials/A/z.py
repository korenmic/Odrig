import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
n = int(sys.argv[1]); box = tuple(int(v) for v in sys.argv[2].split(","))
src = sys.argv[3] if len(sys.argv) > 3 else "skel"
e, p = edit.load(n) if src == "skel" else edit.load_work(n)
h.zoom(e, p, f"z{n}{'' if src=='skel' else 'w'}.png", box)
print(edit.hexes(e))

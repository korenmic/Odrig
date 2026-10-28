import sys
sys.path.insert(0, r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA")
import h, edit
e, p = edit.load_work(15)
FACE = 7
edit.replace_box(p, (38, 21, 43, 26), {0, 1, 2, 3, 4, 5, 6}, FACE)
edit.write(e, p, clock=e["clock"])

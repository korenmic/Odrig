import sys
from PIL import Image
OUT = r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsB/v"
for n in map(int, sys.argv[1:]):
    a = Image.open(rf"C:/Users/koren/src/Odrig/scratch/clocks/clock-{n:03d}.png").convert("RGB")
    b = Image.open(rf"C:/Users/koren/src/Odrig/scratch/clocks52/reduced/clock-{n:03d}.png").convert("RGB")
    a = a.resize((a.width * 4, a.height * 4), Image.NEAREST)
    b = b.resize((480, 480), Image.NEAREST)
    im = Image.new("RGB", (a.width + b.width + 10, max(a.height, b.height)), (255, 0, 255))
    im.paste(a, (0, 0)); im.paste(b, (a.width + 10, 0))
    im.save(f"{OUT}/t{n:03d}.png")

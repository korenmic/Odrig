# red.py N x0 y0 x1 y1 [-w] : the reduced (skeleton) or work picture of a box, enlarged 16x with a grid (magenta every 5)
import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit
from PIL import Image, ImageDraw
n = int(sys.argv[1]); x0, y0, x1, y1 = map(int, sys.argv[2:6])
entry, pic = (edit.load_work(n) if "-w" in sys.argv else edit.load(n))
pal = entry["palette"]
k = 16
im = Image.new("RGB", ((x1 - x0) * k, (y1 - y0) * k))
d = ImageDraw.Draw(im)
for y in range(y0, y1):
    for x in range(x0, x1):
        c = pal[int(pic[y, x])]
        d.rectangle([(x - x0) * k, (y - y0) * k, (x - x0 + 1) * k - 1, (y - y0 + 1) * k - 1], fill=((c >> 16) & 255, (c >> 8) & 255, c & 255))
for x in range(x0, x1 + 1):
    d.line([((x - x0) * k, 0), ((x - x0) * k, im.height)], fill=(255, 0, 255) if x % 5 == 0 else (60, 60, 60))
for y in range(y0, y1 + 1):
    d.line([(0, (y - y0) * k), (im.width, (y - y0) * k)], fill=(255, 0, 255) if y % 5 == 0 else (60, 60, 60))
im.save(rf"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsB/r{n:03d}.png")

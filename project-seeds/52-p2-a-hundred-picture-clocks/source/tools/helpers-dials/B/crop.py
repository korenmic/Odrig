# crop.py SHEET OUT x0 y0 x1 y1 [rows...] : crops each picture of rows of a sheet to a box in tile pixels
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert("RGB")
x0, y0, x1, y1 = map(int, sys.argv[3:7])
rows = [int(r) for r in sys.argv[7:]] or [0]
n = 8
cell = im.width // n
s = (cell - 4) / 60
lines = []
for row in rows:
    parts = []
    for i in range(n):
        left = i * cell + 2
        top = row * cell + 2
        parts.append(im.crop((int(left + x0 * s), int(top + y0 * s), int(left + x1 * s), int(top + y1 * s))))
    k = 220 / parts[0].width
    parts = [p.resize((int(p.width * k), int(p.height * k)), Image.NEAREST) for p in parts]
    lines.append(parts)
w = sum(p.width + 6 for p in lines[0]); h = sum(l[0].height + 6 for l in lines)
out = Image.new("RGB", (w, h), (255, 0, 255))
y = 0
for l in lines:
    x = 0
    for p in l:
        out.paste(p, (x, y)); x += p.width + 6
    y += l[0].height + 6
out.save(sys.argv[2])

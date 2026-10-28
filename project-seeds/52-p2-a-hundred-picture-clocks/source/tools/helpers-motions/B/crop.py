"""Crop a region (in tile pixels x0 y0 x1 y1) from every picture of a sheet made at a scale:
python -I crop.py SHEET OUT scale x0 y0 x1 y1 [zoom] [--cols a,b,...]"""
import sys
from PIL import Image
a = sys.argv[1:]
cols = None
if "--cols" in a:
    i = a.index("--cols"); cols = [int(c) for c in a[i + 1].split(",")]; del a[i:i + 2]
sheet, out, scale, x0, y0, x1, y1 = a[0], a[1], *map(int, a[2:7])
zoom = int(a[7]) if len(a) > 7 else 2
im = Image.open(sheet).convert("RGB")
cell = 60 * scale + 4
ncol, nrow = im.size[0] // cell, im.size[1] // cell
cols = cols or list(range(ncol))
w, h = (x1 - x0) * scale * zoom, (y1 - y0) * scale * zoom
outim = Image.new("RGB", (len(cols) * (w + 6), nrow * (h + 6)), (255, 0, 255))
for r in range(nrow):
    for k, c in enumerate(cols):
        X, Y = c * cell + 2 + x0 * scale, r * cell + 2 + y0 * scale
        part = im.crop((X, Y, X + (x1 - x0) * scale, Y + (y1 - y0) * scale)).resize((w, h), Image.NEAREST)
        outim.paste(part, (k * (w + 6), r * (h + 6)))
outim.save(out)
print(out, outim.size)

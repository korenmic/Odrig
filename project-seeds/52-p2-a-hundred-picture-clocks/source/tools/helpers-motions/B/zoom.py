"""Zoomed view of a box of a tile: python -I zoom.py OUT N x0 y0 x1 y1 [--work] [--scale S]"""
import json, sys, pathlib
from PIL import Image, ImageDraw
ROOT = pathlib.Path(__file__).resolve().parents[2]
a = sys.argv[1:]
work = "--work" in a
a = [x for x in a if x != "--work"]
S = 16
if "--scale" in a:
    i = a.index("--scale"); S = int(a[i + 1]); del a[i:i + 2]
out, n, x0, y0, x1, y1 = a[0], int(a[1]), *map(int, a[2:6])
e = {x["tile"]: x for x in json.loads((ROOT / "skeleton.json").read_text(encoding="utf-8"))}[n]
if work:
    e = json.loads((ROOT / "work" / f"clock-{n:03d}.json").read_text(encoding="utf-8"))
w, h = x1 - x0, y1 - y0
img = Image.new("RGB", (w * S + 30, h * S + 30), (60, 60, 60))
d = ImageDraw.Draw(img)
for y in range(y0, y1):
    for x in range(x0, x1):
        i = int(e["picture"][y][x]); c = e["palette"][i]
        X, Y = 30 + (x - x0) * S, 30 + (y - y0) * S
        d.rectangle([X, Y, X + S - 1, Y + S - 1], fill=(c >> 16, (c >> 8) & 255, c & 255))
        lum = (c >> 16) * .3 + ((c >> 8) & 255) * .59 + (c & 255) * .11
        d.text((X + S // 2 - 3, Y + S // 2 - 6), str(i), fill=(0, 0, 0) if lum > 110 else (255, 255, 255))
for x in range(x0, x1):
    if x % 5 == 0:
        d.text((30 + (x - x0) * S + 2, 5), str(x), fill=(255, 255, 0))
        d.line([30 + (x - x0) * S, 30, 30 + (x - x0) * S, 30 + h * S], fill=(255, 0, 255))
for y in range(y0, y1):
    if y % 5 == 0:
        d.text((2, 30 + (y - y0) * S + 2), str(y), fill=(255, 255, 0))
        d.line([30, 30 + (y - y0) * S, 30 + w * S, 30 + (y - y0) * S], fill=(255, 0, 255))
img.save(out)
print(out)

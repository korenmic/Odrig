"""Zoomed view of a region of a tile (skeleton or work): python -I zoom.py OUT.png N x0 y0 x1 y1 [--work] [--scale S]"""
import json, sys, pathlib
from PIL import Image, ImageDraw
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
a = sys.argv[1:]
work = "--work" in a
a = [x for x in a if x != "--work"]
S = 16
if "--scale" in a:
    i = a.index("--scale"); S = int(a[i + 1]); del a[i:i + 2]
out, n, x0, y0, x1, y1 = a[0], int(a[1]), *map(int, a[2:6])
skel = {e["tile"]: e for e in json.loads((ROOT / "skeleton.json").read_text(encoding="utf-8"))}
e = skel[n]
if work:
    e = json.loads((ROOT / "work" / f"clock-{n:03d}.json").read_text(encoding="utf-8"))
W, H = (x1 - x0) * S + 30, (y1 - y0) * S + 30
img = Image.new("RGB", (W, H), (60, 60, 60))
d = ImageDraw.Draw(img)
for y in range(y0, y1):
    for x in range(x0, x1):
        c = e["palette"][int(e["picture"][y][x])]
        X, Y = 25 + (x - x0) * S, 25 + (y - y0) * S
        d.rectangle([X, Y, X + S - 1, Y + S - 1], fill=(c >> 16, (c >> 8) & 255, c & 255))
for x in range(x0, x1 + 1):
    X = 25 + (x - x0) * S
    d.line([X, 25, X, H - 5], fill=(255, 0, 255) if x % 5 == 0 else (90, 90, 90))
    if x % 5 == 0: d.text((X + 2, 5), str(x), fill=(255, 255, 255))
for y in range(y0, y1 + 1):
    Y = 25 + (y - y0) * S
    d.line([25, Y, W - 5, Y], fill=(255, 0, 255) if y % 5 == 0 else (90, 90, 90))
    if y % 5 == 0: d.text((2, Y + 2), str(y), fill=(255, 255, 255))
img.save(out)

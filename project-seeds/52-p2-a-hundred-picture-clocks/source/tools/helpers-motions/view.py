"""Enlarged views of tiles with a coordinate grid: python -I view.py OUT.png N [N...] [--work]"""
import json, sys, pathlib
from PIL import Image, ImageDraw
ROOT = pathlib.Path(__file__).resolve().parent.parent
args = sys.argv[1:]
work = "--work" in args
args = [a for a in args if a != "--work"]
out, nums = args[0], [int(a) for a in args[1:]]
skel = {e["tile"]: e for e in json.loads((ROOT / "skeleton.json").read_text(encoding="utf-8"))}
S = 10
cols = min(len(nums), 3)
rows = (len(nums) + cols - 1) // cols
W = 60 * S + 30
img = Image.new("RGB", (cols * W, rows * W), (60, 60, 60))
d = ImageDraw.Draw(img)
for k, n in enumerate(nums):
    e = skel[n]
    if work:
        p = ROOT / "work" / f"clock-{n:03d}.json"
        if p.exists():
            e = json.loads(p.read_text(encoding="utf-8"))
    ox, oy = (k % cols) * W + 25, (k // cols) * W + 25
    for y, row in enumerate(e["picture"]):
        for x, ch in enumerate(row):
            c = e["palette"][int(ch)]
            d.rectangle([ox + x * S, oy + y * S, ox + x * S + S - 1, oy + y * S + S - 1], fill=(c >> 16, (c >> 8) & 255, c & 255))
    for i in range(0, 61, 5):
        col = (255, 0, 255) if i % 10 == 0 else (0, 160, 160)
        d.line([ox + i * S, oy, ox + i * S, oy + 60 * S], fill=col, width=1)
        d.line([ox, oy + i * S, ox + 60 * S, oy + i * S], fill=col, width=1)
        if i % 10 == 0:
            d.text((ox + i * S - 4, oy - 12), str(i), fill=(255, 255, 255))
            d.text((ox - 20, oy + i * S - 5), str(i), fill=(255, 255, 255))
    d.text((ox, oy + 60 * S + 2), f"tile {n}", fill=(255, 255, 0))
img.save(out)
print(out)

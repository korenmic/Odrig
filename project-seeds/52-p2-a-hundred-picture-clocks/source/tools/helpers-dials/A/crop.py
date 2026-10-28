import sys
from PIL import Image
src, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
idx = [int(v) for v in sys.argv[4].split(",")]
box = [int(v) for v in sys.argv[5].split(",")] if len(sys.argv) > 5 else None
a = Image.open(src).convert("RGB")
w = a.width // n
parts = []
for k in idx:
    f = a.crop((k * w, 0, (k + 1) * w, a.height))
    if box:
        s = f.width / 60
        f = f.crop(tuple(int(v * s) for v in box))
        f = f.resize((f.width * 2, f.height * 2), Image.NEAREST)
    parts.append(f)
b = Image.new("RGB", (sum(p.width for p in parts) + 4 * len(parts), parts[0].height), (255, 0, 255))
x = 0
for p in parts:
    b.paste(p, (x, 0)); x += p.width + 4
b.save(out)
print(b.size)

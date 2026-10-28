# orig.py N x0 y0 x1 y1 : the original tile cropped to a box given in 60-px coordinates, enlarged, with a grid every 60-px pixel
import sys
from PIL import Image, ImageDraw
n = int(sys.argv[1]); x0, y0, x1, y1 = map(int, sys.argv[2:6])
a = Image.open(rf"C:/Users/koren/src/Odrig/scratch/clocks/clock-{n:03d}.png").convert("RGB")
f = a.width / 60
k = 16  # output px per 60-px pixel
b = a.crop((int(x0 * f), int(y0 * f), int(x1 * f), int(y1 * f))).resize(((x1 - x0) * k, (y1 - y0) * k), Image.LANCZOS)
d = ImageDraw.Draw(b)
for x in range(x0, x1 + 1):
    d.line([((x - x0) * k, 0), ((x - x0) * k, b.height)], fill=(255, 0, 255) if x % 5 == 0 else (90, 90, 90), width=1)
for y in range(y0, y1 + 1):
    d.line([(0, (y - y0) * k), (b.width, (y - y0) * k)], fill=(255, 0, 255) if y % 5 == 0 else (90, 90, 90), width=1)
b.save(rf"{sys.argv[0].rsplit(chr(92),1)[0].rsplit('/',1)[0]}/o{n:03d}.png")
print(a.size)

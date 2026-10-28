import sys
from PIL import Image
out = sys.argv[1]
tiles = [int(t) for t in sys.argv[2:]]
S = 6
imgs = []
for t in tiles:
    a = Image.open(f"C:/Users/koren/src/Odrig/scratch/clocks/clock-{t:03d}.png").convert("RGB")
    a = a.resize((a.width * 3, a.height * 3), Image.NEAREST)
    b = Image.open(f"C:/Users/koren/src/Odrig/scratch/clocks52/reduced/clock-{t:03d}.png").convert("RGB")
    b = b.resize((60 * S, 60 * S), Image.NEAREST)
    imgs.append((a, b))
W = max(a.width for a, b in imgs) + 60 * S + 10
H = sum(max(a.height, b.height) + 10 for a, b in imgs)
sheet = Image.new("RGB", (W, H), (255, 0, 255))
y = 0
for a, b in imgs:
    sheet.paste(a, (0, y)); sheet.paste(b, (a.width + 10, y))
    y += max(a.height, b.height) + 10
sheet.save(out)

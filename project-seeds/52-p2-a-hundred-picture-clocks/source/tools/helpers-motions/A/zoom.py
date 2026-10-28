"""python -I zoom.py SHEET.png OUT.png [factor] [col0 col1] : enlarge sheet columns (cells of 244 px at scale 4)."""
import sys
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
f = int(sys.argv[3]) if len(sys.argv) > 3 else 2
im = Image.open(src)
if len(sys.argv) > 5:
    c0, c1 = int(sys.argv[4]), int(sys.argv[5])
    cell = 244
    im = im.crop((c0 * cell, 0, c1 * cell, im.size[1]))
im.resize((im.size[0] * f, im.size[1] * f), Image.NEAREST).save(out)
print(out, im.size[0] * f, im.size[1] * f)

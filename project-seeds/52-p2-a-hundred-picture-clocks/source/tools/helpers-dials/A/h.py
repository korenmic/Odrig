import sys
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools")
import edit  # noqa: E402
import numpy  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

OUT = r"M:/AI-Cache/Temp/claude/C--Users-koren-src-Odrig/69b1d5af-136a-4c43-9bfe-3aacaccfd78e/scratchpad/dialsA/"


def zoom(entry, pic, name, box=None, s=14, marks=()):
    """An enlarged picture of a box with a pixel grid and coordinates every 5."""
    x0, y0, x1, y1 = box or (0, 0, 60, 60)
    pal = entry["palette"]
    W = (x1 - x0) * s + 30
    H = (y1 - y0) * s + 30
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = pal[int(pic[y, x])]
            X = 30 + (x - x0) * s
            Y = 30 + (y - y0) * s
            d.rectangle([X, Y, X + s - 1, Y + s - 1], fill=((c >> 16) & 255, (c >> 8) & 255, c & 255))
            d.text((X + 3, Y + 1), str(int(pic[y, x])), fill=(255, 0, 255) if int(pic[y, x]) < 4 else (0, 120, 0))
    for x in range(x0, x1 + 1):
        X = 30 + (x - x0) * s
        d.line([X, 30, X, H], fill=(255, 0, 0) if x % 5 == 0 else (128, 128, 128))
        if x % 5 == 0 and x < x1:
            d.text((X + 2, 2), str(x), fill=(0, 0, 0))
    for y in range(y0, y1 + 1):
        Y = 30 + (y - y0) * s
        d.line([30, Y, W, Y], fill=(255, 0, 0) if y % 5 == 0 else (128, 128, 128))
        if y % 5 == 0 and y < y1:
            d.text((2, Y + 2), str(y), fill=(0, 0, 0))
    for (mx, my) in marks:
        X = 30 + (mx - x0) * s
        Y = 30 + (my - y0) * s
        d.ellipse([X - 3, Y - 3, X + 3, Y + 3], outline=(255, 0, 0), width=2)
    im.save(OUT + name)


def seg_erase(pic, x0, y0, x1, y1, r, to, only=None, keep=None):
    """Pixels whose centre lies within r of the segment from (x0, y0) to (x1, y1), in pixel
    coordinates (the centre of pixel x, y is x, y here), become `to`; restricted to the
    indices `only` when given, never the indices `keep`."""
    ys, xs = numpy.mgrid[0:60, 0:60]
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    t = ((xs - x0) * dx + (ys - y0) * dy) / L2 if L2 else 0 * xs
    t = numpy.clip(t, 0, 1)
    px, py = x0 + t * dx, y0 + t * dy
    near = (xs - px) ** 2 + (ys - py) ** 2 <= r * r
    if only is not None:
        near &= numpy.isin(pic, list(only))
    if keep is not None:
        near &= ~numpy.isin(pic, list(keep))
    pic[near] = to
    return int(near.sum())


def diff(a, b):
    ys, xs = numpy.nonzero(a != b)
    return list(zip(xs.tolist(), ys.tolist()))


def seg_mask(x0, y0, x1, y1, r):
    ys, xs = numpy.mgrid[0:60, 0:60]
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    t = ((xs - x0) * dx + (ys - y0) * dy) / L2 if L2 else 0 * xs
    t = numpy.clip(t, 0, 1)
    px, py = x0 + t * dx, y0 + t * dy
    return (xs - px) ** 2 + (ys - py) ** 2 <= r * r


def inpaint(pic, mask, avoid=()):
    """The pixels of the mask take, from the outside in, the most common colour among their
    eight neighbours outside the mask (colours in `avoid` not counted)."""
    mask = mask.copy()
    while mask.any():
        changes = []
        for y, x in zip(*numpy.nonzero(mask)):
            votes = {}
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if (dy or dx) and 0 <= yy < 60 and 0 <= xx < 60 and not mask[yy, xx]:
                        c = int(pic[yy, xx])
                        if c not in avoid:
                            votes[c] = votes.get(c, 0) + (2 if dx == 0 or dy == 0 else 1)
            if votes:
                changes.append((y, x, max(sorted(votes), key=lambda c: votes[c])))
        if not changes:
            break
        for y, x, c in changes:
            pic[y, x] = c
            mask[y, x] = False


def inpaint_vertical(pic, mask):
    """Each pixel of the mask takes the colour of the nearest pixel outside the mask in its
    own column (above when both are as near), which keeps a vertical grain."""
    out = pic.copy()
    for y, x in zip(*numpy.nonzero(mask)):
        for d in range(1, 60):
            up, down = y - d, y + d
            if up >= 0 and not mask[up, x]:
                out[y, x] = pic[up, x]
                break
            if down < 60 and not mask[down, x]:
                out[y, x] = pic[down, x]
                break
    pic[:] = out

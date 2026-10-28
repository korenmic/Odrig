import numpy
from collections import Counter

def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5

def band(segments, width, size=60):
    """Pixels whose centre is within `width` of any segment ((ax, ay, bx, by) in pixel coordinates)."""
    out = set()
    for ax, ay, bx, by in segments:
        for y in range(size):
            for x in range(size):
                if seg_dist(x, y, ax, ay, bx, by) <= width:
                    out.add((x, y))
    return out

def fill(pic, pixels, hand_colors, reach=3, keep=None):
    """Each pixel of `pixels` whose colour is in hand_colors becomes the most common colour of
    its neighbours within `reach` that are neither in `pixels` nor of hand_colors (ties: nearest)."""
    keep = keep or set()
    todo = [(x, y) for (x, y) in pixels if int(pic[y, x]) in hand_colors and (x, y) not in keep]
    src = pic.copy()
    for x, y in todo:
        c = Counter()
        for yy in range(max(0, y - reach), min(60, y + reach + 1)):
            for xx in range(max(0, x - reach), min(60, x + reach + 1)):
                if (xx, yy) in pixels or int(src[yy, xx]) in hand_colors:
                    continue
                d = abs(xx - x) + abs(yy - y)
                c[int(src[yy, xx])] += 1.0 / d
        if c:
            pic[y, x] = c.most_common(1)[0][0]
    return todo

"""A replica of motion.js turned(), for trials: rotate(pic, box, moving, behind, centre, degrees)."""
import math
import numpy

ONE = 16384


def rotate(pic, box, moving, behind, centre, degrees):
    out = pic.copy()
    c = round(math.cos(math.radians(degrees)) * ONE)
    s = round(math.sin(math.radians(degrees)) * ONE)
    cx, cy = centre
    left, top, w, h = box
    mv = set(moving)
    for y in range(top, top + h):
        for x in range(left, left + w):
            du = 2 * x + 1 - cx
            dv = 2 * y + 1 - cy
            fx = (cx + (du * c + dv * s) // ONE) // 2
            fy = (cy + (-du * s + dv * c) // ONE) // 2
            inside = left <= fx < left + w and top <= fy < top + h
            src = pic[fy, fx] if inside else -1
            if inside and src in mv:
                out[y, x] = src
            elif pic[y, x] in mv:
                out[y, x] = behind
    return out


def spikes(pic, box, moving):
    """Pixels of the moving set with at most one 4-neighbour of the moving set."""
    left, top, w, h = box
    m = numpy.isin(pic, list(moving))
    n = 0
    for y in range(top, top + h):
        for x in range(left, left + w):
            if m[y, x]:
                k = sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= y + dy < 60 and 0 <= x + dx < 60 and m[y + dy, x + dx])
                if k <= 1:
                    n += 1
    return n

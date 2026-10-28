"""Helpers for the hourglass tiles (group A)."""
import sys
from collections import deque
sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions")
from lib import *  # noqa: F401,F403
import numpy


def stream_variants(a, b, c):
    """Variants that move a pattern a, b, c (at y % 3 = 0, 1, 2) down one pixel a step."""
    return [[], [[a, c], [b, a], [c, b]], [[a, b], [b, c], [c, a]]]


def draw_stream(pic, xs, y0, y1, colours):
    """Paints the pattern colours[y % 3] in the columns xs, rows y0..y1-1."""
    for y in range(y0, y1):
        for x in xs:
            pic[y, x] = colours[y % 3]


def vessel(pic, seeds, passable, box):
    """The 4-connected pixels of passable indices reached from the seeds within box (x0,y0,x1,y1)."""
    x0, y0, x1, y1 = box
    mask = numpy.zeros(pic.shape, dtype=bool)
    todo = deque(seeds)
    while todo:
        x, y = todo.popleft()
        if not (x0 <= x < x1 and y0 <= y < y1) or mask[y, x] or pic[y, x] not in passable:
            continue
        mask[y, x] = True
        todo.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    return mask


def strays(pic, box, inside, mask):
    """Pixels of the box with an inside index that are not in the vessel."""
    x0, y0, x1, y1 = box
    out = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if pic[y, x] in inside and not mask[y, x]:
                out.append((x, y, int(pic[y, x])))
    return out


def show_mask(pic, mask, box):
    x0, y0, x1, y1 = box
    lines = []
    for y in range(y0, y1):
        lines.append(f"{y:3d} " + "".join(("*" if mask[y, x] else str(int(pic[y, x]))) for x in range(x0, x1)))
    return "\n".join(lines)

"""Helpers to make the entries of the inventory of seed 52 by hand, one tile at a time.

    import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/tools"); import edit
    entry, pic = edit.load(15)            # the tile reduced to its colours, from skeleton.json
    print(edit.grid(pic, (20, 20, 40, 40)))   # the indices of a box, x and y from the top left
    edit.replace_disc(pic, 30, 30, 12, {0}, 3)  # within a disc, indices 0 become 3
    edit.write(entry, pic, clock={...})   # work/clock-015.json

A picture is a numpy array of 60 rows of 60 palette indices, row 0 at the top. Positions
are pixels, x from the left and y from the top, from 0. A pivot or a cap in the inventory
is in half pixels: the centre of pixel x, y is at 2x + 1, 2y + 1.

Run Python with -I.
"""

import json
import pathlib

import numpy

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
WORK = ROOT / "work"
SIZE = 60


def skeleton():
    return {one["name"]: one for one in json.loads((ROOT / "skeleton.json").read_text(encoding="utf-8"))}


def load(number):
    """The tile's entry from the skeleton, and its picture as an array."""
    entry = dict(skeleton()[f"clock-{number:03d}"])
    pic = numpy.array([[int(c) for c in row] for row in entry["picture"]], dtype=numpy.int16)
    return entry, pic


def load_work(number):
    """The tile's entry as written to work/, and its picture."""
    entry = json.loads((WORK / f"clock-{number:03d}.json").read_text(encoding="utf-8"))
    pic = numpy.array([[int(c) for c in row] for row in entry["picture"]], dtype=numpy.int16)
    return entry, pic


def hexes(entry):
    """The palette as #rrggbb, by index."""
    return {i: f"#{c:06x}" for i, c in enumerate(entry["palette"])}


def grid(pic, box=None):
    """The indices of a box (x0, y0, x1, y1), x1 and y1 not included, with the numbers of
    the columns above and of the rows on the left."""
    x0, y0, x1, y1 = box or (0, 0, SIZE, SIZE)
    lines = ["    " + "".join(str((x // 10) % 10) for x in range(x0, x1)), "    " + "".join(str(x % 10) for x in range(x0, x1))]
    for y in range(y0, y1):
        lines.append(f"{y:3d} " + "".join(str(int(v)) for v in pic[y, x0:x1]))
    return "\n".join(lines)


def counts(pic, box=None):
    """How many pixels of each index a box has."""
    x0, y0, x1, y1 = box or (0, 0, SIZE, SIZE)
    values, numbers = numpy.unique(pic[y0:y1, x0:x1], return_counts=True)
    return dict(zip(values.tolist(), numbers.tolist()))


def replace_box(pic, box, indices, to):
    """Within a box, the pixels of these indices become `to`."""
    x0, y0, x1, y1 = box
    part = pic[y0:y1, x0:x1]
    part[numpy.isin(part, list(indices))] = to


def replace_disc(pic, cx, cy, radius, indices, to):
    """Within a disc about the centre of pixel cx, cy, the pixels of these indices become
    `to`."""
    ys, xs = numpy.mgrid[0:SIZE, 0:SIZE]
    inside = (xs - cx) ** 2 + (ys - cy) ** 2 <= radius * radius
    pic[inside & numpy.isin(pic, list(indices))] = to


def set_pixels(pic, points, to):
    """These pixels, (x, y) each, become `to`."""
    for x, y in points:
        pic[y, x] = to


def fill_box(pic, box, to):
    x0, y0, x1, y1 = box
    pic[y0:y1, x0:x1] = to


def rows_of(pic):
    return ["".join(str(int(v)) for v in row) for row in pic]


def write(entry, pic, clock=None, motion=None, kind=None):
    """Writes work/clock-NNN.json: the entry with its picture, its kind and its clock or
    motion."""
    WORK.mkdir(exist_ok=True)
    made = {"name": entry["name"], "tile": entry["tile"], "kind": kind or entry["kind"], "about": entry["about"],
            "palette": entry["palette"], "picture": rows_of(pic)}
    if clock is not None:
        made["clock"] = clock
    if motion is not None:
        made["motion"] = motion
    path = WORK / f"{entry['name']}.json"
    path.write_text(json.dumps(made, indent=1) + "\n", encoding="utf-8")
    return path


DIAL = {"seconds": 30, "speed_min": 60, "speed_max": 600, "direction": "random", "turns": 30}
DIAL_WITH_SECONDS = {"seconds": 30, "speed_min": 2, "speed_max": 30, "direction": "random", "turns": 30}


def hand(unit, color, x, y, length, half, tail=0, offset=0):
    """A hand about the centre of pixel x, y; its length, tail and half width in half
    pixels."""
    return {"unit": unit, "color": color, "x": 2 * x + 1, "y": 2 * y + 1, "length": length, "tail": tail, "half": half, "offset": offset}


def hand_at(unit, color, hx, hy, length, half, tail=0, offset=0):
    """A hand about a point given in half pixels."""
    return {"unit": unit, "color": color, "x": hx, "y": hy, "length": length, "tail": tail, "half": half, "offset": offset}


def cap(color, x, y, radius):
    """A cap about the centre of pixel x, y; its radius in half pixels."""
    return {"x": 2 * x + 1, "y": 2 * y + 1, "radius": radius, "color": color}


def cap_at(color, hx, hy, radius):
    return {"x": hx, "y": hy, "radius": radius, "color": color}

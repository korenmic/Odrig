"""Shared helpers for the motion tiles of seed 52.

    import sys; sys.path.insert(0, r"C:/Users/koren/src/Odrig/scratch/clocks52/helpers-motions"); from lib import *
    entry, pic = load(4)
    print(grid(pic, (10, 10, 50, 50)))         # x0, y0, x1, y1 (x1, y1 excluded)
    parts = [level(bx(19, 10, 43, 27), [3, 4, 5], 5, 4, "bottom", 60, 5), ...]
    save(entry, pic, motion(parts, seconds=12))  # writes work/clock-004.json and checks it
    sheet("motions-A-1", [4, 5], times=(0, 3000, 6000, 9000))

Boxes of parts are [left, top, width, height]; bx() converts from x0, y0, x1, y1.
Centres are in half pixels: centre of pixel x, y is 2x+1, 2y+1 (use px(x, y)).
"""
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tools"))
import edit  # noqa: E402
from edit import grid, counts, replace_box, replace_disc, set_pixels, fill_box  # noqa: E402,F401

ENV = dict(os.environ, ODRIG_TREE="C:/Users/koren/src/Odrig/scratch/clocks52/stage")


def load(n):
    return edit.load(n)


def load_work(n):
    return edit.load_work(n)


def bx(x0, y0, x1, y1):
    return [x0, y0, x1 - x0, y1 - y0]


def px(x, y):
    return [2 * x + 1, 2 * y + 1]


def level(box, inside, fill, empty, rests, frm, to):
    return {"kind": "level", "box": list(box), "inside": list(inside), "fill": fill, "empty": empty, "rests": rests, "from": frm, "to": to}


def flicker(box, variants, step_ms):
    return {"kind": "flicker", "box": list(box), "variants": [[list(p) for p in v] for v in variants], "step_ms": step_ms}


def pulse(box, variants):
    return {"kind": "pulse", "box": list(box), "variants": [[list(p) for p in v] for v in variants]}


def turn(box, moving, behind, centre, degrees):
    return {"kind": "turn", "box": list(box), "moving": list(moving), "behind": behind, "centre": list(centre), "degrees": degrees}


def swing(box, moving, behind, centre, degrees, swings):
    return {"kind": "swing", "box": list(box), "moving": list(moving), "behind": behind, "centre": list(centre), "degrees": degrees, "swings": swings}


def motion(parts, seconds=12, frame_ms=50):
    return {"seconds": seconds, "frame_ms": frame_ms, "parts": parts}


def path_of(n):
    return ROOT / "work" / f"clock-{n:03d}.json"


def check(*nums):
    out = subprocess.run(["node", "tools/tile.mjs", "check", *[str(path_of(n)) for n in nums]], cwd=ROOT, env=ENV, capture_output=True, text=True)
    print(out.stdout.strip(), out.stderr.strip())
    return out.returncode == 0


def save(entry, pic, mot):
    edit.write(entry, pic, motion=mot, kind="motion")
    return check(entry["tile"])


def sheet(name, nums, times=(0, 3000, 6000, 9000), scale=4):
    out = ROOT / "sheets" / f"{name}.png"
    res = subprocess.run(["node", "tools/tile.mjs", "sheet", str(out), *[str(path_of(n)) for n in nums], "--times", ",".join(str(t) for t in times), "--scale", str(scale)],
                         cwd=ROOT, env=ENV, capture_output=True, text=True)
    print(res.stdout.strip(), res.stderr.strip())
    return out

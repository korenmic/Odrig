"""Writes the readme of each of the 112 animations of seed 52, in the shape of seed 46: a
title line, an empty line and 16 lines `- Label: value`.

usage: python -I readmes.py PICTURE INVENTORY TWELVE_JSON COMPARISON_JSON FILES_DIR

With TWELVE_JSON and COMPARISON_JSON given as -, only the readmes of the tiles are written.

FILES_DIR holds the files; each X.md is written beside X. The key of a file is the CRC-32
of zlib and its size, as the converter's `thumbnail` names its preview.
"""

import json
import pathlib
import sys
import zlib

import numpy
from PIL import Image

DATE = "2026-10-28"
SHARE = "https://chatgpt.com/share/6ae1379a-9dc8-83ed-8fee-9aca58017cc7"
SCENES = {
    "original": ["The same second, two times", "The countdown never reaches zero", "Sand goes back up", "We were here", "Every row another time", "The clock melts"],
    "standalone": ["The same second, two times", "The countdown never reaches zero", "The reverse hourglass", "We have been here before", "Each row has a different time", "The melting clock"],
}
HEBREW = ["אותה שנייה, שני זמנים", "עוד שנייה זה קורה", "החול חוזר למעלה", "כבר היינו כאן", "כל שורה בזמן אחר", "השעון נוזל"]


def bands(source, axis):
    dark = (source.max(axis=2) < 45).mean(axis=axis) > 0.9
    found, start = [], None
    for at, gutter in enumerate(dark):
        if not gutter and start is None:
            start = at
        elif gutter and start is not None:
            found.append((start, at))
            start = None
    if start is not None:
        found.append((start, len(dark)))
    return found


def key_of(data):
    return f"{zlib.crc32(data):08x}-{len(data)}"


def lines_of(title, values):
    labels = ["File", "Key", "Animation", "Source", "Platform", "Uploader", "Title", "Media id", "Part", "Crop", "Fit", "Made with",
              "Converted", "Found", "Added", "Notes"]
    assert len(values) == len(labels) and all(values)
    return f"# {title}\n\n" + "".join(f"- {label}: {value}\n" for label, value in zip(labels, values))


def notes_of(tile):
    if tile["kind"] == "dial":
        hands = tile["clock"]["hands"]
        units = ", ".join(hand["unit"] for hand in hands)
        return (f"A picture dial: the tile's hands are erased from its picture and the player draws {len(hands)} hands ({units}) "
                f"over it, at a virtual time of a random speed from {tile['clock']['speed_min']} to {tile['clock']['speed_max']} "
                f"times real time, in a random direction.")
    if tile["kind"] == "display":
        patterns = ", ".join(f"`{field['pattern']}` in the font {field['font']}" for field in tile["clock"]["fields"])
        return (f"A picture display: the tile's time is erased from its picture and the player draws {patterns} over it, at a "
                f"virtual time of a random speed from {tile['clock']['speed_min']} to {tile['clock']['speed_max']} times real time, "
                f"in a random direction.")
    kinds = ", ".join(part["kind"] for part in tile["motion"]["parts"])
    return f"Frames of the tile's picture, {tile['motion']['seconds']} s looping without a jump, its parts moved: {kinds}."


def main():
    picture, inventory, twelve, comparison, files = map(pathlib.Path, sys.argv[1:6])
    source = numpy.asarray(Image.open(picture).convert("RGB")).astype(numpy.int32)
    rows, columns = bands(source, 1), bands(source, 0)
    assert len(rows) == 10 and len(columns) == 10
    for tile in json.loads(inventory.read_text(encoding="utf-8"))["tiles"]:
        name = tile["name"] + (".odrg" if tile["kind"] == "motion" else ".odrgx")
        if not (files / name).exists():
            continue
        data = (files / name).read_bytes()
        row, column = divmod(tile["tile"] - 1, 10)
        (y0, y1), (x0, x1) = rows[row], columns[column]
        if tile["kind"] == "motion":
            frames = sum(1 for _ in range(0, 1000 * tile["motion"]["seconds"], tile["motion"]["frame_ms"]))
            animation = f"60 x 60, frames, {tile['motion']['seconds']} s, {frames} frames before the same ones are merged"
        else:
            animation = f"60 x 60, widget, {tile['clock']['seconds']} s, 0 frames: the player draws it"
        title = f"Clock {tile['tile']}: {tile['about']}"
        printed = {85: " (printed 95)", 86: " (printed 96)"}.get(tile["tile"], "")
        values = [
            f"`{name}`", f"`{key_of(data)}`", animation,
            f"the owner's picture `its not the time frames.png`, tile {tile['tile']}{printed}, row {row + 1}, column {column + 1}",
            "unknown", "the owner", tile["about"], f"tile {tile['tile']}", "whole",
            f"{x1 - x0}:{y1 - y0}:{x0}:{y0}, the tile's cut, its printed number painted out",
            f"scaled to 60 x 60 with a box filter and reduced to {len(tile['palette'])} colours",
            "`node converter/odrig.js clocks INVENTORY.json --out DIR` on the inventory beside seed 52, its entry made with the tools beside it",
            DATE, "the owner's picture in the root of the checkout on the Windows computer, put there on 2026-10-27", DATE, notes_of(tile),
        ]
        (files / f"{pathlib.Path(name).stem}.md").write_text(lines_of(title, values), encoding="utf-8", newline="\n")
    if str(twelve) == "-":
        return
    compared = {one["name"]: one for one in json.loads(comparison.read_text(encoding="utf-8"))}
    for one in json.loads(twelve.read_text(encoding="utf-8")):
        name = one["name"] + ".odrg"
        data = (files / name).read_bytes()
        kind, number = one["name"].split("-")[1], int(one["name"].split("-")[2])
        title = SCENES[kind][number - 1]
        if kind == "original":
            source_line = (f"the scene {number} of the script `references/original/animation.js` of seed 52, the demos of the owner's "
                           f"ChatGPT conversation \"רעיונות לאנימציות זמן\", {SHARE}")
            platform = "unknown"
            gif = f"references/original/original-{number}-{'-'.join(one['name'].split('-')[3:])}.gif"
        else:
            source_line = f"the scene {number} of the script `references/standalone/standalone-script.js` of seed 52, a standalone page"
            platform = "unknown"
            gif = f"references/standalone/standalone-{number}-{'-'.join(one['name'].split('-')[3:])}.gif"
        frames = 1000 * one["seconds"] // one["frame_ms"]
        c = compared[one["name"]]
        values = [
            f"`{name}`", f"`{key_of(data)}`", f"60 x 60, frames, {one['seconds']} s, {frames} frames before the same ones are merged",
            source_line, platform, "the owner", f"{title} ({HEBREW[number - 1]})" if kind == "original" else title,
            f"scene {number}", f"whole: one period, {one['seconds']} s", "none",
            f"drawn at 60 x 60, {one['frame_ms']} ms a frame; {len(one['palette'])} colours: {', '.join(one['palette'])}",
            "`render12.mjs` of the tools beside seed 52 in a headless Chrome, then its `make12.mjs`",
            DATE, "the references beside seed 52 in the repository", DATE,
            f"Rendered from its script, not from its reference GIF `{gif}`; compared with that GIF at its {c['frames']} frames, at most "
            f"{c['largest']} and on average {c['mean']} of the 3,600 pixels differ once both are in these colours.",
        ]
        (files / f"{pathlib.Path(name).stem}.md").write_text(lines_of(f"{title}, {kind} {number}", values), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

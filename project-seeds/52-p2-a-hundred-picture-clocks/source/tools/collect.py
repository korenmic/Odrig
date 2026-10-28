"""Puts the 112 animations of seed 52 into the collection's folder `clocks/`, with their
previews, their readmes and their source, and reads every copy back.

usage: python -I collect.py FILES_DIR THUMBNAILS_DIR CLOCKS52_DIR COLLECTION_CLOCKS_DIR

FILES_DIR holds X.odrg/X.odrgx and X.md; THUMBNAILS_DIR is the repository's `thumbnails/`,
whose `<key>.gif` becomes X.gif. The source: the owner's picture, the cut tiles, the
inventory, the base pictures as PNG, and the tools. Only the folder COLLECTION_CLOCKS_DIR
is made and written; a file there of the same name is replaced.
"""

import hashlib
import json
import pathlib
import shutil
import sys
import zlib

import numpy
from PIL import Image

PICTURE = pathlib.Path(r"C:\Users\koren\src\Odrig\its not the time frames.png")
TILES = pathlib.Path(r"C:\Users\koren\src\Odrig\scratch\clocks")


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
        raise SystemExit(f"{target} does not read back as {source}")


def main():
    files, thumbnails, clocks52, out = map(pathlib.Path, sys.argv[1:5])
    names = sorted(path.name for path in files.iterdir() if path.suffix in (".odrg", ".odrgx"))
    for name in names:
        data = (files / name).read_bytes()
        key = f"{zlib.crc32(data):08x}-{len(data)}"
        copy(files / name, out / name)
        copy(files / f"{name}.md", out / f"{pathlib.Path(name).stem}.md")
        copy(thumbnails / f"{key}.gif", out / f"{pathlib.Path(name).stem}.gif")
    source = out / "source"
    copy(PICTURE, source / PICTURE.name)
    for tile in sorted(TILES.glob("clock-*.png")):
        copy(tile, source / "tiles" / tile.name)
    copy(clocks52 / "inventory.json", source / "inventory.json")
    inventory = json.loads((clocks52 / "inventory.json").read_text(encoding="utf-8"))
    for tile in inventory["tiles"]:
        palette = numpy.array([[colour >> 16, (colour >> 8) & 255, colour & 255] for colour in tile["palette"]], dtype=numpy.uint8)
        indices = numpy.array([[int(c) for c in row] for row in tile["picture"]])
        base = source / "base" / f"{tile['name']}.png"
        base.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(palette[indices], "RGB").save(base)
    for tool in sorted((clocks52 / "tools").iterdir()):
        if tool.is_file():
            copy(tool, source / "tools" / tool.name)
    for folder in ("helpers-dials", "helpers-displays", "helpers-motions"):
        for path in sorted((clocks52 / folder).rglob("*")):
            if path.is_file() and path.suffix == ".py":
                copy(path, source / "tools" / folder / path.relative_to(clocks52 / folder))
    copy(clocks52 / "INSTRUCTIONS.md", source / "tools" / "INSTRUCTIONS.md")
    print(f"{len(names)} animations with their previews and readmes, and the source, in {out}")


if __name__ == "__main__":
    main()

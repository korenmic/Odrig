import sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from lib import *  # noqa
import lib  # noqa
import numpy  # noqa
PY = r"C:/Users/koren/src/Odrig/.venv/Scripts/python"


def view(pic, entry, out, scale=10):
    """An enlarged view of a picture of indices with a grid every 5 px."""
    from PIL import Image, ImageDraw
    S = scale
    img = Image.new("RGB", (60 * S + 30, 60 * S + 30), (60, 60, 60))
    d = ImageDraw.Draw(img)
    for y in range(60):
        for x in range(60):
            c = entry["palette"][int(pic[y, x])]
            d.rectangle([25 + x * S, 25 + y * S, 25 + x * S + S - 1, 25 + y * S + S - 1], fill=(c >> 16, (c >> 8) & 255, c & 255))
    for i in range(0, 61, 5):
        col = (255, 0, 255) if i % 10 == 0 else (0, 160, 160)
        d.line([25 + i * S, 25, 25 + i * S, 25 + 60 * S], fill=col)
        d.line([25, 25 + i * S, 25 + 60 * S, 25 + i * S], fill=col)
        if i % 10 == 0:
            d.text((25 + i * S - 4, 12), str(i), fill=(255, 255, 255))
            d.text((4, 25 + i * S - 5), str(i), fill=(255, 255, 255))
    img.save(pathlib.Path(__file__).resolve().parent / out)

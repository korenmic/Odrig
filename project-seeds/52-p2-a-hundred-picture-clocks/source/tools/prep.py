"""Prepares the 100 tiles of the owner's picture for the inventory of seed 52.

Each cut tile is scaled to 60 x 60 with a box filter and reduced to at most 8 colours: a
median cut of the scaled tile, refined by k-means, then black, when the tile has a pixel
darker than 24 in each channel, in the place of the colour nearest to it. Every pixel
takes the nearest of the colours, without dithering. The colours are ordered from dark to
light.

usage: python -I prep.py TILES_DIR OUT_DIR

Writes OUT_DIR/reduced/clock-NNN.png, OUT_DIR/skeleton.json (the inventory's tiles with
their palettes, pictures, kinds and words, without their clocks and motions) and
OUT_DIR/sheet-reduced-R.png, one sheet for each row of the grid.
"""

import json
import pathlib
import sys

import numpy
from PIL import Image, ImageDraw

SIZE = 60
COLOURS = 8
DARK = 24

DIALS = {1, 2, 3, *range(15, 21), *range(31, 51), 57, 58, 59, 68, 70, 76, 77, 82, 91}
DISPLAYS = {*range(21, 31), 51, 52, 53, 60, 64, 66, 67, 75, 81, 83, 84, 85, 86, 89, *range(97, 101)}

ABOUT = {
    1: "a sundial of stone on a round base, under the sun",
    2: "a round sundial with its gnomon, under the sun",
    3: "an obelisk casting its shadow on the sand, under the sun",
    4: "an hourglass in a wooden frame",
    5: "an hourglass with golden sand",
    6: "three hourglasses of red, gold and pink sand",
    7: "a water clock: a blue bowl with water running out",
    8: "a water clock: two blue bowls, one pouring into the other",
    9: "a water clock: a tap filling a blue pot",
    10: "a candle burning in a holder",
    11: "three candles burning",
    12: "an incense spiral smoking",
    13: "an oil lamp burning",
    14: "a lava lamp",
    15: "a wall clock with numbers",
    16: "a golden pocket watch with Roman numerals",
    17: "a golden pocket watch",
    18: "an open pocket watch on its chain",
    19: "a red alarm clock with bells",
    20: "a blue alarm clock with bells",
    21: "a digital alarm clock in red digits",
    22: "a digital alarm clock in green digits",
    23: "a digital alarm clock in blue digits",
    24: "a flip clock",
    25: "four nixie tubes",
    26: "a red LED matrix clock",
    27: "a digital wrist watch",
    28: "a smart watch",
    29: "a fitness band with the hours above the minutes",
    30: "a round smart watch with a coloured ring",
    31: "a wrist watch on a brown strap",
    32: "a diver's watch with a blue dial",
    33: "a chronograph with three small dials",
    34: "a skeleton watch with its gears",
    35: "a square wrist watch",
    36: "a golden wrist watch",
    37: "a black wrist watch",
    38: "a wooden wall clock",
    39: "a plain wall clock with a red second hand",
    40: "a cuckoo clock",
    41: "a grandfather clock",
    42: "a mantel clock of wood",
    43: "a golden carriage clock",
    44: "a gothic mantel clock",
    45: "a ship's wheel clock",
    46: "a station clock on a bracket",
    47: "a street clock on its post",
    48: "a clock tower",
    49: "Big Ben",
    50: "an astronomical clock",
    51: "an atomic clock with its display",
    52: "a GPS receiver showing the time",
    53: "an NTP server showing the time",
    54: "a radio mast sending its signal",
    55: "a satellite sending its signal",
    56: "the moon in two phases",
    57: "the Earth with clock hands",
    58: "a globe with red clock hands",
    59: "a world map with three clocks",
    60: "the time of three cities",
    61: "a calendar page",
    62: "a desk calendar",
    63: "a date drum",
    64: "a display of the date and the time",
    65: "a display of the phases of the moon",
    66: "a red countdown timer",
    67: "a tomato timer",
    68: "a kitchen timer with one hand",
    69: "an egg timer",
    70: "a chess clock with two dials",
    71: "a metronome",
    72: "a tuning fork humming",
    73: "a music box",
    74: "an hourglass on red",
    75: "a stopwatch with a display",
    76: "a stopwatch with a hand",
    77: "a piano with a small clock",
    78: "a drum machine",
    79: "an hourglass and a progress bar",
    80: "a spinner of dots",
    81: "a pink children's watch",
    82: "a clock between a fork and a knife",
    83: "a shower timer",
    84: "a traffic light counting down",
    85: "a steaming alarm clock with a display",
    86: "a parking meter",
    87: "an hourglass in a frame",
    88: "a window with an hourglass",
    89: "a battery with a time",
    90: "a light bulb",
    91: "a rooster with a clock",
    92: "gears",
    93: "a water wheel",
    94: "a solar panel under the sun",
    95: "a zen garden with a ball",
    96: "an atom with orbits",
    97: "a holographic cube with a time",
    98: "a crystal with a time",
    99: "a globe hologram with a time",
    100: "a ring portal with a time",
}


def reduce(tile):
    """The tile scaled to 60 x 60, its colours from dark to light and each pixel's index."""
    scaled = tile.resize((SIZE, SIZE), Image.Resampling.BOX)
    pixels = numpy.asarray(scaled).astype(numpy.int32)
    quantized = scaled.quantize(colors=COLOURS, method=Image.Quantize.MEDIANCUT, kmeans=5, dither=Image.Dither.NONE)
    palette = numpy.array(quantized.getpalette()[: 3 * COLOURS], dtype=numpy.int32).reshape(-1, 3)
    used = sorted(set(numpy.asarray(quantized).flatten().tolist()))
    palette = palette[used]
    if ((pixels < DARK).all(axis=2)).any():
        nearest = int(numpy.argmin((palette ** 2).sum(axis=1)))
        palette[nearest] = (0, 0, 0)
    palette = numpy.unique(palette, axis=0)
    order = numpy.argsort(palette @ numpy.array([299, 587, 114]), kind="stable")
    palette = palette[order]
    distance = ((pixels[:, :, None, :] - palette[None, None, :, :]) ** 2).sum(axis=3)
    indices = distance.argmin(axis=2)
    present = sorted(set(indices.flatten().tolist()))
    remap = {old: new for new, old in enumerate(present)}
    palette = palette[present]
    indices = numpy.vectorize(remap.get)(indices)
    return palette, indices


def image_of(palette, indices):
    return Image.fromarray(palette[indices].astype(numpy.uint8), "RGB")


def main():
    tiles, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    (out / "reduced").mkdir(parents=True, exist_ok=True)
    entries = []
    images = []
    for number in range(1, 101):
        name = f"clock-{number:03d}"
        tile = Image.open(tiles / f"{name}.png").convert("RGB")
        palette, indices = reduce(tile)
        image = image_of(palette, indices)
        image.save(out / "reduced" / f"{name}.png")
        images.append(image)
        kind = "dial" if number in DIALS else "display" if number in DISPLAYS else "motion"
        entries.append({
            "name": name, "tile": number, "kind": kind, "about": ABOUT[number],
            "palette": [int(r) * 65536 + int(g) * 256 + int(b) for r, g, b in palette.tolist()],
            "picture": ["".join(str(int(v)) for v in row) for row in indices.tolist()],
        })
    (out / "skeleton.json").write_text(json.dumps(entries, indent=1) + "\n", encoding="utf-8")
    scale = 3
    for row in range(10):
        sheet = Image.new("RGB", (10 * (SIZE * scale + 6), SIZE * scale + 22), (30, 30, 30))
        draw = ImageDraw.Draw(sheet)
        for column in range(10):
            number = row * 10 + column + 1
            x = column * (SIZE * scale + 6) + 3
            sheet.paste(images[number - 1].resize((SIZE * scale, SIZE * scale), Image.Resampling.NEAREST), (x, 20))
            draw.text((x, 4), f"{number} {entries[number - 1]['kind']} {len(entries[number - 1]['palette'])}c", fill=(255, 255, 255))
        sheet.save(out / f"sheet-reduced-{row + 1}.png")
    print(f"{len(entries)} tiles: {sum(e['kind'] == 'dial' for e in entries)} dials, "
          f"{sum(e['kind'] == 'display' for e in entries)} displays, {sum(e['kind'] == 'motion' for e in entries)} motions")


if __name__ == "__main__":
    main()

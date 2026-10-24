"""Write the source of the snake tests and encode it with the converter into its embedded
bytes; with --check, compare both with what would be written."""
import argparse
import json
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'core/assets/mapping-snakes.json'
INCLUDE = ROOT / 'core/src/snakes_data.h'
SIDE = 60
SNAKES = 20
WHITE = 0xFFFFFF


def picture(snake):
    """Snake n's picture: on the 60 x 60 canvas, white at (3n-2 + (y-1) // 20, y) for every
    y from 1 to 60, black elsewhere. The pixels go row by row from the bottom row, each row
    from the left, as the format has them."""
    pixels = [0] * (SIDE * SIDE)
    for y in range(1, SIDE + 1):
        x = 3 * snake - 2 + (y - 1) // 20
        pixels[(y - 1) * SIDE + (x - 1)] = WHITE
    return pixels


def source_text():
    frames = [{"ms": 1000, "pixels": picture(snake)} for snake in range(1, SNAKES + 1)]
    return json.dumps({"version": 1, "width": SIDE, "height": SIDE, "frames": frames}, separators=(',', ':')) + '\n'


def generated(source):
    with tempfile.TemporaryDirectory() as folder:
        given = pathlib.Path(folder) / 'snakes.json'
        given.write_text(source)
        out = pathlib.Path(folder) / 'snakes.odrg'
        subprocess.run(['node', str(ROOT / 'converter/odrig.js'), 'encode', str(given), str(out)], check=True, capture_output=True)
        data = out.read_bytes()
    rows = [', '.join(f'0x{byte:02x}' for byte in data[at:at + 16]) for at in range(0, len(data), 16)]
    return 'static const uint8_t kSnakeTests[] = {\n    ' + ',\n    '.join(rows) + '\n};\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source = source_text()
    include = generated(source)
    if args.check:
        if not SOURCE.exists() or SOURCE.read_text() != source:
            raise SystemExit('mapping-snakes.json differs from its rule; run python3 core/snakes.py')
        if not INCLUDE.exists() or INCLUDE.read_text() != include:
            raise SystemExit('snakes_data.h differs from the converter output; run python3 core/snakes.py')
    else:
        SOURCE.write_text(source)
        INCLUDE.write_text(include)

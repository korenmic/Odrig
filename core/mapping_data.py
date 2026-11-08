"""Hold the installation's mapping file in the core and maintain its embedded bytes."""
import argparse
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'mapping/legs-20.json'
INCLUDE = ROOT / 'core/src/mapping_data.h'


def generated():
    data = SOURCE.read_bytes()
    rows = [', '.join(f'0x{byte:02x}' for byte in data[at:at+16]) for at in range(0, len(data), 16)]
    return 'static const uint8_t kBuiltInMapping[] = {\n    ' + ',\n    '.join(rows) + '\n};\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = generated()
    if args.check:
        if not INCLUDE.exists() or INCLUDE.read_text() != text:
            raise SystemExit('mapping_data.h differs from mapping/legs-20.json; run python3 core/mapping_data.py')
    else:
        INCLUDE.write_text(text, newline='\n')

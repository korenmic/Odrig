"""Encode the diagnostic source with the converter and maintain its embedded bytes."""
import argparse
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'animations/mapping-diagonal.json'
INCLUDE = ROOT / 'core/src/diagonal_data.h'


def generated():
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder) / 'diagonal.odrg'
        subprocess.run(['node', str(ROOT / 'converter/odrig.js'), 'encode', str(SOURCE), str(out)], check=True, capture_output=True)
        data = out.read_bytes()
    rows = [', '.join(f'0x{byte:02x}' for byte in data[at:at+16]) for at in range(0,len(data),16)]
    return 'static const uint8_t kDiagonal[] = {\n    ' + ',\n    '.join(rows) + '\n};\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = generated()
    if args.check:
        if not INCLUDE.exists() or INCLUDE.read_text() != text:
            raise SystemExit('diagonal_data.h differs from the converter output; run python3 core/diagonal.py')
    else:
        INCLUDE.write_text(text)

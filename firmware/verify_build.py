"""Inspect the default build offline; never open a board or a serial port."""
import json
import struct
import sys

from fwtool import Failure, build, env, paths, process, provenance, wled


def checked(image):
    build.checked_image(image)
    build.check_size(image)
    data = image.read_bytes()
    if len(data) < 24 or data[0] != 0xE9 or not 1 <= data[1] <= 16 or struct.unpack_from('<H', data, 12)[0] != 9:
        raise Failure('build-failed', 'the image header is not an ESP32-S3 application')
    record = json.loads(provenance.beside(image).read_text(encoding='utf-8'))
    if record['image']['sha256'] != provenance.digest(image) or record['image']['bytes'] != len(data):
        raise Failure('build-failed', 'the image does not match its provenance')
    if record['wled']['commit'] != wled.COMMIT or record['environment'] != 'odrig_microsd':
        raise Failure('build-failed', 'the image uses a different vendor source or environment')
    if record['inputs'] != provenance.source_inputs() or record['source']['commit'] != provenance.git_identity()['commit']:
        raise Failure('build-failed', 'the image was built from different current sources')
    return record


def inspect():
    image = build.image_path('firmware')
    record = checked(image)
    image_info = process.run([paths.PYTHON, '-m', 'esptool', '--chip', 'esp32s3', 'image-info', image],
                             env=env.child(), capture_output=True, text=True, check=True)
    (paths.OUT / 'image-info.txt').write_text(image_info.stdout, encoding='utf-8', newline='\n')
    tools = sorted(file for file in (paths.NEWER_PIO_CORE / 'packages').glob('*/bin/*-nm*')
                   if file.is_file() and file.name.startswith('xtensa-') and file.name.endswith(('-nm', '-nm.exe')))
    if not tools:
        raise Failure('build-failed', 'the selected cross compiler has no symbol inspector')
    elf = paths.WLED / '.pio' / 'build' / 'odrig_microsd' / 'firmware.elf'
    symbols = process.run([tools[0], '-C', elf], env=env.child(newer=True), capture_output=True, text=True, check=True)
    required = ('odrig_core_begin', 'odrig_core_poll', 'odrig_core_feed')
    lines = [line for line in symbols.stdout.splitlines() if any(name in line for name in required)]
    if any(not any(name in line for line in lines) for name in required):
        raise Failure('build-failed', 'the ELF does not contain the current player entry points')
    report = dict(version=1, source=record['source'], host=record['host'], inputsSha256=record['inputs']['sha256'],
                  image=record['image'], elf=dict(bytes=elf.stat().st_size, sha256=provenance.digest(elf)),
                  chip='ESP32-S3', environment=record['environment'],
                  symbolTool=tools[0].name, symbols=lines, physicalAcceptance=False)
    (paths.OUT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        inspect()
    except (Failure, OSError, ValueError, KeyError) as error:
        print(f'build inspection failed: {error}', file=sys.stderr)
        raise SystemExit(1)

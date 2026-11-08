"""Inspect the default build offline, or the spare's; never open a board or a serial port."""
import argparse
import collections
import json
import struct
import sys

from fwtool import Failure, build, env, paths, process, provenance, wled

# The modules the firmware is built for, by name: the kind of the image, its environment, the
# flash size its header says, the high nibble of byte 3, the release name among its bytes,
# and the suffix of the files written beside it.
Module = collections.namedtuple('Module', 'kind environment flash_size release suffix')
MODULES = {
    'n16r8': Module('firmware', 'odrig_microsd', 0x4, 'odrig_ESP32-S3_16MB_opi', ''),
    'n8r2': Module('n8r2', 'odrig_microsd_n8r2', 0x3, 'odrig_ESP32-S3_8MB_qspi', '-n8r2'),
}


def checked(image, module):
    build.checked_image(image)
    build.check_size(image)
    data = image.read_bytes()
    if len(data) < 24 or data[0] != 0xE9 or not 1 <= data[1] <= 16 or struct.unpack_from('<H', data, 12)[0] != 9:
        raise Failure('build-failed', 'the image header is not an ESP32-S3 application')
    if data[3] >> 4 != module.flash_size:
        raise Failure('build-failed', "the image header says a flash size that is not the module's")
    if module.release.encode('ascii') not in data:
        raise Failure('build-failed', 'the image does not hold the release name of its module')
    if any(other.release.encode('ascii') in data for other in MODULES.values() if other != module):
        raise Failure('build-failed', 'the image holds the release name of the other module')
    record = json.loads(provenance.beside(image).read_text(encoding='utf-8'))
    if record['image']['sha256'] != provenance.digest(image) or record['image']['bytes'] != len(data):
        raise Failure('build-failed', 'the image does not match its provenance')
    if record['wled']['commit'] != wled.COMMIT or record['environment'] != module.environment:
        raise Failure('build-failed', 'the image uses a different vendor source or environment')
    if record['inputs'] != provenance.source_inputs() or record['source']['commit'] != provenance.git_identity()['commit']:
        raise Failure('build-failed', 'the image was built from different current sources')
    return record


def inspect(name):
    module = MODULES[name]
    image = build.image_path(module.kind)
    record = checked(image, module)
    image_info = process.run([paths.PYTHON, '-m', 'esptool', '--chip', 'esp32s3', 'image-info', image],
                             env=env.child(), capture_output=True, text=True, check=True)
    (paths.OUT / f'image-info{module.suffix}.txt').write_text(image_info.stdout, encoding='utf-8', newline='\n')
    tools = sorted(file for file in (paths.NEWER_PIO_CORE / 'packages').glob('*/bin/*-nm*')
                   if file.is_file() and file.name.startswith('xtensa-') and file.name.endswith(('-nm', '-nm.exe')))
    if not tools:
        raise Failure('build-failed', 'the selected cross compiler has no symbol inspector')
    elf = paths.WLED / '.pio' / 'build' / module.environment / 'firmware.elf'
    symbols = process.run([tools[0], '-C', elf], env=env.child(newer=True), capture_output=True, text=True, check=True)
    required = ('odrig_core_begin', 'odrig_core_poll', 'odrig_core_feed')
    lines = [line for line in symbols.stdout.splitlines() if any(name in line for name in required)]
    if any(not any(name in line for line in lines) for name in required):
        raise Failure('build-failed', 'the ELF does not contain the current player entry points')
    report = dict(version=1, source=record['source'], host=record['host'], inputsSha256=record['inputs']['sha256'],
                  image=record['image'], elf=dict(bytes=elf.stat().st_size, sha256=provenance.digest(elf)),
                  chip='ESP32-S3', environment=record['environment'],
                  symbolTool=tools[0].name, symbols=lines, physicalAcceptance=False)
    (paths.OUT / f'verification{module.suffix}.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', choices=sorted(MODULES), default=build.DEFAULT_MODULE,
                        help="the module the image was built for: the installation's board, the default, or the spare's")
    arguments = parser.parse_args()
    try:
        inspect(arguments.module)
    except (Failure, OSError, ValueError, KeyError) as error:
        print(f'build inspection failed: {error}', file=sys.stderr)
        raise SystemExit(1)

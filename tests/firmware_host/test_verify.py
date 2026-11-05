import contextlib
import io
import json
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from fwtool import Failure, build, paths, process, provenance
import verify_build

IDENTITY = dict(commit='a' * 40, trackedDirty=False)
TOOLS = dict(python='Python 3.12.0', platformio='PlatformIO Core, version 6.1.0', node='v20.0.0', npm='10.0.0')
INPUTS = dict(sha256='f' * 64, files={'core/player.cpp': 'e' * 64})


@contextlib.contextmanager
def known_sources():
    """The source identity, the tool versions and the inputs of a build on a clean tree, the
    same when the record is written and when the image is checked against it."""
    with mock.patch.object(provenance, 'git_identity', return_value=dict(IDENTITY)), \
         mock.patch.object(provenance, 'versions', return_value=dict(TOOLS)), \
         mock.patch.object(provenance, 'source_inputs', return_value=dict(INPUTS)):
        yield


def other_than(name):
    return next(module for other, module in verify_build.MODULES.items() if other != name)


def image_of(module, flash_size=None, names=None):
    """An image of a module in `paths.OUT`, with its checksum beside it: an ESP32-S3 header
    whose byte 3 says the flash size in its high nibble, and the release names among its
    bytes, the module's own unless others are given."""
    data = bytearray(24)
    data[0], data[1], data[2] = 0xE9, 3, 2
    data[3] = (module.flash_size if flash_size is None else flash_size) << 4 | 0xF
    struct.pack_into('<H', data, 12, 9)
    for name in [module.release] if names is None else names:
        data += b'\0' + name.encode('ascii')
    data += bytes(40)
    image = build.image_path(module.kind)
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(bytes(data))
    build.write_checksum(image)
    return image


def record_of(image, name, environment=None):
    module = verify_build.MODULES[name]
    with known_sources():
        provenance.write(module.kind, module.environment if environment is None else environment, image, True, module=name)


class Modules(unittest.TestCase):
    def test_each_module_names_its_kind_environment_flash_size_release_name_and_suffix(self):
        self.assertEqual(verify_build.Module._fields, ('kind', 'environment', 'flash_size', 'release', 'suffix'))
        self.assertEqual(verify_build.MODULES, {
            'n16r8': ('firmware', 'odrig_microsd', 0x4, 'odrig_ESP32-S3_16MB_opi', ''),
            'n8r2': ('n8r2', 'odrig_microsd_n8r2', 0x3, 'odrig_ESP32-S3_8MB_qspi', '-n8r2')})
        self.assertEqual(sorted(verify_build.MODULES), sorted(build.MODULES))
        self.assertIn(build.DEFAULT_MODULE, verify_build.MODULES)
        for name, module in verify_build.MODULES.items():
            self.assertEqual(build.KINDS[module.kind].environment, module.environment)
            self.assertEqual(build.module_of(module.kind), name)


class Checked(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix='odrig-fw-verify-')
        self.addCleanup(folder.cleanup)
        patched = mock.patch.object(paths, 'OUT', pathlib.Path(folder.name) / 'out')
        patched.start()
        self.addCleanup(patched.stop)

    def checked(self, image, name):
        with known_sources():
            return verify_build.checked(image, verify_build.MODULES[name])

    def refused(self, image, name, detail):
        with self.assertRaises(Failure) as caught:
            self.checked(image, name)
        self.assertEqual((caught.exception.reason, caught.exception.detail), ('build-failed', detail))

    def test_an_image_of_each_module_passes_with_its_provenance(self):
        for name, module in verify_build.MODULES.items():
            with self.subTest(module=name):
                image = image_of(module)
                record_of(image, name)
                record = self.checked(image, name)
                self.assertEqual((record['kind'], record['environment'], record['module']), (module.kind, module.environment, name))
                self.assertEqual(image.name, build.KINDS[module.kind].image)

    def test_a_header_of_the_other_modules_flash_size_is_refused(self):
        for name, module in verify_build.MODULES.items():
            with self.subTest(module=name):
                image = image_of(module, flash_size=other_than(name).flash_size)
                record_of(image, name)
                self.refused(image, name, "the image header says a flash size that is not the module's")

    def test_bytes_that_hold_the_other_modules_release_name_are_refused(self):
        for name, module in verify_build.MODULES.items():
            with self.subTest(module=name):
                image = image_of(module, names=[module.release, other_than(name).release])
                record_of(image, name)
                self.refused(image, name, 'the image holds the release name of the other module')

    def test_bytes_that_hold_no_release_name_of_the_module_are_refused(self):
        for name, module in verify_build.MODULES.items():
            for names in ([], [other_than(name).release]):
                with self.subTest(module=name, names=names):
                    image = image_of(module, names=names)
                    record_of(image, name)
                    self.refused(image, name, 'the image does not hold the release name of its module')

    def test_a_provenance_of_the_other_modules_environment_is_refused(self):
        for name, module in verify_build.MODULES.items():
            with self.subTest(module=name):
                image = image_of(module)
                record_of(image, name, environment=other_than(name).environment)
                self.refused(image, name, 'the image uses a different vendor source or environment')

    def test_a_header_that_is_not_an_application_is_refused_before_its_flash_size(self):
        module = verify_build.MODULES['n8r2']
        image = image_of(module, flash_size=other_than('n8r2').flash_size)
        image.write_bytes(image.read_bytes()[:20])
        build.write_checksum(image)
        record_of(image, 'n8r2')
        self.refused(image, 'n8r2', 'the image header is not an ESP32-S3 application')


class Inspect(unittest.TestCase):
    def test_it_writes_the_files_of_its_module_beside_the_image(self):
        for name, module in verify_build.MODULES.items():
            with self.subTest(module=name), tempfile.TemporaryDirectory(prefix='odrig-fw-inspect-') as folder:
                root = pathlib.Path(folder)
                elf = root / 'WLED' / '.pio' / 'build' / module.environment / 'firmware.elf'
                elf.parent.mkdir(parents=True)
                elf.write_bytes(b'linked for ' + name.encode('ascii'))
                nm = root / 'newer-pio' / 'packages' / 'toolchain-xtensa-esp-elf' / 'bin' / 'xtensa-esp-elf-nm'
                nm.parent.mkdir(parents=True)
                nm.write_bytes(b'')
                commands = []

                def ran(command, **kwargs):
                    commands.append(command)
                    if command[1:3] == ['-m', 'esptool']:
                        return subprocess.CompletedProcess(command, 0, f'Flash size: {8 if name == "n8r2" else 16}MB\n', '')
                    return subprocess.CompletedProcess(command, 0, '40370000 T odrig_core_begin\n40370010 T odrig_core_feed\n'
                                                                   '40370020 T odrig_core_poll\n40370030 T loop\n', '')
                with mock.patch.object(paths, 'OUT', root / 'out'), mock.patch.object(paths, 'WLED', root / 'WLED'), \
                     mock.patch.object(paths, 'NEWER_PIO_CORE', root / 'newer-pio'), \
                     mock.patch.object(process, 'run', side_effect=ran), known_sources(), \
                     contextlib.redirect_stdout(io.StringIO()) as printed:
                    image = image_of(module)
                    record_of(image, name)
                    verify_build.inspect(name)
                self.assertEqual(len(commands), 2)
                self.assertEqual(commands[0][:3] + [commands[0][-1]], [paths.PYTHON, '-m', 'esptool', image])
                self.assertEqual(commands[1], [nm, '-C', elf])
                self.assertEqual((root / 'out' / f'image-info{module.suffix}.txt').read_bytes(),
                                 f'Flash size: {8 if name == "n8r2" else 16}MB\n'.encode('ascii'))
                report = json.loads((root / 'out' / f'verification{module.suffix}.json').read_bytes())
                self.assertEqual((report['environment'], report['chip'], report['symbolTool']), (module.environment, 'ESP32-S3', nm.name))
                self.assertEqual(report['image'], dict(file=image.name, bytes=image.stat().st_size, sha256=provenance.digest(image)))
                self.assertEqual(report['elf'], dict(bytes=elf.stat().st_size, sha256=provenance.digest(elf)))
                self.assertEqual(len(report['symbols']), 3)
                self.assertEqual(json.loads(printed.getvalue()), report)
                self.assertEqual(sorted(file.name for file in (root / 'out').iterdir()),
                                 sorted([image.name, image.name + '.sha256', image.name + '.build.json',
                                         f'image-info{module.suffix}.txt', f'verification{module.suffix}.json']))


class TheOption(unittest.TestCase):
    def test_a_module_that_is_not_known_is_refused_by_the_choices(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-verify-option-') as folder:
            done = subprocess.run([sys.executable, '-B', verify_build.__file__, '--module', 'n4r2'], capture_output=True,
                                  text=True, env=dict(os.environ, ODRIG_TOOLS=folder))
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIn("invalid choice: 'n4r2'", done.stderr)
        for name in verify_build.MODULES:
            self.assertIn(name, done.stderr)

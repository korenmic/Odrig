import json
import concurrent.futures
import pathlib
import shlex
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

from fwtool import build, paths, standalone, wled


class PortableConfiguration(unittest.TestCase):
    def test_wled_paths_with_spaces_remain_whole_dependency_and_include_arguments(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-config-') as folder:
            root=pathlib.Path(folder,'source with spaces');root.mkdir()
            text=wled.override_text(root)
            self.assertIn('symlink://'+root.resolve().as_posix()+'/core',text)
            include=next(line.strip() for line in text.splitlines() if '/core/include' in line)
            self.assertEqual(shlex.split(include),['-I'+(root.resolve()/'core'/'include').as_posix()])
            forced=next(line.strip() for line in text.splitlines() if 'odrig_newer.h' in line)
            self.assertEqual(shlex.split(forced),['-include',(root.resolve()/'firmware'/'newer'/'odrig_newer.h').as_posix()])

    def test_standalone_paths_with_spaces_preserve_the_same_source_and_partition_file(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-standalone-') as folder:
            root=pathlib.Path(folder,'source with spaces');root.mkdir()
            checkout=pathlib.Path(folder,'WLED with spaces');checkout.mkdir()
            text=standalone.project_text(root,checkout)
            self.assertIn('src_dir = '+(root.resolve()/'firmware'/'standalone'/'src').as_posix(),text)
            self.assertIn('board_build.partitions = '+(checkout.resolve()/'tools'/'WLED_ESP32_16MB_9MB_FS.csv').as_posix(),text)
            include=next(line.strip() for line in text.splitlines() if '/core/include' in line)
            self.assertEqual(shlex.split(include),['-I'+(root.resolve()/'core'/'include').as_posix()])

    def test_checksum_companion_is_utf8_with_lf_on_every_host(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-checksum-') as folder:
            image=pathlib.Path(folder,'firmware.bin');image.write_bytes(b'image')
            build.write_checksum(image)
            self.assertEqual(build.checksum_path(image).read_bytes(),(build.sha256(image)+'  firmware.bin\n').encode('utf-8'))

    def test_compilation_concurrency_is_explicitly_bounded(self):
        command=build.pio_command('odrig_microsd')
        self.assertIn('-j',command)
        self.assertGreaterEqual(int(command[command.index('-j')+1]),1)
        self.assertLessEqual(int(command[command.index('-j')+1]),4)


class VariantBuilds(unittest.TestCase):
    def test_builds_of_one_checkout_serialize_mutation_and_compilation(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-serialized-') as directory:
            active=0;maximum=0;guard=threading.Lock()
            def compiled(*args):
                nonlocal active,maximum
                with guard:active+=1;maximum=max(active,maximum)
                time.sleep(0.1)
                with guard:active-=1
                return pathlib.Path(directory,'image.bin'),1
            with mock.patch.object(paths,'BUILD_LOCK',pathlib.Path(directory,'build.lock')), \
                 mock.patch.object(build.toolchain,'python_environment'),mock.patch.object(build.toolchain,'newer_environment'), \
                 mock.patch.object(build,'_build',side_effect=compiled):
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    results=list(pool.map(build.build,['firmware','probe']))
            self.assertEqual(len(results),2)
            self.assertEqual(maximum,1)

    def test_every_existing_variant_keeps_its_environment_output_and_software_family(self):
        expected={'firmware':('odrig_microsd','odrig-firmware.bin',True),
                  'microsd':('odrig_microsd','odrig-microsd.bin',True),
                  'probe':('odrig_microsd_probe','odrig-probe.bin',True),
                  'stock':('esp32s3dev_16MB_opi','stock-built.bin',False),
                  'stick':('odrig','odrig-stick.bin',False),
                  'stick-probe':('odrig_probe','odrig-stick-probe.bin',False),
                  'standalone':('odrig_standalone','odrig-standalone.bin',False),
                  'standalone-probe':('odrig_standalone_probe','odrig-standalone-probe.bin',False)}
        self.assertEqual(set(build.KINDS),set(expected))
        for kind,(environment,name,newer) in expected.items():
            with self.subTest(kind=kind),tempfile.TemporaryDirectory(prefix='odrig-fw-variant-') as directory:
                root=pathlib.Path(directory)
                def compiled(command,**kwargs):
                    folder=pathlib.Path(command[command.index('-d')+1])
                    target=folder/'.pio'/'build'/environment/'firmware.bin'
                    target.parent.mkdir(parents=True);target.write_bytes(b'compiled')
                    self.assertEqual(command[0],str(paths.NEWER_PYTHON if newer else paths.PYTHON))
                    return subprocess.CompletedProcess(command,0)
                with mock.patch.object(paths,'WLED',root/'WLED'),mock.patch.object(paths,'OUT',root/'out'), \
                     mock.patch.object(paths,'BUILD_LOCK',root/'build.lock'), \
                     mock.patch.object(build.toolchain,'python_environment') as base_setup, \
                     mock.patch.object(build.toolchain,'newer_environment') as newer_setup, \
                     mock.patch.object(wled,'restore_and_patch') as restore,mock.patch.object(wled,'write_override'), \
                     mock.patch.object(wled,'check'),mock.patch.object(standalone,'write_project',return_value=root/'standalone'), \
                     mock.patch.object(build.process,'run',side_effect=compiled),mock.patch.object(build.provenance,'write') as recorded:
                    image,size=build.build(kind)
                    self.assertEqual((image.name,size),(name,8))
                    self.assertEqual(build.checked_image(image),image)
                    base_setup.assert_called_once()
                    self.assertEqual(newer_setup.call_count,int(newer))
                    if kind.startswith('standalone'):restore.assert_not_called()
                    else:restore.assert_called_once_with(patches=None if kind=='stock' else paths.PATCHES)
                    recorded.assert_called_once_with(kind,environment,image,newer)

    def test_pinned_package_manager_links_spaced_current_sources_without_os_symlinks(self):
        if not paths.PYTHON.is_file():self.skipTest('pinned PlatformIO is not installed; run firmware setup for package integration')
        code='''import json,pathlib,sys,tempfile,unittest.mock
try:
 from platformio.package.manager.library import LibraryPackageManager
 from platformio.package.meta import PackageSpec
except ImportError:
 sys.exit(77)
with tempfile.TemporaryDirectory(prefix='odrig-pio-links-') as folder:
 root=pathlib.Path(folder); source=root/'source with spaces';source.mkdir()
 (source/'library.json').write_text(json.dumps(dict(name='current_core',version='1.0.0')),encoding='utf-8')
 file=source/'current.cpp';file.write_bytes(b'current one')
 manager=LibraryPackageManager(str(root/'libdeps'))
 with unittest.mock.patch('os.symlink',side_effect=AssertionError('privileged OS symlink attempted')):
  package=manager.install(PackageSpec('current_core = symlink://'+source.as_posix()),skip_dependencies=True)
  assert pathlib.Path(package.path).resolve()==source.resolve()
  file.write_bytes(b'current two')
  assert (pathlib.Path(package.path)/'current.cpp').read_bytes()==b'current two'
  assert list((root/'libdeps').glob('*.pio-link'))
print('portable current-source link verified')
'''
        result=build.process.run([str(paths.PYTHON),'-c',code],capture_output=True,text=True,env=build.env.child())
        if result.returncode==77:self.skipTest('pinned PlatformIO is not installed; run firmware setup for package integration')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('portable current-source link verified',result.stdout)

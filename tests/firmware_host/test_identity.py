import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from fwtool import Failure, host, paths, toolchain, wled


class Identity(unittest.TestCase):
    def test_host_aliases_and_native_programs(self):
        for system, machine, expected in [('win32','AMD64','x86_64'), ('darwin','aarch64','arm64'),
                                          ('darwin','x86_64','x86_64'), ('linux','aarch64','arm64')]:
            self.assertEqual(host.supported(system,machine),(system,expected))
            base=pathlib.Path('tools with spaces')
            expected_program=base/'Scripts'/'python.exe' if system=='win32' else base/'bin'/'python'
            self.assertEqual(host.program(base,'python',system),expected_program)

    def test_other_hosts_fail_before_a_fetch_or_install(self):
        with mock.patch.object(host,'identity',return_value=('win32','arm64')), mock.patch.object(wled,'fetch') as fetched:
            with self.assertRaises(Failure) as caught: toolchain.python_environment()
            self.assertEqual(caught.exception.reason,'unsupported-platform')
            fetched.assert_not_called()

    def test_mac_paths_stay_compatible_and_other_host_caches_are_distinct(self):
        base=pathlib.Path('shared tools')
        self.assertEqual(host.tool_root(base,'darwin','arm64'),base)
        win=host.tool_root(base,'win32','AMD64')
        linux=host.tool_root(base,'linux','x86_64')
        self.assertEqual(len({base,win,linux}),3)
        self.assertTrue(win.is_relative_to(base) and linux.is_relative_to(base))

    def test_stamps_depend_on_host_and_requirement_bytes(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-host-stamp-') as folder:
            file=pathlib.Path(folder,'requirements.txt');file.write_bytes(b'tool==1\n')
            with mock.patch.object(toolchain,'requirement_files',return_value=[file]):
                with mock.patch.object(host,'supported',return_value=('win32','x86_64')): one=toolchain._wanted()
                with mock.patch.object(host,'supported',return_value=('darwin','arm64')): two=toolchain._wanted()
        self.assertNotEqual(one,two)


class AtomicSetup(unittest.TestCase):
    def test_newer_environment_stamps_only_completed_pinned_installation(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-newer-stamp-') as folder:
            root=pathlib.Path(folder)
            python=root/'python.exe';python.touch()
            requirements=root/'requirements.txt';requirements.write_bytes(b'platformio==6.2.0\n')
            stamp=root/'stamp'
            with mock.patch.object(paths,'NEWER_PYTHON',python), mock.patch.object(paths,'NEWER_REQUIREMENTS',requirements), \
                 mock.patch.object(toolchain,'NEWER_STAMP',stamp), mock.patch.object(toolchain,'_run') as run:
                run.side_effect=Failure('setup-failed','simulated newer package failure')
                with self.assertRaises(Failure):toolchain._newer_environment()
                self.assertFalse(stamp.exists())
                run.side_effect=None
                self.assertEqual(toolchain._newer_environment(),['installed the newer software\'s Python packages'])
                command=run.call_args.args[1]
                self.assertEqual(command[0],python)
                self.assertEqual(command[-1],requirements)
                self.assertTrue(run.call_args.kwargs['newer'])
                self.assertEqual(len(stamp.read_text(encoding='utf-8').strip()),64)
                calls=run.call_count
                self.assertEqual(toolchain._newer_environment(),[])
                self.assertEqual(run.call_count,calls)

    def test_failed_packages_never_mark_an_environment_ready_and_retry_is_idempotent(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-stamp-') as folder:
            root=pathlib.Path(folder)
            stamp=root/'stamp'
            first,second=root/'first.txt',root/'second.txt'
            first.write_bytes(b'one==1\n');second.write_bytes(b'two==2\n')
            python=root/'python.exe';python.touch()
            calls=[]
            fail=True
            def run(what, command):
                calls.append(command)
                if command[-1]==second and fail: raise Failure('setup-failed','simulated package failure')
                return ''
            with mock.patch.object(wled,'fetch',return_value=False), mock.patch.object(wled,'check'), \
                 mock.patch.object(wled,'copy',return_value=False), mock.patch.object(paths,'PYTHON',python), \
                 mock.patch.object(toolchain,'STAMP',stamp), mock.patch.object(toolchain,'requirement_files',return_value=[first,second]), \
                 mock.patch.object(toolchain,'_run',side_effect=run):
                with self.assertRaises(Failure): toolchain._python_environment()
                self.assertFalse(stamp.exists())
                fail=False
                self.assertEqual(toolchain._python_environment(),['installed the Python packages'])
                self.assertEqual(stamp.read_bytes(),(toolchain._wanted()+'\n').encode('utf-8'))
                count=len(calls)
                self.assertEqual(toolchain._python_environment(),[])
                self.assertEqual(len(calls),count)
            self.assertEqual([str(c[-1]) for c in calls],[str(first),str(second)]*2)

    def test_failed_wled_clone_is_not_published_as_a_reusable_source(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-fetch-') as folder:
            target=pathlib.Path(folder,'WLED')
            def failed(command,**kwargs):
                partial=pathlib.Path(command[-1]);partial.mkdir(exist_ok=True)
                (partial/'incomplete').write_bytes(b'partial download')
                return subprocess.CompletedProcess(command,1,'','network failed')
            with mock.patch.object(wled.process,'run',side_effect=failed):
                with self.assertRaises(Failure): wled.fetch(target)
            self.assertFalse(target.exists(),'a failed clone was published in the reusable cache')

    def test_checked_wled_identity_is_never_bypassed_on_another_host(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-pin-') as folder:
            answers=[subprocess.CompletedProcess([],0,str(pathlib.Path(folder).resolve())+'\n',''),
                     subprocess.CompletedProcess([],0,'0'*40+'\n','')]
            with mock.patch.object(wled,'_git',side_effect=answers):
                with self.assertRaises(Failure) as caught: wled.check(folder)
            self.assertEqual(caught.exception.reason,'wled-mismatch')

    def test_copy_preserves_an_unrelated_preexisting_partial_folder(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-copy-') as folder:
            root=pathlib.Path(folder)
            source=root/'source';source.mkdir();(source/'tracked').write_bytes(b'current source')
            destination=root/'checkout'
            unrelated=root/'checkout.partial';unrelated.mkdir()
            marker=unrelated/'belongs-to-someone-else';marker.write_bytes(b'keep')
            with mock.patch.object(wled,'copy_command',return_value=None):
                self.assertTrue(wled.copy(source,destination))
            self.assertTrue(marker.is_file(),'copy removed an unrelated preexisting folder')
            self.assertEqual((destination/'tracked').read_bytes(),b'current source')

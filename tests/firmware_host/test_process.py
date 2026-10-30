import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from fwtool import Failure, process, toolchain
from .test_setup import alive, end_owned
from . import ROOT


def parent_code(end):
    return (
        'import json,os,pathlib,subprocess,sys,time; '
        'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"], '
        'stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL, '
        'creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)); '
        'pathlib.Path(sys.argv[1]).write_text(json.dumps([os.getpid(),p.pid]),encoding="utf-8"); '
        + end
    )


class OwnedProcesses(unittest.TestCase):
    def assert_ended(self, ids):
        deadline=time.monotonic()+3
        while any(alive(pid) for pid in ids) and time.monotonic()<deadline: time.sleep(0.02)
        self.assertFalse(any(alive(pid) for pid in ids),f'owned processes remained: {ids}')

    def case(self, action):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-owner-') as folder:
            pidfile=pathlib.Path(folder,'paths with spaces.json')
            try:
                action(pidfile)
                self.assertTrue(pidfile.is_file(),'parent never reached child creation')
                self.assert_ended(json.loads(pidfile.read_text(encoding='utf-8')))
            finally:
                if pidfile.exists():
                    for pid in json.loads(pidfile.read_text(encoding='utf-8')):end_owned(pid)

    def test_failed_parent_closes_its_descendants_and_keeps_useful_diagnostics(self):
        def failed(pidfile):
            with self.assertRaises(Failure) as caught:
                toolchain._run('compiler', [sys.executable,'-c',parent_code('print("compile failed",file=sys.stderr);sys.exit(7)'),str(pidfile)])
            self.assertEqual(caught.exception.reason,'setup-failed')
            self.assertIn('status 7',caught.exception.detail)
            self.assertIn('compile failed',caught.exception.detail)
        self.case(failed)

    def test_timeout_ends_parent_and_child(self):
        def timed(pidfile):
            with self.assertRaises(subprocess.TimeoutExpired):
                process.run([sys.executable,'-c',parent_code('time.sleep(60)'),str(pidfile)],capture_output=True,timeout=3)
        self.case(timed)

    def test_parent_exit_closes_a_descendant_that_inherits_the_output_pipe(self):
        def inherited(pidfile):
            code=('import json,os,pathlib,subprocess,sys; '
                  'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],stdout=sys.stdout,stderr=sys.stderr, '
                  'creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)); '
                  'pathlib.Path(sys.argv[1]).write_text(json.dumps([os.getpid(),p.pid]),encoding="utf-8"); '
                  'print("parent finished",flush=True)')
            result=process.run([sys.executable,'-c',code,str(pidfile)],capture_output=True,text=True,timeout=2)
            self.assertEqual((result.returncode,result.stdout.strip()),(0,'parent finished'))
        self.case(inherited)

    def test_interruption_after_child_creation_ends_the_tree(self):
        def interrupted(pidfile):
            owned=[]
            def communicate(child,*args,**kwargs):
                owned.append(child)
                deadline=time.monotonic()+10
                while not pidfile.is_file() and time.monotonic()<deadline: time.sleep(0.02)
                raise KeyboardInterrupt()
            with mock.patch.object(subprocess.Popen,'communicate',communicate):
                with self.assertRaises(KeyboardInterrupt):
                    process.run([sys.executable,'-c',parent_code('time.sleep(60)'),str(pidfile)],capture_output=True)
            self.assertEqual(len(owned),1)
            for stream in (owned[0].stdin,owned[0].stdout,owned[0].stderr):
                if stream is not None:self.assertTrue(stream.closed,'interrupted tool left a pipe handle open')
        self.case(interrupted)

    def test_setup_text_is_utf8_and_arguments_keep_spaces_and_non_ascii(self):
        text='path with spaces caf\u00e9 \u20ac'
        said=toolchain._run('unicode tool', [sys.executable,'-c','import sys;print(sys.argv[1])',text])
        self.assertEqual(said.strip(),text)

    @unittest.skipUnless(sys.platform=='win32','Windows can have CRT streams without Win32 standard handles')
    def test_consoleless_launcher_preserves_its_python_output_streams(self):
        code=('import ctypes,sys;from fwtool import process; '
              'k=ctypes.WinDLL("kernel32"); '
              'k.SetStdHandle.argtypes=[ctypes.c_uint32,ctypes.c_void_p]; '
              'k.SetStdHandle(0xfffffff5,None);k.SetStdHandle(0xfffffff4,None); '
              'r=process.run([sys.executable,"-c","print(\\\"owned-output\\\",flush=True)"]); '
              'sys.exit(r.returncode)')
        childenv=dict(os.environ,PYTHONPATH=str(ROOT/'firmware'))
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,encoding='utf-8',
                              env=childenv,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'owned-output')

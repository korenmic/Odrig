import ctypes
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from fwtool import env, paths, toolchain


def alive(pid):
    if sys.platform == 'win32':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle: return False
        try: return kernel.WaitForSingleObject(handle, 0) == 258
        finally: kernel.CloseHandle(handle)
    stat=pathlib.Path('/proc',str(pid),'stat')
    if stat.is_file() and stat.read_text(encoding='utf-8').rpartition(')')[2].split()[0]=='Z': return False
    try: os.kill(pid, 0)
    except ProcessLookupError: return False
    return True


def end_owned(pid):
    if not alive(pid): return
    if sys.platform == 'win32':
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        os.kill(pid, signal.SIGTERM)


class NativeSetup(unittest.TestCase):
    def test_python_and_environment_path_use_native_executable_locations(self):
        scripts = 'Scripts' if sys.platform == 'win32' else 'bin'
        python = 'python.exe' if sys.platform == 'win32' else 'python'
        self.assertEqual(paths.PYTHON, paths.VENV / scripts / python)
        self.assertEqual(paths.NEWER_PYTHON, paths.NEWER_VENV / scripts / python)
        self.assertEqual(env.child({'PATH': ''})['PATH'], str(paths.VENV / scripts))

    def test_setup_ends_a_descendant_even_after_its_parent_succeeds(self):
        with tempfile.TemporaryDirectory(prefix='odrig-fw-process-') as folder:
            pidfile = pathlib.Path(folder, 'child.pid')
            code = (
                'import pathlib,subprocess,sys; '
                'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"], '
                'stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL, '
                'creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)); '
                'pathlib.Path(sys.argv[1]).write_text(str(p.pid),encoding="utf-8"); print("finished")'
            )
            pid = None
            try:
                self.assertEqual(toolchain._run('owned child', [sys.executable, '-c', code, str(pidfile)]).strip(), 'finished')
                pid = int(pidfile.read_text(encoding='utf-8'))
                deadline = time.monotonic() + 2
                while alive(pid) and time.monotonic() < deadline: time.sleep(0.02)
                self.assertFalse(alive(pid), 'setup left its owned compiler/Node descendant running')
            finally:
                if pid is None and pidfile.exists(): pid = int(pidfile.read_text(encoding='utf-8'))
                if pid is not None: end_owned(pid)

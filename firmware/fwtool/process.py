"""Run one owned process tree and close it on every outcome."""
import ctypes
import contextlib
import os
import signal
import subprocess
import sys
import threading

CREATE_SUSPENDED = 0x00000004

@contextlib.contextmanager
def interrupts_delayed():
    """Delay a main-thread Ctrl-C during a resource ownership transition."""
    previous = signal.getsignal(signal.SIGINT)
    enabled = threading.current_thread() is threading.main_thread() and callable(previous)
    pending = []
    if enabled: signal.signal(signal.SIGINT, lambda number, frame: pending.append((number, frame)))
    try:
        yield
    finally:
        if enabled: signal.signal(signal.SIGINT, previous)
    if pending: previous(*pending[-1])


class WindowsJob:
    def __init__(self):
        self.lock = threading.Lock()
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                        ('flags', w.DWORD), ('minimum', ctypes.c_size_t), ('maximum', ctypes.c_size_t),
                        ('active', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
        class Limits(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = w.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle: raise ctypes.WinError(ctypes.get_last_error())
        limits = Limits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.get_last_error()
            self.close()
            raise ctypes.WinError(error)

    def assign(self, child):
        if not self.kernel.AssignProcessToJobObject(self.handle, int(child._handle)):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        with self.lock:
            if self.handle:
                self.kernel.CloseHandle(self.handle)
                self.handle = None


def resume(pid):
    """Resume the suspended child's threads only after the job owns the process."""
    from ctypes import wintypes as w
    class Thread(ctypes.Structure):
        _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('tid', w.DWORD),
                    ('owner', w.DWORD), ('base_priority', w.LONG), ('delta_priority', w.LONG), ('flags', w.DWORD)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = w.HANDLE
    kernel.Thread32First.argtypes = [w.HANDLE, ctypes.POINTER(Thread)]
    kernel.Thread32Next.argtypes = [w.HANDLE, ctypes.POINTER(Thread)]
    kernel.OpenThread.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenThread.restype = w.HANDLE
    kernel.ResumeThread.argtypes = [w.HANDLE]
    kernel.ResumeThread.restype = w.DWORD
    kernel.CloseHandle.argtypes = [w.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(4, 0)
    if snapshot == ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
    found = Thread()
    found.size = ctypes.sizeof(found)
    resumed = 0
    try:
        more = kernel.Thread32First(snapshot, ctypes.byref(found))
        while more:
            if found.owner == pid:
                handle = kernel.OpenThread(2, False, found.tid)
                if not handle: raise ctypes.WinError(ctypes.get_last_error())
                try:
                    if kernel.ResumeThread(handle) == 0xffffffff:
                        raise ctypes.WinError(ctypes.get_last_error())
                    resumed += 1
                finally: kernel.CloseHandle(handle)
            more = kernel.Thread32Next(snapshot, ctypes.byref(found))
    finally: kernel.CloseHandle(snapshot)
    if not resumed: raise OSError(f'no suspended thread found for owned process {pid}')


def run(command, *, input=None, capture_output=False, text=False, timeout=None, check=False, **settings):
    """Like subprocess.run, with UTF-8 text and process-tree ownership."""
    if capture_output:
        if settings.get('stdout') is not None or settings.get('stderr') is not None: raise ValueError('capture_output with explicit streams')
        settings.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        if settings.get('stdout') is None: settings['stdout'] = sys.stdout
        if settings.get('stderr') is None: settings['stderr'] = sys.stderr
    if input is not None:
        if 'stdin' in settings: raise ValueError('input with explicit stdin')
        settings['stdin'] = subprocess.PIPE
    if text:
        settings.setdefault('encoding', 'utf-8')
        settings.setdefault('errors', 'replace')
    job = WindowsJob() if sys.platform == 'win32' else None
    child = None
    watcher = None
    tree_lock = threading.Lock()
    tree_closed = False
    def close_tree():
        nonlocal tree_closed
        with tree_lock:
            if tree_closed: return
            if job is not None:
                job.close()
            elif child is not None:
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            tree_closed = True
    def parent_ended():
        child.wait()
        close_tree()
    try:
        if job is not None:
            settings['creationflags'] = settings.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW | CREATE_SUSPENDED
        else:
            settings['start_new_session'] = True
        with interrupts_delayed():
            child = subprocess.Popen(command, text=text, **settings)
            if job is not None:
                job.assign(child)
                resume(child.pid)
            watcher = threading.Thread(target=parent_ended, name='firmware-owned-process', daemon=True)
            watcher.start()
        out, err = child.communicate(input, timeout=timeout)
        result = subprocess.CompletedProcess(command, child.returncode, out, err)
        if check: result.check_returncode()
        return result
    finally:
        with interrupts_delayed():
            try:
                close_tree()
                if child is not None:
                    if child.poll() is None: child.kill()
                    child.wait()
                if watcher is not None and watcher.ident is not None: watcher.join()
            finally:
                if child is not None:
                    for stream in (child.stdin, child.stdout, child.stderr):
                        if stream is not None: stream.close()

"""Whether a process still runs, by its id, on macOS, Linux and Windows: what an emulator
started with `--parent PID` watches, so that it ends when the program that started it is
gone, even when that program was killed without a chance to end it."""

import os
import sys
import threading

WINDOWS = sys.platform == "win32"


def alive(pid):
    if WINDOWS:
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 0x102  # WAIT_TIMEOUT: still running
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def watch(pid, stopped, every=1.0):
    """Sets `stopped` once the process `pid` has ended; checks every second, on a thread of
    its own that ends with the program."""

    def check():
        while not stopped.wait(every):
            if not alive(pid):
                stopped.set()

    threading.Thread(target=check, daemon=True).start()

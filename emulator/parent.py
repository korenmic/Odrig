"""Whether a process still runs, by its id, on macOS, Linux and Windows: what an emulator
started with `--parent PID` watches, so that it ends when the program that started it is
gone, even when that program was killed without a chance to end it."""

import os
import subprocess
import sys
import threading

WINDOWS = sys.platform == "win32"


def alive(pid):
    if WINDOWS:
        # Windows' own list of processes, filtered by the id: a line naming it while it runs.
        listed = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"], capture_output=True, text=True)
        return f'"{pid}"' in listed.stdout
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

"""The files of a show folder, handed out as the core asks for them."""

import collections
import os
import sys

LOG_LINES = 100


class FolderHost:
    """What the core needs from its host besides memory: one open file, and a place for
    its diagnostic lines."""

    def __init__(self, folder, verbose=False):
        self.folder = os.fspath(folder)
        self.verbose = verbose
        self.logged = collections.deque(maxlen=LOG_LINES)
        self._file = None

    def open(self, name):
        """1 when the file is open, 0 when the folder has no file of that name, -1 otherwise."""
        self.close()
        if not name or "/" in name or "\\" in name or os.sep in name or (os.altsep and os.altsep in name):
            return -1
        try:
            self._file = open(os.path.join(self.folder, name), "rb")
        except FileNotFoundError:
            return 0
        except OSError:
            return -1
        return 1

    def read(self, capacity):
        """Up to `capacity` bytes of the open file, none at its end, `None` on a failure."""
        if self._file is None:
            return None
        try:
            return self._file.read(capacity)
        except OSError:
            return None

    def close(self):
        if self._file is not None:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None

    def log(self, text):
        self.logged.append(text)
        if self.verbose:
            print(f"core: {text}", file=sys.stderr, flush=True)

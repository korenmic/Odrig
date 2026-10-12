"""The files of a show folder, handed out and changed as the core asks."""

import collections
import os
import sys

LOG_LINES = 100

# The storage of the board, which the emulator reports in place of the Mac's disk: the
# size of the board's storage and the size of a block of its file system.
STORAGE_BYTES = 10354688
STORAGE_BLOCK = 4096
MOST_STORAGE = 4294967295

LONGEST_NAME = 32
NAME_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-_.")


class FolderHost:
    """What the core needs from its host besides memory: one open file, a place for its
    diagnostic lines, and the storage functions on the folder."""

    def __init__(self, folder, verbose=False, storage=STORAGE_BYTES):
        self.folder = os.fspath(folder)
        self.verbose = verbose
        self.storage = storage
        self.logged = collections.deque(maxlen=LOG_LINES)
        self._file = None
        self._written = None
        self._written_name = None
        self._second = None
        self._second_name = None

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

    def release(self):
        """Closes every file the host holds, for the end of the program. A file that was
        being written stays as far as it was written."""
        self.close()
        self._drop_second()
        self._give_up()

    def log(self, text):
        self.logged.append(text)
        if self.verbose:
            print(f"core: {text}", file=sys.stderr, flush=True)

    def _path(self, name):
        """The place of a file in the folder, or `None` for a name that is not one the core
        may use: 1 to 32 characters of a-z, 0-9, `-`, `_` and `.`, and not made of dots
        alone. Such a name has no path separator, so the place is in the folder."""
        if not name or len(name) > LONGEST_NAME or not NAME_CHARACTERS.issuperset(name) or not name.strip("."):
            return None
        return os.path.join(self.folder, name)

    def _give_up(self):
        """Closes the file being written, if any, without making it whole."""
        if self._written is not None:
            try:
                self._written.close()
            except OSError:
                pass
        self._written = None
        self._written_name = None

    def _drop_second(self, name=None):
        """Closes the file `read_at` holds, when it is the named one or no name is given."""
        if self._second is not None and name in (None, self._second_name):
            try:
                self._second.close()
            except OSError:
                pass
            self._second = None
            self._second_name = None

    def write_open(self, name):
        """Begins a new, empty file of this name. 1, or -1 on a failure."""
        if self._written is not None:
            given_up = self._written_name
            self._give_up()
            self.remove(given_up)
        path = self._path(name)
        if path is None:
            return -1
        self._drop_second(name)
        try:
            self._written = open(path, "wb")
        except OSError:
            return -1
        self._written_name = name
        return 1

    def write(self, data):
        """Adds bytes to the file being written. 1, or -1 on a failure."""
        if self._written is None:
            return -1
        try:
            self._written.write(data)
        except OSError:
            return -1
        return 1

    def write_close(self):
        """Ends the writing: the file is whole on the disk afterwards. 1, or -1."""
        written, self._written, self._written_name = self._written, None, None
        if written is None:
            return -1
        try:
            written.flush()
            os.fsync(written.fileno())
            written.close()
        except OSError:
            try:
                written.close()
            except OSError:
                pass
            return -1
        return 1

    def rename(self, old, new):
        """Gives a file another name, in place of a file that has it. 1, or -1."""
        source, target = self._path(old), self._path(new)
        if source is None or target is None:
            return -1
        self._drop_second(old)
        self._drop_second(new)
        try:
            os.replace(source, target)
        except OSError:
            return -1
        return 1

    def remove(self, name):
        """Removes a file: 1 when it removed one, 0 when there was none, -1 on a failure. A
        file being written under the name is given up."""
        path = self._path(name)
        if path is None:
            return -1
        if self._written_name == name:
            self._give_up()
        self._drop_second(name)
        try:
            os.remove(path)
        except FileNotFoundError:
            return 0
        except OSError:
            return -1
        return 1

    def space(self):
        """`(free, total)` in bytes, as the board would report them for the files of the
        folder: the total less the size of each file rounded up to a whole block, and not
        below 0. `None` when the folder cannot be listed."""
        used = 0
        try:
            with os.scandir(self.folder) as entries:
                for entry in entries:
                    if entry.is_file():
                        used += -(-entry.stat().st_size // STORAGE_BLOCK) * STORAGE_BLOCK
        except OSError:
            return None
        return max(0, self.storage - used), self.storage

    def read_at(self, name, offset, capacity):
        """Up to `capacity` bytes of a file from an offset, apart from the open file: none at
        or after its end, `None` on a failure and when there is no such file."""
        path = self._path(name)
        if path is None:
            return None
        try:
            if self._second_name != name:
                self._drop_second()
                self._second = open(path, "rb")
                self._second_name = name
            if self._second.tell() != offset:
                self._second.seek(offset)
            return self._second.read(capacity)
        except OSError:
            self._drop_second()
            return None

"""The files of a show folder, handed out and changed as the core asks."""

import collections
import os
import sys
import time

LOG_LINES = 100

# The storage of the board, which the emulator reports in place of the Mac's disk: the
# size of the board's storage and the size of a block of its file system.
STORAGE_BYTES = 13500416
STORAGE_BLOCK = 4096
MOST_STORAGE = 4294967295

LONGEST_NAME = 32
NAME_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-_.")

# The most files of a drive, how often the folder of a drive is looked for, and the
# beginning of the name the core gives a file of the drive.
DRIVE_MOST = 256
DRIVE_LOOK_SECONDS = 1.0
DRIVE_PREFIX = "drive/"


def drive_list(folder):
    """The names of the animation files of a drive's folder `odrig`: those that end in
    `.odrg`, in any case, and do not begin with a dot, in the order of their bytes, the
    first 256. Empty when the folder cannot be listed."""
    try:
        with os.scandir(folder) as entries:
            names = [entry.name for entry in entries if entry.is_file()]
    except OSError:
        return []
    kept = [name for name in names if name.lower().endswith(".odrg") and not name.startswith(".")]
    return sorted(kept, key=os.fsencode)[:DRIVE_MOST]


class Drive:
    """A folder of the computer that stands for the top of a USB drive. Its folder `odrig`
    appearing is a drive plugged in, with a number one higher than the last, and its going
    is the drive pulled out. The folder is looked for at most once in DRIVE_LOOK_SECONDS
    of the clock. Its list is made when it appears, and not again while it stays, as the
    files of a drive do not change while it is plugged in."""

    def __init__(self, top, clock=time.monotonic):
        self.top = os.fspath(top)
        self.folder = os.path.join(self.top, "odrig")
        self.clock = clock
        self.number = 0
        self.names = []
        self._plugged = 0
        self._looked = None

    def look(self):
        """The number of the drive that is plugged in now, 0 for none."""
        now = self.clock()
        if self._looked is not None and now - self._looked < DRIVE_LOOK_SECONDS:
            return self.number
        self._looked = now
        there = os.path.isdir(self.folder)
        if there and self.number == 0:
            self.names = drive_list(self.folder)
            self._plugged += 1
            self.number = self._plugged
        elif not there and self.number != 0:
            self.number = 0
            self.names = []
        return self.number

    def name(self, drive, place):
        """The name of the file at a place of that drive's list, or `None`."""
        if drive == 0 or drive != self.number or place >= len(self.names):
            return None
        return self.names[place]

    def path(self, name):
        """The file a name `drive/<place>` stands for, or `None` when the drive that is
        plugged in has none at that place."""
        place = name[len(DRIVE_PREFIX):]
        if not place.isascii() or not place.isdigit() or self.number == 0 or int(place) >= len(self.names):
            return None
        return os.path.join(self.folder, self.names[int(place)])


class FolderHost:
    """What the core needs from its host besides memory: one open file, a place for its
    diagnostic lines, the storage functions on the folder, and a `Drive` or `None`."""

    def __init__(self, folder, verbose=False, storage=STORAGE_BYTES, drive=None):
        self.folder = os.fspath(folder)
        self.verbose = verbose
        self.storage = storage
        self.drive = drive
        self._drive_number = 0
        self.logged = collections.deque(maxlen=LOG_LINES)
        self._file = None
        self._written = None
        self._written_name = None
        self._second = None
        self._second_name = None

    def open(self, name):
        """1 when the file is open, 0 when the folder has no file of that name, -1 otherwise."""
        self.close()
        if self._of_the_drive(name):
            path = self.drive.path(name)
            if path is None:
                return 0
            try:
                self._file = open(path, "rb")
            except FileNotFoundError:
                return 0
            except OSError:
                return -1
            return 1
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

    def _of_the_drive(self, name):
        return self.drive is not None and name.startswith(DRIVE_PREFIX)

    def drive_number(self):
        """The number of the drive that is plugged in now, 0 for none. A file of the drive
        before it that `read_at` holds is closed: its name may stand for another file now."""
        number = self.drive.look()
        if number != self._drive_number:
            self._drive_number = number
            if self._second_name is not None and self._second_name.startswith(DRIVE_PREFIX):
                self._drop_second()
        return number

    def drive_name(self, drive, place):
        """The name of the file at a place of that drive's list, or `None`."""
        return self.drive.name(drive, place)

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
            # Without a buffer of its own: every piece is in the folder when it was taken,
            # so the space the folder takes is the bytes written so far.
            self._written = open(path, "wb", buffering=0)
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
        path = self.drive.path(name) if self._of_the_drive(name) else self._path(name)
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

"""The files of a show folder, handed out and changed as the core asks."""

import collections
import os
import platform
import shutil
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
# What a part of a name of a file of a drive may not hold, the longest length of a whole
# name, how many sub-folders of the drive's folder are taken, how deep below it a folder
# may lie, and the folder of the file system that is never one of them.
DRIVE_FORBIDDEN = frozenset('/\\:*?"<>|')
DRIVE_LONGEST_NAME = 100
DRIVE_MOST_FOLDERS = 32
DRIVE_DEEPEST = 3
DRIVE_SYSTEM_FOLDER = "System Volume Information"


def drive_part_sound(part):
    """Whether one part of a drive file's name, a folder's name or the file's, is sound:
    printable ASCII other than / \\ : * ? " < > |, not empty, not beginning with a dot."""
    return (part != "" and part.isascii() and not part.startswith(".")
            and all(" " <= character <= "~" and character not in DRIVE_FORBIDDEN for character in part))


def drive_name_sound(name):
    """Whether a name is one a file of a drive's folder may have: a path from the folder
    `odrig`, the names of at most three folders and the file's name joined by `/`, 1 to 100
    bytes in all, each part sound."""
    parts = name.split("/")
    return 0 < len(name) <= DRIVE_LONGEST_NAME and len(parts) <= DRIVE_DEEPEST + 1 and all(drive_part_sound(part) for part in parts)


def drive_listed(path):
    """Whether a listing takes a file of this path: its name ends in `.odrg` or `.odrgx` in any
    case and does not begin with a dot, and every folder of the path is sound, does not end
    with a space or a dot, and is not the file system's own folder."""
    *folders, file = path.split("/")
    if not file.lower().endswith((".odrg", ".odrgx")) or file.startswith("."):
        return False
    return all(drive_part_sound(folder) and folder[-1] not in ". " and folder != DRIVE_SYSTEM_FOLDER for folder in folders)


def drive_listing_key(path):
    """The place of a path in the depth-first order: a folder's files by the bytes of their
    names, then its sub-folders by the bytes of their names, each the same way."""
    *folders, file = path.split("/")
    return tuple(os.fsencode(folder) for folder in folders), os.fsencode(file)


def drive_cut(paths):
    """The paths of a sorted listing within the limits: at most 256 files and at most 32
    sub-folders, a folder counted with its uncounted ancestors when the first file at or
    below it is kept; from the file whose folder would be counted past the 32nd, and from
    the 257th, the rest is passed over."""
    kept, counted = [], set()
    for path in paths:
        folders = path.split("/")[:-1]
        new = {"/".join(folders[:depth]) for depth in range(1, len(folders) + 1)} - counted
        if len(kept) >= DRIVE_MOST or len(counted) + len(new) > DRIVE_MOST_FOLDERS:
            break
        counted |= new
        kept.append(path)
    return kept

# Windows refuses to remove a file that a program holds open, and its folder, unless the
# program let others do so when it opened the file. The host lets them, as macOS does: a
# drive is pulled out by moving its folder away while one of its files plays.
WINDOWS = sys.platform == "win32"
SHARE_EVERYTHING = 0x1 | 0x2 | 0x4  # FILE_SHARE_READ, FILE_SHARE_WRITE and FILE_SHARE_DELETE


def reading(path):
    """A file opened to be read, which may be moved or removed while it is open. A file that
    is not there raises `FileNotFoundError` and any other failure an `OSError`, as `open`."""
    if not WINDOWS:
        return open(path, "rb")
    import _winapi
    import msvcrt

    handle = _winapi.CreateFile(os.fspath(path), _winapi.GENERIC_READ, SHARE_EVERYTHING, 0, _winapi.OPEN_EXISTING, 0, 0)
    try:
        return os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY), "rb")
    except OSError:
        _winapi.CloseHandle(handle)
        raise


def drive_list(folder):
    """The paths of the animation files of a drive's folder `odrig` and of its sub-folders
    to three levels, depth first: a folder's files by the bytes of their names, then its
    sub-folders by the bytes of their names, each listed the same way, at most 256 files
    and 32 sub-folders. Empty when the folder cannot be listed."""
    found = []
    pending = [("", 0)]
    while pending:
        prefix, depth = pending.pop()
        try:
            with os.scandir(os.path.join(folder, *prefix.split("/")) if prefix else folder) as entries:
                for entry in entries:
                    path = f"{prefix}/{entry.name}" if prefix else entry.name
                    if entry.is_dir():
                        if depth < DRIVE_DEEPEST and drive_part_sound(entry.name) and entry.name[-1] not in ". " and entry.name != DRIVE_SYSTEM_FOLDER:
                            pending.append((path, depth + 1))
                    elif entry.is_file() and drive_listed(path):
                        found.append(path)
        except OSError:
            if not prefix:
                return []
    return drive_cut(sorted(found, key=drive_listing_key))


class Drive:
    """A folder of the computer that stands for the top of a drive, a card or a USB stick.
    Its folder `odrig` appearing is a drive plugged in, with a number one higher than the
    last, and its going is the drive pulled out. The folder is looked for at most once in
    DRIVE_LOOK_SECONDS of the clock. It is listed when the core asks, and not otherwise; the
    core may give the names of places instead. The core may change its files unless it is
    read only."""

    def __init__(self, top, clock=time.monotonic, writable=True):
        self.top = os.fspath(top)
        self.folder = os.path.join(self.top, "odrig")
        self.clock = clock
        self.writable = writable
        self.number = 0
        self.names = []
        self.listings = 0
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
            self.names = []
            self._plugged += 1
            self.number = self._plugged
        elif not there and self.number != 0:
            self.number = 0
            self.names = []
        return self.number

    def list(self, drive):
        """Lists the folder of that drive now. The number of files, or `None` when it is not
        plugged in any more."""
        if drive == 0 or drive != self.number:
            return None
        self.names = drive_list(self.folder)
        self.listings += 1
        return len(self.names)

    def bind(self, drive, place, name):
        """Gives the place to the file of this name. False when that drive is not plugged in
        any more or the name is not one of a drive's file."""
        if drive == 0 or drive != self.number or not drive_name_sound(name) or place >= DRIVE_MOST:
            return False
        self.names += [None] * (place + 1 - len(self.names))
        self.names[place] = name
        return True

    def can_write(self, drive):
        return self.writable and drive != 0 and drive == self.number

    def name(self, drive, place):
        """The name of the file at a place of that drive's list, or `None`."""
        if drive == 0 or drive != self.number or place >= len(self.names):
            return None
        return self.names[place]

    def path(self, name, changing=False):
        """The file a name `drive/<place>` or `drive/<name>` stands for, or `None` when the
        drive that is plugged in has none at that place, the name is not one of a drive's
        file, or a change is asked of a drive that cannot be written. A place is never
        changed."""
        rest = name[len(DRIVE_PREFIX):]
        if self.number == 0:
            return None
        if rest.isascii() and rest.isdigit():
            if changing or int(rest) >= len(self.names) or self.names[int(rest)] is None:
                return None
            return os.path.join(self.folder, self.names[int(rest)])
        if not drive_name_sound(rest) or (changing and not self.writable):
            return None
        return os.path.join(self.folder, rest)


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
                self._file = reading(path)
            except FileNotFoundError:
                return 0
            except OSError:
                return -1
            return 1
        if not name or "/" in name or "\\" in name or os.sep in name or (os.altsep and os.altsep in name):
            return -1
        try:
            self._file = reading(os.path.join(self.folder, name))
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

    def drive_space(self, generation):
        """Filesystem free and total bytes of the mounted external folder, or unknown."""
        if self.drive is None or generation == 0 or generation != self.drive.look():
            return None
        try:
            usage = shutil.disk_usage(self.drive.top)
            return usage.free, usage.total
        except OSError:
            return None

    def drive_name(self, drive, place):
        """The name of the file at a place of that drive's list, or `None`."""
        return self.drive.name(drive, place)

    def about(self):
        """The name the emulator gives itself in `status`."""
        return f"odrig emulator on {platform.system()} {platform.machine()}"

    def drive_list(self, drive):
        """Lists the drive's folder now: the number of its files, or `None`."""
        return self.drive.list(drive)

    def drive_bind(self, drive, place, name):
        return self.drive.bind(drive, place, name)

    def drive_writable(self, drive):
        return self.drive.can_write(drive)

    def log(self, text):
        self.logged.append(text)
        if self.verbose:
            print(f"core: {text}", file=sys.stderr, flush=True)

    def _path(self, name):
        """The place of a file in the folder, or `None` for a name that is not one the core
        may use: 1 to 32 characters of a-z, 0-9, `-`, `_` and `.`, and not made of dots
        alone. Such a name has no path separator, so the place is in the folder. A name
        `drive/<name>` is the file of that name of the drive, when it can be written."""
        if self._of_the_drive(name):
            return self.drive.path(name, changing=True)
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
                self._second = reading(path)
                self._second_name = name
            if self._second.tell() != offset:
                self._second.seek(offset)
            return self._second.read(capacity)
        except OSError:
            self._drop_second()
            return None

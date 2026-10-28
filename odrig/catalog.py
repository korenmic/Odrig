"""The catalog of a storage of animations, as docs/catalog.md states it, and the changes a
computer makes to it.

The core keeps the same catalogs on the board, in C++. This module does what the core does,
so that the same changes leave the same files. A drive's catalog, of version 2, has an index
beside its pages: a file of rows for each folder, a table of the folders and a map of the
ids. `python3 -m odrig.catalog` manages the folder `odrig` of a card mounted on a computer.
"""

import binascii
import dataclasses
import os
import re
import sys

from . import errors, odrg, odrgx

# The format of the board's own catalog, and of a drive's, which has an index.
FORMAT = 1
DRIVE_FORMAT = 2
CHECK = 1
PAGES = 16
MARKER = "catalog.txt"
NEW_MARKER = "catalog.new"
DO = "catalog.do"
PART = "upload.part"
MARKER_SIZE = 409
DRIVE_MARKER_SIZE = 461
LONGEST_NAME = 100
LONGEST_LIST = 256
# The most sub-folders of a card's folder `odrig` that are taken, how deep below it a
# folder may lie, and the folder of the file system that is never one of them.
MOST_FOLDERS = 32
DEEPEST = 3
SYSTEM_FOLDER = "System Volume Information"
# The canvas of the installation, which a card's animations are for.
CANVAS = (60, 60)
TYPES = ("frames", "text", "widget")
# The endings of the names of animation files: an ODRG file, an ODRGX container.
ENDINGS = (".odrg", odrgx.ENDING)
FORBIDDEN = set('/\\:*?"<>|')

# The index of a drive: the table of the folders, the map of the ids, and a file of rows
# for each folder, named by its id, the root's 0. A line of a folder's file and of the table
# is ROW bytes, one of the map ID_ROW, each padded with spaces before its line feed.
FOLDERS = "index-folders.txt"
IDS = "index-ids.txt"
ROW = 180
ID_ROW = 36
FIRST_ID = 60001
LAST_ID = 4294967295
# What a rebuild of the board writes for itself while it runs, and removes.
SCAN = "rebuild.tmp"
DRAFT = "rebuild-folders.tmp"

# What a catalog is: none (the storage has no catalog), ok, damaged, incompatible.
NONE = "none"
OK = "ok"
DAMAGED = "damaged"
INCOMPATIBLE = "incompatible"

_FIRST_LINE = re.compile(r"odrig-catalog (0|[1-9][0-9]{0,8}) check (0|[1-9][0-9]{0,8}) generation ([0-9a-f]{8})")
_PAGE_LINE = re.compile(r"page ([0-9]{2}) ([0-9]{4}) ([0-9a-f]{8})")
_INDEX_LINE = re.compile(r"(folders|ids) ([0-9]{10}) ([0-9a-f]{8})")
_CRC_LINE = re.compile(r"crc ([0-9a-f]{8})")
_ENTRY = re.compile(r"([0-9a-f]{8}) (0|[1-9][0-9]{0,9}) ([1-9][0-9]{0,4}) ([1-9][0-9]{0,4}) (0|[1-9][0-9]{0,19}) (frames|text|widget) (.+)")
_NUMBER = r"(0|[1-9][0-9]{0,9})"
_TABLE_ROW = re.compile(" ".join([_NUMBER] * 7) + r" ([0-9a-f]{8})(?: (.+))?")
_FILE_ROW = re.compile(_NUMBER + r" f ([0-9a-f]{8}) " + _NUMBER + r" ([1-9][0-9]{0,4}) ([1-9][0-9]{0,4}) (0|[1-9][0-9]{0,19}) (frames|text|widget) (.+)")
_FOLDER_ROW = re.compile(_NUMBER + r" d " + _NUMBER + r" (.+)")
_MAP_ROW = re.compile(_NUMBER + r" ([fd]) " + _NUMBER + " " + _NUMBER)
_DO_FIRST = re.compile(r"odrig-catalog-do 1 generation ([0-9a-f]{8})")
_DO_PAGES = re.compile(r"pages ([0-9a-f]{4})")
_DO_MOVE = re.compile(r"move ([^ ]+) (.+)")
_DO_REMOVE = re.compile(r"remove (.+)")


def page_name(number):
    return f"catalog-{number:02d}.txt"


def new_page_name(number):
    return f"catalog-{number:02d}.new"


def folder_file(folder_id):
    """The name of the file of a folder's rows, by the folder's id: the root's is 0."""
    return f"index-{folder_id}.txt"


def new_name(name):
    """The name a new version of an index file is written under before it is put in place."""
    return name[: -len(".txt")] + ".new"


def crc(data):
    """The CRC-32 of zlib."""
    return binascii.crc32(data) & 0xFFFFFFFF


def page_of(name):
    """The page of a name: the low four bits of the FNV-1a hash of its bytes."""
    value = 2166136261
    for byte in name.encode("ascii"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value & 15


def part_sound(part):
    """Whether one part of a path, a folder's name or a file's, keeps the rule of its
    characters: printable ASCII other than / \\ : * ? " < > |, neither beginning nor ending
    with a space or a dot, and not empty."""
    if not part or not part.isascii():
        return False
    if any(not 0x20 <= ord(character) <= 0x7E or character in FORBIDDEN for character in part):
        return False
    return part[0] not in ". " and part[-1] not in ". "


def name_allowed(name):
    """Whether a catalog may hold a file of this name: a path from the card's folder `odrig`,
    the names of at most three folders and the file's name joined by `/`, 1 to 100 bytes in
    all. A folder's name keeps the rule of its characters and may be digits alone; the
    file's name keeps it, is not digits alone, and ends in `.odrg` or `.odrgx`."""
    if not 1 <= len(name) <= LONGEST_NAME or not name.isascii():
        return False
    parts = name.split("/")
    if len(parts) > DEEPEST + 1 or not all(part_sound(part) for part in parts):
        return False
    return not parts[-1].isdigit() and parts[-1].lower().endswith(ENDINGS)


def listed(path):
    """Whether a lister takes a file of this path from the card: its name ends in `.odrg` or
    `.odrgx` in any case and does not begin with a dot, and every folder of the path, at
    most three, keeps the rule of a folder's name, does not begin with a dot and is not
    `System Volume Information`."""
    *folders, file = path.split("/")
    if len(folders) > DEEPEST or not file.lower().endswith(ENDINGS) or file.startswith("."):
        return False
    return all(part_sound(folder) and folder != SYSTEM_FOLDER for folder in folders)


def listing_key(path):
    """The place of a path in the depth-first order of a listing: a folder's files by the
    bytes of their names, then its sub-folders by the bytes of their names, each listed the
    same way. A tuple that is a prefix of another sorts first, so a folder's files come
    before its sub-folders' and siblings sort by their bytes."""
    *folders, file = path.split("/")
    return tuple(folder.encode("utf-8", "surrogateescape") for folder in folders), file.encode("utf-8", "surrogateescape")


def folder_key(path):
    """The place of a folder's path in the listing's order, the root's "" first: a folder
    before the folders below it, siblings by the bytes of their names, one part at a time."""
    return tuple(part.encode("utf-8", "surrogateescape") for part in path.split("/")) if path else ()


def folder_of(path):
    """The folder of a file's path: the part before its last `/`, "" for the root's."""
    return path.rsplit("/", 1)[0] if "/" in path else ""


def cut_listing(paths):
    """The paths of a sorted listing that the limits of a drive without a catalog take: at
    most 256 files and at most 32 sub-folders, a folder counted with each of its ancestors
    not yet counted when the first file at or below it is kept. The files after the 256th,
    and every file from the one whose folder would be counted past the 32nd on, are passed
    over."""
    kept, counted = [], set()
    for path in paths:
        folders = path.split("/")[:-1]
        new = {"/".join(folders[:depth]) for depth in range(1, len(folders) + 1)} - counted
        if len(kept) >= LONGEST_LIST or len(counted) + len(new) > MOST_FOLDERS:
            break
        counted |= new
        kept.append(path)
    return kept


def walk(folder):
    """The paths of the animation files of a folder and of its sub-folders to three levels,
    as `listed` takes them, in no order; empty when the folder cannot be listed."""
    found = []
    pending = [("", 0)]
    while pending:
        prefix, depth = pending.pop()
        try:
            with os.scandir(os.path.join(folder, *prefix.split("/")) if prefix else folder) as entries:
                for entry in entries:
                    path = f"{prefix}/{entry.name}" if prefix else entry.name
                    if entry.is_dir():
                        if depth < DEEPEST and part_sound(entry.name) and entry.name != SYSTEM_FOLDER:
                            pending.append((path, depth + 1))
                    elif entry.is_file() and listed(path):
                        found.append(path)
        except OSError:
            if not prefix:
                return []
    return found


class Unusable(Exception):
    """A catalog that cannot be read: `state` is DAMAGED or INCOMPATIBLE, and `detail` says
    what: `marker`, `page`, `line` or `interrupted`, or the version for an incompatible one."""

    def __init__(self, state, detail):
        super().__init__(f"{state}: {detail}")
        self.state = state
        self.detail = detail


@dataclasses.dataclass(frozen=True)
class Entry:
    """One animation of a catalog."""

    name: str
    bytes: int
    crc: int
    width: int
    height: int
    total_ms: int
    type: str = "frames"

    def line(self):
        return f"{self.crc:08x} {self.bytes} {self.width} {self.height} {self.total_ms} {self.type} {self.name}\n".encode("ascii")


@dataclasses.dataclass(frozen=True)
class Marker:
    """The marker: the generation, and each page's count of entries and CRC-32; of a drive's
    catalog also the lines and the CRC-32 of the table of the folders and of the map of the
    ids, each `(lines, crc)`, which make it of version 2."""

    generation: int
    counts: tuple
    crcs: tuple
    folders: tuple = None
    ids: tuple = None

    def text(self):
        version = FORMAT if self.folders is None else DRIVE_FORMAT
        made = f"odrig-catalog {version} check {CHECK} generation {self.generation:08x}\n"
        for number in range(PAGES):
            made += f"page {number:02d} {self.counts[number]:04d} {self.crcs[number]:08x}\n"
        if self.folders is not None:
            made += f"folders {self.folders[0]:010d} {self.folders[1]:08x}\n"
            made += f"ids {self.ids[0]:010d} {self.ids[1]:08x}\n"
        made = made.encode("ascii")
        return made + f"crc {crc(made):08x}\n".encode("ascii")


EMPTY = Marker(0, (0,) * PAGES, (0,) * PAGES)


def next_generation(generation):
    return 1 if generation >= 0xFFFFFFFF else generation + 1


def parse_marker(data, drive=False):
    """The marker these bytes hold: of version 1 for the board's own storage, of version 2
    with its index's lines for a drive. Raises `Unusable`."""
    version, size = (DRIVE_FORMAT, DRIVE_MARKER_SIZE) if drive else (FORMAT, MARKER_SIZE)
    first = data.split(b"\n", 1)[0]
    found = _FIRST_LINE.fullmatch(first.decode("ascii", "replace"))
    if found is not None and (int(found.group(1)) != version or int(found.group(2)) != CHECK):
        raise Unusable(INCOMPATIBLE, f"format {found.group(1)}, check {found.group(2)}")
    if found is None or len(data) != size or not data.endswith(b"\n"):
        raise Unusable(DAMAGED, "marker")
    lines = data.decode("ascii", "replace").split("\n")[:-1]
    if len(lines) != (4 if drive else 2) + PAGES:
        raise Unusable(DAMAGED, "marker")
    closing = _CRC_LINE.fullmatch(lines[-1])
    if closing is None or int(closing.group(1), 16) != crc(data[: size - 13]):
        raise Unusable(DAMAGED, "marker")
    generation = int(found.group(3), 16)
    counts = []
    crcs = []
    for number, line in enumerate(lines[1 : 1 + PAGES]):
        page = _PAGE_LINE.fullmatch(line)
        if page is None or int(page.group(1)) != number:
            raise Unusable(DAMAGED, "marker")
        count, value = int(page.group(2)), int(page.group(3), 16)
        if count == 0 and value != 0:
            raise Unusable(DAMAGED, "marker")
        counts.append(count)
        crcs.append(value)
    if generation == 0:
        raise Unusable(DAMAGED, "marker")
    if not drive:
        return Marker(generation, tuple(counts), tuple(crcs))
    index = []
    for word, line in zip(("folders", "ids"), lines[1 + PAGES : -1]):
        found_line = _INDEX_LINE.fullmatch(line)
        if found_line is None or found_line.group(1) != word:
            raise Unusable(DAMAGED, "marker")
        lines_of, value = int(found_line.group(2)), int(found_line.group(3), 16)
        if lines_of == 0 and value != 0:
            raise Unusable(DAMAGED, "marker")
        index.append((lines_of, value))
    if index[0][0] == 0:
        raise Unusable(DAMAGED, "marker")
    return Marker(generation, tuple(counts), tuple(crcs), index[0], index[1])


def parse_page(data, number, marker):
    """The entries of page `number`, whose file holds these bytes, as the marker has it.
    Raises `Unusable`."""
    if crc(data) != marker.crcs[number] or data.count(b"\n") != marker.counts[number] or (data and not data.endswith(b"\n")):
        raise Unusable(DAMAGED, "page")
    entries = []
    for line in data.decode("ascii", "replace").split("\n")[:-1]:
        found = _ENTRY.fullmatch(line)
        if found is None:
            raise Unusable(DAMAGED, "line")
        value, size, width, height, total, kind, name = found.groups()
        if int(size) > 0xFFFFFFFF or int(width) > 65535 or int(height) > 65535 or int(total) > 0xFFFFFFFFFFFFFFFF:
            raise Unusable(DAMAGED, "line")
        if not name_allowed(name) or page_of(name) != number:
            raise Unusable(DAMAGED, "line")
        entries.append(Entry(name, int(size), int(value, 16), int(width), int(height), int(total), kind))
    return entries


def padded(text, width):
    """A line of an index file: the text, spaces up to `width` - 1 bytes and a line feed."""
    if len(text) >= width:
        raise ValueError(f"a line of {len(text)} bytes is longer than {width - 1}")
    return (text + " " * (width - 1 - len(text)) + "\n").encode("ascii")


def unpadded(data, width):
    """The lines of an index file of this line length, without their padding; None when the
    bytes are not whole lines of that length or a line holds no text."""
    if len(data) % width:
        return None
    lines = []
    for at in range(0, len(data), width):
        line = data[at : at + width]
        if line[-1:] != b"\n" or b"\n" in line[:-1]:
            return None
        text = line[:-1].decode("ascii", "replace").rstrip(" ")
        if not text:
            return None
        lines.append(text)
    return lines


@dataclasses.dataclass
class Folder:
    """A folder of a drive's index: its path from the folder `odrig`, "" for the root, its
    id, 0 for the root, and its own files in the saved order, each `(id, Entry)`."""

    path: str
    id: int
    rows: list = dataclasses.field(default_factory=list)

    @property
    def depth(self):
        return self.path.count("/") + 1 if self.path else 0


class Index:
    """The index of a drive: its folders in the table's order, the root first, depth first.
    Every derived line and file is made from them."""

    def __init__(self, folders):
        self.folders = folders

    def ends(self):
        """For each folder, the ordinal after its last descendant."""
        made = []
        for ordinal, folder in enumerate(self.folders):
            end = ordinal + 1
            while end < len(self.folders) and self.folders[end].depth > folder.depth:
                end += 1
            made.append(end)
        return made

    def firsts(self):
        """For each folder, the number of files of the folders before it."""
        made, before = [], 0
        for folder in self.folders:
            made.append(before)
            before += len(folder.rows)
        return made

    def children(self, ordinal):
        """The ordinals of a folder's sub-folders, in the table's order."""
        ends = self.ends()
        made, at = [], ordinal + 1
        while at < ends[ordinal]:
            made.append(at)
            at = ends[at]
        return made

    def files(self):
        return sum(len(folder.rows) for folder in self.folders)

    def folder_text(self, ordinal):
        """The bytes of a folder's file: its file rows, then its folder rows."""
        made = b""
        for file_id, entry in self.folders[ordinal].rows:
            made += padded(f"{file_id} f {entry.crc:08x} {entry.bytes} {entry.width} {entry.height} {entry.total_ms} {entry.type} {entry.name}", ROW)
        for child in self.children(ordinal):
            sub = self.folders[child]
            made += padded(f"{sub.id} d {len(sub.rows)} {sub.path}", ROW)
        return made

    def table_text(self):
        ends, firsts = self.ends(), self.firsts()
        made = b""
        for ordinal, folder in enumerate(self.folders):
            text = self.folder_text(ordinal)
            made += padded(
                f"{ordinal} {folder.id} {folder.depth} {ends[ordinal]} {firsts[ordinal]} {len(folder.rows)} {len(self.children(ordinal))} "
                f"{crc(text) if text else 0:08x} {folder.path}".rstrip(" "),
                ROW,
            )
        return made

    def map_lines(self):
        """`(id, kind, ordinal, row)` of every id, sorted by id."""
        made = []
        for ordinal, folder in enumerate(self.folders):
            made += [(file_id, "f", ordinal, row) for row, (file_id, _) in enumerate(folder.rows)]
            if ordinal:
                made.append((folder.id, "d", ordinal, 0))
        return sorted(made)

    def map_text(self):
        return b"".join(padded(f"{line[0]} {line[1]} {line[2]} {line[3]}", ID_ROW) for line in self.map_lines())

    def ids(self):
        return {line[0] for line in self.map_lines()}

    def entries(self):
        return [entry for folder in self.folders for _, entry in folder.rows]

    def find(self, name):
        """`(ordinal, row)` of the file of this name, or None."""
        for ordinal, folder in enumerate(self.folders):
            for row, (_, entry) in enumerate(folder.rows):
                if entry.name == name:
                    return ordinal, row
        return None

    def ordinal_of(self, path):
        for ordinal, folder in enumerate(self.folders):
            if folder.path == path:
                return ordinal
        return None

    def counts(self):
        """`(folders, ids)` as the marker gives them: the lines and the CRC-32 of the table and
        of the map, 0 for one without a line."""
        table, ids = self.table_text(), self.map_text()
        return (len(self.folders), crc(table)), (len(ids) // ID_ROW, crc(ids) if ids else 0)


EMPTY_INDEX = Index([Folder("", 0)])


def parse_index(storage, marker):
    """The index of a drive whose marker is this one, read and checked: each file agrees with
    the CRC-32 the marker or the table gives it, and the files are those its folders make
    again, byte for byte. Raises `Unusable`."""
    table = storage.read(FOLDERS) or b""
    ids = storage.read(IDS) or b""
    if len(table) // ROW != marker.folders[0] or crc(table) != marker.folders[1] or len(ids) // ID_ROW != marker.ids[0] or (crc(ids) if ids else 0) != marker.ids[1]:
        raise Unusable(DAMAGED, "page")
    lines = unpadded(table, ROW)
    if lines is None:
        raise Unusable(DAMAGED, "line")
    folders, crcs = [], []
    for ordinal, line in enumerate(lines):
        found = _TABLE_ROW.fullmatch(line)
        if found is None or int(found.group(1)) != ordinal:
            raise Unusable(DAMAGED, "line")
        folders.append(Folder(found.group(9) or "", int(found.group(2))))
        crcs.append(int(found.group(8), 16))
    for folder, expected in zip(folders, crcs):
        text = storage.read(folder_file(folder.id)) if expected else b""
        if text is None or (crc(text) if text else 0) != expected:
            raise Unusable(DAMAGED, "page")
        rows = unpadded(text, ROW) if text else []
        if rows is None:
            raise Unusable(DAMAGED, "line")
        for row in rows:
            found = _FILE_ROW.fullmatch(row)
            if found is None:
                if _FOLDER_ROW.fullmatch(row) is None:
                    raise Unusable(DAMAGED, "line")
                continue
            file_id, value, size, width, height, total, kind, name = found.groups()
            if int(size) > 0xFFFFFFFF or int(width) > 65535 or int(height) > 65535 or int(total) > 0xFFFFFFFFFFFFFFFF or not name_allowed(name):
                raise Unusable(DAMAGED, "line")
            folder.rows.append((int(file_id), Entry(name, int(size), int(value, 16), int(width), int(height), int(total), kind)))
    index = Index(folders)
    try:
        again = index.table_text() == table and index.map_text() == ids and all(
            (storage.read(folder_file(folder.id)) or b"") == index.folder_text(ordinal) for ordinal, folder in enumerate(folders))
    except ValueError:
        again = False
    paths_sound = folders and folders[0].path == "" and folders[0].id == 0 and all(
        folder_of(entry.name) == folder.path for folder in folders for _, entry in folder.rows)
    if not again or not paths_sound or len(index.ids()) != len(index.map_lines()) or any(not FIRST_ID <= value <= LAST_ID for value in index.ids()):
        raise Unusable(DAMAGED, "line")
    return index


def do_text(generation, mask, actions):
    """The commit record of a change: its generation, the mask of its pages and its actions,
    each `("move", from, to)` or `("remove", name)`."""
    made = f"odrig-catalog-do 1 generation {generation:08x}\npages {mask:04x}\n"
    for action in actions:
        made += " ".join(action) + "\n"
    made = made.encode("ascii")
    return made + f"crc {crc(made):08x}\n".encode("ascii")


def parse_do(data):
    """`(generation, mask, actions)` of a whole commit record, or `None` for one that is not."""
    if not data.endswith(b"\n"):
        return None
    lines = data.decode("ascii", "replace").split("\n")[:-1]
    if len(lines) < 3:
        return None
    closing = _CRC_LINE.fullmatch(lines[-1])
    if closing is None or int(closing.group(1), 16) != crc(data[: len(data) - len(lines[-1]) - 1]):
        return None
    first = _DO_FIRST.fullmatch(lines[0])
    pages = _DO_PAGES.fullmatch(lines[1])
    if first is None or pages is None:
        return None
    actions = []
    for line in lines[2:-1]:
        move = _DO_MOVE.fullmatch(line)
        removal = _DO_REMOVE.fullmatch(line)
        if move is not None:
            actions.append(("move", move.group(1), move.group(2)))
        elif removal is not None:
            actions.append(("remove", removal.group(1)))
        else:
            return None
    return int(first.group(1), 16), int(pages.group(1), 16), actions


def entry_of(name, data, canvas=CANVAS):
    """The entry of an animation file of this name and these bytes, as the core's check
    admits it: an ODRG file, of frames, its length the sum of their durations; or an ODRGX
    container, told apart by its first four bytes, of its type and with the loop its header
    gives, a container of frames read through its frames, one of text or a widget by its
    header and the length its header gives the payload. With `canvas` None the canvas is not
    compared. Raises `errors.Rejection` with the check's reason."""
    if odrgx.is_container(data):
        header = odrgx.read_header(data)
        if odrgx.TYPE_NAMES[header.type] == "frames":
            header, _ = odrgx.decode_frames(data)
        elif len(data) - odrgx.HEADER.size != header.payload_size:
            raise errors.Rejection(errors.PAYLOAD_SIZE, f"the header gives the payload {header.payload_size} bytes and it has {len(data) - odrgx.HEADER.size}")
        width, height, total_ms, kind = header.width, header.height, header.loop_ms, odrgx.TYPE_NAMES[header.type]
    else:
        decoded = odrg.decode(data)
        width, height, total_ms, kind = decoded.width, decoded.height, sum(duration for duration, _ in decoded.records), "frames"
    if canvas is not None and (width, height) != tuple(canvas):
        raise errors.Rejection(errors.SIZE_MISMATCH, f"the file is {width} x {height}, the canvas {canvas[0]} x {canvas[1]}")
    return Entry(name, len(data), crc(data), width, height, total_ms, kind)


class Storage:
    """The files of one folder, by name, with the calls the core makes of its host. A drive's
    folder, `drive=True`, has a catalog of version 2 with its index."""

    def __init__(self, folder, drive=False):
        self.folder = os.fspath(folder)
        self.drive = drive

    def _path(self, name):
        return os.path.join(self.folder, name)

    def read(self, name):
        """The bytes of a file, or `None` when there is none."""
        try:
            with open(self._path(name), "rb") as file:
                return file.read()
        except FileNotFoundError:
            return None

    def exists(self, name):
        return os.path.isfile(self._path(name))

    def write(self, name, data):
        """A new file of this name, whole and on the disk when this returns."""
        with open(self._path(name), "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())

    def rename(self, old, new):
        os.replace(self._path(old), self._path(new))

    def remove(self, name):
        """True when a file was removed, false when there was none."""
        try:
            os.remove(self._path(name))
        except FileNotFoundError:
            return False
        return True

    def names(self):
        """Every animation file of the folder and of its sub-folders as a drive lists them, by
        their paths from the folder: a folder's files by the bytes of their names, then its
        sub-folders by the bytes of their names, each the same way."""
        return sorted(walk(self.folder), key=listing_key)

    def leftovers(self):
        """The names of the folder's own files that a change of the index writes before it
        is committed: `index-*.new`."""
        try:
            return sorted(name for name in os.listdir(self.folder) if name.startswith("index-") and name.endswith(".new"))
        except OSError:
            return []


class MemoryStorage(Storage):
    """Files held in a dict, for a folder that is made before it is written anywhere."""

    def __init__(self, files=None, drive=False):
        self.files = dict(files or {})
        self.drive = drive

    def read(self, name):
        return self.files.get(name)

    def exists(self, name):
        return name in self.files

    def write(self, name, data):
        self.files[name] = bytes(data)

    def rename(self, old, new):
        self.files[new] = self.files.pop(old)

    def remove(self, name):
        return self.files.pop(name, None) is not None

    def names(self):
        return sorted((name for name in self.files if listed(name)), key=listing_key)

    def leftovers(self):
        return sorted(name for name in self.files if name.startswith("index-") and name.endswith(".new"))


@dataclasses.dataclass
class Catalog:
    """What a storage's catalog is: its state, and for one that is ok its marker and its
    entries, page by page in the order of their lines, and a drive's index."""

    state: str
    detail: str = ""
    marker: Marker = EMPTY
    entries: list = dataclasses.field(default_factory=list)
    index: Index = None

    def entry(self, name):
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None


def _drive(storage):
    return getattr(storage, "drive", False)


def read(storage):
    """The catalog of a storage, without changing anything. A drive's index is read with it
    and must agree with its pages."""
    if parse_do(storage.read(DO) or b"") is not None:
        return Catalog(DAMAGED, "interrupted")
    data = storage.read(MARKER)
    if data is None:
        return Catalog(NONE)
    try:
        marker = parse_marker(data, _drive(storage))
        entries = []
        for number in range(PAGES):
            page = storage.read(page_name(number)) if marker.counts[number] else b""
            if page is None:
                raise Unusable(DAMAGED, "page")
            entries += parse_page(page, number, marker)
        if len({entry.name for entry in entries}) != len(entries):
            raise Unusable(DAMAGED, "line")
        index = None
        if _drive(storage):
            index = parse_index(storage, marker)
            if sorted(index.entries(), key=lambda entry: entry.name) != sorted(entries, key=lambda entry: entry.name):
                raise Unusable(DAMAGED, "line")
    except Unusable as unusable:
        return Catalog(unusable.state, unusable.detail)
    return Catalog(OK, "", marker, entries, index)


def finish(storage):
    """Finishes the change whose commit record is whole: its actions, its pages, its marker,
    and the record removed. True when there was one."""
    record = storage.read(DO)
    parsed = parse_do(record) if record is not None else None
    if parsed is None:
        return False
    _, mask, actions = parsed
    for action in actions:
        if action[0] == "move":
            if storage.exists(action[1]):
                storage.rename(action[1], action[2])
        else:
            storage.remove(action[1])
    new = storage.read(NEW_MARKER)
    try:
        counts = parse_marker(new if new is not None else storage.read(MARKER) or b"", _drive(storage)).counts
    except Unusable:
        counts = (1,) * PAGES
    for number in range(PAGES):
        if not mask & (1 << number):
            continue
        if storage.exists(new_page_name(number)):
            storage.rename(new_page_name(number), page_name(number))
        elif counts[number] == 0:
            storage.remove(page_name(number))
    if new is not None:
        storage.rename(NEW_MARKER, MARKER)
    storage.remove(DO)
    return True


def _usable(storage):
    """The catalog of a storage for a change: an interrupted change finished first; one that
    is not ok raises `Unusable`, and a storage without one `Unusable(NONE)`."""
    finish(storage)
    catalog = read(storage)
    if catalog.state != OK:
        raise Unusable(catalog.state, catalog.detail or "no catalog")
    return catalog


def _write_pages(storage, catalog, pages, removed, added):
    """Writes the new pages of a change and gives the counts and CRC-32s of every page."""
    counts = list(catalog.marker.counts)
    crcs = list(catalog.marker.crcs)
    for number in pages:
        old = parse_page(storage.read(page_name(number)) if counts[number] else b"", number, catalog.marker)
        kept = []
        placed = False
        for entry in old:
            if added is not None and entry.name == added.name:
                kept.append(added)
                placed = True
            elif entry.name not in removed:
                kept.append(entry)
        if added is not None and page_of(added.name) == number and not placed:
            kept.append(added)
        text = b"".join(entry.line() for entry in kept)
        counts[number] = len(kept)
        crcs[number] = crc(text) if kept else 0
        if kept:
            storage.write(new_page_name(number), text)
        else:
            # A new page left by a change that was not committed must not be finished.
            storage.remove(new_page_name(number))
    return counts, crcs


def _index_actions(storage, index, folders, table=True, ids=True, gone=()):
    """Writes the index files of a change as `.new` and gives the actions that put them in
    place, `(removals, moves)`: the removals of the files of the folders that went, `gone`
    (ids), which come first in the record; then the folders' files of `folders` (ordinals),
    in the table's order, each moved, or removed when it has no line; the table; the map,
    moved or removed. The animation's own action stands between the two."""
    removals = [("remove", folder_file(folder_id)) for folder_id in gone]
    actions = []
    for ordinal in sorted(folders):
        name = folder_file(index.folders[ordinal].id)
        text = index.folder_text(ordinal)
        if text:
            storage.write(new_name(name), text)
            actions.append(("move", new_name(name), name))
        else:
            storage.remove(new_name(name))
            actions.append(("remove", name))
    if table:
        storage.write(new_name(FOLDERS), index.table_text())
        actions.append(("move", new_name(FOLDERS), FOLDERS))
    if ids:
        text = index.map_text()
        if text:
            storage.write(new_name(IDS), text)
            actions.append(("move", new_name(IDS), IDS))
        else:
            storage.remove(new_name(IDS))
            actions.append(("remove", IDS))
    return removals, actions


def commit(storage, catalog, removed=(), added=None, actions=(), index=None, index_actions=((), ())):
    """Commits a change of the catalog `catalog` read from the storage: the entries of the
    names `removed` taken out, the entry `added` added or put in the place of the entry of
    its name, and the actions done before the pages are. A drive's change gives its new
    `index` and the actions of its index files, written already, as `_index_actions` gives
    them. Finishes it, and returns the new catalog."""
    pages = sorted({page_of(name) for name in removed} | ({page_of(added.name)} if added is not None else set()))
    counts, crcs = _write_pages(storage, catalog, pages, removed, added)
    generation = next_generation(catalog.marker.generation)
    if index is not None:
        folders, ids = index.counts()
        marker = Marker(generation, tuple(counts), tuple(crcs), folders, ids)
        actions = list(index_actions[0]) + list(actions) + list(index_actions[1])
    else:
        marker = Marker(generation, tuple(counts), tuple(crcs))
    storage.write(NEW_MARKER, marker.text())
    storage.write(DO, do_text(generation, sum(1 << number for number in pages), actions))
    finish(storage)
    return read(storage)


def add(storage, name, data, canvas=CANVAS):
    """Adds the animation `name` with these bytes, or replaces the one of that name, as an
    upload does: the bytes go to `upload.part`, are read back and checked, and the change
    moves them onto the name. A drive's file goes into its root, last of the root's files,
    with the lowest free id; a replacement keeps its place and its id. Returns the entry."""
    if not name_allowed(name):
        raise errors.Rejection(errors.FILE_MALFORMED, f"{name!r} is not a name a catalog may hold")
    if _drive(storage) and "/" in name:
        raise errors.Rejection(errors.FILE_MALFORMED, f"{name!r}: a file is added to the folder odrig itself")
    catalog = _usable(storage)
    storage.write(PART, data)
    try:
        entry = entry_of(name, storage.read(PART), canvas)
    except errors.Rejection:
        storage.remove(PART)
        raise
    if catalog.index is None:
        commit(storage, catalog, added=entry, actions=[("move", PART, name)])
        return entry
    index = Index([Folder(folder.path, folder.id, list(folder.rows)) for folder in catalog.index.folders])
    root = index.folders[0]
    at = next((row for row, (_, old) in enumerate(root.rows) if old.name == name), None)
    if at is not None:
        root.rows[at] = (root.rows[at][0], entry)
    else:
        root.rows.append((lowest_free_id(catalog.index), entry))
    index_actions = _index_actions(storage, index, [0], ids=at is None)
    commit(storage, catalog, added=entry, actions=[("move", PART, name)], index=index, index_actions=index_actions)
    return entry


def lowest_free_id(index):
    """The lowest id from 60001 up that the map of an index does not hold."""
    taken = index.ids()
    found = FIRST_ID
    while found in taken:
        found += 1
    return found


def remove(storage, name):
    """Removes the animation `name`: its file and its entry. From a drive's index its row
    goes, and so does every folder left without a file at or below it."""
    catalog = _usable(storage)
    if catalog.entry(name) is None:
        raise errors.Rejection(errors.FILE_MISSING, f"the catalog has no {name}")
    if catalog.index is None:
        commit(storage, catalog, removed=(name,), actions=[("remove", name)])
        return
    old = catalog.index
    ordinal, row = old.find(name)
    folders = [Folder(folder.path, folder.id, list(folder.rows)) for folder in old.folders]
    del folders[ordinal].rows[row]
    ends = old.ends()

    def parent_of(at):
        return max(before for before in range(at) if folders[before].depth == folders[at].depth - 1)

    # The folder and each ancestor left without a file at or below it leave the table: the
    # chain from the topmost of them down to the folder, a range of the table. The parent
    # of what leaves, or of the folder, loses or changes a folder row, and is written too.
    top = None
    at = ordinal
    while at != 0 and not any(folders[below].rows for below in range(at, ends[at])):
        top = at
        at = parent_of(at)
    if top is None:
        gone = []
        touched = [ordinal] + ([parent_of(ordinal)] if ordinal else [])
    else:
        gone = list(range(top, ends[top]))
        touched = [parent_of(top)]
    index = Index([folder for at, folder in enumerate(folders) if at not in gone])
    index_actions = _index_actions(storage, index, touched, gone=[old.folders[at].id for at in gone])
    commit(storage, catalog, removed=(name,), actions=[("remove", name)], index=index, index_actions=index_actions)


def move(storage, name, before=None):
    """Moves a drive's animation `name` among its folder's files: right before the file
    `before`, or last when it is None. A move that changes nothing writes nothing."""
    catalog = _usable(storage)
    if catalog.index is None:
        raise Unusable(catalog.state, "no index")
    found = catalog.index.find(name)
    if found is None:
        raise errors.Rejection(errors.FILE_MISSING, f"the catalog has no {name}")
    ordinal, row = found
    rows = list(catalog.index.folders[ordinal].rows)
    moved = rows.pop(row)
    if before is None:
        rows.append(moved)
    else:
        target = catalog.index.find(before)
        if target is None or target[0] != ordinal:
            raise errors.Rejection(errors.FILE_MISSING, f"{before} is no file of the folder of {name}")
        if before == name:
            return
        rows.insert(next(at for at, (_, entry) in enumerate(rows) if entry.name == before), moved)
    if rows == catalog.index.folders[ordinal].rows:
        return
    folders = [Folder(folder.path, folder.id, list(folder.rows)) for folder in catalog.index.folders]
    folders[ordinal].rows = rows
    index = Index(folders)
    index_actions = _index_actions(storage, index, [ordinal])
    commit(storage, catalog, index=index, index_actions=index_actions)


def _sound_old(storage):
    """The old index of a drive's catalog as a rebuild takes it, `(rows, names, ids)`: for
    each folder's path, first in the table, the names of its file rows in their order; the
    names of its pages' lines; and the ids of its folders, in the table's order. Given when
    its marker is of version 2 and every page, the table, the map and each folder's file
    agree with their CRC-32s and each line is in its form; None otherwise. The rows are
    taken as they stand, not made again."""
    try:
        marker = parse_marker(storage.read(MARKER) or b"", drive=True)
        names = set()
        for number in range(PAGES):
            page = storage.read(page_name(number)) if marker.counts[number] else b""
            if page is None:
                return None
            names |= {entry.name for entry in parse_page(page, number, marker)}
        table = storage.read(FOLDERS) or b""
        ids = storage.read(IDS) or b""
        if len(table) // ROW != marker.folders[0] or crc(table) != marker.folders[1] or len(ids) // ID_ROW != marker.ids[0] or (crc(ids) if ids else 0) != marker.ids[1]:
            return None
        table_lines = unpadded(table, ROW)
        id_lines = unpadded(ids, ID_ROW) if ids else []
        if table_lines is None or id_lines is None or any(_MAP_ROW.fullmatch(line) is None for line in id_lines):
            return None
        rows_of = {}
        ids_of = []
        for ordinal, line in enumerate(table_lines):
            found = _TABLE_ROW.fullmatch(line)
            if found is None or int(found.group(1)) != ordinal:
                return None
            path, folder_id, expected = found.group(9) or "", int(found.group(2)), int(found.group(8), 16)
            text = storage.read(folder_file(folder_id)) if expected else b""
            if text is None or (crc(text) if text else 0) != expected:
                return None
            rows = unpadded(text, ROW) if text else []
            if rows is None:
                return None
            names_here = []
            for row in rows:
                file_row = _FILE_ROW.fullmatch(row)
                if file_row is not None:
                    names_here.append(file_row.group(8))
                elif _FOLDER_ROW.fullmatch(row) is None:
                    return None
            rows_of.setdefault(path, names_here)
            ids_of.append(folder_id)
        return rows_of, names, ids_of
    except Unusable:
        return None


def build_index(passed, old=None):
    """The index of a rebuild of the passed entries, in the listing's order: the folders of
    their paths in the listing's order, each folder's files those of the old index's rows of
    its path that passed, in their order, then those the old pages have no line for, by the
    bytes of their names; the files' ids in the walk's order from 60001, the folders' after
    them. `old` is what `_sound_old` gives, or None."""
    paths = {""}
    for entry in passed:
        parts = entry.name.split("/")[:-1]
        paths |= {"/".join(parts[:depth]) for depth in range(1, len(parts) + 1)}
    folders = [Folder(path, 0) for path in sorted(paths, key=folder_key)]
    by_name = {entry.name: entry for entry in passed}
    own = {folder.path: [] for folder in folders}
    for entry in passed:
        own[folder_of(entry.name)].append(entry)
    old_rows = old[0] if old is not None else {}
    next_id = FIRST_ID
    for folder in folders:
        chosen = []
        if old is not None:
            chosen += [by_name[name] for name in old_rows.get(folder.path, []) if name in by_name and folder_of(name) == folder.path]
            chosen += [entry for entry in own[folder.path] if entry.name not in old[1]]
        else:
            chosen = own[folder.path]
        for entry in chosen:
            folder.rows.append((next_id, entry))
            next_id += 1
    for ordinal, folder in enumerate(folders):
        if ordinal:
            folder.id = next_id
            next_id += 1
    return Index(folders)


def rebuild(storage, names=None, canvas=CANVAS, generation=None):
    """Writes the catalog of every animation that passes the check, as `catalog rebuild`
    does: the names in their order (the drive's listing when none are given), page by page,
    and of a drive its index. Returns `(catalog, refused)`, `refused` the names and their
    reasons."""
    finish(storage)
    drive = _drive(storage)
    old_marker = None
    try:
        old_marker = parse_marker(storage.read(MARKER) or b"", drive) if drive else None
    except Unusable:
        old_marker = None
    if generation is None:
        if drive:
            generation = next_generation(old_marker.generation if old_marker is not None else 0)
        else:
            old = read(storage)
            generation = next_generation(old.marker.generation if old.state == OK else 0)
    names = storage.names() if names is None else list(names)
    if drive:
        names = sorted(dict.fromkeys(names), key=listing_key)
    passed = {}
    refused = []
    for name in names:
        data = storage.read(name)
        try:
            if data is None:
                raise errors.Rejection(errors.FILE_MISSING, name)
            if not name_allowed(name):
                raise errors.Rejection(errors.FILE_MALFORMED, f"{name!r} is not a name a catalog may hold")
            passed[name] = entry_of(name, data, canvas)
        except errors.Rejection as rejection:
            refused.append((name, rejection.reason))
    refused.sort(key=lambda found: page_of(found[0]) if found[0].isascii() else -1)
    counts = [0] * PAGES
    crcs = [0] * PAGES
    for number in range(PAGES):
        text = b"".join(entry.line() for name, entry in passed.items() if page_of(name) == number)
        counts[number] = text.count(b"\n")
        if counts[number]:
            crcs[number] = crc(text)
            storage.write(new_page_name(number), text)
        else:
            storage.remove(new_page_name(number))
    if drive:
        old = _sound_old(storage)
        index = build_index(list(passed.values()), old)
        new_ids = {folder.id for folder in index.folders}
        gone = [folder_id for folder_id in old[2] if folder_id not in new_ids] if old is not None else []
        removals, moves = _index_actions(storage, index, range(len(index.folders)), gone=gone)
        actions = removals + moves
        folders, ids = index.counts()
        marker = Marker(generation, tuple(counts), tuple(crcs), folders, ids)
    else:
        actions = []
        marker = Marker(generation, tuple(counts), tuple(crcs))
    storage.write(NEW_MARKER, marker.text())
    storage.write(DO, do_text(generation, 0xFFFF, actions))
    finish(storage)
    return read(storage), refused


def check(storage):
    """Each entry whose file is gone or differs from it: `(name, what)`, `what` being
    `missing`, `size` or `crc`."""
    catalog = read(storage)
    if catalog.state != OK:
        raise Unusable(catalog.state, catalog.detail)
    found = []
    for entry in catalog.entries:
        data = storage.read(entry.name)
        if data is None:
            found.append((entry.name, "missing"))
        elif len(data) != entry.bytes:
            found.append((entry.name, "size"))
        elif crc(data) != entry.crc:
            found.append((entry.name, "crc"))
    return found


def recover(storage):
    """Finishes an interrupted change, then removes what a change that was not committed
    left: a torn commit record, the new marker, pages and index files, an upload's part and
    a rebuild's own files. Returns the names removed."""
    finish(storage)
    removed = []
    names = [DO, NEW_MARKER, PART] + [new_page_name(number) for number in range(PAGES)]
    if _drive(storage):
        names += storage.leftovers() + [SCAN, DRAFT]
    for name in names:
        if storage.remove(name):
            removed.append(name)
    return removed


def _state_line(storage):
    """The line `status` prints for a storage, and its exit status."""
    made = read(storage)
    files = storage.names()
    if made.state == NONE:
        return f"catalog: none; {len(files)} animation files; import writes the catalog", 0
    if made.state != OK:
        advice = "; recover finishes the change" if made.detail == "interrupted" else ""
        return f"catalog: {made.state}, {made.detail}{advice}", 1
    named = {entry.name for entry in made.entries}
    without = sum(1 for name in files if name not in named)
    return (f"catalog: ok, generation {made.marker.generation}, {len(made.entries)} entries; "
            f"{len(files)} animation files, {without} without an entry"), 0


def _status(storage, arguments):
    line, status = _state_line(storage)
    print(line)
    return status


def _import(storage, arguments):
    made, refused = rebuild(storage)
    for name, reason in refused:
        print(f"refused: {name}: {reason}")
    print(f"imported: {len(made.entries)} animations, generation {made.marker.generation}")
    return 1 if refused else 0


def _add(storage, arguments):
    status = 0
    for path in arguments.files:
        name = os.path.basename(path)
        try:
            with open(path, "rb") as file:
                data = file.read()
        except OSError:
            print(f"refused: {name}: {errors.FILE_MISSING}")
            status = 1
            continue
        known = read(storage)
        replaced = known.state == OK and known.entry(name) is not None
        try:
            entry = add(storage, name, data)
        except errors.Rejection as rejection:
            print(f"refused: {name}: {rejection.reason}")
            status = 1
            continue
        print(f"{'replaced' if replaced else 'added'}: {name}, {entry.bytes} bytes")
    return status


def _remove(storage, arguments):
    status = 0
    for name in arguments.names:
        try:
            remove(storage, name)
        except errors.Rejection as rejection:
            print(f"refused: {name}: {rejection.reason}")
            status = 1
            continue
        print(f"removed: {name}")
    return status


def _check(storage, arguments):
    found = check(storage)
    for name, what in found:
        print(f"differs: {name}: {what}")
    print(f"checked: {len(read(storage).entries)} entries, {len(found)} differ")
    return 1 if found else 0


def _recover(storage, arguments):
    finished = finish(storage)
    removed = recover(storage)
    if finished:
        print("recovered: finished an interrupted change")
    if removed:
        print(f"recovered: removed {', '.join(removed)}")
    if not finished and not removed:
        print("recovered: nothing to do")
    return _status(storage, arguments)


_COMMANDS = {"status": _status, "import": _import, "add": _add, "remove": _remove, "check": _check, "recover": _recover}


def main(argv=None):
    """`python3 -m odrig.catalog [--folder] MOUNT COMMAND`: manages the folder `odrig` of a card
    mounted at MOUNT on this computer, or with `--folder` the folder MOUNT itself. Prints one
    line for each outcome. Exit status 0; 1 when a file was refused, a file differs from its
    entry or the catalog cannot be used; 2 for a command line that is not understood."""
    import argparse

    made = argparse.ArgumentParser(
        prog="python3 -m odrig.catalog",
        description="Manages the catalog of the animations of a card mounted on this computer, in the card's folder odrig.",
    )
    made.add_argument("--folder", action="store_true", help="MOUNT is the folder odrig itself")
    made.add_argument("mount", metavar="MOUNT", help="where the card is mounted")
    commands = made.add_subparsers(dest="command", metavar="COMMAND", required=True)
    commands.add_parser("status", help="say what the catalog is and how many animation files the folder holds")
    commands.add_parser("import", help="check every animation file of the folder and write the catalog and its index anew")
    adding = commands.add_parser("add", help="put files into the folder, each checked and with its entry, in place of one of the same name")
    adding.add_argument("files", metavar="FILE", nargs="+")
    removing = commands.add_parser("remove", help="take animations out of the folder, each with its entry")
    removing.add_argument("names", metavar="NAME", nargs="+")
    commands.add_parser("check", help="compare each file's size and CRC-32 with its entry")
    commands.add_parser("recover", help="finish a change that was cut, and remove what a change that was not committed left")
    arguments = made.parse_args(argv)
    folder = arguments.mount if arguments.folder else os.path.join(arguments.mount, "odrig")
    if not os.path.isdir(folder):
        made.error(f"{folder} is not a folder")
    storage = Storage(folder, drive=True)
    try:
        return _COMMANDS[arguments.command](storage, arguments)
    except Unusable as unusable:
        detail = f", {unusable.detail}" if unusable.detail and unusable.state != NONE else ""
        if unusable.detail == "interrupted":
            advice = "recover finishes the change"
        elif unusable.state == NONE:
            advice = "import writes it"
        else:
            advice = "import writes it anew"
        print(f"error: the catalog is {unusable.state}{detail}; {advice}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""The catalog of a storage of animations, as docs/catalog.md states it, and the changes a
computer makes to it.

The core keeps the same catalogs on the board, in C++. This module does what the core does,
step by step and with the same storage calls, so that the same changes leave the same files.
`python3 -m odrig.catalog` manages the folder `odrig` of a card mounted on a computer.
"""

import binascii
import dataclasses
import os
import re
import sys

from . import errors, odrg

FORMAT = 1
CHECK = 1
PAGES = 16
MARKER = "catalog.txt"
NEW_MARKER = "catalog.new"
DO = "catalog.do"
PART = "upload.part"
MARKER_SIZE = 409
LONGEST_NAME = 100
LONGEST_LIST = 256
# The canvas of the installation, which a card's animations are for.
CANVAS = (60, 60)
TYPES = ("frames", "text", "widget")
FORBIDDEN = set('/\\:*?"<>|')

# What a catalog is: none (the storage has no catalog), ok, damaged, incompatible.
NONE = "none"
OK = "ok"
DAMAGED = "damaged"
INCOMPATIBLE = "incompatible"

_FIRST_LINE = re.compile(r"odrig-catalog (0|[1-9][0-9]{0,8}) check (0|[1-9][0-9]{0,8}) generation ([0-9a-f]{8})")
_PAGE_LINE = re.compile(r"page ([0-9]{2}) ([0-9]{4}) ([0-9a-f]{8})")
_CRC_LINE = re.compile(r"crc ([0-9a-f]{8})")
_ENTRY = re.compile(r"([0-9a-f]{8}) (0|[1-9][0-9]{0,9}) ([1-9][0-9]{0,4}) ([1-9][0-9]{0,4}) (0|[1-9][0-9]{0,19}) (frames|text|widget) (.+)")
_DO_FIRST = re.compile(r"odrig-catalog-do 1 generation ([0-9a-f]{8})")
_DO_PAGES = re.compile(r"pages ([0-9a-f]{4})")
_DO_MOVE = re.compile(r"move ([^ ]+) (.+)")
_DO_REMOVE = re.compile(r"remove (.+)")


def page_name(number):
    return f"catalog-{number:02d}.txt"


def new_page_name(number):
    return f"catalog-{number:02d}.new"


def crc(data):
    """The CRC-32 of zlib."""
    return binascii.crc32(data) & 0xFFFFFFFF


def page_of(name):
    """The page of a name: the low four bits of the FNV-1a hash of its bytes."""
    value = 2166136261
    for byte in name.encode("ascii"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value & 15


def name_allowed(name):
    """Whether a catalog may hold a file of this name."""
    if not 1 <= len(name) <= LONGEST_NAME or not name.isascii():
        return False
    if any(not 0x20 <= ord(character) <= 0x7E or character in FORBIDDEN for character in name):
        return False
    if name[0] in ". " or name[-1] in ". " or name.isdigit():
        return False
    return name.lower().endswith(".odrg")


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
    """The marker: the generation, and each page's count of entries and CRC-32."""

    generation: int
    counts: tuple
    crcs: tuple

    def text(self):
        made = f"odrig-catalog {FORMAT} check {CHECK} generation {self.generation:08x}\n"
        for number in range(PAGES):
            made += f"page {number:02d} {self.counts[number]:04d} {self.crcs[number]:08x}\n"
        made = made.encode("ascii")
        return made + f"crc {crc(made):08x}\n".encode("ascii")


EMPTY = Marker(0, (0,) * PAGES, (0,) * PAGES)


def next_generation(generation):
    return 1 if generation >= 0xFFFFFFFF else generation + 1


def parse_marker(data):
    """The marker these bytes hold. Raises `Unusable`."""
    first = data.split(b"\n", 1)[0]
    found = _FIRST_LINE.fullmatch(first.decode("ascii", "replace"))
    if found is not None and (int(found.group(1)) != FORMAT or int(found.group(2)) != CHECK):
        raise Unusable(INCOMPATIBLE, f"format {found.group(1)}, check {found.group(2)}")
    if found is None or len(data) != MARKER_SIZE or not data.endswith(b"\n"):
        raise Unusable(DAMAGED, "marker")
    lines = data.decode("ascii", "replace").split("\n")[:-1]
    if len(lines) != 2 + PAGES:
        raise Unusable(DAMAGED, "marker")
    closing = _CRC_LINE.fullmatch(lines[-1])
    if closing is None or int(closing.group(1), 16) != crc(data[: MARKER_SIZE - 13]):
        raise Unusable(DAMAGED, "marker")
    generation = int(found.group(3), 16)
    counts = []
    crcs = []
    for number, line in enumerate(lines[1:-1]):
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
    return Marker(generation, tuple(counts), tuple(crcs))


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
    admits it. Raises `errors.Rejection` with the check's reason."""
    decoded = odrg.decode(data)
    if canvas is not None and (decoded.width, decoded.height) != tuple(canvas):
        raise errors.Rejection(errors.SIZE_MISMATCH, f"the file is {decoded.width} x {decoded.height}, the canvas {canvas[0]} x {canvas[1]}")
    return Entry(name, len(data), crc(data), decoded.width, decoded.height, sum(duration for duration, _ in decoded.records))


class Storage:
    """The files of one folder, by name, with the calls the core makes of its host."""

    def __init__(self, folder):
        self.folder = os.fspath(folder)

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
        """The animation files of the folder as a drive lists them: names ending in `.odrg`
        in any case and not beginning with a dot, in the order of their bytes, the first 256."""
        try:
            with os.scandir(self.folder) as entries:
                found = [entry.name for entry in entries if entry.is_file()]
        except OSError:
            return []
        kept = [name for name in found if name.lower().endswith(".odrg") and not name.startswith(".")]
        return sorted(kept, key=os.fsencode)[:LONGEST_LIST]


class MemoryStorage(Storage):
    """Files held in a dict, for a folder that is made before it is written anywhere."""

    def __init__(self, files=None):
        self.files = dict(files or {})

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
        kept = [name for name in self.files if name.lower().endswith(".odrg") and not name.startswith(".")]
        return sorted(kept, key=lambda name: name.encode("utf-8", "surrogateescape"))[:LONGEST_LIST]


@dataclasses.dataclass
class Catalog:
    """What a storage's catalog is: its state, and for one that is ok its marker and its
    entries, page by page in the order of their lines."""

    state: str
    detail: str = ""
    marker: Marker = EMPTY
    entries: list = dataclasses.field(default_factory=list)

    def entry(self, name):
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None


def read(storage):
    """The catalog of a storage, without changing anything."""
    if parse_do(storage.read(DO) or b"") is not None:
        return Catalog(DAMAGED, "interrupted")
    data = storage.read(MARKER)
    if data is None:
        return Catalog(NONE)
    try:
        marker = parse_marker(data)
        entries = []
        for number in range(PAGES):
            page = storage.read(page_name(number)) if marker.counts[number] else b""
            if page is None:
                raise Unusable(DAMAGED, "page")
            entries += parse_page(page, number, marker)
        if len({entry.name for entry in entries}) != len(entries):
            raise Unusable(DAMAGED, "line")
    except Unusable as unusable:
        return Catalog(unusable.state, unusable.detail)
    return Catalog(OK, "", marker, entries)


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
        counts = parse_marker(new if new is not None else storage.read(MARKER) or b"").counts
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


def commit(storage, catalog, removed=(), added=None, actions=()):
    """Commits a change of the catalog `catalog` read from the storage: the entries of the
    names `removed` taken out, the entry `added` added or put in the place of the entry of
    its name, and the actions done before the pages are. Finishes it, and returns the new
    catalog."""
    pages = sorted({page_of(name) for name in removed} | ({page_of(added.name)} if added is not None else set()))
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
    generation = next_generation(catalog.marker.generation)
    storage.write(NEW_MARKER, Marker(generation, tuple(counts), tuple(crcs)).text())
    storage.write(DO, do_text(generation, sum(1 << number for number in pages), actions))
    finish(storage)
    return read(storage)


def add(storage, name, data, canvas=CANVAS):
    """Adds the animation `name` with these bytes, or replaces the one of that name, as an
    upload does: the bytes go to `upload.part`, are read back and checked, and the change
    moves them onto the name. Returns the entry."""
    if not name_allowed(name):
        raise errors.Rejection(errors.FILE_MALFORMED, f"{name!r} is not a name a catalog may hold")
    catalog = _usable(storage)
    storage.write(PART, data)
    try:
        entry = entry_of(name, storage.read(PART), canvas)
    except errors.Rejection:
        storage.remove(PART)
        raise
    commit(storage, catalog, added=entry, actions=[("move", PART, name)])
    return entry


def remove(storage, name):
    """Removes the animation `name`: its file and its entry."""
    catalog = _usable(storage)
    if catalog.entry(name) is None:
        raise errors.Rejection(errors.FILE_MISSING, f"the catalog has no {name}")
    commit(storage, catalog, removed=(name,), actions=[("remove", name)])


def rebuild(storage, names=None, canvas=CANVAS, generation=None):
    """Writes the catalog of every animation that passes the check, as `catalog rebuild`
    does: the names in their order (the drive's listing when none are given), page by page.
    Returns `(catalog, refused)`, `refused` the names and their reasons."""
    finish(storage)
    if generation is None:
        old = read(storage)
        generation = next_generation(old.marker.generation if old.state == OK else 0)
    names = storage.names() if names is None else list(names)
    counts = [0] * PAGES
    crcs = [0] * PAGES
    refused = []
    for number in range(PAGES):
        text = b""
        for name in names:
            if page_of(name) != number:
                continue
            data = storage.read(name)
            try:
                if data is None:
                    raise errors.Rejection(errors.FILE_MISSING, name)
                if not name_allowed(name):
                    raise errors.Rejection(errors.FILE_MALFORMED, f"{name!r} is not a name a catalog may hold")
                text += entry_of(name, data, canvas).line()
            except errors.Rejection as rejection:
                refused.append((name, rejection.reason))
                continue
            counts[number] += 1
        if counts[number]:
            crcs[number] = crc(text)
            storage.write(new_page_name(number), text)
        else:
            storage.remove(new_page_name(number))
    storage.write(NEW_MARKER, Marker(generation, tuple(counts), tuple(crcs)).text())
    storage.write(DO, do_text(generation, 0xFFFF, []))
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
    left: a torn commit record, the new marker and pages, and an upload's part. Returns the
    names removed."""
    finish(storage)
    removed = []
    for name in [DO, NEW_MARKER, PART] + [new_page_name(number) for number in range(PAGES)]:
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
    commands.add_parser("import", help="check every animation file of the folder and write the catalog anew")
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
    storage = Storage(folder)
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

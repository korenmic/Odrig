"""The board's storage as an image: its LittleFS file system, the folder `/odrig` in it, and
the blocks in which two images differ."""

import collections
import json
import pathlib
import struct
import time

from littlefs import LittleFS, UserContext
from littlefs.errors import LittleFSError

from odrig import catalog
from odrig import errors as show_errors
from odrig import mapping, odrg, show

from . import Failure, paths

FOLDER = "/odrig"
MAPPING_NAME = "mapping.json"
SHOW_NAME = "show.json"
# The saved playlist order, which a show folder may hold beside the files of the show.
ORDER_NAME = "order.txt"
# The files of the internal catalog: its marker and its pages.
CATALOG_NAMES = (catalog.MARKER, *(catalog.page_name(number) for number in range(catalog.PAGES)))
MARK = b"littlefs"
NO_SPACE = -28
KEPT_IMAGES = 8
# The block sizes a file system of the board can have, WLED's first.
USUAL_BLOCK_SIZES = (4096, 512, 1024, 2048, 8192, 16384, 32768, 65536)
PENDING = ".part"
# The beginning of the name under which a changed file of `/odrig` is written before it takes
# the place of the old one, in the image on this computer only.
SPARE = "~"


def geometry(image):
    """The disk version, the block size and the number of blocks, from the superblock.

    littlefs reads the figures from the newest commit of the superblock, given the block
    size: the one a copy of the figures right after the superblock's mark names, else each
    of the usual ones. A file system that has grown, or whose superblock has been written
    again, keeps its figures elsewhere in its first block."""
    if image.find(MARK) < 0:
        raise Failure("layout-mismatch", "storage holds no LittleFS file system")
    sizes = []
    at = image.find(MARK)
    while 0 <= at and at + 24 <= len(image):
        _, block_size, _ = struct.unpack_from("<III", image, at + 12)
        if block_size >= 128 and block_size & (block_size - 1) == 0 and block_size not in sizes:
            sizes.append(block_size)
        at = image.find(MARK, at + 1)
    sizes += [size for size in USUAL_BLOCK_SIZES if size not in sizes]
    for block_size in sizes:
        if len(image) % block_size:
            continue
        system = LittleFS(block_size=block_size, block_count=0, mount=False)
        system.context.buffer = bytearray(image)
        try:
            system.mount()
        except LittleFSError:
            continue
        found = system.fs_stat()
        if found.block_size * found.block_count != len(image):
            raise Failure("layout-mismatch", f"the file system has {found.block_count} blocks of {found.block_size} bytes, and storage {len(image)} bytes")
        return found.disk_version, found.block_size, found.block_count
    raise Failure("layout-mismatch", "storage holds no LittleFS file system")


def mount(image):
    """Mounts an image at the disk version it has, so that it keeps that version."""
    version, block_size, block_count = geometry(image)
    system = LittleFS(block_size=block_size, block_count=block_count, mount=False, disk_version=version)
    system.context.buffer = bytearray(image)
    system.mount()
    return system


def files_in(system, folder="/"):
    """The content of every file under a folder, by its full path."""
    found = {}
    for root, _, names in system.walk(folder):
        for name in names:
            path = root.rstrip("/") + "/" + name
            with system.open(path, "rb") as file:
                found[path] = file.read()
    return found


def has_folder(system, folder):
    try:
        return (system.stat(folder).type & 0x02) != 0
    except LittleFSError:
        return False


def show_of(image):
    """The files of `/odrig` in an image: the content of each by its name."""
    system = mount(image)
    if not has_folder(system, FOLDER):
        return {}
    return {path[len(FOLDER) + 1:]: content for path, content in files_in(system, FOLDER).items()}


def other_files(image):
    """Every file of an image outside `/odrig`."""
    return {path: content for path, content in files_in(mount(image)).items() if not path.startswith(FOLDER + "/")}


Change = collections.namedtuple("Change", "kept added replaced removed")


def change_of(present, wanted):
    """What turns the files `present` into the files `wanted`, each by its name: the names
    kept with their bytes, the names added, the names whose bytes are replaced, and the
    names removed, each list in the order of the names."""
    return Change(
        sorted(name for name in wanted if present.get(name) == wanted[name]),
        sorted(name for name in wanted if name not in present),
        sorted(name for name in wanted if name in present and present[name] != wanted[name]),
        sorted(name for name in present if name not in wanted),
    )


def _spare_name(taken):
    """A short name that no file of `taken` has: a new file waits under it until it takes
    the place of the file it replaces."""
    number = 0
    while f"{SPARE}{number}" in taken:
        number += 1
    return f"{SPARE}{number}"


def _changed(image, present, wanted, write_first):
    """The image with the files of `/odrig` changed from `present` to `wanted`, and nothing
    else touched. With `write_first` every new and changed file is written while the files
    of the image before are all still there, so that the file system puts the new bytes
    into blocks the image before does not use; a changed file waits under a spare name and
    then takes the place of the old one, and the files that go are removed last. Without
    it the files that go and the files that change are removed first, which leaves the
    most room."""
    change = change_of(present, wanted)
    system = mount(image)
    if not has_folder(system, FOLDER):
        system.mkdir(FOLDER)
    gone = change.removed if write_first else change.removed + change.replaced
    if not write_first:
        for name in gone:
            system.remove(f"{FOLDER}/{name}")
    taken = set(present) | set(wanted)
    waiting = []
    for name in sorted(change.added + change.replaced):
        target = name
        if write_first and name in present:
            target = _spare_name(taken)
            taken.add(target)
            waiting.append((target, name))
        with system.open(f"{FOLDER}/{target}", "wb") as file:
            file.write(wanted[name])
    for target, name in waiting:
        system.rename(f"{FOLDER}/{target}", f"{FOLDER}/{name}")
    if write_first:
        for name in gone:
            system.remove(f"{FOLDER}/{name}")
    # A folder inside `/odrig` that is empty now goes too.
    for root, folders, names in list(system.walk(FOLDER))[::-1]:
        if root.rstrip("/") != FOLDER and not folders and not names:
            system.rmdir(root.rstrip("/"))
    system.unmount()
    return bytes(system.context.buffer)


def with_show(image, files):
    """The image with `/odrig` holding exactly the files given, and everything else as it
    was. A file the folder holds with the same bytes stays where it is, unread and
    unwritten; only the files that are new, changed or gone are written or removed. The
    result is checked before it is returned. An image that holds exactly these files
    already is returned as it is."""
    wanted = dict(files)
    present = show_of(image)
    if present == wanted:
        return image
    try:
        try:
            made = _changed(image, present, wanted, write_first=True)
        except LittleFSError as error:
            if error.code != NO_SPACE:
                raise
            made = _changed(image, present, wanted, write_first=False)
    except LittleFSError as error:
        if error.code == NO_SPACE:
            raise Failure("no-space", f"the {len(files)} files, {sum(map(len, files.values()))} bytes, do not fit into storage") from None
        raise Failure("verify-failed", f"the file system refused the files: {error}") from None
    if geometry(made) != geometry(image):
        raise Failure("verify-failed", "the file system changed its version or its size")
    difference = differing(show_of(made), wanted)
    if difference:
        raise Failure("verify-failed", f"{FOLDER} in the new image does not hold exactly the files given: {difference}")
    difference = differing(other_files(made), other_files(image))
    if difference:
        raise Failure("verify-failed", f"a file outside {FOLDER} changed in the new image: {difference}")
    kept = change_of(present, wanted).kept
    before, after = blocks_of_files(image), blocks_of_files(made)
    moved = [path for path in sorted(before) if path in after and before[path] != after[path]
             and (not path.startswith(FOLDER + "/") or path[len(FOLDER) + 1:] in kept)]
    if moved:
        raise Failure("verify-failed", f"a file that did not change was moved in the new image: {', '.join(moved)}")
    return made


class _Watched(UserContext):
    """The image of a file system in memory, which notes every block that is read."""

    def __init__(self, image):
        super().__init__(buffer=bytearray(image))
        self.blocks = set()

    def read(self, cfg, block, off, size):
        self.blocks.add(block)
        return super().read(cfg, block, off, size)


def _watched(image):
    version, block_size, block_count = geometry(image)
    context = _Watched(image)
    system = LittleFS(context=context, block_size=block_size, block_count=block_count, mount=False, disk_version=version)
    system.mount()
    return system, context


def blocks_in_use(image):
    """The blocks the file system of an image uses: the two of its superblock, its metadata
    pairs and the blocks of every file. They are the blocks it reads while it counts its
    used blocks and while every file is read to its end."""
    system, context = _watched(image)
    system.used_block_count
    for root, _, names in system.walk("/"):
        for name in names:
            with system.open(root.rstrip("/") + "/" + name, "rb") as file:
                file.read()
    return context.blocks | {0, 1}


def blocks_of_files(image):
    """The blocks of its own that each file of an image is read from, by its full path:
    the blocks its bytes are read from, less the blocks of the file system's records, which
    the folders' lists and the opening of files read. A small file kept inside those records
    has none of its own."""
    system, context = _watched(image)
    listed = [root.rstrip("/") + "/" + name for root, _, names in system.walk("/") for name in names]
    records = set(context.blocks)
    found = {}
    for path in listed:
        with system.open(path, "rb") as file:
            records |= context.blocks
            context.blocks = set()
            file.read()
            found[path] = set(context.blocks)
            context.blocks = set()
    return {path: frozenset(blocks - records) for path, blocks in found.items()}


def with_settings(image, size, room=None):
    """A storage image of `size` bytes that holds the settings of `image`, every file of it
    outside `/odrig`, and no show, in a file system of the disk version and the block size
    of `image`. With `room`, everything the file system holds lies in its first `room`
    bytes: it is made that large and then grown. The result is checked before it is
    returned."""
    version, block_size, _ = geometry(image)
    settings = other_files(image)
    blocks = size // block_size
    system = LittleFS(block_size=block_size, block_count=(room or size) // block_size, disk_version=version, mount=False)
    system.format()
    system.mount()
    try:
        for path in sorted(settings):
            folder = path.rsplit("/", 1)[0]
            if folder:
                system.makedirs(folder, exist_ok=True)
            with system.open(path, "wb") as file:
                file.write(settings[path])
        if room is not None:
            system.fs_grow(blocks)
        system.unmount()
    except LittleFSError as error:
        raise Failure("verify-failed", f"the file system refused the settings: {error}") from None
    made = bytes(system.context.buffer)
    made += b"\xff" * (size - len(made))
    if geometry(made) != (version, block_size, blocks):
        raise Failure("verify-failed", "the new storage does not have the size it was made for")
    difference = differing(other_files(made), settings)
    if difference or show_of(made):
        raise Failure("verify-failed", f"the new storage does not hold exactly the settings: {difference or FOLDER}")
    if room is not None and made[room:] != b"\xff" * (size - room):
        raise Failure("verify-failed", f"the new storage holds something beyond its first {room} bytes")
    return made


def differing(found, wanted):
    """What differs between two sets of files, in words; empty when nothing does."""
    said = []
    said += [f"{name} is there and should not be" for name in sorted(set(found) - set(wanted))]
    said += [f"{name} is missing" for name in sorted(set(wanted) - set(found))]
    said += [f"{name} has other bytes" for name in sorted(set(found) & set(wanted)) if found[name] != wanted[name]]
    return "; ".join(said)


def runs(old, new, block_size, among=None):
    """The stretches in which two images differ, as `(offset, bytes of the new image)`:
    whole blocks, neighbouring changed blocks joined. With `among`, a set of block numbers,
    only the changed blocks that are among them."""
    found, start = [], None
    for offset in range(0, len(new) + block_size, block_size):
        differs = offset < len(new) and old[offset:offset + block_size] != new[offset:offset + block_size]
        differs = differs and (among is None or offset // block_size in among)
        if differs and start is None:
            start = offset
        elif not differs and start is not None:
            found.append((start, new[start:offset]))
            start = None
    return found


def _rejected(rejection):
    return Failure(rejection.reason, rejection.detail)


def folder_files(folder, check=True):
    """The files of a show folder: the content of each by its name.

    The folder must be flat. With `check` it must also be a valid installed file set, as
    the readers of the converter judge it, and hold no file the show does not name.
    """
    folder = pathlib.Path(folder)
    if not folder.is_dir():
        raise Failure("not-a-show-folder", f"{folder} is not a folder")
    entries = sorted(folder.iterdir())
    for entry in entries:
        if not entry.is_file():
            raise Failure("not-a-show-folder", f"{entry} is not a file; a show folder is flat")
    files = {entry.name: entry.read_bytes() for entry in entries}
    if check:
        # A folder's own catalog, as `read-show` copies it, is made anew.
        files = {name: data for name, data in files.items() if name not in CATALOG_NAMES}
        try:
            canvas = mapping.read(folder / MAPPING_NAME)
            named = show.files(show.read(folder / SHOW_NAME))
            for name in named:
                if name not in files:
                    raise show_errors.Rejection(show_errors.FILE_MISSING, f"{folder / name}: the show names it and it is not there")
            # The catalog's rebuild reads each animation once and refuses what the check
            # refuses; the first refused in the show's order is judged again for its words. A
            # name the catalog cannot hold is checked alone and left out of the catalog.
            allowed = [name for name in named if catalog.name_allowed(name)]
            made, refused = catalog_files(files, allowed, (canvas.width, canvas.height))
            refused_names = sorted((name for name, _ in refused), key=named.index)
            for name in refused_names[:1] + [name for name in named if name not in allowed]:
                _check_animation(folder / name, files[name], canvas)
            if refused:
                raise show_errors.Rejection(show_errors.FILE_MALFORMED, f"{folder / refused_names[0]}: {dict(refused)[refused_names[0]]}")
        except show_errors.Rejection as rejection:
            raise _rejected(rejection) from None
        for name in files:
            if name not in (MAPPING_NAME, SHOW_NAME, ORDER_NAME, *named):
                raise Failure("not-a-show-folder", f"{folder / name} is not a file of the show")
        files.update(made)
    return files


def _check_animation(path, data, canvas):
    """Refuses an animation file the readers of the converter refuse, or of another canvas."""
    try:
        animation = odrg.decode(data)
    except show_errors.Rejection as rejection:
        raise show_errors.Rejection(show_errors.FILE_MALFORMED, f"{path}: {rejection.reason}: {rejection.detail}") from None
    if (animation.width, animation.height) != (canvas.width, canvas.height):
        raise show_errors.Rejection(show_errors.SIZE_MISMATCH, f"{path}: the canvas is {animation.width} x {animation.height} and the mapping's is {canvas.width} x {canvas.height}")


def catalog_files(files, names, canvas, generation=1):
    """The files of the internal catalog of the animations `names` of `files`, as a rebuild
    writes them: the names in their order, each checked for the canvas. Returns them, and the
    names refused with their reasons."""
    memory = catalog.MemoryStorage({name: files[name] for name in names})
    _, refused = catalog.rebuild(memory, names=names, canvas=canvas, generation=generation)
    return {name: data for name, data in memory.files.items() if name in CATALOG_NAMES}, refused


def with_board_generation(files, present):
    """The files of a folder with the marker of their catalog made for the board, whose files
    of `/odrig` are `present`: the board's own marker when its catalog has the same pages, so
    that nothing changes; otherwise one of the generation after the board's, or of 1 when the
    board has no catalog it can read."""
    if catalog.MARKER not in files:
        return files
    new = catalog.parse_marker(files[catalog.MARKER])
    try:
        old = catalog.parse_marker(present.get(catalog.MARKER, b""))
    except catalog.Unusable:
        return files
    if (old.counts, old.crcs) == (new.counts, new.crcs):
        return dict(files, **{catalog.MARKER: present[catalog.MARKER]})
    marker = catalog.Marker(catalog.next_generation(old.generation), new.counts, new.crcs)
    return dict(files, **{catalog.MARKER: marker.text()})


def write_folder(folder, files):
    """Copies files into a folder that is new or empty."""
    folder = paths.output(folder)
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        raise Failure("output-not-empty", f"{folder} exists and is not an empty folder")
    folder.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (folder / name).write_bytes(content)


def stamp():
    return time.strftime("%Y%m%dT%H%M%S")


def kept_images(size):
    """The storage images of that size in the work folder, newest first."""
    if not paths.STORAGE.is_dir():
        return []
    images = [path for path in paths.STORAGE.glob("*.bin") if path.stat().st_size == size]
    return sorted(images, key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)


def prune(size):
    """Removes all but the newest storage images from the work folder."""
    for path in kept_images(size)[KEPT_IMAGES:]:
        path.unlink()


def from_board(on_port, region):
    """A file in the work folder that holds the board's storage as it is now. The chip stays
    in its bootloader.

    The newest image the work folder holds is taken when the board's storage has its
    checksum, which esptool has the chip work out; otherwise the whole partition is read.
    """
    newest = kept_images(region.size)[:1]
    for image in newest:
        try:
            on_port.verify(region.address, image, [region], restart=False)
            return image
        except Failure as failure:
            if failure.reason != "verify-failed":
                raise
    return on_port.read(region.address, region.size, paths.STORAGE / f"{stamp()}-before.bin", [region])


def pending(image):
    """Writes a new storage image into the work folder under a name that is not yet one of
    the kept images, and returns its path."""
    folder = paths.output(paths.STORAGE)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stamp()}-after.bin{PENDING}"
    number = 1
    while path.exists() or path.with_name(path.name[:-len(PENDING)]).exists():
        number += 1
        path = folder / f"{stamp()}-after-{number}.bin{PENDING}"
    path.write_bytes(image)
    return path


def keep(path, size):
    """Makes a pending image, which the board now holds, the newest kept image."""
    kept = path.with_name(path.name[:-len(PENDING)])
    path.replace(kept)
    prune(size)
    return kept


def discard(path):
    """Removes a pending image that did not reach the board."""
    path.unlink(missing_ok=True)


def status_error(reply):
    """The `error` member of a reply to `status`: None for a valid show."""
    return json.loads(reply).get("error")


# The runs of a change, as `(offset, bytes)` in the storage region, in its two parts: the
# blocks the board's file system does not use, and the blocks it uses.
Plan = collections.namedtuple("Plan", "free in_use")


def plan(before, after):
    """The change from the image the board holds to the new one, in the two parts it is
    written in: the runs of blocks the file system of `before` does not use, which can be
    written without changing what the board's file system holds, and the runs of blocks it
    uses, whose writing is the commit."""
    block_size = geometry(before)[1]
    in_use = blocks_in_use(before)
    every = range(len(before) // block_size)
    return Plan(runs(before, after, block_size, set(every) - in_use), runs(before, after, block_size, in_use))


def run_bytes(found):
    """The bytes of a list of runs."""
    return sum(len(content) for _, content in found)

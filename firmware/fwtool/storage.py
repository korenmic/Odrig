"""The board's storage as an image: its LittleFS file system, the folder `/odrig` in it, and
the blocks in which two images differ."""

import json
import pathlib
import struct
import time

from littlefs import LittleFS
from littlefs.errors import LittleFSError

from odrig import errors as show_errors
from odrig import mapping, odrg, show

from . import Failure, paths

FOLDER = "/odrig"
MAPPING_NAME = "mapping.json"
SHOW_NAME = "show.json"
MARK = b"littlefs"
NO_SPACE = -28
KEPT_IMAGES = 8
# The block sizes a file system of the board can have, WLED's first.
USUAL_BLOCK_SIZES = (4096, 512, 1024, 2048, 8192, 16384, 32768, 65536)
PENDING = ".part"


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


def remove_tree(system, folder):
    """Removes a folder with everything in it. A folder that is absent is fine."""
    if not has_folder(system, folder):
        return
    for root, folders, names in list(system.walk(folder))[::-1]:
        for name in names:
            system.remove(root.rstrip("/") + "/" + name)
        for name in folders:
            system.rmdir(root.rstrip("/") + "/" + name)
    system.rmdir(folder)


def show_of(image):
    """The files of `/odrig` in an image: the content of each by its name."""
    system = mount(image)
    if not has_folder(system, FOLDER):
        return {}
    return {path[len(FOLDER) + 1:]: content for path, content in files_in(system, FOLDER).items()}


def other_files(image):
    """Every file of an image outside `/odrig`."""
    return {path: content for path, content in files_in(mount(image)).items() if not path.startswith(FOLDER + "/")}


def with_show(image, files):
    """The image with `/odrig` holding exactly the files given, and everything else as it
    was. The result is checked before it is returned. An image that holds exactly these
    files already is returned as it is."""
    system = mount(image)
    if show_of(image) == dict(files):
        return image
    try:
        remove_tree(system, FOLDER)
        system.mkdir(FOLDER)
        for name in sorted(files):
            with system.open(f"{FOLDER}/{name}", "wb") as file:
                file.write(files[name])
        system.unmount()
    except LittleFSError as error:
        if error.code == NO_SPACE:
            raise Failure("no-space", f"the {len(files)} files, {sum(map(len, files.values()))} bytes, do not fit into storage") from None
        raise Failure("verify-failed", f"the file system refused the files: {error}") from None
    made = bytes(system.context.buffer)
    if geometry(made) != geometry(image):
        raise Failure("verify-failed", "the file system changed its version or its size")
    difference = differing(show_of(made), dict(files))
    if difference:
        raise Failure("verify-failed", f"{FOLDER} in the new image does not hold exactly the files given: {difference}")
    difference = differing(other_files(made), other_files(image))
    if difference:
        raise Failure("verify-failed", f"a file outside {FOLDER} changed in the new image: {difference}")
    return made


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


def runs(old, new, block_size):
    """The stretches in which two images differ, as `(offset, bytes of the new image)`:
    whole blocks, neighbouring changed blocks joined."""
    found, start = [], None
    for offset in range(0, len(new) + block_size, block_size):
        differs = offset < len(new) and old[offset:offset + block_size] != new[offset:offset + block_size]
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
        try:
            canvas = mapping.read(folder / MAPPING_NAME)
            named = show.files(show.read(folder / SHOW_NAME))
            for name in named:
                if name not in files:
                    raise show_errors.Rejection(show_errors.FILE_MISSING, f"{folder / name}: the show names it and it is not there")
                try:
                    animation = odrg.decode(files[name])
                except show_errors.Rejection as rejection:
                    raise show_errors.Rejection(show_errors.FILE_MALFORMED, f"{folder / name}: {rejection.reason}: {rejection.detail}") from None
                if (animation.width, animation.height) != (canvas.width, canvas.height):
                    raise show_errors.Rejection(show_errors.SIZE_MISMATCH, f"{folder / name}: the canvas is {animation.width} x {animation.height} and the mapping's is {canvas.width} x {canvas.height}")
        except show_errors.Rejection as rejection:
            raise _rejected(rejection) from None
        for name in files:
            if name not in (MAPPING_NAME, SHOW_NAME, *named):
                raise Failure("not-a-show-folder", f"{folder / name} is not a file of the show")
    return files


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

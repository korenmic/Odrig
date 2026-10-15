"""Reads the partition table of an ESP32, checks that it is a layout the tool writes to, and
makes the tables of the two layouts it knows."""

import collections
import hashlib
import struct

from . import Failure

TABLE_ADDRESS = 0x8000
TABLE_SIZE = 0xC00
ENTRY_SIZE = 32
ENTRY_MAGIC = b"\xaa\x50"
CHECKSUM_MAGIC = b"\xeb\xeb"
TYPE_APPLICATION = 0
TYPE_DATA = 1
APPLICATION_ADDRESS = 0x10000
STORAGE_NAME = "spiffs"

Partition = collections.namedtuple("Partition", "name type subtype offset size")

# The two layouts. WLED's is that of its 16 MB build, with two firmware slots, the second
# for updates over Wi-Fi. The bigger one gives the second slot's room to the storage, and
# its one firmware slot is a factory slot: an update over Wi-Fi finds no slot to write.
WLED = (
    Partition("nvs", TYPE_DATA, 0x02, 0x9000, 0x5000),
    Partition("otadata", TYPE_DATA, 0x00, 0xE000, 0x2000),
    Partition("app0", TYPE_APPLICATION, 0x10, APPLICATION_ADDRESS, 0x300000),
    Partition("app1", TYPE_APPLICATION, 0x11, 0x310000, 0x300000),
    Partition(STORAGE_NAME, TYPE_DATA, 0x82, 0x610000, 0x9E0000),
    Partition("coredump", TYPE_DATA, 0x03, 0xFF0000, 0x10000),
)
BIGGER = (
    Partition("nvs", TYPE_DATA, 0x02, 0x9000, 0x5000),
    Partition("otadata", TYPE_DATA, 0x00, 0xE000, 0x2000),
    Partition("app0", TYPE_APPLICATION, 0x00, APPLICATION_ADDRESS, 0x300000),
    Partition(STORAGE_NAME, TYPE_DATA, 0x82, 0x310000, 0xCE0000),
    Partition("coredump", TYPE_DATA, 0x03, 0xFF0000, 0x10000),
)
WLEDS = "WLED's"
BIGGER_NAME = "bigger"


def table(entries):
    """The bytes of a partition table as it lies in the flash: the entries, the entry of
    their checksum, and the rest of its room filled with 0xFF."""
    made = b""
    for entry in entries:
        made += ENTRY_MAGIC + struct.pack("<BBII", entry.type, entry.subtype, entry.offset, entry.size)
        made += entry.name.encode("ascii").ljust(16, b"\0") + struct.pack("<I", 0)
    made += CHECKSUM_MAGIC + b"\xff" * 14 + hashlib.md5(made).digest()
    return made.ljust(TABLE_SIZE, b"\xff")


def parse(table):
    """The partitions of a table as it is read from the flash."""
    found = []
    for start in range(0, len(table) - ENTRY_SIZE + 1, ENTRY_SIZE):
        entry = table[start:start + ENTRY_SIZE]
        if entry == b"\xff" * ENTRY_SIZE:
            break
        if entry[:2] == CHECKSUM_MAGIC:
            if entry[16:] != hashlib.md5(table[:start]).digest():
                raise Failure("layout-mismatch", "the partition table does not match its own checksum")
            break
        if entry[:2] != ENTRY_MAGIC:
            raise Failure("layout-mismatch", f"entry {start // ENTRY_SIZE} of the partition table begins with {entry[:2].hex()}, not with aa50")
        kind, subtype, offset, size = struct.unpack("<BBII", entry[2:12])
        name = entry[12:28].split(b"\0", 1)[0].decode("ascii", "replace")
        found.append(Partition(name, kind, subtype, offset, size))
    if not found:
        raise Failure("layout-mismatch", "the partition table is empty")
    return found


def application(found, image_size):
    """The application partition at the address the tool writes, which the image must fit in."""
    for partition in found:
        if partition.type == TYPE_APPLICATION and partition.offset == APPLICATION_ADDRESS:
            if image_size > partition.size:
                raise Failure("layout-mismatch", f"the image has {image_size} bytes and the partition {partition.name} only {partition.size}")
            return partition
    raise Failure("layout-mismatch", f"there is no application partition at {APPLICATION_ADDRESS:#x}")


def storage(found):
    """The data partition that holds the file system."""
    for partition in found:
        if partition.type == TYPE_DATA and partition.name == STORAGE_NAME:
            return partition
    raise Failure("layout-mismatch", f"there is no data partition named {STORAGE_NAME}")


def check(table, image_size):
    """Parses a table and returns its application partition and its storage partition."""
    found = parse(table)
    return application(found, image_size), storage(found)


def layout_of(found):
    """The name of the layout of a parsed table, by its firmware slots: WLED's with a second
    one, the bigger one with one alone."""
    slots = [partition for partition in found if partition.type == TYPE_APPLICATION]
    return WLEDS if len(slots) > 1 else BIGGER_NAME


def layout_line(table):
    """The line in which a command says which layout it found on the board."""
    found = parse(table)
    return f"layout: {layout_of(found)}, storage {storage(found).size} bytes"

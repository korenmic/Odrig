"""Reads the partition table of an ESP32 and checks that it is the layout the tool writes to."""

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

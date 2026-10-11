"""The stock WLED files: where they are and the checksums they must have."""

import collections
import hashlib
import pathlib

from . import Failure, paths

LIST = paths.FIRMWARE / "stock.sha256"
FOLDER = paths.FIRMWARE / "wled-16.0.1"

APPLICATION = "WLED_16.0.1_ESP32-S3_16MB_opi.bin"
BOOTLOADER = "bootloader_s3.bin"
TABLE = "partitions_s3_16m.bin"

Checked = collections.namedtuple("Checked", "application bootloader table")


def checksums(listing=None):
    """The tracked list: the SHA-256 of each stock file by its name."""
    found = {}
    for line in pathlib.Path(listing or LIST).read_text().splitlines():
        digest, name = line.split()
        found[name] = digest
    return found


def checked(folder=FOLDER, full=False, listing=None):
    """The stock files that are about to be written, each checked against the list."""
    folder = pathlib.Path(folder)
    wanted = checksums(listing)
    names = [APPLICATION, BOOTLOADER, TABLE] if full else [APPLICATION]
    for name in names:
        path = folder / name
        if not path.is_file():
            raise Failure("stock-missing", f"{path} is not there")
        if hashlib.sha256(path.read_bytes()).hexdigest() != wanted[name]:
            raise Failure("checksum-mismatch", f"{path} does not have the SHA-256 of {LIST.name}")
    return Checked(folder / APPLICATION, folder / BOOTLOADER if full else None, folder / TABLE if full else None)

"""Runs esptool on the board: read, write, erase a region, verify.

Every address is checked against the regions the tool may touch before esptool is started.
The whole flash is never erased and no fuse is ever written.
"""

import collections
import subprocess
import tempfile
import pathlib

from . import Failure, env, paths, partitions

Region = collections.namedtuple("Region", "name address size")

BOOTLOADER = Region("bootloader", 0x0, 0x8000)
TABLE = Region("partition table", partitions.TABLE_ADDRESS, 0x1000)
BOOT_SELECTION = Region("boot selection", 0xE000, 0x2000)
APPLICATION = Region("first application", partitions.APPLICATION_ADDRESS, 0x300000)

CHIP = "esp32s3"
# The rate esptool is told. The board's socket marked COM reaches the chip through a
# bridge to its UART, where the rate is what the transfer takes; the chip's own USB
# socket has no rate and ignores it.
BITS_PER_SECOND = 921600
KEEP = ["--flash-mode", "keep", "--flash-freq", "keep", "--flash-size", "keep"]
DETECT_SIZE = ["--flash-mode", "keep", "--flash-freq", "keep", "--flash-size", "detect"]
NO_PROGRAM_CHECK = "--force"


def storage_region(partition):
    return Region("storage", partition.offset, partition.size)


def within(address, size, regions):
    """The region that holds a stretch of the flash whole, or a refusal."""
    for region in regions:
        if region.address <= address and address + size <= region.address + region.size and size > 0:
            return region
    names = ", ".join(region.name for region in regions)
    raise Failure("esptool-failed", f"{size} bytes at {address:#x} are outside what may be touched here: {names}")


def run_esptool(arguments):
    """Starts esptool from the work folder's environment and returns its status and output.

    esptool runs in a session of its own, so that an interrupt from the keyboard reaches
    the tool alone: the tool ends esptool when it gives up, and lets it finish a write that
    must not be cut."""
    done = subprocess.run([str(paths.PYTHON), "-m", "esptool", *arguments], capture_output=True, text=True, env=env.child(), start_new_session=True)
    return done.returncode, done.stdout + done.stderr


class Flasher:
    """esptool on one port. `run` stands in for esptool in tests."""

    def __init__(self, port, run=None):
        self.port = port
        self.run = run

    def _esptool(self, after, *arguments):
        command = ["--chip", CHIP, "--port", str(self.port), "--baud", str(BITS_PER_SECOND), "--after", after, *arguments]
        status, output = (self.run or run_esptool)(command)
        if status != 0:
            raise Failure("esptool-failed", f"esptool {arguments[0]} ended with status {status}: {output.strip()[-400:]}")
        return output

    def read(self, address, size, path, regions):
        """Reads a stretch of the flash into a file. The chip stays in its bootloader."""
        within(address, size, regions)
        path = paths.output(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._esptool("no-reset", "read-flash", f"{address:#x}", f"{size:#x}", str(path))
        return path

    def read_table(self):
        """The partition table of the board."""
        with tempfile.TemporaryDirectory() as folder:
            path = self.read(partitions.TABLE_ADDRESS, partitions.TABLE_SIZE, pathlib.Path(folder, "table.bin"), [TABLE])
            return path.read_bytes()

    def erase(self, region):
        """Erases the boot selection data, the one region that is ever erased."""
        if region != BOOT_SELECTION:
            raise Failure("esptool-failed", f"the region {region.name} is not erased by this tool")
        self._esptool("no-reset", "erase-region", f"{region.address:#x}", f"{region.size:#x}")

    def write(self, files, regions, restart, data=False):
        """Writes files, each at its address, in one esptool call. esptool compares a
        checksum of what it wrote. With `restart` the board is reset afterwards.

        A bootloader is written with the flash size esptool finds on the chip in its
        header, which is how the bootloader on the board was written; every other file
        goes to the flash as it is.

        `data` says that the files are no programs. esptool takes every file that begins
        with the first byte of a program image for one, and refuses it when the rest is
        not a program for this chip; a block of storage can begin with any byte. For data
        esptool is therefore told to leave that check out. A program is always checked.
        """
        arguments = []
        for address, path in files:
            within(address, pathlib.Path(path).stat().st_size, regions)
            arguments += [f"{address:#x}", str(path)]
        if not arguments:
            return
        if data and any(region in (BOOTLOADER, TABLE, APPLICATION) for region in regions):
            raise Failure("esptool-failed", "a program is not written as data")
        settings = DETECT_SIZE if any(address == BOOTLOADER.address for address, _ in files) else KEEP
        unchecked = [NO_PROGRAM_CHECK] if data else []
        self._esptool("hard-reset" if restart else "no-reset", "write-flash", *unchecked, *settings, *arguments)

    def verify(self, address, path, regions, restart):
        """Compares a stretch of the flash with a file, as `write` would have written it."""
        within(address, pathlib.Path(path).stat().st_size, regions)
        settings = DETECT_SIZE if address == BOOTLOADER.address else KEEP
        try:
            self._esptool("hard-reset" if restart else "no-reset", "verify-flash", *settings, f"{address:#x}", str(path))
        except Failure as failure:
            raise Failure("verify-failed", failure.detail) from None

    def compare(self, files, regions, restart):
        """Has the chip compare stretches of the flash with files, each at its address, in
        one esptool call; the chip works out the checksum of each stretch. With `restart`
        the board is reset once every stretch is equal; otherwise, and when one differs,
        the chip stays in its bootloader."""
        arguments = []
        for address, path in files:
            within(address, pathlib.Path(path).stat().st_size, regions)
            arguments += [f"{address:#x}", str(path)]
        if not arguments:
            return
        try:
            self._esptool("hard-reset" if restart else "no-reset", "verify-flash", *KEEP, *arguments)
        except Failure as failure:
            raise Failure("verify-failed", failure.detail) from None

    def restart(self):
        """Resets the board out of its bootloader."""
        self._esptool("hard-reset", "chip-id")

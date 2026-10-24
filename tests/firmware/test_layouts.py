"""The two layouts the firmware tool knows, and the line in which a command names the one it
found on the board."""

import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from fwtool import build, limit, partitions, paths

from . import FIRMWARE, support

STOCK_TABLE = FIRMWARE / "wled-16.0.1" / "partitions_s3_16m.bin"
REPLY = support.VALID


class Tables(unittest.TestCase):
    def test_the_table_of_wleds_layout_is_the_stock_one(self):
        made = partitions.table(partitions.WLED)
        self.assertEqual(made, support.partition_table())
        if STOCK_TABLE.is_file():
            self.assertEqual(made, STOCK_TABLE.read_bytes())

    def test_the_bigger_layout_gives_the_second_slots_room_to_the_storage(self):
        found = partitions.parse(partitions.table(partitions.BIGGER))
        self.assertEqual(found, list(partitions.BIGGER))
        self.assertEqual(partitions.table(partitions.BIGGER), support.partition_table(support.BIGGER_LAYOUT))
        slot, kept = partitions.check(partitions.table(partitions.BIGGER), 3 * 1024 * 1024)
        self.assertEqual((slot.name, slot.subtype, slot.offset, slot.size), ("app0", 0x00, 0x10000, 0x300000))
        self.assertEqual((kept.offset, kept.size), (0x310000, 13500416))
        self.assertEqual(kept.offset + kept.size, 0xFF0000)
        self.assertEqual([entry.name for entry in found if entry.type == partitions.TYPE_APPLICATION], ["app0"])
        wleds = {entry.name: entry for entry in partitions.WLED}
        for entry in found:
            if entry.name in ("nvs", "otadata", "coredump"):
                self.assertEqual(entry, wleds[entry.name])
        self.assertEqual(13500416 - 10354688, 3145728)

    def test_each_table_is_named_by_its_firmware_slots(self):
        for layout, name in ((support.LAYOUT, "WLED's"), (support.small_layout(), "WLED's"), (support.BIGGER_LAYOUT, "bigger"), (support.small_bigger_layout(), "bigger")):
            with self.subTest(layout=name):
                self.assertEqual(partitions.layout_of(partitions.parse(support.partition_table(layout))), name)

    def test_the_line_names_the_layout_and_the_size_of_its_storage(self):
        self.assertEqual(partitions.layout_line(partitions.table(partitions.WLED)), "layout: WLED's, storage 10354688 bytes")
        self.assertEqual(partitions.layout_line(partitions.table(partitions.BIGGER)), "layout: bigger, storage 13500416 bytes")

    def test_a_table_that_is_neither_is_refused(self):
        no_storage = tuple(entry for entry in support.BIGGER_LAYOUT if entry[0] != "spiffs")
        elsewhere = tuple(entry if entry[0] != "app0" else ("app0", 0, 0x00, 0x20000, 0x300000) for entry in support.BIGGER_LAYOUT)
        for layout in (no_storage, elsewhere):
            with self.subTest(layout=layout):
                self.assertEqual(support.reason_of(self, lambda: partitions.check(support.partition_table(layout), 0)), "layout-mismatch")


class OnEachLayout(unittest.TestCase):
    """The commands that read the board's table, on a stand-in board of each layout, with a
    storage of a few blocks."""

    LAYOUTS = (("WLED's", support.small_layout(), 0x610000), ("bigger", support.small_bigger_layout(), 0x310000))

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name)
        patched = mock.patch.object(paths, "STORAGE", self.folder / "storage")
        patched.start()
        self.addCleanup(patched.stop)
        self.old = support.storage_image()
        with support.example_show() as packed:
            shutil.copytree(packed, self.folder / "show")

    def esptool(self, layout, address):
        return support.RecordedEsptool(support.partition_table(layout), {address: self.old})

    def line(self, name):
        return f"layout: {name}, storage {64 * support.BLOCK_SIZE} bytes"

    def run_on(self, layout, address, *arguments):
        esptool = self.esptool(layout, address)
        with support.no_board(esptool, answer=REPLY):
            return support.run_main(*arguments), esptool

    def test_install_show_prints_the_layout_first_and_writes_where_the_table_puts_the_storage(self):
        for name, layout, address in self.LAYOUTS:
            with self.subTest(layout=name):
                result, esptool = self.run_on(layout, address, "install-show", self.folder / "show")
                lines = result.out.splitlines()
                self.assertEqual((result.status, lines[0], lines[-2], lines[-1], result.err), (0, self.line(name), REPLY, "outcome: healthy", ""))
                self.assertTrue(all(address <= at < address + 64 * support.BLOCK_SIZE for at, _ in esptool.wrote))

    def test_read_show_and_read_limit_print_the_layout_first(self):
        for name, layout, address in self.LAYOUTS:
            with self.subTest(layout=name):
                result, _ = self.run_on(layout, address, "read-show", self.folder / f"read-{name[0]}")
                self.assertEqual(result.status, 0, result.err)
                self.assertEqual(result.out.splitlines()[0], self.line(name))
                result, _ = self.run_on(layout, address, "read-limit")
                self.assertEqual(result.out, f"{self.line(name)}\n{limit.NOT_STORED}\n")

    def test_set_limit_prints_the_layout_first(self):
        settings = self.folder / "limit.json"
        settings.write_text('{"milliamps": 850}')
        for name, layout, address in self.LAYOUTS:
            with self.subTest(layout=name):
                result, _ = self.run_on(layout, address, "set-limit", "--settings", settings)
                self.assertEqual((result.status, result.out), (0, f"{self.line(name)}\nlimit: 850 mA\n{REPLY}\n"))

    def test_flash_prints_the_layout_first_and_writes_the_first_slot_on_either(self):
        image = self.folder / "odrig-firmware.bin"
        image.write_bytes((support.PROGRAM + bytes(range(256)) * 16)[:4096])
        build.write_checksum(image)
        for name, layout, address in self.LAYOUTS:
            with self.subTest(layout=name):
                result, esptool = self.run_on(layout, address, "flash", "--image", image)
                self.assertEqual((result.status, result.out), (0, f"{self.line(name)}\n{REPLY}\n"))
                self.assertEqual(esptool.written(), [("0x10000", "odrig-firmware.bin")])


if __name__ == "__main__":
    unittest.main()

"""The move of a board to the bigger layout, `big-storage`, and the way back,
`restore-stock --full`, on a stand-in for esptool."""

import hashlib
import pathlib
import tempfile
import unittest
from unittest import mock

from fwtool import partitions, paths, stock, storage

from . import support

WLED_STORAGE = (0x610000, 0x9E0000)
BIGGER_STORAGE = (0x310000, 0xCE0000)
ROOM = 0x300000
STOCK_NAMES = ["WLED_16.0.1_ESP32-S3_16MB_opi.bin", "bootloader_s3.bin", "partitions_s3_16m.bin"]


def full_image(files, size):
    return support.storage_image(files, blocks=size // support.BLOCK_SIZE)


class FailingWrite(support.RecordedEsptool):
    """A stand-in whose first write of the flash fails."""

    def __call__(self, arguments):
        if "write-flash" in arguments and not any("write-flash" in call for call in self.calls):
            self.calls.append(list(arguments))
            return 2, "A fatal error occurred: the port went away"
        return super().__call__(arguments)


class Moving(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = full_image(support.SAVED_FILES, WLED_STORAGE[1])

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name)
        patched = mock.patch.object(paths, "STORAGE", self.folder / "storage")
        patched.start()
        self.addCleanup(patched.stop)

    def move(self, table, flash, esptool_kind=support.RecordedEsptool):
        esptool = esptool_kind(table, flash)
        with support.no_board(esptool, answer=support.VALID):
            return support.run_main("big-storage"), esptool

    def test_a_board_of_wleds_layout_gets_the_bigger_one_with_its_settings_and_no_show(self):
        result, esptool = self.move(support.partition_table(), {WLED_STORAGE[0]: self.old})
        self.assertEqual(result.status, 0, result.err)
        lines = result.out.splitlines()
        self.assertEqual(lines[0], "layout: WLED's, storage 10354688 bytes")
        self.assertRegex(lines[1], r"^kept: .+-before\.bin$")
        self.assertEqual(pathlib.Path(lines[1][len("kept: "):]).read_bytes(), self.old)
        self.assertEqual(lines[2:], [support.VALID])
        self.assertEqual(esptool.commands(), ["read-flash", "read-flash", "write-flash", "verify-flash", "erase-region", "write-flash", "verify-flash"])
        (head_at, head), (table_at, table) = esptool.wrote
        self.assertEqual((head_at, len(head)), (BIGGER_STORAGE[0], ROOM))
        self.assertEqual((table_at, table), (0x8000, partitions.table(partitions.BIGGER)))
        # The board's new storage: the head, and beyond it what was WLED's storage.
        now = (head + self.old)[:BIGGER_STORAGE[1]]
        self.assertEqual(storage.geometry(now)[1:], (4096, 3296))
        self.assertEqual(storage.other_files(now), storage.other_files(self.old))
        self.assertEqual(storage.show_of(now), {})
        self.assertIn("/wsec.json", storage.other_files(now))

    def test_a_show_installs_into_the_moved_storage_and_reads_back(self):
        _, esptool = self.move(support.partition_table(), {WLED_STORAGE[0]: self.old})
        now = (dict(esptool.wrote)[BIGGER_STORAGE[0]] + self.old)[:BIGGER_STORAGE[1]]
        files = {"mapping.json": b"a mapping", "show.json": b"a show", "big.odrg": bytes(range(256)) * 12000}
        installed = storage.with_show(now, files)
        self.assertEqual(storage.show_of(installed), files)
        self.assertEqual(storage.other_files(installed), storage.other_files(self.old))
        self.assertEqual(storage.geometry(installed), storage.geometry(now))

    def test_the_head_is_written_and_checked_before_the_table_and_the_board_restarts_last(self):
        _, esptool = self.move(support.partition_table(), {WLED_STORAGE[0]: self.old})
        writes = [call for call in esptool.calls if "write-flash" in call or "verify-flash" in call or "erase-region" in call]
        self.assertEqual([call[call.index("--after") + 1] for call in writes], ["no-reset", "no-reset", "no-reset", "no-reset", "hard-reset"])
        self.assertIn("--force", writes[0], "the storage is written as data")
        self.assertNotIn("--force", writes[3])
        self.assertEqual(esptool.call("erase-region"), ["0xe000", "0x2000"])

    def test_a_board_of_the_bigger_layout_is_left_as_it_is(self):
        result, esptool = self.move(partitions.table(partitions.BIGGER), {})
        self.assertEqual((result.status, result.out), (0, "layout: bigger, storage 13500416 bytes\nnothing to do: the board has the bigger layout\n"))
        self.assertEqual(esptool.commands(), ["read-flash", "chip-id"])

    def test_a_table_that_is_not_wleds_own_is_refused_before_anything_is_written(self):
        result, esptool = self.move(support.partition_table(support.small_layout()), {})
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: layout-mismatch: the board's partition table is not WLED's own")
        self.assertEqual(esptool.commands(), ["read-flash", "chip-id"])

    def test_a_failure_while_the_head_is_written_leaves_the_table_as_it_was(self):
        result, esptool = self.move(support.partition_table(), {WLED_STORAGE[0]: self.old}, FailingWrite)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: esptool-failed: ")
        self.assertNotIn("erase-region", esptool.commands())
        self.assertEqual(sum("write-flash" in call for call in esptool.calls), 1)
        self.assertEqual(esptool.commands()[-1], "chip-id")

    def test_its_options_are_the_port_and_the_wait(self):
        made = support.cli.parser()
        self.assertEqual(made.parse_args(["big-storage"]).wait, 20.0)
        self.assertEqual(made.parse_args(["big-storage", "--port", "/dev/x", "--wait", "5"]).port, "/dev/x")
        self.assertEqual(support.run_main("big-storage", "--sideways").status, 2)


class WayBack(Moving):
    def stock_folder(self):
        folder = self.folder / "stock"
        folder.mkdir()
        contents = {STOCK_NAMES[0]: b"\x01" * 4096, STOCK_NAMES[1]: b"\x02" * 4096, STOCK_NAMES[2]: support.partition_table()}
        lines = []
        for name, content in contents.items():
            (folder / name).write_bytes(content)
            lines.append(f"{hashlib.sha256(content).hexdigest()}  {name}\n")
        (self.folder / "stock.sha256").write_text("".join(lines))
        return folder

    def restore(self, table, flash):
        folder = self.stock_folder()
        esptool = support.RecordedEsptool(table, flash)
        with mock.patch.object(stock, "LIST", self.folder / "stock.sha256"), support.no_board(esptool):
            return support.run_main("restore-stock", "--full", "--stock-dir", folder), esptool

    def test_on_the_bigger_layout_it_also_writes_wleds_storage_with_the_settings(self):
        bigger = storage.with_settings(self.old, BIGGER_STORAGE[1], room=ROOM)
        with_a_show = storage.with_show(bigger, {"mapping.json": b"a mapping", "show.json": b"a show"})
        result, esptool = self.restore(partitions.table(partitions.BIGGER), {BIGGER_STORAGE[0]: with_a_show})
        self.assertEqual(result.status, 0, result.err)
        lines = result.out.splitlines()
        self.assertEqual(lines[0], "layout: bigger, storage 13500416 bytes")
        self.assertRegex(lines[1], r"^kept: ")
        self.assertEqual(esptool.written(), [("0x0", STOCK_NAMES[1]), ("0x8000", STOCK_NAMES[2]), ("0x610000", esptool.written()[2][1]), ("0x10000", STOCK_NAMES[0])])
        written = dict(esptool.wrote)[WLED_STORAGE[0]]
        self.assertEqual(len(written), WLED_STORAGE[1])
        self.assertEqual(storage.geometry(written)[1:], (4096, 2528))
        self.assertEqual(storage.other_files(written), storage.other_files(self.old))
        self.assertEqual(storage.show_of(written), {})

    def test_on_wleds_layout_it_writes_no_storage(self):
        result, esptool = self.restore(support.partition_table(), {WLED_STORAGE[0]: self.old})
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual([address for address, _ in esptool.wrote], [0x0, 0x8000, 0x10000])
        self.assertNotIn("kept:", result.out)


if __name__ == "__main__":
    unittest.main()

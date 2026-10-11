import hashlib
import pathlib
import re
import shutil
import tempfile
import unittest

from fwtool import stock

from . import support

NAMES = ["WLED_16.0.1_ESP32-S3_16MB_opi.bin", "bootloader_s3.bin", "partitions_s3_16m.bin"]


class TheList(unittest.TestCase):
    def test_it_has_three_lines_of_a_checksum_and_a_name(self):
        lines = stock.LIST.read_text().splitlines()
        self.assertEqual(len(lines), 3)
        for line, name in zip(lines, NAMES):
            self.assertRegex(line, rf"^[0-9a-f]{{64}}  {re.escape(name)}$")

    def test_the_application_has_the_checksum_of_the_release_of_wled_16_0_1(self):
        self.assertEqual(stock.checksums()[stock.APPLICATION], "bd31bba8e4cb16c387bcf5dfd78be11924a3dcda54fd1207fcc648eb97306e9b")

    def test_the_stock_files_are_not_tracked(self):
        self.assertEqual(stock.FOLDER, support.ROOT / "firmware" / "wled-16.0.1")
        self.assertEqual(support.git(support.ROOT, "ls-files", "firmware/wled-16.0.1"), "")


class Checked(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name)
        self.listing = self.folder / "list.sha256"
        self.files = self.folder / "stock"
        self.files.mkdir()
        lines = []
        for number, name in enumerate(NAMES):
            content = bytes([number]) * 100
            (self.files / name).write_bytes(content)
            lines.append(f"{hashlib.sha256(content).hexdigest()}  {name}\n")
        self.listing.write_text("".join(lines))

    def checked(self, full):
        return stock.checked(self.files, full, self.listing)

    def test_the_application_alone_is_checked_without_full(self):
        (self.files / "bootloader_s3.bin").write_bytes(b"changed")
        (self.files / "partitions_s3_16m.bin").unlink()
        found = self.checked(full=False)
        self.assertEqual(found.application, self.files / NAMES[0])
        self.assertIsNone(found.bootloader)
        self.assertIsNone(found.table)

    def test_all_three_are_checked_with_full(self):
        found = self.checked(full=True)
        self.assertEqual([found.application, found.bootloader, found.table], [self.files / name for name in NAMES])

    def test_a_changed_file_is_a_checksum_mismatch(self):
        for name, full in ((NAMES[0], False), (NAMES[1], True), (NAMES[2], True)):
            kept = (self.files / name).read_bytes()
            (self.files / name).write_bytes(kept[:-1] + b"\xff")
            self.assertEqual(support.reason_of(self, lambda: self.checked(full)), "checksum-mismatch", name)
            (self.files / name).write_bytes(kept)

    def test_a_missing_file_is_stock_missing(self):
        for name, full in ((NAMES[0], False), (NAMES[1], True), (NAMES[2], True)):
            shutil.move(self.files / name, self.folder / "aside")
            self.assertEqual(support.reason_of(self, lambda: self.checked(full)), "stock-missing", name)
            shutil.move(self.folder / "aside", self.files / name)

    def test_a_missing_folder_is_stock_missing(self):
        self.assertEqual(support.reason_of(self, lambda: stock.checked(self.folder / "nowhere", False, self.listing)), "stock-missing")


class RestoreChecksFirst(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.copy = pathlib.Path(holder.name)
        for name in NAMES:
            (self.copy / name).write_bytes(b"not the stock file " + name.encode())

    def test_a_changed_stock_file_stops_the_restore_before_any_esptool_call(self):
        for extra in ([], ["--full"]):
            with support.untouched_board():
                result = support.run_main("restore-stock", "--stock-dir", self.copy, *extra)
            self.assertEqual(result.status, 1)
            self.assertRegex(result.err, r"^error: checksum-mismatch: .*\n$")

    def test_a_missing_stock_file_stops_the_restore_before_any_esptool_call(self):
        (self.copy / NAMES[0]).unlink()
        with support.untouched_board():
            result = support.run_main("restore-stock", "--stock-dir", self.copy)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: stock-missing: .*\n$")

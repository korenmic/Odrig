import ast
import hashlib
import pathlib
import tempfile
import unittest
from unittest import mock

from fwtool import build, flasher, stock

from . import FIRMWARE, support

STOCK_NAMES = ["WLED_16.0.1_ESP32-S3_16MB_opi.bin", "bootloader_s3.bin", "partitions_s3_16m.bin"]
FORBIDDEN_WORDS = ("erase-flash", "erase_flash", "--erase-all", "-e", "espefuse", "burn-efuse", "write-protect-efuse")


class Temporary(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name)

    def image(self, name="odrig-firmware.bin", size=4096):
        path = self.folder / name
        path.write_bytes(bytes(range(256)) * (size // 256))
        build.write_checksum(path)
        return path

    def stock_folder(self):
        """A folder of stand-ins for the stock files and the list that fits them."""
        folder = self.folder / "stock"
        folder.mkdir()
        contents = {STOCK_NAMES[0]: b"\x01" * 4096, STOCK_NAMES[1]: b"\x02" * 4096, STOCK_NAMES[2]: support.partition_table()}
        lines = []
        for name, content in contents.items():
            (folder / name).write_bytes(content)
            lines.append(f"{hashlib.sha256(content).hexdigest()}  {name}\n")
        (self.folder / "stock.sha256").write_text("".join(lines))
        return folder


class Flash(Temporary):
    def test_it_reads_the_table_erases_the_boot_selection_and_writes_the_image_at_0x10000(self):
        image = self.image()
        with support.no_board() as esptool:
            result = support.run_main("flash", "--image", image, "--port", "/dev/cu.given", "--expect", "wled")
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(esptool.commands(), ["read-flash", "erase-region", "write-flash"])
        self.assertEqual(esptool.call("read-flash")[:2], ["0x8000", "0xc00"])
        self.assertEqual(esptool.call("erase-region"), ["0xe000", "0x2000"])
        self.assertEqual(esptool.written(), [("0x10000", "odrig-firmware.bin")])
        self.assertEqual(result.out, "WLED 2606300\n")

    def test_every_call_names_the_chip_and_the_port(self):
        with support.no_board() as esptool:
            support.run_main("flash", "--image", self.image(), "--port", "/dev/cu.given")
        for call in esptool.calls:
            self.assertEqual(call[:4], ["--chip", "esp32s3", "--port", "/dev/cu.given"])

    def test_the_image_is_written_as_it_is_and_the_board_restarted_after_it(self):
        with support.no_board() as esptool:
            support.run_main("flash", "--image", self.image())
        write = next(call for call in esptool.calls if "write-flash" in call)
        self.assertEqual(write[write.index("--after") + 1], "hard-reset")
        for setting in ("--flash-mode", "--flash-freq", "--flash-size"):
            self.assertEqual(write[write.index(setting) + 1], "keep")
        for call in esptool.calls[:-1]:
            self.assertEqual(call[call.index("--after") + 1], "no-reset")

    def test_without_an_image_given_it_is_the_built_firmware(self):
        with support.no_board(), mock.patch.object(build, "checked_image", side_effect=lambda image: self.image()) as checked:
            support.run_main("flash")
        checked.assert_called_once_with(build.image_path("firmware"))
        self.assertEqual(build.image_path("firmware"), support.ROOT / "build" / "firmware" / "out" / "odrig-firmware.bin")

    def test_a_board_with_another_layout_is_refused_before_anything_is_written(self):
        layouts = {
            "no spiffs": [entry for entry in support.LAYOUT if entry[0] != "spiffs"],
            "app0 elsewhere": [entry if entry[0] != "app0" else ("app0", 0, 0x10, 0x20000, 0x2F0000) for entry in support.LAYOUT],
        }
        for what, layout in layouts.items():
            with support.no_board(support.RecordedEsptool(support.partition_table(layout))) as esptool:
                result = support.run_main("flash", "--image", self.image())
            self.assertEqual(result.status, 1, what)
            self.assertRegex(result.err, r"^error: layout-mismatch: ", what)
            self.assertEqual(esptool.commands(), ["read-flash"], what)

    def test_a_failing_esptool_is_esptool_failed(self):
        def failing(arguments):
            return 2, "A fatal error occurred: could not open the port"
        with support.no_board(failing):
            result = support.run_main("flash", "--image", self.image())
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: esptool-failed: .*could not open the port\n$")


class RestoreStock(Temporary):
    def restore(self, *extra):
        folder = self.stock_folder()
        with mock.patch.object(stock, "LIST", self.folder / "stock.sha256"), support.no_board() as esptool:
            result = support.run_main("restore-stock", "--stock-dir", folder, *extra)
        self.assertEqual(result.status, 0, result.err)
        return esptool

    def test_it_erases_the_boot_selection_and_writes_the_application_at_0x10000(self):
        esptool = self.restore()
        self.assertEqual(esptool.commands(), ["read-flash", "erase-region", "write-flash"])
        self.assertEqual(esptool.call("erase-region"), ["0xe000", "0x2000"])
        self.assertEqual(esptool.written(), [("0x10000", STOCK_NAMES[0])])

    def test_with_full_it_also_writes_the_bootloader_at_0x0_and_the_table_at_0x8000_in_the_same_call(self):
        esptool = self.restore("--full")
        self.assertEqual(esptool.commands(), ["erase-region", "write-flash"])
        self.assertEqual(esptool.written(), [("0x0", STOCK_NAMES[1]), ("0x8000", STOCK_NAMES[2]), ("0x10000", STOCK_NAMES[0])])

    def test_with_full_the_bootloader_gets_the_flash_size_of_the_chip(self):
        write = self.restore("--full").call("write-flash")
        self.assertEqual(write[write.index("--flash-size") + 1], "detect")
        self.assertEqual(write[write.index("--flash-mode") + 1], "keep")
        self.assertEqual(write[write.index("--flash-freq") + 1], "keep")

    def test_the_stock_files_are_those_beside_the_repository_unless_told_otherwise(self):
        self.assertEqual(stock.FOLDER, support.ROOT / "firmware" / "wled-16.0.1")
        self.assertEqual(support.cli.parser().parse_args(["restore-stock"]).stock_dir, stock.FOLDER)


class InstallShow(Temporary):
    def install(self):
        with support.example_show() as show:
            esptool = support.RecordedEsptool(support.partition_table(support.small_layout()), {0x610000: support.storage_image()})
            with mock.patch.object(flasher.paths, "STORAGE", self.folder / "storage"), support.no_board(esptool, answer='{"ok":true,"error":null}'):
                result = support.run_main("install-show", show)
        self.assertEqual(result.status, 0, result.err)
        return esptool

    def test_it_writes_only_inside_the_storage_partition(self):
        esptool = self.install()
        start, end = 0x610000, 0x610000 + 64 * 4096
        self.assertGreater(len(esptool.wrote), 0)
        for address, content in esptool.wrote:
            self.assertTrue(start <= address and address + len(content) <= end, hex(address))

    def test_it_writes_all_its_stretches_in_one_call_and_erases_nothing(self):
        esptool = self.install()
        self.assertEqual(esptool.commands().count("write-flash"), 1)
        self.assertNotIn("erase-region", esptool.commands())
        write = next(call for call in esptool.calls if "write-flash" in call)
        for setting in ("--flash-mode", "--flash-freq", "--flash-size"):
            self.assertEqual(write[write.index(setting) + 1], "keep")

    def test_it_reads_only_the_partition_table_and_storage(self):
        reads = [call[call.index("read-flash") + 1:][:2] for call in self.install().calls if "read-flash" in call]
        self.assertEqual(reads, [["0x8000", "0xc00"], ["0x610000", "0x40000"]])

    def test_no_word_of_any_call_erases_the_flash_or_names_a_fuse_program(self):
        words = self.install().words()
        for word in FORBIDDEN_WORDS:
            self.assertNotIn(word, words)

    def test_a_write_beside_the_storage_partition_is_refused(self):
        region = flasher.Region("storage", 0x610000, 64 * 4096)
        esptool = support.RecordedEsptool()
        on_port = flasher.Flasher("/dev/cu.test", esptool)
        piece = self.image(size=8192)
        for address in (0x610000 - 4096, 0x610000 + 63 * 4096, 0x10000, 0xFF0000):
            action = lambda: on_port.write([(address, piece)], [region], restart=False)
            self.assertEqual(support.reason_of(self, action), "esptool-failed", hex(address))
        self.assertEqual(esptool.calls, [])


class Regions(Temporary):
    def flasher(self):
        esptool = support.RecordedEsptool()
        return flasher.Flasher("/dev/cu.test", esptool), esptool

    def test_the_regions_are_those_of_wleds_16_mb_layout(self):
        self.assertEqual((flasher.BOOTLOADER.address, flasher.TABLE.address), (0x0, 0x8000))
        self.assertEqual((flasher.BOOT_SELECTION.address, flasher.BOOT_SELECTION.size), (0xE000, 0x2000))
        self.assertEqual((flasher.APPLICATION.address, flasher.APPLICATION.size), (0x10000, 0x300000))

    def test_a_write_outside_the_regions_it_may_touch_is_refused(self):
        on_port, esptool = self.flasher()
        image = self.image(size=8192)
        application_only = [flasher.APPLICATION]
        for address in (0x0, 0x8000, 0x9000, 0xE000, 0xF000, 0x310000 - 4096, 0x310000, 0x610000, 0xFF0000):
            action = lambda: on_port.write([(address, image)], application_only, restart=True)
            self.assertEqual(support.reason_of(self, action), "esptool-failed", hex(address))
        self.assertEqual(esptool.calls, [])

    def test_a_write_of_several_files_is_refused_as_a_whole_when_one_is_outside(self):
        on_port, esptool = self.flasher()
        image = self.image()
        action = lambda: on_port.write([(0x10000, image), (0x9000, image)], [flasher.APPLICATION], restart=True)
        self.assertEqual(support.reason_of(self, action), "esptool-failed")
        self.assertEqual(esptool.calls, [])

    def test_only_the_boot_selection_is_ever_erased(self):
        on_port, esptool = self.flasher()
        for region in (flasher.BOOTLOADER, flasher.TABLE, flasher.APPLICATION, flasher.Region("storage", 0x610000, 0x9E0000), flasher.Region("all", 0, 0x1000000)):
            self.assertEqual(support.reason_of(self, lambda: on_port.erase(region)), "esptool-failed", region.name)
        self.assertEqual(esptool.calls, [])

    def test_a_read_outside_the_regions_it_may_touch_is_refused(self):
        on_port, esptool = self.flasher()
        action = lambda: on_port.read(0x9000, 0x5000, self.folder / "nvs.bin", [flasher.TABLE])
        self.assertEqual(support.reason_of(self, action), "esptool-failed")
        self.assertEqual(esptool.calls, [])

    def test_a_read_into_the_factory_backup_is_refused(self):
        on_port, esptool = self.flasher()
        action = lambda: on_port.read(0x8000, 0xC00, flasher.paths.PROTECTED / "table.bin", [flasher.TABLE])
        self.assertEqual(support.reason_of(self, action), "backup-protected")
        self.assertEqual(esptool.calls, [])

    def test_a_failed_comparison_is_verify_failed(self):
        on_port = flasher.Flasher("/dev/cu.test", lambda arguments: (2, "Verification failed"))
        action = lambda: on_port.verify(0x10000, self.image(), [flasher.APPLICATION], restart=False)
        self.assertEqual(support.reason_of(self, action), "verify-failed")


class NeverTheWholeFlashAndNoFuse(Temporary):
    def test_no_call_of_any_command_erases_the_flash_or_names_a_fuse_program(self):
        folder = self.stock_folder()
        words = []
        for arguments in (["flash", "--image", self.image()], ["restore-stock", "--stock-dir", folder], ["restore-stock", "--stock-dir", folder, "--full"]):
            with mock.patch.object(stock, "LIST", self.folder / "stock.sha256"), support.no_board() as esptool:
                self.assertEqual(support.run_main(*arguments).status, 0)
            words += esptool.words()
        self.assertIn("write-flash", words)
        for word in FORBIDDEN_WORDS:
            self.assertNotIn(word, words)

    def test_no_source_of_the_tool_names_them(self):
        sources = sorted((FIRMWARE / "fwtool").glob("*.py")) + [FIRMWARE / "fw.py"]
        self.assertGreater(len(sources), 8)
        for path in sources:
            texts = [node.value for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
            for text in texts:
                self.assertNotRegex(text, r"erase[-_]flash|erase[-_]all|\befuse|espefuse", path.name)

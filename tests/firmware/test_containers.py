"""A show folder that names ODRGX containers, of text, of a widget and of frames, beside an
ODRG file: checked as the board checks them, and installed."""

import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from fwtool import Failure, paths, storage
from odrig import catalog, odrgx
from tests.converter.test_catalog_format import animation

from . import ROOT, support

VECTORS = ROOT / "tests" / "vectors"
TEXT = VECTORS / "texts" / "valid" / "hebrew.marquee.odrgx"
WIDGET = VECTORS / "widgets" / "valid" / "analog.odrgx"
NAMES = ["sun.odrg", "hebrew.marquee.odrgx", "analog.odrgx", "film.odrgx"]


def film():
    """A container of frames for the canvas of 60 x 60: three frames of 40, 60 and 100 ms."""
    return odrgx.wrap(1, 60, 60, 200, animation(8))


class Containers(unittest.TestCase):
    def setUp(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        self.work = pathlib.Path(made.name)
        self.show = self.work / "show"
        self.show.mkdir()
        shutil.copyfile(ROOT / "mapping" / "legs-20.json", self.show / "mapping.json")
        (self.show / "sun.odrg").write_bytes(animation(1))
        shutil.copyfile(TEXT, self.show / "hebrew.marquee.odrgx")
        shutil.copyfile(WIDGET, self.show / "analog.odrgx")
        (self.show / "film.odrgx").write_bytes(film())
        items = [{"id": number, "file": name} for number, name in enumerate(NAMES, start=1)]
        (self.show / "show.json").write_text(json.dumps({"version": 1, "brightness": 40, "items": items}))

    def refusal(self):
        with self.assertRaises(Failure) as caught:
            storage.folder_files(self.show)
        return caught.exception

    def test_a_checked_folder_takes_containers_of_text_of_a_widget_and_of_frames(self):
        files = storage.folder_files(self.show)
        self.assertEqual({name: data for name, data in files.items() if name not in storage.CATALOG_NAMES}, support.files_of(self.show))

    def test_the_catalog_records_the_type_and_the_loop_of_each(self):
        made = catalog.read(catalog.MemoryStorage(storage.folder_files(self.show)))
        self.assertEqual(made.state, "ok")
        self.assertEqual(sorted((entry.name, entry.type, entry.total_ms) for entry in made.entries), [
            ("analog.odrgx", "widget", 30000), ("film.odrgx", "frames", 200), ("hebrew.marquee.odrgx", "text", 3967), ("sun.odrg", "frames", 200),
        ])

    def test_install_show_puts_them_on_the_board(self):
        table = support.partition_table(support.small_layout())
        image = support.storage_image()
        esptool = support.RecordedEsptool(table, {0x610000: image})
        with mock.patch.object(paths, "STORAGE", self.work / "storage"), support.no_board(esptool, answer=support.VALID):
            result = support.run_main("install-show", self.show)
        self.assertEqual(result.status, 0, result.err)
        board = bytearray(image)
        for address, content in esptool.wrote:
            board[address - 0x610000:address - 0x610000 + len(content)] = content
        self.assertEqual(storage.show_of(bytes(board)), storage.folder_files(self.show))

    def test_a_broken_container_is_refused_with_the_reason_the_library_gives(self):
        cases = {
            VECTORS / "containers" / "invalid" / "truncated.header.odrgx": "truncated",
            VECTORS / "containers" / "invalid" / "unknown-type.odrgx": "unknown-type",
            VECTORS / "texts" / "invalid" / "trailing-bytes.odrgx": "payload-size",
            VECTORS / "widgets" / "invalid" / "payload-size.short.odrgx": "payload-size",
            VECTORS / "widgets" / "invalid" / "payload-size.header.odrgx": "payload-size",
        }
        for vector, reason in cases.items():
            with self.subTest(vector=vector.name):
                shutil.copyfile(vector, self.show / "analog.odrgx")
                refused = self.refusal()
                self.assertEqual(refused.reason, "file-malformed")
                self.assertTrue(refused.detail.startswith(f"{self.show / 'analog.odrgx'}: {reason}: "), refused.detail)

    def test_a_container_of_frames_is_judged_by_its_frames_and_its_loop(self):
        (self.show / "film.odrgx").write_bytes(odrgx.wrap(1, 60, 60, 199, animation(8)))
        self.assertTrue(self.refusal().detail.startswith(f"{self.show / 'film.odrgx'}: loop-mismatch: "))
        (self.show / "film.odrgx").write_bytes(odrgx.wrap(1, 60, 6, 200, animation(8)))
        self.assertTrue(self.refusal().detail.startswith(f"{self.show / 'film.odrgx'}: canvas-mismatch: "))

    def test_a_container_of_another_canvas_is_a_size_mismatch(self):
        shutil.copyfile(VECTORS / "widgets" / "valid" / "small.analog.odrgx", self.show / "analog.odrgx")
        refused = self.refusal()
        self.assertEqual((refused.reason, refused.detail), ("size-mismatch", f"{self.show / 'analog.odrgx'}: the canvas is 21 x 13 and the mapping's is 60 x 60"))

    def test_an_odrg_file_is_refused_in_the_words_of_before(self):
        (self.show / "sun.odrg").write_bytes(animation(1)[:-3])
        refused = self.refusal()
        self.assertEqual(refused.reason, "file-malformed")
        self.assertTrue(refused.detail.startswith(f"{self.show / 'sun.odrg'}: truncated: "), refused.detail)
        (self.show / "sun.odrg").write_bytes(film())
        files = storage.folder_files(self.show)
        self.assertEqual(files["sun.odrg"], film())
        self.assertEqual(catalog.read(catalog.MemoryStorage(files)).entry("sun.odrg").type, "frames")


if __name__ == "__main__":
    unittest.main()

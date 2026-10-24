"""The internal catalog the firmware tool writes with a show folder it installs."""

import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from fwtool import paths, storage
from odrig import catalog, mapping, show
from tests.converter.test_catalog_format import animation

from . import support

PAGES = {catalog.page_name(number) for number in range(catalog.PAGES)}


def catalog_part(files):
    """The files of a catalog among files."""
    return {name: data for name, data in files.items() if name == catalog.MARKER or name in PAGES}


class Shown(unittest.TestCase):
    """The example show packed into a folder."""

    def setUp(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        self.folder = pathlib.Path(made.name)
        with support.example_show() as packed:
            shutil.copytree(packed, self.folder / "show")
        self.show = self.folder / "show"
        canvas = mapping.read(self.show / "mapping.json")
        self.canvas = (canvas.width, canvas.height)
        self.named = show.files(show.read(self.show / "show.json"))

    def library_rebuild(self, generation=1):
        """The catalog files the PC library's rebuild writes for the show's animations in
        the show's order, on a copy of the folder."""
        copy = self.folder / "copy"
        shutil.copytree(self.show, copy)
        made, refused = catalog.rebuild(catalog.Storage(copy), names=self.named, canvas=self.canvas, generation=generation)
        self.assertEqual(refused, [])
        return catalog_part(support.files_of(copy))


class Folder(Shown):
    def test_a_checked_folder_gets_the_catalog_of_its_animations(self):
        files = storage.folder_files(self.show)
        self.assertEqual({name: data for name, data in files.items() if name not in catalog_part(files)}, support.files_of(self.show))
        made = catalog.read(catalog.MemoryStorage(files))
        self.assertEqual((made.state, made.marker.generation), ("ok", 1))
        self.assertEqual(sorted(entry.name for entry in made.entries), sorted(self.named))
        self.assertEqual({(entry.width, entry.height) for entry in made.entries}, {self.canvas})
        self.assertEqual(catalog.check(catalog.MemoryStorage(files)), [])

    def test_the_catalog_is_the_one_a_rebuild_of_the_folder_writes(self):
        self.assertEqual(catalog_part(storage.folder_files(self.show)), self.library_rebuild())

    def test_without_the_check_there_is_none(self):
        self.assertEqual(storage.folder_files(self.show, check=False), support.files_of(self.show))

    def test_a_folders_own_catalog_is_made_anew(self):
        (self.show / catalog.MARKER).write_bytes(b"an old marker")
        (self.show / catalog.page_name(3)).write_bytes(b"an old page")
        self.assertEqual(catalog_part(storage.folder_files(self.show)), self.library_rebuild())

    def test_a_refused_animation_is_refused_with_its_reason_as_before(self):
        kept = (self.show / "dvd.odrg").read_bytes()
        (self.show / "dvd.odrg").write_bytes(kept[:-3])
        self.assertEqual(support.reason_of(self, lambda: storage.folder_files(self.show)), "file-malformed")
        (self.show / "dvd.odrg").write_bytes(animation(5, 30, 6))
        self.assertEqual(support.reason_of(self, lambda: storage.folder_files(self.show)), "size-mismatch")


class Installed(Shown):
    def setUp(self):
        super().setUp()
        patched = mock.patch.object(paths, "STORAGE", self.folder / "storage")
        patched.start()
        self.addCleanup(patched.stop)
        self.table = support.partition_table(support.small_layout())

    def install(self, image, *extra):
        esptool = support.RecordedEsptool(self.table, {0x610000: image})
        with support.no_board(esptool, answer=support.VALID):
            result = support.run_main("install-show", self.show, *extra)
        self.assertEqual(result.status, 0, result.err)
        made = bytearray(image)
        for address, content in esptool.wrote:
            made[address - 0x610000:address - 0x610000 + len(content)] = content
        return bytes(made), result

    def test_the_board_gets_the_catalog_with_the_show(self):
        board, _ = self.install(support.storage_image())
        self.assertEqual(storage.show_of(board), storage.folder_files(self.show))
        self.assertEqual(catalog.read(catalog.MemoryStorage(storage.show_of(board))).marker.generation, 1)

    def test_a_second_install_of_the_same_folder_changes_nothing(self):
        board, _ = self.install(support.storage_image())
        shutil.rmtree(self.folder / "storage")
        again, result = self.install(board)
        self.assertEqual(again, board)
        self.assertIn("storage: unchanged: nothing written; the board restarts\n", result.out)

    def test_a_changed_file_changes_its_page_and_the_marker_only(self):
        board, _ = self.install(support.storage_image())
        (self.show / "hello.odrg").write_bytes(animation(9, *self.canvas))
        shutil.rmtree(self.folder / "storage")
        again, _ = self.install(board)
        before, after = catalog_part(storage.show_of(board)), catalog_part(storage.show_of(again))
        changed = {name for name in set(before) | set(after) if before.get(name) != after.get(name)}
        self.assertEqual(changed, {catalog.MARKER, catalog.page_name(catalog.page_of("hello.odrg"))})
        self.assertEqual(catalog.read(catalog.MemoryStorage(storage.show_of(again))).marker.generation, 2)

    def test_the_generation_follows_the_boards_catalog(self):
        files = storage.folder_files(self.show)
        older = catalog.MemoryStorage(dict(files, **{"hello.odrg": animation(9, *self.canvas)}))
        catalog.rebuild(older, names=self.named, canvas=self.canvas, generation=41)
        image = support.storage_image(dict({path: data for path, data in support.WLED_FILES.items() if not path.startswith("/odrig/")},
                                           **{f"/odrig/{name}": data for name, data in older.files.items()}))
        board, _ = self.install(image)
        self.assertEqual(catalog.read(catalog.MemoryStorage(storage.show_of(board))).marker.generation, 42)
        damaged = support.storage_image(dict({path: data for path, data in support.WLED_FILES.items() if not path.startswith("/odrig/")},
                                             **{"/odrig/catalog.txt": b"damaged"}))
        shutil.rmtree(self.folder / "storage")
        board, _ = self.install(damaged)
        self.assertEqual(catalog.read(catalog.MemoryStorage(storage.show_of(board))).marker.generation, 1)

    def test_an_install_without_the_check_writes_no_catalog(self):
        board, _ = self.install(support.storage_image(), "--no-check")
        self.assertEqual(catalog_part(storage.show_of(board)), {})


if __name__ == "__main__":
    unittest.main()

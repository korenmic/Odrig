"""The numbered folders of the board's storage in the firmware tool: a show folder that holds
them as `folders.txt` or its show names them, an image that gets them, the board's
`folders.txt` kept, and an install that would remove the files of the board's folders,
refused unless `--replace-folders` is given, which keeps the board's next number."""

import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from fwtool import paths, storage

from . import support
from .test_storage import LAYOUT_LINE, applied

FOLDERS = b"odrig-folders 1 3\n1 20 0 shows\n2 21 0 shows/night\n"


def foldered(show_folder):
    """Moves the show's animations into the internal folders `shows` and `shows/night`."""
    show_path = show_folder / "show.json"
    show = json.loads(show_path.read_bytes())
    moved = {}
    for number, item in zip((1, 2), [item for item in show["items"] if "file" in item]):
        (show_folder / str(number)).mkdir(exist_ok=True)
        shutil.move(show_folder / item["file"], show_folder / str(number) / item["file"])
        moved[item["file"]] = f"{number}/{item['file']}"
    for item in show["items"]:
        if "file" in item:
            item["file"] = moved.get(item["file"], item["file"])
    show_path.write_text(json.dumps(show), encoding="utf-8", newline="\n")
    (show_folder / "folders.txt").write_bytes(FOLDERS)
    return moved


class Folders(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name)
        with support.example_show() as packed:
            shutil.copytree(packed, self.folder / "show")
        self.show = self.folder / "show"

    def test_a_show_folder_holds_the_numbered_folders_its_folders_file_names(self):
        moved = foldered(self.show)
        files = storage.folder_files(self.show)
        self.assertEqual(sorted(name for name in files if "/" in name), sorted(moved.values()))
        self.assertEqual(files["folders.txt"], FOLDERS)
        (self.show / "9").mkdir()
        (self.show / "9" / "x.odrg").write_bytes(b"x")
        self.assertEqual(support.reason_of(self, lambda: storage.folder_files(self.show)), "not-a-show-folder")
        self.assertEqual(support.reason_of(self, lambda: storage.folder_files(self.show, check=False)), "not-a-show-folder")

    def test_a_numbered_folder_that_only_the_show_names_is_a_folder_of_its_files(self):
        # As `read-show` writes the files of a folder whose line the board's file lacks.
        moved = foldered(self.show)
        (self.show / "folders.txt").unlink()
        for check in (True, False):
            with self.subTest(check=check):
                files = storage.folder_files(self.show, check=check)
                self.assertEqual(sorted(name for name in files if "/" in name), sorted(moved.values()))

    def test_an_image_gets_the_numbered_folders_and_keeps_an_empty_one_its_folders_file_names(self):
        foldered(self.show)
        files = storage.folder_files(self.show)
        files["folders.txt"] = FOLDERS + b"3 22 0 empty\n"
        made = storage.with_show(support.storage_image(), files)
        self.assertEqual(storage.show_of(made), files)
        system = storage.mount(made)
        self.assertTrue(storage.has_folder(system, "/odrig/3"))
        again = storage.with_show(made, files)
        self.assertEqual(again, made)


class Installing(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name)
        patched = mock.patch.object(paths, "STORAGE", self.folder / "storage")
        patched.start()
        self.addCleanup(patched.stop)
        self.table = support.partition_table(support.small_layout())
        with support.example_show() as packed:
            shutil.copytree(packed, self.folder / "show")
        self.show = self.folder / "show"
        board = dict(support.WLED_FILES, **{"/odrig/folders.txt": FOLDERS, "/odrig/1/kept.odrg": b"kept", "/odrig/2/other.odrg": b"other"})
        self.old = support.storage_image(board)

    def install(self, *extra):
        esptool = support.RecordedEsptool(self.table, {0x610000: self.old})
        with support.no_board(esptool, answer='{"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}'):
            result = support.run_main("install-show", self.show, *extra)
        return result, applied(self.old, [(address - 0x610000, content) for address, content in esptool.wrote])

    def test_an_install_that_would_remove_the_files_of_the_boards_folders_is_refused(self):
        result, after = self.install()
        self.assertEqual(result.status, 1)
        self.assertIn("error: folders-present: ", result.err)
        self.assertIn("1/kept.odrg", result.err)
        self.assertIn("2/other.odrg", result.err)
        self.assertEqual(after, self.old)

    def test_replace_folders_installs_the_folder_in_their_place_and_keeps_the_next_number(self):
        result, after = self.install("--replace-folders")
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out.splitlines()[0], LAYOUT_LINE)
        self.assertEqual(storage.show_of(after), dict(storage.folder_files(self.show), **{"folders.txt": b"odrig-folders 1 3\n"}))

    def test_the_boards_folders_file_is_kept_for_a_folder_without_one(self):
        self.old = support.storage_image(dict(support.WLED_FILES, **{"/odrig/folders.txt": FOLDERS}))
        result, after = self.install()
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(storage.show_of(after), dict(storage.folder_files(self.show), **{"folders.txt": FOLDERS}))
        system = storage.mount(after)
        self.assertTrue(storage.has_folder(system, "/odrig/1") and storage.has_folder(system, "/odrig/2"))

    def test_a_folder_that_holds_the_files_of_the_boards_folders_is_installed(self):
        moved = foldered(self.show)
        self.old = support.storage_image(dict(support.WLED_FILES, **{"/odrig/folders.txt": FOLDERS, **{f"/odrig/{name}": b"old" for name in moved.values()}}))
        result, after = self.install()
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(storage.show_of(after), storage.folder_files(self.show))


class ReadingBack(unittest.TestCase):
    def test_write_folder_puts_the_files_of_numbered_folders_into_sub_folders(self):
        with tempfile.TemporaryDirectory() as holder:
            out = pathlib.Path(holder, "out")
            storage.write_folder(out, {"folders.txt": FOLDERS, "1/a.odrg": b"a", "b.odrg": b"b"})
            self.assertEqual((out / "1" / "a.odrg").read_bytes(), b"a")
            self.assertEqual(sorted(storage.folder_files(out, check=False)), ["1/a.odrg", "b.odrg", "folders.txt"])


if __name__ == "__main__":
    unittest.main()

import json
import pathlib
import tempfile
import unittest

from tests.core import support as core_support
from tests.core.support import BOARD_STORAGE, STORAGE_BLOCK, ReferencePlayer

from . import support


def over_serial(emulator, line):
    with support.Serial(emulator.serial) as port:
        return port.ask(line)


def over_http(emulator, line):
    return emulator.command(line)


ROUTES = {"serial": over_serial, "http": over_http}


class Space(unittest.TestCase):
    def setUp(self):
        self.folder = pathlib.Path(support.entered(self, support.example_show()))

    def started(self, *options):
        return support.entered(self, support.Emulator(self.folder, *options))

    def test_space_gives_the_reply_of_the_reference_over_serial_and_over_http(self):
        emulator = self.started()
        expected = ReferencePlayer(support.files_of(self.folder)).command(0, b"space")
        self.assertEqual(expected, b'{"ok":true,"free":10338304,"total":10354688,"animations":2}\n')
        for route, ask in ROUTES.items():
            self.assertEqual(ask(emulator, "space"), expected, route)
            self.assertEqual(ask(emulator, "space 1"), b'{"ok":false,"error":"bad-argument"}\n', route)

    def test_the_total_is_the_boards_storage_and_the_free_space_is_counted_in_blocks_of_the_files(self):
        (self.folder / "extra.odrg").write_bytes(bytes(STORAGE_BLOCK + 1))
        emulator = self.started()
        for route, ask in ROUTES.items():
            reply = json.loads(ask(emulator, "space"))
            self.assertEqual(reply, {"ok": True, "free": BOARD_STORAGE - 6 * STORAGE_BLOCK, "total": BOARD_STORAGE, "animations": 2}, route)
        (self.folder / "more.odrg").write_bytes(bytes(3 * STORAGE_BLOCK))
        self.assertEqual(json.loads(over_http(emulator, "space"))["free"], BOARD_STORAGE - 9 * STORAGE_BLOCK)
        (self.folder / "more.odrg").unlink()
        (self.folder / "extra.odrg").unlink()
        self.assertEqual(json.loads(over_serial(emulator, "space"))["free"], BOARD_STORAGE - 4 * STORAGE_BLOCK)

    def test_the_storage_option_sets_the_total(self):
        for total in (0, 10000, 4 * STORAGE_BLOCK, 4 * STORAGE_BLOCK + 7, 4294967295):
            with self.subTest(total=total):
                emulator = support.Emulator(self.folder, "--storage", total)
                try:
                    expected = ReferencePlayer(support.files_of(self.folder), storage=total).command(0, b"space")
                    for route, ask in ROUTES.items():
                        self.assertEqual(ask(emulator, "space"), expected, route)
                    self.assertEqual(json.loads(expected), {"ok": True, "free": max(0, total - 4 * STORAGE_BLOCK), "total": total, "animations": 2})
                finally:
                    emulator.stop()

    def test_space_with_an_invalid_show_reports_no_animations(self):
        (self.folder / "dvd.odrg").unlink()
        emulator = self.started()
        for route, ask in ROUTES.items():
            self.assertEqual(json.loads(ask(emulator, "space")), {"ok": True, "free": BOARD_STORAGE - 3 * STORAGE_BLOCK, "total": BOARD_STORAGE, "animations": 0}, route)
        self.assertEqual(emulator.status()["error"], "file-missing dvd.odrg")

    def test_space_changes_no_file_of_the_folder(self):
        before = support.files_of(self.folder)
        emulator = self.started()
        for ask in ROUTES.values():
            ask(emulator, "space")
        emulator.stop()
        self.assertEqual(support.files_of(self.folder), before)
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), sorted(before))


class ListAndRemove(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.folder = support.installed(self.work / "show", core_support.example_show())
        (self.work / "beside.txt").write_bytes(b"not of the show")

    def started(self, *options):
        return support.entered(self, support.Emulator(self.folder, *options))

    def reference(self):
        return ReferencePlayer(support.files_of(self.folder))

    def test_list_gives_the_reply_of_the_reference_over_serial_and_over_http(self):
        emulator = self.started()
        player = self.reference()
        for line in ("list", "list 0", "list 1", "list 2", "list 3", "list 65535", "list x", "list 1 2"):
            expected = player.command(0, line.encode())
            for route, ask in ROUTES.items():
                self.assertEqual(ask(emulator, line), expected, (route, line))
        self.assertEqual(
            player.command(0, b"list"),
            b'{"ok":true,"items":[{"id":1,"file":"hello.odrg","bytes":1138},{"id":2,"file":"dvd.odrg","bytes":1612},{"id":3,"cycle":[1,2],"seconds":15}],"next":null}\n',
        )

    def test_remove_changes_the_show_and_the_folder_as_the_reference_has_them_by_each_route(self):
        for first, second in (("serial", "http"), ("http", "serial")):
            with self.subTest(first=first):
                support.installed(self.folder, core_support.example_show())
                player = self.reference()
                emulator = support.Emulator(self.folder)
                try:
                    session = (
                        (first, "remove 1"), (second, "list"), (first, "remove 3"), (second, "status"), (second, "list"), (second, "remove 1"), (first, "remove 9"),
                        (first, "space"), (second, "remove 2"), (first, "list"), (second, "space"), (first, "remove 2"),
                    )
                    for route, line in session:
                        expected = player.command(0, line.encode())
                        reply = ROUTES[route](emulator, line)
                        if line == "status":
                            self.assertEqual(support.without_fps(reply), support.without_fps(expected), line)
                        else:
                            self.assertEqual(reply, expected, (route, line))
                finally:
                    emulator.stop()
                self.assertEqual(support.files_of(self.folder), player.files)
                self.assertEqual(sorted(support.files_of(self.folder)), ["mapping.json", "show.json"])
                self.assertEqual((self.folder / "show.json").read_bytes(), b'{"version":1,"brightness":128,"items":[]}\n')

    def test_a_removal_is_there_after_the_emulator_was_started_again(self):
        emulator = support.Emulator(self.folder)
        try:
            self.assertEqual(emulator.status()["playing"], 3)
            self.assertEqual(over_serial(emulator, "remove 3"), b'{"ok":true}\n')
            self.assertEqual(emulator.status()["playing"], None)
            self.assertEqual(over_http(emulator, "remove 2"), b'{"ok":true}\n')
            listed = over_http(emulator, "list")
        finally:
            emulator.stop()
        self.assertEqual(sorted(support.files_of(self.folder)), ["hello.odrg", "mapping.json", "show.json"])
        again = self.started()
        self.assertEqual(over_serial(again, "list"), listed)
        self.assertEqual(listed, b'{"ok":true,"items":[{"id":1,"file":"hello.odrg","bytes":1138}],"next":null}\n')
        state = again.status()
        self.assertEqual((state["playing"], state["error"]), (None, None))
        self.assertEqual(over_http(again, "play 1"), b'{"ok":true}\n')
        self.assertEqual(again.status()["animation"], 1)
        self.assertEqual(json.loads(over_http(again, "space"))["animations"], 1)

    def test_the_commands_write_in_the_folder_and_nowhere_else(self):
        emulator = self.started()
        for line in ("remove 3", "remove 1", "list", "space"):
            over_http(emulator, line)
        emulator.stop()
        self.assertEqual(sorted(path.name for path in self.work.iterdir()), ["beside.txt", "show"])
        self.assertEqual((self.work / "beside.txt").read_bytes(), b"not of the show")
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ["dvd.odrg", "mapping.json", "show.json"])

    def test_what_an_interrupted_change_left_is_removed_when_the_emulator_starts(self):
        (self.folder / "upload.part").write_bytes(b"half")
        (self.folder / "show.part").write_bytes(b"{")
        (self.folder / "pending.txt").write_bytes(b"stray.odrg\nhello.odrg\n")
        (self.folder / "stray.odrg").write_bytes((self.folder / "hello.odrg").read_bytes())
        emulator = self.started()
        self.assertEqual(emulator.status()["error"], None)
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])


if __name__ == "__main__":
    unittest.main()

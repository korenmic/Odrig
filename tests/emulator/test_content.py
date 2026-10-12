import json
import pathlib
import unittest

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


if __name__ == "__main__":
    unittest.main()

"""The emulator's drive: listed only when the core asks, the names the core gives its places,
and the files it may change, by name, unless the drive is read only."""

import pathlib
import tempfile
import unittest

from emulator import host


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        self.now += 10
        return self.now


class TheDrive(unittest.TestCase):
    def setUp(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        self.top = pathlib.Path(made.name)
        self.folder = self.top / "odrig"
        self.folder.mkdir()
        for name in ("b.odrg", "A.ODRG", ".hidden.odrg", "notes.txt"):
            (self.folder / name).write_bytes(name.encode())
        (self.top / "show").mkdir()

    def host(self, writable=True):
        return host.FolderHost(self.top / "show", drive=host.Drive(self.top, clock=Clock(), writable=writable))

    def test_it_is_listed_only_when_the_core_asks(self):
        made = self.host()
        number = made.drive_number()
        self.assertNotEqual(number, 0)
        self.assertIsNone(made.drive_name(number, 0))
        self.assertEqual(made.drive.listings, 0)
        self.assertEqual(made.drive_list(number), 2)
        self.assertEqual([made.drive_name(number, place) for place in range(3)], ["A.ODRG", "b.odrg", None])
        self.assertIsNone(made.drive_list(number + 1))

    def test_places_get_the_names_the_core_gives(self):
        made = self.host()
        number = made.drive_number()
        self.assertTrue(made.drive_bind(number, 3, "Fire Swirl 2.ODRG"))
        self.assertEqual((made.drive_name(number, 3), made.drive_name(number, 1)), ("Fire Swirl 2.ODRG", None))
        for name in ("", ".hidden.odrg", "a?b.odrg", "x" * 101, "/b.odrg", "a//b.odrg", "a/", "a/.b.odrg", "../b.odrg", "a/b/c/d/e.odrg"):
            self.assertFalse(made.drive_bind(number, 4, name), name)
        self.assertTrue(made.drive_bind(number, 5, "night/comet.odrg"))
        self.assertEqual(made.drive_name(number, 5), "night/comet.odrg")
        (self.folder / "night").mkdir()
        (self.folder / "night" / "comet.odrg").write_bytes(b"comet")
        self.assertEqual(made.read_at("drive/5", 0, 512), b"comet")
        self.assertEqual(made.read_at("drive/night/comet.odrg", 0, 512), b"comet")
        self.assertFalse(made.drive_bind(number + 1, 4, "a.odrg"))
        (self.folder / "Fire Swirl 2.ODRG").write_bytes(b"swirl")
        self.assertEqual(made.read_at("drive/3", 0, 512), b"swirl")
        self.assertEqual(made.read_at("drive/Fire Swirl 2.ODRG", 0, 512), b"swirl")

    def test_files_are_changed_by_name_in_the_folder(self):
        made = self.host()
        number = made.drive_number()
        self.assertTrue(made.drive_writable(number))
        self.assertEqual(made.write_open("drive/upload.part"), 1)
        self.assertEqual(made.write(b"new bytes"), 1)
        self.assertEqual(made.write_close(), 1)
        self.assertEqual(made.rename("drive/upload.part", "drive/new one.odrg"), 1)
        self.assertEqual((self.folder / "new one.odrg").read_bytes(), b"new bytes")
        self.assertEqual(made.remove("drive/b.odrg"), 1)
        self.assertEqual(made.remove("drive/b.odrg"), 0)
        self.assertFalse((self.folder / "b.odrg").exists())
        # A place is not a name a change may use.
        made.drive_list(number)
        self.assertEqual(made.remove("drive/0"), -1)

    def test_a_drive_that_is_read_only_is_not_changed(self):
        made = self.host(writable=False)
        number = made.drive_number()
        self.assertFalse(made.drive_writable(number))
        self.assertEqual(made.write_open("drive/upload.part"), -1)
        self.assertEqual(made.rename("drive/b.odrg", "drive/c.odrg"), -1)
        self.assertEqual(made.remove("drive/b.odrg"), -1)
        self.assertTrue((self.folder / "b.odrg").exists())
        self.assertEqual(made.read_at("drive/b.odrg", 0, 512), b"b.odrg")

    def test_a_drive_pulled_out_is_neither_read_nor_changed(self):
        made = self.host()
        made.drive_number()
        self.folder.rename(self.top / "away")
        self.assertEqual(made.drive_number(), 0)
        self.assertIsNone(made.read_at("drive/b.odrg", 0, 512))
        self.assertEqual(made.write_open("drive/upload.part"), -1)


if __name__ == "__main__":
    unittest.main()

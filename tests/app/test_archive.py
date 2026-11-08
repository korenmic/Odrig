"""A zip archive of animations opened on the phone, its animations listed, ticked and
uploaded one after another."""

import io
import math
import pathlib
import tempfile
import unittest
import zipfile

from odrig import catalog, odrg, odrgx

from tests.core import support as core_support
from tests.emulator import support as emulator_support
from . import support
from .test_target import entered

NAME_RULE = "Use a filename of at most 32 lowercase letters, digits, dots, - or _, ending in .odrg or .odrgx."
THERE = "A file of this name is there."


def kb(size):
    return str(math.ceil(size / 1000))


def zipped(entries):
    """A zip of `(name, data, method)` entries, in their order."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data, method in entries:
            info = zipfile.ZipInfo(name, (2026, 11, 8, 0, 0, 0))
            info.compress_type = method
            archive.writestr(info, data)
    return bytearray(buffer.getvalue())


def headers(data, name):
    """The places of an entry's local header and of its central one."""
    encoded = name.encode("utf-8")
    local = central = None
    at = 0
    while True:
        at = data.find(b"PK\x03\x04", at)
        if at < 0:
            break
        length = int.from_bytes(data[at + 26:at + 28], "little")
        if data[at + 30:at + 30 + length] == encoded:
            local = at
        at += 4
    at = 0
    while True:
        at = data.find(b"PK\x01\x02", at)
        if at < 0:
            break
        length = int.from_bytes(data[at + 28:at + 30], "little")
        if data[at + 46:at + 46 + length] == encoded:
            central = at
        at += 4
    return local, central


def encrypted(data, name):
    local, central = headers(data, name)
    data[local + 6] |= 1
    data[central + 8] |= 1


def zip64(data, name):
    _, central = headers(data, name)
    data[central + 20:central + 28] = b"\xff" * 8


def damaged(data, name):
    local, _ = headers(data, name)
    start = local + 30 + int.from_bytes(data[local + 26:local + 28], "little") + int.from_bytes(data[local + 28:local + 30], "little")
    size = int.from_bytes(data[local + 18:local + 22], "little")
    for at in range(start + size // 3, start + size // 3 + 8):
        data[at] ^= 0x5A


class Reading(unittest.TestCase):
    def setUp(self):
        self.show = entered(self, emulator_support.example_show())
        self.hello = (self.show / "hello.odrg").read_bytes()
        loop = sum(ms for ms, _ in odrg.decode(self.hello).records)
        self.loop = loop
        self.container = odrgx.wrap(1, 60, 6, loop, self.hello)
        self.media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        long_clip = core_support.clip(5, 60, 6, (20,) * 30)
        data = zipped([
            ("clips/a.odrg", self.hello, zipfile.ZIP_STORED),
            ("b.odrgx", self.container, zipfile.ZIP_DEFLATED),
            ("readme.txt", b"not an animation", zipfile.ZIP_DEFLATED),
            ("big.odrg", core_support.clip(1, 60, 60, (20, 20)), zipfile.ZIP_DEFLATED),
            ("a-very-long-name-of-more-than-32-characters.odrg", self.hello, zipfile.ZIP_DEFLATED),
            ("locked.odrg", self.hello, zipfile.ZIP_STORED),
            ("wide.odrg", self.hello, zipfile.ZIP_STORED),
            ("broken.odrg", long_clip, zipfile.ZIP_DEFLATED),
            ("hello.odrg", self.hello, zipfile.ZIP_DEFLATED),
        ])
        encrypted(data, "locked.odrg")
        zip64(data, "wide.odrg")
        damaged(data, "broken.odrg")
        (self.media / "archive.png").write_bytes(bytes(data))

    def opened(self, *options, **settings):
        emulator = entered(self, emulator_support.Emulator(self.show, *options))
        return support.run("archive", address=f"127.0.0.1:{emulator.port}", media=self.media,
                           settings={"rows": 2, "zip": ["archive.png", "clocks.zip"], **settings}).seen

    def test_the_entries_are_listed_with_their_kind_size_and_length_or_why_not(self):
        found = self.opened(renames=[[4, "short-name.odrg"]], replace=[8], none=True)
        self.assertEqual(found["name"], "clocks.zip: 4 animations of 9 entries.")
        rows = found["rows"]
        self.assertEqual([row["path"] for row in rows], ["clips/a.odrg", "b.odrgx", "readme.txt", "big.odrg", "a-very-long-name-of-more-than-32-characters.odrg",
                                                         "locked.odrg", "wide.odrg", "broken.odrg", "hello.odrg"])
        seconds = f"{self.loop / 1000:.2f} s"
        self.assertEqual(rows[0], {"path": "clips/a.odrg", "state": "", "facts": f"{kb(len(self.hello))} KB, frames, {seconds}", "ticked": True, "tickable": True,
                                   "name": "a.odrg", "why": None, "replace": False})
        self.assertEqual((rows[1]["facts"], rows[1]["name"], rows[1]["ticked"]), (f"{kb(len(self.container))} KB, frames, {seconds}", "b.odrgx", True))
        self.assertEqual((rows[2]["state"], rows[2]["tickable"], rows[2]["name"]), ("passed over: not an animation", False, None))
        self.assertEqual((rows[3]["state"], rows[3]["tickable"]), ("refused: The animation canvas is 60 × 60; the target needs 60 × 6.", False))
        self.assertEqual((rows[4]["why"], rows[4]["tickable"]), (NAME_RULE, True))
        self.assertEqual(rows[5]["state"], "unreadable: The entry is encrypted.")
        self.assertEqual(rows[6]["state"], "unreadable: The entry is in zip64, which the app does not read.")
        self.assertTrue(rows[7]["state"].startswith("unreadable: The entry is damaged"), rows[7]["state"])
        self.assertEqual((rows[8]["why"], rows[8]["replace"]), (THERE, True))
        self.assertEqual(found["button"], {"disabled": True, "reason": "Mend the names marked in the list."})
        self.assertTrue(found["sum"].startswith(f"4 ticked, {kb(3 * len(self.hello) + len(self.container))} KB. Internal storage: Free "), found["sum"])
        # The long name renamed, and Replace ticked beside the name that is there.
        self.assertEqual(found["renamed"]["rows"], [None] * 8 + [THERE])
        self.assertEqual(found["none"]["ticked"], [False] * 9)
        self.assertEqual(found["none"]["button"], {"disabled": True, "reason": "Tick the animations to upload."})
        self.assertEqual(found["all"], [True, True, False, False, True, False, False, False, True])

    def test_a_name_that_is_there_waits_for_replace(self):
        found = self.opened(renames=[[4, "short-name.odrg"]])
        self.assertEqual(found["renamed"]["button"], {"disabled": True, "reason": "Tick Replace beside a name that is there, or rename the file."})

    def test_the_card_takes_the_paths_of_the_archive(self):
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        drive = top / "odrig"
        drive.mkdir()
        (drive / "old.odrg").write_bytes(self.hello)
        _, refused = catalog.rebuild(catalog.Storage(drive, drive=True), names=["old.odrg"], canvas=(60, 6))
        self.assertEqual(refused, [])
        found = self.opened("--drive", top, rows=3, store="internal")
        self.assertEqual(found["rows"][0]["name"], "clips/a.odrg")
        self.assertEqual(found["stored"][0], "a.odrg")

    def test_the_sum_against_the_free_space_disables_the_upload(self):
        found = self.opened("--storage", 28000, renames=[[4, "short-name.odrg"]], replace=[8])
        self.assertTrue(found["renamed"]["button"]["disabled"])

    def test_a_file_that_is_no_zip_is_said(self):
        (self.media / "notzip.png").write_bytes(b"not a zip at all")
        found = self.opened(zip=["notzip.png", "notzip.zip"])
        self.assertEqual(found["message"], "Cannot open this archive: The file is not a zip archive.")


if __name__ == "__main__":
    unittest.main()

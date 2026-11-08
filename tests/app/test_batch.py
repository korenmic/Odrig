"""Ready-made animations picked several at once and uploaded as one run."""

import math
import pathlib
import tempfile
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support
from . import support
from .test_target import entered

NAME_RULE = "Use a filename of at most 32 lowercase letters, digits, dots, - or _, ending in .odrg or .odrgx."


def kb(size):
    return str(math.ceil(size / 1000))


class Picking(unittest.TestCase):
    """The list a pick of several files makes, before anything is sent."""

    def setUp(self):
        self.show = entered(self, emulator_support.example_show())
        self.hello = (self.show / "hello.odrg").read_bytes()
        self.dvd = (self.show / "dvd.odrg").read_bytes()
        self.media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        for name, data in (("hello.odrg", self.hello), ("dvd.odrg", self.dvd), ("notes.png", b"not an animation"),
                           ("big.odrg", core_support.clip(1, 60, 60, (20, 20)))):
            (self.media / name).write_bytes(data)

    def test_files_picked_at_once_are_listed_checked_and_named_and_add_more_adds_to_them(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        found = support.run("batch", address=f"127.0.0.1:{emulator.port}", media=self.media, settings={
            "rows": 2,
            "first": [["hello.odrg", "Sun Rise.odrg"], "hello.odrg", ["dvd.odrg", "HELLO.odrg"]],
            "more": [["notes.png", "notes.txt"], "big.odrg", "hello.odrg"],
            "renames": [[0, "Bad Name.odrg"], [0, "hello-2.odrg"], [0, "sun-rise.odrg"]],
            "remove": [4, 3, 2, 1],
        }).seen
        self.assertEqual(found["chooser"], ["Choose ready-made animations"])
        self.assertTrue(found["multiple"])
        three = [{"name": "sun-rise.odrg", "state": "waiting", "why": None}, {"name": "hello-2.odrg", "state": "waiting", "why": None},
                 {"name": "hello-3.odrg", "state": "waiting", "why": None}]
        self.assertEqual(found["listed"], three)
        self.assertTrue(found["formHidden"])
        total = 2 * len(self.hello) + len(self.dvd)
        self.assertEqual(found["sum"], f"3 animations, {kb(total)} KB.")
        self.assertEqual(found["button"], {"words": "Upload 3 animations", "disabled": False, "reason": None})
        # The same file picked again is listed once; one of another ending and one of another
        # canvas are refused with today's words.
        self.assertEqual(found["more"], three + [
            {"name": "notes.txt", "state": "refused: Choose an .odrg or .odrgx animation file.", "why": None},
            {"name": "big.odrg", "state": "refused: The animation canvas is 60 × 60; the target needs 60 × 6.", "why": None}])
        self.assertEqual(found["sumMore"], f"3 animations, {kb(total)} KB.")
        mend = {"words": "Upload 3 animations", "disabled": True, "reason": "Mend the names marked in the list."}
        self.assertEqual(found["renamed"], [
            {"rows": [NAME_RULE, None, None, None, None], "button": mend},
            {"rows": ["Another file of this batch has this name.", "Another file of this batch has this name.", None, None, None], "button": mend},
            {"rows": [None] * 5, "button": {"words": "Upload 3 animations", "disabled": False, "reason": None}},
        ])
        # Four rows removed leave one, which stays a list.
        self.assertEqual(found["afterRemove"], ["sun-rise.odrg"])
        self.assertTrue(found["listShown"])

    def test_names_follow_the_storage_until_the_start(self):
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        emulator_support.installed(top / "odrig", {"sun-rise.odrg": self.hello})
        emulator = entered(self, emulator_support.Emulator(self.show, "--drive", top))
        found = support.run("batch", address=f"127.0.0.1:{emulator.port}", media=self.media, settings={
            "rows": 3, "first": [["hello.odrg", "Sun Rise.odrg"], "hello.odrg"], "renames": [[1, "kept.odrg"]], "store": "internal"}).seen
        # On the card the card's root has sun-rise.odrg; in the board's storage the root has
        # hello.odrg. The edited name stays.
        self.assertEqual([row["name"] for row in found["listed"]], ["sun-rise-2.odrg", "hello.odrg"])
        self.assertEqual(found["storage"], "external")
        self.assertEqual(found["afterStore"], ["sun-rise.odrg", "kept.odrg"])
        self.assertEqual(found["destination"], "Internal /")

    def test_the_sum_against_the_free_space_disables_the_button(self):
        emulator = entered(self, emulator_support.Emulator(self.show, "--storage", 28000))
        found = support.run("batch", address=f"127.0.0.1:{emulator.port}", media=self.media, settings={
            "rows": 2, "first": [["hello.odrg", "a.odrg"], ["hello.odrg", "b.odrg"], ["dvd.odrg", "c.odrg"], ["dvd.odrg", "d.odrg"]]}).seen
        self.assertTrue(found["button"]["disabled"])
        self.assertRegex(found["button"]["reason"], r"\AThese animations need [0-9]+ KB and the installation has [0-9]+ KB free\.\Z")

    def test_one_file_opens_todays_form(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        found = support.run("batch", address=f"127.0.0.1:{emulator.port}", media=self.media, settings={"mode": "one", "rows": 2, "file": "hello.odrg"}).seen
        self.assertTrue(found["facts"].startswith("Ready-made animation, 60 × 6,"))
        self.assertIsNone(found["list"])
        self.assertEqual(found["button"], "Upload to the installation")


if __name__ == "__main__":
    unittest.main()

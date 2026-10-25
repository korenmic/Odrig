import json
import pathlib
import shutil
import tempfile
import unittest

from . import support
from tests.core import support as core_support
from tests.emulator.support import Emulator
from tests.mapping.test_core import PINS, files, set_line

DEFAULTS = list(range(1, 19)) + [21, 47]
PHOTOS = sorted(path.name for path in (support.ROOT / "project-seeds" / "40-p2-the-mapping-from-a-photo-of-the-diagonal" / "photos").glob("*.jpg"))


def shows(pins, position):
    """The snake a position shows when the board's pins are these and the wall is wired as
    the defaults say."""
    return pins.index(DEFAULTS[position - 1]) + 1


class TheAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        folder = pathlib.Path(cls.work.name, "media")
        folder.mkdir()
        cls.media = support.make_media(folder)
        for name in PHOTOS:
            shutil.copy(support.ROOT / "project-seeds" / "40-p2-the-mapping-from-a-photo-of-the-diagonal" / "photos" / name, cls.media)
        cls.seen = support.run("photo-analysis", settings={"photos": PHOTOS}, media=cls.media).seen

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def assert_read_back(self, name, dead=(), readings=1):
        found = self.seen[name]
        self.assertNotIn("refused", found, found)
        self.assertGreaterEqual(found["points"], 2 * (20 - len(dead)), found)
        self.assertEqual(found["readings"][0]["nulls"], len(dead), found)
        self.assertEqual(len(found["readings"]), readings, found)
        self.assertEqual(found["pins"], DEFAULTS, found)
        self.assertLess(found["ms"], 2000, found)

    def test_every_position_showing_its_own_snake_reads_back_the_pins_as_they_are(self):
        self.assert_read_back("plain")
        self.assertEqual(self.seen["plain"]["positions"], list(range(1, 21)))
        self.assertEqual(self.seen["plain"]["ignored"], 0)

    def test_a_permutation_reads_back_turned_slanted_blurred_and_grainy(self):
        for name in ("shuffled", "keystone"):
            with self.subTest(name):
                self.assert_read_back(name)
                self.assertEqual(self.seen[name]["readings"][0]["filled"], [])

    def test_a_dead_line_in_the_middle_gets_the_snake_that_remains(self):
        self.assert_read_back("deadMiddle", dead=[7])
        reading = self.seen["deadMiddle"]["readings"][0]
        shuffled = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 47, 15, 16, 17, 18, 21, 1, 11]
        self.assertEqual(reading["filled"], [{"position": 7, "snake": shows(shuffled, 7)}])
        self.assertEqual((reading["xEnd"], reading["yEnd"]), (None, None))

    def test_a_dead_line_at_an_end_offers_both_readings_and_one_is_right(self):
        found = self.seen["deadEnd"]
        self.assertEqual([(reading["xEnd"], reading["yEnd"]) for reading in found["readings"]], [("right", None), ("left", None)])
        self.assert_read_back("deadEnd", dead=[1], readings=2)
        self.assertEqual(found["readings"][1]["filled"], [{"position": 1, "snake": 10}])

    def test_two_dead_lines_get_the_remaining_snakes_lowest_to_leftmost(self):
        self.assert_read_back("twoDead", dead=[5, 12])
        self.assertEqual(self.seen["twoDead"]["readings"][0]["filled"], [{"position": 5, "snake": 5}, {"position": 12, "snake": 12}])

    def test_bright_spots_off_the_grid_are_ignored(self):
        self.assert_read_back("noise")
        self.assertGreaterEqual(self.seen["noise"]["ignored"], 1)

    def test_a_flash_photo_of_the_unlit_wall_is_refused_with_the_count(self):
        found = self.seen["flash"]
        self.assertTrue(found["refused"], found)
        self.assertGreater(found["found"], 100)

    def test_the_owners_photos_of_the_unlit_wall_are_refused(self):
        self.assertEqual(len(PHOTOS), 4)
        for name in PHOTOS:
            with self.subTest(name):
                found = self.seen["owner"][name]
                self.assertTrue(found["refused"], found)
                self.assertLessEqual(max(found["width"], found["height"]), 600)

    def test_a_png_file_is_read_and_scaled_like_a_jpeg(self):
        found = self.seen["png"]
        self.assertEqual((found["width"], found["height"]), (600, 375), found)
        self.assertGreater(found["bytes"], 1000)
        self.assertNotIn("refused", found, found)
        self.assertEqual(found["pins"], DEFAULTS, found)

    def test_a_jpeg_turned_by_its_orientation_tag_is_read_upright(self):
        found = self.seen["turned"]
        self.assertEqual((found["width"], found["height"]), (480, 270), found)
        self.assertNotIn("refused", found, found)
        self.assertEqual(found["positions"], list(range(1, 21)), found)
        self.assertEqual(found["pins"], DEFAULTS)


SHUFFLED = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 47, 15, 16, 17, 18, 21, 1, 11]
SWAPPED = [10, 2, 3, 4, 5, 6, 7, 8, 9, 1, 11, 12, 13, 14, 15, 16, 17, 18, 21, 47]


class TheScreen(unittest.TestCase):
    """Settings' mapping from a photo, in Chrome against the emulator and stand-in targets."""

    def opened(self, pins=None):
        folder = self.enterContext(core_support.installed(files()))
        target = self.enterContext(Emulator(folder))
        if pins is not None:
            self.assertTrue(json.loads(target.command(set_line(pins)))["ok"])
        return target

    def mapping(self, target):
        return json.loads(target.command("mapping get"))

    def test_a_photo_of_a_permuted_wall_is_read_shown_and_applied(self):
        target = self.opened(SHUFFLED)
        found = support.run("photomap", address=f"127.0.0.1:{target.port}", settings={"photo": {"pins": SHUFFLED, "angle": 3}}, steps=[lambda: None]).seen
        self.assertIn("whole wall", found["advice"])
        self.assertTrue(found["diagonalOffered"])
        self.assertEqual(found["marks"], 20)
        self.assertGreater(found["previewWidth"], 200)
        self.assertEqual(found["choices"], [])
        self.assertTrue(found["applyShown"])
        self.assertEqual(found["discardWords"], "Discard")
        # Position 1 has pin 1, which drives snake 19 under the shuffled pins.
        self.assertIn(f"Position 1 shows snake {shows(SHUFFLED, 1)}.", found["words"])
        self.assertNotIn("Every position shows its own snake.", found["words"])
        self.assertEqual(found["said"], "Saved from the photo.")
        self.assertTrue(found["applyDisabled"])
        self.assertFalse(found["otherShown"])
        self.assertEqual(self.mapping(target)["pins"], PINS)
        self.assertTrue(found["droppedOnLeaving"])

    def test_a_right_wall_says_so_and_the_diagonal_is_started_from_the_screen(self):
        target = self.opened()
        tests = []
        found = support.run("photomap", address=f"127.0.0.1:{target.port}", settings={"diagonal": True, "photo": {"pins": PINS, "png": False}},
                            steps=[lambda: tests.append(self.mapping(target)["test"]), lambda: None]).seen
        self.assertEqual(tests, [True])
        self.assertFalse(found["diagonalOffered"])
        self.assertEqual(found["words"], ["Every position shows its own snake."])
        self.assertIn("nothing to save", found["said"])
        self.assertEqual(self.mapping(target)["pins"], PINS)

    def test_a_dead_line_at_an_end_offers_the_readings_and_the_chosen_one_is_applied(self):
        target = self.opened(SWAPPED)
        found = support.run("photomap", address=f"127.0.0.1:{target.port}", settings={"photo": {"pins": SWAPPED, "dead": [1]}, "pick": "Dark strip at the left"}, steps=[lambda: None]).seen
        self.assertEqual(found["choices"], [["Dark strip at the right", "true"], ["Dark strip at the left", "false"]])
        self.assertEqual(found["picked"], ["false", "true"])
        self.assertIn("Position 1 shows no snake; snake 10 goes there.", found["wordsPicked"])
        self.assertEqual(found["marks"], 20)
        self.assertEqual(found["said"], "Saved from the photo.")
        self.assertTrue(found["otherShown"])
        self.assertEqual(self.mapping(target)["pins"], PINS)

    def test_other_reading_applies_the_next_one(self):
        target = self.opened()
        pins = []
        found = support.run("photomap", address=f"127.0.0.1:{target.port}", settings={"photo": {"pins": PINS, "dead": [1]}, "other": True},
                            steps=[lambda: pins.append(self.mapping(target)["pins"]), lambda: pins.append(self.mapping(target)["pins"])]).seen
        self.assertEqual(len(found["choices"]), 4)
        self.assertEqual(found["otherPicked"], ["false", "true", "false", "false"])
        self.assertEqual(len(pins), 2)
        self.assertNotEqual(pins[0], pins[1])
        self.assertEqual(sorted(pins[1]), sorted(PINS))

    def test_discard_drops_the_photo(self):
        target = self.opened(SHUFFLED)
        found = support.run("photomap", address=f"127.0.0.1:{target.port}", settings={"photo": {"pins": SHUFFLED}, "discard": True}).seen
        self.assertTrue(found["hiddenAfterDiscard"])
        self.assertTrue(found["inputEmpty"])
        self.assertEqual(self.mapping(target)["pins"], SHUFFLED)

    def test_a_photo_without_the_diagonal_is_refused_with_the_count_and_the_advice(self):
        target = self.opened()
        found = support.run("photomap", address=f"127.0.0.1:{target.port}", settings={"photo": {"flash": True}, "refused": True}).seen
        self.assertRegex(found["words"][0], r"^No reading: [0-9]+ bright spots found, and ")
        self.assertIn("whole wall", found["words"][1])
        self.assertEqual(found["marks"], 0)
        self.assertFalse(found["applyShown"])
        self.assertEqual(found["discardWords"], "Try another photo")

    def test_a_change_elsewhere_before_apply_is_said(self):
        state = {"ok": True, "editable": True, "pins": SHUFFLED, "revision": 123, "test": False, "snake": None}

        def mapping(line):
            words = line.decode().split()
            if words[1] == "set":
                return (200, json.dumps({"ok": False, "error": "mapping-conflict"}))
            if words[1] == "test":
                return (200, json.dumps({"ok": True}))
            return (200, json.dumps(state))
        with support.StandIn({**support.SOUND, "mapping": mapping}) as target:
            found = support.run("photomap", address=target.address, settings={"photo": {"pins": SHUFFLED}}, steps=[lambda: None]).seen
        self.assertIn("changed on the target", found["said"])

    def test_an_installation_whose_mapping_is_not_editable_offers_no_photo(self):
        with support.StandIn(support.SOUND) as target:
            found = support.run("photomap", address=target.address, settings={"unsupported": True}).seen
        self.assertTrue(found["hidden"])


if __name__ == "__main__":
    unittest.main()

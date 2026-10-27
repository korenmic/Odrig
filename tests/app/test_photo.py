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
UNLIT = [name for name in PHOTOS if "the-diagonal" not in name]
LIT = [name for name in PHOTOS if "the-diagonal" in name]
# What the owner's photo of the diagonal shows, read by eye from the stubs: position 1 at
# the top of the picture, snake 1 at its left.
FROM_THE_SIDE = [1, 17, 10, 8, 11, 18, 3, 7, 20, 14, 12, 13, 15, 16, 2, 6, 9, 5, 4, 19]


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

    def assert_read_back(self, name, dead=(), readings=1, turned=False):
        """The photo reads back the default pins, with `readings` readings for each of the
        two sides the wires may be at."""
        found = self.seen[name]
        self.assertNotIn("refused", found, found)
        self.assertGreaterEqual(found["points"], 2 * (20 - len(dead)), found)
        self.assertEqual(found["turned"], turned, found)
        self.assertEqual(found["readings"][0]["nulls"], len(dead), found)
        self.assertEqual(len(found["readings"]), 2 * readings, found)
        self.assertEqual([reading["side"] for reading in found["readings"]], ["left", "right"] * readings if turned else ["bottom"] * readings + ["top"] * readings, found)
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
        self.assertEqual([(reading["side"], reading["xEnd"], reading["yEnd"]) for reading in found["readings"]],
                         [("bottom", "right", None), ("bottom", "left", None), ("top", "right", None), ("top", "left", None)])
        self.assert_read_back("deadEnd", dead=[1], readings=2)
        self.assertEqual(found["readings"][1]["filled"], [{"position": 1, "snake": 10}])

    def test_a_wall_seen_from_the_side_reads_back_with_the_wires_at_the_left(self):
        self.assert_read_back("fromTheSide", turned=True)
        self.assertEqual(self.seen["fromTheSide"]["readings"][0]["filled"], [])

    def test_a_wall_seen_from_the_far_edge_reads_back_under_the_wires_at_the_top(self):
        found = self.seen["fromTheFarEdge"]
        self.assert_read_back("fromTheFarEdge")
        # The first reading, the wires at the bottom, reads the picture as it is: mirrored.
        self.assertNotEqual(found["positions"], list(range(1, 21)))

    def test_two_dead_lines_get_the_remaining_snakes_lowest_to_leftmost(self):
        self.assert_read_back("twoDead", dead=[5, 12])
        self.assertEqual(self.seen["twoDead"]["readings"][0]["filled"], [{"position": 5, "snake": 5}, {"position": 12, "snake": 12}])

    def test_a_cross_wired_position_read_with_the_box_off_gets_the_snake_that_remains(self):
        """The core places position 10's second and third pixels on its other two lines,
        in the rows of the snake 21 - s: the position that shows that snake keeps it, and
        position 10 gets the snake no other position shows, its own."""
        found = self.seen["crossedTen"]
        self.assertNotIn("refused", found, found)
        shuffled = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 47, 15, 16, 17, 18, 21, 1, 11]
        self.assertIsNone(found["positions"][9], found)
        self.assertEqual(found["readings"][0]["filled"], [{"position": 10, "snake": shows(shuffled, 10)}])
        self.assertEqual(found["pins"], DEFAULTS)

    def test_bright_spots_off_the_grid_are_ignored(self):
        self.assert_read_back("noise")
        self.assertGreaterEqual(self.seen["noise"]["ignored"], 1)

    def test_a_flash_photo_of_the_unlit_wall_is_refused_with_the_count(self):
        found = self.seen["flash"]
        self.assertTrue(found["refused"], found)
        self.assertEqual(found["why"], "many")
        self.assertGreater(found["found"], 100)

    def test_the_owners_photos_of_the_unlit_wall_are_refused(self):
        self.assertEqual(len(UNLIT), 4)
        for name in UNLIT:
            with self.subTest(name):
                found = self.seen["owner"][name]
                self.assertTrue(found["refused"], found)
                self.assertEqual(found["why"], "many", found)
                self.assertLessEqual(max(found["width"], found["height"]), 900)

    def test_the_owners_photos_of_the_diagonal_in_a_lit_room_are_read(self):
        """The wall lit by the room, every lens catching light, seen from the side with the
        wires at the left: the lit LEDs are told from the lenses and read."""
        self.assertEqual(len(LIT), 2)
        for name in LIT:
            with self.subTest(name):
                found = self.seen["owner"][name]
                self.assertFalse(found["refused"], found)
                self.assertTrue(found["turned"], found)
                self.assertEqual(found["side"], "left", found)
        # The screenshot of the photo: all 57 LEDs in view, each position found, all distinct.
        found = self.seen["owner"][LIT[0]]
        self.assertEqual(found["points"], 57, found)
        self.assertEqual(found["readings"], 2, found)
        self.assertEqual(found["positions"], FROM_THE_SIDE, found)
        self.assertEqual(found["distinct"], 20, found)
        # The same, darkened by the owner, which loses the dimmer LEDs: what is read agrees.
        found = self.seen["owner"][LIT[1]]
        self.assertGreaterEqual(found["points"], 35, found)
        for position, snake in enumerate(found["positions"], start=1):
            if snake is not None:
                self.assertEqual(snake, FROM_THE_SIDE[position - 1], (position, found))

    def test_a_png_file_is_read_and_scaled_like_a_jpeg(self):
        found = self.seen["png"]
        self.assertEqual((found["width"], found["height"]), (900, 563), found)
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
        self.assertEqual(found["choices"], [["Wires at the bottom", "true"], ["Wires at the top", "false"]])
        self.assertTrue(found["applyShown"])
        self.assertEqual(found["discardWords"], "Discard")
        # Position 1 has pin 1, which drives snake 19 under the shuffled pins.
        self.assertIn(f"Position 1 shows snake {shows(SHUFFLED, 1)}.", found["words"])
        self.assertNotIn("Every position shows its own snake.", found["words"])
        self.assertEqual(found["said"], "Saved from the photo.")
        self.assertTrue(found["applyDisabled"])
        self.assertTrue(found["otherShown"])
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
        found = support.run("photomap", address=f"127.0.0.1:{target.port}", settings={"photo": {"pins": SWAPPED, "dead": [1]}, "pick": "Wires at the bottom \u00b7 Position 1 dark"}, steps=[lambda: None]).seen
        self.assertEqual(found["choices"], [["Wires at the bottom \u00b7 Position 20 dark", "true"], ["Wires at the bottom \u00b7 Position 1 dark", "false"],
                                            ["Wires at the top \u00b7 Position 20 dark", "false"], ["Wires at the top \u00b7 Position 1 dark", "false"]])
        self.assertEqual(found["picked"], ["false", "true", "false", "false"])
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
        self.assertEqual(len(found["choices"]), 8)
        self.assertEqual(found["otherPicked"], ["false", "true"] + ["false"] * 6)
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

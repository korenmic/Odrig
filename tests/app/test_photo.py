import pathlib
import shutil
import tempfile
import unittest

from . import support

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


if __name__ == "__main__":
    unittest.main()

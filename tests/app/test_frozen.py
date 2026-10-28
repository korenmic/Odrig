import json
import pathlib
import tempfile
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

ROWS = 20
NO_ROOM = {"top": 0, "right": 0, "bottom": 0, "left": 0}
# A phone's status bar of 24 pixels and its line of gesture navigation of 16.
BARS = {"top": 24, "right": 0, "bottom": 16, "left": 0}
# Whole rows of the list: 80 pixels.
ROW = 80
# How far a box may stand off by the rounding of a browser.
SLACK = 0.5


class TheFrozenTop(unittest.TestCase):
    """The panel of what plays at the top of Animations, against the emulator with a long
    list, whose status reports the counts of the turn, so that the bar has its three lines."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        items = [{"id": number, "file": f"animation-{number:02d}.odrg"} for number in range(1, ROWS + 1)]
        files = {"mapping.json": core_support.mapping_texts()["legs-2"], "show.json": json.dumps({"version": 1, "brightness": 128, "items": items}),
                 **{item["file"]: core_support.clip(item["id"], 60, 6, (1000,) * 5) for item in items}}
        folder = emulator_support.installed(pathlib.Path(cls.work.name, "show"), files)
        cls.emulator = emulator_support.Emulator(folder)
        cls.addClassCleanup(cls.emulator.stop)
        cls.address = f"127.0.0.1:{cls.emulator.port}"

    def measured(self, size, room=NO_ROOM, **settings):
        return support.run("frozen", address=self.address, settings={"rows": ROWS, "room": room, **settings}, size=size).seen

    def assert_frozen(self, seen, where):
        top, scrolled = seen["top"], seen["scrolled"]
        self.assertTrue(top["frozen"], where)
        self.assertEqual(top["position"], "sticky", where)
        # It stays under the band of the phone's bar while the list scrolls under it.
        self.assertGreater(scrolled["scrolled"], 0, where)
        self.assertAlmostEqual(scrolled["top"], scrolled["band"], delta=SLACK, msg=where)
        self.assertTrue(scrolled["onTop"], where)
        self.assertEqual(scrolled["background"], "rgb(15, 22, 48)", where)
        self.assertGreaterEqual(scrolled["view"] - scrolled["nav"] - scrolled["bottom"], ROW - SLACK, where)
        # A field brought into view stops under it.
        self.assertTrue(scrolled["padding"].endswith("px"), where)
        self.assertAlmostEqual(float(scrolled["padding"][:-2]), scrolled["band"] + scrolled["height"], delta=SLACK, msg=where)

    def test_it_stays_at_the_top_of_a_tall_phone_with_four_rows_or_more_under_it(self):
        seen = self.measured((412, 915))
        self.assert_frozen(seen, "412 x 915")
        self.assertGreaterEqual(seen["scrolled"]["rowsUnder"], 4)

    def test_it_stays_at_the_top_of_a_phone_of_360_by_740_exactly_while_a_row_fits_under_it(self):
        for room in (NO_ROOM, BARS):
            with self.subTest(room=room):
                seen = self.measured((360, 740), room, threshold=True)
                top = seen["top"]
                left = top["view"] - top["band"] - top["height"] - top["nav"]
                self.assertEqual(top["frozen"], left >= ROW, left)
                self.assertTrue(seen["exact"]["frozen"])
                self.assertFalse(seen["short"]["frozen"])
                self.assertEqual(seen["short"]["position"], "static")
                if top["frozen"]:
                    self.assert_frozen(seen, f"360 x 740 with {room}")

    def test_it_does_not_stay_at_the_top_sideways_on_a_short_phone_or_with_the_keyboard_open(self):
        for size in ((740, 360), (320, 568)):
            with self.subTest(size=size):
                seen = self.measured(size)
                self.assertFalse(seen["top"]["frozen"])
                self.assertEqual(seen["scrolled"]["position"], "static")
                self.assertLess(seen["scrolled"]["top"], 0)
        seen = self.measured((412, 915), keyboard=True)
        self.assertTrue(seen["top"]["frozen"])
        self.assertTrue(seen["typing"]["typing"])
        self.assertFalse(seen["typing"]["frozen"])
        self.assertTrue(seen["afterTyping"]["frozen"])

    def test_a_row_moved_under_it_stops_below_it(self):
        seen = self.measured((412, 915), lift=12)
        self.assertTrue(seen["lifted"]["found"])
        self.assertGreaterEqual(seen["lifted"]["top"], seen["lifted"]["panelBottom"] - SLACK)


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from . import support

ROWS = 20
LISTED = (200, json.dumps({"ok": True, "items": [{"id": number, "file": f"animation-{number}.odrg", "bytes": 1000 * number} for number in range(1, ROWS + 1)], "next": None}) + "\n")
SPACE = (200, '{"ok":true,"free":8372224,"total":10354688,"animations":20}\n')
TARGET = {"status": support.PLAYING, "list": LISTED, "space": SPACE}
MIDNIGHT = "rgb(5, 8, 22)"
TABS = ["Animations", "Upload", "Settings", "Target"]
# How far a box may stand off by the rounding of a browser.
SLACK = 0.5


class Layout:
    """The page measured with the room of the bars of one phone, held one way."""

    size = None
    room = None

    @classmethod
    def setUpClass(cls):
        target = support.StandIn(TARGET).__enter__()
        cls.addClassCleanup(target.__exit__, None, None, None)
        cls.seen = support.run("bars", address=target.address, settings={"rows": ROWS, "room": cls.room}, size=cls.size).seen

    def area(self, measured):
        """The area the room leaves: left, top, right, bottom."""
        return (self.room["left"], self.room["top"], measured["width"] - self.room["right"], measured["height"] - self.room["bottom"])

    def inside(self, thing, measured, where, vertically=True):
        left, top, right, bottom = self.area(measured)
        self.assertGreaterEqual(thing["left"], left - SLACK, f"{where}: {thing.get('what')} reaches into the room at the left")
        self.assertLessEqual(thing["right"], right + SLACK, f"{where}: {thing.get('what')} reaches into the room at the right")
        if vertically:
            self.assertGreaterEqual(thing["top"], top - SLACK, f"{where}: {thing.get('what')} reaches into the room at the top")
            self.assertLessEqual(thing["bottom"], bottom + SLACK, f"{where}: {thing.get('what')} reaches into the room at the bottom")

    def screens(self):
        for name in ("animations", "animationsEnd", "uploadTop", "uploadEnd", "message"):
            yield name, self.seen[name]

    def test_the_tabs_lie_wholly_above_the_room_at_the_bottom_and_clear_of_the_sides(self):
        for name, measured in self.screens():
            self.assertEqual([tab["what"] for tab in measured["tabs"]], TABS, name)
            for tab in measured["tabs"]:
                self.inside(tab, measured, name)

    def test_the_tabs_dark_reaches_the_bottom_and_the_sides(self):
        for name, measured in self.screens():
            nav = measured["nav"]
            self.assertEqual((nav["left"], nav["right"], nav["bottom"]), (0, measured["width"], measured["height"]), name)
            self.assertEqual(nav["colour"], "rgba(8, 12, 32, 0.97)", name)

    def test_the_heading_lies_below_the_room_at_the_top(self):
        for name in ("animations", "uploadTop"):
            measured = self.seen[name]
            self.assertEqual(measured["scrolled"], 0, name)
            self.assertGreaterEqual(min(thing["top"] for thing in measured["things"]), self.room["top"] - SLACK, name)

    def test_everything_of_a_screen_is_clear_of_the_room_at_the_sides(self):
        for name, measured in self.screens():
            self.assertGreater(len(measured["things"]), 3, name)
            for thing in measured["things"]:
                self.inside(thing, measured, name, vertically=False)

    def test_what_scrolls_up_goes_under_a_band_of_midnight_in_the_room_at_the_top(self):
        for name in ("animationsEnd",):
            measured = self.seen[name]
            self.assertGreater(measured["scrolled"], self.room["top"], name)
            if self.room["top"] > 0:
                self.assertEqual(set(measured["top"]["found"]), {"body"}, name)
            band = measured["top"]["band"]
            self.assertEqual((band["height"], band["colour"], band["position"]), (self.room["top"], MIDNIGHT, "fixed"), name)

    def test_the_last_line_of_each_list_can_be_scrolled_above_the_tabs(self):
        for name in ("animationsEnd", "uploadEnd"):
            measured = self.seen[name]
            tabs_top = min(tab["top"] for tab in measured["tabs"])
            self.assertLessEqual(measured["last"]["bottom"], tabs_top + SLACK, name)
            self.inside(measured["last"], measured, name)

    def test_a_message_lies_above_the_tabs_and_clear_of_the_sides(self):
        measured = self.seen["message"]
        self.inside(measured["message"], measured, "message")
        self.assertLessEqual(measured["message"]["bottom"], min(tab["top"] for tab in measured["tabs"]) + SLACK)

    def test_with_the_keyboard_open_the_tabs_are_hidden_and_the_field_is_in_view(self):
        typing = self.seen["typing"]
        self.assertTrue(typing["focus"])
        self.assertLess(typing["height"], self.size[1] * 0.75)
        self.assertEqual((typing["tabs"], typing["nav"]), ([], None))
        self.inside(typing["field"], typing, "typing")

    def test_a_field_with_the_focus_and_no_keyboard_keeps_the_tabs_and_they_come_back_after(self):
        for name in ("focused", "after"):
            self.assertEqual([tab["what"] for tab in self.seen[name]["tabs"]], TABS, name)

    def test_without_the_room_the_page_is_as_before(self):
        plain = self.seen["plain"]
        self.assertEqual(plain["padding"], [8, 12, 104, 12])
        self.assertEqual(plain["nav"]["bottom"], plain["height"])
        self.assertEqual(min(tab["bottom"] for tab in plain["tabs"]), plain["height"] - 8)
        self.assertEqual(plain["top"]["band"]["height"], 0)


class TheAndroidShell(unittest.TestCase):
    def test_it_gives_the_page_the_room_and_has_light_icons_on_black(self):
        config = json.loads((support.APP / "capacitor.config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["plugins"]["SystemBars"], {"insetsHandling": "css", "style": "DARK", "initialViewportFitValueHint": "cover"})
        self.assertEqual(config["android"]["backgroundColor"], "#000000")
        styles = (support.APP / "android" / "app" / "src" / "main" / "res" / "values" / "styles.xml").read_text(encoding="utf-8")
        theme = styles.split('<style name="AppTheme.NoActionBar"')[1].split("</style>")[0]
        self.assertIn('<item name="android:windowBackground">@android:color/black</item>', theme)
        self.assertIn('content="width=device-width, initial-scale=1, viewport-fit=cover"', (support.WWW / "index.html").read_text(encoding="utf-8"))


class ThreeButtonsUpright(Layout, unittest.TestCase):
    size = (360, 740)
    room = {"top": 24, "right": 0, "bottom": 48, "left": 0}


class GesturesUpright(Layout, unittest.TestCase):
    size = (360, 740)
    room = {"top": 24, "right": 0, "bottom": 16, "left": 0}


class Sideways(Layout, unittest.TestCase):
    size = (740, 360)
    room = {"top": 24, "right": 48, "bottom": 0, "left": 32}


if __name__ == "__main__":
    unittest.main()

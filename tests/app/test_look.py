import json
import pathlib
import re
import tempfile
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

LONGEST_NAME = "a-file-name-of-32-characters.odrg"[:27] + ".odrg"
BLACK = "rgb(0, 0, 0)"


def rgb(colour):
    return [int(number) for number in re.findall(r"[0-9]+", colour)[:3]]


def luminance(colour):
    parts = []
    for value in rgb(colour):
        value /= 255
        parts.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]


def contrast(first, second):
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def apart(first, second):
    """How far two boxes are from each other, in pixels; below 0 when they overlap."""
    across = max(second["left"] - first["right"], first["left"] - second["right"])
    down = max(second["top"] - first["bottom"], first["top"] - second["bottom"])
    return max(across, down)


class Look(unittest.TestCase):
    """The three screens, a message and a question, measured at the width of a phone and
    at a narrow one, with a show whose file names are as long as a name can be."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        items = [{"id": 1, "file": "hello.odrg"}, {"id": 65535, "file": LONGEST_NAME}, {"id": 3, "file": "third.odrg"}]
        files = {item["file"]: core_support.clip(item["id"], 60, 6) for item in items}
        show = {"version": 1, "brightness": 128, "items": items}
        folder = emulator_support.installed(pathlib.Path(cls.work.name, "show"), {"mapping.json": core_support.mapping_texts()["legs-2"], "show.json": json.dumps(show), **files})
        cls.emulator = emulator_support.Emulator(folder)
        cls.addClassCleanup(cls.emulator.stop)
        address = f"127.0.0.1:{cls.emulator.port}"
        cls.measured = {size: support.run("look", address=address, settings={"rows": 3}, size=size).seen for size in ((360, 740), (320, 640))}

    def each(self):
        for size, screens in self.measured.items():
            for name, screen in screens.items():
                yield f"{size[0]} wide, {name}", size, screen

    def test_the_file_name_of_the_test_is_as_long_as_a_name_can_be(self):
        self.assertEqual(len(LONGEST_NAME), 32)
        self.assertEqual(self.measured[(360, 740)]["show"]["width"], 360)
        self.assertEqual(self.measured[(320, 640)]["show"]["width"], 320)

    def test_every_button_field_and_slider_is_56_pixels_high_or_more(self):
        for where, size, screen in self.each():
            self.assertGreaterEqual(len(screen["controls"]), 5, where)
            for control in screen["controls"]:
                self.assertGreaterEqual(control["bottom"] - control["top"], 56 - 0.01, f"{where}: {control['what']}")
                self.assertGreaterEqual(control["right"] - control["left"], 56 - 0.01, f"{where}: {control['what']}")

    def test_every_control_is_8_pixels_from_the_next(self):
        for where, size, screen in self.each():
            for group in ("screen", "nav", "message", "question"):
                controls = [control for control in screen["controls"] if control["group"] == group]
                for position, first in enumerate(controls):
                    for second in controls[position + 1:]:
                        self.assertGreaterEqual(apart(first, second), 8 - 0.01, f"{where}: {first['what']} and {second['what']}")

    def test_the_three_screen_buttons_lie_along_the_bottom_edge_each_a_third_of_the_width(self):
        for where, size, screen in self.each():
            buttons = [control for control in screen["controls"] if control["group"] == "nav"]
            self.assertEqual([button["what"] for button in buttons], ["to-show", "to-storage", "to-target"], where)
            widths = [button["right"] - button["left"] for button in buttons]
            self.assertAlmostEqual(widths[0], widths[1], delta=1, msg=where)
            self.assertAlmostEqual(widths[1], widths[2], delta=1, msg=where)
            # The edges and the gaps take 8 pixels each.
            self.assertAlmostEqual(sum(widths), size[0] - 4 * 8, delta=1, msg=where)
            self.assertAlmostEqual(screen["nav"]["bottom"], screen["height"], delta=1, msg=where)
            # The last control of a long screen can be moved clear of them.
            self.assertGreaterEqual(screen["spaceBelow"], screen["nav"]["bottom"] - screen["nav"]["top"] + 8, where)

    def test_a_message_and_a_question_lie_above_the_screen_buttons(self):
        for size, screens in self.measured.items():
            self.assertIsNone(screens["show"]["message"])
            self.assertIsNone(screens["storage"]["question"])
            for name, what in (("withMessage", "message"), ("withQuestion", "question")):
                placed, nav = screens[name][what], screens[name]["nav"]
                self.assertGreaterEqual(nav["top"] - placed["bottom"], 8 - 0.01, (size, what))
                self.assertGreaterEqual(placed["left"], 8 - 0.01, (size, what))
                self.assertLessEqual(placed["right"], size[0] - 8 + 0.01, (size, what))

    def test_the_background_is_black_and_no_area_is_bright(self):
        for where, size, screen in self.each():
            self.assertIn(BLACK, screen["back"], where)
            for text in screen["texts"]:
                self.assertLess(luminance(text["behind"]), 0.02, f"{where}: behind {text['what']} is {text['behind']}")

    def test_every_text_has_a_contrast_of_7_to_1_or_more(self):
        colours = set()
        for where, size, screen in self.each():
            self.assertGreaterEqual(len(screen["texts"]), 8, where)
            for text in screen["texts"]:
                colours.add(tuple(rgb(text["colour"])))
                self.assertGreaterEqual(contrast(text["colour"], text["behind"]), 7, f"{where}: {text['what']} is {text['colour']} on {text['behind']}")
        self.assertEqual(colours, {(0xE8, 0xE8, 0xE8), (0xB0, 0xB0, 0xB0), (0xFF, 0xB0, 0x00)})

    def test_the_sizes_of_the_letters(self):
        for where, size, screen in self.each():
            sizes = {text["what"]: text["size"] for text in screen["texts"]}
            self.assertEqual({size for what, size in sizes.items() if what in ("to-show", "to-storage", "to-target", "use", "board", "on", "off", "play-all", "confirm-yes", "confirm-no")}, {20}, where)
            self.assertGreaterEqual(min(sizes.values()), 14, where)
        show = {text["what"]: text["size"] for text in self.measured[(360, 740)]["show"]["texts"]}
        self.assertEqual((show["power"], show["brightness"], show["playing"]), (28, 18, 18))

    def test_nothing_scrolls_sideways(self):
        for where, size, screen in self.each():
            self.assertLessEqual(screen["scrollWidth"], screen["width"], where)
            for control in screen["controls"]:
                self.assertGreaterEqual(control["left"], 0, f"{where}: {control['what']}")
                self.assertLessEqual(control["right"], size[0] + 0.01, f"{where}: {control['what']}")


class Touch(unittest.TestCase):
    def test_nothing_depends_on_a_pointer_hovering_a_long_press_or_a_swipe(self):
        style = (support.WWW / "style.css").read_text(encoding="utf-8")
        self.assertNotRegex(style, r":hover|:active|@media\s*\(\s*(hover|pointer)")
        listened = set()
        for path in sorted(support.WWW.rglob("*.js")):
            text = path.read_text(encoding="utf-8")
            listened |= set(re.findall(r"""addEventListener\(\s*["']([a-z]+)["']""", text))
            self.assertNotRegex(text, r"\bon(mouse|touch|pointer|contextmenu)[a-z]*\s*=", path.name)
        self.assertEqual(listened, {"click", "input", "change", "visibilitychange", "popstate", "contextmenu"})
        # A long press or a right click has one listener, which stops its menu outside
        # the fields and does nothing else.
        start = (support.WWW / "main.js").read_text(encoding="utf-8")
        listener = start.split('document.addEventListener("contextmenu", (event) => {\n')[1].split("\n});\n")[0]
        self.assertEqual(listener.split(), 'if (!(event.target instanceof Element && event.target.matches(":read-write"))) { event.preventDefault(); }'.split())
        # The media of a conversion tell when they are loaded or sought, and when they
        # cannot be read.
        conversion = (support.WWW / "convert.js").read_text(encoding="utf-8")
        awaited = {name for names in re.findall(r"either\(\w+, \[([^\]]*)\]\)", conversion) for name in re.findall(r'"([a-z]+)"', names)}
        self.assertEqual(awaited, {"loadedmetadata", "loadeddata", "seeked"})
        self.assertIn('for (const name of [...names, "error"])', conversion)


class Back(unittest.TestCase):
    def test_from_the_target_screen_back_goes_to_the_show_screen_which_is_the_apps_first_entry(self):
        emulator = entered(self, emulator_support.Emulator(entered(self, emulator_support.demo_show())))
        found = support.run("back", address=f"127.0.0.1:{emulator.port}", settings={"answers": True, "rows": 2}).seen
        entries = found["first"]["entries"]
        # After the first answer the show screen is where the app begins: going back
        # from it leaves the app.
        self.assertEqual((found["first"]["shown"], found["first"]["state"]), ("show", {"screen": "show", "depth": 0}))
        self.assertEqual((found["second"]["shown"], found["second"]["state"], found["second"]["entries"]), ("target", {"screen": "target", "depth": 1}, entries + 1))
        self.assertEqual((found["back"]["shown"], found["back"]["state"]), ("show", {"screen": "show", "depth": 0}))
        # The button `Show` goes back as the gesture does: no entries pile up.
        for look in found["toggled"]:
            self.assertEqual((look["shown"], look["state"], look["entries"]), ("show", {"screen": "show", "depth": 0}, entries + 1))
        # The storage screen lies on top of the show screen as the target screen does,
        # and one takes the other's place there: back goes to the show screen.
        self.assertEqual((found["storage"]["shown"], found["storage"]["state"], found["storage"]["entries"]), ("storage", {"screen": "storage", "depth": 1}, entries + 1))
        self.assertEqual((found["across"]["shown"], found["across"]["state"], found["across"]["entries"]), ("target", {"screen": "target", "depth": 1}, entries + 1))
        self.assertEqual((found["home"]["shown"], found["home"]["state"]), ("show", {"screen": "show", "depth": 0}))

    def test_while_the_target_has_not_answered_the_target_screen_is_the_apps_first_entry(self):
        found = support.run("back", address=f"127.0.0.1:{support.free_port()}", settings={"answers": False}).seen
        self.assertEqual((found["unanswered"]["shown"], found["unanswered"]["state"]), ("target", {"screen": "target", "depth": 0}))
        self.assertEqual(found["unanswered"]["entries"], found["began"]["entries"])


if __name__ == "__main__":
    unittest.main()

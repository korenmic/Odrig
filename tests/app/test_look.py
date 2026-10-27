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
# The sizes the screens are measured at: a phone upright, a narrow one, and a phone held
# sideways.
SIZES = ((360, 740), (320, 640), (740, 360))
# The midnight of the page's background.
MIDNIGHT = "rgb(5, 8, 22)"


def rgb(colour):
    return [int(float(number)) for number in re.findall(r"[0-9.]+", colour)[:3]]


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
    """The four screens, a row's menu, a message and a question, measured upright at the
    width of a phone and at a narrow one, and sideways, with a show whose file names are as
    long as a name can be."""

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
        # The row of the longest name is ignored, so that its note stands in it.
        assert json.loads(cls.emulator.command("ignore 65535 1"))["ok"]
        address = f"127.0.0.1:{cls.emulator.port}"
        cls.measured = {size: support.run("look", address=address, settings={"rows": 3}, size=size).seen for size in SIZES}

    def each(self):
        for size, screens in self.measured.items():
            for name, screen in screens.items():
                yield f"{size[0]} wide, {name}", size, screen

    def test_the_file_name_of_the_test_is_as_long_as_a_name_can_be(self):
        self.assertEqual(len(LONGEST_NAME), 32)
        self.assertEqual([self.measured[size]["animations"]["width"] for size in SIZES], [size[0] for size in SIZES])

    def test_every_control_is_44_pixels_high_and_wide_or_more_and_the_main_ones_48_high(self):
        for where, size, screen in self.each():
            self.assertGreaterEqual(len(screen["controls"]), 5, where)
            for control in screen["controls"]:
                self.assertGreaterEqual(control["bottom"] - control["top"], 44 - 0.01, f"{where}: {control['what']}")
                self.assertGreaterEqual(control["right"] - control["left"], 44 - 0.01, f"{where}: {control['what']}")
                # A row's own controls, its Play, its menu and its checkbox, are 44 high.
                if control["group"] in ("screen", "nav") and not control["what"].startswith(("Actions for ", "Play ", "Select animation ")):
                    self.assertGreaterEqual(control["bottom"] - control["top"], 48 - 0.01, f"{where}: {control['what']}")

    def test_every_control_is_8_pixels_from_the_next(self):
        for where, size, screen in self.each():
            for group in ("screen", "nav", "message", "question", "menu"):
                controls = [control for control in screen["controls"] if control["group"] == group]
                for position, first in enumerate(controls):
                    for second in controls[position + 1:]:
                        self.assertGreaterEqual(apart(first, second), 8 - 0.01, f"{where}: {first['what']} and {second['what']}")

    def test_the_four_tabs_lie_along_the_bottom_edge_at_equal_width(self):
        for where, size, screen in self.each():
            buttons = [control for control in screen["controls"] if control["group"] == "nav"]
            self.assertEqual([button["what"] for button in buttons], ["to-animations", "to-upload", "to-settings", "to-target"], where)
            widths = [button["right"] - button["left"] for button in buttons]
            for width in widths[1:]:
                self.assertAlmostEqual(width, widths[0], delta=1, msg=where)
            # The edges and the gaps take 8 pixels each.
            self.assertAlmostEqual(sum(widths), size[0] - 5 * 8, delta=1, msg=where)
            self.assertAlmostEqual(screen["nav"]["bottom"], screen["height"], delta=1, msg=where)
            # The last control of a long screen can be moved clear of them.
            self.assertGreaterEqual(screen["spaceBelow"], screen["nav"]["bottom"] - screen["nav"]["top"] + 8, where)

    def test_a_menu_a_message_and_a_question_lie_above_the_tabs(self):
        for size, screens in self.measured.items():
            self.assertIsNone(screens["animations"]["message"])
            self.assertIsNone(screens["animations"]["menu"])
            for name, what in (("withMessage", "message"), ("withQuestion", "question"), ("withMenu", "menu")):
                placed, nav = screens[name][what], screens[name]["nav"]
                self.assertGreaterEqual(nav["top"] - placed["bottom"], 8 - 0.01, (size, what))
                self.assertGreaterEqual(placed["left"], 8 - 0.01, (size, what))
                self.assertLessEqual(placed["right"], size[0] - 8 + 0.01, (size, what))

    def test_the_background_is_midnight_and_the_panels_are_dark(self):
        for where, size, screen in self.each():
            self.assertIn(MIDNIGHT, screen["back"], where)
            self.assertGreaterEqual(len(screen["panels"]), 1, where)
            for panel in screen["panels"]:
                self.assertLess(luminance(panel), 0.02, f"{where}: a panel is {panel}")

    def test_every_text_has_a_contrast_of_7_to_1_or_more(self):
        for where, size, screen in self.each():
            self.assertGreaterEqual(len(screen["texts"]), 8, where)
            for text in screen["texts"]:
                if text["stale"]:
                    continue
                self.assertGreaterEqual(contrast(text["colour"], text["behind"]), 7, f"{where}: {text['what']} is {text['colour']} on {text['behind']}")

    def test_the_sizes_of_the_letters(self):
        for where, size, screen in self.each():
            self.assertGreaterEqual(min(text["size"] for text in screen["texts"]), 14, where)
            nav = {control["what"] for control in screen["controls"] if control["group"] == "nav"}
            self.assertEqual(len(nav), 4, where)

    def test_the_brightness_field_stands_on_one_line_with_its_label_and_the_slider_under_it(self):
        for size in SIZES:
            where = f"{size[0]} wide"
            level = self.measured[size]["animations"]["level"]
            label, field, slider = level["label"], level["field"], level["slider"]
            # One line: the label's middle within the field's height, 8 pixels before it, and
            # the field at the panel's right edge.
            self.assertLessEqual(field["top"], (label["top"] + label["bottom"]) / 2, where)
            self.assertGreaterEqual(field["bottom"], (label["top"] + label["bottom"]) / 2, where)
            self.assertAlmostEqual(field["left"] - label["right"], 8, delta=0.5, msg=where)
            self.assertAlmostEqual(field["right"], level["right"], delta=0.5, msg=where)
            # About 5.5 em of the field's letters, 44 pixels wide and 48 high or more, with
            # digits of one width.
            self.assertAlmostEqual(field["right"] - field["left"], 5.5 * level["letters"], delta=1, msg=where)
            self.assertGreaterEqual(field["right"] - field["left"], 44, where)
            self.assertGreaterEqual(field["bottom"] - field["top"], 48 - 0.01, where)
            self.assertEqual(level["digits"], "tabular-nums", where)
            # The slider 8 pixels under it, across the panel.
            self.assertAlmostEqual(slider["top"] - field["bottom"], 8, delta=0.5, msg=where)
            self.assertAlmostEqual(slider["left"], level["left"], delta=0.5, msg=where)
            self.assertAlmostEqual(slider["right"], level["right"], delta=0.5, msg=where)

    def test_nothing_scrolls_sideways(self):
        for where, size, screen in self.each():
            self.assertLessEqual(screen["scrollWidth"], screen["width"], where)
            for control in screen["controls"]:
                self.assertGreaterEqual(control["left"], 0, f"{where}: {control['what']}")
                self.assertLessEqual(control["right"], size[0] + 0.01, f"{where}: {control['what']}")


class Touch(unittest.TestCase):
    def test_nothing_depends_on_a_pointer_hovering_or_a_swipe(self):
        style = (support.WWW / "style.css").read_text(encoding="utf-8")
        self.assertNotRegex(style, r":hover|:active|@media\s*\(\s*(hover|pointer)")
        listened = set()
        for path in sorted(support.WWW.rglob("*.js")):
            text = path.read_text(encoding="utf-8")
            listened |= set(re.findall(r"""addEventListener\(\s*["']([a-z]+)["']""", text))
            self.assertNotRegex(text, r"\bon(mouse|touch|pointer|contextmenu)[a-z]*\s*=", path.name)
        self.assertEqual(listened, {"click", "input", "change", "visibilitychange", "popstate", "contextmenu", "resize", "focusin", "focusout", "keydown", "scroll",
                                    "pointerdown", "pointermove", "pointerup", "pointercancel", "touchmove"})
        # A long press or a drag is only ever the lifting of a row of the playlist, which Move
        # up and Move down in the row's menu do as well, or of a pin of the mapping, which the
        # arrow keys on its handle move as well.
        reorder = (support.WWW / "screens" / "reorder.js").read_text(encoding="utf-8")
        self.assertIn('label: "Move up"', reorder)
        self.assertIn('label: "Move down"', reorder)
        mapping = (support.WWW / "screens" / "mapping.js").read_text(encoding="utf-8")
        self.assertIn('"ArrowUp"', mapping)
        self.assertIn('"ArrowDown"', mapping)
        self.assertEqual({name.name for name in support.WWW.rglob("*.js") if "pointerdown" in name.read_text(encoding="utf-8")}, {"reorder.js", "mapping.js"})
        # A right click has one listener, which stops its menu outside the fields and does
        # nothing else.
        start = (support.WWW / "main.js").read_text(encoding="utf-8")
        listener = start.split('document.addEventListener("contextmenu", (event) => {\n')[1].split("\n});\n")[0]
        self.assertEqual(listener.split(), "if (!isField(event.target)) { event.preventDefault(); }".split())
        field = start.split("function isField(element) {\n")[1].split("\n}\n")[0]
        self.assertEqual(field.split(), 'return element instanceof Element && element.matches(":read-write");'.split())
        # The media of a conversion tell when they are loaded or sought, and when they
        # cannot be read.
        conversion = (support.WWW / "convert.js").read_text(encoding="utf-8")
        awaited = {name for names in re.findall(r"either\(\w+, \[([^\]]*)\]\)", conversion) for name in re.findall(r'"([a-z]+)"', names)}
        self.assertEqual(awaited, {"loadedmetadata", "loadeddata", "seeked"})
        self.assertIn('for (const name of [...names, "error"])', conversion)


class Back(unittest.TestCase):
    def test_from_the_target_screen_back_goes_to_animations_which_is_the_apps_first_entry(self):
        emulator = entered(self, emulator_support.Emulator(entered(self, emulator_support.demo_show())))
        found = support.run("back", address=f"127.0.0.1:{emulator.port}", settings={"answers": True, "rows": 2}).seen
        entries = found["first"]["entries"]
        # After the first answer Animations is where the app begins: going back from it
        # leaves the app.
        self.assertEqual((found["first"]["shown"], found["first"]["state"]), ("animations", {"screen": "animations", "depth": 0}))
        self.assertEqual((found["second"]["shown"], found["second"]["state"], found["second"]["entries"]), ("target", {"screen": "target", "depth": 1}, entries + 1))
        self.assertEqual((found["back"]["shown"], found["back"]["state"]), ("animations", {"screen": "animations", "depth": 0}))
        # The button `Animations` goes back as the gesture does: no entries pile up.
        for look in found["toggled"]:
            self.assertEqual((look["shown"], look["state"], look["entries"]), ("animations", {"screen": "animations", "depth": 0}, entries + 1))
        # Upload and Settings lie on top of Animations as the target screen does, and one
        # takes the other's place there: back goes to Animations. So does `Add animation`.
        self.assertEqual((found["upload"]["shown"], found["upload"]["state"], found["upload"]["entries"]), ("upload", {"screen": "upload", "depth": 1}, entries + 1))
        self.assertEqual((found["settings"]["shown"], found["settings"]["state"], found["settings"]["entries"]), ("settings", {"screen": "settings", "depth": 1}, entries + 1))
        self.assertEqual((found["across"]["shown"], found["across"]["state"], found["across"]["entries"]), ("target", {"screen": "target", "depth": 1}, entries + 1))
        self.assertEqual((found["home"]["shown"], found["home"]["state"]), ("animations", {"screen": "animations", "depth": 0}))
        self.assertEqual((found["added"]["shown"], found["added"]["state"], found["added"]["entries"]), ("upload", {"screen": "upload", "depth": 1}, entries + 1))

    def test_while_the_target_has_not_answered_the_target_screen_is_the_apps_first_entry(self):
        found = support.run("back", address=f"127.0.0.1:{support.free_port()}", settings={"answers": False}).seen
        self.assertEqual((found["unanswered"]["shown"], found["unanswered"]["state"]), ("target", {"screen": "target", "depth": 0}))
        self.assertEqual(found["unanswered"]["entries"], found["began"]["entries"])


if __name__ == "__main__":
    unittest.main()

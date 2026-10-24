import re
import unittest

from . import support
from .test_storage import SPACE

# The kinds of `input` that take typing. Such an input is a field unless it is read only
# or switched off, and so is a text area.
TYPED = {"text", "number", "search", "url", "email", "tel", "password", "date", "time", "datetime-local", "month", "week"}
# The fields of the page: the address, and the start and the length of a part of a video.
FIELDS = ["#start", "#length", "#text-words", "#text-speed", "#text-pause", "#address"]
LOOKS = ("animations", "upload", "question", "target", "message")


def is_field(element):
    typed = element["tag"] == "textarea" or (element["tag"] == "input" and element["kind"] in TYPED)
    return typed and not element["readOnly"]


def declarations(style, selector):
    """The declarations of the rules of a style sheet that have this selector alone."""
    found = []
    style = re.sub(r"(?s)/\*.*?\*/", "", style)
    for selectors, body in re.findall(r"(?ms)^([^{}]+)\{([^}]*)\}", style):
        if [part.strip() for part in selectors.split(",")] == [selector]:
            found += [" ".join(line.strip().rstrip(";").split()) for line in body.split(";") if line.strip()]
    return found


class ALongPressOrARightClick(unittest.TestCase):
    """Where a long press or a right click marks text and opens its menu: in a field one
    types into, and nowhere else."""

    @classmethod
    def setUpClass(cls):
        target = support.StandIn({"status": support.PLAYING, "list": support.LISTED, "space": SPACE})
        target.__enter__()
        cls.addClassCleanup(target.__exit__, None, None, None)
        cls.seen = support.run("marks", address=target.address, settings={"rows": 2}).seen

    def test_outside_the_fields_no_text_can_be_marked_and_no_menu_opens(self):
        for look in LOOKS:
            elements = self.seen[look]["elements"]
            self.assertGreater(len(elements), 100, look)
            for element in elements:
                if not is_field(element):
                    self.assertEqual((element["marks"], element["stopped"]), ("none", True), f"{look}: {element['what']}")
        tags = {element["tag"] for element in self.seen["upload"]["elements"]}
        self.assertLessEqual({"html", "body", "main", "section", "h1", "p", "label", "button", "span", "div", "nav", "canvas", "input"}, tags)
        kinds = {element["kind"] for element in self.seen["animations"]["elements"] if element["tag"] == "input"}
        self.assertLessEqual({"range", "file"}, kinds)
        rows = [element["what"] for element in self.seen["animations"]["elements"] if element["what"].startswith("#animations-list > div.row")]
        self.assertGreaterEqual(len(rows), 2 * 6)

    def test_in_every_field_text_can_be_marked_and_the_menu_opens(self):
        for look in LOOKS:
            fields = [element for element in self.seen[look]["elements"] if is_field(element)]
            self.assertEqual([field["what"] for field in fields], FIELDS, look)
            for field in fields:
                self.assertEqual((field["marks"], field["stopped"]), ("text", False), f"{look}: {field['what']}")

    def test_select_all_marks_nothing_on_any_screen(self):
        for look in LOOKS:
            self.assertEqual(self.seen[look]["marked"], "", look)

    def test_a_button_whose_menu_was_stopped_still_works_by_a_press(self):
        # The scenario pressed `Upload` after the stopped right click, and Upload came.
        self.assertTrue(self.seen["stoppedBeforePress"])
        self.assertIn("upload", self.seen)

    def test_what_is_made_later_is_a_field_by_its_kind(self):
        made = self.seen["made"]
        self.assertEqual(sorted(made), sorted(["text", "number", "untyped", "area", "readOnly", "slider", "paragraph", "button"]))
        for name in ("text", "number", "untyped", "area"):
            self.assertTrue(is_field(made[name]), name)
            self.assertEqual((made[name]["marks"], made[name]["stopped"]), ("text", False), name)
        for name in ("readOnly", "slider", "paragraph", "button"):
            self.assertFalse(is_field(made[name]), name)
            self.assertEqual((made[name]["marks"], made[name]["stopped"]), ("none", True), name)

    def test_the_page_for_an_old_web_view_marks_nothing(self):
        old = self.seen["old"]
        self.assertEqual(old["marked"], "")
        self.assertIn("p", {element["tag"] for element in old["elements"]})
        for element in old["elements"]:
            self.assertEqual(element["marks"], "none", element["what"])


class TheRule(unittest.TestCase):
    def test_it_is_stated_once_in_the_style_sheet_by_the_kind_of_a_field(self):
        style = (support.WWW / "style.css").read_text(encoding="utf-8")
        everything = declarations(style, "*")
        for declaration in ("-webkit-user-select: none", "user-select: none", "-webkit-touch-callout: none"):
            self.assertIn(declaration, everything)
        self.assertEqual(declarations(style, ":read-write"), ["-webkit-user-select: text", "user-select: text", "-webkit-touch-callout: default"])
        self.assertEqual(len(re.findall(r"user-select:", style)), 4)
        self.assertEqual(len(re.findall(r"-webkit-touch-callout:", style)), 2)

    def test_it_is_stated_once_in_the_scripts_by_the_same_kind(self):
        scripts = {path.name: path.read_text(encoding="utf-8") for path in support.WWW.rglob("*.js")}
        self.assertEqual({name for name, text in scripts.items() if '"contextmenu"' in text}, {"main.js"})
        self.assertEqual(sum(text.count(":read-write") for text in scripts.values()), 1)
        self.assertEqual(scripts["main.js"].count('"contextmenu"'), 1)

    def test_the_page_for_an_old_web_view_has_it_in_its_own_style(self):
        old = (support.WWW / "old.html").read_text(encoding="utf-8")
        style = old.split("<style>")[1].split("</style>")[0]
        for declaration in ("-webkit-user-select: none", "user-select: none", "-webkit-touch-callout: none"):
            self.assertIn(declaration, declarations(style, "*"))


if __name__ == "__main__":
    unittest.main()

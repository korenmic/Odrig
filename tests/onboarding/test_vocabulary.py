import re
import unittest

from . import support

PAGE = "agent/vocabulary.md"

GROUPS = ("The installation", "What is played", "The programs", "How the work is organised")

# The words a newcomer meets on the first day, in the order the page explains them.
WORDS = (
    "board", "pin", "canvas", "strip", "leg", "snake", "mapping", "bench build", "target",
    "animation", "frame", "refresh", "source", "JSON frames", "ODRG", "generator", "show", "item", "cycle", "playlist", "turn", "installed file set", "command",
    "converter", "Python library", "core", "host", "emulator", "firmware", "command tool", "operators' app",
    "owner", "seed", "spec", "task", "drift",
)


def entries(text):
    """`(word, definition)` for every entry of the page, in order, the definition on one line."""
    found = re.findall(r"(?ms)^- \*\*(.+?)\*\*: (.+?)(?=^- \*\*|^## |\Z)", text)
    return [(word, " ".join(definition.split())) for word, definition in found]


class Vocabulary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = support.read(PAGE)
        cls.entries = entries(cls.text)

    def test_it_is_one_of_the_pages(self):
        self.assertIn(PAGE, support.PAGES)

    def test_it_has_its_four_groups(self):
        self.assertEqual(tuple(re.findall(r"(?m)^## (.+)$", self.text)), GROUPS)

    def test_every_word_has_one_entry_and_the_entries_are_in_the_order_of_reading(self):
        self.assertEqual(tuple(word for word, _ in self.entries), WORDS)

    def test_a_definition_is_one_to_four_sentences(self):
        for word, definition in self.entries:
            with self.subTest(word=word):
                sentences = [sentence for sentence in re.split(r"(?<=[.])\s+(?=[A-Z`\[])", definition) if not sentence.startswith("See [")]
                self.assertTrue(1 <= len(sentences) <= 4, sentences)

    def test_a_definition_uses_no_word_that_is_explained_further_down(self):
        for position, (word, definition) in enumerate(self.entries):
            later = [other for other, _ in self.entries[position + 1:]]
            plain = re.sub(r"\[[^\]]*\]\([^)]*\)|`[^`]*`", " ", definition).lower()
            used = [other for other in later if re.search(rf"\b{re.escape(other.lower())}s?\b", plain)]
            self.assertEqual(used, [], word)

    def test_the_bench_build_and_the_target_say_what_is_wired(self):
        defined = dict(self.entries)
        self.assertIn("`mapping/legs-2.json`", defined["bench build"])
        self.assertIn("one strip of 60 LEDs, on pin 1", defined["bench build"])
        self.assertIn("`mapping/legs-20.json`", defined["target"])
        self.assertIn("not wired", defined["target"])

    def test_the_entry_for_command_names_every_command_of_the_command_list(self):
        table = support.read("docs/commands.md").split("\n## Commands\n")[1].split("\n## ")[0]
        listed = sorted({row.split("`")[1].split(" ")[0] for row in table.splitlines() if row.startswith("| `")})
        self.assertEqual(listed, ["brightness", "fault", "ignore", "list", "mapping", "off", "on", "order", "play", "read", "remove", "space", "status", "upload"])
        named = sorted({span.split(" ")[0] for span in re.findall(r"`([^`]+)`", dict(self.entries)["command"])})
        self.assertEqual(named, listed)

    def test_the_entries_are_found_as_they_are_written(self):
        text = "## A\n\n- **one**: First. Second\n  line.\n- **two words**: Third.\n\n## B\n\n- **three**: Fourth.\n"
        self.assertEqual(entries(text), [("one", "First. Second line."), ("two words", "Third."), ("three", "Fourth.")])


if __name__ == "__main__":
    unittest.main()

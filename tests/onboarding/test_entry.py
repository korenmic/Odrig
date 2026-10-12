import json
import re
import unittest

from . import support
from .test_pages import broken_links

ENTRY = support.ENTRY
POINTER = "CLAUDE.md"
README = "README.md"

HEADINGS = (
    "What this is",
    "Read first",
    "Then read, by task",
    "Rules you may not break",
    "Never touch",
    "What needs the owner",
    "Commands you will use",
    "What is coming",
    "The owner's workflow",
)

# The parts of the project, each with the folder that holds it.
PARTS = {"converter": "odrig/", "core": "core/", "emulator": "emulator/", "command tool": "odrigctl/", "firmware tool": "firmware/"}

# The pages for people, in the order the README gives them.
READING_ORDER = ("docs/getting-started.md", "docs/vocabulary.md", "docs/animation-guide.md", "docs/working-rules.md")

# The states of a seed on which no work has begun.
NOT_BEGUN = ("remaining", "suspended")


def flat(text):
    return " ".join(text.split())


def seeds():
    """`(number, state)` of every seed, in the order of the numbers."""
    states = [json.loads(path.read_text(encoding="utf-8")) for path in (support.ROOT / "project-seeds").glob("*/state.json")]
    return sorted((state["number"], state["state"]) for state in states)


class EntryFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = support.read(ENTRY)

    def part(self, heading):
        return flat(support.section(self.text, heading))

    def test_it_is_one_of_the_pages_and_fits_in_its_lines(self):
        self.assertIn(ENTRY, support.PAGES)
        self.assertEqual(support.ENTRY_LINES, 150)
        self.assertLessEqual(len(self.text.splitlines()), support.ENTRY_LINES)

    def test_it_has_its_sections_in_the_order_an_agent_needs_them(self):
        self.assertEqual(tuple(re.findall(r"(?m)^## (.+)$", self.text)), HEADINGS)

    def test_it_says_what_the_project_is_and_names_its_parts_with_their_folders(self):
        what = self.part("What this is")
        for name, folder in PARTS.items():
            with self.subTest(part=name):
                self.assertIn(f"the **{name}**, `{folder}`", what)
                self.assertTrue((support.ROOT / folder).is_dir())
        self.assertIn("60 x 60", what)

    def test_every_document_is_linked_and_the_other_places_are_named(self):
        linked = set(support.links(self.text))
        documents = sorted(f"docs/{path.name}" for path in (support.ROOT / "docs").glob("*.md"))
        self.assertGreaterEqual(len(documents), 17)
        self.assertEqual([name for name in documents if name not in linked], [])
        first = support.section(self.text, "Read first")
        for name in ("docs/vocabulary.md", "docs/working-rules.md", "docs/getting-started.md"):
            self.assertIn(f"]({name})", first)
        by_task = self.part("Then read, by task")
        self.assertGreaterEqual(len(re.findall(r"(?m)^\| [A-Z].+ \| .*\]\(docs/.+\|$", support.section(self.text, "Then read, by task"))), 7)
        for place in ("`project-seeds/`", "`docs/specs/`", "`tests/`", "`docs/drifts.md`"):
            self.assertIn(place, by_task)

    def test_it_states_the_rules_and_points_to_their_full_text(self):
        rules = self.part("Rules you may not break")
        self.assertEqual(re.findall(r"(?m)^([0-9]+)\. \*\*", support.section(self.text, "Rules you may not break")), [str(number) for number in range(1, 12)])
        for phrase in ("Never commit on `master`", "One task, one commit", "`git add -A`", "`git add .`", "`git add -u`", "`git commit -a`", "`git show --stat`",
                       "seen failing first", "Code carries no history", "selected by discovery", "answered, not asked", "is fixed once its tasks are being done",
                       "you tell the owner in words", "added to at the end only", "from 20 to 50 a second", "[docs/working-rules.md](docs/working-rules.md)"):
            self.assertIn(phrase, rules)

    def test_it_lists_what_must_never_be_touched(self):
        never = self.part("Never touch")
        for folder in support.FIRST_COMPUTER_ONLY:
            self.assertIn(f"`{folder}`", never)
        for phrase in ("on the first computer only", "Never change, move, delete or commit them", "An untracked file that you did not make",
                       "`firmware/fw.py` and `odrigctl`", "a brightness of 40 or less"):
            self.assertIn(phrase, never)

    def test_it_says_what_needs_the_owner(self):
        needed = self.part("What needs the owner")
        for phrase in ("Every addition to the command list", "changes a decision in `docs/decisions.md`", "hardware or power"):
            self.assertIn(phrase, needed)

    def test_the_commands_it_gives_are_the_setup_and_the_suites_of_the_getting_started_page(self):
        start = support.read("docs/getting-started.md")
        given = [command for heading, command in support.page_commands(self.text) if heading == "Commands you will use"]
        there = [command for heading, command in support.page_commands(start) if heading in ("Set up", "Run the tests")]
        self.assertEqual(given, there)
        self.assertEqual(len(given), 7)

    def test_what_is_coming_names_every_seed_that_is_not_begun_and_no_seed_that_is_completed(self):
        coming = self.part("What is coming")
        named = {int(number) for number in re.findall(r"\bseed ([0-9]{2})\b", coming)}
        self.assertGreaterEqual(len(named), 1)
        self.assertGreaterEqual(len(seeds()), 10)
        for number, state in seeds():
            with self.subTest(seed=number, state=state):
                if state in NOT_BEGUN:
                    self.assertIn(number, named)
                if state == "completed":
                    self.assertNotIn(number, named)
        self.assertIn("not in the repository yet", coming)
        self.assertIn("Today the Python tool is the converter", coming)

    def test_it_says_what_the_workflow_skills_are_and_that_they_are_not_needed(self):
        workflow = self.part("The owner's workflow")
        for phrase in ("seed to spec, enqueue, implement, a task runner and notify", "outside this repository", "You do not need them to make animations or to contribute"):
            self.assertIn(phrase, workflow)


class Pointer(unittest.TestCase):
    def test_it_points_to_the_entry_file_and_states_nothing_of_its_own(self):
        self.assertIn(POINTER, support.PAGES)
        text = support.read(POINTER)
        self.assertEqual(support.links(text), [ENTRY])
        self.assertIn(f"\n@{ENTRY}\n", text)
        self.assertLessEqual(len(text.splitlines()), 8)
        self.assertEqual(support.spans(text), [])


class Readme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = support.read(README)

    def test_it_gives_the_reading_order_for_people_before_the_reference_documents(self):
        self.assertEqual(re.findall(r"(?m)^## (.+)$", self.text)[:2], ["Start here", "Workstreams"])
        start = support.section(self.text, "Start here")
        self.assertEqual(tuple(re.findall(r"(?m)^[0-9]+\. \[(docs/[a-z-]+\.md)\]\(\1\)", start)), READING_ORDER)

    def test_it_points_agents_to_the_entry_file(self):
        self.assertIn(f"Coding agents start at [{ENTRY}]({ENTRY}).", flat(support.section(self.text, "Start here")))

    def test_every_link_of_it_leads_somewhere(self):
        self.assertEqual(broken_links(README, self.text), [])


if __name__ == "__main__":
    unittest.main()

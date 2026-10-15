import json
import re
import subprocess
import unittest

from . import support
from .test_pages import broken_links

ENTRY = support.ENTRY
POINTER = "CLAUDE.md"
README = "README.md"
FOLDER = "agent"
BOOTSTRAP = "agent/README.md"

HEADINGS = (
    "What this is",
    "Read first",
    "Then read, by task",
    "Rules you may not break",
    "Never touch",
    "What needs the owner",
    "If you work on Windows",
    "What is coming",
    "The owner's workflow",
)
BOOTSTRAP_HEADINGS = ("What the project is", "Read in this order", "What each file here is for", "Where everything else is")

# The parts of the project, each with the folder that holds it.
PARTS = {"converter": "converter/", "reference converter": "odrig/", "core": "core/", "emulator": "emulator/", "command tool": "odrigctl/", "firmware tool": "firmware/"}

# The pages of the folder in the order a newcomer reads them, and in the order the README
# gives them to people.
READ_IN_THIS_ORDER = ("vocabulary.md", "working-rules.md", "getting-started.md", "animation-guide.md")
READING_ORDER = ("agent/getting-started.md", "agent/vocabulary.md", "agent/animation-guide.md", "agent/working-rules.md")

SEED_FOR_WINDOWS = "project-seeds/11-p0-emulator-and-tools-on-windows/"

# The states of a seed on which no work has begun.
NOT_BEGUN = ("remaining", "suspended")


def flat(text):
    return " ".join(text.split())


def seeds():
    """`(number, state)` of every seed, in the order of the numbers."""
    states = [json.loads(path.read_text(encoding="utf-8")) for path in (support.ROOT / "project-seeds").glob("*/state.json")]
    return sorted((state["number"], state["state"]) for state in states)


def pages_of_the_folder():
    return sorted(f"{FOLDER}/{path.name}" for path in (support.ROOT / FOLDER).glob("*.md"))


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

    def test_it_says_what_the_project_is_and_points_into_the_folder(self):
        what = self.part("What this is")
        for phrase in ("60 x 60", "the folder `agent/`"):
            self.assertIn(phrase, what)
        first = support.section(self.text, "Read first")
        self.assertEqual(re.findall(r"(?m)^[0-9]+\. \[(agent/[A-Za-z-]+\.md)\]\(\1\)", first), [BOOTSTRAP, "agent/vocabulary.md", "agent/working-rules.md", "agent/getting-started.md"])

    def test_it_says_which_tool_is_the_converter_and_what_the_python_package_is_for(self):
        what = self.part("What this is")
        for phrase in ("The converter is the JavaScript tool in `converter/`, started as `node converter/odrig.js`", "The Python package `odrig/` was the converter before it",
                       "the reference that tests compare the converter with", "it holds the generators", "Convert and pack with the JavaScript tool only"):
            self.assertIn(phrase, what)
        self.assertTrue((support.ROOT / support.CONVERTER).is_file())
        self.assertTrue((support.ROOT / "odrig" / "generators").is_dir())
        by_task = support.section(self.text, "Then read, by task")
        rows = dict(re.findall(r"(?m)^\| (.+?) \| (.+) \|$", by_task))
        self.assertIn("[docs/converter.md](docs/converter.md)", rows["Change the converter"])
        self.assertIn("[docs/reference-converter.md](docs/reference-converter.md)", rows["Change the Python reference, a generator or the test vectors"])
        self.assertIn("`converter/tests/`", flat(by_task))

    def test_every_document_and_every_page_is_linked_and_the_other_places_are_named(self):
        linked = {target.split("#")[0] for target in support.links(self.text)}
        documents = sorted(f"docs/{path.name}" for path in (support.ROOT / "docs").glob("*.md"))
        self.assertGreaterEqual(len(documents), 13)
        self.assertEqual(len(pages_of_the_folder()), 5)
        self.assertEqual([name for name in documents + pages_of_the_folder() if name not in linked], [])
        by_task = self.part("Then read, by task")
        self.assertGreaterEqual(len(re.findall(r"(?m)^\| [A-Z].+ \| .*\]\((?:docs|agent)/.+\|$", support.section(self.text, "Then read, by task"))), 7)
        for place in ("`project-seeds/`", "`docs/specs/`", "`tests/`", "`docs/drifts.md`", "the getting-started page has the command of each"):
            self.assertIn(place, by_task)
        self.assertEqual([block for block in support.blocks(self.text) if block.mark == "sh"], [])

    def test_it_states_the_rules_and_points_to_their_full_text(self):
        rules = self.part("Rules you may not break")
        self.assertEqual(re.findall(r"(?m)^([0-9]+)\. \*\*", support.section(self.text, "Rules you may not break")), [str(number) for number in range(1, 13)])
        for phrase in ("Never commit on `master` directly", "One task, one commit", "`git add -A`", "`git add .`", "`git add -u`", "`git commit -a`", "`git show --stat`",
                       "seen failing first", "Code carries no history", "selected by discovery", "answered, not asked", "is fixed once its tasks are being done",
                       "you tell the owner in words", "added to at the end only", "bring your branch up to date with `origin/master`",
                       "Never rewrite history that has been pushed", "from 20 to 50 a second", "[agent/working-rules.md](agent/working-rules.md)"):
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

    def test_it_says_what_works_on_windows_and_what_is_different_there(self):
        windows = " ".join(self.part("If you work on Windows").split())
        for phrase in ("The reference converter, the core's build, the emulator and the command tool work on Windows 10 and 11, and their suites pass there.",
                       "The converter's own suite, `npm test --prefix converter`, does not pass on Windows yet", "Mending that is not part of seed 11.",
                       "That was seed 11", f"`{SEED_FOR_WINDOWS}`", "built there by `python core/build.py shared`, not by `make`",
                       "Windows has no virtual serial port", "with `--tcp` or `--http`", "The firmware tool and the board stay with the first computer.",
                       "Nothing is installed in the system", "unpacked into `tools/`", "a trial goes into `scratch/`", "Git ignores both",
                       "[agent/getting-started.md](agent/getting-started.md#on-windows)"):
            self.assertIn(phrase, windows)
        for folder in ("tools/x", "scratch/x"):
            self.assertEqual(subprocess.run(["git", "check-ignore", "-q", folder], cwd=support.ROOT).returncode, 0, folder)

    def test_what_is_coming_names_every_seed_that_is_not_begun_and_no_seed_that_is_completed(self):
        coming = self.part("What is coming")
        named = {int(number) for number in re.findall(r"\bseed ([0-9]{2})\b", coming)}
        self.assertLessEqual({12}, named)
        self.assertGreaterEqual(len(seeds()), 10)
        for number, state in seeds():
            with self.subTest(seed=number, state=state):
                if state in NOT_BEGUN:
                    self.assertIn(number, named)
                if state == "completed":
                    self.assertNotIn(number, named)
        self.assertIn("not in the repository yet", coming)
        self.assertIn("it has not been run inside the APK on a phone yet", flat(support.read("docs/decisions.md")))

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


class Bootstrap(unittest.TestCase):
    """The page of the folder that a newcomer begins with."""

    @classmethod
    def setUpClass(cls):
        cls.text = support.read(BOOTSTRAP)

    def test_it_is_one_of_the_pages_and_has_its_sections(self):
        self.assertIn(BOOTSTRAP, support.PAGES)
        self.assertEqual(tuple(re.findall(r"(?m)^## (.+)$", self.text)), BOOTSTRAP_HEADINGS)

    def test_the_pages_of_the_quick_suite_are_the_two_at_the_top_and_those_of_the_folder(self):
        self.assertEqual(sorted(support.PAGES), sorted([ENTRY, POINTER] + pages_of_the_folder()))
        self.assertEqual([name for name in support.tracked("docs") if name in support.PAGES], [])

    def test_it_says_what_the_project_is_and_names_its_parts_with_their_folders(self):
        what = flat(support.section(self.text, "What the project is"))
        for name, folder in PARTS.items():
            with self.subTest(part=name):
                self.assertIn(f"the **{name}**, `{folder}`", what)
                self.assertTrue((support.ROOT / folder).is_dir())
        for phrase in ("60 x 60", "the board stays with the first computer"):
            self.assertIn(phrase, what)

    def test_it_gives_the_reading_order_and_then_the_documents_by_task(self):
        order = support.section(self.text, "Read in this order")
        self.assertEqual(tuple(re.findall(r"(?m)^[0-9]+\. \[([a-z-]+\.md)\]\(\1\)", order)), READ_IN_THIS_ORDER)
        self.assertIn("[AGENTS.md](../AGENTS.md#then-read-by-task)", order)

    def test_it_says_what_each_file_of_the_folder_is_for(self):
        table = support.section(self.text, "What each file here is for")
        rows = dict(re.findall(r"(?m)^\| `(agent/[A-Za-z-]+\.md)` \| (.+) \|$", table))
        self.assertEqual(sorted(rows), pages_of_the_folder())
        self.assertTrue(all(purpose.strip() for purpose in rows.values()))
        for phrase in ("`AGENTS.md` and `CLAUDE.md` belong with these pages", "the tools of coding agents look for them there"):
            self.assertIn(phrase, flat(table))

    def test_it_says_where_everything_else_is(self):
        elsewhere = flat(support.section(self.text, "Where everything else is"))
        for place in ("`docs/`", "`project-seeds/`", "`docs/specs/`", "`tests/`"):
            self.assertIn(place, elsewhere)


class Readme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = support.read(README)

    def test_it_gives_the_reading_order_for_people_before_the_reference_documents(self):
        self.assertEqual(re.findall(r"(?m)^## (.+)$", self.text)[:2], ["Start here", "Workstreams"])
        start = support.section(self.text, "Start here")
        self.assertEqual(tuple(re.findall(r"(?m)^[0-9]+\. \[(agent/[a-z-]+\.md)\]\(\1\)", start)), READING_ORDER)
        self.assertIn(f"[{BOOTSTRAP}]({BOOTSTRAP})", start)

    def test_it_points_agents_to_the_entry_file(self):
        self.assertIn(f"Coding agents start at [{ENTRY}]({ENTRY}).", flat(support.section(self.text, "Start here")))

    def test_its_line_about_the_agent_files_names_the_folder(self):
        line = [entry for entry in re.split(r"(?m)^- ", support.section(self.text, "Workstreams")) if entry.startswith("**Agent files**")]
        self.assertEqual(len(line), 1)
        for phrase in ("[agent/](agent/)", "`AGENTS.md` and `CLAUDE.md`"):
            self.assertIn(phrase, flat(line[0]))

    def test_every_link_of_it_leads_somewhere(self):
        self.assertEqual(broken_links(README, self.text), [])


if __name__ == "__main__":
    unittest.main()

import json
import re
import unittest

from . import support

PAGE = "agent/working-rules.md"
REMOTE = "https://github.com/korenmic/Odrig"
DECISIONS = "docs/decisions.md"
CHANGE_LOG = "\n## Change log\n"

HEADINGS = (
    "How work is planned and recorded",
    "How commits are made",
    "What needs the owner",
    "If you have a board",
    "The frame rate",
    "Several contributors at once",
    "Code that runs on every computer",
    "The owner's workflow skills",
)

# The states a seed can have.
STATES = ("remaining", "in_progress", "completed", "suspended", "cancelled", "superseded")


def flat(text):
    """A text with every run of white space as one space, so a phrase is found across lines."""
    return " ".join(text.split())


class WorkingRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = support.read(PAGE)

    def part(self, heading):
        return flat(support.section(self.text, heading))

    def test_it_is_one_of_the_pages_and_has_its_eight_sections(self):
        self.assertIn(PAGE, support.PAGES)
        self.assertEqual(tuple(re.findall(r"(?m)^## (.+)$", self.text)), HEADINGS)

    def test_it_says_how_work_is_planned_and_recorded(self):
        planned = self.part("How work is planned and recorded")
        for phrase in ("`project-seeds/`", "`seed.md`", "`state.json`", "`docs/specs/`", "`requirements.md`", "`design.md`", "`tasks.md`",
                       "One seed, one commit", "One task, one commit", "checkbox", "**Question.**, **Answer.** and **Resolution.**",
                       "is fixed once its tasks are being done", "reaches the owner in words"):
            self.assertIn(phrase, planned)
        for state in STATES:
            self.assertIn(f"`{state}`", planned)

    def test_the_states_it_lists_are_the_ones_the_seeds_have(self):
        found = {json.loads(path.read_text(encoding="utf-8"))["state"] for path in (support.ROOT / "project-seeds").glob("*/state.json")}
        self.assertGreaterEqual(len(found), 2)
        self.assertLessEqual(found, set(STATES))

    def test_it_says_how_commits_are_made(self):
        made = self.part("How commits are made")
        for phrase in ("`git add <path> ...`", "`git add -A`", "`git add .`", "`git add -u`", "`git commit -a`", "`git show --stat`",
                       "seen failing first", "into the commit message", "Code carries no history", "selected by discovery", "lists test files"):
            self.assertIn(phrase, made)

    def test_it_says_what_needs_the_owner(self):
        needed = self.part("What needs the owner")
        for phrase in ("Every addition to the command list", "Anything that changes a decision", "Anything about hardware or power"):
            self.assertIn(phrase, needed)

    def test_it_gives_the_rules_of_the_board(self):
        board = self.part("If you have a board")
        self.assertEqual(re.findall(r"(?m)^([0-9]+)\. \*\*", support.section(self.text, "If you have a board")), [str(number) for number in range(1, 10)])
        for folder in support.FIRST_COMPUTER_ONLY:
            self.assertIn(f"`{folder}`", board)
        for phrase in ("never changed, moved, deleted or committed", "`firmware/fw.py`", "`odrigctl`", "RTS before the line DTR", "One program uses the board at a time",
                       "Brightness 40 or less", "one strip of 60 leds", "3.3 V pin", "never erased", "no fuse", "`python3 firmware/fw.py build`", "needs a person"):
            self.assertIn(phrase.lower(), board.lower())

    def test_the_rules_of_the_board_are_those_of_the_firmware_document(self):
        firmware = flat(support.read("docs/firmware.md"))
        for phrase in ("must have a brightness of 40 or less", "fed from the board's 3.3 V pin", "RTS lowered before DTR, does not reset the board", "The whole flash is never erased"):
            self.assertIn(phrase, firmware)

    def test_it_gives_the_frame_rate_rule_with_the_rates_that_were_measured(self):
        rate = self.part("The frame rate")
        for phrase in ("from 20 to 50 a second", "for any content", "above 50 or below 20", "Do not propose work", "36 to 42", "45 to 47"):
            self.assertIn(phrase, rate)
        firmware = flat(support.read("docs/firmware.md"))
        self.assertIn("45 to 47 against 36 to 42", firmware)
        self.assertIn("Any rate from 20 to 50 refreshes a second is fine on the board, for any content", firmware)

    def test_it_says_how_several_contributors_work_at_once(self):
        several = self.part("Several contributors at once")
        self.assertEqual(re.findall(r"(?m)^([0-9]+)\. \*\*", support.section(self.text, "Several contributors at once")), [str(number) for number in range(1, 9)])
        for phrase in (f"`{REMOTE}`", f"`git clone {REMOTE}.git`", "`git switch -c <your-branch>`", "Two contributors never work in one checkout",
                       "Nothing is committed directly on `master`", "`git fetch origin`", "`git merge origin/master`", "Run every suite that works on your computer",
                       "merged only when all of them pass", "`git merge <your-branch>`", "`git push origin master`", "Never rewrite history that has been pushed",
                       "added to at the end only", "keep both by hand, those of `master` first", "A seed's number is chosen after fetching",
                       "one folder and one commit", "at once by `.venv/bin/python tests/run.py`",
                       "with `--walkthrough` when `agent/getting-started.md` or `agent/animation-guide.md` changed"):
            self.assertIn(phrase, several)

    def test_what_a_test_or_a_tool_starts_it_ends(self):
        every = flat(self.part("Code that runs on every computer"))
        for phrase in ("**What you start, you end.**", "ends every process it starts, when it is done and when it is stopped", "`--parent` for an emulator",
                       "the runner's `ODRIG_RUN`", "by which the runner ends what is left"):
            self.assertIn(phrase, every)

    def test_the_drift_log_keeps_the_additions_of_both_sides_of_a_merge(self):
        self.assertIn("`.gitattributes` has git keep the additions of both sides of a merge", self.part("Several contributors at once"))
        attributes = (support.ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
        self.assertIn("docs/drifts.md merge=union", attributes)

    def test_it_says_what_the_workflow_skills_are_and_that_they_are_not_needed(self):
        skills = self.part("The owner's workflow skills")
        for phrase in ("not part of this repository", "You do not need them", "to make animations", "`.codex/`"):
            self.assertIn(phrase, skills)


class Decisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = support.read(DECISIONS)
        cls.sections, cls.log = text.split(CHANGE_LOG)
        cls.entries = re.findall(r"(?ms)^- (2[0-9]{3}-[0-9]{2}-[0-9]{2}): (.+?)(?=^- 2[0-9]{3}-|\Z)", cls.log)

    def test_the_rule_for_several_contributors_stands_in_place_of_the_rule_of_one(self):
        process = flat(self.sections.split("\n## Scope and process\n")[1].split("\n## ")[0])
        self.assertNotIn("All work is committed directly on `master`", process)
        self.assertNotIn("There is no remote yet", process)
        for phrase in ("Several contributors work at once", "Each works on a branch of their own", "nothing is committed directly on `master`",
                       "brought up to date with `master` before it is merged", "only with every test suite that needs no board passing",
                       "only ever added to at the end", f"The remote is `{REMOTE}`, a public repository", "is never rewritten",
                       "[working-rules.md](../agent/working-rules.md)"):
            self.assertIn(phrase, process)

    def test_the_decisions_say_that_the_repository_carries_the_vocabulary_and_the_rules(self):
        process = flat(self.sections.split("\n## Scope and process\n")[1].split("\n## ")[0])
        self.assertNotIn("will carry", process)
        for phrase in ("in the folder `agent/`", "a vocabulary, [vocabulary.md](../agent/vocabulary.md), and the working rules",
                       "A second contributor works on a Windows computer", "is seed 11"):
            self.assertIn(phrase, process)

    def test_the_change_log_has_the_new_rule_after_the_rule_of_one_and_only_grows_at_its_end(self):
        self.assertGreaterEqual(len(self.entries), 15)
        dates = [date for date, _ in self.entries]
        self.assertEqual(dates, sorted(dates))
        entries = [flat(entry) for _, entry in self.entries]
        self.assertTrue(entries[0].startswith("Workstreams agreed."))
        of_one = [position for position, entry in enumerate(entries) if entry.startswith("All work goes directly on `master`; no remote yet.")]
        of_several = [position for position, entry in enumerate(entries) if entry.startswith("Several contributors now work at once")]
        self.assertEqual((len(of_one), len(of_several)), (1, 1))
        self.assertLess(of_one[0], of_several[0])
        for phrase in ("a branch for each contributor", "added to at the end only"):
            self.assertIn(phrase, entries[of_several[0]])
        of_the_remote = [position for position, entry in enumerate(entries) if entry.startswith("The repository has a remote")]
        self.assertEqual(len(of_the_remote), 1)
        self.assertLess(of_several[0], of_the_remote[0])
        for phrase in (f"`{REMOTE}`", "the folder `agent/`", "a Windows computer", "seed 11"):
            self.assertIn(phrase, entries[of_the_remote[0]])


if __name__ == "__main__":
    unittest.main()

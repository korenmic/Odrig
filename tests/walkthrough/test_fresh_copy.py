import collections
import pathlib
import re
import tempfile
import unittest

from emulator import recfile
from tests.onboarding import support as pages

from . import support

Followed = collections.namedtuple("Followed", "page followed left_out")

# The pages the walk-through follows, in the order a newcomer reads them. For each: the
# headings whose commands are run, in the order of the page, and the headings whose
# commands are not run, each with the reason.
PLAN = (
    Followed(
        "docs/getting-started.md",
        ("Set up", "Run the tests", "Pack the demo show", "Check it without a screen"),
        {
            "Suites that need more": "the firmware tool's suite fetches its build tools, one suite is this one, and two need the board",
            "Run it in the emulator": "it needs a second terminal and somebody to look at the page",
        },
    ),
)

DEMO_SHOW = "build/demo-20/show"
DEMO_FILES = ("dvd.odrg", "hello.odrg", "mapping.json", "show.json")
DEMO_RECORD = "build/demo-20/check.odrr"
SUITES = 4


def reply(output):
    """The reply of the one command a record run was given by its script."""
    found = re.findall(r"(?m)^reply [0-9]+ (\{.*\})$", output)
    return found[0] if len(found) == 1 else None


class Plan(unittest.TestCase):
    def test_every_heading_with_commands_is_followed_or_left_out_with_its_reason(self):
        for plan in PLAN:
            with self.subTest(page=plan.page):
                with_commands = {heading for heading, _ in pages.page_commands(pages.read(plan.page))}
                self.assertEqual(with_commands, set(plan.followed) | set(plan.left_out))
                self.assertEqual(set(plan.followed) & set(plan.left_out), set())
                self.assertTrue(all(reason.strip() for reason in plan.left_out.values()))

    def test_the_followed_headings_are_in_the_order_of_the_page(self):
        for plan in PLAN:
            with self.subTest(page=plan.page):
                order = [heading for heading in re.findall(r"(?m)^## (.+)$", pages.read(plan.page)) if heading in plan.followed]
                self.assertEqual(tuple(order), plan.followed)


class FreshCopy(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="odrig-walkthrough-")
        self.addCleanup(folder.cleanup)
        self.copy = pathlib.Path(folder.name) / "odrig"
        self.changed, self.gone = support.fresh_copy(self.copy)

    def follow(self, plan):
        """Runs the commands under the followed headings of a page, in the page's order, from
        the root of the copy. Returns what each command printed, by heading."""
        path = self.copy / plan.page
        self.assertTrue(path.is_file(), f"{plan.page} is not in the fresh copy: a new file has to be staged before the walk-through sees it")
        printed = collections.defaultdict(list)
        for heading, command in pages.page_commands(path.read_text(encoding="utf-8")):
            if heading not in plan.followed:
                continue
            done = support.run(command, self.copy)
            self.assertEqual(done.status, 0, f"{plan.page}, under \"{heading}\": the command\n    {command}\nended with status {done.status} and printed:\n{done.output[-6000:]}")
            printed[heading].append((command, done.output))
        return printed

    def test_the_copy_holds_what_git_tracks_and_nothing_else(self):
        self.assertEqual(support.tracked(self.copy), {name for name in support.tracked(support.ROOT) if (support.ROOT / name).is_file()})
        self.assertEqual(support.git(self.copy, "status", "--porcelain"), "")
        for name in sorted(support.tracked(self.copy)):
            self.assertEqual((self.copy / name).read_bytes(), (support.ROOT / name).read_bytes(), name)
        for made in ("build", ".venv", ".codex", "core/build"):
            self.assertFalse((self.copy / made).exists(), made)

    def test_the_pages_can_be_followed_from_a_fresh_copy(self):
        started = self.follow(PLAN[0])

        suites = started["Run the tests"]
        self.assertEqual(len(suites), SUITES)
        for command, output in suites:
            self.assertEqual(output.strip().splitlines()[-1], "OK", command)

        show = self.copy / DEMO_SHOW
        self.assertEqual(sorted(path.name for path in show.iterdir()), sorted(DEMO_FILES))
        self.assertEqual((show / "mapping.json").read_bytes(), (self.copy / "mapping" / "legs-20.json").read_bytes())
        self.assertEqual((show / "show.json").read_bytes(), (self.copy / "shows" / "demo-20" / "show.json").read_bytes())

        recorded = [output for command, output in started["Check it without a screen"] if "--record" in command]
        self.assertEqual(len(recorded), 1)
        answer = reply(recorded[0])
        self.assertIsNotNone(answer, recorded[0])
        for member in ('"ok":true', '"playing":3', '"animation":1', '"error":null'):
            self.assertIn(member, answer)
        self.assertIn(f"reply 1000 {answer}", pages.read(PLAN[0].page))
        recording = recfile.read(self.copy / DEMO_RECORD)
        self.assertEqual(len(recording.legs), 20)
        self.assertEqual(len(recording.ticks), 100)
        self.assertTrue(all(tick.produced and any(tick.data) for tick in recording.ticks))


if __name__ == "__main__":
    unittest.main()

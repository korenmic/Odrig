import collections
import pathlib
import re
import tempfile
import time
import unittest

from emulator import recfile
from tests import run as runner
from tests.onboarding import support as pages

from . import support

Followed = collections.namedtuple("Followed", "page followed left_out")


def on_any_computer(reply):
    """A reply of `status` with the emulator's name in `host` cut to the words that do not
    name the computer it runs on, which the page cannot know."""
    return re.sub(r'"host":"odrig emulator on [^"]*"', '"host":"odrig emulator on <system>"', reply)


# The pages the walk-through follows, in the order a newcomer reads them. For each: the
# headings whose commands are run, in the order of the page, and the headings whose
# commands are not run, each with the reason.
START = Followed(
    "agent/getting-started.md",
    ("Set up", "Run the tests", "Pack the demo show", "Check it without a screen"),
    {
        "Suites that need more": "the firmware tool's suite fetches its build tools, one suite is this one, and two need the board",
        "Run it in the emulator": "it needs a second terminal and somebody to look at the page",
    },
)
GUIDE = Followed(
    "agent/animation-guide.md",
    ("A generator", "An import", "Check a source", "Pack it into a show", "Check it without a screen"),
    {
        "Look at it in the emulator": "it needs somebody to look at the page",
    },
)
PLAN = (START, GUIDE)

# The suites the getting-started page runs after the setup. The copy's runner runs them, all
# at once, rather than their commands one after another; each has its line, which ends with
# OK when it passed, naming the tests that were left out, as the emulator's suite does for
# those of the other system.
TESTS = "Run the tests"
SUITES = 5


def passed(suite):
    return re.compile(rf"(?m)^{re.escape(suite)}: [1-9][0-9]* tests, [0-9]+ s, OK( \(skipped=[0-9]+\))?$")

# What the setup of the page leaves in the copy: the Python of the environment, the two
# packages of the converter with the decoder program, and the core's library.
INSTALLED = (".venv/bin/python", "converter/node_modules/omggif", "converter/node_modules/ffmpeg-static/ffmpeg", "core/build/libodrig_core.dylib")

DEMO_SHOW = "build/demo-20/show"
DEMO_FILES = ("dvd.odrg", "hello.odrg", "mapping.json", "show.json")
DEMO_RECORD = "build/demo-20/check.odrr"

# The media file the guide imports, and the program of this suite that writes one.
CLIP = "build/try/clip.gif"
MAKE_CLIP = f".venv/bin/python tests/walkthrough/make_gif.py {CLIP}"
TRIED_SHOW = "build/try/show"
TRIED_FILES = ("clip.odrg", "dvd.odrg", "mapping.json", "show.json")


def reply(output):
    """The reply to the one command that the script of a record run gave."""
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

    def test_the_guide_imports_the_clip_this_suite_writes(self):
        imports = [command for heading, command in pages.page_commands(pages.read(GUIDE.page)) if heading == "An import"]
        self.assertEqual(len(imports), 1)
        self.assertIn(f" import {CLIP} ", imports[0])

    def test_every_suite_the_page_runs_is_one_of_the_runner(self):
        commands = [command for heading, command in pages.page_commands(pages.read(START.page)) if heading == TESTS]
        self.assertEqual(len(commands), SUITES)
        names = [support.runner_suite(command, runner.SUITES) for command in commands]
        self.assertNotIn(None, names, commands)
        self.assertEqual(len(set(names)), SUITES)


class Commands(unittest.TestCase):
    def test_a_command_s_children_end_with_it_and_npm_prefers_the_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            done = support.run("sleep 60 >/dev/null 2>&1 & echo $!; echo $npm_config_prefer_offline", folder)
        self.assertEqual(done.status, 0, done.output)
        child, offline = done.output.split()
        deadline = time.monotonic() + 5
        while runner.alive(int(child)) and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertFalse(runner.alive(int(child)))
        self.assertEqual(offline, "true")


class FreshCopy(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="odrig-walkthrough-")
        self.addCleanup(folder.cleanup)
        self.copy = pathlib.Path(folder.name) / "odrig"
        self.changed, self.gone = support.fresh_copy(self.copy)

    def run_in_the_copy(self, command, where):
        done = support.run(command, self.copy)
        self.assertEqual(done.status, 0, f"{where}: the command\n    {command}\nended with status {done.status} and printed:\n{done.output[-6000:]}")
        return done.output

    def follow(self, plan):
        """Runs the commands under the followed headings of a page, in the page's order, from
        the root of the copy. Returns what each command printed, by heading. The commands of
        the suites are run together, by the copy's runner, once the heading's commands are
        read; each of them gets the runner's output."""
        path = self.copy / plan.page
        self.assertTrue(path.is_file(), f"{plan.page} is not in the fresh copy: a new file has to be staged before the walk-through sees it")
        printed = collections.defaultdict(list)
        commands = [(heading, command) for heading, command in pages.page_commands(path.read_text(encoding="utf-8")) if heading in plan.followed]
        for index, (heading, command) in enumerate(commands):
            if heading != TESTS:
                printed[heading].append((command, self.run_in_the_copy(command, f"{plan.page}, under \"{heading}\"")))
            elif index + 1 == len(commands) or commands[index + 1][0] != TESTS:
                printed[heading] = self.run_the_suites([each for under, each in commands if under == TESTS], plan.page)
        return printed

    def run_the_suites(self, commands, page):
        names = [support.runner_suite(command, runner.SUITES) for command in commands]
        for command, name in zip(commands, names):
            self.assertIsNotNone(name, f"{page}: the command\n    {command}\nis not one of a suite the runner knows")
        output = self.run_in_the_copy(f".venv/bin/python tests/run.py --suites {','.join(names)}", f"{page}, under \"{TESTS}\", by the runner")
        return [(command, output) for command in commands]

    def shown(self, plan, heading):
        """The blocks of a page, under a heading, that show what a command prints."""
        text = (self.copy / plan.page).read_text(encoding="utf-8")
        return [block.body for block in pages.blocks(text) if block.heading == heading and block.mark == "text"]

    def test_the_copy_holds_what_git_tracks_and_nothing_else(self):
        self.assertEqual(support.tracked(self.copy), {name for name in support.tracked(support.ROOT) if (support.ROOT / name).is_file()})
        self.assertEqual(support.git(self.copy, "status", "--porcelain"), "")
        for name in sorted(support.tracked(self.copy)):
            self.assertEqual((self.copy / name).read_bytes(), (support.ROOT / name).read_bytes(), name)
        for made in ("build", ".venv", ".codex", "core/build", "converter/node_modules"):
            self.assertFalse((self.copy / made).exists(), made)

    def test_the_pages_can_be_followed_from_a_fresh_copy(self):
        started = self.follow(START)

        for installed in INSTALLED:
            self.assertTrue((self.copy / installed).exists(), installed)

        suites = started[TESTS]
        self.assertEqual(len(suites), SUITES)
        for command, output in suites:
            self.assertRegex(output, passed(support.runner_suite(command, runner.SUITES)), command)

        show = self.copy / DEMO_SHOW
        self.assertEqual(sorted(path.name for path in show.iterdir()), sorted(DEMO_FILES))
        self.assertEqual((show / "mapping.json").read_bytes(), (self.copy / "mapping" / "legs-20.json").read_bytes())
        self.assertEqual((show / "show.json").read_bytes(), (self.copy / "shows" / "demo-20" / "show.json").read_bytes())

        recorded = [output for command, output in started["Check it without a screen"] if "--record" in command]
        self.assertEqual(len(recorded), 1)
        answer = reply(recorded[0])
        self.assertIsNotNone(answer, recorded[0])
        for member in ('"ok":true', '"playing":"all"', '"animation":1', '"error":null'):
            self.assertIn(member, answer)
        self.assertEqual([on_any_computer(block) for block in self.shown(START, "Check it without a screen")], [on_any_computer(f"reply 1000 {answer}\n")])
        recording = recfile.read(self.copy / DEMO_RECORD)
        self.assertEqual(len(recording.legs), 20)
        self.assertEqual(len(recording.ticks), 100)
        self.assertTrue(all(tick.produced and any(tick.data) for tick in recording.ticks))

        (self.copy / CLIP).parent.mkdir(parents=True)
        self.run_in_the_copy(MAKE_CLIP, "the clip for the guide's import")
        made = self.follow(GUIDE)

        checked = [output for command, output in made["Check a source"]]
        self.assertEqual(checked, self.shown(GUIDE, "Check a source"))
        self.assertIn("canvas: 60x60\n", checked[0])
        self.assertIn("duration_ms: 1000\n", checked[0])

        show = self.copy / TRIED_SHOW
        self.assertEqual(sorted(path.name for path in show.iterdir()), sorted(TRIED_FILES))
        self.assertEqual((show / "mapping.json").read_bytes(), (self.copy / "mapping" / "legs-20.json").read_bytes())

        recorded = [output for command, output in made["Check it without a screen"] if "--record" in command]
        self.assertEqual(len(recorded), 1)
        answer = reply(recorded[0])
        self.assertIsNotNone(answer, recorded[0])
        for member in ('"ok":true', '"playing":"all"', '"animation":1', '"error":null'):
            self.assertIn(member, answer)


if __name__ == "__main__":
    unittest.main()

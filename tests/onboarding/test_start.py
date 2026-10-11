import json
import re
import unittest

from . import support

PAGE = "docs/getting-started.md"

HEADINGS = (
    "What you need",
    "Set up",
    "Run the tests",
    "Suites that need more",
    "Pack the demo show",
    "Run it in the emulator",
    "Check it without a screen",
    "What to read next",
)

# For every folder of tests/ that holds a suite: the command that runs it, and whether the
# page gives it among the suites to run right after the setup.
SUITES = {
    "converter": (".venv/bin/python -m unittest discover -s tests/converter -t .", True),
    "core": ("make -C core test", True),
    "emulator": (".venv/bin/python -m unittest discover -s tests/emulator -t .", True),
    "onboarding": (".venv/bin/python -m unittest discover -s tests/onboarding -t .", True),
    "firmware": ("python3 firmware/fw.py test", False),
    "walkthrough": (".venv/bin/python -m unittest discover -s tests/walkthrough -t .", False),
    "board": ("python3 firmware/fw.py test-board", False),
    "air": ("python3 firmware/fw.py test-air", False),
}
NEED_THE_BOARD = ("board", "air")


def flat(text):
    return " ".join(text.split())


class GettingStarted(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = support.read(PAGE)

    def part(self, heading):
        return support.section(self.text, heading)

    def commands(self, heading):
        return [command for under, command in support.page_commands(self.text) if under == heading]

    def test_it_is_one_of_the_pages_and_has_its_sections(self):
        self.assertIn(PAGE, support.PAGES)
        self.assertEqual(tuple(re.findall(r"(?m)^## (.+)$", self.text)), HEADINGS)

    def test_it_says_what_has_to_be_on_the_computer_and_what_runs_elsewhere(self):
        needed = flat(self.part("What you need"))
        for phrase in ("A Mac", "run on macOS only at present", "command-line developer tools", "`make`", "`git`", "Python 3.10 or later, as `python3`",
                       "On Windows and Linux only the converter", "it has been run on macOS only"):
            self.assertIn(phrase, needed)
        self.assertIn("is verified on macOS", flat(support.read("docs/converter.md")))

    def test_the_setup_is_the_environment_the_libraries_and_the_shared_library(self):
        self.assertEqual(self.commands("Set up"), ["python3 -m venv .venv", ".venv/bin/python -m pip install -r requirements.txt", "make -C core shared"])
        pinned = re.findall(r"(?m)^([a-z]+)==", (support.ROOT / "requirements.txt").read_text(encoding="utf-8"))
        self.assertEqual(sorted(set(pinned)), ["av", "numpy", "pillow"])
        setup = flat(self.part("Set up"))
        for phrase in ("numpy, Pillow and PyAV", "`core/build/libodrig_core.dylib`", "`.venv/bin/python` is the Python for every command", "write it as `python`"):
            self.assertIn(phrase, setup)

    def test_every_folder_of_tests_that_holds_a_suite_has_its_command(self):
        folders = sorted(path.name for path in (support.ROOT / "tests").iterdir() if any(path.glob("test_*.py")))
        self.assertEqual(folders, sorted(SUITES))
        after_setup = self.commands("Run the tests")
        self.assertEqual(after_setup, [command for command, at_once in SUITES.values() if at_once])
        given = flat(self.text)
        for suite, (command, _) in SUITES.items():
            with self.subTest(suite=suite):
                self.assertIn(command, given)
                self.assertIn(f"`tests/{suite}`", given)
        more = flat(self.part("Suites that need more"))
        for suite in NEED_THE_BOARD:
            self.assertIn(f"`tests/{suite}`", more)
        self.assertIn("need the board on USB and write to it", more)
        self.assertIn("None needs the board or the network", flat(self.part("Run the tests")))

    def test_it_packs_the_demo_show_from_what_the_generators_write(self):
        commands = self.commands("Pack the demo show")
        self.assertEqual(commands[0], "mkdir -p build/demo-20/sources")
        self.assertEqual(sum(command.startswith(".venv/bin/python -m odrig.generators.") for command in commands), 2)
        self.assertEqual(commands[-1], ".venv/bin/python -m odrig pack --show shows/demo-20/show.json --mapping mapping/legs-20.json --sources build/demo-20/sources --out build/demo-20/show")
        show = json.loads((support.ROOT / "shows" / "demo-20" / "show.json").read_text(encoding="utf-8"))
        named = sorted(item["file"] for item in show["items"] if "file" in item)
        self.assertEqual(named, ["dvd.odrg", "hello.odrg"])
        for name in named:
            self.assertTrue(any(f"build/demo-20/sources/{name[:-5]}.json" in command for command in commands), name)
            self.assertIn(f"`{name}`", self.part("Pack the demo show"))
        self.assertEqual([item["seconds"] for item in show["items"] if "cycle" in item], [15])
        self.assertIn("15 seconds each", flat(self.part("Pack the demo show")))

    def test_it_runs_the_emulator_and_sends_it_a_command_by_each_way(self):
        commands = self.commands("Run it in the emulator")
        self.assertEqual(commands[0], ".venv/bin/python -m emulator build/demo-20/show")
        sent = [command for command in commands[1:] if command.startswith(".venv/bin/python -m odrigctl ")]
        self.assertEqual(len(sent), len(commands) - 1)
        self.assertTrue(any("--port build/emulator/serial" in command for command in sent))
        self.assertTrue(any("--http 127.0.0.1:8600" in command for command in sent))
        shown = flat(self.part("Run it in the emulator"))
        for phrase in ("page: http://127.0.0.1:8600/", "build/emulator/serial", "Ctrl-C", "`Mapping`", "`core` and `page`"):
            self.assertIn(phrase, shown)

    def test_it_checks_a_show_without_a_screen_in_record_mode(self):
        commands = self.commands("Check it without a screen")
        self.assertEqual(len(commands), 2)
        self.assertTrue(commands[0].startswith("printf '1000 status\\n' > "))
        self.assertIn("--record", commands[1])
        self.assertIn("--script", commands[1])
        said = flat(self.part("Check it without a screen"))
        for phrase in ('reply 1000 {"ok":true', '`"error":null`', '`"playing":3`', "[reasons.md](reasons.md)"):
            self.assertIn(phrase, said)


if __name__ == "__main__":
    unittest.main()

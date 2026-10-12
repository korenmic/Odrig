import json
import re
import unittest

from . import support

PAGE = "agent/getting-started.md"

HEADINGS = (
    "What you need",
    "On Windows",
    "Set up",
    "Run the tests",
    "Suites that need more",
    "Pack the demo show",
    "Run it in the emulator",
    "Check it without a screen",
    "What to read next",
)

CLONE = "git clone https://github.com/korenmic/Odrig.git"
SEED_FOR_WINDOWS = "project-seeds/11-p0-emulator-and-tools-on-windows/"

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

# The suite of the converter, which lives beside the tool and not in tests/: its folder and
# the command that runs it. The page gives it first among the suites to run after the setup.
CONVERTER_SUITE = ("converter/tests", "npm test --prefix converter")
CONVERTER = "node converter/odrig.js"


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

    def test_it_says_what_has_to_be_on_the_computer(self):
        needed = flat(self.part("What you need"))
        for phrase in ("A Mac", "run on macOS only at present", "command-line developer tools", "`make`", "`git`", "Python 3.10 or later, as `python3`",
                       "Node.js 20 or later, as `node`", "the `npm` that comes with it", "`node --version` has to say v20 or more"):
            self.assertIn(phrase, needed)
        package = json.loads((support.ROOT / "converter" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["engines"], {"node": ">=20"})
        self.assertIn("On a Windows computer read [On Windows](#on-windows) first.", flat(self.text.split("\n## ")[0]))

    def test_it_says_what_works_on_windows_today_and_whose_job_the_rest_is(self):
        windows = flat(self.part("On Windows"))
        for phrase in ("| The converter and its suite | Written to run there. They have been run on macOS only. |",
                       "| The reference converter, the generators and their suite | The same: written to run there, run on macOS only. |",
                       "| The core's build, the emulator, the command tool | macOS only. |",
                       "| The firmware tool and the board | They stay with the first computer. |",
                       "is seed 11", f"`{SEED_FOR_WINDOWS}`", "the first job of the contributor on Windows",
                       "its spec, its tasks and their implementation on the Windows computer", "Python 3.10 or later", "Node.js 20 or later",
                       "the converter and the generators can be tried on Windows", "which also runs the converter's suite on Windows",
                       "from `make -C core shared` on, is what seed 11 provides"):
            self.assertIn(phrase, windows)
        self.assertIn("Windows and Linux are supported by construction and not verified: nothing has been run there.", flat(support.read("docs/converter.md")))
        self.assertIn("It is verified on macOS with Python 3.14.", flat(support.read("docs/reference-converter.md")))

    def test_the_setup_on_windows_is_the_part_that_is_known_and_is_not_given_as_run(self):
        self.assertEqual(self.commands("On Windows"), [])
        shown = [block.body.splitlines() for block in support.blocks(self.text) if block.heading == "On Windows"]
        self.assertEqual(shown, [[
            CLONE,
            "cd Odrig",
            "python -m venv .venv",
            ".venv\\Scripts\\python -m pip install -r requirements.txt",
            "npm ci --prefix converter",
            CONVERTER_SUITE[1],
            ".venv\\Scripts\\python -m unittest discover -s tests/converter -t .",
        ]])
        self.assertIn("none of it has been tried there", flat(self.part("On Windows")))

    def test_the_setup_is_the_clone_the_environment_the_libraries_the_packages_and_the_shared_library(self):
        self.assertEqual(self.commands("Set up"), ["python3 -m venv .venv", ".venv/bin/python -m pip install -r requirements.txt", "npm ci --prefix converter", "make -C core shared"])
        pinned = re.findall(r"(?m)^([a-z]+)==", (support.ROOT / "requirements.txt").read_text(encoding="utf-8"))
        self.assertEqual(sorted(set(pinned)), ["av", "numpy", "pillow"])
        package = json.loads((support.ROOT / "converter" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(package["dependencies"]), ["ffmpeg-static", "omggif"])
        setup = flat(self.part("Set up"))
        for phrase in (f"`{CLONE}`", "numpy, Pillow and PyAV", "with which the reference converter reads videos and GIFs", "the converter's two packages for the same job",
                       "`converter/node_modules/`", "fetches a decoder program", "`core/build/libodrig_core.dylib`", "Git ignores these three folders",
                       "`.venv/bin/python` is the Python for every command", "write it as `python`"):
            self.assertIn(phrase, setup)
        ignored = (support.ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for folder in ("/.venv/", "/converter/node_modules/", "/core/build/"):
            self.assertIn(folder, ignored)

    def test_every_folder_of_tests_that_holds_a_suite_has_its_command(self):
        folders = sorted(path.name for path in (support.ROOT / "tests").iterdir() if any(path.glob("test_*.py")))
        self.assertEqual(folders, sorted(SUITES))
        beside, of_the_converter = CONVERTER_SUITE
        self.assertTrue(any((support.ROOT / beside).glob("*.test.js")))
        after_setup = self.commands("Run the tests")
        self.assertEqual(after_setup, [of_the_converter] + [command for command, at_once in SUITES.values() if at_once])
        given = flat(self.text)
        self.assertIn(f"| `{beside}` |", given)
        for suite, (command, _) in SUITES.items():
            with self.subTest(suite=suite):
                self.assertIn(command, given)
                self.assertIn(f"`tests/{suite}`", given)
        more = flat(self.part("Suites that need more"))
        for suite in NEED_THE_BOARD:
            self.assertIn(f"`tests/{suite}`", more)
        self.assertIn("need the board on USB and write to it", more)
        self.assertEqual(len(after_setup), 5)
        self.assertIn("runs the five suites above", more)
        after = flat(self.part("Run the tests"))
        for phrase in ("The first ends with a list of counts, in which `fail 0` says that every test passed", "Each of the others ends with the line `OK`",
                       "None needs the board or the network"):
            self.assertIn(phrase, after)

    def test_it_packs_the_demo_show_from_what_the_generators_write_and_calls_it_test_content(self):
        commands = self.commands("Pack the demo show")
        self.assertEqual(commands[0], "mkdir -p build/demo-20/sources")
        self.assertEqual(sum(command.startswith(".venv/bin/python -m odrig.generators.") for command in commands), 2)
        self.assertEqual(commands[-1], f"{CONVERTER} pack --show shows/demo-20/show.json --mapping mapping/legs-20.json --sources build/demo-20/sources --out build/demo-20/show")
        show = json.loads((support.ROOT / "shows" / "demo-20" / "show.json").read_text(encoding="utf-8"))
        named = sorted(item["file"] for item in show["items"] if "file" in item)
        self.assertEqual(named, ["dvd.odrg", "hello.odrg"])
        for name in named:
            self.assertTrue(any(f"build/demo-20/sources/{name[:-5]}.json" in command for command in commands), name)
            self.assertIn(f"`{name}`", self.part("Pack the demo show"))
        self.assertEqual([item["seconds"] for item in show["items"] if "cycle" in item], [15])
        packed = flat(self.part("Pack the demo show"))
        for phrase in ("15 seconds each", "is test content for the target and not finished work", "two proof-of-concept animations"):
            self.assertIn(phrase, packed)

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
        for phrase in ('reply 1000 {"ok":true', '`"error":null`', '`"playing":3`', "[reasons.md](../docs/reasons.md)"):
            self.assertIn(phrase, said)


if __name__ == "__main__":
    unittest.main()

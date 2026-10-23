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

# For every folder of tests/ that holds a suite: the command that runs it, and whether the
# page gives it among the suites to run right after the setup.
SUITES = {
    "converter": (".venv/bin/python -m unittest discover -s tests/converter -t .", True),
    "core": ("make -C core test", True),
    "emulator": (".venv/bin/python -m unittest discover -s tests/emulator -t .", True),
    "onboarding": (".venv/bin/python -m unittest discover -s tests/onboarding -t .", True),
    "firmware": ("python3 firmware/fw.py test", False),
    "app": ("python3 -m unittest discover -s tests/app -t .", False),
    "mapping": ("python3 -m unittest discover -s tests/mapping -t .", False),
    "apk": ("python3 -m unittest discover -s tests/apk -t .", False),
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
        for phrase in ("A Mac, or a Windows computer", "The firmware tool runs on macOS only at present", "command-line developer tools", "`make`", "`git`", "Python 3.10 or later, as `python3`",
                       "Node.js 20 or later, as `node`", "the `npm` that comes with it", "`node --version` has to say v20 or more"):
            self.assertIn(phrase, needed)
        package = json.loads((support.ROOT / "converter" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["engines"], {"node": ">=20"})
        self.assertIn("On a Windows computer read [On Windows](#on-windows) first.", flat(self.text.split("\n## ")[0]))

    def test_it_says_what_works_on_windows_what_stays_with_the_first_computer_and_what_to_install(self):
        windows = flat(self.part("On Windows"))
        for phrase in ("The Python library, the core's build, the emulator, the command tool and their suites work on Windows 10 and 11.",
                       f"The converter's own suite, `{CONVERTER_SUITE[1]}`, passes there too.",
                       "The firmware tool, the board and the walk-through suite stay with the first computer.",
                       "git, Python 3.10 or later as `python`, Node.js 20 or later, and a C++ compiler",
                       "`g++` or `clang++` on the path, and Microsoft's C++ build tools", "the WinLibs build of MinGW-w64",
                       "into the folder `tools/` of the repository: nothing is installed"):
            self.assertIn(phrase, windows)
        self.assertIn("It is verified on macOS and on Windows 11, each with Python 3.14.", flat(support.read("docs/python-library.md")))
        self.assertEqual(support.subprocess.run(["git", "check-ignore", "-q", "tools/x"], cwd=support.ROOT).returncode, 0)

    def test_the_setup_on_windows_and_its_suites_are_commands_their_tools_understand(self):
        self.assertEqual(self.commands("On Windows"), [], "the walk-through runs on macOS and is not to run these")
        shown = [block.body.splitlines() for block in support.blocks(self.text) if block.heading == "On Windows"]
        python = support.WINDOWS_PYTHON
        self.assertEqual(shown, [[
            CLONE,
            "cd Odrig",
            "python -m venv .venv",
            "npm ci --prefix converter",
            CONVERTER_SUITE[1],
            f"{python} core/build.py shared",
            f"{python} -m unittest discover -s tests/converter -t .",
            f"{python} core/build.py test",
            f"{python} -m unittest discover -s tests/emulator -t .",
            f"{python} -m unittest discover -s tests/onboarding -t .",
        ]])
        for command in shown[0]:
            self.assertIsNone(support.refusal(command), command)
        self.assertEqual(python, ".venv\\Scripts\\python")

    def test_the_suites_of_windows_are_the_suites_the_page_runs_after_the_setup(self):
        on_windows = [line for block in support.blocks(self.text) if block.heading == "On Windows" for line in block.body.splitlines() if "tests/" in line or line.endswith(" test") or line == CONVERTER_SUITE[1]]
        after_setup = self.commands("Run the tests")
        self.assertEqual(len(on_windows), len(after_setup))
        written = {".venv/bin/python": support.WINDOWS_PYTHON, "make -C core test": f"{support.WINDOWS_PYTHON} core/build.py test"}
        for here, there in zip(after_setup, on_windows):
            for old, new in written.items():
                here = here.replace(old, new)
            self.assertEqual(here, there)

    def test_the_differences_on_windows_are_one_table(self):
        rows = re.findall(r"(?m)^\| (.+?) \| (.+?) \|$", self.part("On Windows"))
        self.assertEqual(rows[0][1], "On Windows")
        differences = dict(rows[1:])
        self.assertEqual(differences["`.venv/bin/python`"], f"`{support.WINDOWS_PYTHON}`")
        self.assertEqual(differences["`mkdir -p build/demo-20/sources`"], "`mkdir build\\demo-20\\sources`")
        self.assertEqual(differences["`printf '1000 status\\n' > FILE`"], '`Set-Content FILE "1000 status"`')
        built = [(here, there) for here, there in differences.items() if here.startswith("`make -C core shared`")]
        self.assertEqual(len(built), 1)
        for word in ("`core/build/libodrig_core.dylib`",):
            self.assertIn(word, built[0][0])
        for word in ("`core/build.py shared`", "`core/build/odrig_core.dll`"):
            self.assertIn(word, built[0][1])
        ports = [(here, there) for here, there in differences.items() if "`serial:`" in here]
        self.assertEqual(len(ports), 1)
        self.assertIn("`--port build/emulator/serial`", ports[0][0])
        for word in ("`tcp: 127.0.0.1:8601`", "`--tcp 127.0.0.1:8601`"):
            self.assertIn(word, ports[0][1])
        from emulator import app, binding

        self.assertEqual((app.TCP_PORT, binding.library_of("win32")[0], binding.library_of("darwin")[0]), (8601, "odrig_core.dll", "libodrig_core.dylib"))
        used = flat(self.text.split("\n## Set up\n")[1])
        for here in ("mkdir -p build/demo-20/sources", "printf '1000 status\\n' > ", "--port build/emulator/serial", "make -C core shared", ".venv/bin/python"):
            self.assertIn(here, used, "the page no longer uses what the table translates")

    def test_the_setup_is_the_clone_the_environment_the_libraries_the_packages_and_the_shared_library(self):
        self.assertEqual(self.commands("Set up"), ["python3 -m venv .venv", "npm ci --prefix converter", "make -C core shared"])
        self.assertFalse((support.ROOT / "requirements.txt").exists())
        package = json.loads((support.ROOT / "converter" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(package["dependencies"]), ["ffmpeg-static", "omggif"])
        setup = flat(self.part("Set up"))
        for phrase in (f"`{CLONE}`", "nothing is installed into it", "needs only Python's own library", "the converter's two packages",
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
        for phrase in ("The first ends with a list of counts, in which `fail 0` says that every test passed", "Each of the others ends with the line `OK`", "leaves out the tests that are for the other system and says how many, as in `OK (skipped=9)`",
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
        # It has no cycle and no start: it plays its playlist.
        self.assertEqual(([item for item in show["items"] if "cycle" in item], "start" in show), ([], False))
        packed = flat(self.part("Pack the demo show"))
        for phrase in ("plays the two in turn from power-on, each for half a minute or more", "is test content for the target and not finished work", "two proof-of-concept animations"):
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
        for phrase in ('reply 1000 {"ok":true', '`"error":null`', '`"playing":"all"`', "the playlist is playing", "[reasons.md](../docs/reasons.md)"):
            self.assertIn(phrase, said)


if __name__ == "__main__":
    unittest.main()

import json
import re
import shlex
import unittest

from fwtool import cli, flasher
from odrig import mapping
from odrig.generators import hello_world

from . import ROOT

DOCUMENT = ROOT / "docs" / "firmware.md"
TEST_COMMANDS = {
    "test": "tests/firmware/",
    "test-board": "tests/board/",
    "test-air": "tests/air/",
}
OWNERS_CHECKS = 6
# The pins of the target file, and how many of the legs of a mapping file get an RMT output.
TARGET_PINS = [*range(1, 19), 21, 47]
RMT_OUTPUTS = 4


def section(text, title):
    """The text under a heading of the second level, up to the next one."""
    found = re.search(rf"(?ms)^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text)
    assert found, f"no section {title!r}"
    return found.group(1)


class Firmware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOCUMENT.read_text(encoding="utf-8")

    def commands(self):
        actions = next(action for action in cli.parser()._actions if getattr(action, "choices", None) and "build" in action.choices)
        return dict(actions.choices)

    def test_it_names_every_command_of_the_tool_with_a_section_and_an_example(self):
        commands = self.commands()
        self.assertEqual(set(commands), {"setup", "build", "flash", "restore-stock", "install-show", "read-show", "test", "test-board", "test-air"})
        for name in commands:
            self.assertRegex(self.text, rf"(?m)^### {re.escape(name)}$", name)
            self.assertRegex(self.text, rf"(?m)^python3 firmware/fw\.py {re.escape(name)}\b", name)

    def test_it_names_every_option_of_every_command(self):
        for name, command in self.commands().items():
            for action in command._actions:
                for option in action.option_strings:
                    if option.startswith("--") and option != "--help":
                        self.assertRegex(section(self.text, "Commands"), rf"(?m)^python3 firmware/fw\.py {re.escape(name)}\b.*{re.escape(option)}\b", f"{name} {option}")

    def test_it_names_the_three_test_commands_and_their_folders(self):
        for name, folder in TEST_COMMANDS.items():
            self.assertRegex(section(self.text, "Commands"), rf"(?s)### {re.escape(name)}\n.*?`{re.escape(folder)}`", name)

    def test_it_says_what_the_tool_needs_and_where_its_work_folder_is(self):
        needs = section(self.text, "What the tool needs")
        for expected in ("Apple's command-line developer tools", "git", "Python 3.10 or later"):
            self.assertIn(expected, needs)
        self.assertIn("build/firmware/", section(self.text, "The work folder"))

    def test_it_lists_the_regions_the_tools_write(self):
        regions = section(self.text, "The regions of the flash")
        for region in (flasher.BOOTLOADER, flasher.TABLE, flasher.BOOT_SELECTION, flasher.APPLICATION):
            self.assertRegex(regions, rf"(?im)^\| .* \| `0x{region.address:X}` \|", region.name)
        self.assertRegex(regions, r"(?m)^\| Storage \(`spiffs`\) \| `0x610000` \| `0x9E0000` \| `install-show`")
        for never in ("never erased", "fuse"):
            self.assertIn(never, regions)

    def test_it_says_how_to_roll_back(self):
        back = section(self.text, "Rolling back")
        self.assertIn("python3 firmware/fw.py restore-stock", back)
        self.assertIn("--full", back)
        self.assertIn("factory backup", back)

    def test_it_says_what_the_firmware_changes_in_wled_and_what_it_leaves(self):
        changes = section(self.text, "What the firmware changes in WLED")
        self.assertRegex(changes, r"(?m)^\| Changed \| Left as it is \|$")
        for expected in ("effects", "current limiter", "Wi-Fi", "serial"):
            self.assertIn(expected, changes)

    def test_it_lists_the_owners_checks_as_numbered_steps_with_what_must_be_seen(self):
        checks = section(self.text, "The owner's checks")
        steps = re.findall(r"(?m)^(\d+)\. \*\*(.+?) \((seed 05, )?(\d+\.\d+)\)\.\*\*", checks)
        self.assertEqual([number for number, _, _, _ in steps], [str(number) for number in range(1, OWNERS_CHECKS + 1)])
        self.assertEqual(len(re.findall(r"(?m)^\d+\. \*\*", checks)), OWNERS_CHECKS)
        bodies = re.split(r"(?m)^\d+\. \*\*", checks)[1:]
        self.assertEqual([body.count("*Seen:*") for body in bodies], [1] * OWNERS_CHECKS)
        for expected in ("power", "49", "python3 firmware/fw.py test-air --http 4.3.2.1", "http://4.3.2.1/"):
            self.assertIn(expected, checks)

    def test_the_owners_checks_of_the_target_are_a_strip_on_the_parallel_driver_and_twenty_wired_legs(self):
        checks = section(self.text, "The owner's checks")
        steps = re.findall(r"(?m)^(\d+)\. \*\*(.+?) \((seed 05, )?(\d+\.\d+)\)\.\*\*", checks)
        self.assertEqual([(number, criterion) for number, _, marked, criterion in steps if marked], [("5", "18.3"), ("6", "18.3")])
        self.assertEqual([criterion.split(".")[0] for _, _, marked, criterion in steps if not marked], ["16"] * 4)
        bodies = dict(zip((number for number, _, _, _ in steps), re.split(r"(?m)^\d+\. \*\*", checks)[1:]))
        self.assertIn("parallel driver", bodies["5"])
        self.assertIn("sixteenth lane", bodies["5"])
        for expected in ("twenty legs", "build/demo-20/show", "HELLO WORLD", "rows 28 to 33", "`20/20`"):
            self.assertIn(expected, " ".join(bodies["6"].split()))
        requirements = (ROOT / "docs" / "specs" / "05-p0-canvas-60-by-60" / "requirements.md").read_text(encoding="utf-8")
        asked = " ".join(requirements.split("\n## Requirement 18:")[1].split("\n3. ")[1].split("\n4. ")[0].split())
        self.assertIn("a strip on a pin of the parallel driver shows its picture", asked)
        self.assertIn("twenty wired legs show the demo show", asked)
        opening = " ".join(checks.split("\n1. **")[0].split())
        self.assertIn("Steps 5 and 6 stay listed as open and do not hold seed 05 open", opening)
        self.assertIn("does not reach 49 refreshes a second with a dense 60 x 60 clip", opening)

    def test_the_mapping_of_the_fifth_check_puts_the_wired_strip_on_the_last_lane_and_the_strip_shows_what_the_check_says(self):
        body = re.split(r"(?m)^\d+\. \*\*", section(self.text, "The owner's checks"))[5]
        blocks = [re.sub(r"(?m)^   ", "", block) for block in re.findall(r"(?s)```(?:json)?\n(.*?)```", body)]
        self.assertEqual(len(blocks), 3)
        written, commands, pattern = blocks
        canvas = mapping.loads(written.encode("utf-8"))
        self.assertEqual((canvas.kind, canvas.width, canvas.height), (mapping.ROWS, 60, 20))
        self.assertEqual([canvas.led_count(leg) for leg in canvas.legs], [60] * 20)
        self.assertEqual(sorted(leg.pin for leg in canvas.legs), TARGET_PINS)
        # The first legs of a file get the RMT outputs and the others the lanes of the
        # parallel driver in turn, so the last of twenty legs is on its sixteenth lane.
        self.assertEqual([leg.pin for leg in canvas.legs].index(1) - RMT_OUTPUTS + 1, 16)
        strip = canvas.legs[-1]
        self.assertEqual((strip.pin, strip.first_led, len(strip.strips)), (1, "right", 1))
        row = strip.strips[0]
        self.assertIn(f"the row y = {row},", body)
        lit = set(hello_world.lit_pixels(canvas.width, canvas.height))
        self.assertEqual(pattern.strip(), "".join("X" if (x, row) in lit else "." for x in range(1, canvas.width + 1)))
        self.assertEqual(min(y for _, y in lit), row)
        # The first LED of the strip, at its wired end, is the right end of the row.
        self.assertEqual(mapping.position(canvas, strip, 1), (canvas.width, row))
        lines = re.sub(r"\\\n\s*", "", commands).splitlines()
        show = json.loads(shlex.split(next(line for line in lines if line.startswith("printf ")))[1].replace("\\n", ""))
        self.assertLessEqual(show["brightness"], 40)
        self.assertEqual(show["items"], [{"id": 1, "file": "hello.odrg"}])
        for line in ("python -m odrig.generators.hello_world build/lane/sources/hello.json --mapping build/lane/mapping.json",
                     "python -m odrig pack --show build/lane/show.json --mapping build/lane/mapping.json --sources build/lane/sources --out build/lane/show",
                     "python3 firmware/fw.py install-show build/lane/show"):
            self.assertIn(line, lines)
        self.assertIn("`build/lane/mapping.json`", body)

    def test_it_gives_the_measurements_made_on_the_board(self):
        measured = section(self.text, "Measurements on the board")
        for expected in ("Start of the core", "Refreshes a second", "9 MB", "install-show"):
            self.assertIn(expected, measured)

    def test_the_readme_points_to_it(self):
        self.assertIn("[docs/firmware.md](docs/firmware.md)", (ROOT / "README.md").read_text(encoding="utf-8"))

import re
import unittest

from fwtool import cli, flasher

from . import ROOT

DOCUMENT = ROOT / "docs" / "firmware.md"
TEST_COMMANDS = {
    "test": "tests/firmware/",
    "test-board": "tests/board/",
    "test-air": "tests/air/",
}
OWNERS_CHECKS = 4


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
        steps = re.findall(r"(?m)^(\d+)\. \*\*", checks)
        self.assertEqual(steps, [str(number) for number in range(1, OWNERS_CHECKS + 1)])
        self.assertEqual(len(re.findall(r"\*Seen:\*", checks)), OWNERS_CHECKS)
        for expected in ("power", "49", "python3 firmware/fw.py test-air --http 4.3.2.1", "http://4.3.2.1/"):
            self.assertIn(expected, checks)

    def test_it_gives_the_measurements_made_on_the_board(self):
        measured = section(self.text, "Measurements on the board")
        for expected in ("Start of the core", "Refreshes a second", "9 MB", "install-show"):
            self.assertIn(expected, measured)

    def test_the_readme_points_to_it(self):
        self.assertIn("[docs/firmware.md](docs/firmware.md)", (ROOT / "README.md").read_text(encoding="utf-8"))

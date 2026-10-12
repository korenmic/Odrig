import json
import re
import shlex
import unittest

from fwtool import cli, flasher
from odrig import jsonframes, mapping, odrg
from odrig.generators import hello_world

from . import ROOT

DOCUMENT = ROOT / "docs" / "firmware.md"
TEST_COMMANDS = {
    "test": "tests/firmware/",
    "test-board": "tests/board/",
    "test-air": "tests/air/",
}
OWNERS_CHECKS = 7
# How a step of the owner's checks is headed: its number, what it is, and the criterion it
# covers, marked with the seed when it is not a criterion of seed 04.
STEP = r"(?m)^(\d+)\. \*\*(.+?) \((seed 0[57], )?(\d+\.\d+)\)\.\*\*"
# The pins of the target file, and how many of the legs of a mapping file get an RMT output.
TARGET_PINS = [*range(1, 19), 21, 47]
RMT_OUTPUTS = 4


def section(text, title):
    """The text under a heading of the second level, up to the next one."""
    found = re.search(rf"(?ms)^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text)
    assert found, f"no section {title!r}"
    return found.group(1)


def cells(line):
    """The cells of one line of a table."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


class Firmware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOCUMENT.read_text(encoding="utf-8")

    def commands(self):
        actions = next(action for action in cli.parser()._actions if getattr(action, "choices", None) and "build" in action.choices)
        return dict(actions.choices)

    def test_it_names_every_command_of_the_tool_with_a_section_and_an_example(self):
        commands = self.commands()
        self.assertEqual(set(commands), {"setup", "build", "flash", "restore-stock", "install-show", "set-wifi", "read-show", "test", "test-board", "test-air"})
        for name in commands:
            self.assertRegex(self.text, rf"(?m)^### {re.escape(name)}$", name)
            self.assertRegex(self.text, rf"(?m)^python3 firmware/fw\.py {re.escape(name)}\b", name)

    def test_it_names_every_option_of_every_command(self):
        for name, command in self.commands().items():
            for action in command._actions:
                for option in action.option_strings:
                    if option.startswith("--") and option != "--help":
                        self.assertRegex(section(self.text, "Commands"), rf"(?m)^python3 firmware/fw\.py {re.escape(name)}\b.*{re.escape(option)}\b", f"{name} {option}")

    def test_it_says_what_set_wifi_does_and_names_its_reasons(self):
        commands = section(self.text, "Commands")
        for reason in ("wifi-settings-missing", "wifi-settings-malformed", "wifi-name-invalid", "wifi-password-invalid", "wled-settings-malformed"):
            self.assertRegex(commands, rf"(?m)^\| `{reason}` \| ", reason)
        told = " ".join(commands.split("\n### set-wifi\n")[1].split("\n### ")[0].split())
        for expected in ("`name: <name>`", "`password: set`", "`firmware/wifi.json`", "`--settings FILE`", "`--wait SECONDS`", "1 to 32 characters", "8 to 63",
                         "printable ASCII", "`/cfg.json`", "`/wsec.json`", "`ap.ssid`", "`ap.pskl`", "`ap.psk`", "The password is never printed",
                         "no option and no variable carries either", "`no-reply`", "[wifi.md](wifi.md)"):
            self.assertIn(expected, told)
        self.assertRegex(section(self.text, "The regions of the flash"), r"(?m)^\| Storage \(`spiffs`\) \| .* \| `install-show` and `set-wifi`, changed blocks only \|$")

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
        steps = re.findall(STEP, checks)
        self.assertEqual([number for number, _, _, _ in steps], [str(number) for number in range(1, OWNERS_CHECKS + 1)])
        self.assertEqual(len(re.findall(r"(?m)^\d+\. \*\*", checks)), OWNERS_CHECKS)
        bodies = re.split(r"(?m)^\d+\. \*\*", checks)[1:]
        self.assertEqual([body.count("*Seen:*") for body in bodies], [1] * OWNERS_CHECKS)
        for expected in ("power", "49", "python3 firmware/fw.py test-air --http 4.3.2.1", "http://4.3.2.1/"):
            self.assertIn(expected, checks)

    def test_the_owners_checks_of_the_target_are_a_strip_on_the_parallel_driver_and_twenty_wired_legs(self):
        checks = section(self.text, "The owner's checks")
        steps = re.findall(STEP, checks)
        self.assertEqual([(number, criterion) for number, _, marked, criterion in steps if marked == "seed 05, "], [("5", "18.3"), ("6", "18.3")])
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
        self.assertIn("the owner accepts any rate from 20 to 50", opening)

    def test_the_owners_check_of_the_content_commands_is_an_upload_over_the_boards_network(self):
        from odrigctl import cli as command_tool

        checks = section(self.text, "The owner's checks")
        steps = re.findall(STEP, checks)
        self.assertEqual([(number, criterion) for number, _, marked, criterion in steps if marked == "seed 07, "], [("7", "21.5")])
        body = re.split(r"(?m)^\d+\. \*\*", checks)[7]
        (block,) = [re.sub(r"(?m)^   ", "", found) for found in re.findall(r"(?s)```\n(.*?)```", body)]
        lines = block.splitlines()
        self.assertEqual(lines[0], "node converter/odrig.js encode animations/hello.json build/hello-bench.odrg")
        made = command_tool.parser()
        sent = [command_tool.checked(made, made.parse_args(shlex.split(line)[3:])) for line in lines[1:]]
        self.assertEqual(sent, [["upload", "9", "build/hello-bench.odrg"], ["list"], ["play", "9"], ["remove", "9"], ["play", "3"]])
        self.assertTrue(all(line.startswith("python -m odrigctl --http 4.3.2.1 ") for line in lines[1:]))
        said = " ".join(body.split())
        for expected in ("`upload: checking`", '`{"id":9,"file":"hello-bench.odrg","bytes":1138}`', "`build/firmware/out/upload-air.json`", "`python3 firmware/fw.py test-air --http 4.3.2.1`"):
            self.assertIn(expected, said)
        requirements = (ROOT / "docs" / "specs" / "07-p1-content-commands" / "requirements.md").read_text(encoding="utf-8")
        asked = " ".join(requirements.split("\n## Requirement 21:")[1].split("\n5. ")[1].split("\n6. ")[0].split())
        self.assertIn("an animation SHALL be uploaded over HTTP, listed, played and removed", asked)
        opening = " ".join(checks.split("\n1. **")[0].split())
        self.assertIn("seed 07 when step 7 is done", opening)
        # The file of the step is the one the example show has as hello.odrg, under a name
        # no item has.
        self.assertEqual(len(odrg.encode(jsonframes.read(ROOT / "animations" / "hello.json"))), 1138)
        show = json.loads((ROOT / "shows" / "example" / "show.json").read_text(encoding="utf-8"))
        self.assertNotIn("hello-bench.odrg", [item.get("file") for item in show["items"]])
        self.assertNotIn(9, [item["id"] for item in show["items"]])

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
                     "node converter/odrig.js pack --show build/lane/show.json --mapping build/lane/mapping.json --sources build/lane/sources --out build/lane/show",
                     "python3 firmware/fw.py install-show build/lane/show"):
            self.assertIn(line, lines)
        self.assertIn("`build/lane/mapping.json`", body)

    def test_the_probe_report_has_the_access_points_name_and_protection(self):
        probe = " ".join(section(self.text, "The probe build").split())
        self.assertRegex(probe, r'"ap":1,"ap_name":"[^"]+","ap_auth":3,"error":null')
        for expected in ("| `ap_name` | The name in the configuration the radio holds for its access point", "| `ap_auth` | The protection in that configuration",
                         "0 open, 3 WPA2 with a password", "`null` while `ap` is 0"):
            self.assertIn(expected, probe)

    def test_it_says_what_the_firmware_writes_how_it_paces_and_what_an_upload_measured(self):
        does = " ".join(section(self.text, "What the firmware does").split())
        for expected in ("**Storage.**", "Every path is `/odrig/<name>`", "The firmware writes, renames and deletes a file only there", "`upload.part`", "`show.part`", "`pending.txt`",
                         "**Storage calls are paced.**", "the longer of 20 ms and twice d", "The port's queue for what arrives has 4,096 bytes",
                         "Of a body longer than 4,096 bytes the first 4,096 are passed on"):
            self.assertIn(expected, does)
        for function in ("write_open", "write", "write_close", "rename", "remove", "space", "read_at"):
            self.assertIn(f"| `{function}` | ", section(self.text, "What the firmware does"))
        probe = " ".join(section(self.text, "The probe build").split())
        for expected in ("`space_us`", "`store`", "`calls`", "`longest_us`", "`total_us`", "`check_steps`", "`check_longest_us`", "`check_total_us`", "`#store <bytes>`"):
            self.assertIn(expected, probe)
        measured = " ".join(section(self.text, "Measurements on the board").split())
        self.assertIn("**An upload over USB.**", measured)
        self.assertIn("`build/firmware/out/upload.json`", measured)
        self.assertRegex(measured, r"\*\*The speed\*\* was [\d,]+ bytes a second")
        self.assertRegex(measured, r"\*\*While the data arrived\*\* `status` reported \d+ to \d+ refreshes a second")
        self.assertRegex(measured, r"\*\*After `upload end`\*\* `status` reported \d+")
        self.assertRegex(measured, r"\*\*The storage calls\*\* .* the longest took \d+ ms")
        rates = [int(rate) for rate in re.search(r"`status` reported (\d+) to (\d+) refreshes a second", measured).groups()]
        self.assertTrue(all(20 <= rate <= 51 for rate in rates), rates)
        verified = " ".join(section(self.text, "Verified on the board").split())
        for letter in ("B1", "B2", "B3", "B4", "B5", "B6"):
            self.assertIn(f"| {letter} | ", verified)

    def test_it_gives_the_measurements_made_on_the_board(self):
        measured = section(self.text, "Measurements on the board")
        for expected in ("Start of the core", "Refreshes a second", "9 MB", "install-show"):
            self.assertIn(expected, measured)

    def test_its_first_table_of_measurements_has_every_value_for_the_demo_show_and_the_dense_clip_on_the_target(self):
        measured = section(self.text, "Measurements on the board")
        said = " ".join(measured.split())
        for expected in ("`tests/board/test_measure.py`", "`build/firmware/out/measurements.json`", "twenty outputs, four through WLED's RMT driver and sixteen through its parallel driver"):
            self.assertIn(expected, said)
        written = re.findall(r"(?m)((?:^\|.*\|\n)+)", measured)
        tables = [[cells(line) for line in table.splitlines()] for table in written]
        self.assertEqual(len(tables), 2)
        heading, _, *rows = tables[0]
        # The number of outputs, the start of the core, the refreshes sent in a second, the
        # longest time between two sends, the mean and the longest time of a request and
        # of a send, the free internal memory, and the time `install-show` takes.
        columns = {"Working outputs": r"\d+ of \d+", "`install-show`": r"\d+ s", "Start of the core": r"[\d,]+ ms", "Refreshes a second": r"\d+(?: (?:to|or) \d+)?",
                   "Longest gap": r"\d+ ms", "Request for a refresh, mean": r"[\d.]+ ms", "Send, mean": r"[\d.]+ ms", "Free internal memory": r"[\d,]+ bytes"}
        for name in columns:
            self.assertEqual(heading.count(name), 1, name)
        self.assertEqual([heading[heading.index(name) + 1] for name in ("Request for a refresh, mean", "Send, mean")], ["longest", "longest"])
        by_show = {row[0]: dict(zip(heading, row)) for row in rows}
        on_the_target = [show for show in by_show if show.startswith(("Demo show, the target file", "Dense 60 x 60 clip of 10 s, compressed, the target file", "The same clip, uncompressed"))]
        self.assertEqual(len(on_the_target), 3)
        for row in rows:
            self.assertEqual(len(row), len(heading), row[0])
            for name, figure in columns.items():
                self.assertRegex(row[heading.index(name)], rf"\A{figure}\Z", f"{row[0]}: {name}")
            for name in ("Request for a refresh, mean", "Send, mean"):
                self.assertRegex(row[heading.index(name) + 1], r"\A[\d.]+ ms\Z", f"{row[0]}: {name}, longest")
        for show in on_the_target:
            self.assertEqual(by_show[show]["Working outputs"], "20 of 20", show)
            # Every rate is one the owner accepts on the board: from 20 to 50, and a second
            # can count one refresh more than was due in it.
            rates = [int(number) for number in re.findall(r"\d+", by_show[show]["Refreshes a second"] + " " + by_show[show]["`fps` in `status`"])]
            self.assertTrue(all(20 <= rate <= 51 for rate in rates), (show, rates))
        # The second table is a record, and the text that leads to it says so.
        between = measured[measured.index(written[0]) + len(written[0]):measured.index(written[1])]
        self.assertIn("before the target became twenty upright legs", " ".join(between.split()))
        self.assertNotIn("Working outputs", tables[1][0])

    def test_it_says_how_many_outputs_the_firmware_drives_and_how(self):
        does = " ".join(section(self.text, "What the firmware does").split())
        for expected in ("one output for each leg, in the order of the mapping file, on the leg's pin, with the leg's number of LEDs, for WS2812B LEDs with the colour order green, red, blue",
                         "the first four legs of the mapping file get WLED's four RMT outputs and the next sixteen its parallel driver, so the board can drive 20 legs",
                         "An output that cannot be made, for a twenty-first leg or a pin the board cannot use, does not work; the other outputs do, and the core runs unchanged."):
            self.assertIn(expected, does)
        self.assertIn("**The firmware drives twenty outputs.** With the target file all twenty work, on pins 1 to 18, 21 and 47.", " ".join(section(self.text, "Measurements on the board").split()))

    def test_it_names_every_patch_file_and_every_file_of_wled_a_patch_changes(self):
        from .test_patches import changed_files, tracked_patches

        changes = section(self.text, "What the firmware changes in WLED")
        patches = tracked_patches()
        self.assertGreaterEqual(len(patches), 1)
        changed = sorted(name for patch in patches for name in changed_files(patch))
        self.assertEqual(sorted(re.findall(r"`firmware/patches/([^`]+\.patch)`", changes)), [patch.name for patch in patches])
        self.assertEqual(sorted(re.findall(r"(?m)^\| `([^`]+)` \| .+ \|$", changes)), changed)
        said = " ".join(changes.split())
        for expected in ("which `build` and `build --probe` apply and `build --stock` does not", "`WLED_MAX_I2S_CHANNELS` is 16 in place of 8", "sixteen-lane", "The usermod cannot do this from outside"):
            self.assertIn(expected, said)

    def test_the_rates_of_the_dense_clip_on_the_target_are_given_beside_what_the_owner_accepts(self):
        verified = " ".join(section(self.text, "Verified on the board").split())
        for expected in ("**What the owner accepts.** Any rate from 20 to 50 refreshes a second is fine on the board, for any content",
                         "| Compressed, 1,383,766 bytes | 22 to 24 | 36 to 42 |", "| Uncompressed, 1,462,236 bytes | 32 to 34 | 45 to 47 |",
                         "50 for the demo show on the target file, 36 to 42 for the dense 60 x 60 clip compressed and 45 to 47 uncompressed"):
            self.assertIn(expected, verified)
        decisions = (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")
        firmware = " ".join(decisions.split("\n## Firmware\n")[1].split("\n## ")[0].split())
        for expected in ("On the board any refresh rate from 20 to 50 a second is accepted, for any content.", "36 to 42 times for the compressed file and 45 to 47 for the uncompressed one"):
            self.assertIn(expected, firmware)

    def test_the_readme_points_to_it(self):
        self.assertIn("[docs/firmware.md](docs/firmware.md)", (ROOT / "README.md").read_text(encoding="utf-8"))

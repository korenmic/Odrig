import io
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

from emulator import app, binding, failure, hub, recfile
from odrig import odrg
from odrigctl import cli, content

from . import support
from .test_layout import dump, meetings

DOCUMENT = support.ROOT / "docs" / "emulator.md"
SPECS = support.ROOT / "docs" / "specs"

# The criteria that a person, or a tool that drives a browser, checks by looking at the
# page: those of the emulator's requirements, and those of the requirements of the 60 x 60
# canvas, which the check list marks with the name of their seed.
BY_EYE = ("4.2", "4.6", "4.8", "4.9", "8.1", "8.4", "9.1", "9.5", "9.8", "10.1", "14.5")
BY_EYE_ON_THE_TARGET = ("8.2", "8.6", "8.9", "9.2", "9.3", "9.4", "9.5", "9.8", "9.9", "10.1")
MARK_OF_THE_TARGET = "seed 05"


def criteria(listed):
    """The criteria a sentence of a requirements file names, as "8.2": it lists them as
    "Requirement 8 criteria 2, 6 and 9" and a run of them as "criteria 2 to 5"."""
    named = set()
    for number, numbers in re.findall(r"Requirement ([0-9]+)\s+criteri(?:a|on)\s+((?:[0-9]+|to|and|,|\s)+)", listed):
        numbers = re.sub(r"([0-9]+)\s+to\s+([0-9]+)", lambda run: " ".join(map(str, range(int(run.group(1)), int(run.group(2)) + 1))), numbers)
        named |= {f"{number}.{criterion}" for criterion in re.findall(r"[0-9]+", numbers)}
    return named


def section(text, heading):
    """The text under a heading of the second level, to the next one."""
    return text.split(f"\n## {heading}\n")[1].split("\n## ")[0]


def blocks(text):
    """The lines of the code blocks of a text, with lines that end in a backslash joined."""
    lines = []
    for block in re.findall(r"(?s)```\n(.*?)```", text):
        lines += re.sub(r"\\\n\s*", "", block).splitlines()
    return lines


class EmulatorDocument(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOCUMENT.read_text(encoding="utf-8")
        cls.commands = blocks(cls.text) + re.findall(r"`(python -m (?:emulator|odrigctl|odrig)[^`\n]*)`", cls.text)

    def test_it_has_a_section_for_everything_the_requirements_list(self):
        headings = re.findall(r"(?m)^##+ (.+)$", self.text)
        for heading in ("Commands", "Two shows to run", "Starting", "The serial port", "The line port", "Commands over HTTP", "The page", "The LEDs view", "The mapping view",
                        "The event stream", "The command tool", "Record mode", "The script", "The record file", "Exit statuses", "On Windows", "The check list by eye"):
            self.assertIn(heading, headings)
        for target in re.findall(r"\]\(#([a-z-]+)\)", self.text):
            self.assertIn(target, [heading.lower().replace(" ", "-") for heading in headings], target)

    def test_it_gives_the_command_that_builds_the_library_and_the_test_command_and_what_each_needs(self):
        rows = dict(re.findall(r"(?m)^\| `([^`]+)` \| .+ \| (.+) \|$", section(self.text, "Commands")))
        self.assertEqual(sorted(rows), ["make -C core shared", "python -m unittest discover -s tests/emulator -t .", "python core/build.py shared", "python3 -m unittest discover -s tests/emulator -t ."])
        self.assertIn("command-line developer tools", rows["make -C core shared"])
        self.assertIn("Python 3.10", rows["python3 -m unittest discover -s tests/emulator -t ."])
        self.assertIn("JavaScript shell", rows["python3 -m unittest discover -s tests/emulator -t ."])
        for needed in ("`g++` or `clang++`", "`tools/`", "Microsoft's C++ build tools", "No GNU Make"):
            self.assertIn(needed, rows["python core/build.py shared"])
        for needed in ("Python 3.10", "Node.js as the JavaScript shell"):
            self.assertIn(needed, rows["python -m unittest discover -s tests/emulator -t ."])
        self.assertIn(f"core/build/{binding.library_of('win32')[0]}", self.text)
        self.assertEqual(binding.library_of("win32")[1], "python core/build.py shared")
        makefile = (support.ROOT / "core" / "Makefile").read_text(encoding="utf-8")
        self.assertRegex(makefile, r"(?m)^shared: \$\(SHARED\)$")
        self.assertRegex(makefile, r"(?m)^\$\(SHARED\): \$\(OBJECTS\)\n\t\$\(CXX\) -dynamiclib -o \$@ \$\(OBJECTS\)$")
        self.assertRegex(makefile, r"(?m)^SHARED = \$\(BUILD\)/libodrig_core\.dylib$")
        self.assertRegex(makefile, r"(?m)^SOURCES = \$\(wildcard src/\*\.cpp\)$")
        self.assertIn("core/build/libodrig_core.dylib", self.text)

    def test_it_names_the_start_command_and_every_option_of_the_emulator(self):
        self.assertIn("python -m emulator SHOW_DIR [--port N] [--serial-link PATH] [--tcp-port N] [--core PATH] [--verbose] [--storage BYTES] [--lan] [--drive DIR]\n", self.text)
        self.assertIn("python -m emulator SHOW_DIR --record OUT --seconds S [--script FILE] [--core PATH] [--storage BYTES]\n", self.text)
        options = {option for action in app.parser()._actions for option in action.option_strings if option.startswith("--")} - {"--help"}
        self.assertEqual(options, {"--port", "--serial-link", "--tcp-port", "--core", "--verbose", "--storage", "--lan", "--drive", "--record", "--seconds", "--script"})
        self.assertIn("| `--storage BYTES` | The size of the storage the core is told of, as the total space of `space`: a whole number from 0 to 4,294,967,295. | 10,354,688, the size of the board's storage |", self.text)
        for option in sorted(options):
            self.assertRegex(self.text, rf"`{option}[ `]", option)
        self.assertIn("page: http://127.0.0.1:8600/", self.text)
        self.assertRegex(self.text, r"serial: \S+/build/emulator/serial")
        self.assertIn("| `--port N` | The port of the address on 127.0.0.1; 0 takes any free port. | 8600 |", self.text)

    def test_it_says_how_a_phone_reaches_the_emulator(self):
        said = " ".join(section(self.text, "From a phone").split())
        for phrase in ("python -m emulator build/demo-20/show --lan", "lan: http://192.168.1.23:8600/", "`lan: no address`",
                       "warning: --lan: anyone on the local network can send commands to this emulator and open its page", "The emulator has no password.",
                       "The serial port and the [line port](#the-line-port) stay on this computer.", "`--lan` does not go with `--record`"):
            self.assertIn(phrase, said)
        self.assertIn("warning: --lan: anyone on the local network can send commands to this emulator and open its page", (support.ROOT / "emulator" / "app.py").read_text(encoding="utf-8"))

    def test_every_emulator_command_it_gives_is_understood_by_the_emulator(self):
        given = [line for line in self.commands if line.startswith("python -m emulator ") and "[" not in line]
        self.assertGreaterEqual(len(given), 6)
        folders = set()
        for line in given:
            arguments = app.parse(shlex.split(line)[3:])
            folders.add(arguments.show_dir)
        self.assertLessEqual({"build/example-show", "build/demo-20/show", "build/dense/show", "build/example-broken"}, folders)
        self.assertTrue(any("--record build/example.odrr --seconds 60" in line for line in given))

    def test_it_names_every_command_of_the_tool_by_each_transport(self):
        text = section(self.text, "The command tool")
        given = [line for line in blocks(text) if line.startswith("python -m odrigctl ") and "(" not in line]
        made = cli.parser()
        sent = {"--port": set(), "--tcp": set(), "--http": set()}
        for line in given:
            arguments = made.parse_args(shlex.split(line)[3:])
            transport = "--port" if arguments.port is not None else "--tcp" if arguments.tcp is not None else "--http"
            sent[transport].add(cli.checked(made, arguments)[0])
        for transport in sent:
            self.assertEqual(sent[transport], set(cli.COMMANDS), transport)
        for command, takes in cli.COMMANDS.items():
            synopsis = " ".join(["python -m odrigctl (--port NAME | --tcp ADDRESS | --http ADDRESS) [--timeout SECONDS]", command, *takes])
            self.assertIn(synopsis + "\n", text)
        for status, meaning in ((0, '"ok":true'), (1, '"ok":false'), (2, "not understood"), (2, "error: not-found: <detail>"), (3, "error: unreachable: <detail>")):
            self.assertRegex(text, rf"(?m)^\| {status} \| .*{re.escape(meaning)}")
        self.assertIn("application/octet-stream", text)
        self.assertIn("lowers RTS before it lowers DTR", text)

    def test_it_describes_the_upload_of_the_tool_as_the_tool_does_it(self):
        text = " ".join(section(self.text, "The command tool").split())
        self.assertIn("upload: 45% 613500/1362000 bytes 21400 B/s", section(self.text, "The command tool"))
        written = io.StringIO()
        now = [0.0]
        progress = cli.Progress(written, clock=lambda: now[0])
        now[0] = 28.67
        progress.sent(613500, 1362000, 613500 / 21400)
        progress.checking()
        self.assertEqual(written.getvalue(), "upload: 45% 613500/1362000 bytes 21400 B/s\nupload: checking\n")
        for phrase in ("`upload: checking`", f"every {content.BUSY_PAUSE_SECONDS:g} seconds", f"{content.BUSY_SECONDS:g} seconds", "`upload cancel`", "`bad-offset`",
                       "the last part of the path", f"half a second", "keeps the port open", "`list <next>`"):
            self.assertIn(phrase, text)
        self.assertEqual(cli.REPORT_SECONDS, 0.5)
        for function in ("odrigctl.client.Session(port=..., http=..., timeout=...)", "odrigctl.content.list_all(session, show)", "odrigctl.content.upload(session, item, name, data, progress)"):
            self.assertIn(function, text)

    def test_every_tool_command_it_gives_anywhere_is_understood_by_the_tool(self):
        given = [line for line in self.commands if line.startswith("python -m odrigctl ") and "(" not in line]
        self.assertGreaterEqual(len(given), 21)
        made = cli.parser()
        for line in given:
            cli.checked(made, made.parse_args(shlex.split(line)[3:]))

    def test_it_describes_the_http_address_with_a_curl_example(self):
        text = section(self.text, "Commands over HTTP")
        self.assertIn("curl --data-binary 'play 2' http://127.0.0.1:8600/odrig", text)
        for phrase in ("`POST /odrig`", "Status 200", "`application/json`", "Status 405 with `Allow: POST`", "Status 411", "Status 404", "4,096", "2,048", "`Access-Control-Allow-Origin: *`"):
            self.assertIn(phrase, text)

    def test_it_describes_the_port(self):
        text = section(self.text, "The serial port")
        for phrase in ("pseudo-terminal", "symbolic link", "does not echo", "open and close the port any number of times", "Setting a speed", "DTR or RTS"):
            self.assertIn(phrase, text)

    def test_it_describes_the_two_views_the_status_and_the_log(self):
        text = section(self.text, "The page")
        for phrase in ("### The LEDs view", "### The mapping view", "`LEDs`", "`Mapping`", "brightness", "`core`", "`page`", "reason band", "command log",
                       "(1,1) at\nthe bottom-left", "`255 * (v / 255) ^ (1 / 2.2)`", "`emulator/web/board.js`", "`GPIO <pin>`", "Pointing", "sends no command"):
            self.assertIn(phrase, text)

    def test_its_events_are_the_ones_the_emulator_sends(self):
        text = section(self.text, "The event stream")
        events = dict(re.findall(r"event: ([a-z]+)\ndata: (.+)", text))
        self.assertEqual(sorted(events), ["frame", "hello", "log", "status"])
        self.assertEqual(sorted(json.loads(events["hello"])), ["drive", "error", "legs", "page", "serial", "show", "t0", "tcp"])
        entry = hub.Hub().log(5, "serial", b"play 2", False, b'{"ok":true}\n')
        self.assertEqual(sorted(json.loads(events["log"])), sorted(entry))
        self.assertEqual(sorted(json.loads(events["status"])), ["animation", "brightness", "error", "fps", "height", "ok", "on", "playing", "width"])
        self.assertRegex(events["frame"], r"\A[0-9]+ ")
        self.assertIn(str(hub.LOG_ENTRIES), text)
        self.assertIn("`: keep-alive`", text)

    def test_it_describes_the_record_mode_its_script_and_its_file(self):
        text = section(self.text, "Record mode")
        self.assertIn("### The script", text)
        self.assertIn("### The record file", text)
        table = text.split("| Offset | Size | Field | Value |\n|---:|---:|---|---|\n")[1].split("\n\n")[0]
        rows = [[cell.strip() for cell in row.strip("|").split("|")] for row in table.splitlines()]
        self.assertEqual([(int(offset), size) for offset, size, _, _ in rows], [(0, "4"), (4, "1"), (5, "1"), (6, "2"), (8, "4"), (12, "4"), (16, "8 * L")])
        self.assertEqual((recfile.HEADER.size, recfile.LEG.size, recfile.TICK.size), (16, 8, 9))
        self.assertIn("`4F 44 52 52`", text)
        self.assertEqual(bytes.fromhex("4F 44 52 52"), recfile.MAGIC)
        self.assertIn("`9 + B`", text)
        self.assertIn("reply 1010 ", text)
        self.assertIn("`OUT.part`", text)

    def test_its_table_of_failures_holds_every_reason_of_the_emulator(self):
        text = section(self.text, "Exit statuses")
        listed = re.findall(r"(?m)^\| `([a-z-]+)` \| ", text)
        self.assertEqual(sorted(listed), sorted(failure.REASONS))
        self.assertEqual(len(listed), 7)
        for status in (0, 1, 2):
            self.assertRegex(text, rf"(?m)^\| {status} \| ")
        self.assertIn("error: <reason>: <detail>", text)

    def test_it_describes_both_views_for_both_kinds_of_leg(self):
        leds = " ".join(self.text.split("\n### The LEDs view\n")[1].split("\n### ")[0].split())
        for phrase in ("**Row legs**", "**Column legs**", "feed edge", "leg band", "bracket", "written upright", "9 pixels or more", "twenty colours"):
            self.assertIn(phrase, leds)
        wired = " ".join(self.text.split("\n### The mapping view\n")[1].split("\n## ")[0].split())
        for phrase in ("**Row legs.**", "**Column legs.**", "level channel", "upright channel", "*Wide: the board beside the canvas.*", "*Narrow: the board below the canvas.*",
                       "*Level tracks.*", "*Upright tracks of the left row of pads*", "The short way", "The long way", "far edge", "turned over from top to bottom",
                       "**The snake of a leg**", "arrow head", "a bar"):
            self.assertIn(phrase, wired)

    def test_the_crossings_it_counts_for_the_target_file_are_those_of_the_lines_the_page_draws(self):
        wired = " ".join(self.text.split("\n### The mapping view\n")[1].split("\n## ")[0].split())
        counted = re.search(r"the lines of the target file cross ([0-9]+) times, in both arrangements", wired)
        self.assertIsNotNone(counted)
        arrangements = set()
        for mapped in dump(support.TARGET.read_text(encoding="utf-8"), areas=[[1280, 546], [756, 627]])["mapped"]:
            wires = mapped["wires"]
            crossings = [meetings(first["points"], second["points"])[0] for index, first in enumerate(wires) for second in wires[index + 1:]]
            self.assertEqual(sum(crossings), int(counted.group(1)), mapped["fit"]["arrangement"])
            self.assertLessEqual(max(crossings), 1)
            arrangements.add(mapped["fit"]["arrangement"])
        self.assertEqual(arrangements, {"wide", "narrow"})

    def test_the_sizes_it_gives_for_the_target_file_are_those_of_the_layout_script(self):
        wired = self.text.split("\n### The mapping view\n")[1].split("\n## ")[0]
        rows = re.findall(r"(?m)^\| ([0-9]+) x ([0-9]+) \| cells of ([0-9]+), (with|without) the LED numbers \| (wide|narrow), cells of ([0-9]+), the drawing ([0-9]+) x ([0-9]+) \|$", wired)
        areas = [[int(width), int(height)] for width, height, *_ in rows]
        self.assertLessEqual({(1280, 546), (756, 627)}, set(map(tuple, areas)))
        self.assertIn("1280 x 546 of a window of 1280 x 800", " ".join(wired.split()))
        self.assertIn("756 x 627 of a window of 756 x 900", " ".join(wired.split()))
        dumped = dump(support.TARGET.read_text(encoding="utf-8"), areas=areas)
        for row, fitted, mapped in zip(rows, dumped["fits"], dumped["mapped"]):
            f = mapped["fit"]
            found = (str(fitted["cell"]), "with" if fitted["numberTop"] else "without", f["arrangement"], str(f["cell"]), str(f["content"]["width"]), str(f["content"]["height"]))
            self.assertEqual(found, row[2:], row[:2])
        f = dumped["mapped"][0]["fit"]
        text = " ".join(wired.split())
        self.assertIn(f"the level channel is {f['level']['height']} pixels deep and the upright channel {f['upright']['width']} pixels wide", text)
        self.assertIn(f"the number bands are {f['numberTop']['height']} pixels high", text)

    def test_its_check_list_has_a_numbered_step_for_every_criterion_that_needs_eyes(self):
        text = section(self.text, "The check list by eye")
        steps = re.findall(rf"(?m)^([0-9]+)\. \*\*(.+?) \(({MARK_OF_THE_TARGET}, )?([0-9]+\.[0-9]+)\)\.\*\*", text)
        self.assertEqual([int(number) for number, _, _, _ in steps], list(range(1, len(steps) + 1)))
        self.assertEqual({criterion for _, _, marked, criterion in steps if not marked}, set(BY_EYE))
        self.assertEqual({criterion for _, _, marked, criterion in steps if marked}, set(BY_EYE_ON_THE_TARGET))
        bodies = re.split(r"(?m)^[0-9]+\. \*\*", text.split("\n### ")[0])[1:]
        self.assertEqual(len(bodies), len(steps))
        for body in bodies:
            self.assertEqual(body.count("*Seen:*"), 1, body[:60])
        for phrase in ("Safari", "Chrome", "1280 x 800", "756 x 900", "build/example-show", "build/dense/show", "build/demo-20/show", "`Mapping`", "file-missing dvd.odrg",
                       "docs/specs/03-p0-emulator/requirements.md", "docs/specs/05-p0-canvas-60-by-60/requirements.md"):
            self.assertIn(phrase, text)
        requirements = (SPECS / "03-p0-emulator" / "requirements.md").read_text(encoding="utf-8")
        self.assertEqual(criteria(requirements.split("each to be checked in Safari and in\n   Chrome:")[1].split("\n\n")[0]), set(BY_EYE))
        requirements = (SPECS / "05-p0-canvas-60-by-60" / "requirements.md").read_text(encoding="utf-8")
        asked = requirements.split("\n## Requirement 18:")[1].split("\n1. ")[1].split("\n2. ")[0]
        self.assertEqual(criteria(asked), set(BY_EYE_ON_THE_TARGET))

    def test_it_says_what_was_checked_how_and_what_is_left_for_a_person(self):
        checked = " ".join(section(self.text, "The check list by eye").split("\n### What has been checked\n")[1].split())
        for phrase in ("Chrome", "headless", "1280 x 800", "756 x 900", "screenshots", "`build/", "`page`", "Safari", "A person at a screen"):
            self.assertIn(phrase, checked)


class DocumentedShows(unittest.TestCase):
    """The commands the document gives for the two shows and for the dense clip, run as
    they are written, in a folder that has the repository's tracked folders linked in.
    The shows are packed by the converter, a program for Node.js, and their sources are
    written by the generators of the Python package."""

    PACK = "node converter/odrig.js pack "

    def test_the_commands_for_the_shows_pack_three_folders_the_emulator_runs(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        lines = blocks(section(text, "Two shows to run")) + blocks(section(text, "The check list by eye"))
        commands = [line for line in lines if line.split(" ")[0] in ("mkdir", "printf") or line.startswith(("python -m odrig", "node converter/"))]
        self.assertEqual(sum(line.startswith(self.PACK) for line in commands), 3)
        self.assertEqual(sum(line.startswith("node ") for line in commands), 3)
        self.assertEqual(sum(line.startswith("python -m odrig.generators.") for line in commands), 3)
        self.assertEqual(sum(line.startswith("python ") for line in commands), 3)
        for line in commands:
            self.assertNotRegex(line, r"\b(60|30)\b", line)
        node = shutil.which("node")
        self.assertIsNotNone(node, "the pack commands of the document need Node.js 20 or later as `node`: see docs/converter.md, \"Setup\"")
        with tempfile.TemporaryDirectory() as folder:
            work = pathlib.Path(folder)
            for name in ("odrig", "converter", "mapping", "shows", "animations"):
                support.linked(support.ROOT / name, work / name)
            for line in commands:
                words = shlex.split(line)
                if words[0] == "printf":
                    target = words[words.index(">") + 1]
                    (work / target).write_text(words[1].replace("\\n", "\n"), encoding="utf-8", newline="\n")
                    continue
                if words[0] == "mkdir" and shutil.which("mkdir") is None:
                    (work / words[-1]).mkdir(parents=True, exist_ok="-p" in words)
                    continue
                if words[0] == "python":
                    words[0] = sys.executable
                if words[0] == "node":
                    words[0] = node
                done = subprocess.run(words, cwd=work, capture_output=True, text=True)
                self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""), line)
            for show, legs in (("build/example-show", 2), ("build/demo-20/show", 20), ("build/dense/show", 20)):
                result = support.run(work / show, "--record", work / "out.odrr", "--seconds", "0.1")
                self.assertEqual((result.status, result.err), (0, ""), show)
                recording = recfile.read(work / "out.odrr")
                self.assertEqual(len(recording.legs), legs, show)
                self.assertEqual(recording.led_bytes, 540 * legs, show)
                self.assertTrue(all(tick.produced and any(tick.data) for tick in recording.ticks), show)
            packed = {path.name: path.read_bytes() for path in sorted((work / "build/demo-20/show").glob("*.odrg"))}
        # The table of the demo show's two files: the frames, and the sizes, which the
        # converter gives on every computer.
        rows = re.findall(r"(?m)^\| `([a-z]+\.odrg)`, ([0-9.]+) s \| ([0-9]+) \| ([0-9,]+) \|$", section(text, "Two shows to run"))
        self.assertEqual([name for name, _, _, _ in rows], ["hello.odrg", "dvd.odrg"])
        for name, seconds, frames, size in rows:
            records = odrg.decode(packed[name]).records
            self.assertEqual(len(records), int(frames), name)
            self.assertEqual(f"{sum(ms for ms, _ in records) / 1000:.1f}", seconds, name)
            self.assertEqual(len(packed[name]), int(size.replace(",", "")), name)


class Readme(unittest.TestCase):
    def test_it_points_to_the_emulator_document(self):
        text = (support.ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("(docs/emulator.md)", text)
        self.assertEqual(text.count("docs/emulator.md"), 2)


if __name__ == "__main__":
    unittest.main()

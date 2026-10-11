import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

from emulator import app, failure, hub, recfile
from odrigctl import cli

from . import support

DOCUMENT = support.ROOT / "docs" / "emulator.md"

# The criteria that a person, or a tool that drives a browser, checks by looking at the page.
BY_EYE = ("4.2", "4.6", "4.8", "4.9", "8.1", "8.4", "9.1", "9.5", "9.8", "10.1", "14.5")


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
        for heading in ("Commands", "Two shows to run", "Starting", "The serial port", "Commands over HTTP", "The page", "The LEDs view", "The mapping view",
                        "The event stream", "The command tool", "Record mode", "The script", "The record file", "Exit statuses", "The check list by eye"):
            self.assertIn(heading, headings)
        for target in re.findall(r"\]\(#([a-z-]+)\)", self.text):
            self.assertIn(target, [heading.lower().replace(" ", "-") for heading in headings], target)

    def test_it_gives_the_command_that_builds_the_library_and_the_test_command_and_what_each_needs(self):
        rows = dict(re.findall(r"(?m)^\| `([^`]+)` \| .+ \| (.+) \|$", section(self.text, "Commands")))
        self.assertEqual(sorted(rows), ["make -C core shared", "python3 -m unittest discover -s tests/emulator -t ."])
        self.assertIn("command-line developer tools", rows["make -C core shared"])
        self.assertIn("Python 3.10", rows["python3 -m unittest discover -s tests/emulator -t ."])
        self.assertIn("JavaScript shell", rows["python3 -m unittest discover -s tests/emulator -t ."])
        makefile = (support.ROOT / "core" / "Makefile").read_text(encoding="utf-8")
        self.assertRegex(makefile, r"(?m)^shared: \$\(SHARED\)$")
        self.assertRegex(makefile, r"(?m)^\$\(SHARED\): \$\(OBJECTS\)\n\t\$\(CXX\) -dynamiclib -o \$@ \$\(OBJECTS\)$")
        self.assertRegex(makefile, r"(?m)^SHARED = \$\(BUILD\)/libodrig_core\.dylib$")
        self.assertRegex(makefile, r"(?m)^SOURCES = \$\(wildcard src/\*\.cpp\)$")
        self.assertIn("core/build/libodrig_core.dylib", self.text)

    def test_it_names_the_start_command_and_every_option_of_the_emulator(self):
        self.assertIn("python -m emulator SHOW_DIR [--port N] [--serial-link PATH] [--core PATH] [--verbose]", self.text)
        self.assertIn("python -m emulator SHOW_DIR --record OUT --seconds S [--script FILE] [--core PATH]", self.text)
        options = {option for action in app.parser()._actions for option in action.option_strings if option.startswith("--")} - {"--help"}
        self.assertEqual(options, {"--port", "--serial-link", "--core", "--verbose", "--record", "--seconds", "--script"})
        for option in sorted(options):
            self.assertRegex(self.text, rf"`{option}[ `]", option)
        self.assertIn("page: http://127.0.0.1:8600/", self.text)
        self.assertRegex(self.text, r"serial: \S+/build/emulator/serial")
        self.assertIn("| `--port N` | The port of the address on 127.0.0.1; 0 takes any free port. | 8600 |", self.text)

    def test_every_emulator_command_it_gives_is_understood_by_the_emulator(self):
        given = [line for line in self.commands if line.startswith("python -m emulator ") and "[" not in line]
        self.assertGreaterEqual(len(given), 6)
        folders = set()
        for line in given:
            arguments = app.parse(shlex.split(line)[3:])
            folders.add(arguments.show_dir)
        self.assertLessEqual({"build/example-show", "build/demo-10/show", "build/dense/show", "build/example-broken"}, folders)
        self.assertTrue(any("--record build/example.odrr --seconds 60" in line for line in given))

    def test_it_names_every_command_of_the_tool_by_each_transport(self):
        text = section(self.text, "The command tool")
        given = [line for line in blocks(text) if line.startswith("python -m odrigctl ") and "(" not in line]
        made = cli.parser()
        sent = {"--port": set(), "--http": set()}
        for line in given:
            arguments = made.parse_args(shlex.split(line)[3:])
            transport = "--port" if arguments.port is not None else "--http"
            sent[transport].add(cli.command_line(made, arguments).decode("ascii").split()[0])
        self.assertEqual(sent["--port"], set(cli.COMMANDS))
        self.assertEqual(sent["--http"], set(cli.COMMANDS))
        for command, takes in cli.COMMANDS.items():
            synopsis = f"python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] {command}" + (f" {takes}" if takes else "")
            self.assertIn(synopsis, text)
        for status, meaning in ((0, '"ok":true'), (1, '"ok":false'), (2, "not understood"), (3, "error: unreachable: <detail>")):
            self.assertRegex(text, rf"(?m)^\| {status} \| .*{re.escape(meaning)}")
        self.assertIn("application/octet-stream", text)
        self.assertIn("lowers RTS before it lowers DTR", text)

    def test_every_tool_command_it_gives_anywhere_is_understood_by_the_tool(self):
        given = [line for line in self.commands if line.startswith("python -m odrigctl ") and "(" not in line]
        self.assertGreaterEqual(len(given), 13)
        made = cli.parser()
        for line in given:
            cli.command_line(made, made.parse_args(shlex.split(line)[3:]))

    def test_it_describes_the_http_address_with_a_curl_example(self):
        text = section(self.text, "Commands over HTTP")
        self.assertIn("curl --data-binary 'play 2' http://127.0.0.1:8600/odrig", text)
        for phrase in ("`POST /odrig`", "Status 200", "`application/json`", "Status 405 with `Allow: POST`", "Status 411", "Status 404", "128", "`Access-Control-Allow-Origin: *`"):
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
        self.assertEqual(sorted(json.loads(events["hello"])), ["error", "legs", "page", "serial", "show", "t0"])
        entry = hub.Hub().log(5, "serial", b"play 2", False, b'{"ok":true}\n')
        self.assertEqual(sorted(json.loads(events["log"])), sorted(entry))
        self.assertEqual(sorted(json.loads(events["status"])), ["animation", "brightness", "error", "fps", "ok", "on", "playing"])
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

    def test_its_check_list_has_a_numbered_step_for_every_criterion_that_needs_eyes(self):
        text = section(self.text, "The check list by eye")
        steps = re.findall(r"(?m)^([0-9]+)\. \*\*(.+?) \(([0-9]+\.[0-9]+)\)\.\*\*", text)
        self.assertEqual([int(number) for number, _, _ in steps], list(range(1, len(steps) + 1)))
        self.assertEqual({criterion for _, _, criterion in steps}, set(BY_EYE))
        self.assertGreaterEqual(len(steps), len(BY_EYE))
        bodies = re.split(r"(?m)^[0-9]+\. \*\*", text)[1:]
        self.assertEqual(len(bodies), len(steps))
        for body in bodies:
            self.assertIn("*Seen:*", body)
        for phrase in ("Safari", "Chrome", "1280 x 800", "build/example-show", "build/dense/show", "build/demo-10/show", "`Mapping`", "file-missing dvd.odrg"):
            self.assertIn(phrase, text)
        requirements = (support.ROOT / "docs" / "specs" / "03-p0-emulator" / "requirements.md").read_text(encoding="utf-8")
        listed = requirements.split("each to be checked in Safari and in\n   Chrome:")[1].split("\n\n")[0]
        named = set()
        for number, criteria in re.findall(r"Requirement ([0-9]+)\s+criteri(?:a|on)\s+([0-9, and\n]+)", listed):
            named |= {f"{number}.{criterion}" for criterion in re.findall(r"[0-9]+", criteria)}
        self.assertEqual(named, set(BY_EYE))


class DocumentedShows(unittest.TestCase):
    """The commands the document gives for the two shows and for the dense clip, run as
    they are written, in a folder that has the repository's tracked folders linked in."""

    def test_the_commands_for_the_shows_pack_three_folders_the_emulator_runs(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        lines = blocks(section(text, "Two shows to run")) + blocks(section(text, "The check list by eye"))
        commands = [line for line in lines if line.split(" ")[0] in ("mkdir", "printf") or line.startswith("python -m odrig")]
        self.assertEqual(sum(line.startswith("python -m odrig pack ") for line in commands), 3)
        self.assertEqual(sum(line.startswith("python -m odrig.generators.") for line in commands), 3)
        for line in commands:
            self.assertNotRegex(line, r"\b(60|30)\b", line)
        with tempfile.TemporaryDirectory() as folder:
            work = pathlib.Path(folder)
            for name in ("odrig", "mapping", "shows", "animations"):
                os.symlink(support.ROOT / name, work / name)
            for line in commands:
                words = shlex.split(line)
                if words[0] == "printf":
                    target = words[words.index(">") + 1]
                    (work / target).write_text(words[1].replace("\\n", "\n"), encoding="utf-8")
                    continue
                if words[0] == "python":
                    words[0] = sys.executable
                done = subprocess.run(words, cwd=work, capture_output=True, text=True)
                self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""), line)
            for show, legs in (("build/example-show", 2), ("build/demo-10/show", 10), ("build/dense/show", 10)):
                result = support.run(work / show, "--record", work / "out.odrr", "--seconds", "0.1")
                self.assertEqual((result.status, result.err), (0, ""), show)
                recording = recfile.read(work / "out.odrr")
                self.assertEqual(len(recording.legs), legs, show)
                self.assertTrue(all(tick.produced and any(tick.data) for tick in recording.ticks), show)


class Readme(unittest.TestCase):
    def test_it_points_to_the_emulator_document(self):
        text = (support.ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("(docs/emulator.md)", text)
        self.assertEqual(text.count("docs/emulator.md"), 2)


if __name__ == "__main__":
    unittest.main()

import json
import pathlib
import re
import subprocess
import tempfile
import unittest

from . import FIRMWARE, ROOT

USERMOD = FIRMWARE / "usermod"
SOURCES = sorted(path for path in USERMOD.iterdir() if path.suffix in (".cpp", ".h"))
ALLOWED_HEADERS = {"wled.h", "stddef.h", "stdint.h"}
PROBE_FILES = {"odrig_probe.h", "odrig_probe.cpp"}

PATTERN_MAIN = r"""
#include <stdio.h>
#include "odrig_pattern.h"
int main() {
  OdrigPattern::begin();
  OdrigLegSource legs = OdrigPattern::legs();
  for (uint32_t i = 0; i < legs.count(); i++) {
    OdrigLeg leg;
    if (!legs.leg(i, &leg)) return 1;
    printf("%u %u %u", (unsigned)leg.leg, (unsigned)leg.pin, (unsigned)leg.led_count);
    for (uint32_t n = 0; n < leg.led_count * 3; n++) printf(" %u", (unsigned)leg.rgb[n]);
    printf("\n");
  }
  OdrigLeg none;
  return legs.leg(legs.count(), &none) ? 1 : 0;
}
"""


def text_of(path):
    return path.read_text(encoding="utf-8")


def included(path):
    return re.findall(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', text_of(path), re.M)


def outside_probe_blocks(text):
    """The lines of a source that are compiled without ODRIG_PROBE."""
    kept, depth, probe_depth, in_else = [], 0, None, False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#if"):
            depth += 1
            if probe_depth is None and re.fullmatch(r"#ifdef\s+ODRIG_PROBE", stripped):
                probe_depth, in_else = depth, False
                continue
        elif stripped.startswith("#else") and probe_depth == depth:
            in_else = True
            continue
        elif stripped.startswith("#endif"):
            if probe_depth == depth:
                probe_depth = None
                depth -= 1
                continue
            depth -= 1
        if probe_depth is None or in_else:
            kept.append(line)
    return "\n".join(kept)


class TheLibrary(unittest.TestCase):
    def test_the_usermod_is_a_library_named_odrig_that_is_linked_directly(self):
        self.assertEqual(json.loads(text_of(USERMOD / "library.json")), {"name": "odrig", "build": {"libArchive": False}, "dependencies": {}})

    def test_it_has_the_sources_this_test_reads(self):
        names = {path.name for path in SOURCES}
        for expected in ("odrig_usermod.cpp", "odrig_leds.h", "odrig_leds.cpp", "odrig_serial.h", "odrig_serial.cpp", "odrig_probe.h", "odrig_probe.cpp"):
            self.assertIn(expected, names)

    def test_one_object_is_registered_as_a_usermod(self):
        registered = [(path.name, name) for path in SOURCES for name in re.findall(r"^REGISTER_USERMOD\((\w+)\);", text_of(path), re.M)]
        self.assertEqual(registered, [("odrig_usermod.cpp", "odrigUsermod")])
        self.assertRegex(text_of(USERMOD / "odrig_usermod.cpp"), r"class OdrigUsermod : public Usermod")


class Includes(unittest.TestCase):
    def test_the_sources_include_only_wleds_header_and_their_own(self):
        own = {path.name for path in SOURCES if path.suffix == ".h"}
        for path in SOURCES:
            for header in included(path):
                self.assertIn(header, ALLOWED_HEADERS | own, f"{path.name} includes {header}")

    def test_the_port_is_named_only_where_it_is_handled(self):
        naming = {path.name for path in SOURCES if re.search(r"\bSerial\b", text_of(path))}
        self.assertEqual(naming, {"odrig_serial.cpp", "odrig_probe.cpp"})

    def test_the_usermod_names_no_function_of_wleds_serial_handling(self):
        for path in SOURCES:
            self.assertNotRegex(text_of(path), r"handleSerial|handleImprov|Adalight", path.name)


class ProbeCode(unittest.TestCase):
    def test_the_probe_files_are_empty_without_the_probe_flag(self):
        for name in sorted(PROBE_FILES):
            left = outside_probe_blocks(text_of(USERMOD / name))
            code = [line for line in left.splitlines() if line.strip() and not line.strip().startswith("//") and line.strip() != "#pragma once"]
            self.assertEqual(code, [], name)

    def test_every_other_use_of_the_probe_is_inside_the_probe_flag(self):
        for path in SOURCES:
            if path.name in PROBE_FILES:
                continue
            self.assertNotRegex(outside_probe_blocks(text_of(path)), r"OdrigProbe|odrig_probe", path.name)

    def test_the_reader_of_this_test_tells_the_two_builds_apart(self):
        text = "a\n#ifdef ODRIG_PROBE\nprobe\n#ifdef X\nx\n#endif\n#else\nplain\n#endif\nb"
        self.assertEqual(outside_probe_blocks(text), "a\nplain\nb")


class ThePattern(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as folder:
            main = pathlib.Path(folder, "main.cpp")
            main.write_text(PATTERN_MAIN)
            program = pathlib.Path(folder, "pattern")
            subprocess.run(["c++", "-std=c++11", "-Wall", "-Werror", f"-I{USERMOD}", str(main), str(USERMOD / "odrig_pattern.cpp"), "-o", str(program)], check=True, cwd=ROOT)
            printed = subprocess.run([str(program)], capture_output=True, text=True, check=True).stdout
        cls.legs = [[int(word) for word in line.split()] for line in printed.splitlines()]

    def test_it_lists_ten_legs_on_pins_1_to_10_with_180_leds_each(self):
        self.assertEqual([leg[:3] for leg in self.legs], [[number, number, 180] for number in range(1, 11)])

    def test_no_value_is_above_40(self):
        self.assertEqual(max(max(leg[3:]) for leg in self.legs), 40)

    def test_every_led_has_a_colour_of_its_own(self):
        colours = [tuple(leg[3 + 3 * n:6 + 3 * n]) for leg in self.legs for n in range(180)]
        self.assertEqual(len(set(colours)), 1800)

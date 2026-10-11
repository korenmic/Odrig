import json
import pathlib
import re
import subprocess
import unittest

from . import FIRMWARE, ROOT

USERMOD = FIRMWARE / "usermod"
SOURCES = sorted(path for path in USERMOD.iterdir() if path.suffix in (".cpp", ".h"))
CORE = ROOT / "core"
ALLOWED_HEADERS = {"wled.h", "odrig_core.h", "stddef.h", "stdint.h"}
# The one header of the chip's own software that a source names: the USB unit behind the
# port, which the port's driver does not let through.
ALLOWED_IN = {"odrig_serial.cpp": {"hal/usb_serial_jtag_ll.h"}}
PROBE_FILES = {"odrig_probe.h", "odrig_probe.cpp"}

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
        for expected in ("odrig_usermod.cpp", "odrig_files.h", "odrig_files.cpp", "odrig_leds.h", "odrig_leds.cpp", "odrig_serial.h", "odrig_serial.cpp", "odrig_probe.h", "odrig_probe.cpp"):
            self.assertIn(expected, names)
        self.assertNotIn("odrig_pattern.cpp", names)

    def test_one_object_is_registered_as_a_usermod(self):
        registered = [(path.name, name) for path in SOURCES for name in re.findall(r"^REGISTER_USERMOD\((\w+)\);", text_of(path), re.M)]
        self.assertEqual(registered, [("odrig_usermod.cpp", "odrigUsermod")])
        self.assertRegex(text_of(USERMOD / "odrig_usermod.cpp"), r"class OdrigUsermod : public Usermod")


class Includes(unittest.TestCase):
    def test_the_sources_include_only_wleds_header_and_their_own(self):
        own = {path.name for path in SOURCES if path.suffix == ".h"}
        for path in SOURCES:
            for header in included(path):
                self.assertIn(header, ALLOWED_HEADERS | own | ALLOWED_IN.get(path.name, set()), f"{path.name} includes {header}")

    def test_the_port_is_named_only_where_it_is_handled(self):
        naming = {path.name for path in SOURCES if re.search(r"\bSerial\b", text_of(path))}
        self.assertEqual(naming, {"odrig_serial.cpp"})

    def test_the_core_is_called_only_by_the_usermod_itself(self):
        calling = {path.name for path in SOURCES if re.search(r"\bodrig_core_\w+\(", text_of(path))}
        self.assertEqual(calling, {"odrig_usermod.cpp"})

    def test_every_call_to_the_core_after_its_start_is_made_with_the_lock_held(self):
        text = text_of(USERMOD / "odrig_usermod.cpp")
        calls = [match for match in re.finditer(r"\bodrig_core_(\w+)\(", text) if match.group(1) != "begin"]
        self.assertGreaterEqual(len(calls), 3)
        for call in calls:
            block = text[text.rfind("\n}", 0, call.start()):call.start()]
            self.assertRegex(block, r"\bLocked held;", f"odrig_core_{call.group(1)}")

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


class TheCore(unittest.TestCase):
    def test_the_core_is_a_library_named_odrig_core_for_every_platform(self):
        self.assertEqual(json.loads(text_of(CORE / "library.json")), {"name": "odrig_core", "version": "1.0.0", "frameworks": "*", "platforms": "*"})

    def test_no_file_under_firmware_has_the_name_of_a_file_of_the_core(self):
        core_names = {path.name for path in (CORE / "src").iterdir()} | {path.name for path in (CORE / "include").iterdir()}
        self.assertIn("player.cpp", core_names)
        tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "firmware"], capture_output=True, text=True, check=True).stdout.split()
        under_firmware = {pathlib.Path(name).name for name in tracked} | {path.name for path in USERMOD.iterdir()}
        self.assertEqual(under_firmware & core_names, set())

    def test_the_build_names_the_core_as_a_library_where_it_is(self):
        template = text_of(FIRMWARE / "platformio_override.ini.in")
        self.assertRegex(template, r"(?m)^lib_deps = \$\{esp32s3\.lib_deps\}\n  odrig_core = symlink://@REPO@/core$")
        self.assertRegex(template, r"(?m)^  -I@REPO@/core/include$")

    def test_the_usermod_has_no_decoder_mapping_show_or_command_code_of_its_own(self):
        for path in SOURCES:
            self.assertNotRegex(text_of(path), r"inflate|first_led|\bcycle\b|\"play\"|\"brightness\"|unknown-command", path.name)

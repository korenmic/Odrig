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
# The headers of the chip's own software that a source names: the USB unit behind the
# port, which the port's driver does not let through; and, in the probe build, the pulse
# counter, the routing of a pin to it, and the LCD unit, which is the parallel driver.
ALLOWED_IN = {
    "odrig_serial.cpp": {"hal/usb_serial_jtag_ll.h"},
    "odrig_probe.cpp": {"driver/pcnt.h", "esp_rom_gpio.h", "soc/lcd_cam_struct.h", "soc/pcnt_periph.h"},
}
PROBE_FILES = {"odrig_probe.h", "odrig_probe.cpp"}
# What the probe build measures of the signal itself: named nowhere else.
SIGNAL_MEASURES = r"pcnt_|PCNT_|LCD_CAM|wire_us|\bpulses\b|esp_timer_create|esp_timer_start"

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
        for expected in ("odrig_usermod.cpp", "odrig_files.h", "odrig_files.cpp", "odrig_leds.h", "odrig_leds.cpp", "odrig_serial.h", "odrig_serial.cpp", "odrig_http.h", "odrig_http.cpp", "odrig_probe.h", "odrig_probe.cpp"):
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


class WebServer(unittest.TestCase):
    def test_one_handler_is_registered_for_the_command_path(self):
        registered = [(path.name, match) for path in SOURCES for match in re.findall(r"\bserver\.on\(([^,]+),", text_of(path))]
        self.assertEqual(registered, [("odrig_http.cpp", "PATH")])
        self.assertRegex(text_of(USERMOD / "odrig_http.cpp"), r'const char PATH\[\] = "/odrig";')

    def test_the_handler_answers_as_the_commands_document_defines(self):
        text = text_of(USERMOD / "odrig_http.cpp")
        for expected in ("HTTP_POST", "405", 'F("Allow"), F("POST")', "404", 'F("application/json")', "BODY_BYTES = 128"):
            self.assertIn(expected, text)

    def test_the_usermod_names_no_wifi_function_of_wled(self):
        for path in SOURCES:
            self.assertNotRegex(text_of(path), r"\bWiFi\b|initAP|initConnection|apSSID|apPass|multiWiFi|forceReconnect|WLED_CONNECTED", path.name)

    def test_the_captive_portal_is_kept_answering_and_an_update_stops_the_loop_first(self):
        text = text_of(USERMOD / "odrig_usermod.cpp")
        self.assertIn("if (apActive) dnsServer.processNextRequest();", text)
        loop = text[text.index("void loop() override {"):]
        first = [line.strip() for line in loop.splitlines()[1:] if line.strip() and not line.strip().startswith("//")][0]
        self.assertEqual(first, "if (updating) return;")
        self.assertIn("void onUpdateBegin(bool begins) override { updating = begins; }", text)

    def test_the_information_has_the_three_entries(self):
        text = text_of(USERMOD / "odrig_usermod.cpp")
        for entry in ("odrig show", "odrig outputs", "odrig start"):
            self.assertIn(f'F("{entry}")', text)


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

    def test_the_pulse_counter_and_the_wire_time_are_in_the_probe_files_only(self):
        probe = text_of(USERMOD / "odrig_probe.cpp")
        for expected in ("pcnt_unit_config", "pcnt_get_counter_value", "PIN_INPUT_ENABLE", "esp_rom_gpio_connect_in_signal", "LCD_CAM.lcd_user.lcd_start", '\\"wire_us\\":', '\\"pulses\\":'):
            self.assertIn(expected, probe)
        for path in SOURCES:
            if path.name not in PROBE_FILES:
                self.assertNotRegex(text_of(path), SIGNAL_MEASURES, path.name)

    def test_the_counter_leaves_what_the_pin_puts_out_alone(self):
        probe = text_of(USERMOD / "odrig_probe.cpp")
        self.assertIn("config.pulse_gpio_num = PCNT_PIN_NOT_USED;", probe)
        self.assertNotRegex(probe, r"gpio_set_direction|pinMode|gpio_config\b|pcnt_set_pin")

    def test_a_long_line_of_the_probe_build_is_written_without_waiting_for_the_port(self):
        serial = text_of(USERMOD / "odrig_serial.cpp")
        self.assertNotRegex(outside_probe_blocks(serial), r"writeLong|longLine")
        self.assertIn("OdrigSerial::writeLong(line.c_str(), line.length());", text_of(USERMOD / "odrig_probe.cpp"))
        self.assertIn("if (longLineWaits()) return;", serial)

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


class Host(unittest.TestCase):
    """What the usermod gives the core, read in its sources."""

    @classmethod
    def setUpClass(cls):
        cls.files = text_of(USERMOD / "odrig_files.cpp")
        cls.leds = text_of(USERMOD / "odrig_leds.cpp")

    def test_memory_comes_from_the_internal_memory_before_the_external(self):
        internal, external = self.files.index("MALLOC_CAP_INTERNAL"), self.files.index("MALLOC_CAP_SPIRAM")
        self.assertLess(internal, external)
        self.assertRegex(self.files, r"if \(block == nullptr\) block = heap_caps_aligned_alloc\(8, bytes, MALLOC_CAP_SPIRAM")
        self.assertNotRegex(self.files, r"\bfree\(|heap_caps_free")

    def test_the_time_is_the_64_bit_clock_since_start_in_milliseconds(self):
        self.assertIn("uint64_t OdrigFiles::nowMs() { return (uint64_t)esp_timer_get_time() / 1000; }", self.files)
        for path in SOURCES:
            self.assertNotRegex(text_of(path).replace("lastAsked = millis();", "").replace("const uint32_t now = millis();", ""), r"odrig_core_\w+\([^)]*millis\(\)", path.name)

    def test_files_are_read_from_the_shows_folder_in_the_pieces_the_core_asks_for(self):
        self.assertIn('const char FOLDER[] = "/odrig/";', self.files)
        self.assertIn('WLED_FS.open(path, "r")', self.files)
        self.assertIn("openFile.read(buffer, capacity)", self.files)

    def test_nothing_writes_creates_or_deletes_a_file(self):
        for path in SOURCES:
            text = text_of(path)
            self.assertNotRegex(text, r"WLED_FS\.(remove|mkdir|rmdir|rename|format)\b", path.name)
            self.assertNotRegex(text, r'\.open\([^)]*"(w|a|r\+)[^"]*"\)', path.name)
            self.assertNotRegex(text, r"serializeConfig|writeObjectToFile|doSerializeConfig|configNeedsWrite", path.name)

    def test_each_leg_becomes_a_ws2812b_output_in_green_red_blue_with_wleds_led_current(self):
        described = self.leds[self.leds.index("void describeOutputs()"):self.leds.index("void startOutputsAfterAFailedOne()")]
        self.assertRegex(described, r"busConfigs\.emplace_back\(TYPE_WS2812_RGB, pins, keptStart\(start\), keptLength\(leg\.led_count\), COL_ORDER_GRB,")
        self.assertIn("LED_MILLIAMPS_DEFAULT", described)
        self.assertIn("(uint8_t)leg.pin, 255, 255, 255, 255", described)

    def test_a_refresh_goes_to_the_outputs_directly_at_full_brightness(self):
        fill = self.leds[self.leds.index("void OdrigLeds::fill()"):self.leds.index("void OdrigLeds::show()")]
        show = self.leds[self.leds.index("void OdrigLeds::show()"):self.leds.index("void OdrigLeds::dark()")]
        for expected in ("BusManager::setBrightness(255);", "Bus::setCCT(-1);", "bus->setPixelColor(n, RGBW32(rgb[0], rgb[1], rgb[2], 0));"):
            self.assertIn(expected, fill)
        self.assertNotIn("show()", fill.split("{", 1)[1])
        self.assertIn("BusManager::show();", show)
        self.assertNotRegex(fill + show, r"\bstrip\.")

    def test_a_refresh_is_filled_at_once_and_shown_when_the_outputs_can_take_data(self):
        usermod = text_of(USERMOD / "odrig_usermod.cpp")
        loop = outside_probe_blocks(usermod[usermod.index("void loop() override {"):usermod.index("void addToJsonInfo")])
        steps = [loop.index(step) for step in ("refreshWaits = refreshDue();", "OdrigLeds::fill();", "if (!BusManager::canAllShow()) return;", "OdrigLeds::show();", "refreshWaits = refreshFilled = false;")]
        self.assertEqual(steps, sorted(steps))
        self.assertEqual((loop.count("OdrigLeds::fill();"), loop.count("OdrigLeds::show();"), loop.count("refreshDue()")), (1, 1, 1))
        self.assertIn("if (!refreshFilled) {", loop)

    def test_wled_is_held_in_its_live_mode_at_every_pass(self):
        hold = self.leds[self.leds.index("void OdrigLeds::hold()"):self.leds.index("void OdrigLeds::fill()")]
        for expected in ("realtimeOverride = REALTIME_OVERRIDE_NONE;", "useMainSegmentOnly = false;", "realtimeLock(65000, REALTIME_MODE_GENERIC);", "if (doInitBusses)", "else if (!matches())"):
            self.assertIn(expected, hold)
        usermod = text_of(USERMOD / "odrig_usermod.cpp")
        self.assertEqual(usermod.count("OdrigLeds::hold();"), 2)

    def test_the_limiters_maximum_is_never_set_by_the_usermod(self):
        for path in SOURCES:
            self.assertNotRegex(text_of(path), r"setMilliampsMax|_gMilliAmpsMax\s*=", path.name)

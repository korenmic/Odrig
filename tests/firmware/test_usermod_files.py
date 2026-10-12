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
        for expected in ("HTTP_POST", "405", 'F("Allow"), F("POST")', "404", 'F("application/json")', "const size_t BODY_BYTES = 4096;"):
            self.assertIn(expected, text)

    def test_the_body_and_the_reply_of_a_request_are_memory_of_the_request_and_not_of_a_stack(self):
        text = text_of(USERMOD / "odrig_http.cpp")
        kept = text[text.index("struct Kept {"):text.index("};", text.index("struct Kept {"))]
        self.assertIn("char bytes[BODY_BYTES];", kept)
        self.assertIn("char reply[ODRIG_REPLY_MAX + 1];", kept)
        self.assertIn("if (request->_tempObject == nullptr) request->_tempObject = calloc(1, sizeof(Kept));", text)
        outside = text.replace(kept, "")
        self.assertNotRegex(outside, r"\bchar\s+\w+\[[^\]]*(BODY_BYTES|ODRIG_REPLY_MAX|1024|1025|4096)[^\]]*\]")
        self.assertIn("commandNow(kept->bytes, kept->length, kept->reply, ODRIG_REPLY_MAX)", text)

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


class TheTask(unittest.TestCase):
    """The task that asks the core for refreshes, read in the usermod's sources."""

    @classmethod
    def setUpClass(cls):
        cls.usermod = text_of(USERMOD / "odrig_usermod.cpp")
        cls.task = outside_probe_blocks(cls.usermod[cls.usermod.index("void requestRefreshes(void *) {"):cls.usermod.index("#ifdef ODRIG_PROBE\nconst char *errorNow() {")])

    def test_the_usermod_starts_one_task_in_its_own_file_only(self):
        starting = {path.name: len(re.findall(r"\bxTaskCreate\w*\(", text_of(path))) for path in SOURCES}
        self.assertEqual({name: count for name, count in starting.items() if count}, {"odrig_usermod.cpp": 1})
        self.assertIn("xTaskCreatePinnedToCore(requestRefreshes, TASK_NAME, TASK_STACK, nullptr, TASK_PRIORITY, &requester, TASK_PROCESSOR);", self.usermod)
        for constant in ('const char TASK_NAME[] = "odrig";', "const uint32_t TASK_STACK = 8192;", "const UBaseType_t TASK_PRIORITY = 1;", "const BaseType_t TASK_PROCESSOR = 0;"):
            self.assertIn(constant, self.usermod)

    def test_the_task_is_started_after_the_core_and_only_with_a_core(self):
        setup = self.usermod[self.usermod.index("void setup() override {"):self.usermod.index("void loop() override {")]
        self.assertLess(setup.index("core = odrig_core_begin(&host);"), setup.index("xTaskCreatePinnedToCore("))
        self.assertRegex(setup, r"if \(core != nullptr\) \{\n\s+xTaskCreatePinnedToCore\(")

    def test_the_task_asks_again_only_when_the_loop_has_taken_the_last_refresh(self):
        steps = [self.task.index(step) for step in ("if (refreshReady || updating) {", "ulTaskNotifyTake(", "continue;", "const bool due = refreshDue();", "refreshReady = true;", "vTaskDelay(1);")]
        self.assertEqual(steps, sorted(steps))
        self.assertEqual(self.usermod.count("refreshDue()"), 3)
        self.assertNotIn("refreshDue()", self.usermod[self.usermod.index("class OdrigUsermod"):])

    def test_the_legs_are_read_once_so_that_the_loop_needs_no_lock_for_them(self):
        legs = self.usermod[self.usermod.index("void readLegs() {"):self.usermod.index("// Asks the core for a refresh.")]
        self.assertIn("Locked held;", legs[:legs.index("uint32_t legCount()")])
        self.assertNotIn("Locked held;", legs[legs.index("uint32_t legCount()"):])
        self.assertNotRegex(legs[legs.index("uint32_t legCount()"):], r"odrig_core_")
        self.assertEqual(self.usermod.count("readLegs();"), 1)

    def test_the_port_hands_a_line_on_under_one_hold_of_the_lock(self):
        feed = self.usermod[self.usermod.index("size_t feedBytes("):self.usermod.index("// One command line of the web server")]
        self.assertEqual((feed.count("Locked held;"), feed.count("odrig_core_feed(core, OdrigFiles::nowMs(), bytes, length, keepReply, &kept);")), (1, 1))
        serial = text_of(USERMOD / "odrig_serial.cpp")
        self.assertIn("if (byte == '\\n' || waitingBytes == sizeof(waiting)) handOn();", serial)
        self.assertRegex(serial, r"(?s)void OdrigSerial::poll\(Feed feed\) \{.*\n  handOn\(\);\n\}")
        self.assertEqual(serial.count("feedNow(waiting, waitingBytes, reply, sizeof(reply))"), 1)


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

    def test_files_are_written_renamed_and_removed_in_one_source_only(self):
        changing = r'WLED_FS\.(remove|rename)\b|\.open\([^)]*"(w|a|r\+)[^"]*"\)'
        users = {path.name for path in SOURCES if re.search(changing, text_of(path))}
        self.assertEqual(users, {"odrig_files.cpp"})
        users = {path.name for path in SOURCES if re.search(r"\bWLED_FS\b", text_of(path))}
        self.assertEqual(users, {"odrig_files.cpp"})
        for path in SOURCES:
            text = text_of(path)
            self.assertNotRegex(text, r"WLED_FS\.(mkdir|rmdir|format)\b", path.name)
            self.assertNotRegex(text, r"serializeConfig|writeObjectToFile|doSerializeConfig|configNeedsWrite", path.name)

    def test_every_path_given_to_the_file_system_is_in_the_shows_folder(self):
        calls = re.findall(r"WLED_FS\.(open|exists|remove|rename)\(([^)]*)\)", self.files)
        self.assertGreaterEqual(len(calls), 8)
        paths = set()
        for _, arguments in calls:
            paths.update(argument.strip() for argument in arguments.split(",") if not argument.strip().startswith('"'))
        self.assertEqual(paths, {"path", "given", "pathFrom", "pathTo"})
        # Each of them is the folder and a name, put together in one of two ways.
        self.assertEqual(set(re.findall(r"strcpy\((\w+), FOLDER\);", self.files)), {"path", "given"})
        self.assertEqual(set(re.findall(r"pathOf\(\w+, (\w+)\)", self.files)), {"path", "pathFrom", "pathTo"})
        made = self.files[self.files.index("bool pathOf(const char *name, char *path) {"):self.files.index("int openNamed(")]
        self.assertIn("if (!isName(name)) return false;", made)
        self.assertIn("strcpy(path, FOLDER);", made)
        self.assertNotRegex(self.files, r'"/[^o"]')

    def test_a_name_is_checked_for_its_length_and_its_characters_before_it_is_used(self):
        checked = self.files[self.files.index("bool isName(const char *name) {"):self.files.index("bool pathOf(")]
        for expected in ("if (length == LONGEST_NAME) return false;", "(c >= 'a' && c <= 'z')", "(c >= '0' && c <= '9')", "c == '-' || c == '_' || c == '.'", "return length > 0 && !onlyDots;"):
            self.assertIn(expected, checked)
        self.assertIn("const size_t LONGEST_NAME = 32;", self.files)
        for function in ("beginFile", "endFile", "renameFile", "removeFile", "readAt"):
            body = self.files[self.files.index(f" {function}(void *"):]
            body = body[:body.index("\n}\n")]
            self.assertIn("pathOf(", body, function)

    def test_the_host_record_has_the_seven_storage_functions(self):
        for member, function in (("write_open", "beginFile"), ("write", "addBytes"), ("write_close", "endFile"), ("rename", "renameFile"),
                                 ("remove", "removeFile"), ("space", "tellSpace"), ("read_at", "readAt")):
            self.assertIn(f"made.{member} = {function};", self.files)

    def test_a_write_of_the_core_is_one_write_of_the_file_system(self):
        body = self.files[self.files.index("int addBytes(void *, const uint8_t *bytes, size_t length) {"):]
        body = body[:body.index("\n}\n")]
        self.assertEqual(body.count("writtenFile.write(bytes, length)"), 1)
        self.assertIn("return taken == length ? 1 : -1;", body)
        self.assertEqual(self.files.count(".write("), 1)

    def test_a_file_is_whole_when_storage_holds_the_bytes_that_were_given(self):
        body = self.files[self.files.index("int endFile(void *) {"):]
        body = body[:body.index("\n}\n")]
        steps = [body.index(step) for step in ("writtenFile.close();", 'File whole = WLED_FS.open(path, "r");', "whole.size();", "return size == writtenBytes ? 1 : -1;")]
        self.assertEqual(steps, sorted(steps))

    def test_a_rename_and_a_removal_first_close_the_second_reader_and_the_writer(self):
        for function, names in (("renameFile", ("from", "to")), ("removeFile", ("name",))):
            body = self.files[self.files.index(f"int {function}(void *"):]
            body = body[:body.index("\n}\n")]
            for name in names:
                self.assertLess(body.index(f"dropSecond({name});"), body.index("WLED_FS."), function)
                self.assertLess(body.index(f"giveUpWritten({name});"), body.index("WLED_FS."), function)
        removal = self.files[self.files.index("int removeFile(void *"):]
        self.assertIn("if (!WLED_FS.exists(path)) return 0;", removal[:removal.index("\n}\n")])

    def test_the_space_is_asked_of_the_file_system_once_and_kept_up_from_the_storage_calls(self):
        self.assertEqual((self.files.count("WLED_FS.totalBytes()"), self.files.count("WLED_FS.usedBytes()")), (1, 1))
        asked = self.files[self.files.index("void askSpace() {"):]
        asked = asked[:asked.index("\n}\n")]
        for expected in ("WLED_FS.totalBytes()", "WLED_FS.usedBytes() / BLOCK_BYTES", "spaceKnown = true;"):
            self.assertIn(expected, asked)
        self.assertEqual(self.files.count("askSpace();"), 1)
        self.assertIn("odrig_host OdrigFiles::host() {\n  if (!spaceKnown) askSpace();", self.files)
        told = self.files[self.files.index("int tellSpace(void *"):]
        told = told[:told.index("\n}\n")]
        self.assertNotIn("WLED_FS", told)
        self.assertNotIn("Timed", told)
        self.assertIn("(uint64_t)usedBlocks * BLOCK_BYTES", told)
        self.assertIn("const size_t BLOCK_BYTES = 4096;", self.files)
        self.assertIn("const size_t INLINE_BYTES = 512;", self.files)
        # What comes to storage and what leaves it, in each storage call.
        kept_up = {
            "beginFile": ("if (WLED_FS.remove(given)) blocksFreed(left);", "blocksFreed(before);"),
            "addBytes": ("blocksFreed(writtenBytes);", "blocksTaken(writtenBytes);"),
            "renameFile": ("const size_t replaced = sizeAt(pathTo);", "blocksFreed(replaced);"),
            "removeFile": ("const size_t removed = sizeAt(path);", "blocksFreed(removed);"),
        }
        for function, steps in kept_up.items():
            body = self.files[self.files.index(f"int {function}(void *"):]
            body = body[:body.index("\n}\n")]
            places = [body.index(step) for step in steps]
            self.assertEqual(places, sorted(places), function)

    def test_the_blocks_of_a_file_are_counted_as_the_file_system_lays_it_out(self):
        counted = self.files[self.files.index("uint32_t blocksOf(size_t bytes) {"):]
        counted = counted[:counted.index("\n}\n")]
        self.assertIn("if (bytes <= INLINE_BYTES) return 0;", counted)
        self.assertIn("held += BLOCK_BYTES - (blocks == 0 ? 0 : 4 * (__builtin_ctz(blocks) + 1));", counted)

        def blocks_of(size):
            if size <= 512:
                return 0
            blocks, held = 0, 0
            while held < size:
                pointers = 0 if blocks == 0 else 4 * ((blocks & -blocks).bit_length())
                held += 4096 - pointers
                blocks += 1
            return blocks

        self.assertEqual([blocks_of(size) for size in (0, 512, 513, 4096, 4097, 8188, 8189)], [0, 0, 1, 1, 2, 2, 3])
        # A megabyte is 244 whole blocks of data and a part of a 245th, pointers included.
        self.assertEqual(blocks_of(1000000), 245)

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
        steps = [loop.index(step) for step in ("if (!refreshReady) return;", "OdrigLeds::fill();", "refreshReady = false;", "xTaskNotifyGive(requester);", "if (!BusManager::canAllShow()) return;", "OdrigLeds::show();", "refreshFilled = false;")]
        self.assertEqual(steps, sorted(steps))
        self.assertEqual((loop.count("OdrigLeds::fill();"), loop.count("OdrigLeds::show();")), (1, 1))
        self.assertIn("if (!refreshFilled) {", loop)
        self.assertNotRegex(loop, r"refreshDue|odrig_core_")

    def test_wled_is_held_in_its_live_mode_at_every_pass(self):
        hold = self.leds[self.leds.index("void OdrigLeds::hold()"):self.leds.index("void OdrigLeds::fill()")]
        for expected in ("realtimeOverride = REALTIME_OVERRIDE_NONE;", "useMainSegmentOnly = false;", "realtimeLock(65000, REALTIME_MODE_GENERIC);", "if (doInitBusses)", "else if (!matches())"):
            self.assertIn(expected, hold)
        usermod = text_of(USERMOD / "odrig_usermod.cpp")
        self.assertEqual(usermod.count("OdrigLeds::hold();"), 2)

    def test_the_limiters_maximum_is_never_set_by_the_usermod(self):
        for path in SOURCES:
            self.assertNotRegex(text_of(path), r"setMilliampsMax|_gMilliAmpsMax\s*=", path.name)


class Pacing(unittest.TestCase):
    """How command lines are held back after storage calls, read in the usermod's sources."""

    @classmethod
    def setUpClass(cls):
        cls.files = text_of(USERMOD / "odrig_files.cpp")
        cls.serial = text_of(USERMOD / "odrig_serial.cpp")
        cls.usermod = text_of(USERMOD / "odrig_usermod.cpp")

    def test_every_storage_call_is_timed(self):
        for function in ("beginFile", "addBytes", "endFile", "renameFile", "removeFile"):
            body = self.files[self.files.index(f"int {function}(void *"):]
            first = [line.strip() for line in body.splitlines()[1:] if line.strip()][0]
            self.assertEqual(first, "Timed timed;", function)
        timed = self.files[self.files.index("struct Timed {"):self.files.index("// Memory from the chip's internal memory")]
        for expected in ("Timed() : startUs(esp_timer_get_time()) {}", "lastCallEndUs = endUs;", "busyUs += tookUs;"):
            self.assertIn(expected, timed)

    def test_a_line_waits_twice_the_time_of_the_storage_calls_and_20_ms_at_least(self):
        self.assertIn("const int64_t SHORTEST_HOLD_US = 20000;", self.files)
        holding = self.files[self.files.index("bool OdrigFiles::holding() {"):]
        holding = holding[:holding.index("\n}\n")]
        for expected in ("if (busyUs != 0) {", "std::max(SHORTEST_HOLD_US, 2 * (int64_t)busyUs);", "if (nowUs - lastCallEndUs < holdUs) {", "busyUs = 0;"):
            self.assertIn(expected, holding)

    def test_the_port_takes_nothing_while_lines_are_held_back_and_asks_again_after_a_line(self):
        poll = self.serial[self.serial.index("void OdrigSerial::poll(Feed feed) {"):]
        loop = poll.index("for (int taken = 0;")
        self.assertLess(poll.index("if (OdrigFiles::holding()) return;"), loop)
        self.assertRegex(poll[loop:], r"if \(lineHandedOn\) \{\n\s+lineHandedOn = false;\n\s+if \(OdrigFiles::holding\(\)\) break;")
        self.assertIn("if (byte == '\\n') lineHandedOn = true;", self.serial)

    def test_a_request_waits_before_it_takes_the_lock(self):
        command = self.usermod[self.usermod.index("size_t commandLine("):self.usermod.index("// The legs as the core lists them")]
        steps = [command.index(step) for step in ("while (OdrigFiles::holding()) delay(1);", "Locked held;", "odrig_core_command(")]
        self.assertEqual(steps, sorted(steps))

    def test_the_pacing_is_asked_only_by_what_carries_lines(self):
        asking = {path.name: len(re.findall(r"OdrigFiles::holding\(\)", outside_probe_blocks(text_of(path)))) for path in SOURCES}
        self.assertEqual({name: count for name, count in asking.items() if count}, {"odrig_files.cpp": 1, "odrig_serial.cpp": 2, "odrig_usermod.cpp": 1})

    def test_no_source_holds_a_word_of_a_command(self):
        words = r'"(play|on|off|brightness|status|space|list|remove|upload|begin|data|end|cancel)[ "\\]'
        for path in SOURCES:
            self.assertNotRegex(text_of(path), words, path.name)

    def test_the_port_has_a_queue_of_4096_bytes_made_before_the_core_starts(self):
        self.assertIn("const size_t RECEIVE_QUEUE = 4096;", self.serial)
        self.assertIn("Serial.setRxBufferSize(RECEIVE_QUEUE);", self.serial)
        setup = self.usermod[self.usermod.index("void setup() override {"):self.usermod.index("void loop() override {")]
        self.assertLess(setup.index("OdrigSerial::begin();"), setup.index("core = odrig_core_begin(&host);"))

    def test_the_reply_of_the_port_is_not_on_the_stack(self):
        self.assertIn("static char reply[ODRIG_REPLY_MAX];", self.serial)
        self.assertNotRegex(self.serial.replace("static char reply[ODRIG_REPLY_MAX];", ""), r"\bchar\s+\w+\[[^\]]*(ODRIG_REPLY_MAX|1024)[^\]]*\]")

    def test_the_probes_times_of_storage_are_in_the_probe_build_only(self):
        for name in ("odrig_files.h", "odrig_files.cpp", "odrig_usermod.cpp", "odrig_serial.cpp", "odrig_http.cpp"):
            self.assertNotRegex(outside_probe_blocks(text_of(USERMOD / name)), r"StoreTimes|secondReads|timedCalls|storeStep|storing\(", name)
        probe = text_of(USERMOD / "odrig_probe.cpp")
        for expected in ('\\"store\\":{\\"calls\\":', '\\"longest_us\\":', '\\"total_us\\":', '\\"check_steps\\":', '\\"check_longest_us\\":', '\\"check_total_us\\":',
                         'const char STORE_WORD[] = "#store ";', 'const char STORE_PART[] = "probe.part";', 'const char STORE_NAME[] = "probe.odrg";'):
            self.assertIn(expected, probe)
        loop = self.usermod[self.usermod.index("void loop() override {"):self.usermod.index("void addToJsonInfo")]
        self.assertRegex(loop, r"if \(OdrigProbe::storing\(\) && !OdrigFiles::holding\(\)\) \{\n\s+Locked held;\n\s+OdrigProbe::storeStep\(\);")

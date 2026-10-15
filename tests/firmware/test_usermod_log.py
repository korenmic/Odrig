import re
import unittest

from . import FIRMWARE

USERMOD = FIRMWARE / "usermod"


def text_of(path):
    return path.read_text(encoding="utf-8")


def body(text, start):
    """The body of the function that begins with `start`, up to the end of its block."""
    found = text[text.index(start):]
    return found[:found.index("\n}\n")]


class TheLog(unittest.TestCase):
    """The log of the firmware on the serial chip's port, read in its sources."""

    @classmethod
    def setUpClass(cls):
        cls.header = text_of(USERMOD / "odrig_log.h")
        cls.log = text_of(USERMOD / "odrig_log.cpp")
        cls.uart = text_of(USERMOD / "odrig_uart.cpp")
        cls.drive = text_of(USERMOD / "odrig_drive.cpp")
        cls.usermod = text_of(USERMOD / "odrig_usermod.cpp")

    def test_the_serial_ports_code_writes_the_logs_lines_between_replies_and_never_waits(self):
        poll = body(self.uart, "void OdrigUart::poll(Line line) {")
        self.assertTrue(poll.startswith("void OdrigUart::poll(Line line) {\n  writeLog();\n  for ("), poll)
        self.assertEqual(poll.count("writeLog();"), 1)
        write = body(self.uart, "void writeLog() {")
        self.assertIn("const int space = Serial0.availableForWrite() - WRITE_MARGIN;", write)
        self.assertIn("if (space <= 0) return;", write)
        self.assertIn("OdrigLog::take(line, sizeof(line), (size_t)space)", write)
        self.assertIn("if (length == 0) return;\n    Serial0.write((const uint8_t *)line, length);", write)
        self.assertIn("const size_t SEND_QUEUE = 2048;", self.uart)
        begin = body(self.uart, "void OdrigUart::begin() {")
        self.assertLess(begin.index("Serial0.setTxBufferSize(SEND_QUEUE);"), begin.index("Serial0.begin(BITS_PER_SECOND);"))

    def test_a_line_is_its_mark_the_seconds_its_kind_and_printable_text(self):
        self.assertIn('"#log %u.%03u %s: "', self.log)
        self.assertIn("const size_t LINE_ROOM = 160;", self.header)
        self.assertIn("const size_t LINES = 32;", self.log)
        made = body(self.log, "size_t made(char *into, uint64_t ms, const char *kind, const char *text) {")
        self.assertIn("c < 0x20 || c > 0x7e ? '?' : c", made)
        self.assertIn("into[length++] = '\\n';", made)

    def test_adding_never_waits_and_the_oldest_lines_give_way(self):
        add = body(self.log, "void OdrigLog::add(const char *kind, const char *text) {")
        self.assertIn("portENTER_CRITICAL(&guard);", add)
        self.assertNotRegex(add, r"xSemaphoreTake|vTaskDelay|Serial")
        self.assertIn("dropped++;", add)
        self.assertIn("lines dropped", self.log)

    def test_the_usb_ports_events_are_lines_of_the_log(self):
        for text in ("a computer is on the port, which stays a serial port", "no computer on the port within", "host started", "host did not start: ",
                     "a device came: maker %04x, product %04x, %s", "a hub", "a stick", "another device (class %u)", "a device went",
                     "stick opened: %u animation files in odrig", "stick not opened: ", "the stick has no folder odrig"):
            self.assertIn(text, self.drive, text)
        self.assertIn("usb_host_client_register(", self.drive)
        self.assertIn("USB_HOST_CLIENT_EVENT_NEW_DEV", self.drive)
        self.assertIn("USB_HOST_CLIENT_EVENT_DEV_GONE", self.drive)

    def test_every_line_the_player_logs_goes_to_the_log(self):
        self.assertIn('OdrigLog::add("player", text);', self.log)
        setup = self.usermod[self.usermod.index("void setup() override {"):self.usermod.index("void loop() override {")]
        self.assertIn("const odrig_host host = OdrigLog::withLog(OdrigDrive::withDrive(OdrigFiles::host()));", setup)

    def test_nothing_of_the_wifi_settings_is_named_in_the_log(self):
        for text in (self.header, self.log):
            self.assertNotRegex(text, re.compile(r"wifi|password|ssid|apPass|clientPass", re.I))


if __name__ == "__main__":
    unittest.main()

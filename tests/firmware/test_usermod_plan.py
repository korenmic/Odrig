"""The push of the plan on the board's two serial ways: the UART of the socket marked COM is way
1 and the chip's own USB socket way 2, and each writes the `#plan` lines the core has due
between replies, never waiting; read in the firmware's sources."""

import unittest

from . import FIRMWARE

USERMOD = FIRMWARE / "usermod"


def text_of(path):
    return path.read_text(encoding="utf-8")


def body(text, start):
    """The body of the function that begins with `start`, up to the end of its block."""
    found = text[text.index(start):]
    return found[:found.index("\n}\n")]


class TheWays(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.usermod = text_of(USERMOD / "odrig_usermod.cpp")

    def test_the_uart_is_way_1_the_usb_socket_way_2_and_the_web_server_no_way(self):
        self.assertIn("const uint32_t UART_WAY = 1;", self.usermod)
        self.assertIn("const uint32_t USB_WAY = 2;", self.usermod)
        feed = body(self.usermod, "size_t feedBytes(")
        self.assertIn("odrig_core_feed_on(core, OdrigFiles::nowMs(), USB_WAY, bytes, length, keepReply, &kept);", feed)
        self.assertNotIn("odrig_core_feed(", feed)
        command = body(self.usermod, "size_t commandOn(")
        self.assertIn("way == 0 ? odrig_core_command(core, OdrigFiles::nowMs(), line, length, reply, capacity)", command)
        self.assertIn("odrig_core_command_on(core, OdrigFiles::nowMs(), way, line, length, reply, capacity);", command)
        self.assertIn("return commandOn(0, line, length, reply, capacity);", body(self.usermod, "size_t commandLine("))
        self.assertIn("return commandOn(UART_WAY, line, length, reply, capacity);", body(self.usermod, "size_t uartLine("))
        setup = self.usermod[self.usermod.index("void setup() override {"):self.usermod.index("void loop() override {")]
        self.assertIn("OdrigHttp::begin(commandLine);", setup)
        loop = self.usermod[self.usermod.index("void loop() override {"):self.usermod.index("void addToJsonInfo")]
        self.assertIn("OdrigSerial::poll(feedBytes, usbPlan);", loop)
        self.assertIn("OdrigUart::poll(uartLine, uartPlan);", loop)

    def test_a_ways_plan_line_is_asked_for_without_waiting_for_the_lock(self):
        plan = body(self.usermod, "size_t planOn(")
        self.assertIn("if (core == nullptr || xSemaphoreTake(lock, 0) != pdTRUE) return 0;", plan)
        self.assertLess(plan.index("xSemaphoreTake(lock, 0)"), plan.index("odrig_core_plan_line(core, OdrigFiles::nowMs(), way, line, capacity);"))
        self.assertLess(plan.index("odrig_core_plan_line("), plan.index("xSemaphoreGive(lock);"))
        self.assertNotIn("Locked held;", plan)
        self.assertIn("size_t uartPlan(char *line, size_t capacity) { return planOn(UART_WAY, line, capacity); }", self.usermod)
        self.assertIn("size_t usbPlan(char *line, size_t capacity) { return planOn(USB_WAY, line, capacity); }", self.usermod)


class TheUart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uart = text_of(USERMOD / "odrig_uart.cpp")

    def test_a_plan_line_is_written_whole_after_the_log_when_the_queue_takes_all_of_it(self):
        poll = body(self.uart, "void OdrigUart::poll(Line line, Plan plan) {")
        self.assertTrue(poll.startswith("void OdrigUart::poll(Line line, Plan plan) {\n  writeLog();\n  writePlan(plan);\n  for ("), poll)
        write = body(self.uart, "void writePlan(OdrigUart::Plan plan) {")
        self.assertIn("static char line[ODRIG_REPLY_MAX + 8];", write)
        self.assertIn("if (ended || Serial0.availableForWrite() - WRITE_MARGIN < (int)sizeof(line)) return;", write)
        self.assertLess(write.index("availableForWrite()"), write.index("plan(line, sizeof(line))"))
        self.assertIn("if (length > 0) Serial0.write((const uint8_t *)line, length);", write)


class TheUsbSocket(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.serial = text_of(USERMOD / "odrig_serial.cpp")

    def test_a_plan_line_is_written_in_pieces_and_nothing_is_read_until_it_is_whole(self):
        poll = body(self.serial, "void OdrigSerial::poll(Feed feed, Plan plan) {")
        self.assertLess(poll.index("keepSending();"), poll.index("if (planWaits(plan)) return;"))
        self.assertLess(poll.index("if (planWaits(plan)) return;"), poll.index("for (int taken = 0;"))
        self.assertIn("char planLine[ODRIG_REPLY_MAX + 8];", self.serial)
        waits = body(self.serial, "bool planWaits(OdrigSerial::Plan plan) {")
        self.assertIn("planLength = plan(planLine, sizeof(planLine));", waits)
        self.assertLess(waits.index("if (planWritten >= planLength) {"), waits.index("plan(planLine, sizeof(planLine))"))
        self.assertIn("const int room = Serial.availableForWrite();", waits)
        self.assertIn("std::min((size_t)room, planLength - planWritten)", waits)
        self.assertIn("return planWritten < planLength;", waits)


if __name__ == "__main__":
    unittest.main()

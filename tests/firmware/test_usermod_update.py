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


class TheUpdateOverWifi(unittest.TestCase):
    """The usermod's answer to an update sent to WLED's page, read in its sources."""

    @classmethod
    def setUpClass(cls):
        cls.update = text_of(USERMOD / "odrig_update.cpp")
        cls.usermod = text_of(USERMOD / "odrig_usermod.cpp")

    def test_without_a_second_slot_it_answers_post_update_with_the_reason_and_the_way_that_works(self):
        begin = body(self.update, "void OdrigUpdate::begin() {")
        self.assertLess(begin.index("if (secondSlot()) return;"), begin.index("server.on(PATH, HTTP_POST, refuse, dropPiece);"))
        self.assertIn('const char PATH[] = "/update";', self.update)
        self.assertIn("const uint16_t STATUS = 501;", self.update)
        self.assertIn('const char HEADLINE[] = "Update refused";', self.update)
        reason = re.search(r'const char REASON\[\] = "([^"]+)";', self.update).group(1)
        for phrase in ("no second firmware slot", "over the USB cable", "python3 firmware/fw.py flash"):
            self.assertIn(phrase, reason)
        self.assertIn("serveMessage(request, STATUS, HEADLINE, REASON, NO_BUTTON);", self.update)

    def test_a_second_slot_is_one_an_update_could_write_and_not_the_one_that_runs(self):
        slot = body(self.update, "bool secondSlot() {")
        self.assertIn("esp_ota_get_next_update_partition(nullptr)", slot)
        self.assertIn("next != nullptr && next != esp_ota_get_running_partition()", slot)

    def test_it_writes_nothing_and_holds_nothing_back(self):
        self.assertNotRegex(self.update, r"Update\.|esp_ota_begin|esp_ota_write|esp_partition_(erase|write)|onUpdateBegin|UsermodManager")
        self.assertIn("void dropPiece(AsyncWebServerRequest *, String, size_t, uint8_t *, size_t, bool) {}", self.update)

    def test_it_is_registered_in_setup_before_wled_registers_its_pages_and_shown_in_the_information(self):
        setup = self.usermod[self.usermod.index("void setup() override {"):self.usermod.index("void loop() override {")]
        self.assertEqual(setup.count("OdrigUpdate::begin();"), 1)
        info = self.usermod[self.usermod.index("void addToJsonInfo"):self.usermod.index("void onUpdateBegin")]
        self.assertIn('user.createNestedArray(F("odrig update")).add(OdrigUpdate::refusing() ? F("refused: no second slot") : F("WLED\'s"));', info)


if __name__ == "__main__":
    unittest.main()

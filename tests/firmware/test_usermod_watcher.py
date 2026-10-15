import re
import unittest

from . import FIRMWARE

USERMOD = FIRMWARE / "usermod"
SOURCE_ENDINGS = (".c", ".cpp", ".h")


def text_of(path):
    return path.read_text(encoding="utf-8")


def body(text, start):
    """The body of the function that begins with `start`, up to the end of its block."""
    found = text[text.index(start):]
    return found[:found.index("\n}\n")]


class TheWatcher(unittest.TestCase):
    """The second client of the USB host, which says in the log what comes and goes."""

    @classmethod
    def setUpClass(cls):
        cls.drive = text_of(USERMOD / "odrig_drive.cpp")
        cls.describe = body(cls.drive, "void describe(uint8_t address) {")
        cls.event = body(cls.drive, "void watcherEvent(const usb_host_client_event_msg_t *event, void *) {")

    def test_it_keeps_up_to_eight_devices_open_each_with_what_it_is(self):
        self.assertRegex(self.drive, r"(?m)^const size_t MOST_DEVICES = 8;$")
        self.assertRegex(self.drive, r"(?m)^Watched watched\[MOST_DEVICES\] = \{\};$")
        self.assertIn('snprintf(about, sizeof(about), "maker %04x, product %04x, %s"', self.describe)
        self.assertIn('say("a device came: %s", about);', self.describe)
        kept = self.describe[self.describe.index('say("a device came: %s", about);'):]
        self.assertIn("place->handle = opened;", kept)
        self.assertIn("strcpy(place->about, about);", kept)

    def test_a_device_that_finds_no_room_is_closed_at_once(self):
        kept = self.describe[self.describe.index('say("a device came: %s", about);'):]
        self.assertRegex(kept, r"if \(place == nullptr\) \{\n\s+usb_host_device_close\(watcher, opened\);\n\s+return;")

    def test_the_line_of_a_device_that_goes_names_it_as_its_line_of_coming_did(self):
        gone = self.event[self.event.index("USB_HOST_CLIENT_EVENT_DEV_GONE"):]
        self.assertIn("one.handle == event->dev_gone.dev_hdl", gone)
        self.assertIn('say("a device went: %s", one.about);', gone)
        self.assertIn("one.handle = nullptr;", gone)
        self.assertIn("usb_host_device_close(watcher, event->dev_gone.dev_hdl);", gone)
        self.assertNotIn('say("a device went");', self.drive)

    def test_a_description_fits_the_longest_kind_and_a_line_of_the_log(self):
        room = int(re.search(r"(?m)^const size_t ABOUT_ROOM = (\d+);$", self.drive).group(1))
        longest = "maker ffff, product ffff, another device (class 255), on port 255 of a hub"
        self.assertGreater(room, len(longest))
        self.assertLess(len("a device went: ") + room, 160)


class NoHubOfOneMaker(unittest.TestCase):
    def test_no_source_compares_a_makers_or_a_products_number(self):
        compared = re.compile(r"id(Vendor|Product)\s*(==|!=|<=|>=|<|>)|(==|!=|<=|>=|<|>)\s*[\w.]*id(Vendor|Product)\b|case\s+0x[0-9a-fA-F]{4}\s*:")
        for path in sorted(USERMOD.rglob("*")):
            if path.is_file() and path.suffix in SOURCE_ENDINGS:
                self.assertIsNone(compared.search(text_of(path).replace("->", ".")), path.name)


if __name__ == "__main__":
    unittest.main()

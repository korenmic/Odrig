import re
import unittest

from fwtool import wifi

from . import ROOT

PAGE = ROOT / "docs" / "wifi.md"
FIRMWARE_PAGE = ROOT / "docs" / "firmware.md"
SECTIONS = ("The board's network", "Changing the name or the password", "What else changes them", "The owner's check", "Not yet verified")


def flat(text):
    return " ".join(text.split())


def section(text, heading):
    """The text of one second-level section, without its heading."""
    found = re.search(rf"(?ms)^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text)
    if found is None:
        raise AssertionError(f"the page has no section {heading!r}")
    return found.group(1)


class TheWifiPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PAGE.read_text(encoding="utf-8")

    def part(self, heading):
        return flat(section(self.text, heading))

    def test_it_has_its_sections(self):
        headings = re.findall(r"(?m)^## (.+)$", self.text)
        for heading in SECTIONS:
            self.assertIn(heading, headings)
        self.assertNotIn("What our board does today", headings)
        self.assertNotIn("Not yet decided or verified", headings)

    def test_it_describes_the_network_as_it_is(self):
        network = self.part("The board's network")
        for expected in ("named `odrig`", "WPA2", "`firmware/wifi.json`", "the only place in this repository that holds the password",
                         "whoever can read the repository can read it", "`4.3.2.1`", "about two seconds after the firmware has started",
                         "Four devices can be joined at once", "read in the source and not tried"):
            self.assertIn(expected, network)

    def test_it_says_how_the_name_and_the_password_are_changed(self):
        changing = self.part("Changing the name or the password")
        for expected in ("Edit `firmware/wifi.json`", "`python3 firmware/fw.py set-wifi`", "every board", "Commit the file", "every phone",
                         "1 to 32 characters", "8 to 63", "printable ASCII", "`python3 firmware/fw.py install-firmware`"):
            self.assertIn(expected, changing)
        steps = re.findall(r"(?m)^(\d+)\. ", section(self.text, "Changing the name or the password"))
        self.assertEqual(steps, ["1", "2", "3", "4"])

    def test_it_says_what_else_changes_them(self):
        other = self.part("What else changes them")
        for expected in ("WLED's Wi-Fi settings page", "more than five seconds", "more than ten seconds", "`flash` and `restore-stock` keep them",
                         "`build/firmware/storage/`", "`/wsec.json`", "`/cfg.json`", "read in the source and not tried", "`set-wifi` puts"):
            self.assertIn(expected, other)

    def test_the_owners_check_is_numbered_steps_that_say_what_must_be_seen(self):
        check = section(self.text, "The owner's check")
        steps = re.split(r"(?m)^\d+\. ", check)[1:]
        self.assertEqual(len(steps), 4)
        for number, step in enumerate(steps, 1):
            self.assertIn("Seen:", flat(step), f"step {number}")
        told = flat(check)
        for expected in ("`odrig` is there and `WLED-AP` is not", "`python -m odrigctl --http 4.3.2.1 status`", '`"ok":true`',
                         "`POST http://4.3.2.1/odrig`", "`python3 firmware/fw.py test-air --http 4.3.2.1`", "ends with `OK`"):
            self.assertIn(expected, told)

    def test_it_no_longer_says_that_the_name_and_the_password_are_wleds_or_undecided(self):
        told = flat(self.text)
        for gone in ("still has WLED's default name and password", "The access point's own name and password.", "should choose their own before the event",
                     "has not been looked up"):
            self.assertNotIn(gone, told)
        open_points = self.part("Not yet verified")
        self.assertIn("Four", open_points)
        self.assertIn("Range on site", open_points)
        self.assertNotIn("name and password", open_points)

    def test_neither_page_holds_the_password(self):
        password = wifi.read().password
        for page in (PAGE, FIRMWARE_PAGE):
            self.assertFalse(password in page.read_text(encoding="utf-8"), page.name)


class TheFirmwarePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = FIRMWARE_PAGE.read_text(encoding="utf-8")

    def test_it_names_the_settings_file_where_it_says_that_wifi_is_wleds(self):
        does = flat(section(self.text, "What the firmware does"))
        told = does.split("**Wi-Fi is WLED's.**")[1].split("**WLED's information**")[0]
        for expected in ("`firmware/wifi.json`", "`set-wifi`", "`install-firmware`", "[wifi.md](wifi.md)"):
            self.assertIn(expected, told)

    def test_the_owners_checks_name_the_network(self):
        checks = flat(section(self.text, "The owner's checks"))
        self.assertIn("the board's Wi-Fi network, `odrig`,", checks)


if __name__ == "__main__":
    unittest.main()

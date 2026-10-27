import functools
import json
import pathlib
import re
import subprocess
import tempfile
import unittest

from . import FIRMWARE, ROOT

USERMOD = FIRMWARE / "usermod"
HEADER = USERMOD / "odrig_limit_default.h"
PROGRAM = ROOT / "tests" / "firmware" / "limit_default" / "limit_default.cpp"
FLAGS = ("-std=c++11", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-g")
# What WLED keeps of its maximum for the chip, MA_FOR_ESP of WLED on the ESP32.
CHIP_MA = 120
LARGEST_MAXIMUM = 65535

_folder = tempfile.TemporaryDirectory()


@functools.lru_cache(maxsize=None)
def built():
    program = pathlib.Path(_folder.name, "limit_default")
    done = subprocess.run(["c++", *FLAGS, f"-I{USERMOD}", str(PROGRAM), "-o", str(program)], capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(f"the program of the default budget does not compile:\n{done.stderr}")
    return program


def defaults(*maxima):
    done = subprocess.run([str(built()), *(str(maximum) for maximum in maxima)], capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(f"limit_default {maxima}: status {done.returncode}: {done.stderr[-2000:]}")
    return json.loads(done.stdout)


def by_the_rule(maximum):
    """The default for a maximum: no limit for 0, 1 mA for a maximum from 1 to 120, and
    otherwise the maximum less what WLED keeps for the chip."""
    if maximum == 0:
        return 0
    return maximum - CHIP_MA if maximum > CHIP_MA else 1


class TheDefaultBudget(unittest.TestCase):
    """The wall's budget the firmware gives the core while no budgets are saved, from WLED's
    maximum current as WLED loaded it."""

    def test_it_is_the_maximum_less_what_wled_keeps_for_the_chip(self):
        self.assertEqual(defaults(850, 121, 731, 1000, 65535), [730, 1, 611, 880, 65415])

    def test_a_maximum_from_1_to_120_holds_every_led_at_its_lowest_level(self):
        self.assertEqual(defaults(1, 2, 60, 119, 120), [1] * 5)

    def test_a_maximum_of_0_is_no_limit(self):
        self.assertEqual(defaults(0), [0])

    def test_every_maximum_wled_can_hold_follows_the_rule(self):
        self.assertEqual(defaults("all"), [by_the_rule(maximum) for maximum in range(LARGEST_MAXIMUM + 1)])

    def test_the_header_knows_nothing_of_the_chip(self):
        text = HEADER.read_text(encoding="utf-8")
        self.assertEqual(re.findall(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', text, re.M), ["stdint.h"])
        self.assertIn("inline uint32_t odrigWallDefault(uint32_t maximum) {", text)


class TheFirmwareGivesIt(unittest.TestCase):
    """The default is read once, before the core starts, and given to it through the host's
    record."""

    @classmethod
    def setUpClass(cls):
        cls.usermod = (USERMOD / "odrig_usermod.cpp").read_text(encoding="utf-8")

    def test_wleds_maximum_is_read_once_before_the_core_starts(self):
        setup = self.usermod[self.usermod.index("void setup() override {"):self.usermod.index("void loop() override {")]
        read = "wallDefault = odrigWallDefault(BusManager::ablMilliampsMax());"
        given = "host.limit_default = wallDefaultOf;"
        begun = "core = odrig_core_begin(&host);"
        self.assertLess(setup.index(read), setup.index(begun))
        self.assertLess(setup.index(given), setup.index(begun))
        self.assertEqual(self.usermod.count("BusManager::ablMilliampsMax()"), 1)
        self.assertIn('#include "odrig_limit_default.h"', self.usermod)
        self.assertRegex(self.usermod, r"uint32_t wallDefaultOf\(void \*\) \{ return wallDefault; \}")

    def test_the_chips_share_is_wleds(self):
        self.assertIn("static_assert(ODRIG_CHIP_MA == (uint32_t)MA_FOR_ESP,", self.usermod)
        self.assertRegex(HEADER.read_text(encoding="utf-8"), rf"const uint32_t ODRIG_CHIP_MA = {CHIP_MA};")

    def test_the_shared_record_has_no_default(self):
        files = (USERMOD / "odrig_files.cpp").read_text(encoding="utf-8")
        self.assertIn("made.limit_default = nullptr;", files)
        self.assertNotIn("odrig_limit_default.h", files)


if __name__ == "__main__":
    unittest.main()

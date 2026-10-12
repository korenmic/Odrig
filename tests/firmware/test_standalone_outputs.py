import re
import unittest

from . import ROOT

SOURCES = ROOT / "firmware" / "standalone" / "src"
# The sources written for the standalone firmware; the others are one line each and take a
# source of the usermod in.
OWN = sorted(path for path in SOURCES.iterdir() if path.suffix in (".cpp", ".h") and not path.name.startswith("shared_"))
# The parts of the program beside the outputs and the trial that drives the pins itself.
PARTS = [path for path in OWN if path.name not in ("outputs.cpp", "main.cpp")]


def text_of(name):
    return (SOURCES / name).read_text(encoding="utf-8")


class TheOutputs(unittest.TestCase):
    def test_twenty_legs_get_an_output_the_first_four_on_rmt(self):
        header = text_of("outputs.h")
        self.assertIn("const uint32_t MOST = 20;", header)
        self.assertIn("const uint32_t ON_RMT = 4;", header)
        source = text_of("outputs.cpp")
        self.assertIn("typedef NeoPixelBus<NeoGrbFeature, NeoEsp32RmtNWs2812xMethod> RmtBus;", source)
        self.assertIn("typedef NeoPixelBus<NeoGrbFeature, NeoEsp32LcdX16Ws2812xMethod> ParallelBus;", source)
        self.assertRegex(source, r"if \(i < ON_RMT\) \{\s+outputs\[i\] = new OutputOn<RmtBus>\(leds, pin, \(NeoBusChannel\)i\);\s+\} else \{\s+outputs\[i\] = new OutputOn<ParallelBus>\(leds, pin\);")

    def test_the_order_green_red_blue_is_stated_once(self):
        source = text_of("outputs.cpp")
        self.assertEqual(source.count("NeoGrbFeature"), 2)
        self.assertEqual(len(re.findall(r"grb\[0\] = rgb\[1\];\s+grb\[1\] = rgb\[0\];\s+grb\[2\] = rgb\[2\];", source)), 1)
        for path in PARTS:
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"\bgrb\b|NeoGrbFeature|NeoRgbFeature", path.name)

    def test_the_pins_of_the_usb_port_the_flash_and_the_external_memory_get_no_output(self):
        source = text_of("outputs.cpp")
        found = re.search(r"bool usable\(uint32_t pin\) \{ return (.*?); \}", source)
        self.assertIsNotNone(found)
        rule = found.group(1).replace("||", " or ").replace("&&", " and ")
        usable = [pin for pin in range(0, 70) if eval(rule, {"pin": pin})]
        self.assertEqual(usable, [*range(0, 19), 21, *range(38, 49)])
        for pin in (*range(1, 19), 21, 47):
            self.assertIn(pin, usable)
        for pin in (19, 20, 22, 26, 32, 33, 37, 49, 60):
            self.assertNotIn(pin, usable)
        self.assertRegex(source, r"if \(i >= count \|\| !usable\(legs\[i\]\.pin\) \|\| legs\[i\]\.led_count == 0 \|\| legs\[i\]\.led_count > UINT16_MAX\) continue;")

    def test_an_output_that_was_not_made_is_passed_over_everywhere(self):
        source = text_of("outputs.cpp")
        self.assertIn("if (outputs[i] == nullptr) continue;", source)
        self.assertIn("if (outputs[i] != nullptr && !outputs[i]->canShow()) return false;", source)
        self.assertIn("if (outputs[i] != nullptr) outputs[i]->show();", source)
        self.assertIn('if (!ok(index)) return "none";', source)

    def test_no_other_part_names_the_led_library(self):
        self.assertIn("outputs.h", [path.name for path in PARTS])
        for path in PARTS:
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"NeoPixelBus|NeoEsp32|NeoBusChannel", path.name)


class NoWriting(unittest.TestCase):
    def test_no_source_of_the_standalone_firmware_writes_formats_or_removes_a_file(self):
        self.assertIn("outputs.cpp", [path.name for path in OWN])
        for path in OWN:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r'"w\+?"|"a\+?"|"r\+"|FILE_WRITE|FILE_APPEND|\.remove\(|\.rename\(|\.mkdir\(|\.rmdir\(|\.format\(|begin\(true', path.name)


if __name__ == "__main__":
    unittest.main()

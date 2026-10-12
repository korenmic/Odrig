import random
import re
import unittest

from . import ROOT, hostprogram

SOURCES = ROOT / "firmware" / "standalone" / "src"

LED_MA, REST_MA, CHIP_MA = 55, 1, 120


def reference(maximum, outputs):
    """What WLED's limiter does with a maximum for all LEDs together, written from its
    source: `applyABL` and `estimateCurrent` of bus_manager.cpp and `color_fade` of
    colors.cpp, with 55 mA for an LED and the usermod's outputs."""
    if maximum == 0:
        return {"limit_ma": 0, "used_ma": 0, "limited": False, "outputs": list(outputs)}
    estimate = sum(sum(output) * LED_MA // (3 * 255) + len(output) // 3 * REST_MA for output in outputs)
    leds = sum(len(output) // 3 for output in outputs)
    allowed = maximum - CHIP_MA if maximum > CHIP_MA else 1
    level = 255
    if allowed > leds:
        if estimate > allowed:
            level = allowed * 255 // estimate + 1
            estimate = allowed
    else:
        level = 1
        estimate = leds
    limit = maximum - CHIP_MA if maximum > CHIP_MA else 0
    return {"limit_ma": limit, "used_ma": estimate, "limited": estimate >= limit, "outputs": [faded(output, level) for output in outputs]}


def faded(output, level):
    """An output with every LED dimmed to a level as WLED's video scaling does it."""
    if level >= 255:
        return output
    made = bytearray()
    for at in range(0, len(output), 3):
        led = output[at:at + 3]
        if led == b"\x00\x00\x00":
            made += led
            continue
        kept = (max(led) >> 2) + 1
        made += bytes(((value * level + 127) >> 8) | (1 if value > kept else 0) for value in led)
    return bytes(made)


WHITE = b"\xff\xff\xff"


class TheLimiter(unittest.TestCase):
    def same(self, maximum, outputs):
        found = hostprogram.limit(maximum, outputs)
        self.assertEqual(found, reference(maximum, outputs))
        return found

    def test_without_a_limit_nothing_is_estimated_and_nothing_changes(self):
        for outputs in ([WHITE * 180] * 20, [b""], [], [bytes(range(256)) * 3]):
            found = hostprogram.limit(0, outputs)
            self.assertEqual(found, {"limit_ma": 0, "used_ma": 0, "limited": False, "outputs": outputs})

    def test_no_light_is_one_milliamp_for_each_led(self):
        found = self.same(850, [bytes(3 * 60)])
        self.assertEqual((found["limit_ma"], found["used_ma"], found["limited"]), (730, 60, False))
        self.assertEqual(found["outputs"], [bytes(3 * 60)])

    def test_one_white_led_is_55_milliamps_and_its_own_one(self):
        found = self.same(850, [WHITE + bytes(3 * 59)])
        self.assertEqual((found["used_ma"], found["limited"]), (55 + 60, False))

    def test_60_white_leds_at_each_maximum(self):
        strip = WHITE * 60
        whole = 60 * 55 + 60
        self.assertEqual(self.same(65535, [strip])["outputs"], [strip])
        self.assertEqual(self.same(whole + 120, [strip])["used_ma"], whole)
        self.assertTrue(self.same(whole + 120, [strip])["limited"])
        self.assertEqual(self.same(whole + 120, [strip])["outputs"], [strip])
        self.assertFalse(self.same(whole + 121, [strip])["limited"])
        at_850 = self.same(850, [strip])
        self.assertEqual((at_850["limit_ma"], at_850["used_ma"], at_850["limited"]), (730, 730, True))
        level = 730 * 255 // whole + 1
        self.assertEqual(at_850["outputs"], [bytes([(255 * level + 127) >> 8 | 1]) * 180])
        for maximum in (1, 100, 120, 121, 180):
            with self.subTest(maximum=maximum):
                lowest = self.same(maximum, [strip])
                self.assertEqual(lowest["outputs"], [b"\x01" * 180])
                self.assertEqual((lowest["limit_ma"], lowest["used_ma"], lowest["limited"]), (max(maximum - 120, 0), 60, True))
        self.assertEqual(self.same(182, [strip])["used_ma"], 62)

    def test_the_target_at_850_holds_every_lit_channel_at_1_or_0(self):
        rng = random.Random(15)
        outputs = [bytes(rng.choice((0, 0, 3, 40, 128, 255)) for _ in range(540)) for _ in range(20)]
        found = self.same(850, outputs)
        self.assertEqual((found["limit_ma"], found["used_ma"], found["limited"]), (730, 3600, True))
        for before, after in zip(outputs, found["outputs"]):
            self.assertLessEqual(set(after), {0, 1})
            for at in range(0, 540, 3):
                led = before[at:at + 3]
                kept = (max(led) >> 2) + 1
                self.assertEqual(after[at:at + 3], bytes(1 if value > kept else 0 for value in led))

    def test_a_dim_led_keeps_its_hue_as_far_as_wled_keeps_it(self):
        found = self.same(200, [bytes([200, 100, 40, 4, 1, 0, 255, 0, 0, 2, 2, 2]) + WHITE * 200])
        self.assertEqual(found["outputs"][0][:12], faded(bytes([200, 100, 40, 4, 1, 0, 255, 0, 0, 2, 2, 2]), 1))
        self.assertEqual(found["outputs"][0][:6], bytes([1, 1, 0, 1, 0, 0]))

    def test_the_estimate_is_made_for_each_output_and_then_added(self):
        thirds = [bytes([255, 255, 1]) * 5, bytes([1, 0, 0]) * 7, WHITE * 3]
        whole = sum(sum(output) * 55 // 765 + len(output) // 3 for output in thirds)
        joined = sum(map(sum, thirds)) * 55 // 765 + sum(len(output) // 3 for output in thirds)
        self.assertNotEqual(whole, joined)
        self.assertEqual(self.same(65535, thirds)["used_ma"], whole)

    def test_the_order_of_the_three_bytes_of_an_led_does_not_matter(self):
        rng = random.Random(3)
        output = bytes(rng.randrange(256) for _ in range(3 * 200))
        turned = b"".join(bytes([output[at + 1], output[at], output[at + 2]]) for at in range(0, len(output), 3))
        first, second = hostprogram.limit(400, [output]), hostprogram.limit(400, [turned])
        self.assertEqual((first["limit_ma"], first["used_ma"], first["limited"]), (second["limit_ma"], second["used_ma"], second["limited"]))
        back = b"".join(bytes([second["outputs"][0][at + 1], second["outputs"][0][at], second["outputs"][0][at + 2]]) for at in range(0, len(output), 3))
        self.assertEqual(first["outputs"][0], back)

    def test_an_estimate_above_what_16_bits_hold_is_dimmed_to_what_is_allowed(self):
        found = self.same(65535, [WHITE * 180] * 20)
        self.assertEqual((found["limit_ma"], found["used_ma"], found["limited"]), (65415, 65415, True))
        self.assertLess(max(found["outputs"][0]), 255)

    def test_200_pictures_on_one_to_twenty_outputs(self):
        rng = random.Random(12)
        for number in range(200):
            count = rng.randint(1, 20)
            density = rng.choice((0.0, 0.05, 0.5, 1.0))
            brightest = rng.choice((1, 8, 40, 255))
            outputs = [bytes(rng.randint(0, brightest) if rng.random() < density else 0 for _ in range(3 * rng.choice((1, 18, 60, 180)))) for _ in range(count)]
            maximum = rng.choice((0, 1, 100, 120, 121, 300, 850, 2000, 12000, 40000, 65535))
            with self.subTest(picture=number, maximum=maximum, outputs=count):
                self.same(maximum, outputs)


class TheSource(unittest.TestCase):
    def test_the_limiter_knows_nothing_of_the_chip_and_takes_no_memory(self):
        for name in ("limit.h", "limit.cpp"):
            text = (SOURCES / name).read_text(encoding="utf-8")
            headers = set(re.findall(r'(?m)^#include\s+[<"]([^>"]+)[>"]', text))
            self.assertLessEqual(headers, {"stdint.h", "limit.h"}, name)
            self.assertNotRegex(text, r"\bString\b|\bSerial\b|\bmalloc\b|\bnew\b|\bstd::", name)

    def test_its_numbers_are_wleds(self):
        header = (SOURCES / "limit.h").read_text(encoding="utf-8")
        for expected in ("ODRIG_LED_MA = 55;", "ODRIG_REST_MA = 1;", "ODRIG_CHIP_MA = 120;"):
            self.assertIn(expected, header)


if __name__ == "__main__":
    unittest.main()

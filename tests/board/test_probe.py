import time
import unittest
import zlib

from . import support

LEGS = 10
LEDS_PER_LEG = 180


def pattern(leg):
    """The bytes the stand-in gives leg number `leg`, counted from 0."""
    colours = bytearray()
    for n in range(LEDS_PER_LEG):
        colours += bytes([1 + (n * 39) // (LEDS_PER_LEG - 1), (n + leg * 7) % 41, leg * 4])
    return bytes(colours)


def at_the_limiters_minimum(colours):
    """What WLED gives back for colours its current limiter dimmed to its lowest level: a
    channel stays lit when it is above a quarter of the colour's largest, and reads 128."""
    left = bytearray()
    for i in range(0, len(colours), 3):
        colour = colours[i:i + 3]
        threshold = (max(colour) >> 2) + 1
        left += bytes(128 if value > threshold else 0 for value in colour)
    return bytes(left)


class Probe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("probe")

    def test_ten_working_outputs_on_pins_1_to_10_four_rmt_and_six_parallel(self):
        outputs = support.probe()["outputs"]
        self.assertEqual([(o["leg"], o["pin"], o["count"], o["ok"]) for o in outputs], [(n, n, LEDS_PER_LEG, True) for n in range(1, LEGS + 1)])
        self.assertEqual([o["driver"] for o in outputs], ["rmt"] * 4 + ["parallel"] * 6)

    def test_each_output_holds_the_pattern_of_its_leg(self):
        time.sleep(0.2)
        report = support.probe()
        time.sleep(0.2)
        report = support.probe()
        for leg, output in enumerate(report["outputs"]):
            expected = at_the_limiters_minimum(pattern(leg)) if report["limited"] else pattern(leg)
            self.assertEqual(output["crc"], f"{zlib.crc32(expected):08x}", f"leg {leg + 1}, limited in {report['limited']} sends")

    def test_the_limiter_acts_on_every_refresh_when_the_leds_need_more_than_it_allows(self):
        support.probe()
        time.sleep(1.0)
        report = support.probe()
        standby = LEGS * LEDS_PER_LEG
        if report["limit_ma"] > standby:
            self.skipTest(f"WLED's maximum current allows {report['limit_ma']} mA, more than the {standby} mA of the LEDs at rest")
        self.assertGreaterEqual(report["limited"], 45)
        self.assertEqual(report["used_ma"], standby)

    def test_49_or_more_refreshes_are_sent_in_each_of_10_seconds(self):
        time.sleep(1.5)
        sent = [report["sent"] for report in support.each_second(10)]
        self.assertGreaterEqual(min(sent), 49, sent)

    def test_nothing_else_writes_to_the_outputs_over_30_seconds(self):
        support.probe()
        reports = support.each_second(30)
        self.assertEqual([report["overwritten"] for report in reports], [0] * 30)
        self.assertGreater(min(report["sent"] for report in reports), 0)

    def test_wled_is_held_in_its_live_mode(self):
        self.assertEqual(support.probe()["realtime"], 1)

    def test_the_port_is_silent_without_a_command(self):
        self.assertEqual(support.heard(b"", 5.0), [])

    def test_wleds_handshake_gets_no_answer(self):
        self.assertEqual(support.heard(b"v", 3.0), [])
        self.assertEqual(support.probe()["probe"], 1)

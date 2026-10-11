import json
import pathlib
import shutil
import tempfile
import time
import unittest
import zlib

from fwtool import storage

from . import PORT, support

UNKNOWN = b'{"ok":false,"error":"unknown-command"}'
LEGS = len(support.TARGET_PINS)
SECONDS = 10
# The time 180 LEDs take on the wire is 5.7 ms; the timer that takes it looks every tenth
# of a millisecond.
WIRE_US = (4500, 7500)
# A picture that does not change: one frame that lasts a minute, so that the core opens
# its file once in the time of a test.
STILL_MS = 60000


def crc(colours):
    return f"{zlib.crc32(colours):08x}"


def at_the_limiters_minimum(colours):
    """What WLED gives back for colours its current limiter dimmed to its lowest level: a
    channel stays lit when it is above a quarter of the colour's largest, and reads 128."""
    left = bytearray()
    for i in range(0, len(colours), 3):
        colour = colours[i:i + 3]
        threshold = (max(colour) >> 2) + 1
        left += bytes(128 if value > threshold else 0 for value in colour)
    return bytes(left)


def report_after_a_moment():
    """A report that covers only refreshes sent since this call began."""
    support.probe()
    time.sleep(0.3)
    return support.probe()


def report_with_every_pulse_count():
    """A report in which every output has been counted once: one output is counted at
    each send."""
    deadline = time.monotonic() + 10.0
    report = report_after_a_moment()
    while any(output["pulses"] is None for output in report["outputs"]) and time.monotonic() < deadline:
        time.sleep(0.5)
        report = support.probe()
    return report


def pulses_of(report):
    return [output["pulses"] for output in report["outputs"]]


def drivers_of(report):
    return [output["driver"] for output in report["outputs"]]


def outputs_of(report):
    return [(output["leg"], output["pin"], output["count"], output["ok"]) for output in report["outputs"]]


def held(report):
    return [output["crc"] for output in report["outputs"]]


class Outputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("probe")

    def test_the_example_show_has_two_working_outputs_on_pins_1_and_2(self):
        with support.dim_show() as folder:
            support.ensure_installed(folder)
        report = report_after_a_moment()
        self.assertEqual(outputs_of(report), [(1, 1, 180, True), (2, 2, 180, True)])
        self.assertEqual(report["realtime"], 1)
        self.assertIsNone(report["error"])
        self.assertGreater(report["start_ms"], 0)

    def test_each_output_holds_exactly_the_bytes_the_core_gives_its_leg(self):
        for brightness in (40, 1, 32):
            with self.subTest(brightness=brightness), support.one_frame_show(support.TWO_LEGS, brightness) as folder:
                support.ensure_installed(folder)
                expected = support.leg_bytes(support.recorded(folder, 1), 980)
                report = report_after_a_moment()
                self.assertEqual(report["limited"], 0)
                self.assertEqual(held(report), [crc(colours) for colours in expected])
                self.assertEqual(len({bytes(expected[0][i:i + 3]) for i in range(0, 540, 3)}) > 1, brightness > 1)

    def test_the_outputs_follow_every_brightness_from_0_to_40_and_the_switch(self):
        with support.one_frame_show(support.TWO_LEGS, support.DIM) as folder:
            support.ensure_installed(folder)
            script = "".join(f"{1000 * (level + 1)} brightness {level}\n" for level in range(41)) + "43000 off\n44000 on\n"
            recording = support.recorded(folder, 45, script)
        for level in range(41):
            self.assertEqual(support.command(PORT, "brightness", str(level)), (0, {"ok": True}))
            report = support.probe()
            expected = support.leg_bytes(recording, 1000 * (level + 1) + 500)
            self.assertEqual(held(report), [crc(colours) for colours in expected], f"brightness {level}")
            self.assertEqual(report["limited"], 0, f"brightness {level}")
        self.assertEqual(support.command(PORT, "status")[1]["brightness"], 40)
        support.command(PORT, "off")
        self.assertEqual(held(support.probe()), [crc(bytes(540))] * 2)
        self.assertEqual(support.leg_bytes(recording, 43500), [bytes(540)] * 2)
        support.command(PORT, "on")
        self.assertEqual(held(support.probe()), [crc(colours) for colours in support.leg_bytes(recording, 44500)])
        self.assertEqual(support.command(PORT, "brightness", str(support.DIM)), (0, {"ok": True}))

    def test_twenty_column_legs_of_18_leds_hold_exactly_the_bytes_of_their_legs(self):
        mapping = support.legs_mapping(6, legs=LEGS, pins=support.TARGET_PINS, columns=True)
        with support.one_frame_show(mapping, 40) as folder:
            support.ensure_installed(folder)
            expected = support.leg_bytes(support.recorded(folder, 1), 980)
        report = report_with_every_pulse_count()
        self.assertEqual(outputs_of(report), [(number + 1, pin, 18, True) for number, pin in enumerate(support.TARGET_PINS)])
        self.assertEqual(drivers_of(report), ["rmt"] * 4 + ["parallel"] * 16)
        self.assertEqual(report["limited"], 0)
        self.assertEqual(held(report), [crc(colours) for colours in expected])
        self.assertEqual(len(set(held(report))), LEGS)
        self.assertEqual(pulses_of(report), [24 * 18] * LEGS)

    def test_the_target_has_twenty_working_outputs_that_carry_a_whole_refresh_49_times_a_second(self):
        with support.one_frame_show(support.TARGET, support.DIM, ms=STILL_MS) as folder:
            support.ensure_installed(folder)
            expected = support.leg_bytes(support.recorded(folder, 1), 980)
        report = report_with_every_pulse_count()
        self.assertEqual(outputs_of(report), [(number + 1, pin, 180, True) for number, pin in enumerate(support.TARGET_PINS)])
        self.assertEqual(drivers_of(report), ["rmt"] * 4 + ["parallel"] * 16)
        if report["limit_ma"] > 180 * LEGS:
            self.assertEqual(held(report), [crc(colours) for colours in expected])
        else:
            self.assertGreater(report["limited"], 0)
            self.assertEqual(report["used_ma"], 180 * LEGS)
            self.assertEqual(held(report), [crc(at_the_limiters_minimum(colours)) for colours in expected])
        self.assertEqual(pulses_of(report), [24 * 180] * LEGS)
        status = support.command(PORT, "status")[1]
        self.assertEqual((status["brightness"], status["error"]), (support.DIM, None))
        time.sleep(3.0)
        support.probe()
        reports = support.each_second(SECONDS)
        for seen in reports:
            self.assertIsNotNone(seen["wire_us"], seen)
            self.assertGreaterEqual(seen["wire_us"][0], WIRE_US[0], seen["wire_us"])
            self.assertLessEqual(seen["wire_us"][1], WIRE_US[1], seen["wire_us"])
        sent = [seen["sent"] for seen in reports]
        self.assertGreaterEqual(min(sent), 49, sent)
        self.assertEqual([seen["overwritten"] for seen in reports], [0] * SECONDS)
        self.assertEqual(pulses_of(reports[-1]), [24 * 180] * LEGS)

    def test_a_leg_on_a_pin_the_board_cannot_use_leaves_the_other_outputs_working(self):
        mapping = support.legs_mapping(6, legs=3, pins=[1, 60, 2])
        with support.one_frame_show(mapping, 40) as folder:
            support.ensure_installed(folder)
            expected = support.leg_bytes(support.recorded(folder, 1), 980)
        report = report_after_a_moment()
        self.assertEqual([output["ok"] for output in report["outputs"]], [True, False, True])
        self.assertEqual([(output["pin"], output["count"]) for output in report["outputs"] if output["ok"]], [(1, 18), (2, 18)])
        self.assertEqual([held(report)[0], held(report)[2]], [crc(expected[0]), crc(expected[2])])
        self.assertGreaterEqual(min(row["sent"] for row in support.each_second(3)), 49)
        status = support.command(PORT, "status")[1]
        self.assertEqual((status["error"], status["playing"]), (None, 1))

    def test_an_invalid_mapping_leaves_wleds_own_outputs_and_keeps_them_dark(self):
        with support.dim_show() as packed, tempfile.TemporaryDirectory() as work:
            folder = pathlib.Path(work, "show")
            shutil.copytree(packed, folder)
            (folder / "mapping.json").write_text("{")
            done = support.install(folder, "--no-check")
        self.assertEqual(done.status, 1, done.err)
        self.assertEqual(json.loads(done.out)["error"], "mapping-malformed")
        stored = json.loads(storage.other_files(support.storage_image())["/cfg.json"])["hw"]["led"]["ins"]
        report = report_after_a_moment()
        self.assertEqual([(output["pin"], output["count"]) for output in report["outputs"]], [(entry["pin"][0], entry["len"]) for entry in stored])
        self.assertEqual(held(report), [crc(bytes(3 * entry["len"])) for entry in stored])
        self.assertEqual([row["sent"] for row in support.each_second(2)], [0, 0])
        self.assertEqual((report["realtime"], report["error"]), (1, "mapping-malformed"))

    def test_nothing_else_writes_to_the_outputs_over_30_seconds(self):
        with support.dim_show() as folder:
            support.ensure_installed(folder)
        support.probe()
        reports = support.each_second(30)
        self.assertEqual([report["overwritten"] for report in reports], [0] * 30)
        self.assertGreaterEqual(min(report["sent"] for report in reports), 49)
        self.assertEqual({report["realtime"] for report in reports}, {1})


class Port(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("probe")
        with support.dim_show() as folder:
            support.ensure_installed(folder)

    def test_the_report_has_the_reason_that_status_has(self):
        self.assertIsNone(support.probe()["error"])
        self.assertIsNone(support.command(PORT, "status")[1]["error"])

    def test_wled_reports_its_access_point_as_up(self):
        deadline = time.monotonic() + 20.0
        while support.probe()["ap"] != 1 and time.monotonic() < deadline:
            time.sleep(1.0)
        self.assertEqual(support.probe()["ap"], 1)

    def test_the_port_is_silent_without_a_command(self):
        self.assertEqual(support.heard(b"", 5.0), [])

    def test_wleds_handshake_gets_no_answer_and_the_byte_goes_to_the_core(self):
        self.assertEqual(support.heard(b"v", 3.0), [])
        self.assertEqual(support.heard(b"\n", 1.0), [UNKNOWN])
        self.assertEqual(support.command(PORT, "status")[0], 0)

    def test_the_probe_line_is_answered_by_the_usermod_and_every_other_byte_reaches_the_core(self):
        self.assertEqual(support.probe()["probe"], 1)
        self.assertEqual(support.heard(b"#prob\n", 1.0), [UNKNOWN])
        self.assertEqual(support.heard(b"#probes\n", 1.0), [UNKNOWN])
        self.assertEqual(support.heard(b"##probe\n", 1.0), [UNKNOWN])
        self.assertEqual(support.heard(b"on #probe\n", 1.0), [b'{"ok":false,"error":"bad-argument"}'])
        self.assertEqual(support.command(PORT, "status")[0], 0)

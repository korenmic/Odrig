import json
import time
import unittest

from fwtool import paths

from . import PORT, support, test_probe

LEGS = len(support.TARGET_PINS)
SECONDS = 10
RESULT = paths.OUT / "twenty.json"
FIGURES = ("start_ms", "heap", "sent", "gap_ms", "poll_us", "poll_mean_us", "send_us", "send_mean_us")
# The time 180 LEDs take on the wire is 5.7 ms; a pass of the loop is the measure's grain.
WIRE_US = (4500, 7500)
# A picture that does not change: one frame that lasts a minute, so that the core opens
# its file once in the time of a test.
STILL_MS = 60000
# The core checks a dense 60 x 60 clip at its start for several seconds.
START_SECONDS = 60


def row_legs(width):
    """Twenty row legs of three rows each on the pins of the target installation."""
    return support.legs_mapping(width, legs=LEGS, pins=support.TARGET_PINS)


def report_with_every_pulse_count():
    """A report in which every output has been counted once: one output is counted at
    each send."""
    deadline = time.monotonic() + 10.0
    report = test_probe.report_after_a_moment()
    while any(output["pulses"] is None for output in report["outputs"]) and time.monotonic() < deadline:
        time.sleep(0.5)
        report = support.probe()
    return report


def pulses_of(report):
    return [output["pulses"] for output in report["outputs"]]


def drivers_of(report):
    return [output["driver"] for output in report["outputs"]]


class TwentyOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("probe")

    def test_twenty_outputs_of_18_leds_hold_exactly_the_bytes_of_their_legs(self):
        mapping = row_legs(6)
        with support.one_frame_show(mapping, 40) as folder:
            support.ensure_installed(folder)
            expected = support.leg_bytes(support.recorded(folder, 1), 980)
        report = report_with_every_pulse_count()
        self.assertEqual(test_probe.outputs_of(report), [(number + 1, pin, 18, True) for number, pin in enumerate(support.TARGET_PINS)])
        self.assertEqual(drivers_of(report), ["rmt"] * 4 + ["parallel"] * 16)
        self.assertEqual(report["limited"], 0)
        self.assertEqual(test_probe.held(report), [test_probe.crc(colours) for colours in expected])
        self.assertEqual(len(set(test_probe.held(report))), LEGS)
        self.assertEqual(pulses_of(report), [24 * 18] * LEGS)

    def test_twenty_outputs_of_180_leds_carry_a_whole_refresh_49_times_a_second(self):
        mapping = row_legs(60)
        with support.one_frame_show(mapping, support.DIM, ms=STILL_MS) as folder:
            support.ensure_installed(folder)
            expected = support.leg_bytes(support.recorded(folder, 1), 980)
        report = report_with_every_pulse_count()
        self.assertEqual(test_probe.outputs_of(report), [(number + 1, pin, 180, True) for number, pin in enumerate(support.TARGET_PINS)])
        self.assertEqual(drivers_of(report), ["rmt"] * 4 + ["parallel"] * 16)
        if report["limit_ma"] > 180 * LEGS:
            self.assertEqual(test_probe.held(report), [test_probe.crc(colours) for colours in expected])
        else:
            self.assertGreater(report["limited"], 0)
            self.assertEqual(report["used_ma"], 180 * LEGS)
            self.assertEqual(test_probe.held(report), [test_probe.crc(test_probe.at_the_limiters_minimum(colours)) for colours in expected])
        self.assertEqual(pulses_of(report), [24 * 180] * LEGS)
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

    def test_the_dense_60_x_60_clips_on_twenty_outputs_are_measured_and_written(self):
        rows = []
        for compressed in (True, False):
            name = f"dense 60 x 60 clip, {'compressed' if compressed else 'uncompressed'}, twenty row legs"
            clip = support.dense_clip(compressed=compressed, width=60, height=60)
            with support.show_folder(row_legs(60), [("dense.odrg", clip)]) as folder:
                done = support.install(folder, "--wait", START_SECONDS)
            self.assertEqual(done.status, 0, done.out + done.err)
            time.sleep(3.0)
            support.probe()
            reports = support.each_second(SECONDS)
            sent = sum(seen["sent"] for seen in reports)
            rows.append({
                "show": name,
                "bytes": len(clip),
                "start_ms": reports[-1]["start_ms"],
                "heap": reports[-1]["heap"],
                "loops": [min(seen["loops"] for seen in reports), max(seen["loops"] for seen in reports)],
                "sent": [min(seen["sent"] for seen in reports), max(seen["sent"] for seen in reports)],
                "fps": support.command(PORT, "status")[1]["fps"],
                "gap_ms": max(seen["gap_ms"] for seen in reports),
                "poll_us": max(seen["poll_us"] for seen in reports),
                "poll_mean_us": round(sum(seen["poll_total_us"] for seen in reports) / sent) if sent else None,
                "send_us": max(seen["send_us"] for seen in reports),
                "send_mean_us": round(sum(seen["send_total_us"] for seen in reports) / sent) if sent else None,
                "wire_us": [min(seen["wire_us"][0] for seen in reports if seen["wire_us"]), max(seen["wire_us"][1] for seen in reports if seen["wire_us"])] if any(seen["wire_us"] for seen in reports) else None,
                "limited": max(seen["limited"] for seen in reports),
                "pulses": pulses_of(reports[-1]),
            })
            print(json.dumps(rows[-1]), flush=True)
        RESULT.parent.mkdir(parents=True, exist_ok=True)
        RESULT.write_text(json.dumps(rows, indent=2) + "\n")
        for row in rows:
            for figure in FIGURES:
                self.assertIsNotNone(row.get(figure), f"{row['show']}: {figure}")

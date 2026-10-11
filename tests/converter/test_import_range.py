import tempfile
import unittest
from fractions import Fraction as F
from pathlib import Path

from odrig import errors, jsonframes, media

from . import media_fixtures, support

LEGS_2 = support.ROOT / "mapping" / "legs-2.json"
C = media_fixtures.COLOURS


class Ranges(unittest.TestCase):
    """Parts of a video of ten frames of 40 ms: 400 ms, each frame another colour."""

    @classmethod
    def setUpClass(cls):
        folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(folder.cleanup)
        cls.folder = Path(folder.name)
        cls.video = cls.folder / "clip.mp4"
        media_fixtures.write_video(cls.video, C)
        cls.gif = cls.folder / "clip.gif"
        media_fixtures.write_gif(cls.gif, C[:4], [30, 50, 70, 0])

    def run_import(self, *options, source=None, name="out.json"):
        output = self.folder / name
        if output.exists():
            output.unlink()
        result = support.run("import", source or self.video, output, "--mapping", LEGS_2, *options)
        return result, output

    def imported(self, *options, source=None):
        """`(ms, position of the nearest list colour)` for each frame the subcommand writes."""
        result, output = self.run_import(*options, source=source)
        self.assertEqual(result, support.Result(0, "", ""))
        animation = jsonframes.read(output)
        return [(ms, media_fixtures.nearest(picture[:3])) for ms, picture in animation.frames]

    def refused(self, *options, source=None):
        result, output = self.run_import(*options, source=source)
        self.assertEqual(result.status, 1)
        self.assertTrue(result.err.startswith("error: bad-range: "), result.err)
        self.assertEqual(result.err.count("\n"), 1)
        self.assertEqual(result.out, "")
        self.assertFalse(output.exists())

    def test_without_options_the_whole_media_is_converted(self):
        self.assertEqual(self.imported(), [(40, index) for index in range(10)])

    def test_start_and_duration_select_the_stated_ticks(self):
        # Ticks at 80, 100 and 120 ms: the third frame twice and the fourth once.
        self.assertEqual(self.imported("--start", "0.08", "--duration", "0.06"), [(40, 2), (20, 3)])
        # Ticks at 100 and 120 ms.
        self.assertEqual(self.imported("--start", "0.1", "--duration", "0.04"), [(20, 2), (20, 3)])
        # Ticks at 30, 50, 70 and 90 ms: frames 0, 1, 1 and 2.
        self.assertEqual(self.imported("--start", "0.03", "--duration", "0.08"), [(20, 0), (40, 1), (20, 2)])

    def test_start_alone_runs_to_the_end_of_the_media(self):
        # From 300 ms to 400 ms: ticks at 300, 320, 340, 360 and 380.
        self.assertEqual(self.imported("--start", "0.3"), [(20, 7), (40, 8), (40, 9)])

    def test_duration_alone_starts_at_0(self):
        self.assertEqual(self.imported("--duration", "0.1"), [(40, 0), (40, 1), (20, 2)])

    def test_durations_of_30_and_50_ms_give_2_and_3_ticks_and_9_ms_gives_1(self):
        self.assertEqual(self.imported("--duration", "0.03"), [(40, 0)])
        self.assertEqual(self.imported("--duration", "0.05"), [(40, 0), (20, 1)])
        self.assertEqual(self.imported("--duration", "0.009"), [(20, 0)])
        self.assertEqual(self.imported("--duration", "0.029"), [(20, 0)])
        self.assertEqual(self.imported("--duration", "0.049"), [(40, 0)])

    def test_the_total_is_within_20_ms_of_the_requested_length(self):
        for duration_ms in (9, 30, 50, 111, 250, 399, 400):
            with self.subTest(duration_ms=duration_ms):
                frames = self.imported("--duration", f"{duration_ms / 1000:.3f}")
                total = sum(ms for ms, _ in frames)
                self.assertTrue(all(ms % 20 == 0 for ms, _ in frames))
                self.assertLessEqual(abs(total - duration_ms), 20)

    def test_a_part_of_a_gif(self):
        # Frames start at 0, 30, 80 and 150 ms. Ticks at 70, 90, 110, 130 and 150 ms.
        self.assertEqual(self.imported("--start", "0.07", "--duration", "0.1", source=self.gif), [(20, 1), (60, 2), (20, 3)])

    def test_seconds_are_decimal_numbers_rounded_to_whole_milliseconds(self):
        self.assertEqual(self.imported("--start", "0.0795", "--duration", ".06"), [(40, 2), (20, 3)])
        self.assertEqual(self.imported("--start", "8e-2", "--duration", "0.0604"), [(40, 2), (20, 3)])
        self.assertEqual(self.imported("--start", "0", "--duration", "0.4"), [(40, index) for index in range(10)])

    def test_bad_range_start_negative(self):
        self.refused("--start", "-0.1")
        self.refused("--start=-0.001", "--duration", "0.1")

    def test_bad_range_duration_not_above_0(self):
        self.refused("--duration", "0")
        self.refused("--duration", "-0.1")
        self.refused("--duration", "0.0004")

    def test_bad_range_start_not_before_the_end_of_the_media(self):
        self.refused("--start", "0.4")
        self.refused("--start", "0.5")
        self.refused("--start", "0.4", "--duration", "0.02")
        self.refused("--start", "0.25", source=self.gif)

    def test_bad_range_start_plus_duration_after_the_end_of_the_media(self):
        self.refused("--start", "0.3", "--duration", "0.101")
        self.refused("--duration", "0.401")
        self.refused("--duration", "1")
        self.refused("--start", "0.2", "--duration", "0.051", source=self.gif)

    def test_a_part_that_ends_exactly_at_the_end_of_the_media_is_accepted(self):
        self.assertEqual(self.imported("--start", "0.3", "--duration", "0.1"), [(20, 7), (40, 8), (40, 9)])
        self.assertEqual(self.imported("--start", "0.399"), [(20, 9)])
        self.assertEqual(self.imported("--start", "0.2", "--duration", "0.05", source=self.gif), [(60, 3)])

    def test_what_is_not_a_number_of_seconds_is_a_usage_error(self):
        for options in (("--start", "soon"), ("--duration", "nan"), ("--duration", "inf"), ("--start", "")):
            with self.subTest(options=options):
                result, output = self.run_import(*options)
                self.assertEqual(result.status, 2)
                self.assertIn("usage:", result.err)
                self.assertFalse(output.exists())

    def test_two_runs_give_identical_bytes(self):
        for options in ((), ("--start", "0.05", "--duration", "0.2", "--fit", "fit")):
            with self.subTest(options=options):
                first, first_output = self.run_import(*options, name="first.json")
                second, second_output = self.run_import(*options, name="second.json")
                self.assertEqual((first.status, second.status), (0, 0))
                self.assertEqual(first_output.read_bytes(), second_output.read_bytes())

    def test_the_three_fits_are_options_of_the_subcommand(self):
        # 64 x 36 on 60 x 6: fit leaves bars of black on the left and on the right.
        for fit, dark in (("fill", False), ("stretch", False), ("fit", True)):
            with self.subTest(fit=fit):
                result, output = self.run_import("--fit", fit, "--duration", "0.04")
                self.assertEqual(result.status, 0)
                picture = jsonframes.read(output).frames[0][1]
                self.assertEqual(picture[:3] == b"\x00\x00\x00", dark)
                self.assertEqual(media_fixtures.nearest(picture[3 * 30:3 * 31]), 0)
        result, output = self.run_import("--fit", "cover")
        self.assertEqual(result.status, 2)
        self.assertFalse(output.exists())

    def test_fill_is_the_default_fit(self):
        _, default = self.run_import("--duration", "0.04", name="default.json")
        _, fill = self.run_import("--fit", "fill", "--duration", "0.04", name="fill.json")
        self.assertEqual(default.read_bytes(), fill.read_bytes())


class RangesOnMadeFrames(unittest.TestCase):
    FRAMES = [(F(40 * index), F(40 * index + 40), index) for index in range(10)]

    def pictures(self, start, duration):
        return media.tick_pictures(iter(self.FRAMES), start, duration, lambda picture: picture)

    def reason(self, start, duration):
        with self.assertRaises(errors.Rejection) as caught:
            self.pictures(start, duration)
        return caught.exception.reason

    def test_the_first_tick_is_at_the_start(self):
        self.assertEqual(self.pictures(80, 60), [2, 2, 3])
        self.assertEqual(self.pictures(79, 60), [1, 2, 2])
        self.assertEqual(self.pictures(399, None), [9])

    def test_each_condition_of_bad_range(self):
        self.assertEqual(self.reason(-1, None), "bad-range")
        self.assertEqual(self.reason(0, 0), "bad-range")
        self.assertEqual(self.reason(0, -20), "bad-range")
        self.assertEqual(self.reason(400, None), "bad-range")
        self.assertEqual(self.reason(400, 20), "bad-range")
        self.assertEqual(self.reason(390, 11), "bad-range")
        self.assertEqual(self.pictures(390, 10), [9])


if __name__ == "__main__":
    unittest.main()

import shutil
import tempfile
import unittest
from fractions import Fraction as F
from pathlib import Path

from PIL import Image

from odrig import errors, jsonframes, mapping, media

from . import media_fixtures, support

LEGS_2 = support.ROOT / "mapping" / "legs-2.json"
LEGS_10 = support.ROOT / "mapping" / "legs-10.json"
C = media_fixtures.COLOURS
BLACK = (0, 0, 0)


def flat(colour, width=60, height=6):
    """A canvas picture of one colour."""
    return bytes(colour) * (width * height)


class Fixtures(unittest.TestCase):
    """A temporary folder with the media files the tests of this module read."""

    @classmethod
    def setUpClass(cls):
        folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(folder.cleanup)
        cls.folder = Path(folder.name)
        cls.canvas = mapping.read(LEGS_2)
        cls.gif = cls.folder / "clip.gif"
        media_fixtures.write_gif(cls.gif, C[:4], [30, 50, 70, 0])
        cls.videos = {}
        for ending in ("mp4", "mov"):
            cls.videos[ending] = cls.folder / f"clip.{ending}"
            media_fixtures.write_video(cls.videos[ending], C)

    def output(self, name="out.json"):
        path = self.folder / name
        if path.exists():
            path.unlink()
        return path


class Ticks(unittest.TestCase):
    """The timeline alone, on frames made in the test."""

    def pictures(self, frames, start=0, duration=None):
        return media.tick_pictures(iter(frames), start, duration, lambda picture: picture)

    def test_a_tick_shows_the_last_frame_that_starts_no_later(self):
        frames = [(F(0), F(30), "a"), (F(30), F(80), "b"), (F(80), F(150), "c"), (F(150), F(250), "d")]
        # Ticks at 0 20 | 40 60 | 80 100 120 140 | 160 180 200 220 240.
        self.assertEqual("".join(self.pictures(frames)), "aabbccccddddd")

    def test_a_frame_that_starts_exactly_at_a_tick_is_shown_at_that_tick(self):
        frames = [(F(0), F(20), "a"), (F(20), F(40), "b"), (F(40), F(60), "c")]
        self.assertEqual("".join(self.pictures(frames)), "abc")

    def test_frames_at_29_97_per_second(self):
        # A frame every 1001 / 30 ms = 33.37 ms. Six frames start at
        # 0, 33.37, 66.73, 100.1, 133.47 and 166.83 ms, and the media is 200.2 ms long.
        # Ticks:  0 20 | 40 60 | 80 100 | 120 | 140 160 | 180
        # The tick at 100 ms still shows the third frame, because the fourth starts at 100.1.
        step = F(1001, 30)
        frames = [(index * step, (index + 1) * step, str(index)) for index in range(6)]
        self.assertEqual("".join(self.pictures(frames)), "0011223445")

    def test_a_frame_that_is_on_screen_at_no_tick_is_left_out_and_not_resampled(self):
        frames = [(F(10 * index), F(10 * index + 10), index) for index in range(10)]
        seen = []

        def resample(picture):
            seen.append(picture)
            return picture

        self.assertEqual(media.tick_pictures(iter(frames), 0, None, resample), [0, 2, 4, 6, 8])
        self.assertEqual(seen, [0, 2, 4, 6, 8])

    def test_a_frame_on_screen_at_several_ticks_is_resampled_once(self):
        frames = [(F(0), F(100), "a"), (F(100), F(140), "b")]
        calls = []
        result = media.tick_pictures(iter(frames), 0, None, lambda picture: calls.append(picture) or picture)
        self.assertEqual(result, list("aaaaabb"))
        self.assertEqual(calls, ["a", "b"])

    def test_one_frame_gives_at_least_one_tick(self):
        self.assertEqual(self.pictures([(F(0), F(5), "a")]), ["a"])
        self.assertEqual(self.pictures([(F(0), F(20), "a")]), ["a"])

    def test_the_number_of_ticks_is_the_length_over_20_rounded_to_the_nearest_halves_up(self):
        for length, expected in ((1, 1), (9, 1), (10, 1), (29, 1), (30, 2), (49, 2), (50, 3), (250, 13), (F(2002, 10), 10)):
            self.assertEqual(media.tick_count(length), expected, length)
            self.assertEqual(len(self.pictures([(F(0), F(length), "a")])), expected, length)

    def test_reading_stops_when_the_requested_part_is_covered(self):
        def frames():
            yield F(0), F(40), "a"
            yield F(40), F(80), "b"
            raise AssertionError("a frame after the requested part was read")

        self.assertEqual(self.pictures(frames(), 0, 60), ["a", "a", "b"])

    def test_media_without_a_frame_is_unreadable(self):
        with self.assertRaises(errors.Rejection) as caught:
            self.pictures([])
        self.assertEqual(caught.exception.reason, "unreadable-media")


class Gif(Fixtures):
    def test_frames_are_on_screen_for_their_delays_and_the_last_delay_of_0_counts_as_100_ms(self):
        frames = list(media.source_frames(self.gif))
        self.assertEqual([(start, end) for start, end, _ in frames], [(0, 30), (30, 80), (80, 150), (150, 250)])
        self.assertEqual([tuple(picture[0, 0]) for _, _, picture in frames], list(C[:4]))

    def test_delays_of_30_50_70_and_0_ms_give_the_tick_pictures_worked_out_here(self):
        # Frames start at 0, 30, 80 and 150 ms and the media ends at 250 ms: 13 ticks.
        #   ticks 0 20            the first colour
        #   ticks 40 60           the second
        #   ticks 80 100 120 140  the third
        #   ticks 160 to 240      the fourth
        animation = media.import_media(self.gif, self.canvas)
        self.assertEqual((animation.width, animation.height), (60, 6))
        expected = [0, 0, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3]
        self.assertEqual(animation.frames, tuple((20, flat(C[index])) for index in expected))

    def test_the_subcommand_writes_merged_frames_whose_durations_are_multiples_of_20(self):
        output = self.output()
        result = support.run("import", self.gif, output, "--mapping", LEGS_2)
        self.assertEqual(result, support.Result(0, "", ""))
        animation = jsonframes.read(output)
        self.assertEqual((animation.width, animation.height), (60, 6))
        self.assertEqual(
            animation.frames, ((40, flat(C[0])), (40, flat(C[1])), (80, flat(C[2])), (100, flat(C[3])))
        )
        self.assertEqual(output.read_bytes(), jsonframes.dumps(animation))

    def test_it_runs_as_a_module(self):
        output = self.output()
        result = support.run_module("import", self.gif, output, "--mapping", LEGS_2, "--fit", "stretch")
        self.assertEqual(result, support.Result(0, "", ""))
        self.assertEqual(len(jsonframes.read(output).frames), 4)
        broken = self.folder / "module.mp4"
        broken.write_text("this is not a media file\n" * 20)
        output = self.output()
        result = support.run_module("import", broken, output, "--mapping", LEGS_2)
        self.assertEqual(result.status, 1)
        self.assertEqual(result.out, "")
        self.assertTrue(result.err.startswith("error: unreadable-media: "), result.err)
        self.assertEqual(result.err.count("\n"), 1)
        self.assertFalse(output.exists())

    def test_an_existing_output_is_replaced(self):
        output = self.output()
        output.write_bytes(b"something else, and longer than the new content " * 2000)
        self.assertEqual(support.run("import", self.gif, output, "--mapping", LEGS_2).status, 0)
        self.assertEqual(len(jsonframes.read(output).frames), 4)
        self.assertEqual(sorted(entry.name for entry in self.folder.iterdir() if entry.name.startswith("out")), ["out.json"])

    def test_a_delay_of_10_ms_counts_as_100_and_one_of_20_ms_stays(self):
        path = self.folder / "delays.gif"
        media_fixtures.write_gif(path, C[:3], [10, 20, 100])
        self.assertEqual([(start, end) for start, end, _ in media.source_frames(path)], [(0, 100), (100, 120), (120, 220)])

    def test_the_frames_are_gone_through_once(self):
        animation = media.import_media(self.gif, self.canvas)
        self.assertEqual(sum(ms for ms, _ in animation.frames), 260)

    def test_transparent_pixels_are_black(self):
        path = self.folder / "transparent.gif"
        first = Image.new("RGBA", (8, 4), C[0] + (255,))
        for x in range(4, 8):
            for y in range(4):
                first.putpixel((x, y), C[1] + (0,))
        media_fixtures.save_gif(path, [first, Image.new("RGBA", (8, 4), C[2] + (255,))], [40, 40])
        _, _, picture = next(iter(media.source_frames(path)))
        self.assertEqual(tuple(picture[0, 0]), C[0])
        self.assertEqual(tuple(picture[0, 7]), BLACK)
        # On a canvas of the picture's shape, stretched: the left half red, the right half dark.
        canvas = mapping.Mapping(mapping.ROWS, 8, 4, ())
        animation = media.import_media(path, canvas, "stretch")
        self.assertEqual(animation.frames[0][1], (bytes(C[0]) * 4 + bytes(BLACK) * 4) * 4)

    def test_the_top_row_of_the_picture_is_on_canvas_row_h(self):
        path = self.folder / "rows.gif"
        image = Image.new("RGB", (60, 6), C[2])
        for x in range(60):
            image.putpixel((x, 0), C[0])
        media_fixtures.save_gif(path, [image], [100])
        picture = media.import_media(path, self.canvas).frames[0][1]
        # Pixel order starts with canvas row 1, the bottom row; row 6 is the last 60 pixels.
        self.assertEqual(picture, bytes(C[2]) * 300 + bytes(C[0]) * 60)

    def test_a_still_gif_is_one_frame_of_100_ms(self):
        path = self.folder / "still.gif"
        Image.new("RGB", (8, 4), C[5]).save(path)
        animation = media.import_media(path, self.canvas)
        self.assertEqual(jsonframes.merged(animation.frames), [(100, flat(C[5]))])


class Video(Fixtures):
    def seen(self, animation):
        """`(ms, position of the nearest list colour)` for each merged frame, checking flatness."""
        result = []
        for ms, picture in jsonframes.merged(animation.frames):
            colours = set(jsonframes.colours(picture))
            self.assertEqual(len(colours), 1)
            result.append((ms, media_fixtures.nearest(picture[:3])))
        return result

    def test_the_first_video_stream_is_timed_from_its_first_frame(self):
        for ending, path in self.videos.items():
            with self.subTest(ending=ending):
                frames = list(media.source_frames(path))
                self.assertEqual([(start, end) for start, end, _ in frames], [(40 * i, 40 * i + 40) for i in range(10)])
                self.assertEqual([picture.shape for _, _, picture in frames], [(36, 64, 3)] * 10)
                self.assertEqual([media_fixtures.nearest(picture[18, 32]) for _, _, picture in frames], list(range(10)))

    def test_a_25_frames_per_second_source_puts_each_frame_on_two_ticks(self):
        for ending, path in self.videos.items():
            with self.subTest(ending=ending):
                animation = media.import_media(path, self.canvas)
                self.assertEqual(len(animation.frames), 20)
                self.assertEqual(self.seen(animation), [(40, index) for index in range(10)])

    def test_the_subcommand_gives_the_canvas_size_multiples_of_20_and_the_requested_length(self):
        for ending, path in self.videos.items():
            for mapping_path, size in ((LEGS_2, (60, 6)), (LEGS_10, (60, 30))):
                with self.subTest(ending=ending, size=size):
                    output = self.output()
                    result = support.run("import", path, output, "--mapping", mapping_path)
                    self.assertEqual(result, support.Result(0, "", ""))
                    animation = jsonframes.read(output)
                    self.assertEqual((animation.width, animation.height), size)
                    self.assertTrue(all(ms % 20 == 0 for ms, _ in animation.frames))
                    self.assertLessEqual(abs(sum(ms for ms, _ in animation.frames) - 400), 20)
                    self.assertEqual(len(animation.frames), 10)

    def test_the_last_frame_stays_for_the_mean_interval(self):
        path = self.folder / "three.mp4"
        media_fixtures.write_video(path, C[:3])
        self.assertEqual([(start, end) for start, end, _ in media.source_frames(path)], [(0, 40), (40, 80), (80, 120)])

    def test_a_single_frame_stays_for_20_ms(self):
        path = self.folder / "one.mp4"
        media_fixtures.write_video(path, C[:1])
        self.assertEqual([(start, end) for start, end, _ in media.source_frames(path)], [(0, 20)])
        self.assertEqual(self.seen(media.import_media(path, self.canvas)), [(20, 0)])

    def test_time_is_counted_from_the_first_frame_when_it_is_not_at_zero(self):
        for ending in ("mp4", "mov"):
            with self.subTest(ending=ending):
                path = self.folder / f"late.{ending}"
                media_fixtures.write_video(path, C[:4], first_pts=7)
                self.assertEqual([start for start, _, _ in media.source_frames(path)], [0, 40, 80, 120])
                self.assertEqual(self.seen(media.import_media(path, self.canvas)), [(40, index) for index in range(4)])

    def test_capital_letters_in_the_ending_are_accepted(self):
        for name in ("LOUD.MP4", "Mixed.Mov"):
            with self.subTest(name=name):
                path = self.folder / name
                shutil.copyfile(self.videos[name[-3:].lower()], path)
                output = self.output()
                self.assertEqual(support.run("import", path, output, "--mapping", LEGS_2).status, 0)
                self.assertEqual(len(jsonframes.read(output).frames), 10)

    def test_transparent_pixels_of_a_video_are_black(self):
        path = self.folder / "alpha.mov"
        media_fixtures.write_video(path, C[:2], codec="qtrle", pixels="argb", alpha=C[1])
        _, _, picture = next(iter(media.source_frames(path)))
        self.assertEqual(tuple(picture[0, 0]), C[0])
        self.assertEqual(tuple(picture[0, 63]), BLACK)

    def test_sound_is_ignored(self):
        # The fixtures have no sound stream; the reader takes the first video stream only.
        import av

        with av.open(str(self.videos["mp4"])) as container:
            self.assertEqual(len(container.streams.video), 1)


class Refused(Fixtures):
    def refused(self, expected, path, *options):
        output = self.output("refused.json")
        result = support.run("import", path, output, "--mapping", LEGS_2, *options)
        self.assertEqual(result.status, 1)
        self.assertEqual(result.out, "")
        self.assertTrue(result.err.startswith(f"error: {expected}: {path}: "), result.err)
        self.assertEqual(result.err.count("\n"), 1)
        self.assertFalse(output.exists())
        self.assertFalse(Path(str(output) + ".part").exists())

    def test_a_png_name_is_unsupported_media(self):
        path = self.folder / "picture.png"
        Image.new("RGB", (8, 4), C[0]).save(path)
        self.refused("unsupported-media", path)
        for name in ("clip.avi", "clip", "clip.gif.txt", "mp4"):
            self.refused("unsupported-media", self.folder / name)

    def test_a_text_file_named_mp4_is_unreadable_media(self):
        for name in ("text.mp4", "text.mov", "text.gif"):
            with self.subTest(name=name):
                path = self.folder / name
                path.write_text("this is not a media file\n" * 20)
                self.refused("unreadable-media", path)

    def test_an_empty_file_is_unreadable_media(self):
        for name in ("empty.mp4", "empty.gif"):
            path = self.folder / name
            path.write_bytes(b"")
            self.refused("unreadable-media", path)

    def test_a_gif_cut_off_in_its_first_picture_is_unreadable_media(self):
        path = self.folder / "cut.gif"
        path.write_bytes(self.gif.read_bytes()[:40])
        self.refused("unreadable-media", path)

    def test_a_png_file_named_gif_is_unreadable_media(self):
        path = self.folder / "really-png.gif"
        Image.new("RGB", (8, 4), C[0]).save(path, format="PNG")
        self.refused("unreadable-media", path)

    def test_a_media_file_that_does_not_exist_is_not_found(self):
        self.refused("not-found", self.folder / "absent.mp4")

    def test_a_missing_mapping_file_is_mapping_missing(self):
        output = self.output("refused.json")
        result = support.run("import", self.gif, output, "--mapping", self.folder / "absent.json")
        self.assertEqual(result.status, 1)
        self.assertTrue(result.err.startswith("error: mapping-missing: "), result.err)
        self.assertFalse(output.exists())

    def test_without_a_mapping_the_command_line_is_not_understood(self):
        output = self.output("refused.json")
        result = support.run("import", self.gif, output)
        self.assertEqual(result.status, 2)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

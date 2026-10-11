import json
import tempfile
import unittest
from pathlib import Path

from odrig import errors, jsonframes, mapping, odrg
from odrig.generators import dense, dvd_bounce, hello_world, rainbow

from . import support

LEGS_2 = support.ROOT / "mapping" / "legs-2.json"
LEGS_10 = support.ROOT / "mapping" / "legs-10.json"
BLACK = b"\x00\x00\x00"


def at(picture, width, x, y):
    """The colour of canvas pixel (x, y), counted from 1 with (1, 1) at the bottom-left."""
    position = (y - 1) * width + (x - 1)
    return picture[3 * position:3 * position + 3]


def lit(picture, width):
    """The pixels (x, y) of a picture that are not black."""
    count = len(picture) // 3
    return {
        (position % width + 1, position // width + 1)
        for position in range(count)
        if picture[3 * position:3 * position + 3] != BLACK
    }


def mapping_file(folder, width, height):
    """A mapping file with one leg for a canvas of the given size."""
    path = Path(folder) / f"mapping-{width}x{height}.json"
    leg = {"leg": 1, "pin": 1, "first_led": "right", "rows": list(range(height, 0, -1))}
    path.write_text(json.dumps({"version": 1, "width": width, "legs": [leg]}))
    return path


def column_mapping_file(folder, width, height):
    """A column-leg mapping file for a canvas of the given size: legs of up to three columns
    that start at the bottom."""
    path = Path(folder) / f"columns-{width}x{height}.json"
    columns = list(range(1, width + 1))
    legs = [
        {"leg": number, "pin": number, "first_led": "bottom", "columns": columns[3 * number - 3:3 * number]}
        for number in range(1, (width + 2) // 3 + 1)
    ]
    path.write_text(json.dumps({"version": 1, "height": height, "legs": legs}))
    return path


class Rainbow(unittest.TestCase):
    def test_255_different_fully_saturated_colours(self):
        self.assertEqual(len(rainbow.COLOURS), 255)
        self.assertEqual(len(set(rainbow.COLOURS)), 255)
        self.assertEqual(rainbow.COLOURS[0], bytes([255, 0, 0]))
        self.assertEqual(rainbow.COLOURS[85], bytes([0, 255, 0]))
        self.assertEqual(rainbow.COLOURS[170], bytes([0, 0, 255]))
        for entry in rainbow.COLOURS:
            self.assertEqual((max(entry), min(entry)), (255, 0))

    def test_the_hue_circle_runs_once_from_left_to_right_on_the_top_row(self):
        self.assertEqual(rainbow.colour(1, 6, 60, 6), rainbow.COLOURS[0])
        self.assertEqual(rainbow.colour(31, 6, 60, 6), rainbow.COLOURS[127])
        self.assertEqual(rainbow.colour(60, 6, 60, 6), rainbow.COLOURS[250])

    def test_each_row_below_the_top_is_moved_by_a_24th_of_the_circle(self):
        # One row down adds 1 / (4 * 6) to the hue: 255 / 24 = 10.6, so ten colours on.
        self.assertEqual(rainbow.colour(1, 5, 60, 6), rainbow.COLOURS[10])
        self.assertEqual(rainbow.colour(1, 1, 60, 6), rainbow.COLOURS[53])

    def test_a_shift_turns_the_hues(self):
        self.assertEqual(rainbow.colour(1, 6, 60, 6, shift=3), rainbow.COLOURS[3])
        self.assertEqual(rainbow.colour(60, 6, 60, 6, shift=10), rainbow.COLOURS[5])


class HelloWorld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = hello_world.frames(60, 6)
        cls.lit = lit(cls.frames[0][1], 60)

    def test_255_frames_of_20_ms_on_a_60_by_6_canvas(self):
        self.assertEqual(len(self.frames), 255)
        self.assertEqual({ms for ms, _ in self.frames}, {20})
        self.assertEqual({len(picture) for _, picture in self.frames}, {3 * 60 * 6})

    def test_the_same_122_pixels_are_lit_in_every_frame(self):
        self.assertEqual(len(self.lit), 122)
        for _, picture in self.frames:
            self.assertEqual(lit(picture, 60), self.lit)

    def test_the_tops_of_the_letters_are_on_row_6_and_the_text_spans_columns_4_to_56(self):
        self.assertEqual(max(y for _, y in self.lit), 6)
        self.assertEqual(min(y for _, y in self.lit), 1)
        self.assertEqual(min(x for x, _ in self.lit), 4)
        self.assertEqual(max(x for x, _ in self.lit), 56)

    def test_the_words_are_upright_and_read_from_left_to_right(self):
        rows = ["".join("X" if (x, y) in self.lit else "." for x in range(4, 57)) for y in range(6, 0, -1)]
        self.assertEqual(
            rows,
            [
                "X..X.XXXX.X....X.....XX.....X...X..XX..XXX..X....XXX.",
                "X..X.X....X....X....X..X....X...X.X..X.X..X.X....X..X",
                "XXXX.XXX..X....X....X..X....X...X.X..X.X..X.X....X..X",
                "X..X.X....X....X....X..X....X.X.X.X..X.XXX..X....X..X",
                "X..X.X....X....X....X..X....XX.XX.X..X.X.X..X....X..X",
                "X..X.XXXX.XXXX.XXXX..XX.....X...X..XX..X..X.XXXX.XXX.",
            ],
        )

    def test_every_lit_pixel_shows_each_of_the_255_rainbow_colours_exactly_once(self):
        everything = set(rainbow.COLOURS)
        for x, y in sorted(self.lit):
            shown = [at(picture, 60, x, y) for _, picture in self.frames]
            self.assertEqual(len(set(shown)), 255, (x, y))
            self.assertEqual(set(shown), everything, (x, y))

    def test_the_first_frame_is_the_rainbow_of_the_canvas(self):
        for x, y in self.lit:
            self.assertEqual(at(self.frames[0][1], 60, x, y), rainbow.colour(x, y, 60, 6))

    def test_the_rainbow_moves_from_left_to_right(self):
        # (4, 6) and (7, 6) are both lit: the two uprights of the H. On the top row the hue
        # of column x is (x - 1) / 60 of the circle of 255 colours: colour 12 for column 4
        # (12.75 cut to a whole number) and colour 25 for column 7 (25.5). What the left
        # one shows is shown by the right one 13 frames later.
        self.assertIn((4, 6), self.lit)
        self.assertIn((7, 6), self.lit)
        for start in (0, 100, 250):
            colour = at(self.frames[start][1], 60, 4, 6)
            later = next(
                step for step in range(1, 255)
                if at(self.frames[(start + step) % 255][1], 60, 7, 6) == colour
            )
            self.assertEqual(later, 13)

    def test_it_returns_to_its_first_state_after_the_last_frame(self):
        # Each frame turns every pixel one colour back on the circle, so one more turn after
        # frame 255 gives frame 1 again.
        position = {colour: index for index, colour in enumerate(rainbow.COLOURS)}
        for x, y in sorted(self.lit):
            shown = [position[at(picture, 60, x, y)] for _, picture in self.frames]
            for step in range(255):
                self.assertEqual((shown[step] - 1) % 255, shown[(step + 1) % 255], (x, y, step))

    def test_no_two_frames_in_a_row_are_the_same(self):
        self.assertEqual(jsonframes.merged(self.frames), self.frames)

    def test_on_a_larger_canvas_the_text_is_centred(self):
        frames = hello_world.frames(60, 30)
        self.assertEqual(len(frames), 255)
        pixels = lit(frames[0][1], 60)
        self.assertEqual(len(pixels), 122)
        self.assertEqual((min(x for x, _ in pixels), max(x for x, _ in pixels)), (4, 56))
        self.assertEqual((min(y for _, y in pixels), max(y for _, y in pixels)), (13, 18))
        wide = lit(hello_world.frames(100, 6)[0][1], 100)
        self.assertEqual((min(x for x, _ in wide), max(x for x, _ in wide)), (24, 76))

    def test_a_canvas_too_small_for_the_text(self):
        hello_world.frames(53, 6)
        for width, height in ((52, 6), (53, 5), (1, 1)):
            with self.subTest(canvas=(width, height)), self.assertRaises(errors.Rejection) as caught:
                hello_world.frames(width, height)
            self.assertEqual(caught.exception.reason, "canvas-too-small")


class DvdBounce(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = dvd_bounce.frames(60, 6)
        cls.squares = [lit(picture, 60) for _, picture in cls.frames]

    def corner(self, pixels):
        """The left column and the bottom row of a lit 2 x 2 square."""
        left, bottom = min(x for x, _ in pixels), min(y for _, y in pixels)
        self.assertEqual(pixels, {(left, bottom), (left + 1, bottom), (left, bottom + 1), (left + 1, bottom + 1)})
        return left, bottom

    def test_232_frames_of_180_ms_on_a_60_by_6_canvas(self):
        self.assertEqual(len(self.frames), 232)
        self.assertEqual({ms for ms, _ in self.frames}, {180})
        self.assertEqual({len(picture) for _, picture in self.frames}, {3 * 60 * 6})

    def test_exactly_a_2_by_2_square_is_lit_in_every_frame(self):
        for pixels in self.squares:
            self.assertEqual(len(pixels), 4)
            self.corner(pixels)

    def test_it_starts_in_the_top_left_corner(self):
        self.assertEqual(self.squares[0], {(1, 5), (2, 5), (1, 6), (2, 6)})

    def test_it_moves_one_pixel_diagonally_per_frame_and_the_loop_closes(self):
        corners = [self.corner(pixels) for pixels in self.squares]
        for step in range(232):
            (x0, y0), (x1, y1) = corners[step], corners[(step + 1) % 232]
            self.assertEqual((abs(x1 - x0), abs(y1 - y0)), (1, 1), step)

    def test_the_first_moves_are_to_the_right_and_down(self):
        corners = [self.corner(pixels) for pixels in self.squares[:5]]
        self.assertEqual(corners, [(1, 5), (2, 4), (3, 3), (4, 2), (5, 1)])

    def test_it_turns_back_at_every_edge_of_the_canvas(self):
        corners = [self.corner(pixels) for pixels in self.squares]
        self.assertEqual((min(x for x, _ in corners), max(x for x, _ in corners) + 1), (1, 60))
        self.assertEqual((min(y for _, y in corners), max(y for _, y in corners) + 1), (1, 6))
        # At the bottom edge the square goes up again while it keeps going right, and at the
        # right edge it goes left again while it keeps going down.
        self.assertEqual(corners[3:7], [(4, 2), (5, 1), (6, 2), (7, 3)])
        self.assertEqual(corners[57:60], [(58, 4), (59, 3), (58, 2)])

    def test_each_lit_pixel_has_the_colour_the_fixed_rainbow_gives_its_coordinates(self):
        for (_, picture), pixels in zip(self.frames, self.squares):
            for x, y in pixels:
                self.assertEqual(at(picture, 60, x, y), rainbow.colour(x, y, 60, 6))

    def test_no_two_frames_in_a_row_are_the_same(self):
        self.assertEqual(jsonframes.merged(self.frames), self.frames)

    def test_on_another_canvas_it_uses_the_whole_canvas(self):
        frames = dvd_bounce.frames(5, 4)
        self.assertEqual(len(frames), 12)
        corners = [self.corner(lit(picture, 5)) for _, picture in frames]
        self.assertEqual({x for x, _ in corners}, {1, 2, 3, 4})
        self.assertEqual({y for _, y in corners}, {1, 2, 3})
        self.assertEqual(len(dvd_bounce.frames(60, 30)), 1624)

    def test_a_canvas_too_small_for_the_square_to_move(self):
        dvd_bounce.frames(3, 3)
        for width, height in ((2, 2), (2, 6), (60, 2), (1, 1)):
            with self.subTest(canvas=(width, height)), self.assertRaises(errors.Rejection) as caught:
                dvd_bounce.frames(width, height)
            self.assertEqual(caught.exception.reason, "canvas-too-small")


class TrackedSources(unittest.TestCase):
    SOURCES = (("hello.json", hello_world, "hello_world"), ("dvd.json", dvd_bounce, "dvd_bounce"))

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def test_the_tracked_files_are_what_the_generators_give_for_the_two_leg_mapping(self):
        canvas = mapping.read(LEGS_2)
        for name, generator, _ in self.SOURCES:
            with self.subTest(name=name):
                frames = tuple(generator.frames(canvas.width, canvas.height))
                expected = jsonframes.dumps(jsonframes.Animation(canvas.width, canvas.height, frames))
                self.assertEqual((support.ROOT / "animations" / name).read_bytes(), expected)

    def test_the_generators_write_the_tracked_files_when_started_as_modules(self):
        for name, _, module in self.SOURCES:
            with self.subTest(name=name):
                output = self.folder / name
                result = support.run_module(output, "--mapping", LEGS_2, module=f"odrig.generators.{module}")
                self.assertEqual(result, support.Result(0, "", ""))
                self.assertEqual(output.read_bytes(), (support.ROOT / "animations" / name).read_bytes())

    def test_the_canvas_size_comes_from_the_mapping_file(self):
        output = self.folder / "hello.json"
        self.assertEqual(hello_world.main([str(output), "--mapping", str(LEGS_10)]), 0)
        animation = jsonframes.read(output)
        self.assertEqual((animation.width, animation.height), (60, 30))
        output = self.folder / "dvd.json"
        self.assertEqual(dvd_bounce.main([str(output), "--mapping", str(mapping_file(self.folder, 9, 5))]), 0)
        animation = jsonframes.read(output)
        self.assertEqual((animation.width, animation.height), (9, 5))

    def test_a_canvas_that_is_too_small_is_rejected_and_nothing_is_written(self):
        cases = (("hello_world", 52, 6), ("dvd_bounce", 2, 2))
        for module, width, height in cases:
            with self.subTest(module=module):
                small = mapping_file(self.folder, width, height)
                output = self.folder / f"{module}.json"
                result = support.run_module(output, "--mapping", small, module=f"odrig.generators.{module}")
                self.assertEqual(result.status, 1)
                self.assertEqual(result.out, "")
                self.assertTrue(result.err.startswith(f"error: canvas-too-small: {small}: "), result.err)
                self.assertEqual(result.err.count("\n"), 1)
                self.assertFalse(output.exists())

    def test_a_missing_mapping_file_is_rejected(self):
        output = self.folder / "hello.json"
        result = support.run_module(output, "--mapping", self.folder / "absent.json", module="odrig.generators.hello_world")
        self.assertEqual(result.status, 1)
        self.assertTrue(result.err.startswith("error: mapping-missing: "), result.err)
        self.assertFalse(output.exists())

    def test_a_generator_without_a_mapping_is_a_usage_error(self):
        output = self.folder / "hello.json"
        result = support.run_module(output, module="odrig.generators.hello_world")
        self.assertEqual(result.status, 2)
        self.assertIn("usage:", result.err)
        self.assertFalse(output.exists())


class ColumnLegMapping(unittest.TestCase):
    """The generators with a mapping file whose legs are columns."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def test_the_made_up_file_has_as_many_columns_as_the_canvas_is_wide(self):
        canvas = mapping.read(column_mapping_file(self.folder, 56, 8))
        self.assertEqual(canvas.kind, mapping.COLUMNS)
        self.assertEqual((canvas.width, canvas.height), (56, 8))
        self.assertEqual([len(leg.strips) for leg in canvas.legs], [3] * 18 + [2])

    def test_each_generator_writes_for_the_canvas_of_the_mapping(self):
        cases = (
            (hello_world, (56, 8), [], hello_world.frames(56, 8)),
            (dvd_bounce, (5, 9), [], dvd_bounce.frames(5, 9)),
            (dense, (7, 4), ["--seconds", "1"], dense.frames(7, 4, 1)),
        )
        for generator, (width, height), options, frames in cases:
            with self.subTest(generator=generator.__name__):
                output = self.folder / "out.json"
                made = column_mapping_file(self.folder, width, height)
                self.assertEqual(generator.main([str(output), "--mapping", str(made), *options]), 0)
                animation = jsonframes.read(output)
                self.assertEqual((animation.width, animation.height), (width, height))
                self.assertEqual(list(animation.frames), list(frames))

    def test_a_generator_started_as_a_module_writes_for_the_canvas_of_the_mapping(self):
        output = self.folder / "dvd.json"
        made = column_mapping_file(self.folder, 4, 7)
        result = support.run_module(output, "--mapping", made, module="odrig.generators.dvd_bounce")
        self.assertEqual(result, support.Result(0, "", ""))
        animation = jsonframes.read(output)
        self.assertEqual((animation.width, animation.height), (4, 7))

    def test_the_width_is_the_number_of_columns_and_not_the_height_of_the_file(self):
        # Six columns of 53 LEDs are a canvas of 6 x 53: high enough for the text, too narrow.
        narrow = column_mapping_file(self.folder, 6, 53)
        output = self.folder / "hello.json"
        result = support.run_module(output, "--mapping", narrow, module="odrig.generators.hello_world")
        self.assertEqual(result.status, 1)
        self.assertTrue(result.err.startswith(f"error: canvas-too-small: {narrow}: "), result.err)
        self.assertIn("6 x 53", result.err)
        self.assertFalse(output.exists())


class EncodedSources(unittest.TestCase):
    """The tracked sources through the encoder and the reference decoder."""

    SIZES = {
        ("hello.json", False): 17731,
        ("hello.json", True): 1134,
        ("dvd.json", False): 3799,
        ("dvd.json", True): 1594,
    }

    def test_each_encodes_and_decodes_back_to_identical_frames(self):
        for (name, compressed) in self.SIZES:
            with self.subTest(name=name, compressed=compressed):
                animation = jsonframes.read(support.ROOT / "animations" / name)
                decoded = odrg.decode(odrg.encode(animation, compressed=compressed))
                self.assertEqual((decoded.width, decoded.height), (animation.width, animation.height))
                self.assertIs(decoded.compressed, compressed)
                self.assertEqual(decoded.records, animation.frames)

    def test_the_encoded_sizes_are_within_2_percent_of_the_format_document(self):
        for (name, compressed), documented in self.SIZES.items():
            with self.subTest(name=name, compressed=compressed):
                animation = jsonframes.read(support.ROOT / "animations" / name)
                size = len(odrg.encode(animation, compressed=compressed))
                self.assertLessEqual(abs(size - documented) * 100, 2 * documented, size)

    def test_the_documented_sizes_are_those_of_the_format_document(self):
        text = (support.ROOT / "docs" / "format.md").read_text(encoding="utf-8")
        self.assertIn("| DVD bounce, 41.8 s | 60 x 6 | 232 | 3,799 | 1,594 |", text)
        self.assertIn("| Hello world, 5.1 s | 60 x 6 | 255 | 17,731 | 1,134 |", text)

    def test_the_uncompressed_sizes_are_exactly_the_documented_ones(self):
        for name in ("hello.json", "dvd.json"):
            animation = jsonframes.read(support.ROOT / "animations" / name)
            self.assertEqual(len(odrg.encode(animation, compressed=False)), self.SIZES[(name, False)])

    def test_hello_world_has_a_palette_of_black_and_the_255_rainbow_colours(self):
        animation = jsonframes.read(support.ROOT / "animations" / "hello.json")
        palette = odrg.palette_for(animation.frames)
        self.assertEqual(palette[0], BLACK)
        self.assertEqual(palette[1:], rainbow.COLOURS)


class Dense(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        canvas = mapping.read(LEGS_10)
        cls.canvas = (canvas.width, canvas.height)
        cls.frames = dense.frames(canvas.width, canvas.height, 10)

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def test_ten_seconds_for_the_ten_leg_mapping_are_500_frames_of_20_ms_on_60_by_30(self):
        self.assertEqual(self.canvas, (60, 30))
        self.assertEqual(len(self.frames), 500)
        self.assertEqual({ms for ms, _ in self.frames}, {20})
        self.assertEqual({len(picture) for _, picture in self.frames}, {3 * 60 * 30})

    def test_it_has_more_than_256_different_colours(self):
        self.assertGreater(jsonframes.colour_count(self.frames), 256)
        self.assertGreater(jsonframes.colour_count(self.frames[:1]), 256)

    def test_every_pixel_is_lit_in_every_frame(self):
        for _, picture in self.frames:
            self.assertNotIn(0, jsonframes.colours(picture))

    def test_every_pixel_changes_from_each_frame_to_the_next_almost_everywhere(self):
        self.assertEqual(len(jsonframes.merged(self.frames)), 500)
        first, second = self.frames[0][1], self.frames[1][1]
        changed = sum(1 for a, b in zip(jsonframes.colours(first), jsonframes.colours(second)) if a != b)
        self.assertGreater(changed, 1800 * 9 // 10)

    def test_it_encodes_and_decodes_back_to_identical_frames(self):
        animation = jsonframes.Animation(60, 30, tuple(self.frames))
        for compressed in (True, False):
            with self.subTest(compressed=compressed):
                decoded = odrg.decode(odrg.encode(animation, compressed=compressed))
                self.assertIs(decoded.compressed, compressed)
                self.assertEqual(decoded.palette_size, 0)
                self.assertEqual(decoded.records, animation.frames)

    def test_ten_seconds_is_the_default_length(self):
        self.assertEqual(dense.frames(4, 2), dense.frames(4, 2, 10))
        self.assertEqual(len(dense.frames(4, 2)), 500)

    def test_the_same_clip_every_time(self):
        self.assertEqual(dense.frames(60, 30, 1), self.frames[:50])

    def test_one_second_for_the_two_leg_mapping_is_50_frames_on_60_by_6(self):
        output = self.folder / "dense.json"
        result = support.run_module(output, "--mapping", LEGS_2, "--seconds", 1, module="odrig.generators.dense")
        self.assertEqual(result, support.Result(0, "", ""))
        animation = jsonframes.read(output)
        self.assertEqual((animation.width, animation.height), (60, 6))
        self.assertEqual(len(animation.frames), 50)
        self.assertEqual({ms for ms, _ in animation.frames}, {20})
        self.assertEqual(list(animation.frames), dense.frames(60, 6, 1))

    def test_the_length_is_a_whole_number_of_seconds_of_at_least_1(self):
        output = self.folder / "dense.json"
        for seconds in ("0", "-1", "1.5", "ten"):
            with self.subTest(seconds=seconds):
                self.assertEqual(dense.main([str(output), "--mapping", str(LEGS_2), "--seconds", seconds]), 2)
                self.assertFalse(output.exists())

    def test_the_clip_is_written_only_where_it_is_asked_for(self):
        before = sorted(entry.name for entry in (support.ROOT / "animations").iterdir())
        self.assertEqual(dense.main([str(self.folder / "dense.json"), "--mapping", str(LEGS_2), "--seconds", "1"]), 0)
        self.assertEqual(sorted(entry.name for entry in (support.ROOT / "animations").iterdir()), before)
        self.assertEqual([entry.name for entry in self.folder.iterdir()], ["dense.json"])


if __name__ == "__main__":
    unittest.main()

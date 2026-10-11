import unittest
from fractions import Fraction as F

import numpy

from odrig import errors, media


def source(rows):
    """A source picture from rows of grey values or of (red, green, blue) values, top row first."""
    array = numpy.array(rows, dtype=numpy.uint8)
    if array.ndim == 2:
        array = numpy.stack([array] * 3, axis=-1)
    return array


def placed(picture, fit, w, h):
    """The canvas picture as rows of colours, the top canvas row first, as it is looked at."""
    rows, columns = picture.shape[:2]
    data = media.resample(picture, media.source_rect(columns, rows, w, h, fit), w, h)
    pixels = [tuple(data[3 * p:3 * p + 3]) for p in range(w * h)]
    return [pixels[y * w:(y + 1) * w] for y in range(h - 1, -1, -1)]


def greys(picture, fit, w, h):
    """The same for grey pictures: one value for each pixel."""
    result = placed(picture, fit, w, h)
    for row in result:
        for red, green, blue in row:
            assert red == green == blue
    return [[pixel[0] for pixel in row] for row in result]


class SourceRect(unittest.TestCase):
    def test_a_source_taller_than_the_canvas_shape(self):
        # 1920 x 1080 on a 60 x 6 canvas: the canvas is 10 to 1, the source 16 to 9.
        # fill keeps the full width; 1920 / 10 = 192 rows are shown, (1080 - 192) / 2 = 444
        # rows are cut off above and below.
        self.assertEqual(media.source_rect(1920, 1080, 60, 6, "fill"), (0, 444, 1920, 192))
        # fit keeps the full height; the rectangle is 10 * 1080 = 10,800 wide and reaches
        # (10,800 - 1920) / 2 = 4440 beyond the picture on each side.
        self.assertEqual(media.source_rect(1920, 1080, 60, 6, "fit"), (-4440, 0, 10800, 1080))
        self.assertEqual(media.source_rect(1920, 1080, 60, 6, "stretch"), (0, 0, 1920, 1080))

    def test_a_source_wider_than_the_canvas_shape(self):
        # 8 x 2 on a 4 x 4 canvas: the canvas is square.
        # fill keeps the full height: 2 columns are shown, 3 are cut off on each side.
        self.assertEqual(media.source_rect(8, 2, 4, 4, "fill"), (3, 0, 2, 2))
        # fit keeps the full width: the rectangle is 8 high and reaches 3 beyond the picture
        # above and below.
        self.assertEqual(media.source_rect(8, 2, 4, 4, "fit"), (0, -3, 8, 8))
        self.assertEqual(media.source_rect(8, 2, 4, 4, "stretch"), (0, 0, 8, 2))

    def test_a_source_of_the_canvas_shape_is_shown_whole_by_every_fit(self):
        for fit in media.FITS:
            self.assertEqual(media.source_rect(120, 12, 60, 6, fit), (0, 0, 120, 12))

    def test_the_rectangle_is_exact_when_it_does_not_fall_on_whole_pixels(self):
        # 4 x 4 on a 3 x 2 canvas: fill shows 4 * 2 / 3 rows, (4 - 8/3) / 2 = 2/3 from the top.
        self.assertEqual(media.source_rect(4, 4, 3, 2, "fill"), (0, F(2, 3), 4, F(8, 3)))
        # fit shows 4 * 3 / 2 = 6 columns, one beyond the picture on each side.
        self.assertEqual(media.source_rect(4, 4, 3, 2, "fit"), (-1, 0, 6, 4))

    def test_canvas_pixels_are_square(self):
        # A square source on a canvas of 6 x 3 is cut to its middle half by fill.
        self.assertEqual(media.source_rect(100, 100, 6, 3, "fill"), (0, 25, 100, 50))

    def test_an_unknown_fit_is_a_programming_error(self):
        with self.assertRaises(ValueError):
            media.source_rect(4, 4, 2, 2, "cover")


class Shrinking(unittest.TestCase):
    def test_a_4_by_4_source_of_blocks_shrunk_to_2_by_2_is_the_mean_of_each_block(self):
        picture = source([
            [10, 20, 100, 104],
            [30, 40, 108, 112],
            [0, 0, 255, 255],
            [0, 8, 255, 255],
        ])
        # (10 + 20 + 30 + 40) / 4 = 25, (100 + 104 + 108 + 112) / 4 = 106, 8 / 4 = 2, 255.
        self.assertEqual(greys(picture, "stretch", 2, 2), [[25, 106], [2, 255]])

    def test_each_channel_is_averaged_on_its_own(self):
        picture = source([[(255, 0, 10), (1, 0, 30)], [(0, 100, 20), (0, 100, 40)]])
        self.assertEqual(placed(picture, "stretch", 1, 1), [[(64, 50, 25)]])

    def test_a_shrink_by_1_5_weights_the_shared_source_pixel_by_half(self):
        # Three source pixels on two canvas pixels: each canvas pixel covers one whole
        # source pixel and half of the middle one.
        # (0 + 90 / 2) / 1.5 = 30 and (90 / 2 + 30) / 1.5 = 50.
        self.assertEqual(greys(source([[0, 90, 30]]), "stretch", 2, 1), [[30, 50]])
        self.assertEqual(greys(source([[0], [90], [30]]), "stretch", 1, 2), [[30], [50]])

    def test_stretch_uses_a_different_factor_in_each_direction(self):
        picture = source([[10, 30, 50, 70], [110, 130, 150, 170]])
        self.assertEqual(greys(picture, "stretch", 2, 2), [[20, 60], [120, 160]])
        self.assertEqual(greys(picture, "stretch", 4, 1), [[60, 80, 100, 120]])

    def test_a_large_white_picture_stays_white(self):
        picture = numpy.full((1080, 1920, 3), 255, dtype=numpy.uint8)
        for fit in ("fill", "stretch"):
            self.assertEqual(media.resample(picture, media.source_rect(1920, 1080, 60, 30, fit), 60, 30), b"\xff" * 5400)


class Fill(unittest.TestCase):
    def test_a_wider_source_loses_the_same_on_the_left_and_on_the_right(self):
        picture = source([[1, 2, 3, 4, 5, 6], [11, 12, 13, 14, 15, 16]])
        self.assertEqual(greys(picture, "fill", 2, 2), [[3, 4], [13, 14]])

    def test_a_taller_source_loses_the_same_above_and_below(self):
        picture = source([[1, 2], [11, 12], [21, 22], [31, 32], [41, 42], [51, 52]])
        self.assertEqual(greys(picture, "fill", 2, 2), [[21, 22], [31, 32]])

    def test_fill_is_the_default_shape_of_a_cut_that_falls_inside_pixels(self):
        # 4 x 4 on 3 x 2: rows 2/3 to 10/3 are shown, in two slices of 4/3 rows.
        # The first slice has a third of row 0 and all of row 1; the second all of row 2 and
        # a third of row 3. Each canvas column covers 4/3 source columns.
        picture = source([[90] * 4, [30] * 4, [60] * 4, [120] * 4])
        # (90 / 3 + 30) / (4 / 3) = 45 and (60 + 120 / 3) / (4 / 3) = 75.
        self.assertEqual(greys(picture, "fill", 3, 2), [[45, 45, 45], [75, 75, 75]])


class Fit(unittest.TestCase):
    def test_bars_are_black_and_an_edge_inside_a_pixel_is_blended(self):
        # A 2 x 2 source on a 5 x 2 canvas: the rectangle runs from -1.5 to 3.5, one source
        # column for each canvas column. Column 1 is half bar and half picture, column 3 too.
        picture = source([[200, 200], [200, 200]])
        self.assertEqual(greys(picture, "fit", 5, 2), [[0, 100, 200, 100, 0], [0, 100, 200, 100, 0]])

    def test_the_whole_picture_is_inside_the_canvas(self):
        picture = source([[10, 20], [30, 40]])
        self.assertEqual(greys(picture, "fit", 6, 2), [[0, 0, 10, 20, 0, 0], [0, 0, 30, 40, 0, 0]])

    def test_bars_above_and_below_a_wider_source(self):
        picture = source([[10, 20, 30, 40]])
        self.assertEqual(greys(picture, "fit", 4, 3), [[0, 0, 0, 0], [10, 20, 30, 40], [0, 0, 0, 0]])
        # On 4 x 2 the picture is one source row in the middle of two canvas rows: each
        # canvas row is half bar.
        self.assertEqual(greys(picture, "fit", 4, 2), [[5, 10, 15, 20], [5, 10, 15, 20]])


class Growing(unittest.TestCase):
    def test_growing_repeats_source_pixels(self):
        picture = source([[10, 20], [30, 40]])
        self.assertEqual(
            greys(picture, "stretch", 4, 4),
            [[10, 10, 20, 20], [10, 10, 20, 20], [30, 30, 40, 40], [30, 30, 40, 40]],
        )
        self.assertEqual(greys(source([[7]]), "stretch", 3, 2), [[7, 7, 7], [7, 7, 7]])

    def test_growing_by_1_5_blends_the_canvas_pixel_that_covers_two_source_pixels(self):
        self.assertEqual(greys(source([[10, 20]]), "stretch", 3, 1), [[10, 15, 20]])


class Rounding(unittest.TestCase):
    def test_a_result_exactly_between_two_whole_numbers_rounds_up(self):
        self.assertEqual(greys(source([[0, 1]]), "stretch", 1, 1), [[1]])
        self.assertEqual(greys(source([[1, 2]]), "stretch", 1, 1), [[2]])
        self.assertEqual(greys(source([[254, 255]]), "stretch", 1, 1), [[255]])
        self.assertEqual(greys(source([[0, 1], [1, 0]]), "stretch", 1, 1), [[1]])

    def test_below_a_half_rounds_down_and_above_it_up(self):
        self.assertEqual(greys(source([[0, 0], [0, 1]]), "stretch", 1, 1), [[0]])
        self.assertEqual(greys(source([[1, 1], [1, 0]]), "stretch", 1, 1), [[1]])
        self.assertEqual(greys(source([[0, 0, 1]]), "stretch", 1, 1), [[0]])
        self.assertEqual(greys(source([[0, 1, 1]]), "stretch", 1, 1), [[1]])


class Rows(unittest.TestCase):
    def test_the_top_source_row_lands_on_canvas_row_h(self):
        red, blue = (255, 0, 0), (0, 0, 255)
        picture = source([[red], [blue]])
        data = media.resample(picture, media.source_rect(1, 2, 1, 2, "stretch"), 1, 2)
        # Pixel order: canvas row 1, the bottom row, comes first.
        self.assertEqual(data, bytes(blue) + bytes(red))

    def test_the_result_is_in_pixel_order(self):
        picture = source([[1, 2, 3], [4, 5, 6]])
        data = media.resample(picture, media.source_rect(3, 2, 3, 2, "stretch"), 3, 2)
        self.assertEqual(data, bytes([4, 4, 4, 5, 5, 5, 6, 6, 6, 1, 1, 1, 2, 2, 2, 3, 3, 3]))


class WholeNumbers(unittest.TestCase):
    def test_the_same_picture_gives_the_same_bytes(self):
        rng = numpy.random.default_rng(7)
        picture = rng.integers(0, 256, size=(37, 53, 3), dtype=numpy.uint8)
        for fit in media.FITS:
            rect = media.source_rect(53, 37, 60, 6, fit)
            self.assertEqual(media.resample(picture, rect, 60, 6), media.resample(picture.copy(), rect, 60, 6))

    def test_the_mean_agrees_with_exact_fractions(self):
        rng = numpy.random.default_rng(11)
        picture = rng.integers(0, 256, size=(5, 7, 3), dtype=numpy.uint8)
        for fit in media.FITS:
            left, top, width, height = media.source_rect(7, 5, 3, 2, fit)
            data = media.resample(picture, (left, top, width, height), 3, 2)
            for r in range(2):
                for c in range(3):
                    x0, x1 = left + c * width / 3, left + (c + 1) * width / 3
                    y0, y1 = top + r * height / 2, top + (r + 1) * height / 2
                    for channel in range(3):
                        total = F(0)
                        for j in range(5):
                            for i in range(7):
                                share_x = max(F(0), min(x1, i + 1) - max(x0, i))
                                share_y = max(F(0), min(y1, j + 1) - max(y0, j))
                                total += share_x * share_y * int(picture[j, i, channel])
                        mean = total / ((x1 - x0) * (y1 - y0))
                        expected = (2 * mean.numerator + mean.denominator) // (2 * mean.denominator)
                        position = (2 - 1 - r) * 3 + c
                        self.assertEqual(data[3 * position + channel], expected, (fit, r, c, channel))

    def test_a_picture_too_large_for_whole_number_arithmetic_is_unreadable_media(self):
        with self.assertRaises(errors.Rejection) as caught:
            media.resample(source([[1]]), (F(0), F(0), F(2 ** 31), F(2 ** 31)), 1, 1)
        self.assertEqual(caught.exception.reason, "unreadable-media")


if __name__ == "__main__":
    unittest.main()

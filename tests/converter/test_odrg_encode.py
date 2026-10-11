import random
import struct
import unittest
import zlib

from odrig import errors, jsonframes, odrg

CANVASES = [(1, 1), (1, 5), (5, 1), (2, 2), (3, 2), (7, 3), (16, 16), (60, 6)]
COMBINATIONS = [(predictor, run, k) for predictor in range(4) for run in (False, True) for k in range(8)]


def colour(rng):
    return bytes(rng.randrange(256) for _ in range(3))


def few_colours(rng, width, height, frames):
    """Pictures from a handful of colours, each frame changing some pixels of the last."""
    colours = [colour(rng) for _ in range(rng.randrange(1, 9))]
    pixels = [rng.choice(colours) for _ in range(width * height)]
    result = []
    for _ in range(frames):
        for _ in range(rng.randrange(0, max(2, width * height // 4))):
            pixels[rng.randrange(width * height)] = rng.choice(colours)
        result.append((rng.choice((20, 40, 180, 1000)), b"".join(pixels)))
    return result


def gradients(rng, width, height, frames):
    """Smooth full-colour pictures that drift from frame to frame."""
    result = []
    for frame in range(frames):
        picture = bytearray()
        for y in range(height):
            for x in range(width):
                picture += bytes(((3 * x + frame * 2) % 256, (5 * y + frame) % 256, (x + y + 3 * frame) % 256))
        result.append((20, bytes(picture)))
    return result


def noise(rng, width, height, frames):
    return [(20, rng.randbytes(3 * width * height)) for _ in range(frames)]


def timeline(frames):
    """What is on screen when: the frames with equal neighbours joined."""
    return jsonframes.merged(frames)


def records_of(data):
    """The frame records of an uncompressed file as `(duration, mode, data)`."""
    _, _, flags, width, height, palette_size, count = struct.unpack_from("<4sBBHHHI", data)
    assert flags == 0
    at = 16 + 3 * palette_size
    result = []
    for _ in range(count):
        duration, length, mode = struct.unpack_from("<HHB", data, at)
        result.append((duration, mode, data[at + 5:at + 4 + length]))
        at += 4 + length
    assert at == len(data)
    return result


class RoundTrips(unittest.TestCase):
    def check(self, width, height, frames):
        animation = jsonframes.Animation(width, height, tuple(frames))
        for compressed in (False, True):
            data = odrg.encode(animation, compressed=compressed)
            decoded = odrg.decode(data)
            self.assertEqual((decoded.width, decoded.height), (width, height))
            self.assertIs(decoded.compressed, compressed)
            self.assertEqual(timeline(decoded.records), timeline(frames))

    def test_random_animations_decode_to_their_source(self):
        makers = (few_colours, gradients, noise)
        for seed, (width, height) in enumerate(CANVASES):
            for maker in makers:
                with self.subTest(canvas=(width, height), maker=maker.__name__):
                    rng = random.Random(1000 * seed + makers.index(maker))
                    self.check(width, height, maker(rng, width, height, 12))

    def test_both_kinds_of_file_are_covered(self):
        rng = random.Random(7)
        with_palette = odrg.encode(jsonframes.Animation(7, 3, tuple(few_colours(rng, 7, 3, 12))))
        without = odrg.encode(jsonframes.Animation(7, 3, tuple(noise(rng, 7, 3, 20))))
        self.assertGreater(odrg.decode(with_palette).palette_size, 0)
        self.assertEqual(odrg.decode(without).palette_size, 0)

    def test_a_one_pixel_canvas_with_more_than_256_colours(self):
        frames = [(20, bytes((i % 256, i // 256, 7))) for i in range(300)]
        self.check(1, 1, frames)
        self.assertEqual(odrg.decode(odrg.encode(jsonframes.Animation(1, 1, tuple(frames)))).palette_size, 0)

    def test_a_source_that_was_merged_comes_back_frame_for_frame(self):
        rng = random.Random(11)
        frames = jsonframes.merged(few_colours(rng, 7, 3, 30))
        decoded = odrg.decode(odrg.encode(jsonframes.Animation(7, 3, tuple(frames))))
        self.assertEqual(list(decoded.records), frames)


class FrameRecords(unittest.TestCase):
    def pairs(self):
        """Seeded pairs of pixel buffers: `(width, bpp, old, new)`."""
        rng = random.Random(2024)
        for width, height in CANVASES:
            for bpp in (1, 3):
                n = width * height * bpp
                for kind in ("sparse", "small steps", "noise", "same", "from zero"):
                    old = rng.randbytes(n)
                    if kind == "sparse":
                        new = bytearray(old)
                        for _ in range(max(1, n // 10)):
                            new[rng.randrange(n)] = rng.randrange(256)
                    elif kind == "small steps":
                        new = bytes((value + rng.choice((-2, -1, 0, 0, 0, 1, 2))) % 256 for value in old)
                    elif kind == "noise":
                        new = rng.randbytes(n)
                    elif kind == "same":
                        new = old
                    else:
                        old = bytes(n)
                        new = bytes(rng.choice((0, 0, 0, 5)) for _ in range(n))
                    yield width, bpp, old, bytes(new)

    def forced(self, old, new, width, bpp):
        """Every coded record that fits, in the order of the tie-break: `(combination, record)`."""
        result = []
        for predictor, run, k in COMBINATIONS:
            try:
                record = odrg.coded_record(old, new, width, bpp, 20, predictor, run, k)
            except ValueError:
                continue
            result.append(((predictor, run, k), record))
        return result

    def decode_after(self, old, record, width, bpp):
        """The pixel buffer after `record`, read by the reference decoder from a file."""
        height = len(old) // (width * bpp)
        palette = [bytes((i, i, i)) for i in range(256)] if bpp == 1 else None
        data = odrg.container(width, height, palette, [odrg.stored_record(old, 20), record])
        picture = odrg.decode(data).records[1][1]
        return picture[0::3] if bpp == 1 else picture

    def test_every_forced_combination_decodes_to_the_new_buffer(self):
        for width, bpp, old, new in self.pairs():
            for combination, record in self.forced(old, new, width, bpp):
                with self.subTest(width=width, bpp=bpp, n=len(new), combination=combination):
                    self.assertEqual(self.decode_after(old, record, width, bpp), new)

    def test_a_forced_record_carries_its_mode_and_duration(self):
        old, new = bytes(12), bytes([1, 0, 0, 2] * 3)
        record = odrg.coded_record(old, new, 4, 1, 777, 2, True, 5)
        duration, length, mode = struct.unpack_from("<HHB", record)
        self.assertEqual((duration, length, mode), (777, len(record) - 4, 0x20 | 0x08 | 5))

    def test_a_forced_record_that_does_not_fit_is_a_programming_error(self):
        rng = random.Random(3)
        old, new = bytes(30), rng.randbytes(30)
        with self.assertRaises(ValueError):
            odrg.coded_record(old, new, 10, 3, 20, 3, False, 0)

    def test_the_best_record_is_no_longer_than_any_forced_one_or_the_stored_one(self):
        for width, bpp, old, new in self.pairs():
            best = odrg.best_record(old, new, width, bpp, 20)
            with self.subTest(width=width, bpp=bpp, n=len(new)):
                self.assertLessEqual(len(best), len(odrg.stored_record(new, 20)))
                for combination, record in self.forced(old, new, width, bpp):
                    self.assertLessEqual(len(best), len(record), combination)
                self.assertEqual(self.decode_after(old, best, width, bpp), new)

    def test_among_equally_small_records_the_first_in_the_stated_order_is_chosen(self):
        seen_ties = 0
        for width, bpp, old, new in self.pairs():
            best = odrg.best_record(old, new, width, bpp, 20)
            forced = self.forced(old, new, width, bpp)
            smallest = min((len(record) for _, record in forced), default=None)
            with self.subTest(width=width, bpp=bpp, n=len(new)):
                if smallest is None or smallest - 5 >= len(new):
                    self.assertEqual(best, odrg.stored_record(new, 20))
                    continue
                equal = [record for _, record in forced if len(record) == smallest]
                seen_ties += len(equal) > 1
                self.assertEqual(best, equal[0])
        self.assertGreater(seen_ties, 10)

    def test_a_record_is_stored_unless_a_coded_one_has_fewer_than_n_bytes_of_data(self):
        # One pixel with a palette: N = 1, and no coded data is shorter than one byte.
        self.assertEqual(odrg.best_record(b"\x00", b"\x00", 1, 1, 20), odrg.stored_record(b"\x00", 20))
        # Eight unchanged bytes: predictor 0 in plain mode with k = 0 needs one byte of data.
        best = odrg.best_record(bytes(8), bytes(8), 8, 1, 20)
        self.assertEqual(best, struct.pack("<HHB", 20, 2, 0x00) + b"\x00")

    def test_codes_of_each_predictor_on_a_3_by_2_canvas(self):
        # Index bytes 1 2 3 / 4 5 6 become 2 3 5 / 4 6 7.
        old, new = bytes([1, 2, 3, 4, 5, 6]), bytes([2, 3, 5, 4, 6, 7])
        # Predictor 0: the differences +1 +1 +2 0 +1 +1.
        self.assertEqual(odrg.codes(old, new, 3, 1, 0), bytes([2, 2, 4, 0, 2, 2]))
        # Predictor 1: each difference less the one on its left, the first of a row less the
        # first of the row before: +1 0 +1 / -1 +1 0.
        self.assertEqual(odrg.codes(old, new, 3, 1, 1), bytes([2, 0, 2, 1, 2, 0]))
        # Predictor 2: each new byte less its neighbour: 2 +1 +2 / +2 +2 +1.
        self.assertEqual(odrg.codes(old, new, 3, 1, 2), bytes([4, 2, 4, 4, 4, 2]))
        # Predictor 3: the new bytes themselves.
        self.assertEqual(odrg.codes(old, new, 3, 1, 3), bytes([4, 6, 10, 8, 12, 14]))

    def test_the_stored_record(self):
        self.assertEqual(odrg.stored_record(b"\x01\x02\x03", 500), b"\xf4\x01\x04\x00\x40\x01\x02\x03")


class Frames(unittest.TestCase):
    def test_noise_frames_give_stored_records(self):
        rng = random.Random(5)
        frames = noise(rng, 60, 6, 6)
        data = odrg.encode(jsonframes.Animation(60, 6, tuple(frames)), compressed=False)
        self.assertEqual(odrg.decode(data).modes, (0x40,) * 6)
        self.assertEqual([len(record) for _, _, record in records_of(data)], [3 * 60 * 6] * 6)

    def test_consecutive_identical_pictures_are_one_record(self):
        a, b = bytes([9, 9, 9]) * 4, bytes([1, 2, 3]) * 4
        frames = ((20, a), (40, a), (20, b), (20, a), (100, a), (1, a))
        decoded = odrg.decode(odrg.encode(jsonframes.Animation(2, 2, frames)))
        self.assertEqual(decoded.records, ((60, a), (20, b), (121, a)))

    def test_a_frame_of_200000_ms_becomes_four_records_with_the_same_picture(self):
        a, b = bytes([9, 9, 9]) * 4, bytes([1, 2, 3]) * 4
        frames = ((200000, a), (20, b))
        decoded = odrg.decode(odrg.encode(jsonframes.Animation(2, 2, frames)))
        self.assertEqual(decoded.records, ((65535, a), (65535, a), (65535, a), (3395, a), (20, b)))

    def test_a_frame_of_a_whole_number_of_longest_durations_has_no_remainder_record(self):
        a = bytes([9, 9, 9])
        decoded = odrg.decode(odrg.encode(jsonframes.Animation(1, 1, ((131070, a),))))
        self.assertEqual(decoded.records, ((65535, a), (65535, a)))

    def test_identical_frames_that_add_up_to_a_long_one_are_merged_then_split(self):
        a = bytes([9, 9, 9])
        frames = tuple((40000, a) for _ in range(4))
        decoded = odrg.decode(odrg.encode(jsonframes.Animation(1, 1, frames)))
        self.assertEqual([duration for duration, _ in decoded.records], [65535, 65535, 28930])

    def test_every_record_of_a_file_is_the_best_record(self):
        rng = random.Random(21)
        frames = jsonframes.merged(gradients(rng, 16, 16, 4) + noise(rng, 16, 16, 2))
        data = odrg.encode(jsonframes.Animation(16, 16, tuple(frames)), compressed=False)
        self.assertEqual(struct.unpack_from("<H", data, 10)[0], 0)
        old = bytes(768)
        at = 16
        for ms, picture in frames:
            expected = odrg.best_record(old, picture, 16, 3, ms)
            self.assertEqual(data[at:at + len(expected)], expected)
            at += len(expected)
            old = picture
        self.assertEqual(at, len(data))


class Palette(unittest.TestCase):
    ORDERED = [
        (0, 0, 0),         # no hue, brightness 0
        (128, 128, 128),   # no hue, brightness 128
        (255, 255, 255),   # no hue, brightness 255
        (255, 128, 128),   # hue 0, saturation 127/255
        (128, 0, 0),       # hue 0, saturation 1, brightness 128
        (255, 0, 0),       # hue 0, saturation 1, brightness 255
        (255, 1, 0),       # hue 1/255
        (254, 1, 0),       # hue 1/254
        (255, 128, 0),     # hue 128/255
        (255, 255, 0),     # hue 1
        (0, 255, 0),       # hue 2
        (0, 255, 255),     # hue 3
        (0, 0, 255),       # hue 4
        (255, 0, 255),     # hue 5
        (255, 0, 128),     # hue 5 + 127/255
    ]

    def frames(self, colours, seed=1):
        shuffled = [bytes(entry) for entry in colours]
        random.Random(seed).shuffle(shuffled)
        return [(20, b"".join(shuffled))]

    def test_a_known_colour_set_is_ordered_by_hue_then_saturation_then_brightness(self):
        expected = [bytes(entry) for entry in self.ORDERED]
        for seed in range(5):
            self.assertEqual(odrg.palette_for(self.frames(self.ORDERED, seed)), expected)

    def test_the_file_carries_the_palette_in_that_order(self):
        frames = self.frames(self.ORDERED)
        data = odrg.encode(jsonframes.Animation(len(self.ORDERED), 1, tuple(frames)), compressed=False)
        count = struct.unpack_from("<H", data, 10)[0]
        self.assertEqual(count, len(self.ORDERED))
        self.assertEqual(data[16:16 + 3 * count], b"".join(bytes(entry) for entry in self.ORDERED))

    def test_the_palette_holds_exactly_the_colours_of_all_frames(self):
        a, b, c = bytes([5, 5, 5]), bytes([200, 0, 0]), bytes([0, 0, 200])
        frames = [(20, a + a), (20, a + b), (20, c + a)]
        self.assertEqual(odrg.palette_for(frames), [a, b, c])

    def test_256_colours_have_a_palette_and_257_do_not(self):
        colours = [bytes((i, 255 - i, i // 2)) for i in range(256)]
        self.assertEqual(len(odrg.palette_for([(20, b"".join(colours))])), 256)
        self.assertIsNone(odrg.palette_for([(20, b"".join(colours)), (20, bytes([1, 1, 1]) * 256)]))
        with_palette = odrg.encode(jsonframes.Animation(256, 1, ((20, b"".join(colours)),)))
        self.assertEqual(odrg.decode(with_palette).palette_size, 256)
        without = odrg.encode(jsonframes.Animation(257, 1, ((20, b"".join(colours) + bytes([1, 1, 1])),)))
        self.assertEqual(odrg.decode(without).palette_size, 0)

    def test_to_buffer(self):
        a, b = bytes([5, 5, 5]), bytes([200, 0, 0])
        self.assertEqual(odrg.to_buffer(a + b + b + a, [a, b]), bytes([0, 1, 1, 0]))
        self.assertEqual(odrg.to_buffer(a + b, None), a + b)


class Refused(unittest.TestCase):
    def reason(self, animation):
        with self.assertRaises(errors.Rejection) as caught:
            odrg.encode(animation)
        return caught.exception.reason

    def test_canvas_too_large_with_a_palette(self):
        self.assertEqual(self.reason(jsonframes.Animation(65535, 1, ((20, bytes(3 * 65535)),))), "canvas-too-large")
        largest = odrg.encode(jsonframes.Animation(65534, 1, ((20, bytes(3 * 65534)),)))
        self.assertEqual(odrg.decode(largest).records, ((20, bytes(3 * 65534)),))

    def test_canvas_too_large_without_a_palette(self):
        # 150 x 146 is 21,900 pixels: 21,900 bytes with a palette, 65,700 without one.
        plain = bytes(3 * 21900)
        many = b"".join(i.to_bytes(3, "big") for i in range(21900))
        self.assertEqual(odrg.decode(odrg.encode(jsonframes.Animation(150, 146, ((20, plain),)))).palette_size, 1)
        self.assertEqual(self.reason(jsonframes.Animation(150, 146, ((20, many),))), "canvas-too-large")

    def test_too_many_frames(self):
        picture = bytes(3)
        self.assertEqual(self.reason(jsonframes.Animation(1, 1, ((65535 * 2 ** 32, picture),))), "too-many-frames")
        frames = ((65535 * 2 ** 32 - 1, picture), (20, bytes([1, 1, 1])))
        self.assertEqual(self.reason(jsonframes.Animation(1, 1, frames)), "too-many-frames")

    def test_the_canvas_is_judged_before_the_number_of_frames(self):
        animation = jsonframes.Animation(65535, 1, ((65535 * 2 ** 32, bytes(3 * 65535)),))
        self.assertEqual(self.reason(animation), "canvas-too-large")


class Container(unittest.TestCase):
    ANIMATION = jsonframes.Animation(2, 1, ((20, bytes([1, 2, 3, 4, 5, 6])), (40, bytes([1, 2, 3, 9, 9, 9]))))

    def test_compressed_by_default_with_flag_bit_0_set(self):
        data = odrg.encode(self.ANIMATION)
        self.assertEqual(data[5], 1)
        plain = odrg.encode(self.ANIMATION, compressed=False)
        self.assertEqual(plain[5], 0)
        self.assertEqual(data[:5] + data[6:16], plain[:5] + plain[6:16])

    def test_the_compressed_body_is_one_raw_deflate_stream_of_the_uncompressed_body(self):
        data = odrg.encode(self.ANIMATION)
        plain = odrg.encode(self.ANIMATION, compressed=False)
        inflater = zlib.decompressobj(wbits=-15)
        self.assertEqual(inflater.decompress(data[16:]), plain[16:])
        self.assertTrue(inflater.eof)
        self.assertEqual(inflater.unused_data, b"")

    def test_compression_is_kept_when_it_makes_the_file_larger(self):
        animation = jsonframes.Animation(1, 1, ((20, bytes([1, 2, 3])),))
        data, plain = odrg.encode(animation), odrg.encode(animation, compressed=False)
        self.assertGreater(len(data), len(plain))
        self.assertEqual(data[5], 1)

    def test_the_header(self):
        plain = odrg.encode(self.ANIMATION, compressed=False)
        self.assertEqual(struct.unpack_from("<4sBBHHHI", plain), (b"ODRG", 1, 0, 2, 1, 3, 2))

    def test_container_takes_any_deflate_function(self):
        records = [odrg.stored_record(bytes([0, 0]), 20)]
        palette = [bytes([7, 7, 7])]
        stored_blocks = zlib.compressobj(0, zlib.DEFLATED, -15)
        data = odrg.container(2, 1, palette, records, lambda body: stored_blocks.compress(body) + stored_blocks.flush())
        self.assertEqual(data[5], 1)
        self.assertEqual(odrg.decode(data).records, ((20, bytes([7] * 6)),))

    def test_encoding_twice_gives_identical_bytes(self):
        rng = random.Random(99)
        animation = jsonframes.Animation(16, 16, tuple(gradients(rng, 16, 16, 10)))
        for compressed in (False, True):
            self.assertEqual(odrg.encode(animation, compressed), odrg.encode(animation, compressed))


if __name__ == "__main__":
    unittest.main()

import struct
import unittest
import zlib

from odrig import errors, odrg


def header(width, height, palette=0, frames=1, flags=0, magic=b"ODRG", version=1):
    return struct.pack("<4sBBHHHI", magic, version, flags, width, height, palette, frames)


def record(duration, mode, data, length=None):
    """A frame record. `length` overrides the L field, which is otherwise right for the data."""
    if length is None:
        length = len(data) + 1
    return struct.pack("<HHB", duration, length, mode) + data


def mode(k=0, run=0, predictor=0):
    return k | run << 3 | predictor << 4


def bits(text, pad="0"):
    """Bytes from a string of 0 and 1. Spaces are ignored; `pad` fills the last byte."""
    text = text.replace(" ", "")
    text += pad * (-len(text) % 8)
    return bytes(int(text[at:at + 8], 2) for at in range(0, len(text), 8))


def palette(count):
    """A palette whose entry i is the colour (i, 100 + i, 200 + i)."""
    return b"".join(bytes([i & 255, (100 + i) & 255, (200 + i) & 255]) for i in range(count))


def through(count, indexes):
    """The picture of index bytes shown through `palette(count)`."""
    table = palette(count)
    return b"".join(table[3 * i:3 * i + 3] for i in indexes)


def stored_block(body):
    """A raw DEFLATE stream made of one stored block."""
    return b"\x01" + struct.pack("<HH", len(body), len(body) ^ 0xFFFF) + body


STORED = 0x40
NONE = 3

# A 3 x 2 palette canvas: N = 6, one byte per pixel, three bytes per row.
# FIRST sets the index bytes 1 2 3 4 5 6 with predictor 3, plain mode, k = 2.
# The residuals are +1 to +6, so the codes are 2 4 6 8 10 12. In Rice(2):
#   2 = 0 10    4 = 10 00    6 = 10 10    8 = 110 00    10 = 110 10    12 = 1110 00
FIRST = record(500, mode(k=2, predictor=NONE), bits("010 1000 1010 11000 11010 111000"))


def decoded(data):
    return odrg.decode(data)


def pictures(data):
    return [picture for _, picture in odrg.decode(data).records]


def reason_of(data):
    try:
        odrg.decode(data)
    except errors.Rejection as rejection:
        return rejection.reason
    return None


class BitCodes(unittest.TestCase):
    def test_rice_code_of_5_with_k_1_is_1101(self):
        # 1 x 1 without a palette: three codes. 5 = 1101, 0 = 00, 2 = 100.
        # Code 5 is the residual -3, code 0 is 0, code 2 is +1.
        data = header(1, 1) + record(20, mode(k=1, predictor=NONE), bits("1101 00 100"))
        self.assertEqual(pictures(data), [bytes([253, 0, 1])])

    def test_codes_0_to_4_and_255_are_the_residuals_0_minus_1_1_minus_2_2_and_minus_128(self):
        # 2 x 1 without a palette, k = 0: a value below 8 is that many one-bits and a zero-bit,
        # and 255 is eight one-bits followed by 255 as eight bits.
        codes = "0 10 110 1110 11110 11111111 11111111"
        data = header(2, 1) + record(20, mode(k=0, predictor=NONE), bits(codes))
        self.assertEqual(pictures(data), [bytes([0, 255, 1, 254, 2, 128])])

    def test_eight_one_bits_are_followed_by_the_value_as_eight_bits(self):
        # 3 in the long form, then 0 and 1 in the short form, with k = 0.
        data = header(1, 1) + record(20, mode(k=0, predictor=NONE), bits("11111111 00000011 0 10"))
        self.assertEqual(pictures(data), [bytes([254, 0, 255])])

    def test_rice_with_k_7(self):
        # 127 = 0 1111111, 0 = 0 0000000, 64 = 0 1000000.
        # Code 127 is -64, code 64 is +32.
        codes = "0 1111111  0 0000000  0 1000000"
        data = header(1, 1) + record(20, mode(k=7, predictor=NONE), bits(codes))
        self.assertEqual(pictures(data), [bytes([192, 0, 32])])

    def test_rice_with_k_7_and_one_one_bit(self):
        # Run mode: Gamma 1, then Rice(7) of 254 = 10 1111110, so u[0] = 255, which is -128.
        # Gamma 3 = 011 ends the buffer with two zero codes.
        data = header(1, 1) + record(20, mode(k=7, run=1, predictor=NONE), bits("1 10 1111110 011"))
        self.assertEqual(pictures(data), [bytes([128, 0, 0])])

    def test_gamma_codes_of_1_2_and_5_in_run_mode(self):
        # 3 x 1 without a palette: nine codes, run mode, k = 0.
        #   Gamma 1 = 1      no zero code,    then Rice 0 = 0:  u[0] = 1
        #   Gamma 2 = 010    one zero code,   then Rice 1 = 10: u[2] = 2
        #   Gamma 5 = 00101  four zero codes, then Rice 0 = 0:  u[7] = 1
        #   Gamma 2 = 010    one zero code, which reaches the end.
        # The codes are 1 0 2 0 0 0 0 1 0: residuals -1 0 +1 0 0 0 0 -1 0.
        data = header(3, 1) + record(20, mode(k=0, run=1, predictor=NONE), bits("1 0 010 10 00101 0 010"))
        self.assertEqual(pictures(data), [bytes([255, 0, 1, 0, 0, 0, 0, 255, 0])])

    def test_nothing_follows_a_non_zero_last_code_in_run_mode(self):
        # Gamma 3 = 011: two zero codes. Rice(1) of 4 = 110 0: u[2] = 5, the residual -3.
        data = header(1, 1) + record(20, mode(k=1, run=1, predictor=NONE), bits("011 1100"))
        self.assertEqual(pictures(data), [bytes([0, 0, 253])])

    def test_one_gamma_code_can_cover_the_whole_buffer(self):
        # 3 x 2 without a palette: 18 codes, all zero. Gamma 19 = 0000 10011.
        data = header(3, 2) + record(20, mode(run=1, predictor=NONE), bits("0000 10011"))
        self.assertEqual(pictures(data), [bytes(18)])

    def test_padding_bits_are_not_examined(self):
        zeros = header(1, 1) + record(20, mode(k=1, predictor=NONE), bits("1101 00 100", pad="0"))
        ones = header(1, 1) + record(20, mode(k=1, predictor=NONE), bits("1101 00 100", pad="1"))
        self.assertNotEqual(zeros, ones)
        self.assertEqual(pictures(ones), pictures(zeros))

    def test_seven_padding_bits_are_accepted(self):
        # Three codes of three bits each with k = 2: nine bits, then seven bits of padding.
        data = header(1, 1) + record(20, mode(k=2, predictor=NONE), bits("001 010 011"))
        self.assertEqual(pictures(data), [bytes([255, 1, 254])])


class Predictors(unittest.TestCase):
    def after_first(self, second):
        data = header(3, 2, palette=8, frames=2) + palette(8) + FIRST + second
        result = decoded(data)
        self.assertEqual(result.records[0], (500, through(8, [1, 2, 3, 4, 5, 6])))
        return result.records[1]

    def test_3_none_takes_the_residuals_as_the_buffer(self):
        data = header(3, 2, palette=8) + palette(8) + FIRST
        self.assertEqual(decoded(data).records, ((500, through(8, [1, 2, 3, 4, 5, 6])),))

    def test_0_previous_frame(self):
        # Residuals +1 0 -1 +2 0 -2 are the codes 2 0 1 4 0 3; with k = 0:
        #   110 0 10 11110 0 1110
        # 1 2 3 4 5 6 becomes 2 2 2 6 5 4.
        second = record(40, mode(k=0, predictor=0), bits("110 0 10 11110 0 1110"))
        self.assertEqual(self.after_first(second), (40, through(8, [2, 2, 2, 6, 5, 4])))

    def test_1_previous_frame_then_left(self):
        # Residuals +1 0 +1 -1 +1 0 are the codes 2 0 2 1 2 0; with k = 0:
        #   110 0 110 10 110 0
        # d[0] = 1, d[1] = 0 + d[0] = 1, d[2] = 1 + d[1] = 2;
        # d[3] starts the second row, so its neighbour is d[0]: -1 + 1 = 0;
        # d[4] = 1 + d[3] = 1, d[5] = 0 + d[4] = 1.
        # 1 2 3 4 5 6 plus 1 1 2 0 1 1 is 2 3 5 4 6 7.
        second = record(40, mode(k=0, predictor=1), bits("110 0 110 10 110 0"))
        self.assertEqual(self.after_first(second), (40, through(8, [2, 3, 5, 4, 6, 7])))

    def test_2_left(self):
        # Residuals +3 +1 +1 +2 -1 0 are the codes 6 2 2 4 1 0; in Rice(1):
        #   6 = 1110 0   2 = 10 0   2 = 10 0   4 = 110 0   1 = 0 1   0 = 0 0
        # new[0] = 3 + 0, new[1] = 1 + 3 = 4, new[2] = 1 + 4 = 5;
        # new[3] starts the second row, so its neighbour is new[0]: 2 + 3 = 5;
        # new[4] = -1 + 5 = 4, new[5] = 0 + 4 = 4.
        second = record(40, mode(k=1, predictor=2), bits("11100 100 100 1100 01 00"))
        self.assertEqual(self.after_first(second), (40, through(8, [3, 4, 5, 5, 4, 4])))

    def test_2_left_does_not_depend_on_the_previous_frame(self):
        first_only = header(3, 2, palette=8) + palette(8)
        first_only += record(40, mode(k=1, predictor=2), bits("11100 100 100 1100 01 00"))
        self.assertEqual(pictures(first_only), [through(8, [3, 4, 5, 5, 4, 4])])

    def test_the_first_pixel_of_the_first_row_has_the_neighbour_0(self):
        # 1 x 1 with a palette: one code, 6, in Rice(1) = 1110 0. The index is 3 + 0.
        for predictor in (1, 2):
            with self.subTest(predictor=predictor):
                data = header(1, 1, palette=4) + palette(4)
                data += record(20, mode(k=1, predictor=predictor), bits("11100"))
                self.assertEqual(pictures(data), [through(4, [3])])

    def test_2_left_without_a_palette_uses_the_same_channel_of_the_pixel_to_the_left(self):
        # 2 x 2 without a palette: N = 12, three bytes per pixel, six bytes per row.
        # Residuals: 10 20 30, +1 +2 -1, +5 0 -5, 0 +1 0.
        # Codes:     20 40 60,  2  4  1, 10 0  9, 0  2 0.
        # In Rice(3):
        #   20 = 110 100   40 = 111110 000   60 = 11111110 100
        #    2 = 0 010      4 = 0 100         1 = 0 001
        #   10 = 10 010     0 = 0 000         9 = 10 001
        #    0 = 0 000      2 = 0 010         0 = 0 000
        # Pixel (1,1) = 10 20 30. Pixel (2,1) adds to it: 11 22 29.
        # Pixel (1,2) starts a row, so it adds to pixel (1,1): 15 20 25.
        # Pixel (2,2) adds to pixel (1,2): 15 21 25.
        codes = "110100 111110000 11111110100  0010 0100 0001  10010 0000 10001  0000 0010 0000"
        data = header(2, 2) + record(20, mode(k=3, predictor=2), bits(codes))
        self.assertEqual(pictures(data), [bytes([10, 20, 30, 11, 22, 29, 15, 20, 25, 15, 21, 25])])

    def test_1_without_a_palette(self):
        # 2 x 1 without a palette: N = 6, one row. The first record stores 10 20 30 40 50 60.
        # Second record, predictor 1: residuals +1 +2 +3 0 -1 +1, codes 2 4 6 0 1 2; k = 0:
        #   110 11110 1111110 0 10 110
        # d = 1 2 3, then each channel adds to the pixel on its left: 1 1 4.
        # 10 20 30 40 50 60 plus 1 2 3 1 1 4 is 11 22 33 41 51 64.
        second = "110 11110 1111110 0 10 110"
        data = header(2, 1, frames=2)
        data += record(20, STORED, bytes([10, 20, 30, 40, 50, 60]))
        data += record(20, mode(k=0, predictor=1), bits(second))
        self.assertEqual(pictures(data), [bytes([10, 20, 30, 40, 50, 60]), bytes([11, 22, 33, 41, 51, 64])])

    def test_arithmetic_is_modulo_256(self):
        # 2 x 1 without a palette. The first record stores 250 3 128 0 0 0.
        # Second record, predictor 0, k = 4: +10 is code 20 = 10 0100, -5 is code 9 = 0 1001,
        # -128 is code 255 = eight one-bits and 11111111, and three codes 0 = 0 0000.
        # 250 + 10 = 4, 3 - 5 = 254, 128 - 128 = 0.
        codes = "10 0100  0 1001  11111111 11111111  0 0000  0 0000  0 0000"
        data = header(2, 1, frames=2)
        data += record(20, STORED, bytes([250, 3, 128, 0, 0, 0]))
        data += record(20, mode(k=4, predictor=0), bits(codes))
        self.assertEqual(pictures(data)[1], bytes([4, 254, 0, 0, 0, 0]))


class WholeFiles(unittest.TestCase):
    def test_what_decode_returns(self):
        data = header(3, 2, palette=8, frames=2) + palette(8) + FIRST
        data += record(40, mode(k=0, predictor=0), bits("110 0 10 11110 0 1110"))
        result = decoded(data)
        self.assertEqual((result.width, result.height), (3, 2))
        self.assertEqual(result.palette_size, 8)
        self.assertIs(result.compressed, False)
        self.assertEqual(result.modes, (0x32, 0x00))
        self.assertEqual([duration for duration, _ in result.records], [500, 40])

    def test_the_buffer_starts_as_zero(self):
        # Predictor 0 with 18 zero codes leaves the buffer as it started.
        data = header(3, 2) + record(20, mode(run=1, predictor=0), bits("0000 10011"))
        self.assertEqual(pictures(data), [bytes(18)])

    def test_a_stored_frame_without_a_palette(self):
        data = header(2, 1) + record(20, STORED, bytes([1, 2, 3, 250, 251, 252]))
        result = decoded(data)
        self.assertEqual(result.records, ((20, bytes([1, 2, 3, 250, 251, 252])),))
        self.assertEqual(result.modes, (0x40,))

    def test_a_stored_frame_with_a_palette(self):
        data = header(2, 1, palette=3) + palette(3) + record(20, STORED, bytes([2, 0]))
        self.assertEqual(pictures(data), [through(3, [2, 0])])

    def test_a_coded_frame_applies_to_what_a_stored_frame_left(self):
        # Predictor 0, k = 0, residuals +1 0 -1: codes 2 0 1 = 110 0 10.
        data = header(1, 1, frames=2)
        data += record(20, STORED, bytes([7, 8, 9]))
        data += record(30, mode(k=0, predictor=0), bits("110 0 10"))
        self.assertEqual(decoded(data).records, ((20, bytes([7, 8, 9])), (30, bytes([8, 8, 8]))))

    def test_durations_of_1_and_65535(self):
        data = header(1, 1, frames=2)
        data += record(1, STORED, bytes(3))
        data += record(65535, STORED, bytes([1, 1, 1]))
        self.assertEqual([duration for duration, _ in decoded(data).records], [1, 65535])

    def test_a_palette_of_256_colours(self):
        data = header(2, 1, palette=256) + palette(256) + record(20, STORED, bytes([255, 0]))
        self.assertEqual(pictures(data), [through(256, [255, 0])])

    def test_a_compressed_body_made_of_one_stored_block(self):
        body = palette(3) + record(20, STORED, bytes([2, 0]))
        data = header(2, 1, palette=3, flags=1) + stored_block(body)
        result = decoded(data)
        self.assertIs(result.compressed, True)
        self.assertEqual(result.records, ((20, through(3, [2, 0])),))

    def test_a_compressed_body_made_by_zlib(self):
        body = palette(8) + FIRST + record(40, mode(k=0, predictor=0), bits("110 0 10 11110 0 1110"))
        deflater = zlib.compressobj(9, zlib.DEFLATED, -15)
        stream = deflater.compress(body) + deflater.flush()
        plain = decoded(header(3, 2, palette=8, frames=2) + body)
        packed = decoded(header(3, 2, palette=8, frames=2, flags=1) + stream)
        self.assertIs(packed.compressed, True)
        self.assertEqual(packed.records, plain.records)
        self.assertEqual(packed.modes, plain.modes)

    def test_the_largest_canvas(self):
        # 65,534 x 1 with a palette: N = 65,534. One run of all zero codes is Gamma 65,535:
        # fifteen zero-bits and sixteen one-bits.
        data = header(65534, 1, palette=1) + palette(1)
        data += record(20, mode(run=1, predictor=NONE), bits("0" * 15 + "1" * 16))
        self.assertEqual(pictures(data), [through(1, [0]) * 65534])

    def test_the_largest_canvas_without_a_palette(self):
        # 21,844 x 1 without a palette: N = 65,532, so Gamma 65,533 = 15 zero-bits and
        # 1111 1111 1111 1101.
        data = header(21844, 1) + record(20, mode(run=1, predictor=NONE), bits("0" * 15 + "1111111111111101"))
        self.assertEqual(pictures(data), [bytes(65532)])


class Rejected(unittest.TestCase):
    VALID = header(2, 1, palette=3) + palette(3) + record(20, STORED, bytes([2, 0]))

    def check(self, expected, data):
        self.assertEqual(reason_of(data), expected)

    def test_the_file_these_cases_start_from_is_valid(self):
        self.check(None, self.VALID)

    def test_truncated_in_the_header(self):
        self.check("truncated", b"")
        self.check("truncated", self.VALID[:15])
        self.check("truncated", b"ODRG")

    def test_truncated_in_the_palette(self):
        self.check("truncated", self.VALID[:16])
        self.check("truncated", self.VALID[:16 + 8])

    def test_truncated_in_the_first_five_bytes_of_a_record(self):
        self.check("truncated", self.VALID[:16 + 9])
        self.check("truncated", self.VALID[:16 + 9 + 4])

    def test_truncated_in_the_data_of_a_record(self):
        self.check("truncated", self.VALID[:16 + 9 + 5])
        self.check("truncated", self.VALID[:-1])

    def test_truncated_before_a_later_record(self):
        self.check("truncated", header(2, 1, palette=3, frames=2) + self.VALID[16:])

    def test_truncated_deflate_stream(self):
        stream = stored_block(self.VALID[16:])
        self.check(None, header(2, 1, palette=3, flags=1) + stream)
        self.check("truncated", header(2, 1, palette=3, flags=1) + stream[:-1])
        self.check("truncated", header(2, 1, palette=3, flags=1) + stream[:3])
        self.check("truncated", header(2, 1, palette=3, flags=1))

    def test_truncated_deflate_stream_made_by_zlib(self):
        deflater = zlib.compressobj(9, zlib.DEFLATED, -15)
        stream = deflater.compress(self.VALID[16:] * 1) + deflater.flush()
        self.check(None, header(2, 1, palette=3, flags=1) + stream)
        self.check("truncated", header(2, 1, palette=3, flags=1) + stream[:-1])

    def test_truncated_when_a_complete_deflate_stream_ends_inside_a_record(self):
        self.check("truncated", header(2, 1, palette=3, flags=1) + stored_block(self.VALID[16:-1]))
        self.check("truncated", header(2, 1, palette=3, flags=1) + stored_block(palette(3)))
        self.check("truncated", header(2, 1, palette=3, flags=1) + stored_block(b""))

    def test_bad_magic(self):
        self.check("bad-magic", header(2, 1, palette=3, magic=b"ODRX") + self.VALID[16:])
        self.check("bad-magic", header(2, 1, palette=3, magic=b"odrg") + self.VALID[16:])
        self.check("bad-magic", b"\x00" + self.VALID[1:])

    def test_bad_version(self):
        self.check("bad-version", header(2, 1, palette=3, version=2) + self.VALID[16:])
        self.check("bad-version", header(2, 1, palette=3, version=0) + self.VALID[16:])

    def test_reserved_bits_in_the_flags(self):
        for bit in range(1, 8):
            with self.subTest(bit=bit):
                self.check("reserved-bits", header(2, 1, palette=3, flags=1 << bit) + self.VALID[16:])

    def test_reserved_bits_bit_7_of_a_mode_byte(self):
        coded = header(1, 1) + record(20, mode(k=1, predictor=NONE), bits("1101 00 100"))
        self.check(None, coded)
        self.check("reserved-bits", header(1, 1) + record(20, 0x80 | mode(k=1, predictor=NONE), bits("1101 00 100")))
        self.check("reserved-bits", header(2, 1, palette=3) + palette(3) + record(20, 0xC0, bytes([2, 0])))

    def test_reserved_bits_a_stored_mode_byte_other_than_0x40(self):
        for other in (0x41, 0x48, 0x50, 0x60, 0x7F):
            with self.subTest(mode=other):
                self.check("reserved-bits", header(2, 1, palette=3) + palette(3) + record(20, other, bytes([2, 0])))

    def test_zero_size(self):
        self.check("zero-size", header(0, 1, palette=3) + self.VALID[16:])
        self.check("zero-size", header(2, 0, palette=3) + self.VALID[16:])
        self.check("zero-size", header(0, 0, palette=3) + self.VALID[16:])

    def test_bad_palette_size(self):
        self.check("bad-palette-size", header(2, 1, palette=257) + palette(257) + record(20, STORED, bytes([2, 0])))
        self.check("bad-palette-size", header(2, 1, palette=65535) + self.VALID[16:])

    def test_canvas_too_large(self):
        self.check("canvas-too-large", header(65535, 1, palette=1) + palette(1))
        self.check("canvas-too-large", header(21845, 1))
        self.check("canvas-too-large", header(256, 256, palette=1) + palette(1))
        self.check("canvas-too-large", header(65535, 65535))

    def test_no_frames(self):
        self.check("no-frames", header(2, 1, palette=3, frames=0) + palette(3))
        self.check("no-frames", header(2, 1, palette=3, frames=0) + self.VALID[16:])

    def test_bad_deflate(self):
        compressed = header(2, 1, palette=3, flags=1)
        self.check("bad-deflate", compressed + b"\x07")
        self.check("bad-deflate", compressed + b"\x01\x0b\x00\x00\x00" + self.VALID[16:])
        self.check("bad-deflate", compressed + self.VALID[16:])

    def test_zero_duration(self):
        self.check("zero-duration", header(2, 1, palette=3) + palette(3) + record(0, STORED, bytes([2, 0])))

    def test_bad_length_below_2(self):
        start = header(2, 1, palette=3) + palette(3)
        self.check("bad-length", start + record(20, mode(run=1, predictor=NONE), b"", length=1))
        self.check("bad-length", start + record(20, mode(run=1, predictor=NONE), b"", length=0))

    def test_bad_length_above_n_plus_1(self):
        start = header(2, 1, palette=3) + palette(3)
        self.check("bad-length", start + record(20, mode(k=0, predictor=NONE), bits("110 0") + bytes(2)))
        self.check("bad-length", start + record(20, STORED, bytes([2, 0, 0])))
        self.check("bad-length", start + record(20, STORED, bytes([2, 0]), length=65535))

    def test_bad_stored_length(self):
        start = header(2, 1, palette=3) + palette(3)
        self.check("bad-stored-length", start + record(20, STORED, bytes([2])))
        self.check("bad-stored-length", start + record(20, STORED, bytes([2, 0]), length=2))

    def test_out_of_bits_in_plain_mode(self):
        # Three codes are needed. 1101 00 and then the data ends in the middle of the third.
        self.check("out-of-bits", header(1, 1) + record(20, mode(k=1, predictor=NONE), bits("1101 00 10")))
        self.check("out-of-bits", header(1, 1) + record(20, mode(k=0, predictor=NONE), bits("0 0 111111")))
        self.check("out-of-bits", header(1, 1) + record(20, mode(k=0, predictor=NONE), bits("0 0 11111111 1111")))

    def test_out_of_bits_in_a_gamma_code_cut_off_by_the_end_of_the_data(self):
        # Seven zero-bits and a one-bit promise seven more bits, and the data ends. Whatever
        # those bits were, the run would pass the three codes of the buffer.
        self.check("out-of-bits", header(1, 1) + record(20, mode(run=1, predictor=NONE), bits("0000000 1")))
        self.check("out-of-bits", header(1, 1) + record(20, mode(run=1, predictor=NONE), bits("00000000")))

    def test_out_of_bits_after_a_gamma_code(self):
        # Gamma 3 = 011 skips two codes; the Rice(7) code of the third has no room.
        self.check("out-of-bits", header(1, 1) + record(20, mode(k=7, run=1, predictor=NONE), bits("011 10")))

    def test_run_past_end(self):
        # Three codes. Gamma 5 = 00101 asks for four zero codes.
        self.check("run-past-end", header(1, 1) + record(20, mode(run=1, predictor=NONE), bits("00101")))
        # Gamma 1 and Rice 0 set the first code; Gamma 4 = 00100 then asks for three more.
        self.check("run-past-end", header(1, 1) + record(20, mode(run=1, predictor=NONE), bits("1 0 00100")))

    def test_a_run_that_ends_exactly_at_n_is_accepted(self):
        self.check(None, header(1, 1) + record(20, mode(run=1, predictor=NONE), bits("00100")))
        self.check(None, header(1, 1) + record(20, mode(run=1, predictor=NONE), bits("1 0 011")))

    def test_bad_code_in_plain_mode(self):
        # 2 x 1 without a palette: six codes. With k = 6, three one-bits, a zero-bit and
        # 111111 give (3 << 6) + 63 = 255; four one-bits, a zero-bit and 000000 give 256.
        zeros = "  0 000000" * 5
        self.check(None, header(2, 1) + record(20, mode(k=6, predictor=NONE), bits("1110 111111" + zeros)))
        self.check("bad-code", header(2, 1) + record(20, mode(k=6, predictor=NONE), bits("11110 000000" + zeros)))
        # 3 x 1: nine codes. Seven one-bits, a zero-bit and 111111 give (7 << 6) + 63 = 511.
        zeros = "  0 000000" * 8
        self.check("bad-code", header(3, 1) + record(20, mode(k=6, predictor=NONE), bits("11111110 111111" + zeros)))

    def test_bad_code_in_run_mode(self):
        # Gamma 1, then Rice(0) of 255 in the long form: the code would be 256.
        self.check(None, header(1, 1) + record(20, mode(run=1, predictor=NONE), bits("1 11111111 11111110  011")))
        self.check("bad-code", header(1, 1) + record(20, mode(run=1, predictor=NONE), bits("1 11111111 11111111  011")))
        # Gamma 1, then Rice(7) with two one-bits: (2 << 7) + 0 = 256, so the code would be 257.
        self.check("bad-code", header(1, 1) + record(20, mode(k=7, run=1, predictor=NONE), bits("1 110 0000000  011")))

    def test_too_much_padding(self):
        valid = bits("1101 00 100")
        self.check(None, header(1, 1) + record(20, mode(k=1, predictor=NONE), valid))
        self.check("too-much-padding", header(1, 1) + record(20, mode(k=1, predictor=NONE), valid + b"\x00"))
        # Three codes of one bit each leave five bits; one more byte makes thirteen.
        self.check(None, header(1, 1) + record(20, mode(k=0, predictor=NONE), bits("0 0 0")))
        self.check("too-much-padding", header(1, 1) + record(20, mode(k=0, predictor=NONE), bits("0 0 0") + b"\x00"))

    def test_too_much_padding_in_run_mode(self):
        self.check("too-much-padding", header(1, 1) + record(20, mode(run=1, predictor=NONE), bits("00100") + b"\x00"))

    def test_bad_palette_index_in_a_stored_frame(self):
        self.check("bad-palette-index", header(2, 1, palette=3) + palette(3) + record(20, STORED, bytes([3, 0])))
        self.check("bad-palette-index", header(2, 1, palette=3) + palette(3) + record(20, STORED, bytes([0, 255])))

    def test_bad_palette_index_in_a_coded_frame(self):
        # Two codes, k = 0, predictor 3: code 6 is the index 3, code 4 the index 2.
        start = header(2, 1, palette=3) + palette(3)
        self.check(None, start + record(20, mode(k=0, predictor=NONE), bits("11110 0")))
        self.check("bad-palette-index", start + record(20, mode(k=0, predictor=NONE), bits("1111110 0")))

    def test_bad_palette_index_reached_through_a_predictor(self):
        # The first record stores 2 0; the second adds +1 to the first index.
        start = header(2, 1, palette=3, frames=2) + palette(3) + record(20, STORED, bytes([2, 0]))
        self.check(None, start + record(20, mode(k=0, predictor=0), bits("0 110")))
        self.check("bad-palette-index", start + record(20, mode(k=0, predictor=0), bits("110 0")))

    def test_trailing_bytes_in_an_uncompressed_body(self):
        self.check("trailing-bytes", self.VALID + b"\x00")
        self.check("trailing-bytes", self.VALID + self.VALID[16 + 9:])

    def test_trailing_bytes_in_a_compressed_body(self):
        compressed = header(2, 1, palette=3, flags=1)
        self.check("trailing-bytes", compressed + stored_block(self.VALID[16:] + b"\x00"))

    def test_trailing_bytes_after_the_deflate_stream(self):
        compressed = header(2, 1, palette=3, flags=1)
        self.check("trailing-bytes", compressed + stored_block(self.VALID[16:]) + b"\x00")


class TheFirstDefectIsReported(unittest.TestCase):
    def check(self, expected, data):
        self.assertEqual(reason_of(data), expected)

    def test_header_fields_in_the_order_of_their_offsets(self):
        fields = [
            ("bad-magic", {"magic": b"XXXX"}),
            ("bad-version", {"version": 9}),
            ("reserved-bits", {"flags": 0x82}),
            ("zero-size", {"width": 0}),
            ("zero-size", {"height": 0}),
            ("bad-palette-size", {"palette": 300}),
            ("no-frames", {"frames": 0}),
        ]
        for first in range(len(fields)):
            named = {"width": 2, "height": 1}
            for _, change in fields[first:]:
                named.update(change)
            with self.subTest(first=fields[first][0]):
                self.check(fields[first][0], header(**named))

    def test_canvas_too_large_before_no_frames(self):
        self.check("canvas-too-large", header(65535, 1, palette=1, frames=0))

    def test_a_short_file_is_truncated_whatever_its_first_bytes_are(self):
        self.check("truncated", b"XXXX\x09")

    def test_within_a_record_duration_then_length_then_mode_then_data(self):
        start = header(2, 1, palette=3) + palette(3)
        self.check("zero-duration", start + record(0, 0x80, b"", length=1))
        self.check("bad-length", start + record(20, 0x80, b"", length=1))
        self.check("reserved-bits", start + record(20, 0x41, bytes([9])))
        self.check("bad-stored-length", start + record(20, STORED, bytes([9])))
        self.check("truncated", start + record(20, STORED, bytes([9]), length=3))

    def test_the_bits_are_checked_before_the_palette_indexes(self):
        # Code 6 gives the index 3, which the palette does not have, and a byte is left over.
        start = header(2, 1, palette=3) + palette(3)
        self.check("too-much-padding", start + record(20, mode(k=0, predictor=NONE), bits("1111110 0") + b"\x00"))

    def test_a_bad_code_before_the_end_of_the_bits(self):
        # The first code is 256 and the data ends inside the second code.
        self.check("bad-code", header(1, 1) + record(20, mode(k=6, predictor=NONE), bits("11110 000000  0 000")))

    def test_an_earlier_record_before_a_later_one(self):
        start = header(2, 1, palette=3, frames=2) + palette(3)
        self.check("bad-palette-index", start + record(20, STORED, bytes([3, 0])) + record(0, STORED, bytes([0, 0])))
        self.check("zero-duration", start + record(20, STORED, bytes([2, 0])) + record(0, STORED, bytes([3, 0])))


if __name__ == "__main__":
    unittest.main()

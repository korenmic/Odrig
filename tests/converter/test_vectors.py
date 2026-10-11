import collections
import struct
import unittest
import zlib

from odrig import jsonframes, odrg

from . import build_vectors, support

VALID = support.ROOT / "tests" / "vectors" / "valid"

Parsed = collections.namedtuple("Parsed", "width height palette_size compressed n records first_block")
Rice = collections.namedtuple("Rice", "value long_form")
Gamma = collections.namedtuple("Gamma", "value")


def parse(data):
    """The parts of a valid ODRG file, read here without the tool.

    `records` holds `(duration, mode, data)` for each frame record, and `first_block` the
    type of the first DEFLATE block of a compressed body.
    """
    _, _, flags, width, height, palette_size, count = struct.unpack_from("<4sBBHHHI", data)
    body = data[16:]
    first_block = None
    if flags & 1:
        first_block = (body[0] >> 1) & 3
        body = zlib.decompress(body, -15)
    at = 3 * palette_size
    records = []
    for _ in range(count):
        duration, length, mode = struct.unpack_from("<HHB", body, at)
        records.append((duration, mode, body[at + 5:at + 4 + length]))
        at += 4 + length
    n = width * height * (1 if palette_size else 3)
    return Parsed(width, height, palette_size, bool(flags & 1), n, records, first_block)


def spelled(mode, data, n):
    """The Rice and Gamma codes that the bits of a coded frame record spell, in order."""
    bits = "".join(f"{byte:08b}" for byte in data)
    k = mode & 7
    at = 0
    codes = []

    def rice():
        nonlocal at
        ones = 0
        while ones < 8 and bits[at] == "1":
            ones += 1
            at += 1
        if ones == 8:
            codes.append(Rice(int(bits[at:at + 8], 2), True))
            at += 8
        else:
            low = int(bits[at + 1:at + 1 + k], 2) if k else 0
            codes.append(Rice((ones << k) + low, False))
            at += 1 + k

    def gamma():
        nonlocal at
        zeros = 0
        while bits[at] == "0":
            zeros += 1
            at += 1
        codes.append(Gamma(int(bits[at:at + zeros + 1], 2)))
        at += zeros + 1
        return codes[-1].value

    if mode & 8:
        i = 0
        while i < n:
            i += gamma() - 1
            if i == n:
                break
            rice()
            i += 1
    else:
        for _ in range(n):
            rice()
    return codes


class ValidVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = sorted(path.name for path in VALID.iterdir())
        cls.files = {path.name[:-5]: path.read_bytes() for path in VALID.glob("*.odrg")}
        cls.parsed = {name: parse(data) for name, data in cls.files.items()}
        cls.coded = [
            (mode, spelled(mode, data, parsed.n))
            for parsed in cls.parsed.values()
            for _, mode, data in parsed.records
            if mode != 0x40
        ]
        cls.in_plain_mode = [(mode, codes) for mode, codes in cls.coded if not mode & 8]
        cls.in_run_mode = [(mode, codes) for mode, codes in cls.coded if mode & 8]

    def test_the_folder_holds_pairs_of_odrg_and_json_files(self):
        self.assertTrue(self.files)
        for name in self.names:
            stem, _, ending = name.rpartition(".")
            self.assertIn(ending, ("odrg", "json"), name)
            self.assertIn(f"{stem}.odrg", self.names)
            self.assertIn(f"{stem}.json", self.names)

    def test_every_vector_decodes_to_its_expected_frames_record_by_record(self):
        for name, data in self.files.items():
            with self.subTest(name=name):
                expected = jsonframes.read(VALID / f"{name}.json")
                decoded = odrg.decode(data)
                self.assertEqual((decoded.width, decoded.height), (expected.width, expected.height))
                self.assertEqual(len(decoded.records), len(expected.frames))
                self.assertEqual(decoded.records, expected.frames)

    def test_no_odrg_file_is_above_4096_bytes(self):
        for name, data in self.files.items():
            self.assertLessEqual(len(data), 4096, name)

    # The coverage of the set, read from the headers, the mode bytes and the codes of the files.

    def test_files_with_a_palette(self):
        self.assertTrue(any(parsed.palette_size for parsed in self.parsed.values()), "no vector has a palette")

    def test_files_without_a_palette(self):
        self.assertTrue(
            any(not parsed.palette_size for parsed in self.parsed.values()), "no vector is without a palette"
        )

    def test_compressed_bodies(self):
        self.assertTrue(any(parsed.compressed for parsed in self.parsed.values()), "no vector is compressed")

    def test_uncompressed_bodies(self):
        self.assertTrue(
            any(not parsed.compressed for parsed in self.parsed.values()), "no vector is uncompressed"
        )

    def test_every_predictor(self):
        self.assertEqual({(mode >> 4) & 3 for mode, _ in self.coded}, {0, 1, 2, 3}, "a predictor is not used")

    def test_plain_mode_and_run_mode(self):
        self.assertTrue(self.in_plain_mode and self.in_run_mode, "plain mode or run mode is not used")

    def test_every_k_in_plain_mode(self):
        self.assertEqual({mode & 7 for mode, _ in self.in_plain_mode}, set(range(8)), "a k is not used in plain mode")

    def test_every_k_in_run_mode(self):
        self.assertEqual({mode & 7 for mode, _ in self.in_run_mode}, set(range(8)), "a k is not used in run mode")

    def test_every_combination_of_predictor_mode_and_k_with_and_without_a_palette(self):
        for palette in (False, True):
            modes = {
                mode
                for parsed in self.parsed.values()
                if bool(parsed.palette_size) == palette
                for _, mode, _ in parsed.records
            }
            self.assertTrue(set(range(64)) <= modes, f"a combination is not used (palette: {palette})")

    def test_stored_frames(self):
        self.assertTrue(
            any(mode == 0x40 for parsed in self.parsed.values() for _, mode, _ in parsed.records),
            "no vector has a stored frame",
        )

    def test_the_escape_code(self):
        self.assertTrue(
            any(isinstance(code, Rice) and code.long_form for _, codes in self.coded for code in codes),
            "no vector uses the escape code",
        )

    def test_the_escape_code_in_each_mode(self):
        for name, records in (("plain", self.in_plain_mode), ("run", self.in_run_mode)):
            self.assertTrue(
                any(isinstance(code, Rice) and code.long_form for _, codes in records for code in codes),
                f"no vector uses the escape code in {name} mode",
            )

    def test_a_zero_run_that_reaches_the_end_of_the_buffer(self):
        self.assertTrue(
            any(isinstance(codes[-1], Gamma) and codes[-1].value > 1 for _, codes in self.in_run_mode),
            "no run-mode record ends in a zero run",
        )

    def test_a_non_zero_last_code_in_run_mode(self):
        self.assertTrue(
            any(isinstance(codes[-1], Rice) for _, codes in self.in_run_mode),
            "no run-mode record ends in a code that is not zero",
        )

    def test_a_zero_run_longer_than_255_codes(self):
        self.assertTrue(
            any(isinstance(code, Gamma) and code.value > 256 for _, codes in self.in_run_mode for code in codes),
            "no vector has a zero run longer than 255 codes",
        )

    def test_the_duration_65535(self):
        self.assertTrue(
            any(duration == 65535 for parsed in self.parsed.values() for duration, _, _ in parsed.records),
            "no record lasts 65,535 ms",
        )

    def test_a_palette_of_256_colours(self):
        self.assertTrue(
            any(parsed.palette_size == 256 for parsed in self.parsed.values()), "no vector has a palette of 256"
        )

    def test_a_palette_of_1_colour(self):
        self.assertTrue(
            any(parsed.palette_size == 1 for parsed in self.parsed.values()), "no vector has a palette of 1"
        )

    def test_a_canvas_one_pixel_wide(self):
        self.assertTrue(
            any(parsed.width == 1 and parsed.height > 1 for parsed in self.parsed.values()),
            "no vector has a canvas one pixel wide",
        )

    def test_a_canvas_one_pixel_high(self):
        self.assertTrue(
            any(parsed.height == 1 and parsed.width > 1 for parsed in self.parsed.values()),
            "no vector has a canvas one pixel high",
        )

    def test_a_compressed_body_made_of_stored_blocks(self):
        self.assertIn(0, {parsed.first_block for parsed in self.parsed.values()}, "no body of stored blocks")

    def test_a_compressed_body_made_of_fixed_code_blocks(self):
        self.assertIn(1, {parsed.first_block for parsed in self.parsed.values()}, "no body of fixed-code blocks")

    def test_a_compressed_body_made_of_dynamic_code_blocks(self):
        self.assertIn(2, {parsed.first_block for parsed in self.parsed.values()}, "no body of dynamic-code blocks")

    # The set is the output of the builder.

    def test_the_folder_holds_exactly_the_names_the_builder_produces(self):
        self.assertEqual(self.names, sorted(build_vectors.valid_files()))

    def test_every_file_made_without_zlib_is_byte_identical_to_the_builders_output(self):
        compared = 0
        for case in build_vectors.valid_cases():
            with self.subTest(name=case.name):
                self.assertEqual((VALID / f"{case.name}.json").read_bytes(), case.json)
                if not case.zlib:
                    self.assertEqual((VALID / f"{case.name}.odrg").read_bytes(), case.odrg)
                    compared += 1
        self.assertGreater(compared, 0)

    def test_the_expected_frames_are_not_merged(self):
        merged = [
            name for name in self.files
            if len(jsonframes.merged(jsonframes.read(VALID / f"{name}.json").frames)) < len(self.parsed[name].records)
        ]
        self.assertTrue(merged, "no vector has two records in a row with the same picture")


if __name__ == "__main__":
    unittest.main()

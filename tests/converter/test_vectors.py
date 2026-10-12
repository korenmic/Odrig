import collections
import re
import struct
import types
import unittest
import zlib

from odrig import errors, jsonframes, odrg

from . import build_vectors, support

VALID = support.ROOT / "tests" / "vectors" / "valid"
INVALID = support.ROOT / "tests" / "vectors" / "invalid"

# The reasons for which a reader rejects an ODRG file.
READER_REASONS = (
    "truncated",
    "bad-magic",
    "bad-version",
    "reserved-bits",
    "zero-size",
    "bad-palette-size",
    "canvas-too-large",
    "no-frames",
    "bad-deflate",
    "zero-duration",
    "bad-length",
    "bad-stored-length",
    "out-of-bits",
    "run-past-end",
    "bad-code",
    "too-much-padding",
    "bad-palette-index",
    "trailing-bytes",
)

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


def anatomy(data):
    """How far a file can be followed from front to back, without judging what it holds.

    `stream` says what became of a compressed body: "invalid", "cut", "whole", or
    "followed" when bytes come after it. `ends` says where the body stops short: in the
    "palette", in a "record start", in "record data", or at a "bad length". `records` holds
    `(duration, L, mode, data)` for the records reached, and `extra` counts the bytes of the
    body after the last one.
    """
    facts = types.SimpleNamespace(
        header=len(data) >= 16, flags=0, palette_size=0, n=0, stream=None, ends=None, records=[], extra=0
    )
    if not facts.header:
        return facts
    _, _, facts.flags, width, height, facts.palette_size, count = struct.unpack_from("<4sBBHHHI", data)
    facts.n = width * height * (1 if facts.palette_size else 3)
    body = data[16:]
    if facts.flags & 1:
        inflater = zlib.decompressobj(wbits=-15)
        try:
            body = inflater.decompress(body)
        except zlib.error:
            facts.stream = "invalid"
            return facts
        if not inflater.eof:
            facts.stream = "cut"
            return facts
        facts.stream = "followed" if inflater.unused_data else "whole"
    at = 3 * facts.palette_size
    if at > len(body):
        facts.ends = "palette"
        return facts
    for _ in range(count):
        if at + 5 > len(body):
            facts.ends = "record start"
            return facts
        duration, length, mode = struct.unpack_from("<HHB", body, at)
        chunk = body[at + 5:at + 4 + length]
        facts.records.append((duration, length, mode, chunk))
        if length < 2 or length > facts.n + 1:
            facts.ends = "bad length"
            return facts
        if len(chunk) < length - 1:
            facts.ends = "record data"
            return facts
        at += 4 + length
    facts.extra = len(body) - at
    return facts


def reported(data):
    """The reason the reference decoder rejects the file with, or `None`."""
    try:
        odrg.decode(data)
    except errors.Rejection as rejection:
        return rejection.reason
    return None


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


class InvalidVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = {path.name: path.read_bytes() for path in INVALID.iterdir()}
        cls.facts = [(name.split(".")[0], anatomy(data)) for name, data in cls.files.items()]

    def some(self, reason, holds, message):
        self.assertTrue(any(holds(facts) for named, facts in self.facts if named == reason), message)

    def test_every_file_is_named_for_a_reason_a_reader_rejects_with(self):
        self.assertTrue(self.files)
        for name in self.files:
            self.assertRegex(name, r"\A[a-z0-9-]+(\.[a-z0-9-]+)?\.odrg\Z")
            self.assertIn(name.split(".")[0], READER_REASONS, name)

    def test_every_file_is_rejected_with_the_reason_in_its_name(self):
        for name, data in self.files.items():
            expected = name.split(".")[0]
            got = reported(data)
            self.assertEqual(got, expected, f"{name}: expected {expected}, reported {got}")

    def test_every_reason_has_at_least_one_file(self):
        named = {name.split(".")[0] for name in self.files}
        for reason in READER_REASONS:
            self.assertIn(reason, named, f"no invalid vector for {reason}")

    def test_the_reasons_are_those_of_the_odrg_table_of_the_reasons_document(self):
        text = (support.ROOT / "docs" / "reasons.md").read_text(encoding="utf-8")
        section = text.split("## ODRG files")[1].split("\n## ")[0]
        self.assertEqual(tuple(re.findall(r"(?m)^\| `([a-z0-9-]+)` \|", section)), READER_REASONS)

    def test_no_file_is_above_4096_bytes(self):
        for name, data in self.files.items():
            self.assertLessEqual(len(data), 4096, name)

    # The separate cases the set must hold, found by looking into the files.

    def test_a_reserved_flag_bit(self):
        self.some("reserved-bits", lambda facts: facts.flags & 0xFE, "no vector with a reserved flag bit")

    def test_mode_bit_7(self):
        self.some(
            "reserved-bits",
            lambda facts: any(mode & 0x80 for _, _, mode, _ in facts.records),
            "no vector with bit 7 of a mode byte",
        )

    def test_a_stored_mode_byte_other_than_0x40(self):
        self.some(
            "reserved-bits",
            lambda facts: any(mode & 0xC0 == 0x40 and mode != 0x40 for _, _, mode, _ in facts.records),
            "no vector with a stored mode byte other than 0x40",
        )

    def test_a_file_cut_off_in_the_header(self):
        self.some("truncated", lambda facts: not facts.header, "no vector cut off in the header")

    def test_a_file_cut_off_in_the_palette(self):
        self.some(
            "truncated",
            lambda facts: facts.stream is None and facts.ends == "palette",
            "no vector cut off in the palette",
        )

    def test_a_file_cut_off_in_the_first_five_bytes_of_a_record(self):
        self.some(
            "truncated",
            lambda facts: facts.stream is None and facts.ends == "record start",
            "no vector cut off in the first five bytes of a record",
        )

    def test_a_file_cut_off_in_the_data_of_a_record(self):
        self.some(
            "truncated",
            lambda facts: facts.stream is None and facts.ends == "record data",
            "no vector cut off in the data of a record",
        )

    def test_a_deflate_stream_cut_off(self):
        self.some("truncated", lambda facts: facts.stream == "cut", "no vector with a DEFLATE stream cut off")

    def test_a_complete_deflate_stream_whose_output_ends_inside_a_record(self):
        self.some(
            "truncated",
            lambda facts: facts.stream == "whole" and facts.ends in ("record start", "record data"),
            "no vector with a complete DEFLATE stream whose output ends inside a record",
        )

    def test_a_length_below_2(self):
        self.some(
            "bad-length",
            lambda facts: facts.ends == "bad length" and facts.records[-1][1] < 2,
            "no vector with L below 2",
        )

    def test_a_length_above_n_plus_1(self):
        self.some(
            "bad-length",
            lambda facts: facts.ends == "bad length" and facts.records[-1][1] > facts.n + 1,
            "no vector with L above N + 1",
        )

    def largest(self, facts, run):
        """The largest code that the records of one mode spell."""
        return max(
            (
                code.value + (1 if run else 0)
                for _, _, mode, data in facts.records
                if mode & 0xC0 == 0 and bool(mode & 8) == run
                for code in spelled(mode, data, facts.n)
                if isinstance(code, Rice)
            ),
            default=0,
        )

    def test_a_code_above_255_in_plain_mode(self):
        self.some("bad-code", lambda facts: self.largest(facts, False) > 255, "no vector with a code above 255 in plain mode")

    def test_a_code_above_255_in_run_mode(self):
        self.some("bad-code", lambda facts: self.largest(facts, True) > 255, "no vector with a code above 255 in run mode")

    def stored_index_too_large(self, facts):
        return any(mode == 0x40 and max(data) >= facts.palette_size for _, _, mode, data in facts.records)

    def test_a_bad_palette_index_in_a_stored_frame(self):
        self.some("bad-palette-index", self.stored_index_too_large, "no vector with a bad palette index in a stored frame")

    def test_a_bad_palette_index_in_a_coded_frame(self):
        self.some(
            "bad-palette-index",
            lambda facts: not self.stored_index_too_large(facts),
            "no vector with a bad palette index in a coded frame",
        )

    def test_bytes_after_the_last_record_in_an_uncompressed_body(self):
        self.some(
            "trailing-bytes",
            lambda facts: facts.stream is None and facts.extra > 0,
            "no vector with bytes after the last record in an uncompressed body",
        )

    def test_bytes_after_the_last_record_in_a_compressed_body(self):
        self.some(
            "trailing-bytes",
            lambda facts: facts.stream == "whole" and facts.extra > 0,
            "no vector with bytes after the last record in a compressed body",
        )

    def test_bytes_in_the_file_after_the_deflate_stream(self):
        self.some(
            "trailing-bytes",
            lambda facts: facts.stream == "followed" and facts.extra == 0,
            "no vector with bytes after the DEFLATE stream",
        )

    # The set is the output of the builder, and every file has one defect.

    def test_before_its_one_change_every_file_decodes_and_after_it_is_rejected(self):
        for case in build_vectors.invalid_cases():
            with self.subTest(name=case.name):
                self.assertIsNone(reported(case.valid))
                self.assertEqual(reported(case.odrg), case.reason)
                self.assertEqual(case.reason, case.name.split(".")[0])
                self.assertNotEqual(case.odrg, case.valid)

    def test_the_folder_holds_exactly_the_names_the_builder_produces(self):
        self.assertEqual(sorted(self.files), sorted(build_vectors.invalid_files()))

    def test_every_file_made_without_zlib_is_byte_identical_to_the_builders_output(self):
        compared = 0
        for case in build_vectors.invalid_cases():
            if not case.zlib:
                with self.subTest(name=case.name):
                    self.assertEqual(self.files[f"{case.name}.odrg"], case.odrg)
                    compared += 1
        self.assertGreater(compared, 0)


class TheBuilder(unittest.TestCase):
    """The block of the fixed codes that the builder writes itself, where the zlib of this
    Python does not make one when it is told to."""

    BODIES = (b"", b"a", bytes(range(256)) * 9, b"hello hello hello", bytes([143, 144, 255, 0]) * 50)

    def test_the_block_it_writes_is_one_last_block_of_the_fixed_codes(self):
        for body in self.BODIES:
            data = build_vectors.fixed_block(body)
            self.assertEqual(data[0] & 7, 0b011, body[:8])
            self.assertEqual((data[0] & 1, (data[0] >> 1) & 3), (1, build_vectors.FIXED_BLOCKS))

    def test_zlib_inflates_the_block_to_what_went_in_and_nothing_is_left_over(self):
        for body in self.BODIES:
            inflater = zlib.decompressobj(wbits=-15)
            self.assertEqual(inflater.decompress(build_vectors.fixed_block(body)), body, body[:8])
            self.assertTrue(inflater.eof)
            self.assertEqual(inflater.unused_data, b"")

    def test_what_zlib_made_is_kept_when_it_is_such_a_block_and_replaced_when_it_is_not(self):
        body = bytes(range(256)) * 4
        own = build_vectors.fixed_block(body)
        self.assertEqual(build_vectors.fixed_codes(lambda given: own)(body), own)
        for other in (zlib.compress(body, 0, -15), b"\x05" + own[1:]):
            self.assertNotEqual(other[0] & 7, 0b011)
            self.assertEqual(build_vectors.fixed_codes(lambda given: other)(body), own)

    def test_the_vector_named_for_the_fixed_codes_is_such_a_block_with_any_zlib(self):
        made = {case.name: case for case in build_vectors.valid_cases()}
        self.assertEqual(build_vectors.first_block(made["deflate-fixed"].odrg), (True, build_vectors.FIXED_BLOCKS))
        self.assertEqual(odrg.decode(made["deflate-fixed"].odrg), odrg.decode((VALID / "deflate-fixed.odrg").read_bytes()))


if __name__ == "__main__":
    unittest.main()

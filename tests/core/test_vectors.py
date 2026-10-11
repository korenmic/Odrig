import re
import unittest

from odrig import jsonframes

from . import support

VALID = support.ROOT / "tests" / "vectors" / "valid"
INVALID = support.ROOT / "tests" / "vectors" / "invalid"


def reasons_of_an_odrg_file():
    """The reasons that docs/reasons.md lists for an ODRG file."""
    text = (support.ROOT / "docs" / "reasons.md").read_text(encoding="utf-8")
    section = text.split("\n## ODRG files\n")[1].split("\n## ")[0]
    return set(re.findall(r"(?m)^\| `([a-z0-9-]+)` \|", section))


class ValidVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = sorted(VALID.glob("*.odrg"))
        cls.decoded = support.decode_each([path.read_bytes() for path in cls.paths])

    def test_the_folder_holds_vectors_with_their_expected_frames(self):
        self.assertGreaterEqual(len(self.paths), 20)
        names = sorted(path.name for path in VALID.iterdir())
        self.assertEqual(names, sorted(name for path in self.paths for name in (path.name, path.stem + ".json")))

    def test_every_one_decodes_to_its_expected_frames_record_by_record(self):
        for path, decoded in zip(self.paths, self.decoded):
            with self.subTest(vector=path.name):
                expected = jsonframes.loads(path.with_suffix(".json").read_bytes())
                data = path.read_bytes()
                self.assertIsNone(decoded.reason)
                width, height, colours, frames, compressed = decoded.header
                self.assertEqual((width, height), (expected.width, expected.height))
                self.assertEqual(colours, int.from_bytes(data[10:12], "little"))
                self.assertEqual(frames, len(expected.frames))
                self.assertEqual(compressed, bool(data[5] & 1))
                self.assertEqual(len(decoded.records), len(expected.frames))
                for number, (record, frame) in enumerate(zip(decoded.records, expected.frames), 1):
                    self.assertEqual(record, frame, f"record {number}")

    def test_they_decode_the_same_when_read_from_their_folder(self):
        for path, decoded in list(zip(self.paths, self.decoded))[::5]:
            self.assertEqual(support.decode_file(path), decoded, path.name)

    def test_they_hold_palette_files_and_compressed_files(self):
        headers = [decoded.header for decoded in self.decoded]
        self.assertTrue(any(colours == 0 for _, _, colours, _, _ in headers))
        self.assertTrue(any(colours == 256 for _, _, colours, _, _ in headers))
        self.assertTrue(any(compressed for *_, compressed in headers))
        self.assertTrue(any(not compressed for *_, compressed in headers))


class InvalidVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = sorted(INVALID.iterdir())
        cls.decoded = support.decode_each([path.read_bytes() for path in cls.paths])

    def test_every_one_is_rejected_with_the_reason_in_its_name(self):
        self.assertGreaterEqual(len(self.paths), 30)
        for path, decoded in zip(self.paths, self.decoded):
            with self.subTest(vector=path.name):
                self.assertEqual(decoded.reason, path.name.split(".")[0])

    def test_they_are_rejected_the_same_when_read_from_their_folder(self):
        for path, decoded in list(zip(self.paths, self.decoded))[::5]:
            self.assertEqual(support.decode_file(path), decoded, path.name)

    def test_they_cover_every_reason_of_an_odrg_file(self):
        listed = reasons_of_an_odrg_file()
        self.assertIn("bad-code", listed)
        self.assertIn("truncated", listed)
        self.assertEqual({path.name.split(".")[0] for path in self.paths}, listed)

    def test_the_core_has_every_reason_of_an_odrg_file(self):
        self.assertLessEqual(reasons_of_an_odrg_file(), set(support.host_lines("reasons")))

    def test_a_file_that_is_not_there_is_not_decoded(self):
        decoded = support.decode_file(INVALID / "no-such-file.odrg")
        self.assertEqual(decoded, support.Decoded(None, (), "file-missing"))


if __name__ == "__main__":
    unittest.main()

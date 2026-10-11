import tempfile
import unittest
from pathlib import Path

from odrig import jsonframes, odrg

from . import support

RED, GREEN, BLUE, BLACK = b"\xff\x00\x00", b"\x00\xff\x00", b"\x00\x00\xff", b"\x00\x00\x00"

# A 3 x 2 animation of 500 + 70,000 + 20 ms with four colours: red, blue, green and black.
ANIMATION = jsonframes.Animation(
    3,
    2,
    (
        (500, RED + BLACK + BLACK + BLACK + BLACK + BLUE),
        (70000, BLACK + BLACK + BLACK + BLACK + GREEN + BLACK),
        (20, RED + BLACK + BLACK + BLACK + BLACK + BLUE),
    ),
)


class Check(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def file(self, name, data):
        path = self.folder / name
        path.write_bytes(data)
        return path

    def test_a_json_frames_file(self):
        data = jsonframes.dumps(ANIMATION)
        result = support.run("check", self.file("clip.json", data))
        expected = (
            "format: json-frames\n"
            "canvas: 3x2\n"
            "frames: 3\n"
            "duration_ms: 70520\n"
            "colours: 4\n"
            f"file_bytes: {len(data)}\n"
        )
        self.assertEqual(result, support.Result(0, expected, ""))

    def test_frames_of_a_json_frames_file_are_counted_as_the_file_lists_them(self):
        data = (
            b'{"version": 1, "width": 1, "height": 1, "frames": ['
            b'{"ms": 20, "pixels": [5]}, {"ms": 20, "pixels": [5]}, {"ms": 20, "pixels": [5]}]}'
        )
        result = support.run("check", self.file("clip.json", data))
        self.assertEqual(
            result.out,
            f"format: json-frames\ncanvas: 1x1\nframes: 3\nduration_ms: 60\ncolours: 1\nfile_bytes: {len(data)}\n",
        )

    def test_a_compressed_odrg_file_with_a_palette(self):
        data = odrg.encode(ANIMATION)
        result = support.run("check", self.file("clip.odrg", data))
        # The frame of 70,000 ms is two frame records, so the file has four.
        expected = (
            "format: odrg\n"
            "canvas: 3x2\n"
            "frames: 4\n"
            "duration_ms: 70520\n"
            "colours: 4\n"
            f"file_bytes: {len(data)}\n"
            "palette: 4\n"
            "compressed: yes\n"
        )
        self.assertEqual(result, support.Result(0, expected, ""))

    def test_an_uncompressed_odrg_file_without_a_palette(self):
        records = [odrg.stored_record(RED + BLACK, 20), odrg.stored_record(RED + BLUE, 40)]
        data = odrg.container(2, 1, None, records)
        result = support.run("check", self.file("clip.odrg", data))
        expected = (
            "format: odrg\n"
            "canvas: 2x1\n"
            "frames: 2\n"
            "duration_ms: 60\n"
            "colours: 3\n"
            "file_bytes: 38\n"
            "palette: 0\n"
            "compressed: no\n"
        )
        self.assertEqual(result, support.Result(0, expected, ""))

    def test_colours_are_those_that_appear_not_the_size_of_the_palette(self):
        data = odrg.container(2, 1, [RED, GREEN, BLUE], [odrg.stored_record(bytes([2, 0]), 20)])
        result = support.run("check", self.file("clip.odrg", data))
        self.assertIn("colours: 2\n", result.out)
        self.assertIn("palette: 3\n", result.out)

    def test_it_runs_as_a_module(self):
        result = support.run_module("check", self.file("clip.odrg", odrg.encode(ANIMATION)))
        self.assertEqual(result.status, 0)
        self.assertTrue(result.out.startswith("format: odrg\ncanvas: 3x2\n"), result.out)
        self.assertEqual(result.err, "")

    def test_the_ending_of_the_name_may_be_in_any_letter_case(self):
        self.assertTrue(support.run("check", self.file("CLIP.JSON", jsonframes.dumps(ANIMATION))).out.startswith("format: json-frames\n"))
        self.assertTrue(support.run("check", self.file("Clip.Odrg", odrg.encode(ANIMATION))).out.startswith("format: odrg\n"))

    def test_format_overrides_the_file_name(self):
        packed = self.file("packed.json", odrg.encode(ANIMATION))
        source = self.file("source.odrg", jsonframes.dumps(ANIMATION))
        self.assertTrue(support.run("check", packed, "--format", "odrg").out.startswith("format: odrg\n"))
        self.assertTrue(support.run("check", "--format", "json", source).out.startswith("format: json-frames\n"))
        self.assertTrue(support.run("check", packed).err.startswith("error: bad-json: "))
        self.assertTrue(support.run("check", source).err.startswith("error: bad-magic: "))

    def test_format_tells_the_format_of_a_name_without_a_known_ending(self):
        path = self.file("clip.bin", odrg.encode(ANIMATION))
        self.assertTrue(support.run("check", path, "--format", "odrg").out.startswith("format: odrg\n"))

    def test_status_2_when_the_format_is_not_known(self):
        for name in ("clip.bin", "clip", "clip.json.bak", "odrg"):
            with self.subTest(name=name):
                result = support.run("check", self.file(name, odrg.encode(ANIMATION)))
                self.assertEqual(result.status, 2)
                self.assertEqual(result.out, "")
                self.assertIn("usage:", result.err)

    def test_status_2_for_a_format_that_does_not_exist(self):
        result = support.run("check", self.file("clip.json", jsonframes.dumps(ANIMATION)), "--format", "gif")
        self.assertEqual(result.status, 2)
        self.assertEqual(result.out, "")

    def test_a_rejected_json_frames_file_prints_nothing_to_standard_output(self):
        path = self.file("clip.json", jsonframes.dumps(ANIMATION).replace(b'"version": 1', b'"version": 3'))
        result = support.run("check", path)
        self.assertEqual(result.status, 1)
        self.assertEqual(result.out, "")
        self.assertTrue(result.err.startswith(f"error: bad-version: {path}: "), result.err)
        self.assertEqual(result.err.count("\n"), 1)

    def test_a_rejected_odrg_file_prints_nothing_to_standard_output(self):
        path = self.file("clip.odrg", odrg.encode(ANIMATION) + b"\x00")
        result = support.run("check", path)
        self.assertEqual(result.status, 1)
        self.assertEqual(result.out, "")
        self.assertTrue(result.err.startswith(f"error: trailing-bytes: {path}: "), result.err)

    def test_a_file_that_does_not_exist_is_not_found(self):
        result = support.run("check", self.folder / "absent.odrg")
        self.assertEqual(result.status, 1)
        self.assertEqual(result.out, "")
        self.assertTrue(result.err.startswith("error: not-found: "), result.err)

    def test_check_writes_no_file(self):
        self.file("clip.odrg", odrg.encode(ANIMATION))
        support.run("check", self.folder / "clip.odrg")
        self.assertEqual([entry.name for entry in self.folder.iterdir()], ["clip.odrg"])


if __name__ == "__main__":
    unittest.main()

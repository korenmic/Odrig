import re
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from odrig import cli, errors, files

from . import support


def probe(run):
    """A command line with the single subcommand `probe`, which calls `run`."""
    subcommand = cli.Subcommand("probe", "probe", lambda parser: None, run)
    return mock.patch.object(cli, "SUBCOMMANDS", (subcommand,))


class UsageErrors(unittest.TestCase):
    def test_no_subcommand_gives_status_2_and_a_usage_message(self):
        result = support.run()
        self.assertEqual(result.status, 2)
        self.assertIn("usage:", result.err)
        self.assertEqual(result.out, "")

    def test_unknown_subcommand_gives_status_2_and_a_usage_message(self):
        result = support.run("frobnicate")
        self.assertEqual(result.status, 2)
        self.assertIn("usage:", result.err)
        self.assertEqual(result.out, "")

    def test_unknown_option_gives_status_2(self):
        with probe(lambda arguments: None):
            result = support.run("probe", "--no-such-option")
        self.assertEqual(result.status, 2)
        self.assertIn("usage:", result.err)


class StartedAsAModule(unittest.TestCase):
    def test_no_subcommand_exits_with_status_2(self):
        result = support.run_module()
        self.assertEqual(result.status, 2)
        self.assertIn("usage: python -m odrig", result.err)
        self.assertEqual(result.out, "")

    def test_unknown_subcommand_exits_with_status_2(self):
        result = support.run_module("frobnicate")
        self.assertEqual(result.status, 2)
        self.assertIn("usage: python -m odrig", result.err)


class Statuses(unittest.TestCase):
    def test_a_subcommand_that_finishes_gives_status_0(self):
        with probe(lambda arguments: None):
            result = support.run("probe")
        self.assertEqual(result, support.Result(0, "", ""))

    def test_a_rejection_gives_the_error_line_and_status_1(self):
        def reject(arguments):
            raise errors.Rejection(errors.NOT_FOUND, "missing.json: No such file or directory")

        with probe(reject):
            result = support.run("probe")
        self.assertEqual(result.status, 1)
        self.assertEqual(result.err, "error: not-found: missing.json: No such file or directory\n")
        self.assertEqual(result.out, "")

    def test_the_error_is_exactly_one_line(self):
        def reject(arguments):
            raise errors.Rejection(errors.NOT_FOUND, "a.json: first\nsecond")

        with probe(reject):
            result = support.run("probe")
        self.assertEqual(result.err, "error: not-found: a.json: first second\n")

    def test_an_error_that_is_not_a_rejection_is_not_hidden(self):
        def fail(arguments):
            raise ZeroDivisionError

        with probe(fail), self.assertRaises(ZeroDivisionError):
            support.run("probe")


class Reasons(unittest.TestCase):
    def test_every_reason_is_lower_case_letters_digits_and_hyphens(self):
        reasons = [value for name, value in vars(errors).items() if name.isupper()]
        self.assertIn("not-found", reasons)
        for reason in reasons:
            with self.subTest(reason=reason):
                self.assertRegex(reason, r"\A[a-z0-9]+(-[a-z0-9]+)*\Z")

    def test_no_two_reasons_have_the_same_name(self):
        reasons = [value for name, value in vars(errors).items() if name.isupper()]
        self.assertEqual(len(reasons), len(set(reasons)))

    def test_naming_puts_the_file_in_front_of_the_detail(self):
        with self.assertRaises(errors.Rejection) as caught:
            with errors.naming("clip.json"):
                raise errors.Rejection(errors.NOT_FOUND, "gone")
        self.assertEqual(caught.exception.reason, "not-found")
        self.assertEqual(caught.exception.detail, "clip.json: gone")


class ReadingAnInput(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def test_a_file_is_read_whole(self):
        path = self.folder / "data.bin"
        path.write_bytes(b"\x00\x01\r\n\xff")
        self.assertEqual(files.read(path), b"\x00\x01\r\n\xff")

    def test_a_path_that_does_not_exist_is_not_found_and_names_the_file(self):
        path = self.folder / "absent.json"
        with self.assertRaises(errors.Rejection) as caught:
            files.read(path)
        self.assertEqual(caught.exception.reason, "not-found")
        self.assertIn(str(path), caught.exception.detail)

    def test_a_path_that_cannot_be_read_is_not_found(self):
        with self.assertRaises(errors.Rejection) as caught:
            files.read(self.folder)
        self.assertEqual(caught.exception.reason, "not-found")

    def test_the_reason_of_a_missing_file_can_be_more_specific(self):
        with self.assertRaises(errors.Rejection) as caught:
            files.read(self.folder / "absent.json", missing="mapping-missing")
        self.assertEqual(caught.exception.reason, "mapping-missing")

    def test_a_missing_input_gives_the_not_found_line_through_the_command_line(self):
        path = self.folder / "absent.json"
        with probe(lambda arguments: files.read(path)):
            result = support.run("probe")
        self.assertEqual(result.status, 1)
        self.assertTrue(re.fullmatch(r"error: not-found: .*absent\.json: .+\n", result.err), result.err)


class WritingAnOutput(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def names(self):
        return sorted(entry.name for entry in self.folder.iterdir())

    def test_the_file_holds_the_bytes_and_no_part_file_is_left(self):
        files.write(self.folder / "out.bin", b"line\r\nline\n\x00")
        self.assertEqual((self.folder / "out.bin").read_bytes(), b"line\r\nline\n\x00")
        self.assertEqual(self.names(), ["out.bin"])

    def test_an_existing_file_is_replaced(self):
        path = self.folder / "out.bin"
        path.write_bytes(b"a longer earlier content")
        files.write(path, b"new")
        self.assertEqual(path.read_bytes(), b"new")
        self.assertEqual(self.names(), ["out.bin"])

    def test_a_folder_that_does_not_exist_is_cannot_write_and_leaves_nothing(self):
        path = self.folder / "absent" / "out.bin"
        with self.assertRaises(errors.Rejection) as caught:
            files.write(path, b"new")
        self.assertEqual(caught.exception.reason, "cannot-write")
        self.assertIn(str(path), caught.exception.detail)
        self.assertEqual(self.names(), [])

    def test_a_failed_move_removes_the_part_file_and_keeps_the_old_file(self):
        path = self.folder / "out.bin"
        path.write_bytes(b"old")
        with mock.patch("os.replace", side_effect=PermissionError(13, "Permission denied")):
            with self.assertRaises(errors.Rejection) as caught:
                files.write(path, b"new")
        self.assertEqual(caught.exception.reason, "cannot-write")
        self.assertEqual(path.read_bytes(), b"old")
        self.assertEqual(self.names(), ["out.bin"])


def odrg_file(*records, width=1, height=1):
    """An uncompressed ODRG file without a palette, made of stored frame records."""
    data = struct.pack("<4sBBHHHI", b"ODRG", 1, 0, width, height, 0, len(records))
    for duration, picture in records:
        data += struct.pack("<HHB", duration, len(picture) + 1, 0x40) + picture
    return data


class Decode(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.source = self.folder / "clip.odrg"
        self.output = self.folder / "clip.json"

    def names(self):
        return sorted(entry.name for entry in self.folder.iterdir())

    def test_it_writes_the_frames_in_the_canonical_form(self):
        self.source.write_bytes(odrg_file((20, b"\x01\x02\x03"), (40, b"\x00\x00\xff")))
        result = support.run("decode", self.source, self.output)
        self.assertEqual(result, support.Result(0, "", ""))
        expected = (
            b'{\n  "version": 1,\n  "width": 1,\n  "height": 1,\n  "frames": [\n'
            b'    {"ms": 20, "pixels": [66051]},\n'
            b'    {"ms": 40, "pixels": [255]}\n  ]\n}\n'
        )
        self.assertEqual(self.output.read_bytes(), expected)
        self.assertEqual(self.names(), ["clip.json", "clip.odrg"])

    def test_records_with_the_same_picture_become_one_frame(self):
        same = b"\x01\x02\x03"
        self.source.write_bytes(odrg_file((65535, same), (65535, same), (10, same), (20, b"\x00\x00\x00")))
        self.assertEqual(support.run("decode", self.source, self.output).status, 0)
        self.assertIn(b'{"ms": 131080, "pixels": [66051]},\n', self.output.read_bytes())
        self.assertEqual(self.output.read_bytes().count(b'"ms"'), 2)

    def test_it_runs_as_a_module(self):
        self.source.write_bytes(odrg_file((20, b"\x01\x02\x03")))
        result = support.run_module("decode", self.source, self.output)
        self.assertEqual(result, support.Result(0, "", ""))
        self.assertIn(b'"pixels": [66051]', self.output.read_bytes())

    def test_an_existing_output_is_replaced(self):
        self.source.write_bytes(odrg_file((20, b"\x01\x02\x03")))
        self.output.write_bytes(b"something else, and longer than the new content " * 20)
        self.assertEqual(support.run("decode", self.source, self.output).status, 0)
        self.assertTrue(self.output.read_bytes().startswith(b'{\n  "version": 1,\n'))
        self.assertTrue(self.output.read_bytes().endswith(b"]\n}\n"))
        self.assertEqual(self.names(), ["clip.json", "clip.odrg"])

    def test_a_rejected_input_leaves_no_output_and_no_part_file(self):
        self.source.write_bytes(b"ODRX" + odrg_file((20, b"\x01\x02\x03"))[4:])
        result = support.run("decode", self.source, self.output)
        self.assertEqual(result.status, 1)
        self.assertEqual(result.out, "")
        self.assertTrue(result.err.startswith(f"error: bad-magic: {self.source}: "), result.err)
        self.assertEqual(result.err.count("\n"), 1)
        self.assertEqual(self.names(), ["clip.odrg"])

    def test_a_rejected_input_leaves_an_existing_output_as_it_was(self):
        self.source.write_bytes(odrg_file((20, b"\x01\x02\x03"))[:-1])
        self.output.write_bytes(b"kept")
        result = support.run("decode", self.source, self.output)
        self.assertEqual(result.status, 1)
        self.assertTrue(result.err.startswith("error: truncated: "), result.err)
        self.assertEqual(self.output.read_bytes(), b"kept")
        self.assertEqual(self.names(), ["clip.json", "clip.odrg"])

    def test_an_input_that_does_not_exist_is_not_found(self):
        result = support.run("decode", self.source, self.output)
        self.assertEqual(result.status, 1)
        self.assertTrue(result.err.startswith(f"error: not-found: {self.source}: "), result.err)
        self.assertEqual(self.names(), [])

    def test_an_output_folder_that_does_not_exist_is_cannot_write(self):
        self.source.write_bytes(odrg_file((20, b"\x01\x02\x03")))
        result = support.run("decode", self.source, self.folder / "absent" / "clip.json")
        self.assertEqual(result.status, 1)
        self.assertTrue(result.err.startswith("error: cannot-write: "), result.err)
        self.assertEqual(self.names(), ["clip.odrg"])

    def test_a_missing_argument_is_a_usage_error_and_writes_nothing(self):
        self.source.write_bytes(odrg_file((20, b"\x01\x02\x03")))
        result = support.run("decode", self.source)
        self.assertEqual(result.status, 2)
        self.assertIn("usage:", result.err)
        self.assertEqual(self.names(), ["clip.odrg"])


SOURCE = (
    b'{\n  "version": 1,\n  "width": 3,\n  "height": 2,\n  "frames": [\n'
    b'    {"ms": 500, "pixels": [16711680, 0, 0, 0, 0, 255]},\n'
    b'    {"ms": 70000, "pixels": [0, 0, 0, 0, 65280, 0]},\n'
    b'    {"ms": 20, "pixels": [16711680, 0, 0, 0, 0, 255]}\n  ]\n}\n'
)


class Encode(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.source = self.folder / "clip.json"
        self.output = self.folder / "clip.odrg"
        self.source.write_bytes(SOURCE)

    def names(self):
        return sorted(entry.name for entry in self.folder.iterdir())

    def test_it_writes_a_compressed_file_unless_asked_otherwise(self):
        self.assertEqual(support.run("encode", self.source, self.output), support.Result(0, "", ""))
        packed = self.output.read_bytes()
        self.assertEqual(packed[:4], b"ODRG")
        self.assertEqual(packed[5], 1)
        self.assertEqual(support.run("encode", self.source, self.output, "--uncompressed").status, 0)
        plain = self.output.read_bytes()
        self.assertEqual(plain[5], 0)
        self.assertEqual(self.names(), ["clip.json", "clip.odrg"])

    def test_encode_then_decode_of_a_merged_source_gives_a_byte_identical_file(self):
        back = self.folder / "back.json"
        for options in ((), ("--uncompressed",)):
            with self.subTest(options=options):
                self.assertEqual(support.run("encode", self.source, self.output, *options).status, 0)
                self.assertEqual(support.run("decode", self.output, back).status, 0)
                self.assertEqual(back.read_bytes(), SOURCE)

    def test_two_runs_give_identical_bytes(self):
        second = self.folder / "second.odrg"
        for options in ((), ("--uncompressed",)):
            with self.subTest(options=options):
                self.assertEqual(support.run_module("encode", self.source, self.output, *options).status, 0)
                self.assertEqual(support.run_module("encode", self.source, second, *options).status, 0)
                self.assertEqual(self.output.read_bytes(), second.read_bytes())

    def test_an_existing_output_is_replaced(self):
        self.output.write_bytes(b"x" * 5000)
        self.assertEqual(support.run("encode", self.source, self.output).status, 0)
        self.assertEqual(self.output.read_bytes()[:4], b"ODRG")
        self.assertLess(len(self.output.read_bytes()), 5000)

    def test_an_invalid_source_is_rejected_with_its_json_frames_reason(self):
        self.source.write_bytes(SOURCE.replace(b"0, 0, 0, 0, 65280, 0", b"0, 0, 0, 0, 65280"))
        result = support.run("encode", self.source, self.output)
        self.assertEqual(result.status, 1)
        self.assertTrue(result.err.startswith(f"error: bad-pixel-count: {self.source}: "), result.err)
        self.assertEqual(result.out, "")
        self.assertEqual(self.names(), ["clip.json"])

    def test_a_source_that_cannot_be_written_as_odrg_is_rejected(self):
        self.source.write_bytes(SOURCE.replace(b"70000", b"281470681743360"))
        result = support.run("encode", self.source, self.output)
        self.assertEqual(result.status, 1)
        self.assertTrue(result.err.startswith(f"error: too-many-frames: {self.source}: "), result.err)
        self.assertEqual(self.names(), ["clip.json"])

    def test_a_source_that_does_not_exist_is_not_found(self):
        result = support.run("encode", self.folder / "absent.json", self.output)
        self.assertEqual(result.status, 1)
        self.assertTrue(result.err.startswith("error: not-found: "), result.err)
        self.assertEqual(self.names(), ["clip.json"])

    def test_an_unknown_option_is_a_usage_error_and_writes_nothing(self):
        result = support.run("encode", self.source, self.output, "--fast")
        self.assertEqual(result.status, 2)
        self.assertEqual(self.names(), ["clip.json"])


if __name__ == "__main__":
    unittest.main()

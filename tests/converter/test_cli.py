import re
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


if __name__ == "__main__":
    unittest.main()

import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from fwtool import Failure, build, limit, paths

from . import ROOT, support

LIMIT_FILE = ROOT / "firmware" / "limit.json"


class Reading(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = pathlib.Path(folder.name)

    def written(self, content):
        path = self.folder / "limit.json"
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    def refused(self, content):
        with self.assertRaises(Failure) as caught:
            limit.read(self.written(content))
        return caught.exception.reason, caught.exception.detail

    def test_a_whole_number_from_0_to_65535_is_accepted(self):
        for milliamps in (0, 1, 120, 850, 40000, 65535):
            with self.subTest(milliamps=milliamps):
                self.assertEqual(limit.read(self.written('{"milliamps": %d}' % milliamps)), milliamps)
        self.assertIs(type(limit.read(self.written('{"milliamps":0}'))), int)

    def test_a_number_outside_0_to_65535_is_refused_and_named(self):
        for milliamps in (-1, 65536, 1000000, -850):
            with self.subTest(milliamps=milliamps):
                reason, detail = self.refused('{"milliamps": %d}' % milliamps)
                self.assertEqual(reason, "limit-invalid")
                self.assertIn(f"the limit is {milliamps} mA", detail)
                self.assertIn("0 to 65535", detail)

    def test_what_is_no_whole_number_is_malformed(self):
        for label, value in (("a fraction", "1.5"), ("a whole number written with a fraction", "850.0"), ("an exponent", "8e2"), ("a text", '"850"'),
                             ("a word", '"off"'), ("true", "true"), ("false", "false"), ("null", "null"), ("an array", "[850]"), ("an object", '{"mA": 850}')):
            with self.subTest(value=label):
                self.assertEqual(self.refused('{"milliamps": %s}' % value)[0], "limit-settings-malformed")

    def test_every_other_malformed_form_is_refused(self):
        forms = {
            "not UTF-8": b'{"milliamps": 850, "note": "\xff\xfe"}',
            "a byte-order mark": b'\xef\xbb\xbf{"milliamps": 850}',
            "two values": '{"milliamps": 850}{"milliamps": 850}',
            "a member named twice": '{"milliamps": 850, "milliamps": 850}',
            "an array": "[850]",
            "a number alone": "850",
            "no member": "{}",
            "another member": '{"milliamps": 850, "amps": 1}',
            "another name": '{"limit": 850}',
            "cut short": '{"milliamps": 85',
            "empty": "",
        }
        for label, content in forms.items():
            with self.subTest(form=label):
                self.assertEqual(self.refused(content)[0], "limit-settings-malformed")

    def test_a_fault_of_the_json_text_is_given_with_its_line_and_column(self):
        _, detail = self.refused('{\n  "milliamps" 850\n}\n')
        self.assertRegex(detail, r"line 2, column \d+")

    def test_a_file_that_is_not_there_is_missing(self):
        for path in (self.folder / "nothing.json", self.folder):
            with self.assertRaises(Failure) as caught:
                limit.read(path)
            self.assertEqual(caught.exception.reason, "limit-settings-missing")

    def test_the_line_says_the_limit_or_that_the_limiter_is_off(self):
        self.assertEqual(limit.line(850), "limit: 850 mA")
        self.assertEqual(limit.line(65535), "limit: 65535 mA")
        self.assertEqual(limit.line(0), "limit: off")


# What a refused limit file is refused with, through each command that reads one.
REFUSED = {
    "limit-settings-malformed": ('{"milliamps": 1.5}', '{"milliamps": "850"}', "[850]", ""),
    "limit-invalid": ('{"milliamps": -1}', '{"milliamps": 65536}'),
}
COMMANDS = (("set-limit", "--settings"), ("install-firmware", "--limit"))


class ThroughTheCommands(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = pathlib.Path(folder.name)

    def built(self):
        image = self.folder / "odrig-firmware.bin"
        image.write_bytes(support.PROGRAM)
        build.write_checksum(image)
        return image

    def test_a_limit_file_that_is_refused_stops_the_command_before_the_board_is_touched(self):
        for command, option in COMMANDS:
            for reason, contents in REFUSED.items():
                for number, content in enumerate(contents):
                    with self.subTest(command=command, reason=reason, number=number):
                        path = self.folder / "limit.json"
                        path.write_text(content)
                        with support.untouched_board(), mock.patch.object(build, "checked_image", side_effect=lambda image: self.built()):
                            result = support.run_main(command, option, path)
                        self.assertEqual(result.status, 1)
                        self.assertEqual(result.out, "")
                        self.assertRegex(result.err, rf"\Aerror: {reason}: [^\n]+\n\Z")

    def test_a_limit_file_that_is_not_there_stops_the_command_before_the_board_is_touched(self):
        for command, option in COMMANDS:
            with self.subTest(command=command):
                with support.untouched_board():
                    result = support.run_main(command, option, self.folder / "nothing.json")
                self.assertEqual(result.status, 1)
                self.assertRegex(result.err, r"\Aerror: limit-settings-missing: [^\n]+\n\Z")


class TheLimitFile(unittest.TestCase):
    def test_it_is_the_file_the_tool_reads_and_git_tracks_it(self):
        self.assertEqual(paths.LIMIT_SETTINGS, LIMIT_FILE)
        tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "firmware/limit.json"], capture_output=True)
        self.assertEqual(tracked.returncode, 0)

    def test_it_is_accepted_and_holds_850(self):
        self.assertEqual(limit.read(), 850)
        self.assertEqual(limit.read(LIMIT_FILE), 850)


if __name__ == "__main__":
    unittest.main()

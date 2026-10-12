import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from fwtool import Failure, build, paths, wifi

from . import ROOT, support

SETTINGS_FILE = ROOT / "firmware" / "wifi.json"

# Values made for these tests. None is a secret, and none is in the settings file.
NAME = "a-name-for-the-test"
PASSWORD = "a-password-for-the-test"


def text_of(name=NAME, password=PASSWORD):
    quoted = [value.replace("\\", "\\\\").replace('"', '\\"') for value in (name, password)]
    return '{"name": "%s", "password": "%s"}' % tuple(quoted)


def tracked_files_holding(needle, apart_from=()):
    """The tracked files that hold these bytes, by name."""
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True).stdout
    found = []
    for name in listed.decode("utf-8").split("\0"):
        path = ROOT / name
        if name and name not in apart_from and path.is_file() and needle in path.read_bytes():
            found.append(name)
    return found


class Reading(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = pathlib.Path(folder.name)

    def written(self, content):
        path = self.folder / "settings.json"
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    def refused(self, content):
        """The reason and the detail with which a settings file of this content is refused."""
        with self.assertRaises(Failure) as caught:
            wifi.read(self.written(content))
        return caught.exception.reason, caught.exception.detail

    def test_a_name_of_1_and_of_32_characters_and_a_password_of_8_and_of_63_are_accepted(self):
        for name, password in (("n", PASSWORD), ("n" * 32, PASSWORD), (NAME, "p" * 8), (NAME, "p" * 63), (" ~", " ~" * 4)):
            with self.subTest(name=len(name), password=len(password)):
                read = wifi.read(self.written(text_of(name, password)))
                self.assertTrue(read.name == name and read.password == password)

    def test_an_empty_name_and_one_of_33_characters_are_refused(self):
        for name in ("", "n" * 33):
            with self.subTest(length=len(name)):
                reason, detail = self.refused(text_of(name=name))
                self.assertEqual(reason, "wifi-name-invalid")
                self.assertIn(f"has {len(name)} characters", detail)
                self.assertIn("1 to 32", detail)

    def test_a_password_of_7_and_of_64_characters_is_refused(self):
        for password in ("p" * 7, "p" * 64, ""):
            with self.subTest(length=len(password)):
                reason, detail = self.refused(text_of(password=password))
                self.assertEqual(reason, "wifi-password-invalid")
                self.assertIn(f"has {len(password)} characters", detail)
                self.assertIn("8 to 63", detail)

    def test_a_character_outside_printable_ascii_is_refused_with_the_reason_of_its_value(self):
        for label, character in (("a tab", "\\t"), ("a letter outside ASCII", "é"), ("a zero character", "\\u0000"), ("a delete character", "\\u007f")):
            with self.subTest(character=label):
                name = '{"name": "odd%sname", "password": "%s"}' % (character, PASSWORD)
                self.assertEqual(self.refused(name)[0], "wifi-name-invalid")
                password = '{"name": "%s", "password": "odd%spassword"}' % (NAME, character)
                self.assertEqual(self.refused(password)[0], "wifi-password-invalid")

    def test_the_name_is_judged_before_the_password(self):
        self.assertEqual(self.refused(text_of(name="", password=""))[0], "wifi-name-invalid")

    def test_the_values_are_taken_as_they_are_in_the_file(self):
        read = wifi.read(self.written(text_of(name=" a name ", password="  with spaces  ")))
        self.assertTrue(read.name == " a name " and read.password == "  with spaces  ")

    def test_a_file_that_is_not_there_is_missing(self):
        with self.assertRaises(Failure) as caught:
            wifi.read(self.folder / "nothing.json")
        self.assertEqual(caught.exception.reason, "wifi-settings-missing")
        with self.assertRaises(Failure) as caught:
            wifi.read(self.folder)
        self.assertEqual(caught.exception.reason, "wifi-settings-missing")

    def test_every_malformed_form_is_refused(self):
        whole = text_of()
        forms = {
            "not UTF-8": whole.encode("utf-8").replace(b"a-name", b"a-\xff\xfename"),
            "a byte-order mark": b"\xef\xbb\xbf" + whole.encode("utf-8"),
            "two values": whole + whole,
            "a member named twice": '{"name": "%s", "name": "%s", "password": "%s"}' % (NAME, NAME, PASSWORD),
            "an array": '["%s", "%s"]' % (NAME, PASSWORD),
            "a text": '"%s"' % PASSWORD,
            "no name": '{"password": "%s"}' % PASSWORD,
            "no password": '{"name": "%s"}' % NAME,
            "a third member": '{"name": "%s", "password": "%s", "channel": 6}' % (NAME, PASSWORD),
            "a number for the name": '{"name": 5, "password": "%s"}' % PASSWORD,
            "a number for the password": '{"name": "%s", "password": 12345678}' % NAME,
            "null for the password": '{"name": "%s", "password": null}' % NAME,
            "cut short": whole[:-3],
            "empty": "",
        }
        for label, content in forms.items():
            with self.subTest(form=label):
                self.assertEqual(self.refused(content)[0], "wifi-settings-malformed")

    def test_a_fault_of_the_json_text_is_given_with_its_line_and_column(self):
        _, detail = self.refused('{\n  "name": "%s",\n  "password" "%s"\n}\n' % (NAME, PASSWORD))
        self.assertRegex(detail, r"line 3, column \d+")

    def test_no_detail_quotes_text_of_the_file(self):
        marked = "Zq7-marked-text"
        contents = [
            text_of(name=marked * 3), text_of(password=marked * 5),
            '{"name": "%s\\t", "password": "%s"}' % (marked, PASSWORD), '{"name": "%s", "password": "%s\\t"}' % (NAME, marked),
            '{"name": "%s", "password": "%s", "%s": 1}' % (marked, marked, marked), '{"%s": 1, "%s": 2}' % (marked, marked),
            '{"name": "%s", "password": %s}' % (marked, marked), '["%s"]' % marked, '{"name": "%s"' % marked,
            '{"name": "%s", "password": "%s"} %s' % (marked, marked, marked),
        ]
        for content in contents:
            with self.subTest(content=content[:30]):
                reason, detail = self.refused(content)
                self.assertNotIn(marked, detail)
                self.assertNotIn("Zq7", detail)

    def test_the_text_form_of_the_settings_does_not_hold_the_password(self):
        read = wifi.read(self.written(text_of()))
        for text in (repr(read), str(read), f"{read}", "%s" % (read,), repr([read])):
            self.assertNotIn(PASSWORD, text)
            self.assertIn(NAME, text)
        self.assertEqual(repr(read), f"Settings(name={NAME!r}, password=<hidden>)")


# The commands that read a settings file.
COMMANDS = ("set-wifi", "install-firmware")

REFUSED = {
    "wifi-settings-malformed": ('["%s", "%s"]' % (NAME, PASSWORD), '{"name": "%s"}' % NAME, text_of() + text_of(), ""),
    "wifi-name-invalid": (text_of(name=""), text_of(name="n" * 33)),
    "wifi-password-invalid": (text_of(password="p" * 7), text_of(password="p" * 64)),
}


class ThroughTheCommands(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = pathlib.Path(folder.name)

    def built(self):
        """A built image in place, with its checksum beside it."""
        image = self.folder / "odrig-firmware.bin"
        image.write_bytes(support.PROGRAM)
        build.write_checksum(image)
        return image

    def test_a_settings_file_that_is_refused_stops_the_command_before_the_board_is_touched(self):
        for command in COMMANDS:
            for reason, contents in REFUSED.items():
                for number, content in enumerate(contents):
                    with self.subTest(command=command, reason=reason, number=number):
                        path = self.folder / "settings.json"
                        path.write_text(content)
                        with support.untouched_board():
                            result = support.run_main(command, "--settings", path)
                        self.assertEqual(result.status, 1)
                        self.assertEqual(result.out, "")
                        self.assertRegex(result.err, rf"\Aerror: {reason}: [^\n]+\n\Z")
                        with support.untouched_board(), mock.patch.object(build, "checked_image", side_effect=lambda image: self.built()):
                            self.assertEqual(support.run_main(command, "--settings", path), result)

    def test_a_settings_file_that_is_not_there_stops_the_command_before_the_board_is_touched(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                with support.untouched_board():
                    result = support.run_main(command, "--settings", self.folder / "nothing.json")
                self.assertEqual(result.status, 1)
                self.assertRegex(result.err, r"\Aerror: wifi-settings-missing: [^\n]+\n\Z")


class TheSettingsFile(unittest.TestCase):
    def test_it_is_the_file_the_tool_reads_and_git_tracks_it(self):
        self.assertEqual(paths.WIFI_SETTINGS, SETTINGS_FILE)
        tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "firmware/wifi.json"], capture_output=True)
        self.assertEqual(tracked.returncode, 0)

    def test_it_is_accepted_names_odrig_and_does_not_hold_wleds_default_password(self):
        read = wifi.read()
        self.assertEqual(read.name, "odrig")
        self.assertFalse(read.password == "wled1234")
        self.assertEqual(wifi.read(SETTINGS_FILE), read)

    def test_no_other_tracked_file_holds_the_password(self):
        password = wifi.read().password.encode("ascii")
        holding = tracked_files_holding(password, apart_from=("firmware/wifi.json",))
        self.assertEqual(holding, [], "these tracked files hold the password")

    def test_the_search_finds_a_word_of_a_file_in_that_file(self):
        word = max((ROOT / "README.md").read_bytes().split(), key=len)
        self.assertIn("README.md", tracked_files_holding(word))
        self.assertNotIn("README.md", tracked_files_holding(word, apart_from=("README.md",)))


if __name__ == "__main__":
    unittest.main()

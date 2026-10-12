import json
import re
import unittest

from . import ROOT, hostprogram, support

SOURCES = ROOT / "firmware" / "standalone" / "src"

NAME = b"odrig-in-a-test"
PASSWORD = b"a-made-up-password"
NOTHING = {"network": False, "name": b"", "password": b"", "channel": 6, "hidden": False, "limit_ma": 850}


def config(name=NAME, **more):
    access = {} if name is None else {"ssid": name.decode("utf-8")}
    access.update(more)
    return json.dumps({"ap": access}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def secrets(password=PASSWORD):
    return json.dumps({"ap": {"psk": password.decode("utf-8")}}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def with_limit(text):
    return b'{"hw":{"led":{"maxpwr":' + text + b'}}}'


class TheNetwork(unittest.TestCase):
    def test_a_name_and_a_password_give_a_network(self):
        found = hostprogram.settings(config(), secrets())
        self.assertEqual(found, {**NOTHING, "network": True, "name": NAME, "password": PASSWORD})

    def test_the_files_the_firmware_tool_writes_are_read(self):
        from fwtool import storage, wifi
        given = wifi.Settings(NAME.decode(), PASSWORD.decode())
        for label, files in (("the bench board", support.BENCH_FILES), ("what WLED saved", support.SAVED_FILES)):
            with self.subTest(files=label):
                written = storage.files_in(storage.mount(wifi.apply(support.storage_image(files), given)))
                found = hostprogram.settings(written["/cfg.json"], written["/wsec.json"])
                self.assertTrue(found["network"])
                self.assertEqual((found["name"], found["password"]), (NAME, PASSWORD))
                self.assertEqual(found["limit_ma"], 850)
        self.assertEqual((found["channel"], found["hidden"]), (11, True))

    def test_the_lengths_at_and_beside_every_limit(self):
        for length, hosted in ((0, False), (1, True), (32, True), (33, False), (100, False)):
            with self.subTest(name=length):
                found = hostprogram.settings(config(b"n" * length), secrets())
                self.assertEqual((found["network"], found["name"]), (hosted, b"n" * length if hosted else b""))
        for length, hosted in ((0, False), (7, False), (8, True), (63, True), (64, False), (200, False)):
            with self.subTest(password=length):
                found = hostprogram.settings(config(), secrets(b"p" * length))
                self.assertEqual((found["network"], found["password"]), (hosted, b"p" * length if hosted else b""))

    def test_without_either_of_the_two_there_is_no_network_and_neither_is_given(self):
        cases = {
            "no file at all": (None, None),
            "no secrets": (config(), None),
            "no configuration": (None, secrets()),
            "a configuration without an access point": (b'{"hw":{"led":{"maxpwr":850}}}', secrets()),
            "an access point without a name": (config(None, chan=3), secrets()),
            "secrets without the password": (config(), b'{"ap":{},"ota":{"pwd":"made-up"}}'),
            "empty files": (b"", b""),
        }
        for label, (first, second) in cases.items():
            with self.subTest(case=label):
                found = hostprogram.settings(first, second)
                self.assertEqual((found["network"], found["name"], found["password"]), (False, b"", b""))

    def test_a_mark_a_backslash_and_a_slash_may_be_written_with_a_backslash(self):
        found = hostprogram.settings(b'{"ap":{"ssid":"a \\"name\\" \\\\ \\/ here"}}', b'{"ap":{"psk":"pass\\\\word \\"1\\""}}')
        self.assertEqual((found["network"], found["name"], found["password"]), (True, b'a "name" \\ / here', b'pass\\word "1"'))

    def test_a_text_with_another_escape_is_not_taken(self):
        for escaped in (b"\\n", b"\\t", b"\\u0041", b"\\b"):
            with self.subTest(escape=escaped):
                self.assertFalse(hostprogram.settings(b'{"ap":{"ssid":"a' + escaped + b'b"}}', secrets())["network"])
                self.assertFalse(hostprogram.settings(config(), b'{"ap":{"psk":"password' + escaped + b'"}}')["network"])

    def test_bytes_outside_ascii_are_taken_as_they_are(self):
        name = "Wänd ß".encode("utf-8")
        found = hostprogram.settings(config(name), secrets())
        self.assertEqual((found["network"], found["name"]), (True, name))

    def test_what_is_no_text_is_no_name_and_no_password(self):
        for value in (b"5", b"true", b"null", b'["odrig"]', b'{"a":"odrig"}'):
            with self.subTest(value=value):
                self.assertFalse(hostprogram.settings(b'{"ap":{"ssid":' + value + b"}}", secrets())["network"])
                self.assertFalse(hostprogram.settings(config(), b'{"ap":{"psk":' + value + b"}}")["network"])

    def test_of_a_member_named_twice_the_first_counts(self):
        found = hostprogram.settings(b'{"ap":{"ssid":"first","ssid":"second"},"ap":{"ssid":"third"}}', secrets())
        self.assertEqual(found["name"], b"first")

    def test_a_name_elsewhere_in_the_file_is_not_the_networks(self):
        elsewhere = b'{"id":{"ssid":"one"},"nw":{"ins":[{"ssid":"two","ap":{"ssid":"three"}}]},"x":{"ap":{"ssid":"four"}},"ap":{"deeper":{"ssid":"five"}}}'
        self.assertFalse(hostprogram.settings(elsewhere, secrets())["network"])
        found = hostprogram.settings(elsewhere[:-1] + b',"ap":{"ssid":"six"}}', secrets())
        self.assertEqual((found["network"], found["name"]), (True, b"six"))
        found = hostprogram.settings(b'{"x":{"ap":{"ssid":"four"}},"ap":{"deeper":{"ssid":"five"},"ssid":"the one"}}', secrets())
        self.assertEqual((found["network"], found["name"]), (True, b"the one"))


class TheChannelAndTheLimit(unittest.TestCase):
    def test_a_channel_from_1_to_13_is_taken_and_anything_else_is_6(self):
        for written, channel in ((1, 1), (6, 6), (11, 11), (13, 13), (0, 6), (14, 6), (-3, 6), (1.5, 6), ("11", 6), (None, 6), (True, 6)):
            with self.subTest(written=written):
                self.assertEqual(hostprogram.settings(config(chan=written), secrets())["channel"], channel)
        self.assertEqual(hostprogram.settings(config(), secrets())["channel"], 6)

    def test_the_network_is_hidden_when_the_file_says_so_with_a_number_above_0(self):
        for written, hidden in ((0, False), (1, True), (2, True), (-1, False), ("1", False), (None, False)):
            with self.subTest(written=written):
                self.assertEqual(hostprogram.settings(config(hide=written), secrets())["hidden"], hidden)

    def test_the_limit_is_a_whole_number_from_0_to_65535_and_850_without_one(self):
        for written, limit in ((b"0", 0), (b"1", 1), (b"850", 850), (b"36000", 36000), (b"65535", 65535), (b"65536", 850), (b"4294967296", 850),
                               (b"99999999999999999999", 850), (b"-1", 850), (b"850.0", 850), (b"1.5", 850), (b"8e2", 850), (b'"850"', 850),
                               (b"null", 850), (b"true", 850), (b"[850]", 850), (b'{"mA":850}', 850)):
            with self.subTest(written=written):
                self.assertEqual(hostprogram.settings(with_limit(written), None)["limit_ma"], limit)

    def test_the_limit_is_taken_without_a_network_and_the_network_without_a_limit(self):
        self.assertEqual(hostprogram.settings(with_limit(b"0"), None), {**NOTHING, "limit_ma": 0})
        self.assertEqual(hostprogram.settings(config(), secrets())["limit_ma"], 850)
        self.assertEqual(hostprogram.settings(None, secrets())["limit_ma"], 850)

    def test_only_the_limit_of_all_leds_is_taken_not_the_one_of_an_output(self):
        text = b'{"hw":{"led":{"ins":[{"maxpwr":425,"led":{"maxpwr":1}}],"total":360,"maxpwr":0},"maxpwr":7},"led":{"maxpwr":9},"maxpwr":3}'
        self.assertEqual(hostprogram.settings(text, None)["limit_ma"], 0)
        self.assertEqual(hostprogram.settings(b'{"hw":{"led":{"x":{"maxpwr":5}}}}', None)["limit_ma"], 850)


class FilesThatAreNotJson(unittest.TestCase):
    def test_a_file_that_is_not_one_json_object_counts_as_absent(self):
        whole = config(chan=3)[:-1] + b',"hw":{"led":{"maxpwr":0}}}'
        self.assertEqual(hostprogram.settings(whole, secrets()), {**NOTHING, "network": True, "name": NAME, "password": PASSWORD, "channel": 3, "limit_ma": 0})
        broken = {
            "cut short": whole[:-1],
            "cut inside a text": whole[:20],
            "text after it": whole + b" x",
            "two objects": whole + whole,
            "an array": b"[" + whole + b"]",
            "a text": b'"odrig"',
            "a comma too many": whole[:-1] + b",}",
            "a member without a value": whole[:-1] + b',"x":}',
            "a name without marks": whole[:-1] + b",x:1}",
            "a number with two points": whole[:-1] + b',"x":1.2.3}',
            "a number that ends in a point": whole[:-1] + b',"x":1.}',
            "a word that is no value": whole[:-1] + b',"x":nul}',
            "a bad escape": whole[:-1] + b',"x":"\\q"}',
            "a short unicode escape": whole[:-1] + b',"x":"\\u12"}',
            "a line feed inside a text": whole[:-1] + b',"x":"a\nb"}',
            "nested deeper than 32": whole[:-1] + b',"x":' + b"[" * 40 + b"]" * 40 + b"}",
            "longer than 16,384 bytes": whole[:-1] + b',"x":"' + b"x" * 16384 + b'"}',
        }
        for label, text in broken.items():
            with self.subTest(file=label):
                self.assertEqual(hostprogram.settings(text, secrets()), NOTHING)
        self.assertFalse(hostprogram.settings(config(), secrets()[:-1])["network"])

    def test_a_file_of_exactly_the_longest_allowed_is_read(self):
        padded = config()[:-1] + b',"x":"' + b"x" * (16384 - len(config()) - 7) + b'"}'
        self.assertEqual(len(padded), 16384)
        self.assertTrue(hostprogram.settings(padded, secrets())["network"])
        self.assertFalse(hostprogram.settings(padded + b" ", secrets())["network"])

    def test_spaces_and_line_ends_between_the_parts_are_fine(self):
        text = b' {\r\n\t"ap" : {\n  "ssid" : "odrig" ,\n  "chan" : 9\n } ,\n "hw" : { "led" : { "maxpwr" : 0 } }\n}\n'
        found = hostprogram.settings(text, b'\n{ "ap" : { "psk" : "a-made-up-password" } }\n')
        self.assertEqual(found, {**NOTHING, "network": True, "name": b"odrig", "password": PASSWORD, "channel": 9, "limit_ma": 0})

    def test_every_cut_of_a_whole_file_is_read_without_a_fault_and_counts_as_absent(self):
        whole = support.SAVED_CONFIG.encode("utf-8")
        for cut in range(0, len(whole), 7):
            found = hostprogram.settings(whole[:cut], secrets())
            self.assertEqual(found, NOTHING, cut)


class TheSource(unittest.TestCase):
    def test_the_reader_knows_nothing_of_the_chip_and_takes_no_memory(self):
        for name in ("settings.h", "settings.cpp"):
            text = (SOURCES / name).read_text(encoding="utf-8")
            headers = set(re.findall(r'(?m)^#include\s+[<"]([^>"]+)[>"]', text))
            self.assertLessEqual(headers, {"stddef.h", "stdint.h", "string.h", "settings.h"}, name)
            self.assertNotRegex(text, r"\bString\b|\bSerial\b|LittleFS|\bmalloc\b|\bnew\b|\bstd::", name)

    def test_the_limits_are_those_of_a_network_name_and_a_wpa2_password_and_wleds_defaults(self):
        header = (SOURCES / "settings.h").read_text(encoding="utf-8")
        for expected in ("ODRIG_NAME_LONGEST = 32;", "ODRIG_PASSWORD_SHORTEST = 8;", "ODRIG_PASSWORD_LONGEST = 63;", "ODRIG_SETTINGS_LONGEST = 16384;",
                         "ODRIG_CHANNEL_DEFAULT = 6;", "ODRIG_LIMIT_DEFAULT_MA = 850;"):
            self.assertIn(expected, header)


if __name__ == "__main__":
    unittest.main()

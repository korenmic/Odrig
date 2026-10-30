import json
import unittest

from odrig import odrg

from . import support
from .test_playback import T0, Playback

OK = '{"ok":true}'
LONGEST = 2048


def refused(code):
    return f'{{"ok":false,"error":"{code}"}}'


def invalid_show():
    files = support.example_show()
    del files["dvd.odrg"]
    return support.with_show_fault(files)


class Commands(Playback):
    def replies(self, lines, files=None, as_bytes=False):
        """The replies to command lines, all given at one moment. The reference player
        gives the same."""
        files = files or support.example_show()
        make = support.linehex if as_bytes else support.line
        printed = self.assert_as_the_reference(files, [make(T0, line) for line in lines])
        self.assertEqual(len(printed), len(lines))
        return [printed_line[len("reply "):] for printed_line in printed]

    def status(self, files, script):
        """The state the last line of a script reports, which is `status`."""
        printed = self.assert_as_the_reference(files, script)
        return json.loads(printed[-1][len("reply "):])


class EveryCommand(Commands):
    def test_each_command_is_answered(self):
        lines = ["play 1", "play 2", "play 3", "on", "off", "brightness 0", "brightness 255", "status"]
        replies = self.replies(lines)
        self.assertEqual(replies[:7], [OK] * 7)
        self.assertEqual(replies[7], '{"ok":true,"on":false,"brightness":255,"mini":{"supported":false,"on":false,"pending":false,"requested":false,"error":null,"brightness":0},"playing":3,"animation":1,"fps":0,"error":null,"width":60,"height":6,"readiness":"ready","checked":2,"to_check":0,"unavailable":0,"checking":null,"host":null,"seed":null,"repeat":null,"loop":null,"saved":null,"file":"hello.odrg","playlist":null,"clocks":false,"clock_message":false,"left":86400}')

    def test_play_plays_an_animation_in_the_playlist_and_a_cycle_by_itself(self):
        for number, playing, animation in ((1, "all", 1), (2, "all", 2), (3, 3, 1)):
            state = self.status(support.example_show(), [support.line(T0, f"play {number}"), support.line(T0, "status")])
            self.assertEqual((state["playing"], state["animation"]), (playing, animation))

    def test_play_all_plays_the_playlist(self):
        state = self.status(support.example_show(), [support.line(T0, "play all"), support.line(T0, "status")])
        self.assertEqual((state["playing"], state["animation"]), ("all", 1))

    def test_on_and_off_switch_the_leds(self):
        state = self.status(support.example_show(), [support.line(T0, "off"), support.line(T0, "status")])
        self.assertIs(state["on"], False)
        state = self.status(support.example_show(), [support.line(T0, "off"), support.line(T0, "on"), support.line(T0, "status")])
        self.assertIs(state["on"], True)
        state = self.status(support.example_show(), [support.line(T0, "on"), support.line(T0, "on"), support.line(T0, "status")])
        self.assertIs(state["on"], True)

    def test_brightness_sets_the_brightness(self):
        for value in (0, 1, 128, 254, 255):
            state = self.status(support.example_show(), [support.line(T0, f"brightness {value}"), support.line(T0, "status")])
            self.assertEqual(state["brightness"], value)

    def test_leading_zeros_do_not_matter(self):
        files = support.example_show()
        files["show.json"] = support.show_text(json.loads(files["show.json"])["items"] + [{"id": 7, "file": "dvd.odrg"}], 128, 3)
        self.assertEqual(self.replies(["play 007", "play 0000000000000000000000000000000000000000000000000000000007", "brightness 0255", "brightness 000"], files), [OK] * 4)
        state = self.status(files, [support.line(T0, "play 007"), support.line(T0, "brightness 0031"), support.line(T0, "status")])
        self.assertEqual((state["playing"], state["animation"], state["brightness"]), ("all", 7, 31))


class EveryErrorCode(Commands):
    def test_unknown_command(self):
        lines = ["", "stop", "Play 1", "PLAY 1", "STATUS", "On", "plays 1", "pla", "brightnes 5", "statu", "statuss", " status", " on", "status\t", "\tstatus", "play\t1", "?", "{}", "1"]
        self.assertEqual(self.replies(lines), [refused("unknown-command")] * len(lines))

    def test_bad_argument(self):
        lines = [
            "play", "play ", "play  1", "play 1 ", "play 1 2", "play a", "play 1a", "play a1", "play -1", "play +1", "play 1.0", "play 1e0",
            "play 0x1", "play 0", "play 00", "play 4294967296", "play 99999999999", "play 4294967297", "play " + "9" * 30,
            "brightness", "brightness ", "brightness 256", "brightness -1", "brightness 1 1", "brightness  1", "brightness 12.5", "brightness " + "1" * 30,
            "on 1", "on ", "off 0", "off  ", "status 1", "status ", "status  ", "status status",
            "play 1 2 3 4", "play 1 2 3 4 5", "play 1 2 3 4 5 6 7 8 9", "status 1 2 3 4 5", "on" + " " * 5, "off" + " x" * 1000,
            "brightness 1 2 3 4 5 6", "play" + " " * 2044, "status" + " " * 2042,
        ]
        self.assertEqual(self.replies(lines), [refused("bad-argument")] * len(lines))

    def test_bad_argument_for_digits_that_are_not_ascii(self):
        lines = ["play ٣".encode("utf-8"), "brightness １".encode("utf-8"), b"play 1\x00", b"play \x001", b"brightness 1\xff"]
        self.assertEqual(self.replies(lines, as_bytes=True), [refused("bad-argument")] * len(lines))

    def test_unknown_id(self):
        lines = ["play 4", "play 65535", "play 30", "play 0004"]
        self.assertEqual(self.replies(lines), [refused("unknown-id")] * len(lines))

    def test_show_invalid(self):
        lines = ["play 1", "play 2", "play 3", "play 4", "play 65535", "play 001"]
        self.assertEqual(self.replies(lines, invalid_show()), [refused("show-invalid")] * len(lines))

    def test_line_too_long(self):
        lines = ["x" * 2049, "status" + " " * 2043, "play " + "1" * 2044, "brightness " + "0" * 2038, "x" * 4096, "x" * 5000, "x" * 70000, " " * 2049]
        self.assertEqual([len(line) > LONGEST for line in lines], [True] * len(lines))
        self.assertEqual(self.replies(lines), [refused("line-too-long")] * len(lines))

    def test_a_line_of_some_hundred_characters_is_read_as_a_command(self):
        lines = {
            "x" * 65: "unknown-command",
            "x" * 192: "unknown-command",
            "status" + " " * 59: "bad-argument",
            "play " + "1" * 60: "bad-argument",
            "play " + "0" * 59 + "4": "unknown-id",
        }
        self.assertEqual(self.replies(list(lines)), [refused(code) for code in lines.values()])
        self.assertEqual(self.replies(["brightness " + "0" * 54, "play " + "0" * 59 + "2"]), [OK, OK])

    def test_of_two_codes_that_apply_the_first_of_the_table_is_given(self):
        valid = {
            "y" * 2049: "line-too-long",
            "play " + "x" * 2044: "line-too-long",
            "play 99" + " " * 2042: "line-too-long",
            "stop" + " 1" * 1023: "line-too-long",
            "stop 1 2 3": "unknown-command",
            "stop 1 2 3 4 5 6": "unknown-command",
            "stop" + " 1" * 1022: "unknown-command",
            "stop ": "unknown-command",
            "playing x": "unknown-command",
            "play 99 99": "bad-argument",
            "play 0": "bad-argument",
            "play 99": "unknown-id",
        }
        self.assertEqual(self.replies(list(valid)), [refused(code) for code in valid.values()])
        invalid = {
            "play " + "1" * 2044: "line-too-long",
            "plays 1": "unknown-command",
            "plays 1 2 3 4 5 6": "unknown-command",
            "play 1 2 3 4 5 6": "bad-argument",
            "play x": "bad-argument",
            "play 0": "bad-argument",
            "play 4294967296": "bad-argument",
            "play 1 ": "bad-argument",
            "play 99": "show-invalid",
            "play 1": "show-invalid",
        }
        self.assertEqual(self.replies(list(invalid), invalid_show()), [refused(code) for code in invalid.values()])

    def test_a_line_that_is_refused_changes_nothing(self):
        files = support.example_show()
        before = self.status(files, [support.line(T0, "status")])
        refusals = ["play 4", "play 0", "brightness 256", "off 1", "on 1", "bogus", "play 1" + "0" * 70, "play 1" + "0" * 2043, "brightness", "Off", "OFF", "off 1 2 3 4 5 6"]
        after = self.status(files, [support.line(T0, line) for line in refusals] + [support.line(T0, "status")])
        self.assertEqual(after, before)


class LineEndings(Commands):
    def test_one_newline_and_one_carriage_return_before_it_are_ignored(self):
        accepted = [b"on", b"on\n", b"on\r\n", b"on\r"]
        self.assertEqual(self.replies(accepted, as_bytes=True), [OK] * len(accepted))
        other = [b"on\n\n", b"on\r\r\n", b"on\n\r", b"\non", b"\ron", b"on\r\r", b"on \n", b"on\t\n"]
        replies = self.replies(other, as_bytes=True)
        self.assertEqual(replies[:6], [refused("unknown-command")] * 6)
        self.assertEqual(replies[6], refused("bad-argument"))
        self.assertEqual(replies[7], refused("unknown-command"))

    def test_an_empty_line_gets_a_reply(self):
        lines = [b"", b"\n", b"\r\n", b"\r", b" ", b"  "]
        self.assertEqual(self.replies(lines, as_bytes=True), [refused("unknown-command")] * len(lines))

    def test_lines_of_exactly_2048_and_2049_characters(self):
        longest = "brightness " + "0" * 2034 + "200"
        self.assertEqual(len(longest), 2048)
        lines = [longest, longest + "\n", longest + "\r\n", longest + "\r"]
        self.assertEqual(self.replies([line.encode() for line in lines], as_bytes=True), [OK] * 4)
        one_more = "brightness " + "0" * 2035 + "200"
        self.assertEqual(len(one_more), 2049)
        lines = [one_more, one_more + "\n", one_more + "\r\n", longest + "\r\r\n", longest + " "]
        self.assertEqual(self.replies([line.encode() for line in lines], as_bytes=True), [refused("line-too-long")] * 5)
        state = self.status(support.example_show(), [support.line(T0, longest), support.line(T0, "status")])
        self.assertEqual(state["brightness"], 200)

    def test_the_longest_reply_to_status_is_one_line_well_under_the_limit(self):
        longest_name = "a" * 27 + ".odrg"
        bad_index = odrg.container(60, 6, [b"\1\2\3", b"\4\5\6"], [odrg.stored_record(bytes([2]) * 360, 20)])
        files = support.example_show()
        files["show.json"] = support.show_text([{"id": 65535, "file": longest_name}], 255)
        files[longest_name] = bad_index
        printed = self.assert_as_the_reference(files, [support.line(T0, "off"), support.line(T0, "status")])
        reply = printed[-1][len("reply "):]
        # A bad file is quarantined and the show has no error. With the largest numbers and
        # the encoded limit of a host's name, the reply still fits into
        # 1,024 bytes: of a valid show with a file of 32 characters being checked and a seed
        # of ten digits, and of an invalid one with the longest reason text the core can
        # hold, 65 characters, which has neither.
        self.assertIsNone(json.loads(reply)["error"])
        common = len(reply) - len("null") + 1 + 2 * len("4294967295") + len(',"host":""') + 256
        valid = common + 3 * 10 + len('"' + "a" * 32 + '"')
        invalid = common + len('""') + 65
        self.assertLess(max(valid, invalid), 1024)


class BytesOfATransport(Commands):
    def fed(self, pieces, files=None):
        """`(line, reply)` for every line that the pieces complete, fed one after the other."""
        printed = self.assert_as_the_reference(files or support.example_show(), [support.fed(T0 + number, piece) for number, piece in enumerate(pieces)])
        self.assertEqual(len(printed) % 2, 0)
        answered = []
        for line, reply in zip(printed[0::2], printed[1::2]):
            self.assertTrue(line.startswith("fed") and reply.startswith("reply "))
            answered.append((bytes.fromhex(line[4:]), reply[len("reply "):]))
        return answered

    def test_every_newline_ends_a_line_and_every_line_gets_one_reply(self):
        answered = self.fed([b"on\noff\r\nbogus\n\n\r\nbrightness 9\n"])
        self.assertEqual(
            answered,
            [(b"on", OK), (b"off", OK), (b"bogus", refused("unknown-command")), (b"", refused("unknown-command")), (b"", refused("unknown-command")), (b"brightness 9", OK)],
        )

    def test_a_line_split_over_several_calls(self):
        answered = self.fed([b"bri", b"", b"ghtness", b" 4", b"2", b"\r", b"\n", b"sta", b"tus\nplay", b" 2\nstatus\n"])
        self.assertEqual([line for line, _ in answered], [b"brightness 42", b"status", b"play 2", b"status"])
        self.assertEqual(answered[0][1], OK)
        self.assertEqual(json.loads(answered[1][1])["brightness"], 42)
        self.assertEqual(answered[2][1], OK)
        self.assertEqual((json.loads(answered[3][1])["playing"], json.loads(answered[3][1])["animation"]), ("all", 2))

    def test_bytes_without_a_newline_give_no_reply(self):
        self.assertEqual(self.fed([b"status", b"\r", b" on"]), [])

    def test_one_byte_at_a_time(self):
        text = b"off\r\nstatus\nplay 9\n"
        answered = self.fed([bytes([value]) for value in text])
        self.assertEqual([line for line, _ in answered], [b"off", b"status", b"play 9"])
        self.assertEqual(answered[2][1], refused("unknown-id"))
        self.assertIs(json.loads(answered[1][1])["on"], False)

    def test_10000_bytes_without_a_newline_then_a_newline_and_a_valid_command(self):
        answered = self.fed([b"z" * 10000, b"\non\n"])
        self.assertEqual(answered, [(b"z" * 2048, refused("line-too-long")), (b"on", OK)])
        answered = self.fed([b"q" * 4000] + [b"q" * 3000, b"q" * 3000 + b"\n", b"off\r\n"])
        self.assertEqual(answered, [(b"q" * 2048, refused("line-too-long")), (b"off", OK)])
        answered = self.fed([b"w" * 70000, b"\r\n", b"status\n"])
        self.assertEqual(answered[0], (b"w" * 2048, refused("line-too-long")))
        self.assertEqual(answered[1][0], b"status")

    def test_lines_of_2048_and_2049_characters(self):
        longest = b"brightness " + b"0" * 2034 + b"123"
        one_more = b"brightness " + b"0" * 2035 + b"123"
        self.assertEqual((len(longest), len(one_more)), (2048, 2049))
        answered = self.fed([longest + b"\n", longest + b"\r\n", one_more + b"\n", one_more + b"\r\n", longest + b"\r\r\n", longest + b" \n", b"status\n"])
        self.assertEqual(
            answered[:6],
            [
                (longest, OK),
                (longest, OK),
                (one_more[:2048], refused("line-too-long")),
                (one_more[:2048], refused("line-too-long")),
                (longest, refused("line-too-long")),
                (longest, refused("line-too-long")),
            ],
        )
        self.assertEqual(json.loads(answered[6][1])["brightness"], 123)

    def test_a_line_of_2048_characters_that_arrives_in_pieces(self):
        longest = b"brightness " + b"0" * 2035 + b"77"
        self.assertEqual(len(longest), 2048)
        for size in (1, 7, 256, 2047, 2048):
            pieces = [longest[at:at + size] for at in range(0, len(longest), size)] + [b"\r", b"\n", b"status\n"]
            answered = self.fed(pieces)
            self.assertEqual(answered[0], (longest, OK), size)
            self.assertEqual(json.loads(answered[1][1])["brightness"], 77, size)

    def test_a_long_line_does_not_spoil_the_line_after_it(self):
        answered = self.fed([b"x" * 2049 + b"\n" + b"play 2\n" + b"y" * 2050 + b"\r\n" + b"status\n"])
        self.assertEqual([line for line, _ in answered], [b"x" * 2048, b"play 2", b"y" * 2048, b"status"])
        self.assertEqual((json.loads(answered[3][1])["playing"], json.loads(answered[3][1])["animation"]), ("all", 2))

    def test_bytes_of_every_value_are_taken_as_they_are(self):
        answered = self.fed([bytes(range(256))])
        self.assertEqual(answered, [(bytes(range(10)), refused("unknown-command"))])
        answered = self.fed([bytes(range(11, 256)) + b"\n", b"\x00\n", b"on\x00\n", b"\xff\xfe\n"])
        self.assertEqual([reply for _, reply in answered], [refused("unknown-command")] * 4)
        self.assertEqual(answered[0][0], bytes(range(11, 256)))
        every_value = bytes(value for value in range(256) if value != 10) * 9
        answered = self.fed([every_value[:2049] + b"\n"])
        self.assertEqual(answered, [(every_value[:2048], refused("line-too-long"))])

    def test_bytes_and_whole_lines_can_be_mixed(self):
        script = [support.fed(T0, b"brightn"), support.line(T0 + 1, "off"), support.fed(T0 + 2, b"ess 77\n"), support.line(T0 + 3, "status")]
        printed = self.assert_as_the_reference(support.example_show(), script)
        self.assertEqual(printed[0], f"reply {OK}")
        self.assertEqual(bytes.fromhex(printed[1][4:]), b"brightness 77")
        state = json.loads(printed[3][len("reply "):])
        self.assertEqual((state["on"], state["brightness"]), (False, 77))


if __name__ == "__main__":
    unittest.main()

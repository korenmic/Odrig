import json
import unittest

from . import support
from .test_playback import T0, every_20_ms, polls, refreshes

DARK = {1: bytes(540), 2: bytes(540)}
HELLO_MS = 5100


def hello_show(**more):
    """Hello world playing from power-on at full brightness, with more files beside it."""
    files = support.example_show()
    files["show.json"] = support.show_text([{"id": 1, "file": "hello.odrg"}, {"id": 2, "file": "dvd.odrg"}], 255, 1)
    for name, content in more.items():
        files[name.replace("_", ".")] = content
    return files


def asked_at(time, text):
    return support.line(T0 + time, text)


class FailureWhilePlaying(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        produced, _ = refreshes(support.start(hello_show(), every_20_ms(600)).lines)
        cls.undisturbed = {time - T0: legs for time, legs in produced}

    def play(self, options, files=None, last=12000, extra=()):
        """Polls every 20 ms with the host's options and asks for the state at the end.

        Returns the refreshes by time, the log lines with the time of the poll before
        each, and the replies to `status`, `play 1` and `status`.
        """
        script = every_20_ms(last // 20) + list(extra) + [asked_at(last, "status"), asked_at(last, "play 1"), asked_at(last, "status")]
        script += polls([T0 + last, T0 + last + 20])
        run = support.start(files or hello_show(), script, options)
        self.assertIsNone(run.error)
        logs = []
        clock = None
        for line in run.lines:
            if line.startswith("refresh "):
                clock = int(line.split()[1]) - T0
            elif line.startswith("log "):
                logs.append((clock, line[4:]))
        produced, idle = refreshes([line for line in run.lines if line.startswith(("refresh", "data", "idle"))])
        self.assertEqual(idle, [])
        replies = [line[len("reply "):] for line in run.lines if line.startswith("reply ")]
        return {time - T0: legs for time, legs in produced}, logs, replies

    def assert_ended(self, shown, logs, replies, text, first_dark, last=12000):
        """The show ended with this text at the refresh of this time: every refresh before
        it is the undisturbed one, and it and every later one is dark."""
        # The core gives the text to the host's log during the poll that fails, so it is
        # printed after the refresh before it.
        self.assertEqual(logs, [(first_dark - 20 if first_dark else None, text)])
        for time in sorted(shown):
            if time < first_dark:
                self.assertEqual(shown[time], self.undisturbed[time], f"at {time} ms")
            else:
                self.assertEqual(shown[time], DARK, f"at {time} ms")
        self.assertIn(last + 20, shown)
        before, played, after = replies[-3:]
        fps = 50 if last >= 1000 else 0
        expected = {"ok": True, "on": True, "brightness": 255, "playing": None, "animation": None, "fps": fps, "error": text, "width": 60, "height": 6, "seed": None}
        self.assertEqual(json.loads(before), expected)
        self.assertEqual(played, '{"ok":false,"error":"show-invalid"}')
        self.assertEqual(json.loads(after), expected)

    def test_a_file_removed_before_the_next_loop(self):
        shown, logs, replies = self.play(["--remove-after", "hello.odrg", "2"])
        self.assert_ended(shown, logs, replies, "file-missing hello.odrg", HELLO_MS)

    def test_a_file_removed_before_it_is_first_played(self):
        shown, logs, replies = self.play(["--remove-after", "hello.odrg", "1"], last=400)
        self.assert_ended(shown, logs, replies, "file-missing hello.odrg", 0, last=400)

    def test_a_read_failure_in_the_middle_of_a_file(self):
        shown, logs, replies = self.play(["--read-fails-after", "hello.odrg", "600", "2"])
        self.assertEqual(len(logs), 1)
        first_dark = logs[0][0] + 20
        # The file is read some way ahead of the frame on the LEDs, so the failure comes
        # in the second loop, before the frame that the failing bytes hold.
        self.assertGreater(first_dark, HELLO_MS)
        self.assertLess(first_dark, 2 * HELLO_MS)
        self.assert_ended(shown, logs, replies, "read-error hello.odrg", first_dark)

    def test_a_read_failure_at_the_start_of_a_file(self):
        for offset in (0, 5, 16):
            shown, logs, replies = self.play(["--read-fails-after", "hello.odrg", str(offset), "2"])
            self.assert_ended(shown, logs, replies, "read-error hello.odrg", HELLO_MS)

    def test_a_file_replaced_by_one_of_another_size(self):
        files = hello_show(small_odrg=support.clip(1, 59, 6))
        shown, logs, replies = self.play(["--swap-after", "hello.odrg", "2", "small.odrg"], files)
        self.assert_ended(shown, logs, replies, "size-mismatch hello.odrg", HELLO_MS)

    def test_a_file_replaced_by_a_shorter_one_of_the_same_size(self):
        short = support.clip(2, 60, 6, (20,) * 10)
        files = hello_show(short_odrg=short)
        shown, logs, replies = self.play(["--swap-after", "hello.odrg", "2", "short.odrg"], files)
        self.assertEqual(logs, [(HELLO_MS + 180, "file-malformed hello.odrg truncated")])
        # The ten frames of the shorter file are shown, and then a record is missing.
        alone = hello_show(short_odrg=short)
        alone["show.json"] = support.show_text([{"id": 1, "file": "short.odrg"}], 255, 1)
        produced, _ = refreshes(support.start(alone, every_20_ms(10)).lines)
        for step, (_, legs) in enumerate(produced):
            self.assertEqual(shown[HELLO_MS + 20 * step], legs, f"frame {step} of the shorter file")
            self.assertNotEqual(legs, DARK)
        for time in sorted(shown):
            if time < HELLO_MS:
                self.assertEqual(shown[time], self.undisturbed[time], f"at {time} ms")
            elif time >= HELLO_MS + 200:
                self.assertEqual(shown[time], DARK, f"at {time} ms")
        state = json.loads(replies[-1])
        self.assertEqual((state["error"], state["playing"]), ("file-malformed hello.odrg truncated", None))
        self.assertEqual(replies[-2], '{"ok":false,"error":"show-invalid"}')

    def test_a_file_replaced_by_one_that_breaks_its_format(self):
        hello = support.example_show()["hello.odrg"]
        cases = (
            (b"ODRZ" + hello[4:], "bad-magic", HELLO_MS),
            (hello[:16] + b"\x07" + hello[17:], "bad-deflate", HELLO_MS),
            (b"", "truncated", HELLO_MS),
        )
        for content, reason, first_dark in cases:
            with self.subTest(reason=reason):
                shown, logs, replies = self.play(["--swap-after", "hello.odrg", "2", "other.odrg"], hello_show(other_odrg=content))
                self.assert_ended(shown, logs, replies, f"file-malformed hello.odrg {reason}", first_dark)

    def test_a_file_replaced_by_a_longer_one_of_the_same_size_plays_on(self):
        longer = support.clip(3, 60, 6, (20,) * 400)
        shown, logs, replies = self.play(["--swap-after", "hello.odrg", "2", "longer.odrg"], hello_show(longer_odrg=longer))
        self.assertEqual(logs, [])
        self.assertEqual(json.loads(replies[-1])["error"], None)
        self.assertNotIn(DARK, shown.values())
        # It loops where the file checked at startup ended.
        self.assertEqual(shown[2 * HELLO_MS], shown[HELLO_MS])
        self.assertNotEqual(shown[HELLO_MS], self.undisturbed[0])

    def test_a_failure_while_the_leds_are_switched_off(self):
        extra = [asked_at(12000, "on")]
        script_off = [asked_at(0, "off")]
        script = script_off + every_20_ms(600) + extra + [asked_at(12000, "status")] + polls([T0 + 12000])
        run = support.start(hello_show(), script, ["--remove-after", "hello.odrg", "2"])
        state = json.loads(run.lines[-4][len("reply "):])
        self.assertEqual((state["on"], state["playing"], state["error"]), (True, None, "file-missing hello.odrg"))
        self.assertIn("log file-missing hello.odrg", run.lines)
        produced, _ = refreshes([line for line in run.lines if line.startswith(("refresh", "data"))])
        self.assertEqual({tuple(sorted(legs.items())) for _, legs in produced}, {tuple(sorted(DARK.items()))})

    def test_a_failure_in_one_animation_of_a_cycle_ends_the_show(self):
        files = support.example_show()
        files["show.json"] = support.show_text(json.loads(files["show.json"])["items"], 255, 3)
        script = every_20_ms(1600) + [asked_at(32000, "status"), asked_at(32000, "play 1"), asked_at(32000, "play 3")]
        run = support.start(files, script, ["--remove-after", "dvd.odrg", "1"])
        produced, _ = refreshes([line for line in run.lines if line.startswith(("refresh", "data"))])
        shown = {time - T0: legs for time, legs in produced}
        for time in range(0, 15000, 20):
            self.assertEqual(shown[time], self.undisturbed[time % HELLO_MS], f"at {time} ms")
        for time in range(15000, 32000, 20):
            self.assertEqual(shown[time], DARK, f"at {time} ms")
        replies = [line[len("reply "):] for line in run.lines if line.startswith("reply ")]
        state = json.loads(replies[0])
        self.assertEqual((state["playing"], state["animation"], state["error"]), (None, None, "file-missing dvd.odrg"))
        self.assertEqual(replies[1:], ['{"ok":false,"error":"show-invalid"}'] * 2)

    def test_after_a_failure_no_file_is_opened_and_the_reason_stays(self):
        script = every_20_ms(600) + [asked_at(12000, "play 1"), asked_at(12000, "play 2"), "error"]
        run = support.start(hello_show(), script, ["--remove-after", "hello.odrg", "2", "--trace-files"])
        opened = [line for line in run.lines if line.startswith("open ")]
        self.assertEqual(opened, ["open hello.odrg 1", "open hello.odrg 0"])
        self.assertEqual(run.lines[-1], "error file-missing hello.odrg")
        self.assertEqual(len([line for line in run.lines if line.startswith("log ")]), 1)

    def test_the_other_commands_work_after_a_failure(self):
        script = every_20_ms(300) + [asked_at(6000, "off"), asked_at(6000, "brightness 9"), asked_at(6000, "status"), asked_at(6000, "on"), asked_at(6000, "status")]
        run = support.start(hello_show(), script, ["--remove-after", "hello.odrg", "2"])
        replies = [line[len("reply "):] for line in run.lines if line.startswith("reply ")]
        self.assertEqual(replies[0], '{"ok":true}')
        self.assertEqual(replies[1], '{"ok":true}')
        self.assertEqual(
            json.loads(replies[2]),
            {"ok": True, "on": False, "brightness": 9, "playing": None, "animation": None, "fps": 50, "error": "file-missing hello.odrg", "width": 60, "height": 6, "seed": None},
        )
        self.assertIs(json.loads(replies[4])["on"], True)


if __name__ == "__main__":
    unittest.main()

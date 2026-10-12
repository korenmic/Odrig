import json
import unittest

from . import support
from .test_playback import T0, Playback, refreshes

LONG_LINE = "brightness " + "1" * 2038

# What happens besides the polls, by milliseconds after power-on. The cycle of the example
# show, item 3, is played at 7,000 ms and changes turns at 22,000 and at 37,000 ms.
EVENTS = {
    0: ["status"],
    1000: ["brightness 255", "status"],
    2000: ["brightness 1", "status"],
    2500: ["brightness 0"],
    3000: ["brightness 128", "status"],
    4000: ["play 2", "status"],
    5000: ["play 3"],
    5010: ["status"],
    7000: ["play 3", "status"],
    8000: ["bogus", "play", "play 99", LONG_LINE, "brightness 256", "", "play 0", "PLAY 1", "status"],
    9000: [b"sta", b"tus\r\nbright", b"ness 200\n", b"z" * 3000, b"\non\n"],
    12000: ["status", "brightness 128"],
    21000: ["off", "status"],
    22010: ["status"],
    23000: ["on", "status"],
    30000: ["play 4", "on 1", "off ", " off"],
    36990: ["status"],
    37010: ["status"],
    37500: ["off", "brightness 255", "on", "play 1", "status"],
}
LAST = 38000


def scripted_session():
    """The input lines of the session: a poll every 20 ms and the events at their times."""
    script = []
    events = dict(EVENTS)
    for time in range(0, LAST, 10):
        for event in events.pop(time, ()):
            if isinstance(event, bytes):
                script.append(support.fed(T0 + time, event))
            else:
                script.append(support.line(T0 + time, event))
        if time % 20 == 0:
            script.append(f"poll {T0 + time}")
    assert not events
    return script


def replies(printed):
    return [line[len("reply "):] for line in printed if line.startswith("reply ")]


class ScriptedSession(Playback):
    def test_the_session_holds_what_it_is_meant_to_hold(self):
        lines = [event for events in EVENTS.values() for event in events if isinstance(event, str)]
        for command in ("play", "on", "off", "brightness", "status"):
            self.assertTrue(any(line.split(" ")[0] == command for line in lines), command)
        for brightness in (0, 1, 128, 255):
            self.assertIn(f"brightness {brightness}", lines)
        self.assertEqual(lines.count("play 3"), 2)
        self.assertEqual(len(LONG_LINE), 2049)

    def test_on_the_example_show_every_reply_and_every_refresh_is_the_reference_players(self):
        script = scripted_session()
        printed = self.assert_as_the_reference(support.example_show(), script)
        produced, idle = refreshes([line for line in printed if line.startswith(("refresh", "data", "idle"))])
        self.assertEqual(len(produced), LAST // 20)
        self.assertEqual(idle, [])

        answers = replies(printed)
        codes = {json.loads(answer).get("error") for answer in answers if '"ok":false' in answer}
        self.assertEqual(codes, {"line-too-long", "unknown-command", "bad-argument", "unknown-id"})
        # The state at the time of each `status` given as a whole line: its reply is the
        # one that does not follow a line handed back from bytes.
        to_lines = [line for number, line in enumerate(printed) if line.startswith("reply ") and not printed[number - 1].startswith("fed ")]
        asked = [line for line in script if line.startswith("line ")]
        self.assertEqual(len(to_lines), len(asked))
        by_time = {}
        for line, reply in zip(asked, to_lines):
            if line.endswith(" status"):
                by_time[int(line.split()[1]) - T0] = json.loads(reply[len("reply "):])
        # The cycle changes turns twice, at 22,000 and at 37,000 ms, the first time while
        # the LEDs are switched off.
        self.assertEqual(by_time[7000]["animation"], 1)
        self.assertEqual((by_time[21000]["on"], by_time[21000]["animation"]), (False, 1))
        self.assertEqual((by_time[22010]["on"], by_time[22010]["animation"]), (False, 2))
        self.assertEqual((by_time[23000]["on"], by_time[23000]["animation"]), (True, 2))
        self.assertEqual(by_time[36990]["animation"], 2)
        self.assertEqual(by_time[37010]["animation"], 1)
        self.assertEqual(by_time[37500]["playing"], 1)
        self.assertEqual({state["fps"] for time, state in by_time.items() if time >= 1000}, {50})

        shown = {time - T0: legs for time, legs in produced}
        dark = {1: bytes(540), 2: bytes(540)}
        self.assertEqual(shown[2500], dark)
        self.assertEqual(shown[21000], dark)
        self.assertEqual(shown[22000], dark)
        self.assertEqual(shown[22980], dark)
        self.assertNotEqual(shown[23000], dark)
        self.assertNotEqual(shown[36980], shown[37000])
        # The second turn starts the first animation again from its first frame.
        self.assertEqual(shown[37000], shown[7000])
        self.assertEqual(shown[37020], shown[7020])

    def test_on_an_invalid_show_every_reply_and_every_refresh_is_the_reference_players(self):
        files = support.example_show()
        del files["dvd.odrg"]
        printed = self.assert_as_the_reference(files, scripted_session())
        produced, _ = refreshes([line for line in printed if line.startswith(("refresh", "data", "idle"))])
        self.assertEqual({tuple(sorted(legs.items())) for _, legs in produced}, {((1, bytes(540)), (2, bytes(540)))})
        answers = replies(printed)
        codes = {json.loads(answer).get("error") for answer in answers if '"ok":false' in answer}
        self.assertEqual(codes, {"line-too-long", "unknown-command", "bad-argument", "show-invalid"})
        states = [json.loads(answer) for answer in answers if '"on"' in answer]
        self.assertEqual({state["error"] for state in states}, {"file-missing dvd.odrg"})
        self.assertEqual({state["playing"] for state in states}, {None})

    def test_the_same_session_twice_gives_the_same_lines(self):
        script = scripted_session()[:1500]
        first = support.start(support.example_show(), script).lines
        second = support.start(support.example_show(), script).lines
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

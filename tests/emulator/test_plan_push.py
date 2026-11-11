"""The push of the plan on the emulator's line port: each connection has a serial way of its
own, is given the `#plan` lines of its way between the replies to its lines, and its push
ends with it."""

import json
import time
import unittest

from . import support


class Reader:
    """A connection to the line port read line by line: the replies, and the `#plan` lines
    between them."""

    def __init__(self, address):
        self.connection = support.Lines(address)
        self.buffer = b""

    def close(self):
        self.connection.close()

    def line(self, seconds=5):
        """The next whole line, without its newline, or `None` when none comes in time."""
        deadline = time.monotonic() + seconds
        while b"\n" not in self.buffer:
            left = deadline - time.monotonic()
            piece = self.connection.read_lines(1, left) if left > 0 else b""
            if not piece:
                return None
            self.buffer += piece
        line, self.buffer = self.buffer.split(b"\n", 1)
        return line

    def ask(self, line):
        """Sends one line; gives its reply, and the plans of the `#plan` lines before it."""
        self.connection.write(line.encode("ascii") + b"\n")
        plans = []
        while True:
            received = self.line()
            if received is None:
                raise AssertionError(f"no reply to {line!r}")
            if received.startswith(b"#plan "):
                plans.append(json.loads(received[len(b"#plan "):]))
            else:
                return json.loads(received), plans

    def plans(self, seconds):
        """The plans of the `#plan` lines that come within a time; any other line fails."""
        found = []
        while True:
            received = self.line(seconds)
            if received is None:
                return found
            assert received.startswith(b"#plan "), received
            found.append(json.loads(received[len(b"#plan "):]))
            seconds = 0.3


class ThePushOfTheLinePort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packed = support.example_show()
        cls.folder = cls.packed.__enter__()
        cls.emulator = support.Emulator(cls.folder, tcp_port=0)

    @classmethod
    def tearDownClass(cls):
        cls.emulator.stop()
        cls.packed.__exit__(None, None, None)

    def setUp(self):
        # The connections of the test before have let their ways go.
        time.sleep(0.3)
        self.readers = []

    def tearDown(self):
        for reader in self.readers:
            reader.close()

    def reader(self):
        reader = Reader(self.emulator.tcp)
        self.readers.append(reader)
        return reader

    def test_a_connection_with_its_push_on_is_given_the_plan_at_once_and_after_a_change(self):
        one, two = self.reader(), self.reader()
        self.assertEqual(one.ask("plan push on"), ({"ok": True}, []))
        (first,) = one.plans(2)
        self.assertIn("items", first)
        self.assertTrue(two.ask("status")[0]["ok"])
        self.assertEqual(two.ask("play 2"), ({"ok": True}, []))
        later = one.plans(2)
        self.assertTrue(later)
        self.assertGreater(later[-1]["version"], first["version"])
        self.assertEqual(two.plans(0.5), [])

    def test_the_lines_of_a_push_come_between_replies(self):
        one = self.reader()
        replies = [one.ask(line) for line in ("plan push on", "status", "plan push off")]
        self.assertEqual(replies[0], ({"ok": True}, []))
        self.assertTrue(replies[1][0]["ok"])
        self.assertEqual(len(replies[1][1]) + len(replies[2][1]), 1)
        self.assertEqual(replies[2][0], {"ok": True})
        self.assertEqual(one.plans(0.5), [])

    def test_a_connection_that_closes_ends_its_push(self):
        one = self.reader()
        self.assertEqual(one.ask("plan push on")[0], {"ok": True})
        self.assertEqual(len(one.plans(2)), 1)
        one.close()
        time.sleep(0.3)
        again, other = self.reader(), self.reader()
        self.assertEqual(other.ask("play 1")[0], {"ok": True})
        self.assertEqual(again.plans(0.5), [])

    def test_over_http_the_push_is_unsupported(self):
        for line in (b"plan push on", b"plan push off"):
            answer = self.emulator.request(body=line)
            self.assertEqual(json.loads(answer.body), {"ok": False, "error": "unsupported"})

    def test_a_connection_past_the_seventh_has_no_way(self):
        opened = [self.reader() for _ in range(8)]
        answers = [reader.ask("plan push on")[0] for reader in opened]
        self.assertEqual(answers[:7], [{"ok": True}] * 7)
        self.assertEqual(answers[7], {"ok": False, "error": "unsupported"})


if __name__ == "__main__":
    unittest.main()

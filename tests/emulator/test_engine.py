import json
import re
import threading
import time
import unittest

from emulator import binding, engine, host, hub
from tests.core.support import ReferencePlayer

from . import support


class OnTheExampleShow(unittest.TestCase):
    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        files = host.FolderHost(self.folder)
        self.addCleanup(files.close)
        self.hub = hub.Hub()
        self.engine = engine.Engine(binding.Core(support.LIBRARY, files), self.hub)
        self.engine.tick()

    def test_a_tick_hands_the_refresh_and_its_timestamp_to_the_hub(self):
        ms, frame = self.hub.newest_refresh()
        self.assertEqual(ms, self.engine.t0)
        player = ReferencePlayer(support.files_of(self.folder))
        self.assertEqual(frame, b"".join(rgb for _, rgb in player.poll(ms)))

    def test_a_line_is_answered_and_entered_in_the_log_with_its_transport(self):
        reply = self.engine.line(b"play 2\r\n", "http")
        self.assertEqual(reply, b'{"ok":true}\n')
        (entry,) = self.hub.entries()
        self.assertEqual({name: entry[name] for name in ("seq", "transport", "line", "cut", "reply")},
                         {"seq": 1, "transport": "http", "line": "play 2", "cut": False, "reply": '{"ok":true}'})
        self.assertRegex(entry["time"], r"\A[0-2][0-9]:[0-5][0-9]:[0-5][0-9]\.[0-9]{3}\Z")
        self.assertIsInstance(entry["ms"], int)
        self.assertGreaterEqual(entry["ms"], self.engine.t0)

    def test_fed_bytes_give_an_entry_for_every_line_they_finish(self):
        self.assertEqual(self.engine.feed(b"brigh", "serial"), b"")
        self.assertEqual(self.hub.entries(), [])
        replies = self.engine.feed(b"tness 9\r\nplay 99\nsta", "serial")
        self.assertEqual(replies, b'{"ok":true}\n{"ok":false,"error":"unknown-id"}\n')
        self.assertEqual([(entry["seq"], entry["transport"], entry["line"], entry["reply"]) for entry in self.hub.entries()], [
            (1, "serial", "brightness 9", '{"ok":true}'),
            (2, "serial", "play 99", '{"ok":false,"error":"unknown-id"}'),
        ])

    def test_the_line_of_an_entry_is_the_one_the_byte_entry_of_the_core_hands_back(self):
        player = ReferencePlayer(support.files_of(self.folder))
        lines = [b"status", b"status\n", b"on\r\n", b"on\r", b"off\r\r\n", b"x" * 2048, b"x" * 2048 + b"\r\n", b"y" * 2049, b"z" * 4096, b"", b"\n", b"\r\n", b" on ", b"v" * 200, b"w" * 201]
        for line in lines:
            self.engine.line(line, "http")
        handed_back = [player.feed(0, line if line.endswith(b"\n") else line + b"\n")[0][0] for line in lines]
        entries = self.hub.entries()
        self.assertEqual([entry["line"] for entry in entries], [hub.shown(line[:200]) for line in handed_back])
        self.assertEqual([entry["length"] for entry in entries], [len(line) for line in handed_back])
        self.assertEqual([entry["cut"] for entry in entries], [len(line) == 2048 and b"x" not in line for line in handed_back])
        self.assertEqual([entry["line"] for entry in entries[:5]], ["status", "status", "on", "on", "off\\x0D"])
        self.assertEqual((entries[7]["line"], entries[7]["length"], entries[7]["cut"]), ("y" * 200, 2048, True))
        self.assertEqual((entries[8]["line"], entries[8]["length"], entries[8]["cut"]), ("z" * 200, 2048, True))
        self.assertEqual((entries[13]["line"], entries[13]["length"], entries[13]["cut"]), ("v" * 200, 200, False))
        self.assertEqual((entries[14]["line"], entries[14]["length"], entries[14]["cut"]), ("w" * 200, 201, False))

    def test_a_newline_inside_the_body_of_a_request_is_part_of_its_one_line(self):
        self.assertEqual(self.engine.line(b"on\noff\n", "http"), b'{"ok":false,"error":"unknown-command"}\n')
        self.assertEqual(self.engine.line(b"play 2\n\n", "http"), b'{"ok":false,"error":"bad-argument"}\n')
        self.assertEqual([entry["line"] for entry in self.hub.entries()], ["on\\x0Aoff", "play 2\\x0A"])
        self.engine.refresh_status()
        self.assertEqual(json.loads(self.hub.latest_status())["on"], True)

    def test_the_status_is_asked_for_after_every_command_that_arrived(self):
        self.engine.feed(b"brightness 11\noff\n", "serial")
        self.assertEqual((json.loads(self.hub.latest_status())["brightness"], json.loads(self.hub.latest_status())["on"]), (11, False))
        self.engine.line(b"on", "http")
        self.assertEqual(json.loads(self.hub.latest_status())["on"], True)
        self.engine.feed(b"brightness 2", "serial")
        self.assertEqual(json.loads(self.hub.latest_status())["brightness"], 11)
        self.assertEqual(len(self.hub.entries()), 3)

    def test_a_connection_starts_with_hello_the_kept_entries_and_the_latest_status(self):
        self.engine.line(b"brightness 1", "http")
        self.engine.feed(b"off\n", "serial")
        connection = self.hub.connect({"legs": [[1, 1, 180]], "error": None})
        self.addCleanup(self.hub.disconnect, connection)
        events = connection.take(0)
        self.assertEqual([kind for kind, _ in events], ["hello", "log", "log", "status"])
        self.assertEqual(json.loads(events[0][1]), {"legs": [[1, 1, 180]], "error": None})
        self.assertEqual([json.loads(data)["line"] for kind, data in events if kind == "log"], ["brightness 1", "off"])
        self.assertEqual(json.loads(events[3][1])["on"], False)
        self.assertEqual(connection.take(0), [])

    def test_a_connection_keeps_every_log_and_status_event_and_only_the_newest_refresh(self):
        connection = self.hub.connect({})
        self.addCleanup(self.hub.disconnect, connection)
        connection.take(0)
        for number in range(30):
            self.engine.line(b"brightness %d" % number, "http")
            self.hub.refresh(1000 + number, bytes([number]) * 3)
        events = connection.take(0)
        self.assertEqual([kind for kind, _ in events], ["log", "status"] * 30 + ["frame"])
        self.assertEqual([json.loads(data)["line"] for kind, data in events if kind == "log"], [f"brightness {number}" for number in range(30)])
        self.assertEqual(events[-1], ("frame", "1029 HR0d"))
        self.assertEqual(connection.take(0), [])

    def test_a_closed_connection_gives_none_and_is_told_nothing_more(self):
        connection = self.hub.connect({})
        self.hub.disconnect(connection)
        self.assertIsNone(connection.take(0))
        self.engine.line(b"on", "http")
        self.assertIsNone(connection.take(0))
        other = self.hub.connect({})
        self.hub.close()
        self.assertIsNone(other.take(5))

    def test_a_line_above_the_limit_is_entered_with_its_first_200_characters_the_length_read_and_marked_as_cut(self):
        long_line = b"play " + b"7" * 2075
        self.engine.feed(long_line + b"\n", "serial")
        self.engine.line(long_line, "http")
        self.assertEqual(len(self.hub.entries()), 2)
        for entry in self.hub.entries():
            self.assertEqual((entry["line"], entry["length"], entry["cut"]), (long_line[:200].decode("ascii"), 2048, True))
            self.assertEqual(entry["reply"], '{"ok":false,"error":"line-too-long"}')

    def test_a_line_of_300_characters_is_entered_with_its_first_200_and_its_length(self):
        line = b"play " + b"7" * 295
        self.engine.feed(line + b"\r\n", "serial")
        self.engine.line(line + b"\n", "http")
        self.assertEqual(len(self.hub.entries()), 2)
        for entry in self.hub.entries():
            self.assertEqual((entry["line"], entry["length"], entry["cut"]), (line[:200].decode("ascii"), 300, False))
            self.assertEqual(entry["reply"], '{"ok":false,"error":"bad-argument"}')

    def test_bytes_outside_printable_ascii_are_entered_as_escapes(self):
        self.engine.feed(b"pl\x00y \xff\x7f\t~\n", "serial")
        self.assertEqual(self.hub.entries()[0]["line"], "pl\\x00y \\xFF\\x7F\\x09~")

    def test_the_hub_keeps_the_last_500_entries(self):
        for number in range(503):
            self.engine.line(b"brightness %d" % (number % 256), "http")
        entries = self.hub.entries()
        self.assertEqual(len(entries), 500)
        self.assertEqual((entries[0]["seq"], entries[-1]["seq"]), (4, 503))
        self.assertEqual(entries[0]["line"], "brightness 3")

    def test_the_status_for_the_page_is_the_reply_of_the_core_and_is_not_logged(self):
        self.assertIsNone(self.hub.latest_status())
        self.engine.refresh_status()
        self.assertEqual(json.loads(self.hub.latest_status())["brightness"], 128)
        self.assertEqual(self.hub.entries(), [])
        self.engine.line(b"brightness 42", "http")
        status = self.hub.latest_status()
        self.assertEqual(support.without_fps(status), {"ok": True, "on": True, "brightness": 42, "playing": 3, "animation": 1, "error": None, "width": 60, "height": 6})
        self.assertTrue(re.fullmatch(r"\{.*\}", status))
        self.assertEqual(len(self.hub.entries()), 1)


class OneCallAtATime(unittest.TestCase):
    class Core:
        """Stands in for the core and notices two calls at once and a time that goes back."""

        def __init__(self):
            self.inside = 0
            self.together = 0
            self.times = []
            self.calls = 0

        def enter(self, now):
            self.inside += 1
            self.together = max(self.together, self.inside)
            self.times.append(now)
            self.calls += 1
            time.sleep(0.0005)
            self.inside -= 1

        def poll(self, now):
            self.enter(now)
            return True

        def frame(self):
            return b"abc"

        def command(self, now, line):
            self.enter(now)
            return b'{"ok":true}\n'

        def feed(self, now, data):
            self.enter(now)
            return [(data.rstrip(b"\n"), b'{"ok":true}\n', False)]

    def test_calls_from_many_threads_reach_the_core_one_after_another_with_times_in_order(self):
        core = self.Core()
        running = engine.Engine(core, hub.Hub())
        actions = (running.tick, lambda: running.line(b"on", "http"), lambda: running.feed(b"off\n", "serial"), running.refresh_status)
        threads = [threading.Thread(target=lambda action=action: [action() for _ in range(40)]) for action in actions for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(core.calls, 120 + 2 * 120 + 2 * 120 + 120)
        self.assertEqual(core.together, 1)
        self.assertEqual(core.times, sorted(core.times))
        self.assertEqual(len(running.hub.entries()), 240)


if __name__ == "__main__":
    unittest.main()

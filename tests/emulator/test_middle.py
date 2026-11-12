"""The man in the middle of a mirror: every client's line goes to the board, one at a time
over a stream, and its reply back to that client alone; the board's other lines reach the
clients of the serial ways; a lost link ends every wait."""

import json
import threading
import time
import unittest
from unittest import mock

from emulator import app
from emulator.mirror import Mirror, link, middle

from . import support


class StandInLink:
    """Stands in for a stream link: keeps what is sent, and lets the test answer."""

    streamed = True
    kind = "tcp"

    def __init__(self, opens=True):
        self.name = "stand-in"
        self.replied = self.planned = self.heard = lambda line: None
        self.lost = lambda reason: None
        self.opens = opens
        self.opened = 0
        self.sent = []
        self._sent = threading.Condition()

    def open(self):
        self.opened += 1
        if not self.opens:
            raise link.Lost("stand-in: refused")

    def send(self, line):
        with self._sent:
            self.sent.append(line)
            self._sent.notify_all()

    def close(self):
        pass

    def wait_sent(self, count, seconds=5):
        with self._sent:
            self._sent.wait_for(lambda: len(self.sent) >= count, seconds)
            return list(self.sent)


class InThreads:
    """Lines sent from threads of their own, as clients send them; `results` holds each
    reply by the line's name."""

    def __init__(self):
        self.results = {}
        self.threads = []

    def send(self, how, line, **options):
        thread = threading.Thread(target=lambda: self.results.__setitem__(line, how(line, **options)))
        thread.start()
        self.threads.append(thread)

    def join(self):
        for thread in self.threads:
            thread.join(10)


def linked(test, stand_in):
    made = middle.Middle(stand_in)
    made.start()
    test.addCleanup(made.stop)
    deadline = time.monotonic() + 5
    while made.state != middle.LINKED and time.monotonic() < deadline:
        time.sleep(0.01)
    return made


class OverAStream(unittest.TestCase):
    def test_lines_go_one_at_a_time_in_order_and_each_reply_to_its_own_line(self):
        stand_in = StandInLink()
        made = linked(self, stand_in)
        clients = InThreads()
        clients.send(made.send, b"one")
        stand_in.wait_sent(1)
        clients.send(made.send, b"two")
        time.sleep(0.2)
        self.assertEqual(stand_in.sent, [b"one"])
        stand_in.replied(b'{"ok":true,"n":1}')
        self.assertEqual(stand_in.wait_sent(2), [b"one", b"two"])
        stand_in.replied(b'{"ok":true,"n":2}')
        clients.join()
        self.assertEqual(clients.results, {b"one": b'{"ok":true,"n":1}\n', b"two": b'{"ok":true,"n":2}\n'})

    def test_a_clients_line_goes_before_the_mirrors_own(self):
        stand_in = StandInLink()
        made = linked(self, stand_in)
        lines = InThreads()
        lines.send(made.send, b"first")
        stand_in.wait_sent(1)
        lines.send(made.ask, b"own")
        time.sleep(0.1)
        lines.send(made.send, b"client")
        time.sleep(0.1)
        for number in (1, 2, 3):
            stand_in.wait_sent(number)
            stand_in.replied(b'{"ok":true,"n":%d}' % number)
        lines.join()
        self.assertEqual(stand_in.sent, [b"first", b"client", b"own"])
        self.assertEqual(lines.results[b"own"], b'{"ok":true,"n":3}\n')

    def test_a_late_reply_is_dropped_and_never_given_to_the_next_line(self):
        stand_in = StandInLink()
        made = linked(self, stand_in)
        self.assertIsNone(made.send(b"slow", seconds=0.2))
        lines = InThreads()
        lines.send(made.send, b"next")
        time.sleep(0.2)
        self.assertEqual(stand_in.sent, [b"slow"])
        stand_in.replied(b'{"ok":true,"late":1}')
        self.assertEqual(stand_in.wait_sent(2), [b"slow", b"next"])
        stand_in.replied(b'{"ok":true,"n":2}')
        lines.join()
        self.assertEqual(lines.results, {b"next": b'{"ok":true,"n":2}\n'})

    def test_a_line_whose_client_stopped_waiting_is_waited_for_a_while_and_then_let_go(self):
        stand_in = StandInLink()
        with mock.patch.object(middle, "AFTER_SECONDS", 0.3):
            made = linked(self, stand_in)
            self.assertIsNone(made.send(b"never", seconds=0.1))
            lines = InThreads()
            lines.send(made.send, b"after")
            self.assertEqual(stand_in.wait_sent(2), [b"never", b"after"])
            stand_in.replied(b'{"ok":true}')
            lines.join()
        self.assertEqual(lines.results, {b"after": b'{"ok":true}\n'})

    def test_a_reply_that_no_line_waits_for_is_dropped(self):
        stand_in = StandInLink()
        made = linked(self, stand_in)
        stand_in.replied(b'{"ok":true,"stray":1}')
        lines = InThreads()
        lines.send(made.send, b"line")
        stand_in.wait_sent(1)
        stand_in.replied(b'{"ok":true,"n":1}')
        lines.join()
        self.assertEqual(lines.results, {b"line": b'{"ok":true,"n":1}\n'})

    def test_a_lost_link_ends_every_wait_and_is_opened_again(self):
        stand_in = StandInLink()
        told = []
        with mock.patch.object(middle, "RETRY_SECONDS", 0.1):
            made = linked(self, stand_in)
            made.watchers.append(lambda state, reason: told.append(state))
            lines = InThreads()
            lines.send(made.send, b"one")
            lines.send(made.send, b"two")
            stand_in.wait_sent(1)
            stand_in.lost("stand-in: gone")
            lines.join()
            self.assertEqual(lines.results, {b"one": None, b"two": None})
            deadline = time.monotonic() + 5
            while made.state != middle.LINKED and time.monotonic() < deadline:
                time.sleep(0.01)
        self.assertEqual(told[:2], [middle.LOST, middle.LINKED])
        self.assertEqual(stand_in.opened, 2)

    def test_a_link_that_cannot_be_opened_is_tried_again_every_2_seconds_and_lines_get_no_reply(self):
        self.assertEqual(middle.RETRY_SECONDS, 2.0)
        stand_in = StandInLink(opens=False)
        with mock.patch.object(middle, "RETRY_SECONDS", 0.1):
            made = middle.Middle(stand_in)
            made.start()
            self.addCleanup(made.stop)
            time.sleep(0.55)
            self.assertEqual(made.state, middle.WAITING)
            self.assertIn("refused", made.reason)
            self.assertIsNone(made.send(b"status", seconds=1))
        self.assertGreaterEqual(stand_in.opened, 4)
        self.assertEqual(stand_in.sent, [])

    def test_a_restart_ends_the_wait_of_the_line_on_the_link(self):
        stand_in = StandInLink()
        made = linked(self, stand_in)
        lines = InThreads()
        lines.send(made.send, b"lost in a restart")
        stand_in.wait_sent(1)
        made.restarted()
        lines.join()
        self.assertEqual(lines.results, {b"lost in a restart": None})


class StandInHttp:
    streamed = False
    kind = "http"

    def __init__(self):
        self.name = "stand-in"
        self.inside = 0
        self.most = 0
        self.fails = False
        self._lock = threading.Lock()

    def exchange(self, line, seconds):
        if self.fails:
            raise link.Lost("stand-in: refused")
        with self._lock:
            self.inside += 1
            self.most = max(self.most, self.inside)
        time.sleep(0.2)
        with self._lock:
            self.inside -= 1
        return b'{"ok":true,"line":"%s"}\n' % line


class OverHttp(unittest.TestCase):
    def test_each_line_is_a_request_of_its_own_and_they_may_go_together(self):
        stand_in = StandInHttp()
        made = middle.Middle(stand_in)
        made.start()
        lines = InThreads()
        for name in (b"a", b"b", b"c"):
            lines.send(made.send, name)
        lines.join()
        self.assertEqual(lines.results, {name: b'{"ok":true,"line":"%s"}\n' % name for name in (b"a", b"b", b"c")})
        self.assertEqual(stand_in.most, 3)
        self.assertEqual(made.state, middle.LINKED)

    def test_a_request_that_fails_gets_no_reply_and_says_the_link_is_lost(self):
        stand_in = StandInHttp()
        made = middle.Middle(stand_in)
        made.start()
        stand_in.fails = True
        self.assertIsNone(made.send(b"status"))
        self.assertEqual(made.state, middle.WAITING)
        stand_in.fails = False
        self.assertIsNotNone(made.send(b"status"))
        stand_in.fails = True
        self.assertIsNone(made.send(b"status"))
        self.assertEqual(made.state, middle.LOST)


class TheLinesOfAStream(unittest.TestCase):
    def test_a_reply_a_plan_and_every_other_line_go_their_own_ways(self):
        made = link.TcpLink("127.0.0.1:1")
        found = []
        made.replied = lambda line: found.append(("reply", line))
        made.planned = lambda line: found.append(("plan", line))
        made.heard = lambda line: found.append(("heard", line))
        for line in (b'{"ok":true}', b'#plan {"ok":true,"version":3}', b"#log 1.000 usb: host started", b"ESP-ROM:esp32s3-20210327", b"", b"[1,2]"):
            made._sort(line)
        self.assertEqual(found, [("reply", b'{"ok":true}'), ("plan", b'{"ok":true,"version":3}'), ("heard", b"#log 1.000 usb: host started"), ("heard", b"ESP-ROM:esp32s3-20210327"), ("heard", b"[1,2]")])


class TheWaysOfAMirror(unittest.TestCase):
    def test_the_boards_other_lines_wait_for_each_way_that_asked_since(self):
        mirror = Mirror("tcp", "127.0.0.1:1", support.ROOT, {})
        self.assertIsNone(mirror.heard_for(2))
        mirror.middle._heard(b"#log one")
        self.assertIsNone(mirror.heard_for(1))
        self.assertEqual(mirror.heard_for(2), b"#log one\n")
        mirror.middle._heard(b"#log two")
        self.assertEqual(mirror.heard_for(1), b"#log two\n")
        self.assertEqual(mirror.heard_for(2), b"#log two\n")
        self.assertIsNone(mirror.heard_for(0))
        mirror.way_ended(2)
        mirror.middle._heard(b"#log three")
        self.assertIsNone(mirror.heard_for(2))
        self.assertEqual(mirror.heard_for(1), b"#log three\n")


class AMirrorOfAnEmulator(unittest.TestCase):
    """An emulator as the board and another as its mirror, over the line port and over HTTP."""

    @classmethod
    def setUpClass(cls):
        cls.packed = support.example_show()
        cls.folder = cls.packed.__enter__()
        cls.board = support.Emulator(cls.folder, tcp_port=0)

    @classmethod
    def tearDownClass(cls):
        cls.board.stop()
        cls.packed.__exit__(None, None, None)

    def mirror(self, *option):
        mirrored = support.Emulator(self.folder, *option, checked=False)
        self.addCleanup(mirrored.stop)
        deadline = time.monotonic() + 15
        while True:
            try:
                if json.loads(mirrored.command("status"))["ok"]:
                    return mirrored
            except Exception:
                pass
            if time.monotonic() > deadline:
                raise AssertionError(f"the mirror never reached the board: {mirrored.lines}")
            time.sleep(0.1)

    def test_a_clients_line_reaches_the_board_and_the_boards_reply_comes_back(self):
        for option in (("--mirror-tcp", self.board.tcp), ("--mirror-http", f"127.0.0.1:{self.board.port}")):
            with self.subTest(option=option[0]):
                mirrored = self.mirror(*option)
                self.assertIn(f"mirror: {option[0][len('--mirror-'):]} {option[1]}", mirrored.lines)
                self.assertEqual(json.loads(mirrored.command("brightness 33")), {"ok": True})
                self.assertEqual(self.board.status()["brightness"], 33)
                self.assertEqual(json.loads(mirrored.command("brightness 90")), {"ok": True})
                self.assertEqual(self.board.status()["brightness"], 90)
                result = support.run_tool("--http", f"127.0.0.1:{mirrored.port}", "status")
                self.assertEqual((result.status, result.err), (0, ""))
                self.assertEqual(json.loads(result.out)["brightness"], 90)

    def test_the_line_port_of_a_mirror_carries_lines_to_the_board(self):
        mirrored = self.mirror("--mirror-tcp", self.board.tcp)
        target = support.line_target(mirrored)
        result = support.run_tool(*target, "brightness", "44")
        self.assertEqual((result.status, result.out, result.err), (0, '{"ok":true}\n', ""))
        self.assertEqual(self.board.status()["brightness"], 44)
        result = support.run_tool(*target, "play", "abc")
        self.assertEqual((result.status, result.out), (1, '{"ok":false,"error":"bad-argument"}\n'))
        support.run_tool(*target, "brightness", "90")

    def test_the_mirrors_log_lists_each_line_with_the_boards_reply(self):
        mirrored = self.mirror("--mirror-tcp", self.board.tcp)
        mirrored.command("play 99")
        with support.EventStream(mirrored.port) as stream:
            logged = support.of_kind(stream.read_until(lambda events: any(event.kind == "log" and "play 99" in event.data for event in events)), "log")
        entry = [entry for entry in logged if entry["line"] == "play 99"][-1]
        self.assertEqual((entry["transport"], entry["reply"]), ("http", '{"ok":false,"error":"unknown-id"}'))


class TheOptions(unittest.TestCase):
    def test_a_mirror_has_one_link_and_no_drive_and_is_no_recording(self):
        for argv in (["show", "--mirror-tcp", "127.0.0.1:1", "--drive", "d"],
                     ["show", "--mirror-port", "COM5", "--drive-folder", "d"],
                     ["show", "--mirror-http", "4.3.2.1", "--record", "out", "--seconds", "1"],
                     ["show", "--mirror-tcp", "127.0.0.1:1", "--mirror-http", "4.3.2.1"],
                     ["show", "--mirror-tcp", "no-port"]):
            result = support.run(*argv)
            self.assertEqual(result.status, 2, argv)
            self.assertIn("usage:", result.err)
        self.assertEqual(app.mirror_of(app.parse(["show", "--mirror-port", "COM5"])), ("serial", "COM5"))
        self.assertEqual(app.mirror_of(app.parse(["show", "--mirror-tcp", "127.0.0.1:8601"])), ("tcp", "127.0.0.1:8601"))
        self.assertEqual(app.mirror_of(app.parse(["show", "--mirror-http", "http://4.3.2.1"])), ("http", "http://4.3.2.1"))
        self.assertIsNone(app.mirror_of(app.parse(["show"])))

    def test_with_lan_the_warning_says_that_the_network_reaches_the_board_through_the_emulator(self):
        with support.example_show() as folder:
            mirrored = support.Emulator(folder, "--mirror-tcp", f"127.0.0.1:{support.free_port()}", "--lan", checked=False)
            result = mirrored.stop()
        self.assertIn(app.LAN_MIRROR_WARNING + "\n", result.err)
        self.assertNotIn(app.LAN_WARNING, result.err)
        self.assertIn("through this emulator to the board it mirrors", app.LAN_MIRROR_WARNING)


class ALostLink(unittest.TestCase):
    def test_a_client_over_http_gets_its_request_closed_when_the_board_is_gone(self):
        with support.example_show() as folder:
            board = support.Emulator(folder, tcp_port=0)
            try:
                mirrored = support.Emulator(folder, "--mirror-tcp", board.tcp, checked=False)
                self.addCleanup(mirrored.stop)
                deadline = time.monotonic() + 15
                while support.run_tool("--http", f"127.0.0.1:{mirrored.port}", "status").status != 0:
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.1)
            finally:
                board.stop()
            result = support.run_tool("--http", f"127.0.0.1:{mirrored.port}", "status")
            self.assertEqual(result.status, 3)
            self.assertRegex(result.err, r"\Aerror: unreachable: ")


if __name__ == "__main__":
    unittest.main()

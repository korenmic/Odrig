import json
import socket
import threading
import time
import unittest

from odrigctl import cli, client
from tests.core.support import ReferencePlayer

from . import support

OK = '{"ok":true}\n'


class Target:
    """Stands in for a target that takes lines over TCP: keeps what it is sent and, once a
    line is whole, sends the pieces it was given, a short time apart. Then it closes the
    connection, or keeps it open and silent."""

    def __init__(self, *pieces, stays_open=False):
        self.pieces = pieces
        self.stays_open = stays_open
        self.received = []
        self._listener = socket.socket()
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen()
        self.address = f"127.0.0.1:{self._listener.getsockname()[1]}"
        self._ended = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        while not self._ended.is_set():
            try:
                connection, _ = self._listener.accept()
            except OSError:
                return
            with connection:
                data = b""
                while b"\n" not in data:
                    piece = connection.recv(4096)
                    if not piece:
                        break
                    data += piece
                self.received.append(data)
                for piece in self.pieces:
                    connection.sendall(piece)
                    time.sleep(0.03)
                if self.stays_open:
                    self._ended.wait(5)

    def close(self):
        self._ended.set()
        self._listener.close()
        self._thread.join(5)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class AgainstTheEmulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = support.entered(cls, support.example_show())
        cls.emulator = support.entered(cls, support.Emulator(cls.folder, tcp_port=0))
        cls.target = ("--tcp", cls.emulator.tcp)

    def test_each_command_prints_the_reply_and_exits_with_0(self):
        for words in (("brightness", "90"), ("off",), ("on",), ("play", "2"), ("play", "3")):
            with self.subTest(command=words):
                result = support.run_tool(*self.target, *words)
                self.assertEqual((result.status, result.out, result.err), (0, OK, ""))
        result = support.run_tool(*self.target, "status")
        self.assertEqual((result.status, result.err), (0, ""))
        self.assertEqual(support.without_fps(result.out), {"ok": True, "on": True, "brightness": 90, "playing": 3, "animation": 1, "error": None})
        self.assertTrue(result.out.endswith("}\n"))
        self.assertEqual(result.out.count("\n"), 1)

    def test_a_refused_command_prints_the_reply_and_exits_with_1(self):
        for words, code in ((("play", "99"), "unknown-id"), (("play", "abc"), "bad-argument"), (("brightness", "256"), "bad-argument"), (("brightness", "-5"), "bad-argument"),
                            (("play", ""), "bad-argument"), (("play", "1 2"), "bad-argument"), (("play", "1" * 70), "line-too-long")):
            with self.subTest(command=words):
                result = support.run_tool(*self.target, *words)
                self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"%s"}\n' % code, ""))

    def test_the_options_may_stand_before_or_after_the_command(self):
        self.assertEqual(support.run_tool("brightness", "12", *self.target).status, 0)
        self.assertEqual(support.run_tool("--timeout", "3", *self.target, "status").status, 0)
        self.assertEqual(json.loads(support.run_tool("status", *self.target, "--timeout", "3").out)["brightness"], 12)

    def test_a_session_gets_the_replies_of_the_reference_as_over_http(self):
        session = (("on",), ("brightness", "128"), ("play", "3"), ("status",), ("brightness", "77"), ("status",), ("off",), ("status",), ("on",), ("play", "2"), ("status",), ("play", "99"), ("status",))
        player = ReferencePlayer(support.files_of(self.folder))
        player.poll(0)
        for words in session:
            expected = support.without_fps(player.command(100, " ".join(words).encode("ascii")))
            over_tcp = support.run_tool(*self.target, *words)
            self.assertEqual(support.without_fps(over_tcp.out), expected, words)
            if words == ("status",):
                over_http = support.run_tool("--http", f"127.0.0.1:{self.emulator.port}", *words)
                self.assertEqual(support.without_fps(over_http.out), expected, words)

    def test_the_tool_runs_as_a_module(self):
        result = support.run_module("--tcp", self.emulator.tcp, "brightness", "64", module="odrigctl")
        self.assertEqual((result.status, result.out.replace("\r\n", "\n"), result.err), (0, OK, ""))


class TheExchange(unittest.TestCase):
    def test_the_line_is_sent_as_it_is_and_the_reply_comes_back_without_its_line_end(self):
        with Target(b'{"ok":true}\n') as target:
            self.assertEqual(client.tcp_exchange(target.address, b"play 2\n", 2), b'{"ok":true}')
        self.assertEqual(target.received, [b"play 2\n"])

    def test_a_line_that_is_not_a_reply_is_skipped(self):
        with Target(b'boot: ready\n[1,2,3]\n{"state":{"on":true}}\n"ok"\n\n{"ok":false,"error":"unknown-id"}\r\n{"ok":true}\n') as target:
            self.assertEqual(client.tcp_exchange(target.address, b"play 9\n", 2), b'{"ok":false,"error":"unknown-id"}')

    def test_a_reply_that_arrives_in_pieces_is_put_together(self):
        with Target(b'{"ok":tr', b'ue,"on"', b":false}", b"\n", stays_open=True) as target:
            self.assertEqual(client.tcp_exchange(target.address, b"status\n", 2), b'{"ok":true,"on":false}')

    def test_another_judge_of_a_reply_may_be_given(self):
        with Target(b'{"ok":true}\nWLED 16.0.1\n') as target:
            self.assertEqual(client.tcp_exchange(target.address, b"v\n", 2, accept=lambda line: line.startswith(b"WLED")), b"WLED 16.0.1")

    def test_no_reply_within_the_time_is_unreachable(self):
        with Target(b"boot: ready\n", stays_open=True) as target:
            started = time.monotonic()
            with self.assertRaises(client.Unreachable) as caught:
                client.tcp_exchange(target.address, b"status\n", 0.3)
            self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(str(caught.exception), f"{target.address}: no reply within 0.3 seconds")

    def test_a_target_that_closes_without_a_reply_is_unreachable(self):
        with Target(b"boot: ready\n") as target:
            with self.assertRaises(client.Unreachable) as caught:
                client.tcp_exchange(target.address, b"status\n", 2)
        self.assertEqual(str(caught.exception), f"{target.address}: no reply within 2 seconds")

    def test_nothing_listening_is_unreachable(self):
        address = f"127.0.0.1:{support.free_port()}"
        with self.assertRaises(client.Unreachable) as caught:
            client.tcp_exchange(address, b"status\n", 2)
        self.assertTrue(str(caught.exception).startswith(f"{address}: "), caught.exception)

    def test_an_address_is_a_host_and_a_port(self):
        self.assertEqual(client.tcp_address("127.0.0.1:8601"), ("127.0.0.1", 8601))
        self.assertEqual(client.tcp_address("target.local:1"), ("target.local", 1))
        self.assertEqual(client.tcp_address("[::1]:65535"), ("::1", 65535))
        for wrong in ("127.0.0.1", "127.0.0.1:", ":8601", "127.0.0.1:0", "127.0.0.1:65536", "127.0.0.1:x", "127.0.0.1:-1", "127.0.0.1: 80", ""):
            with self.assertRaises(ValueError, msg=wrong):
                client.tcp_address(wrong)
        with self.assertRaises(client.Unreachable):
            client.tcp_exchange("127.0.0.1", b"status\n", 1)


class TheCommandLine(unittest.TestCase):
    def test_a_target_that_cannot_be_reached_exits_with_3_and_one_line(self):
        address = f"127.0.0.1:{support.free_port()}"
        result = support.run_tool("--tcp", address, "status")
        self.assertEqual((result.status, result.out), (3, ""))
        self.assertTrue(result.err.startswith(f"error: unreachable: {address}: "), result.err)
        self.assertEqual(result.err.count("\n"), 1)

    def test_a_target_that_does_not_answer_in_time_exits_with_3(self):
        with Target(stays_open=True) as target:
            result = support.run_tool("--tcp", target.address, "--timeout", "0.3", "status")
        self.assertEqual((result.status, result.out, result.err), (3, "", f"error: unreachable: {target.address}: no reply within 0.3 seconds\n"))

    def test_an_address_without_its_port_is_not_understood(self):
        for wrong in ("127.0.0.1", "127.0.0.1:", "127.0.0.1:0", "127.0.0.1:99999", ":8601"):
            result = support.run_tool("--tcp", wrong, "status")
            self.assertEqual((result.status, result.out), (2, ""), wrong)
            self.assertIn("host:port", result.err)

    def test_exactly_one_target_is_given(self):
        for argv in (("status",), ("--tcp", "127.0.0.1:1", "--http", "127.0.0.1", "status"), ("--tcp", "127.0.0.1:1", "--port", "x", "status"), ("--port", "x", "--http", "127.0.0.1", "status")):
            self.assertEqual(support.run_tool(*argv).status, 2, argv)

    def test_the_targets_are_a_serial_port_a_tcp_address_and_an_http_address(self):
        options = {option for action in cli.parser()._actions for option in action.option_strings}
        self.assertEqual(options, {"-h", "--help", "--port", "--tcp", "--http", "--timeout"})

    def test_the_line_is_the_same_whichever_way_it_travels(self):
        made = cli.parser()
        for argv in (["play", "2"], ["brightness", "40"], ["status"]):
            lines = {cli.command_line(made, made.parse_args([*target, *argv])) for target in (("--port", "x"), ("--tcp", "h:1"), ("--http", "h"))}
            self.assertEqual(len(lines), 1, argv)


if __name__ == "__main__":
    unittest.main()

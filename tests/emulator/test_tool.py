import fcntl
import json
import os
import pathlib
import socket
import struct
import tempfile
import termios
import threading
import time
import unittest
from unittest import mock

from emulator import serialport
from odrig import mapping
from odrigctl import cli, client
from tests.core.support import ReferencePlayer

from . import support

OK = '{"ok":true}\n'

# Every command, an id that does not exist, an id that is no number, a brightness out of
# range, and a line that is too long. Each entry is what follows the target on the command
# line.
SESSION = (
    ("status",),
    ("brightness", "77"),
    ("status",),
    ("off",),
    ("status",),
    ("on",),
    ("play", "2"),
    ("status",),
    ("play", "3"),
    ("status",),
    ("play", "99"),
    ("play", "abc"),
    ("brightness", "256"),
    ("play", "1" * 70),
    ("status",),
)


def reference_replies(files, session):
    player = ReferencePlayer(files)
    player.poll(0)
    return [player.command(100, " ".join(words).encode("ascii")) for words in session]


class AgainstTheEmulator(unittest.TestCase):
    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        self.emulator = support.entered(self, support.Emulator(self.folder))
        self.targets = {"serial": ("--port", self.emulator.serial), "http": ("--http", f"127.0.0.1:{self.emulator.port}")}

    def test_each_command_prints_the_reply_and_exits_with_0_by_each_transport(self):
        for transport, target in self.targets.items():
            for words in (("brightness", "90"), ("off",), ("on",), ("play", "2"), ("play", "3")):
                with self.subTest(transport=transport, command=words):
                    result = support.run_tool(*target, *words)
                    self.assertEqual((result.status, result.out, result.err), (0, OK, ""))
            result = support.run_tool(*target, "status")
            self.assertEqual((result.status, result.err), (0, ""))
            self.assertEqual(support.without_fps(result.out), {"ok": True, "on": True, "brightness": 90, "playing": 3, "animation": 1, "error": None})
            self.assertTrue(result.out.endswith("}\n"))
            self.assertEqual(result.out.count("\n"), 1)

    def test_a_refused_command_prints_the_reply_and_exits_with_1(self):
        for transport, target in self.targets.items():
            for words, code in ((("play", "99"), "unknown-id"), (("play", "abc"), "bad-argument"), (("brightness", "256"), "bad-argument"), (("brightness", "-5"), "bad-argument"),
                                (("play", ""), "bad-argument"), (("play", "1 2"), "bad-argument"), (("play", "1" * 70), "line-too-long")):
                with self.subTest(transport=transport, command=words):
                    result = support.run_tool(*target, *words)
                    self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"%s"}\n' % code, ""))

    def test_the_argument_is_sent_as_it_was_typed(self):
        with support.EventStream(self.emulator.port) as stream:
            stream.read_until(lambda events: any(event.kind == "frame" for event in events))
            typed = ["abc", "007", "+5", "5 ", "0x10", "1e2", "é"]
            for argument in typed:
                support.run_tool(*self.targets["http"], "play", argument)
                support.run_tool(*self.targets["serial"], "brightness", argument)
            logged = support.of_kind(stream.read_until(lambda events: sum(event.kind == "log" for event in events) >= 2 * len(typed), 10), "log")
        expected = [line for argument in typed for line in (f"play {argument}", f"brightness {argument}")]
        self.assertEqual([entry["line"] for entry in logged], [line.replace("é", "\\xC3\\xA9") for line in expected])
        self.assertEqual([entry["transport"] for entry in logged], ["http", "serial"] * len(typed))
        self.assertEqual({entry["reply"] for entry in logged if "007" not in entry["line"]}, {'{"ok":false,"error":"bad-argument"}'})

    def test_the_options_may_follow_the_command_and_the_address_may_be_written_as_a_url(self):
        port = self.emulator.port
        for argv in (
            ["status", "--http", f"127.0.0.1:{port}"],
            ["--http", f"http://127.0.0.1:{port}", "status"],
            ["--http", f"http://127.0.0.1:{port}/", "status"],
            ["--http", f"localhost:{port}", "status", "--timeout", "5"],
            ["brightness", "128", "--port", self.emulator.serial],
            ["--timeout", "0.5", "--port", self.emulator.serial, "on"],
        ):
            self.assertEqual(support.run_tool(*argv).status, 0, argv)

    def test_the_module_runs_as_a_program(self):
        for target in self.targets.values():
            result = support.run_module(*target, "brightness", "128", module="odrigctl")
            self.assertEqual((result.status, result.out, result.err), (0, OK, ""))
            result = support.run_module(*target, "play", "4", module="odrigctl")
            self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"unknown-id"}\n', ""))
        self.assertEqual(support.run_module("--port", self.emulator.serial, module="odrigctl").status, 2)

    def test_the_tool_leaves_nothing_behind_in_the_port(self):
        for _ in range(3):
            self.assertEqual(support.run_tool(*self.targets["serial"], "on").status, 0)
        with support.Serial(self.emulator.serial) as port:
            self.assertEqual(port.read_for(0.3), b"")
            self.assertEqual(port.ask("on"), b'{"ok":true}\n')


class Session(unittest.TestCase):
    def session(self, show, transport):
        """Sends the whole session to a fresh emulator that runs a show. Returns the files
        of the show, what the tool did for each command, and the log entries of the page."""
        with show() as folder, support.Emulator(folder) as emulator:
            target = ("--port", emulator.serial) if transport == "serial" else ("--http", f"127.0.0.1:{emulator.port}")
            results = [support.run_tool(*target, *words) for words in SESSION]
            with support.EventStream(emulator.port) as stream:
                logged = support.of_kind(stream.read_until(lambda events: any(event.kind == "status" for event in events)), "log")
            return support.files_of(folder), results, logged

    def test_the_session_gives_the_replies_of_the_reference_by_each_transport_and_fills_the_log(self):
        self.check_session(support.example_show, legs=2)

    def test_the_session_against_the_demo_show_gives_the_replies_of_the_reference_by_each_transport(self):
        self.check_session(support.demo_show, legs=20)

    def check_session(self, show, legs):
        replies = {}
        for transport in ("serial", "http"):
            with self.subTest(transport=transport):
                files, results, logged = self.session(show, transport)
                self.assertEqual(len(mapping.loads(files["mapping.json"]).legs), legs)
                expected = reference_replies(files, SESSION)
                self.assertEqual([result.err for result in results], [""] * len(SESSION))
                for words, result, wanted in zip(SESSION, results, expected):
                    if words == ("status",):
                        self.assertEqual(support.without_fps(result.out), support.without_fps(wanted), words)
                    else:
                        self.assertEqual(result.out, wanted.decode("ascii"), words)
                    self.assertEqual(result.status, 0 if json.loads(wanted)["ok"] else 1, words)
                replies[transport] = [json.dumps(support.without_fps(result.out)) for result in results]
                self.assertEqual(len(logged), len(SESSION))
                self.assertEqual({entry["transport"] for entry in logged}, {transport})
                self.assertEqual([entry["line"] for entry in logged], [" ".join(words)[:64] for words in SESSION])
                self.assertEqual([entry["cut"] for entry in logged], [len(" ".join(words)) > 64 for words in SESSION])
                self.assertEqual([json.dumps(support.without_fps(entry["reply"])) for entry in logged], replies[transport])
        self.assertEqual(replies["serial"], replies["http"])
        codes = [json.loads(reply).get("error") for reply in replies["http"]]
        self.assertEqual(codes[-5:-1], ["unknown-id", "bad-argument", "bad-argument", "line-too-long"])
        self.assertEqual({words[0] for words in SESSION}, set(cli.COMMANDS))


class Unreachable(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))

    def assert_unreachable(self, result):
        self.assertEqual(result.status, 3)
        self.assertEqual(result.out, "")
        self.assertRegex(result.err, r"\Aerror: unreachable: .+\n\Z")

    def test_a_port_path_that_does_not_exist_exits_with_3_and_one_line(self):
        result = support.run_tool("--port", self.work / "no-such-port", "status")
        self.assert_unreachable(result)
        self.assertIn("no-such-port", result.err)

    def test_a_port_path_that_is_no_serial_port_exits_with_3(self):
        a_file = self.work / "file"
        a_file.write_bytes(b"")
        self.assert_unreachable(support.run_tool("--port", a_file, "status"))
        self.assert_unreachable(support.run_tool("--port", self.work, "status"))
        self.assertEqual(a_file.read_bytes(), b"")

    def test_a_closed_http_port_exits_with_3_and_one_line(self):
        result = support.run_tool("--http", f"127.0.0.1:{support.free_port()}", "status")
        self.assert_unreachable(result)
        self.assert_unreachable(support.run_module("--http", f"127.0.0.1:{support.free_port()}", "on", module="odrigctl"))

    def test_an_address_that_is_none_exits_with_3(self):
        for address in ("127.0.0.1:port", "http://", "", "https://127.0.0.1:1"):
            self.assert_unreachable(support.run_tool("--http", address, "status"))

    def test_a_port_that_stays_silent_exits_with_3_after_the_time_limit(self):
        silent = serialport.Port(self.work / "serial", lambda data: b"")
        self.addCleanup(silent.close)
        silent.start()
        started = time.monotonic()
        result = support.run_tool("--port", silent.link, "--timeout", "0.4", "status")
        elapsed = time.monotonic() - started
        self.assert_unreachable(result)
        self.assertIn("no reply within 0.4 seconds", result.err)
        self.assertGreaterEqual(elapsed, 0.4)
        self.assertLess(elapsed, 2)

    def test_an_address_that_accepts_and_never_answers_exits_with_3_after_the_time_limit(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            started = time.monotonic()
            result = support.run_tool("--http", f"127.0.0.1:{listener.getsockname()[1]}", "--timeout", "0.4", "status")
            elapsed = time.monotonic() - started
        self.assert_unreachable(result)
        self.assertGreaterEqual(elapsed, 0.4)
        self.assertLess(elapsed, 2)

    def test_another_status_than_200_exits_with_3(self):
        with support.example_show() as folder, support.Emulator(folder) as emulator:
            with mock.patch.object(client, "COMMAND_PATH", "/elsewhere"):
                result = support.run_tool("--http", f"127.0.0.1:{emulator.port}", "status")
        self.assert_unreachable(result)
        self.assertIn("status 404", result.err)

    def test_the_time_limit_is_2_seconds_unless_the_option_says_otherwise(self):
        self.assertEqual(cli.parser().parse_args(["--port", "x", "status"]).timeout, 2.0)
        self.assertEqual(cli.parser().parse_args(["--port", "x", "--timeout", "7.5", "status"]).timeout, 7.5)


class Usage(unittest.TestCase):
    def test_a_usage_error_exits_with_2(self):
        for argv in (
            [],
            ["status"],
            ["--port", "a", "--http", "b", "status"],
            ["--port", "a"],
            ["--port", "a", "dance"],
            ["--port", "a", "play"],
            ["--port", "a", "brightness"],
            ["--port", "a", "status", "1"],
            ["--port", "a", "on", "now"],
            ["--port", "a", "play", "1", "2"],
            ["--port", "a", "play", "1\n2"],
            ["--port", "a", "--timeout", "0", "status"],
            ["--port", "a", "--timeout", "soon", "status"],
            ["--port", "a", "--timeout", "inf", "status"],
            ["--port", "a", "--emulator", "status"],
            ["--port", "a", "--board", "status"],
        ):
            result = support.run_tool(*argv)
            self.assertEqual(result.status, 2, argv)
            self.assertIn("usage:", result.err)
            self.assertEqual(result.out, "")

    def test_the_commands_are_those_of_the_commands_document(self):
        text = (support.ROOT / "docs" / "commands.md").read_text(encoding="utf-8")
        table = text.split("\n## Commands\n")[1].split("\n## ")[0]
        documented = [row.split("`")[1] for row in table.splitlines() if row.startswith("| `")]
        self.assertEqual(documented, ["play <id>", "on", "off", "brightness <n>", "status"])
        self.assertEqual([name + (" <x>" if takes else "") for name, takes in cli.COMMANDS.items()], [command.replace("<id>", "<x>").replace("<n>", "<x>") for command in documented])

    def test_the_line_is_the_command_and_its_argument_as_typed_and_a_newline(self):
        made = cli.parser()
        for argv, line in (
            (["status"], b"status\n"),
            (["on"], b"on\n"),
            (["off"], b"off\n"),
            (["play", "12"], b"play 12\n"),
            (["brightness", "300"], b"brightness 300\n"),
            (["play", "abc"], b"play abc\n"),
            (["brightness", " 7"], b"brightness  7\n"),
            (["play", "1" * 70], b"play " + b"1" * 70 + b"\n"),
        ):
            self.assertEqual(cli.command_line(made, made.parse_args(["--port", "x", *argv])), line)

    def test_no_option_tells_the_emulator_from_the_board(self):
        options = {option for action in cli.parser()._actions for option in action.option_strings}
        self.assertEqual(options, {"-h", "--help", "--port", "--http", "--timeout"})


class StandIn:
    """Stands in for `fcntl.ioctl`: writes down the modem-line requests and lets them fail."""

    NAMES = {termios.TIOCM_RTS: "RTS", termios.TIOCM_DTR: "DTR"}

    def __init__(self, fails=False):
        self.requests = []
        self.fails = fails

    def __call__(self, descriptor, request, argument=0, *more):
        if request in (termios.TIOCMBIC, termios.TIOCMBIS, termios.TIOCMSET):
            (lines,) = struct.unpack("I", argument)
            action = {termios.TIOCMBIC: "lower", termios.TIOCMBIS: "raise", termios.TIOCMSET: "set"}[request]
            self.requests.append(f"{action} {self.NAMES.get(lines, lines)}")
            if self.fails:
                raise OSError(25, "Inappropriate ioctl for device")
            return 0
        return fcntl.ioctl(descriptor, request, argument, *more)


class SerialExchange(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.received = []

    def port(self, answer):
        """A port that keeps what it is sent and answers every finished line with fixed bytes."""
        def feed(data):
            self.received.append(data)
            return answer if b"\n" in data else b""

        port = serialport.Port(self.work / "serial", feed)
        self.addCleanup(port.close)
        port.start()
        return port.link

    def test_it_asks_for_rts_to_be_lowered_before_dtr(self):
        link = self.port(b'{"ok":true}\n')
        stand_in = StandIn()
        with mock.patch.object(client.fcntl, "ioctl", stand_in):
            reply = client.serial_exchange(link, b"status\n", 2)
        self.assertEqual(stand_in.requests, ["lower RTS", "lower DTR"], "the modem lines are not lowered RTS first, DTR second")
        self.assertEqual(reply, b'{"ok":true}')

    def test_it_goes_on_when_both_requests_fail(self):
        link = self.port(b'{"ok":true}\n')
        stand_in = StandIn(fails=True)
        with mock.patch.object(client.fcntl, "ioctl", stand_in):
            reply = client.serial_exchange(link, b"status\n", 2)
        self.assertEqual(stand_in.requests, ["lower RTS", "lower DTR"])
        self.assertEqual(reply, b'{"ok":true}')
        self.assertEqual(b"".join(self.received), b"status\n")

    def test_it_sets_the_port_raw_at_115200_without_modem_control(self):
        link = self.port(b'{"ok":true}\n')
        client.serial_exchange(link, b"status\n", 2)
        with support.Serial(link) as port:
            iflag, oflag, cflag, lflag, ispeed, ospeed, characters = termios.tcgetattr(port.fd)
        self.assertEqual((iflag, oflag, lflag), (0, 0, 0))
        self.assertEqual(cflag & (termios.CSIZE | termios.PARENB | termios.CREAD | termios.CLOCAL), termios.CS8 | termios.CREAD | termios.CLOCAL)
        self.assertEqual((ispeed, ospeed), (termios.B115200, termios.B115200))
        self.assertEqual((characters[termios.VMIN], characters[termios.VTIME]), (0, 0))

    def test_a_line_that_is_not_a_reply_is_skipped(self):
        link = self.port(b'boot: ready\n[1,2,3]\n{"state":{"on":true}}\n"ok"\n\n{"ok":false,"error":"unknown-id"}\r\n{"ok":true}\n')
        self.assertEqual(client.serial_exchange(link, b"play 9\n", 2), b'{"ok":false,"error":"unknown-id"}')

    def test_what_was_waiting_in_the_port_is_discarded(self):
        answers = iter([b'{"ok":true,"stale":1}\n', b'{"ok":true,"fresh":1}\n'])
        port = serialport.Port(self.work / "serial", lambda data: next(answers))
        self.addCleanup(port.close)
        port.start()
        with support.Serial(port.link) as program:
            program.write(b"first\n")
            time.sleep(0.2)
        self.assertEqual(client.serial_exchange(port.link, b"second\n", 2), b'{"ok":true,"fresh":1}')

    def test_another_judge_of_a_reply_may_be_given(self):
        link = self.port(b'{"ok":true}\nWLED 16.0.1\n')
        self.assertEqual(client.serial_exchange(link, b"v\n", 2, accept=lambda line: line.startswith(b"WLED")), b"WLED 16.0.1")

    def test_a_reply_that_arrives_in_pieces_is_put_together(self):
        def feed(data):
            def late():
                for piece in (b'{"ok":tr', b'ue,"on"', b":true}", b"\n"):
                    time.sleep(0.05)
                    os.write(port._near, piece)
            threading.Thread(target=late).start()
            return b""

        port = serialport.Port(self.work / "serial", feed)
        self.addCleanup(port.close)
        port.start()
        self.assertEqual(client.serial_exchange(port.link, b"status\n", 2), b'{"ok":true,"on":true}')

    def test_what_a_reply_is(self):
        for line in (b'{"ok":true}', b'{"ok":false,"error":"x"}', b'{"error":null,"ok":true}', b' {"ok": 1} '):
            self.assertTrue(client.is_reply(line), line)
        for line in (b"", b"ok", b'"ok"', b"[1]", b'{"on":true}', b'{"ok":true', b"\xff\xfe", b"null", b"{'ok': true}"):
            self.assertFalse(client.is_reply(line), line)


class HttpExchange(unittest.TestCase):
    def test_it_posts_the_line_as_octet_stream_to_odrig(self):
        seen = []

        def serve(listener):
            connection, _ = listener.accept()
            with connection:
                request = b""
                while not request.endswith(b"status\n"):
                    request += connection.recv(4096)
                seen.append(request)
                connection.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 12\r\n\r\n" + b'{"ok":true}\n')

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            thread = threading.Thread(target=serve, args=(listener,))
            thread.start()
            reply = client.http_exchange(f"127.0.0.1:{listener.getsockname()[1]}", b"status\n", 2)
            thread.join()
        self.assertEqual(reply, b'{"ok":true}')
        head, body = seen[0].split(b"\r\n\r\n", 1)
        lines = head.decode("ascii").split("\r\n")
        self.assertEqual(lines[0], "POST /odrig HTTP/1.1")
        headers = {name.lower(): value for name, value in (line.split(": ", 1) for line in lines[1:])}
        self.assertEqual(headers["content-type"], "application/octet-stream")
        self.assertEqual(headers["content-length"], "7")
        self.assertEqual(body, b"status\n")

    def test_an_address_without_a_port_is_port_80(self):
        with mock.patch.object(client.http.client, "HTTPConnection") as made:
            made.return_value.getresponse.return_value.status = 200
            made.return_value.getresponse.return_value.read.return_value = b'{"ok":true}\n'
            for address in ("4.3.2.1", "http://4.3.2.1", "http://4.3.2.1/", "4.3.2.1/"):
                self.assertEqual(client.http_exchange(address, b"on\n", 2), b'{"ok":true}')
                self.assertEqual(made.call_args.args, ("4.3.2.1",))
        self.assertEqual(client.http.client.HTTPConnection("4.3.2.1").port, 80)


if __name__ == "__main__":
    unittest.main()

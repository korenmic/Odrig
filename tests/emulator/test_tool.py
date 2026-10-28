import base64
import contextlib
import http.server
import io
import json
import os
import pathlib
import socket
import struct
import tempfile
import threading
import time
import unittest
import zlib
from unittest import mock

from odrig import mapping, show
from odrigctl import cli, client, content
from tests.core import support as core_support
from tests.core.support import ReferencePlayer

from . import support

if support.HAS_SERIAL:
    import fcntl
    import termios

    from emulator import serialport

OK = '{"ok":true}\n'

# Every command, an id that does not exist, an id that is no number, a brightness out of
# range, and a line that is too long. Each entry is what follows the target on the command
# line.
SESSION = (
    ("mapping", "test", "off"),
    ("status",),
    ("fault",),
    ("brightness", "77"),
    ("status",),
    ("off",),
    ("status",),
    ("on",),
    ("play", "2"),
    ("status",),
    ("play", "3"),
    ("status",),
    ("read", "1", "0"),
    ("catalog",),
    ("clocks", "off"),
    ("repeat", "99", "2"),
    ("play", "99"),
    ("play", "abc"),
    ("brightness", "256"),
    ("play", "1" * 2050),
    ("space",),
    ("list",),
    ("remove", "99"),
    ("ignore", "999", "1"),
    ("order", "move", "1", "999", "end"),
    ("status",),
)


def catalog_reply(files):
    """The reply to `catalog` of a target whose storage has no catalog and which has no drive."""
    named = len(set(show.files(show.loads(files["show.json"]))))
    return b'{"ok":true,"internal":{"state":"none","uncataloged":%d},"external":{"state":"absent"},"rebuild":null}\n' % named


def reference_replies(files, session):
    player = ReferencePlayer(files)
    player.poll(0)
    return [b'{"ok":true}\n' if words == ("mapping", "test", "off") else b'{"ok":false,"error":"unknown-id"}\n' if words in (("ignore", "999", "1"), ("order", "move", "1", "999", "end")) else
            catalog_reply(files) if words == ("catalog",) else player.command(100, " ".join(words).encode("ascii")) for words in session]


class AgainstTheEmulator(unittest.TestCase):
    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        self.emulator = support.entered(self, support.Emulator(self.folder))
        self.targets = {support.LINES: support.line_target(self.emulator), "http": ("--http", f"127.0.0.1:{self.emulator.port}")}

    def test_each_command_prints_the_reply_and_exits_with_0_by_each_transport(self):
        for transport, target in self.targets.items():
            for words in (("brightness", "90"), ("off",), ("on",), ("play", "2"), ("play", "3")):
                with self.subTest(transport=transport, command=words):
                    result = support.run_tool(*target, *words)
                    self.assertEqual((result.status, result.out, result.err), (0, OK, ""))
            result = support.run_tool(*target, "status")
            self.assertEqual((result.status, result.err), (0, ""))
            self.assertEqual(support.without_fps(result.out), {"ok": True, "on": True, "brightness": 90, "playing": 3, "animation": 1, "error": None, "width": 60, "height": 6, "seed": None})
            self.assertTrue(result.out.endswith("}\n"))
            self.assertEqual(result.out.count("\n"), 1)

    def test_repeat_is_sent_in_its_three_forms(self):
        # The example show plays its cycle, so that a turn's count is stale; a saved repeat is
        # about the animation, and is kept.
        for transport, target in self.targets.items():
            for words, status, out in ((("repeat", "1", "2"), 1, '{"ok":false,"error":"stale"}\n'), (("repeat", "1", "2", "save"), 0, OK),
                                       (("repeat", "1", "default"), 0, OK), (("repeat", "3", "default"), 1, '{"ok":false,"error":"in-use"}\n')):
                with self.subTest(transport=transport, command=words):
                    result = support.run_tool(*target, *words)
                    self.assertEqual((result.status, result.out, result.err), (status, out, ""))
        self.assertEqual((self.folder / "repeats.txt").read_bytes(), b"odrig-repeats 1\n")

    def test_a_refused_command_prints_the_reply_and_exits_with_1(self):
        for transport, target in self.targets.items():
            for words, code in ((("play", "99"), "unknown-id"), (("play", "abc"), "bad-argument"), (("brightness", "256"), "bad-argument"), (("brightness", "-5"), "bad-argument"),
                                (("play", ""), "bad-argument"), (("play", "1 2"), "bad-argument"), (("play", "1" * 70), "bad-argument"), (("play", "1" * 2050), "line-too-long")):
                with self.subTest(transport=transport, command=words):
                    result = support.run_tool(*target, *words)
                    self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"%s"}\n' % code, ""))

    def test_the_argument_is_sent_as_it_was_typed(self):
        with support.EventStream(self.emulator.port) as stream:
            stream.read_until(lambda events: any(event.kind == "frame" for event in events))
            typed = ["abc", "007", "+5", "5 ", "0x10", "1e2", "é"]
            for argument in typed:
                support.run_tool(*self.targets["http"], "play", argument)
                support.run_tool(*self.targets[support.LINES], "brightness", argument)
            logged = support.of_kind(stream.read_until(lambda events: sum(event.kind == "log" for event in events) >= 2 * len(typed), 10), "log")
        expected = [line for argument in typed for line in (f"play {argument}", f"brightness {argument}")]
        self.assertEqual([entry["line"] for entry in logged], [line.replace("é", "\\xC3\\xA9") for line in expected])
        self.assertEqual([entry["transport"] for entry in logged], ["http", support.LINES] * len(typed))
        self.assertEqual({entry["reply"] for entry in logged if "007" not in entry["line"]}, {'{"ok":false,"error":"bad-argument"}'})

    def test_the_options_may_follow_the_command_and_the_address_may_be_written_as_a_url(self):
        port = self.emulator.port
        for argv in (
            ["status", "--http", f"127.0.0.1:{port}"],
            ["--http", f"http://127.0.0.1:{port}", "status"],
            ["--http", f"http://127.0.0.1:{port}/", "status"],
            ["--http", f"localhost:{port}", "status", "--timeout", "5"],
            ["brightness", "128", *support.line_target(self.emulator)],
            ["--timeout", "0.5", *support.line_target(self.emulator), "on"],
        ):
            self.assertEqual(support.run_tool(*argv).status, 0, argv)

    def test_the_module_runs_as_a_program(self):
        for target in self.targets.values():
            result = support.run_module(*target, "brightness", "128", module="odrigctl")
            self.assertEqual((result.status, result.out, result.err), (0, OK, ""))
            result = support.run_module(*target, "play", "4", module="odrigctl")
            self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"unknown-id"}\n', ""))
        self.assertEqual(support.run_module(*support.line_target(self.emulator), module="odrigctl").status, 2)

    def test_the_tool_leaves_nothing_behind_in_the_port(self):
        for _ in range(3):
            self.assertEqual(support.run_tool(*self.targets[support.LINES], "on").status, 0)
        with support.lines(self.emulator) as port:
            self.assertEqual(port.read_for(0.3), b"")
            self.assertEqual(port.ask("on"), b'{"ok":true}\n')


class Session(unittest.TestCase):
    def session(self, show, transport):
        """Sends the whole session to a fresh emulator that runs a show. Returns the files
        of the show, what the tool did for each command, and the log entries of the page."""
        with show() as folder, support.Emulator(folder) as emulator:
            target = support.line_target(emulator) if transport == support.LINES else ("--http", f"127.0.0.1:{emulator.port}")
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
        for transport in (support.LINES, "http"):
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
                self.assertEqual([entry["line"] for entry in logged], [" ".join(words)[:200] for words in SESSION])
                self.assertEqual([entry["length"] for entry in logged], [min(len(" ".join(words)), 2048) for words in SESSION])
                self.assertEqual([entry["cut"] for entry in logged], [len(" ".join(words)) > 2048 for words in SESSION])
                self.assertEqual([json.dumps(support.without_fps(entry["reply"])) for entry in logged], replies[transport])
        self.assertEqual(replies[support.LINES], replies["http"])
        codes = [json.loads(reply).get("error") for reply in replies["http"]]
        self.assertEqual(codes[-10:-1], ["unknown-id", "bad-argument", "bad-argument", "line-too-long", None, None, "unknown-id", "unknown-id", "unknown-id"])
        self.assertEqual({words[0] for words in SESSION}, set(cli.COMMANDS) - {"upload"})


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

    @support.needs_serial
    def test_a_port_that_stays_silent_exits_with_3_after_the_time_limit(self):
        silent = serialport.Port(self.work / "serial", lambda data: b"")
        self.addCleanup(silent.close)
        silent.start()
        started = time.monotonic()
        result = support.run_tool("--port", silent.link, "--timeout", "0.4", "status")
        elapsed = time.monotonic() - started
        self.assert_unreachable(result)
        self.assertIn("no reply within 0.4 seconds", result.err)
        self.assertGreaterEqual(elapsed, 0.4 - support.CLOCK_STEP)
        self.assertLess(elapsed, 2)

    def test_an_address_that_accepts_and_never_answers_exits_with_3_after_the_time_limit(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            started = time.monotonic()
            result = support.run_tool("--http", f"127.0.0.1:{listener.getsockname()[1]}", "--timeout", "0.4", "status")
            elapsed = time.monotonic() - started
        self.assert_unreachable(result)
        self.assertGreaterEqual(elapsed, 0.4 - support.CLOCK_STEP)
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
            ["--port", "a", "space", "1"],
            ["--port", "a", "list", "0"],
            ["--port", "a", "list", "in"],
            ["--port", "a", "list", "at", "60007"],
            ["--port", "a", "list", "in", "60007", "1", "2"],
            ["--port", "a", "remove"],
            ["--port", "a", "remove", "1", "2"],
            ["--port", "a", "remove", "1\n"],
            ["--port", "a", "upload"],
            ["--port", "a", "upload", "9"],
            ["--port", "a", "upload", "9", "a.odrg", "b.odrg"],
            ["--port", "a", "upload", "9\n", "a.odrg"],
            ["--port", "a", "upload", "9", "a\n.odrg"],
            ["--port", "a", "upload begin", "9", "a.odrg"],
            ["--port", "a", "cancel"],
            ["--port", "a", "--timeout", "0", "status"],
            ["--port", "a", "--timeout", "soon", "status"],
            ["--port", "a", "--timeout", "inf", "status"],
            ["--port", "a", "--emulator", "status"],
            ["--port", "a", "--board", "status"],
            ["--port", "a", "clocks"],
            ["--port", "a", "clocks", "message"],
            ["--port", "a", "clocks", "yes"],
            ["--port", "a", "clocks", "on", "now"],
            ["--port", "a", "clocks", "message", "on\n"],
        ):
            result = support.run_tool(*argv)
            self.assertEqual(result.status, 2, argv)
            self.assertIn("usage:", result.err)
            self.assertEqual(result.out, "")

    def test_the_commands_are_those_of_the_commands_document(self):
        text = (support.ROOT / "docs" / "commands.md").read_text(encoding="utf-8")
        table = text.split("\n## Commands\n")[1].split("\n## ")[0]
        documented = [row.split("`")[1] for row in table.splitlines() if row.startswith("| `")]
        self.assertEqual(documented, ["play <id>", "play all", "on", "off", "brightness <n>", "status", "fault", "space", "list", "list in <folder-id>", "read <id> <offset>", "catalog", "catalog page <storage> <page> <offset>", "catalog rebuild <storage>", "catalog cancel", "remove <id>", "remove many <ids>", "ignore <id> <value>", "mapping get", "mapping set <revision> <pins>", "mapping cross on", "mapping cross off", "mapping test on", "mapping test off", "mapping test snake <n>", "order get", "order get in <folder-id>", "order move <revision> <id> <before>", "repeat <id> <n>", "repeat <id> <n> save",
                                      "repeat <id> default", "clocks on", "clocks off", "clocks message on", "clocks message off", "upload begin <id> <file> <bytes>", "upload begin external <file> <bytes>", "upload data <offset> <base64>", "upload expect <crc32>", "upload end <crc32>", "upload cancel"])
        # `play all` is `play` with the word in the place of the id.
        one_line = [command for command in documented if not command.startswith(("upload ", "mapping ", "order ", "catalog", "repeat ", "clocks ")) and command not in ("play all", "remove many <ids>", "list in <folder-id>")]
        self.assertEqual([" ".join([name, *("<x>" for _ in takes)]) for name, takes in cli.COMMANDS.items() if name not in ("upload", "mapping", "order", "catalog", "repeat", "clocks")],
                         [command.replace("<id>", "<x>").replace("<n>", "<x>").replace("<value>", "<x>").replace("<offset>", "<x>") for command in one_line])
        self.assertEqual(list(cli.COMMANDS)[-1], "upload")
        self.assertEqual(cli.COMMANDS["upload"], ("ID", "FILE"))
        self.assertEqual({name: takes for name, takes in cli.COMMANDS.items() if takes},
                         {"play": ("ID",), "brightness": ("N",), "read": ("ID", "OFFSET"), "catalog": ("[OPERATION]",), "remove": ("ID",), "ignore": ("ID", "VALUE"), "mapping": ("OPERATION",), "order": ("OPERATION",), "repeat": ("ID", "N", "[save]"),
                          "clocks": ("OPERATION",), "upload": ("ID", "FILE")})

    def test_a_usage_error_says_what_the_command_takes(self):
        for argv, said in ((["status", "1"], "status takes no argument"), (["play"], "play takes one argument: ID"), (["remove", "1", "2"], "remove takes one argument: ID"),
                           (["upload", "9"], "upload takes two arguments: ID FILE"), (["play", "1\n"], "a command is one line"),
                           (["catalog", "rebuild"], "catalog takes no argument, rebuild internal, rebuild external, cancel, or page internal|external PAGE OFFSET"),
                           (["catalog", "page", "internal", "0"], "catalog takes no argument, rebuild internal, rebuild external, cancel, or page internal|external PAGE OFFSET"),
                           (["catalog", "check"], "catalog takes no argument, rebuild internal, rebuild external, cancel, or page internal|external PAGE OFFSET"),
                           (["repeat", "1"], "repeat takes ID N, ID N save, or ID default"), (["repeat", "1", "8", "keep"], "repeat takes ID N, ID N save, or ID default"),
                           (["repeat", "1", "8", "save", "x"], "repeat takes ID N, ID N save, or ID default"), (["repeat", "1", "8\n"], "a command is one line"),
                           (["clocks"], "clocks takes on, off, message on, or message off"), (["clocks", "message", "yes"], "clocks takes on, off, message on, or message off"),
                           (["status", "--external"], "--external goes with upload"), (["--log", "--external"], "--external goes with upload"),
                           (["upload", "--external"], "upload --external takes one argument: FILE"),
                           (["upload", "--external", "9", "a.odrg"], "upload --external takes one argument: FILE")):
            result = support.run_tool("--port", "a", *argv)
            self.assertEqual(result.status, 2)
            self.assertIn(said, result.err)

    def test_the_line_is_the_command_and_its_argument_as_typed_and_a_newline(self):
        made = cli.parser()
        for argv, line in (
            (["status"], b"status\n"),
            (["on"], b"on\n"),
            (["off"], b"off\n"),
            (["play", "12"], b"play 12\n"),
            (["play", "all"], b"play all\n"),
            (["brightness", "300"], b"brightness 300\n"),
            (["play", "abc"], b"play abc\n"),
            (["brightness", " 7"], b"brightness  7\n"),
            (["play", "1" * 70], b"play " + b"1" * 70 + b"\n"),
            (["space"], b"space\n"),
            (["list"], b"list\n"),
            (["list", "in", "60007"], b"list in 60007\n"),
            (["list", "in", "60007", "4"], b"list in 60007 4\n"),
            (["order", "get", "in", "60007"], b"order get in 60007\n"),
            (["order", "get", "in", "60007", "2"], b"order get in 60007 2\n"),
            (["remove", "12"], b"remove 12\n"),
            (["remove", "x y"], b"remove x y\n"),
            (["catalog"], b"catalog\n"),
            (["catalog", "rebuild", "internal"], b"catalog rebuild internal\n"),
            (["catalog", "rebuild", "external"], b"catalog rebuild external\n"),
            (["catalog", "cancel"], b"catalog cancel\n"),
            (["repeat", "1", "8"], b"repeat 1 8\n"),
            (["repeat", "1", "8", "save"], b"repeat 1 8 save\n"),
            (["repeat", "60001", "default"], b"repeat 60001 default\n"),
            (["clocks", "on"], b"clocks on\n"),
            (["clocks", "off"], b"clocks off\n"),
            (["clocks", "message", "on"], b"clocks message on\n"),
            (["clocks", "message", "off"], b"clocks message off\n"),
        ):
            self.assertEqual(cli.command_line(made, made.parse_args(["--port", "x", *argv])), line)

    def test_the_help_names_play_all(self):
        said = " ".join(cli.parser().format_help().split())
        self.assertIn("Commands: play ID, play all, on, off,", said)
        self.assertIn("the word all of play", said)

    def test_no_option_tells_the_emulator_from_the_board(self):
        options = {option for action in cli.parser()._actions for option in action.option_strings}
        self.assertEqual(options, {"-h", "--help", "--port", "--tcp", "--http", "--timeout", "--log", "--external"})


class StandIn:
    """Stands in for `fcntl.ioctl`: writes down the modem-line requests and lets them fail."""

    def __init__(self, fails=False):
        self.names = {termios.TIOCM_RTS: "RTS", termios.TIOCM_DTR: "DTR"}
        self.requests = []
        self.fails = fails

    def __call__(self, descriptor, request, argument=0, *more):
        if request in (termios.TIOCMBIC, termios.TIOCMBIS, termios.TIOCMSET):
            (lines,) = struct.unpack("I", argument)
            action = {termios.TIOCMBIC: "lower", termios.TIOCMBIS: "raise", termios.TIOCMSET: "set"}[request]
            self.requests.append(f"{action} {self.names.get(lines, lines)}")
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

    @support.needs_serial
    def test_it_asks_for_rts_to_be_lowered_before_dtr(self):
        link = self.port(b'{"ok":true}\n')
        stand_in = StandIn()
        with mock.patch.object(client.fcntl, "ioctl", stand_in):
            reply = client.serial_exchange(link, b"status\n", 2)
        self.assertEqual(stand_in.requests, ["lower RTS", "lower DTR"], "the modem lines are not lowered RTS first, DTR second")
        self.assertEqual(reply, b'{"ok":true}')

    @support.needs_serial
    def test_it_goes_on_when_both_requests_fail(self):
        link = self.port(b'{"ok":true}\n')
        stand_in = StandIn(fails=True)
        with mock.patch.object(client.fcntl, "ioctl", stand_in):
            reply = client.serial_exchange(link, b"status\n", 2)
        self.assertEqual(stand_in.requests, ["lower RTS", "lower DTR"])
        self.assertEqual(reply, b'{"ok":true}')
        self.assertEqual(b"".join(self.received), b"status\n")

    @support.needs_serial
    def test_it_sets_the_port_raw_at_115200_without_modem_control(self):
        link = self.port(b'{"ok":true}\n')
        client.serial_exchange(link, b"status\n", 2)
        with support.Serial(link) as port:
            iflag, oflag, cflag, lflag, ispeed, ospeed, characters = termios.tcgetattr(port.fd)
        self.assertEqual((iflag, oflag, lflag), (0, 0, 0))
        self.assertEqual(cflag & (termios.CSIZE | termios.PARENB | termios.CREAD | termios.CLOCAL), termios.CS8 | termios.CREAD | termios.CLOCAL)
        self.assertEqual((ispeed, ospeed), (termios.B115200, termios.B115200))
        self.assertEqual((characters[termios.VMIN], characters[termios.VTIME]), (0, 0))

    @support.needs_serial
    def test_a_line_that_is_not_a_reply_is_skipped(self):
        link = self.port(b'boot: ready\n[1,2,3]\n{"state":{"on":true}}\n"ok"\n\n{"ok":false,"error":"unknown-id"}\r\n{"ok":true}\n')
        self.assertEqual(client.serial_exchange(link, b"play 9\n", 2), b'{"ok":false,"error":"unknown-id"}')

    @support.needs_serial
    def test_what_was_waiting_in_the_port_is_discarded(self):
        answers = iter([b'{"ok":true,"stale":1}\n', b'{"ok":true,"fresh":1}\n'])
        port = serialport.Port(self.work / "serial", lambda data: next(answers))
        self.addCleanup(port.close)
        port.start()
        with support.Serial(port.link) as program:
            program.write(b"first\n")
            time.sleep(0.2)
        self.assertEqual(client.serial_exchange(port.link, b"second\n", 2), b'{"ok":true,"fresh":1}')

    @support.needs_serial
    def test_another_judge_of_a_reply_may_be_given(self):
        link = self.port(b'{"ok":true}\nWLED 16.0.1\n')
        self.assertEqual(client.serial_exchange(link, b"v\n", 2, accept=lambda line: line.startswith(b"WLED")), b"WLED 16.0.1")

    @support.needs_serial
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


def targets(emulator):
    """What names an emulator on the command line of the tool, by each transport."""
    return {support.LINES: support.line_target(emulator), "http": ("--http", f"127.0.0.1:{emulator.port}")}


class Content(unittest.TestCase):
    """A folder with the example show, a copy of what it held, and emulators started on it."""

    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.folder = support.installed(self.work / "show", core_support.example_show())
        self.before = support.files_of(self.folder)
        self.hello = self.work / "sent" / "hello-again.odrg"
        self.hello.parent.mkdir()
        self.hello.write_bytes(self.before["hello.odrg"])

    def started(self, *options):
        emulator = support.Emulator(self.folder, *options)
        self.addCleanup(emulator.stop)
        return emulator

    def assert_as_before(self):
        """The folder holds what it held before: the same files, and the same show."""
        after = support.files_of(self.folder)
        self.assertEqual(sorted(after), sorted(self.before))
        self.assertEqual({name: data for name, data in after.items() if name != "show.json"}, {name: data for name, data in self.before.items() if name != "show.json"})
        self.assertEqual(json.loads(after["show.json"]), json.loads(self.before["show.json"]))


class SpaceListAndRemove(Content):
    def test_each_command_prints_the_reply_of_the_reference_by_each_transport(self):
        emulator = self.started()
        player = ReferencePlayer(self.before)
        sessions = {
            support.LINES: (("space",), ("list",), ("remove", "99"), ("remove", "abc"), ("remove", "1"), ("remove", "3"), ("list",), ("space",)),
            "http": (("space",), ("list",), ("remove", "3"), ("remove", "0"), ("remove", "2"), ("list",), ("space",)),
        }
        codes = []
        for transport, session in sessions.items():
            for words in session:
                expected = player.command(0, " ".join(words).encode("ascii"))
                result = support.run_tool(*targets(emulator)[transport], *words)
                self.assertEqual((result.status, result.out, result.err), (0 if json.loads(expected)["ok"] else 1, expected.decode("ascii"), ""), (transport, words))
                codes.append(json.loads(expected).get("error"))
        self.assertEqual(codes, [None, None, "unknown-id", "bad-argument", "in-use", None, None, None, None, None, "unknown-id", "bad-argument", None, None, None])
        emulator.stop()
        self.assertEqual(support.files_of(self.folder), player.files)
        self.assertEqual(sorted(player.files), ["hello.odrg", "mapping.json", "show.json"])

    def test_list_prints_a_reply_for_each_part_of_a_show_that_does_not_fit_into_one(self):
        items = [{"id": 100 + number, "file": f"clip-{number:02d}.odrg"} for number in range(60)]
        files = {"mapping.json": self.before["mapping.json"], "show.json": core_support.show_text(items)}
        files.update({item["file"]: core_support.clip(1, 60, 6) for item in items})
        for name in self.before:
            (self.folder / name).unlink()
        support.installed(self.folder, files)
        emulator = self.started()
        for transport, target in targets(emulator).items():
            with self.subTest(transport=transport):
                result = support.run_tool(*target, "list")
                self.assertEqual((result.status, result.err), (0, ""))
                replies = [json.loads(line) for line in result.out.splitlines()]
                self.assertGreater(len(replies), 2)
                self.assertTrue(all(len(line) < 1024 for line in result.out.splitlines()))
                self.assertEqual([item["id"] for reply in replies for item in reply["items"]], [item["id"] for item in items])
                positions = [0]
                for reply in replies:
                    positions.append(positions[-1] + len(reply["items"]))
                self.assertEqual([reply["next"] for reply in replies], positions[1:-1] + [None])
        with support.EventStream(emulator.port) as stream:
            logged = support.of_kind(stream.read_until(lambda events: any(event.kind == "status" for event in events)), "log")
        asked = [entry["line"] for entry in logged if entry["transport"] == "http"]
        self.assertEqual(asked, ["list"] + [f"list {position}" for position in positions[1:-1]])

    def test_list_stops_at_a_reply_that_is_not_ok_and_exits_with_1(self):
        (self.folder / "dvd.odrg").unlink()
        support.with_show_fault(self.folder)
        emulator = self.started()
        for target in targets(emulator).values():
            result = support.run_tool(*target, "list")
            self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"show-invalid"}\n', ""))
            result = support.run_tool(*target, "space")
            self.assertEqual((result.status, json.loads(result.out)["animations"]), (0, 0))

    def test_the_module_runs_the_commands_as_a_program(self):
        emulator = self.started()
        for target in targets(emulator).values():
            self.assertEqual(json.loads(support.run_module(*target, "space", module="odrigctl").out)["animations"], 2)
            self.assertEqual(len(json.loads(support.run_module(*target, "list", module="odrigctl").out)["items"]), 3)
            done = support.run_module(*target, "upload", "9", self.hello, module="odrigctl")
            self.assertEqual((done.status, done.out), (0, OK))
            self.assertRegex(done.err, r"\Aupload: 100% 1138/1138 bytes \d+ B/s\nupload: checking\nupload: committed: 1138 bytes sent and checked by the target\n\Z")
            self.assertEqual(support.run_module(*target, "remove", "9", module="odrigctl"), support.Result(0, OK, ""))


class Upload(Content):
    def named(self, emulator, target):
        """The last item `list` prints, and what `status` reports after `play 9`."""
        listed = support.run_tool(*target, "list")
        self.assertEqual((listed.status, listed.err), (0, ""))
        played = support.run_tool(*target, "play", "9")
        self.assertEqual((played.status, played.out), (0, OK))
        state = json.loads(support.run_tool(*target, "status").out)
        return json.loads(listed.out)["items"][-1], (state["playing"], state["animation"], state["error"])

    def test_hello_world_is_uploaded_listed_played_kept_over_a_restart_and_removed_by_each_transport(self):
        size = len(self.before["hello.odrg"])
        for transport in (support.LINES, "http"):
            with self.subTest(transport=transport):
                emulator = support.Emulator(self.folder)
                try:
                    target = targets(emulator)[transport]
                    result = support.run_tool(*target, "upload", "9", self.hello)
                    self.assertEqual((result.status, result.out), (0, OK))
                    self.assertRegex(result.err, rf"\Aupload: 100% {size}/{size} bytes \d+ B/s\nupload: checking\nupload: committed: {size} bytes sent and checked by the target\n\Z")
                    self.assertEqual(self.named(emulator, target), ({"id": 9, "file": "hello-again.odrg", "bytes": size, "ignored": False, "external": False, "type": "frames"}, ("all", 9, None)))
                finally:
                    emulator.stop()
                self.assertEqual(support.files_of(self.folder)["hello-again.odrg"], self.before["hello.odrg"])
                self.assertEqual(sorted(support.files_of(self.folder)), sorted([*self.before, "hello-again.odrg"]))
                again = support.Emulator(self.folder)
                try:
                    target = targets(again)[transport]
                    self.assertEqual(self.named(again, target), ({"id": 9, "file": "hello-again.odrg", "bytes": size, "ignored": False, "external": False, "type": "frames"}, ("all", 9, None)))
                    removed = support.run_tool(*target, "remove", "9")
                    self.assertEqual((removed.status, removed.out, removed.err), (0, OK, ""))
                    # It was the last animation of the playlist: the first one is next.
                    state = json.loads(support.run_tool(*target, "status").out)
                    self.assertEqual((state["playing"], state["animation"]), ("all", 1))
                finally:
                    again.stop()
                self.assert_as_before()

    def test_a_file_of_many_pieces_arrives_whole_and_the_port_is_opened_once(self):
        clip = core_support.dense_clip(60, 6, 2)
        self.assertGreater(len(clip), 6 * 1500)
        sent = self.work / "sent" / "clip.odrg"
        sent.write_bytes(clip)
        emulator = self.started()
        for number, (transport, target) in enumerate(targets(emulator).items(), start=20):
            with self.subTest(transport=transport), mock.patch.object(client, "_open", wraps=client._open) as opened:
                result = support.run_tool(*target, "upload", number, sent)
                self.assertEqual((result.status, result.out), (0, OK))
                self.assertEqual(opened.call_count, 1 if transport == "serial" else 0)
                lines = result.err.splitlines()
                self.assertEqual(lines[-3:], [mock.ANY, "upload: checking", f"upload: committed: {len(clip)} bytes sent and checked by the target"])
                self.assertRegex(lines[-3], rf"\Aupload: 100% {len(clip)}/{len(clip)} bytes \d+ B/s\Z")
                self.assertEqual(support.files_of(self.folder)["clip.odrg"], clip)
                listed = json.loads(support.run_tool(*target, "list").out)["items"]
                self.assertEqual(listed[-1], {"id": number, "file": "clip.odrg", "bytes": len(clip), "ignored": False, "external": False, "type": "frames"})
                self.assertEqual(support.run_tool(*target, "remove", number).status, 0)
        with support.EventStream(emulator.port) as stream:
            logged = support.of_kind(stream.read_until(lambda events: any(event.kind == "status" for event in events)), "log")
        lines = [entry["line"] for entry in logged if entry["transport"] == "http"]
        self.assertEqual(lines[0], f"upload begin 21 clip.odrg {len(clip)} {zlib.crc32(clip):08x}")
        data = [line for line in lines if line.startswith("upload data ")]
        self.assertEqual([int(line.split(" ")[2]) for line in data], list(range(0, len(clip), 1500)))
        ends = [entry for entry in logged if entry["transport"] == "http" and entry["line"].startswith("upload end ")]
        self.assertEqual({entry["line"] for entry in ends}, {f"upload end {zlib.crc32(clip):08x}"})
        self.assertGreater(len(ends), 1, "the first `upload end` was not answered with `busy`")
        self.assertEqual([json.loads(entry["reply"]).get("error") for entry in ends], ["busy"] * (len(ends) - 1) + [None])
        self.assert_as_before()

    def test_the_same_upload_again_sends_nothing_and_says_so_by_each_transport(self):
        emulator = self.started()
        for transport, target in targets(emulator).items():
            with self.subTest(transport=transport):
                first = support.run_tool(*target, "upload", "9", self.hello)
                self.assertEqual((first.status, first.out), (0, OK))
                self.assertTrue(first.err.endswith("upload: committed: 1138 bytes sent and checked by the target\n"))
                again = support.run_tool(*target, "upload", "9", self.hello)
                self.assertEqual((again.status, again.out, again.err), (0, '{"ok":true,"unchanged":true}\n', f"{cli.UPLOAD_UNCHANGED}\n"))
                self.assertEqual(support.run_tool(*target, "remove", "9").status, 0)
        with support.EventStream(emulator.port) as stream:
            logged = support.of_kind(stream.read_until(lambda events: any(event.kind == "status" for event in events)), "log")
        begun = [entry["line"] for entry in logged if entry["line"].startswith("upload begin")]
        self.assertEqual(begun, [f"upload begin 9 hello-again.odrg 1138 {zlib.crc32(self.before['hello.odrg']):08x}"] * 4)
        self.assertEqual(len([entry for entry in logged if entry["line"].startswith("upload data")]), 2)
        emulator.stop()
        self.assert_as_before()

    def test_the_name_sent_is_the_last_part_of_the_path_and_the_id_goes_out_as_typed(self):
        emulator = self.started()
        target = targets(emulator)["http"]
        odd = self.work / "sent" / "Not A Name.ODRG"
        odd.write_bytes(self.before["hello.odrg"])
        crc = f"{zlib.crc32(self.before['hello.odrg']):08x}"
        # An upload refused with `bad-argument` is asked for once more without the CRC-32,
        # as a target that does not take it would want.
        typed = ((("upload", "abc", self.hello), [f"upload begin abc hello-again.odrg 1138 {crc}", "upload begin abc hello-again.odrg 1138"]),
                 (("upload", "007", odd), [f"upload begin 007 Not A Name.ODRG 1138 {crc}", "upload begin 007 Not A Name.ODRG 1138"]),
                 (("upload", "70000", self.hello), [f"upload begin 70000 hello-again.odrg 1138 {crc}", "upload begin 70000 hello-again.odrg 1138"]), (("remove", "+2"), ["remove +2"]))
        for words, _ in typed:
            result = support.run_tool(*target, *words)
            self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"bad-argument"}\n', ""), words)
        with support.EventStream(emulator.port) as stream:
            logged = support.of_kind(stream.read_until(lambda events: any(event.kind == "status" for event in events)), "log")
        self.assertEqual([entry["line"] for entry in logged], [line for _, lines in typed for line in lines])
        self.assertEqual(emulator.command("upload cancel"), b'{"ok":false,"error":"no-upload"}\n')
        self.assert_as_before()

    def test_a_file_of_another_canvas_is_refused_with_bad_file_and_its_reason(self):
        wrong = self.work / "sent" / "wrong.odrg"
        wrong.write_bytes(core_support.clip(5, 60, 60))
        emulator = self.started()
        for target in targets(emulator).values():
            result = support.run_tool(*target, "upload", "9", wrong)
            self.assertEqual((result.status, result.out), (1, '{"ok":false,"error":"bad-file","reason":"size-mismatch"}\n'))
            self.assertTrue(result.err.endswith("upload: checking\n"))
            self.assertEqual(emulator.command("upload cancel"), b'{"ok":false,"error":"no-upload"}\n')
        emulator.stop()
        self.assert_as_before()

    def test_a_file_that_does_not_fit_the_storage_is_no_space(self):
        emulator = self.started("--storage", 4 * core_support.STORAGE_BLOCK + 16384 + 1000)
        for target in targets(emulator).values():
            result = support.run_tool(*target, "upload", "9", self.hello)
            self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"no-space"}\n', ""))
        emulator.stop()
        self.assert_as_before()

    def test_an_upload_that_is_refused_at_its_begin_cancels_nothing(self):
        emulator = self.started()
        self.assertEqual(emulator.command("upload begin 8 other.odrg 5"), b'{"ok":true,"chunk":1500}\n')
        for target in targets(emulator).values():
            result = support.run_tool(*target, "upload", "9", self.hello)
            self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"busy"}\n', ""))
            result = support.run_tool(*target, "upload", "3", self.hello)
            self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"busy"}\n', ""))
        self.assertEqual(emulator.command("upload cancel"), b'{"ok":true}\n', "the tool cancelled an upload that was not its own")
        result = support.run_tool(*targets(emulator)[support.LINES], "upload", "3", self.hello)
        self.assertEqual((result.status, result.out, result.err), (1, '{"ok":false,"error":"in-use"}\n', ""))

    def test_a_file_that_cannot_be_read_exits_with_2_and_sends_nothing(self):
        emulator = self.started()
        for target in targets(emulator).values():
            for path in (self.work / "sent" / "no-such.odrg", self.work / "sent", ""):
                result = support.run_tool(*target, "upload", "9", path)
                self.assertEqual((result.status, result.out), (2, ""), path)
                self.assertRegex(result.err, r"\Aerror: not-found: .+\n\Z")
                self.assertIn(str(path), result.err)
        self.assertEqual(support.run_tool(*targets(emulator)["http"], "status").status, 0)
        with support.EventStream(emulator.port) as stream:
            logged = support.of_kind(stream.read_until(lambda events: any(event.kind == "status" for event in events)), "log")
        self.assertEqual([entry["line"] for entry in logged], ["status"])
        result = support.run_tool("--port", self.work / "no-such-port", "upload", "9", self.work / "no-such.odrg")
        self.assertEqual(result.status, 2)

    def test_a_target_that_cannot_be_reached_exits_with_3(self):
        for target in (("--port", self.work / "no-such-port"), ("--http", f"127.0.0.1:{support.free_port()}")):
            for words in (("space",), ("list",), ("remove", "1"), ("upload", "9", self.hello)):
                result = support.run_tool(*target, *words)
                self.assertEqual((result.status, result.out), (3, ""), words)
                self.assertRegex(result.err, r"\Aerror: unreachable: .+\n\Z")

    def test_a_target_that_stops_answering_during_an_upload_exits_with_3(self):
        clip = self.work / "sent" / "clip.odrg"
        clip.write_bytes(core_support.dense_clip(60, 6, 1))
        answers = iter([b'{"ok":true,"chunk":1500}\n', b'{"ok":true,"received":1500}\n'])
        waiting = []

        def feed(data):
            waiting.append(data)
            return next(answers, b"") if data.endswith(b"\n") else b""

        port = support.BytePort(self.work, feed)
        self.addCleanup(port.close)
        started = time.monotonic()
        result = support.run_tool(*port.target, "--timeout", "0.3", "upload", "9", clip)
        elapsed = time.monotonic() - started
        self.assertEqual((result.status, result.out), (3, ""))
        self.assertTrue(result.err.endswith("no reply within 0.3 seconds\n"), result.err)
        lines = b"".join(waiting).decode("ascii").splitlines()
        self.assertEqual([line.split(" ")[:3] for line in lines], [["upload", "begin", "9"], ["upload", "data", "0"], ["upload", "data", "1500"], ["upload", "data", "1500"]])
        self.assertEqual(lines[2], lines[3])
        self.assertLess(elapsed, 3)


class Relay:
    """Stands between the tool and an emulator, by each transport, and passes every line on
    and every reply back, apart from what a test tells it to lose."""

    def __init__(self, case, emulator, folder, lost_lines=(), lost_replies=()):
        self.emulator = emulator
        self.lines = []
        self.lost_lines = lost_lines
        self.lost_replies = lost_replies
        self._pending = b""
        self.port = support.BytePort(folder, self._fed)
        case.addCleanup(self.port.close)
        relay = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                reply = relay.answer(self.rfile.read(int(self.headers["Content-Length"])).rstrip(b"\n"))
                if reply is None:
                    self.close_connection = True
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)

            def log_message(self, *_):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        case.addCleanup(thread.join)
        case.addCleanup(self.server.server_close)
        case.addCleanup(self.server.shutdown)
        self.targets = {support.LINES: self.port.target, "http": ("--http", f"127.0.0.1:{self.server.server_address[1]}")}

    def answer(self, line):
        """The emulator's reply to a line, or None for what is lost. The lines are counted
        from 1: a lost line never reaches the emulator, a lost reply never leaves it."""
        self.lines.append(line.decode("utf-8"))
        position = len(self.lines)
        if position in self.lost_lines:
            return None
        reply = self.emulator.command(line)
        return None if position in self.lost_replies else reply

    def _fed(self, data):
        self._pending += data
        replies = b""
        while b"\n" in self._pending:
            line, self._pending = self._pending.split(b"\n", 1)
            replies += self.answer(line) or b""
        return replies


class LostReply(Content):
    def setUp(self):
        super().setUp()
        self.clip = core_support.dense_clip(60, 6, 1)
        self.sent = self.work / "sent" / "clip.odrg"
        self.sent.write_bytes(self.clip)
        self.emulator = self.started()

    def relay(self, **lost):
        return Relay(self, self.emulator, pathlib.Path(support.entered(self, tempfile.TemporaryDirectory())), **lost)

    def upload(self, transport, number, **lost):
        relay = self.relay(**lost)
        result = support.run_tool(*relay.targets[transport], "--timeout", "0.4", "upload", number, self.sent)
        return relay, result

    def test_a_data_line_whose_reply_is_lost_is_sent_once_more_and_bad_offset_for_it_means_taken(self):
        for number, transport in enumerate((support.LINES, "http"), start=30):
            with self.subTest(transport=transport):
                relay, result = self.upload(transport, number, lost_replies=(3,))
                self.assertEqual((result.status, result.out), (0, OK), result.err)
                self.assertEqual(relay.lines[2], relay.lines[3])
                self.assertTrue(relay.lines[2].startswith("upload data 1500 "))
                self.assertTrue(relay.lines[4].startswith("upload data 3000 "))
                self.assertEqual(self.emulator.command("upload data 0 AAAA"), b'{"ok":false,"error":"no-upload"}\n')
                self.assertEqual(support.files_of(self.folder)["clip.odrg"], self.clip)
                self.assertEqual(self.emulator.command(f"remove {number}"), b'{"ok":true}\n')

    def test_a_data_line_that_is_lost_itself_is_sent_once_more_and_taken(self):
        for number, transport in enumerate((support.LINES, "http"), start=40):
            with self.subTest(transport=transport):
                relay, result = self.upload(transport, number, lost_lines=(3,))
                self.assertEqual((result.status, result.out), (0, OK), result.err)
                self.assertEqual(relay.lines[2], relay.lines[3])
                self.assertTrue(relay.lines[4].startswith("upload data 3000 "))
                self.assertEqual(support.files_of(self.folder)["clip.odrg"], self.clip)
                self.assertEqual(self.emulator.command(f"remove {number}"), b'{"ok":true}\n')

    def test_a_data_line_lost_twice_exits_with_3(self):
        for transport in (support.LINES, "http"):
            with self.subTest(transport=transport):
                relay, result = self.upload(transport, 9, lost_lines=(3, 4))
                self.assertEqual((result.status, result.out), (3, ""))
                self.assertRegex(result.err, r"error: unreachable: .+\n\Z")
                self.assertEqual(len(relay.lines), 4)
                self.assertEqual(self.emulator.command("upload cancel"), b'{"ok":true}\n')

    def test_a_reply_that_is_lost_for_another_command_is_not_asked_for_again(self):
        for words in (("space",), ("remove", "9"), ("list",)):
            relay = self.relay(lost_replies=(1,))
            result = support.run_tool(*relay.targets[support.LINES], "--timeout", "0.3", *words)
            self.assertEqual((result.status, result.out), (3, ""))
            self.assertEqual(relay.lines, [" ".join(words)])


class Told:
    """A session that answers from a list, and writes down what it was sent."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []
        self.discarded = []

    def exchange(self, line):
        self.sent.append(line)
        reply = self.replies.pop(0)
        if reply is None:
            raise client.Unreachable("no reply")
        return reply

    def discard(self, seconds):
        self.discarded.append(seconds)


BEGUN = b'{"ok":true,"chunk":700}'


def received(count):
    return b'{"ok":true,"received":%d}' % count


def refused(code):
    return b'{"ok":false,"error":"%s"}' % code.encode("ascii")


class UploadSteps(unittest.TestCase):
    DATA = bytes(range(256)) * 6 + b"end"

    def test_the_lines_are_those_of_the_commands_document(self):
        session = Told([BEGUN, received(700), received(1400), received(1539), b'{"ok":true}'])
        reports, events = [], []
        clock = iter(range(100, 200)).__next__
        reply = content.upload(session, "4", "clip.odrg", self.DATA, lambda *report: reports.append(report), lambda: events.append(len(reports)), clock=clock)
        self.assertEqual(reply, b'{"ok":true}')
        self.assertEqual(session.sent[0], b"upload begin 4 clip.odrg 1539 %08x\n" % zlib.crc32(self.DATA))
        self.assertEqual([line.split(b" ")[:3] for line in session.sent[1:4]], [[b"upload", b"data", b"0"], [b"upload", b"data", b"700"], [b"upload", b"data", b"1400"]])
        pieces = [line.split(b" ")[3] for line in session.sent[1:4]]
        self.assertTrue(all(piece.endswith(b"\n") and b"=" not in piece and b"+" not in piece and b"/" not in piece for piece in pieces))
        self.assertEqual(b"".join(base64.urlsafe_b64decode(piece.strip() + b"=" * (-len(piece.strip()) % 4)) for piece in pieces), self.DATA)
        self.assertEqual(session.sent[4], b"upload end %08x\n" % zlib.crc32(self.DATA))
        self.assertEqual(len(session.sent), 5)
        self.assertEqual(reports, [(700, 1539, 1), (1400, 1539, 2), (1539, 1539, 3)])
        self.assertEqual(events, [3])
        nine = Told([b'{"ok":true,"chunk":1500}', received(9), b'{"ok":true}'])
        content.upload(nine, 1, "a.odrg", b"123456789")
        self.assertEqual(nine.sent, [b"upload begin 1 a.odrg 9 cbf43926\n", b"upload data 0 MTIzNDU2Nzg5\n", b"upload end cbf43926\n"])

    def test_a_target_that_holds_the_file_is_sent_nothing_more(self):
        session = Told([b'{"ok":true,"unchanged":true}'])
        reply = content.upload(session, 4, "a.odrg", b"abc", lambda *report: self.fail("a piece was sent"), lambda: self.fail("the check was waited for"))
        self.assertEqual((reply, session.sent), (b'{"ok":true,"unchanged":true}', [b"upload begin 4 a.odrg 3 %08x\n" % zlib.crc32(b"abc")]))

    def test_a_target_that_refuses_the_crc32_of_upload_begin_gets_the_line_without_it(self):
        session = Told([refused("bad-argument"), b'{"ok":true,"chunk":1500}', received(3), b'{"ok":true}'])
        self.assertEqual(content.upload(session, 4, "a.odrg", b"abc"), b'{"ok":true}')
        self.assertEqual(session.sent[:2], [b"upload begin 4 a.odrg 3 %08x\n" % zlib.crc32(b"abc"), b"upload begin 4 a.odrg 3\n"])
        twice = Told([refused("bad-argument"), refused("bad-argument")])
        self.assertEqual(content.upload(twice, "x", "a.odrg", b"abc"), refused("bad-argument"))
        self.assertEqual(len(twice.sent), 2)

    def test_the_tool_says_what_the_upload_came_to(self):
        cases = (
            ([b'{"ok":true,"unchanged":true}'], 0, f"{cli.UPLOAD_UNCHANGED}\n"),
            ([b'{"ok":true,"chunk":1500}', received(3), b'{"ok":true}'], 0, "upload: committed: 3 bytes sent and checked by the target\n"),
            ([b'{"ok":true,"chunk":1500}', received(3), None], 3, f"{cli.UPLOAD_UNKNOWN}\nerror: unreachable: no reply\n"),
            ([b'{"ok":true,"chunk":1500}', None, None], 3, "error: unreachable: no reply\n"),
            ([refused("no-space")], 1, ""),
        )
        for replies, status, said in cases:
            with self.subTest(replies=replies):
                session = Told(replies)
                session.close = lambda: None
                screen, out = io.StringIO(), io.StringIO()
                with tempfile.TemporaryDirectory() as folder, mock.patch.object(cli.client, "Session", lambda **_: contextlib.nullcontext(session)), \
                        mock.patch.object(cli.sys, "stderr", screen), contextlib.redirect_stdout(out):
                    pathlib.Path(folder, "a.odrg").write_bytes(b"abc")
                    self.assertEqual(cli.main(["--port", "x", "upload", "5", str(pathlib.Path(folder, "a.odrg"))]), status)
                self.assertTrue(screen.getvalue().endswith(said), screen.getvalue())
                self.assertEqual(cli.UPLOAD_UNKNOWN in screen.getvalue(), cli.UPLOAD_UNKNOWN in said)
                if not said:
                    self.assertNotIn("upload: committed", screen.getvalue())

    def test_upload_end_is_sent_again_every_fifth_of_a_second_while_the_reply_is_busy(self):
        session = Told([BEGUN, received(3)] + [refused("busy")] * 7 + [b'{"ok":true}'])
        slept = []
        reply = content.upload(session, 4, "a.odrg", b"abc", sleep=slept.append)
        self.assertEqual(reply, b'{"ok":true}')
        self.assertEqual(session.sent[2:], [b"upload end %08x\n" % zlib.crc32(b"abc")] * 8)
        self.assertEqual(slept, [0.2] * 7)

    def test_after_600_seconds_of_busy_the_upload_is_cancelled_and_the_reply_is_busy(self):
        now = [0.0]

        def sleep(seconds):
            now[0] += seconds

        session = Told([BEGUN, received(3)] + [refused("busy")] * 4000 + [b'{"ok":true}'])
        reply = content.upload(session, 4, "a.odrg", b"abc", clock=lambda: now[0], sleep=sleep)
        self.assertEqual(reply, refused("busy"))
        self.assertEqual(session.sent[-1], b"upload cancel\n")
        ends = session.sent[2:-1]
        self.assertEqual(set(ends), {b"upload end %08x\n" % zlib.crc32(b"abc")})
        self.assertAlmostEqual(len(ends) * 0.2, 600, delta=1)
        self.assertEqual(content.BUSY_SECONDS, 600)

    def test_a_reply_that_is_not_ok_ends_the_upload_and_it_is_cancelled_when_it_may_still_be_open(self):
        pieces = [BEGUN, received(700), received(1400), received(1539)]
        bad_file = b'{"ok":false,"error":"bad-file","reason":"truncated"}'
        for replies, refusal, cancelled in (
            ([refused("busy")], refused("busy"), False),
            ([refused("no-space")], refused("no-space"), False),
            ([refused("in-use")], refused("in-use"), False),
            ([refused("show-invalid")], refused("show-invalid"), False),
            ([BEGUN, refused("bad-offset"), b'{"ok":true}'], refused("bad-offset"), True),
            ([BEGUN, refused("bad-argument"), b'{"ok":true}'], refused("bad-argument"), True),
            ([BEGUN, received(700), refused("storage-error")], refused("storage-error"), False),
            ([BEGUN, refused("no-upload")], refused("no-upload"), False),
            ([*pieces, refused("incomplete"), b'{"ok":true}'], refused("incomplete"), True),
            ([*pieces, refused("incomplete"), None], refused("incomplete"), True),
            ([*pieces, refused("bad-checksum")], refused("bad-checksum"), False),
            ([*pieces, refused("busy"), refused("busy"), bad_file], bad_file, False),
            ([*pieces, refused("storage-error")], refused("storage-error"), False),
        ):
            with self.subTest(replies=replies):
                session = Told(replies)
                reply = content.upload(session, 4, "a.odrg", self.DATA, sleep=lambda seconds: None)
                self.assertEqual(reply, refusal)
                self.assertEqual(session.sent[-1] == b"upload cancel\n", cancelled)
                self.assertEqual(session.sent.count(b"upload cancel\n"), int(cancelled))
                self.assertEqual(session.replies, [])

    def test_a_piece_without_a_reply_is_sent_once_more(self):
        taken = Told([BEGUN, None, refused("bad-offset"), received(1400), received(1539), b'{"ok":true}'])
        self.assertEqual(content.upload(taken, 4, "a.odrg", self.DATA), b'{"ok":true}')
        self.assertEqual(taken.sent[1], taken.sent[2])
        self.assertEqual([line.split(b" ")[2] for line in taken.sent[1:5]], [b"0", b"0", b"700", b"1400"])
        self.assertEqual(taken.discarded, [])
        lost = Told([BEGUN, received(700), None, received(1400), received(1539), b'{"ok":true}'])
        self.assertEqual(content.upload(lost, 4, "a.odrg", self.DATA), b'{"ok":true}')
        self.assertEqual([line.split(b" ")[2] for line in lost.sent[1:5]], [b"0", b"700", b"700", b"1400"])
        self.assertEqual(lost.discarded, [0.5])
        twice = Told([BEGUN, None, None])
        with self.assertRaises(client.Unreachable):
            content.upload(twice, 4, "a.odrg", self.DATA)
        self.assertEqual(len(twice.sent), 3)
        other = Told([BEGUN, None, refused("storage-error")])
        self.assertEqual(content.upload(other, 4, "a.odrg", self.DATA), refused("storage-error"))
        for replies in ([None], [BEGUN, received(700), received(1400), received(1539), None]):
            with self.assertRaises(client.Unreachable):
                content.upload(Told(replies), 4, "a.odrg", self.DATA)

    def test_list_all_asks_from_each_next_position_and_stops_at_a_refusal(self):
        session = Told([b'{"ok":true,"items":[{"id":1}],"next":1}', b'{"ok":true,"items":[{"id":2}],"next":7}', b'{"ok":true,"items":[],"next":null}'])
        shown = []
        self.assertIs(content.list_all(session, shown.append), True)
        self.assertEqual(session.sent, [b"list\n", b"list 1\n", b"list 7\n"])
        self.assertEqual(len(shown), 3)
        session = Told([b'{"ok":true,"items":[{"id":1}],"next":1}', refused("show-invalid"), b'{"ok":true,"items":[],"next":null}'])
        shown = []
        self.assertIs(content.list_all(session, shown.append), False)
        self.assertEqual(shown[-1], refused("show-invalid"))
        self.assertEqual(len(session.replies), 1)
        session = Told([b'{"ok":true,"items":[{"id":1}],"next":1}', b'{"ok":true,"items":[],"next":null}'])
        self.assertIs(content.list_all(session, [].append, b"list in 60007"), True)
        self.assertEqual(session.sent, [b"list in 60007\n", b"list in 60007 1\n"])


class Screen(io.StringIO):
    def isatty(self):
        return True


class ProgressLines(unittest.TestCase):
    def test_a_report_is_written_every_half_second_and_for_the_last_piece(self):
        now = [10.0]
        written = io.StringIO()
        progress = cli.Progress(written, clock=lambda: now[0])
        for sent, at in ((1500, 10.1), (3000, 10.4), (4500, 10.5), (6000, 10.7), (7500, 11.0), (9000, 11.2), (613500, 38.67), (1362000, 60.0)):
            now[0] = at
            progress.sent(sent, 1362000, at - 10.0)
        progress.checking()
        progress.close()
        self.assertEqual(written.getvalue().splitlines(), [
            "upload: 0% 4500/1362000 bytes 9000 B/s",
            "upload: 0% 7500/1362000 bytes 7500 B/s",
            "upload: 45% 613500/1362000 bytes 21399 B/s",
            "upload: 100% 1362000/1362000 bytes 27240 B/s",
            "upload: checking",
        ])
        self.assertTrue(written.getvalue().endswith("checking\n"))

    def test_a_piece_acknowledged_in_no_time_has_the_speed_0(self):
        written = io.StringIO()
        cli.Progress(written, clock=lambda: 0.0).sent(5, 5, 0.0)
        self.assertEqual(written.getvalue(), "upload: 100% 5/5 bytes 0 B/s\n")

    def test_on_a_terminal_one_line_is_written_over_again(self):
        now = [0.0]
        screen = Screen()
        progress = cli.Progress(screen, clock=lambda: now[0])
        for sent in (1000, 2000, 10000):
            now[0] += 1
            progress.sent(sent, 10000, now[0])
        progress.checking()
        progress.close()
        progress.close()
        text = screen.getvalue()
        self.assertEqual(text.count("\n"), 1)
        self.assertTrue(text.endswith("\n"))
        parts = text.rstrip("\n").split("\r")
        self.assertEqual([part.rstrip() for part in parts], ["", "upload: 10% 1000/10000 bytes 1000 B/s", "upload: 20% 2000/10000 bytes 1000 B/s", "upload: 100% 10000/10000 bytes 3333 B/s", "upload: checking"])
        self.assertGreaterEqual(len(parts[4]), len(parts[3]))

    def test_the_tool_ends_the_line_on_a_terminal_before_it_prints_the_reply(self):
        screen = Screen()
        out = io.StringIO()
        session = Told([b'{"ok":true,"chunk":1500}', received(3), refused("bad-checksum")])
        session.close = lambda: None
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(cli.client, "Session", lambda **_: contextlib.nullcontext(session)), \
                mock.patch.object(cli.sys, "stderr", screen), contextlib.redirect_stdout(out):
            pathlib.Path(folder, "a.odrg").write_bytes(b"abc")
            status = cli.main(["--port", "x", "upload", "5", str(pathlib.Path(folder, "a.odrg"))])
        self.assertEqual((status, out.getvalue()), (1, '{"ok":false,"error":"bad-checksum"}\n'))
        written = screen.getvalue()
        self.assertEqual((written.count("\n"), written[-1]), (1, "\n"))
        parts = [part.rstrip() for part in written.split("\r")]
        self.assertEqual((parts[0], parts[2], len(parts)), ("", "upload: checking", 3))
        self.assertRegex(parts[1], r"\Aupload: 100% 3/3 bytes \d+ B/s\Z")
        self.assertEqual(session.sent[0], b"upload begin 5 a.odrg 3 %08x\n" % zlib.crc32(b"abc"))


class SessionOfExchanges(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))

    def test_a_session_through_a_port_opens_it_once_and_gives_each_line_its_reply(self):
        with support.example_show() as folder, support.Emulator(folder) as emulator:
            with mock.patch.object(client, "_open", wraps=client._open) as opened:
                with client.Session(**support.session_target(emulator), timeout=2) as session:
                    replies = [session.exchange(line) for line in (b"brightness 9\n", b"play 99\n", b"status\n", b"space\n")]
                    descriptor = session._descriptor
                    self.assertIsNotNone(descriptor)
                    if support.HAS_SERIAL:
                        os.fstat(descriptor)
                self.assertEqual(opened.call_count, 1 if support.HAS_SERIAL else 0)
                self.assertIsNone(session._descriptor)
                if support.HAS_SERIAL:
                    with self.assertRaises(OSError):
                        os.fstat(descriptor)
                session.close()
                with self.assertRaisesRegex(client.Unreachable, "the session is closed"):
                    session.exchange(b"status\n")
            self.assertEqual(replies[:2], [b'{"ok":true}', b'{"ok":false,"error":"unknown-id"}'])
            self.assertEqual(json.loads(replies[2])["brightness"], 9)
            self.assertEqual(json.loads(replies[3])["animations"], 2)
            with client.Session(http=f"127.0.0.1:{emulator.port}", timeout=2) as session:
                self.assertEqual(session.exchange(b"brightness 10\n"), b'{"ok":true}')
                self.assertEqual(json.loads(session.exchange(b"status\n"))["brightness"], 10)
                session.discard(5)

    @support.needs_serial
    def test_a_line_that_arrived_whole_before_a_line_is_sent_is_no_answer_to_it(self):
        answers = iter([b'boot\n{"ok":true,"n":1}\n{"ok":true,"stray":1}\nnoi', b'se\n{"ok":true,"n":2}\n{"ok":true,"stray":2}\n', b"", b'{"ok":true,"n":4}\n'])
        port = serialport.Port(self.work / "serial", lambda data: next(answers))
        self.addCleanup(port.close)
        port.start()
        with client.Session(port=port.link, timeout=0.4) as session:
            self.assertEqual(session.exchange(b"a\n"), b'{"ok":true,"n":1}')
            time.sleep(0.1)
            self.assertEqual(session.exchange(b"b\n"), b'{"ok":true,"n":2}')
            time.sleep(0.1)
            with self.assertRaisesRegex(client.Unreachable, "no reply within 0.4 seconds"):
                session.exchange(b"c\n")
            self.assertEqual(session.exchange(b"d\n"), b'{"ok":true,"n":4}')

    @support.needs_serial
    def test_what_arrives_while_the_session_discards_is_no_answer(self):
        def feed(data):
            def late():
                time.sleep(0.15)
                os.write(port._near, b'{"ok":true,"late":1}\n')
            if data == b"a\n":
                threading.Thread(target=late).start()
            return b'{"ok":true,"n":2}\n' if data == b"b\n" else b""

        port = serialport.Port(self.work / "serial", feed)
        self.addCleanup(port.close)
        port.start()
        with client.Session(port=port.link, timeout=0.1) as session:
            with self.assertRaises(client.Unreachable):
                session.exchange(b"a\n")
            started = time.monotonic()
            session.discard(0.3)
            self.assertGreaterEqual(time.monotonic() - started, 0.3)
            self.assertEqual(session.exchange(b"b\n"), b'{"ok":true,"n":2}')
        started = time.monotonic()
        client.Session(http="127.0.0.1:1").discard(5)
        self.assertLess(time.monotonic() - started, 1)

    def test_a_session_is_with_a_port_or_with_an_address(self):
        for arguments in ({}, {"port": "a", "http": "b"}, {"port": "a", "tcp": "b:1"}, {"tcp": "a:1", "http": "b"}):
            with self.assertRaises(ValueError):
                client.Session(**arguments)
        with self.assertRaises(client.Unreachable):
            client.Session(port=self.work / "no-such-port")
        with self.assertRaises(client.Unreachable):
            client.Session(http=f"127.0.0.1:{support.free_port()}", timeout=1).exchange(b"status\n")

    def test_an_answer_over_http_that_is_no_reply_is_not_reached(self):
        with mock.patch.object(client, "http_exchange", return_value=b"<html>"):
            with self.assertRaisesRegex(client.Unreachable, "the answer is not a reply"):
                client.Session(http="4.3.2.1").exchange(b"status\n")
        self.assertEqual(client.Session(http="4.3.2.1").timeout, 2.0)


if __name__ == "__main__":
    unittest.main()

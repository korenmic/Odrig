import contextlib
import io
import json
import os
import pathlib
import socket
import tempfile
import threading
import unittest

from emulator import app, binding, failure, httpd, lineport
from tests.core.support import ReferencePlayer

from . import support

OK = b'{"ok":true}\n'


class Feed:
    """Stands in for the engine: keeps what arrives, and answers every line that the bytes
    finish with the line between two marks."""

    def __init__(self):
        self.received = []
        self._waiting = b""
        self._lock = threading.Lock()

    def __call__(self, data):
        with self._lock:
            self.received.append(data)
            *lines, self._waiting = (self._waiting + data).split(b"\n")
        return b"".join(b"<" + line + b">\n" for line in lines)

    def all(self):
        with self._lock:
            return b"".join(self.received)


class ThePort(unittest.TestCase):
    def setUp(self):
        self.feed = Feed()
        self.port = lineport.Port(0, self.feed)
        self.addCleanup(self.port.close)
        self.port.start()

    def program(self):
        return support.entered(self, support.Lines(self.port.address))

    def test_it_listens_on_127_0_0_1_and_takes_a_free_port_when_0_is_asked(self):
        self.assertEqual(self.port.server_address[0], httpd.ADDRESS)
        self.assertGreater(self.port.port, 0)
        self.assertEqual(self.port.address, f"127.0.0.1:{self.port.port}")
        self.assertFalse(support.refused(self.port.port))

    def test_every_byte_reaches_the_feed_unchanged_and_in_order(self):
        sent = bytes(range(256)) * 40 + b"\r\n\n\x00end"
        program = self.program()
        program.write(sent)
        program.read_lines(sent.count(b"\n"))
        self.assertEqual(self.feed.all(), sent)

    def test_a_reply_is_written_back_and_nothing_is_echoed(self):
        program = self.program()
        self.assertEqual(program.ask("status"), b"<status>\n")
        self.assertEqual(program.read_for(0.2), b"")

    def test_bytes_that_finish_no_line_get_no_answer(self):
        program = self.program()
        program.write(b"brightness 4")
        self.assertEqual(program.read_for(0.3), b"")
        self.assertEqual(self.feed.all(), b"brightness 4")

    def test_a_line_that_arrives_in_pieces_is_answered_once_it_is_whole(self):
        program = self.program()
        for piece in (b"br", b"ightn", b"ess 9"):
            program.write(piece)
            self.assertEqual(program.read_for(0.1), b"")
        program.write(b"\n")
        self.assertEqual(program.read_lines(1), b"<brightness 9>\n")

    def test_several_lines_at_once_get_their_replies_in_order(self):
        program = self.program()
        program.write(b"one\ntwo\r\nthree\n")
        self.assertEqual(program.read_lines(3), b"<one>\n<two\r>\n<three>\n")

    def test_a_reply_goes_to_the_connection_whose_bytes_finished_the_line(self):
        first, second = self.program(), self.program()
        first.write(b"begun by one, ")
        self.assertEqual(first.read_for(0.2), b"")
        second.write(b"ended by the other\n")
        self.assertEqual(second.read_lines(1), b"<begun by one, ended by the other>\n")
        self.assertEqual(first.read_for(0.2), b"")

    def test_a_program_may_connect_any_number_of_times(self):
        for turn in range(25):
            with support.Lines(self.port.address) as program:
                self.assertEqual(program.ask(f"turn {turn}"), f"<turn {turn}>\n".encode("ascii"))

    def test_several_programs_may_be_connected_at_once(self):
        programs = [self.program() for _ in range(6)]
        for number, program in enumerate(programs):
            self.assertEqual(program.ask(f"program {number}"), f"<program {number}>\n".encode("ascii"))
        for number, program in reversed(list(enumerate(programs))):
            self.assertEqual(program.ask(f"again {number}"), f"<again {number}>\n".encode("ascii"))

    def test_a_program_that_leaves_without_reading_ends_only_its_connection(self):
        with support.Lines(self.port.address) as leaving:
            leaving.write(b"left\n" * 50)
        self.assertEqual(self.program().ask("still here"), b"<still here>\n")

    def test_closing_the_port_ends_the_connections_and_frees_the_address(self):
        program = self.program()
        self.assertEqual(program.ask("status"), b"<status>\n")
        number = self.port.port
        self.port.close()
        program.socket.settimeout(5)
        try:
            ended = program.socket.recv(16)
        except ConnectionError:
            ended = b""
        self.assertEqual(ended, b"")
        self.assertTrue(support.refused(number))
        self.port.close()

    def test_a_connection_that_comes_while_the_port_closes_is_not_taken(self):
        self.assertIs(self.port.opened(first := socket.socket()), True)
        self.addCleanup(first.close)
        self.port.close()
        late = socket.socket()
        self.addCleanup(late.close)
        self.assertIs(self.port.opened(late), False)
        self.assertEqual(self.feed.received, [])

    def test_bytes_that_arrive_once_the_port_closes_are_not_handed_on(self):
        program = self.program()
        self.assertEqual(program.ask("before"), b"<before>\n")
        with self.port._lock:
            self.port._closing = True
        program.write(b"after\n")
        self.assertEqual(program.read_for(0.3), b"")
        self.assertEqual(self.feed.all(), b"before\n")

    def test_a_port_that_is_taken_is_address_in_use(self):
        with self.assertRaises(failure.Failure) as caught:
            lineport.Port(self.port.port, self.feed)
        self.assertEqual(caught.exception.reason, failure.ADDRESS_IN_USE)
        self.assertTrue(caught.exception.detail.startswith(f"127.0.0.1:{self.port.port}: "), caught.exception.detail)
        self.assertEqual(self.program().ask("status"), b"<status>\n")

    def test_a_port_that_another_program_listens_on_is_address_in_use(self):
        with socket.socket() as other:
            other.bind(("127.0.0.1", 0))
            other.listen()
            with self.assertRaises(failure.Failure) as caught:
                lineport.Port(other.getsockname()[1], self.feed)
        self.assertEqual(caught.exception.reason, failure.ADDRESS_IN_USE)


def arguments(*argv):
    return app.parse(["show", *argv])


class WhichPortsOpen(unittest.TestCase):
    def test_with_a_pseudo_terminal_the_serial_port_opens_and_the_line_port_only_when_asked(self):
        self.assertEqual(app.ports(arguments(), has_serial=True), (app.SERIAL_LINK, None))
        self.assertEqual(app.ports(arguments("--serial-link", "here"), has_serial=True), ("here", None))
        self.assertEqual(app.ports(arguments("--tcp-port", "7007"), has_serial=True), (app.SERIAL_LINK, 7007))
        self.assertEqual(app.ports(arguments("--tcp-port", "0", "--serial-link", "here"), has_serial=True), ("here", 0))

    def test_without_one_the_line_port_opens_always_and_on_8601_unless_told(self):
        self.assertEqual(app.TCP_PORT, 8601)
        self.assertEqual(app.ports(arguments(), has_serial=False), (None, 8601))
        self.assertEqual(app.ports(arguments("--tcp-port", "0"), has_serial=False), (None, 0))
        self.assertEqual(app.ports(arguments("--tcp-port", "7007"), has_serial=False), (None, 7007))

    def test_without_one_a_link_for_the_serial_port_is_refused(self):
        with self.assertRaises(failure.Failure) as caught:
            app.ports(arguments("--serial-link", "here"), has_serial=False)
        self.assertEqual(caught.exception.reason, failure.SERIAL_UNAVAILABLE)
        self.assertIn("here", caught.exception.detail)

    def test_this_system_has_the_serial_port_when_it_has_pseudo_terminals(self):
        self.assertEqual(app.HAS_SERIAL, hasattr(os, "openpty"))
        self.assertEqual(app.ports(arguments()), app.ports(arguments(), has_serial=app.HAS_SERIAL))

    def test_the_port_is_a_number_from_0_to_65535(self):
        for wrong in ("-1", "65536", "x", "80.5", ""):
            with self.assertRaises(SystemExit) as stopped, contextlib.redirect_stderr(io.StringIO()):
                arguments("--tcp-port", wrong)
            self.assertEqual(stopped.exception.code, 2, wrong)
        self.assertEqual(arguments("--tcp-port", "65535").tcp_port, 65535)

    def test_the_default_library_is_the_one_of_this_system(self):
        self.assertEqual(app.LIBRARY, support.ROOT / "core" / "build" / binding.LIBRARY_NAME)
        self.assertEqual(arguments().core, str(support.LIBRARY))
        self.assertIn(f"core/build/{binding.LIBRARY_NAME}", app.parser().format_help())


class TheEmulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = support.entered(cls, support.example_show())
        cls.emulator = support.entered(cls, support.Emulator(cls.folder, tcp_port=0))

    def program(self):
        return support.entered(self, support.Lines(self.emulator.tcp))

    def test_it_prints_the_address_of_the_line_port_after_the_other_lines(self):
        expected = [f"page: {self.emulator.url}"]
        if support.HAS_SERIAL:
            expected.append(f"serial: {self.emulator.serial}")
        expected.append(f"tcp: {self.emulator.tcp}")
        self.assertEqual(self.emulator.lines, expected)
        self.assertRegex(self.emulator.tcp, r"\A127\.0\.0\.1:[0-9]+\Z")
        self.assertNotEqual(self.emulator.tcp, f"127.0.0.1:{self.emulator.port}")

    def test_commands_are_answered_as_the_reference_answers_them(self):
        session = ("on", "brightness 128", "play 3", "status", "brightness 77", "status", "off", "status", "on", "play 2", "status", "play 99", "play abc", "brightness 256", "play " + "1" * 70, "dance", "", "status")
        player = ReferencePlayer(support.files_of(self.folder))
        player.poll(0)
        program = self.program()
        for line in session:
            expected = player.command(100, line.encode("ascii"))
            reply = program.ask(line)
            self.assertTrue(reply.endswith(b"\n"), line)
            self.assertEqual(reply.count(b"\n"), 1, line)
            self.assertEqual(support.without_fps(reply), support.without_fps(expected), line)
        self.assertEqual((self.emulator.status()["playing"], self.emulator.status()["animation"]), ("all", 2))
        self.assertEqual(self.program().ask("play 3"), OK)

    def test_a_command_that_arrived_by_the_line_port_is_in_the_log_as_tcp(self):
        with support.EventStream(self.emulator.port) as stream:
            stream.read_until(lambda events: any(event.kind == "status" for event in events))
            self.assertEqual(self.program().ask("brightness 33"), OK)
            self.emulator.command("brightness 44")
            logged = support.of_kind(stream.read_until(lambda events: sum(event.kind == "log" for event in events) >= 2), "log")
        self.assertEqual([(entry["transport"], entry["line"], entry["reply"]) for entry in logged[-2:]], [("tcp", "brightness 33", '{"ok":true}'), ("http", "brightness 44", '{"ok":true}')])

    def test_hello_carries_the_address_of_the_line_port(self):
        with support.EventStream(self.emulator.port) as stream:
            hello = json.loads(stream.read_until(lambda events: bool(events))[0].data)
        self.assertEqual(sorted(hello), ["error", "legs", "page", "serial", "show", "t0", "tcp"])
        self.assertEqual(hello["tcp"], self.emulator.tcp)
        self.assertEqual(hello["serial"], self.emulator.serial)
        self.assertEqual(hello["serial"] is None, not support.HAS_SERIAL)

    def test_a_line_begun_by_one_connection_is_ended_by_the_next_bytes(self):
        first, second = self.program(), self.program()
        first.write(b"brightn")
        self.assertEqual(first.read_for(0.2), b"")
        second.write(b"ess 55\nstatus\n")
        replies = second.read_lines(2).split(b"\n")
        self.assertEqual(replies[0], OK.rstrip(b"\n"))
        self.assertEqual(json.loads(replies[1])["brightness"], 55)
        self.assertEqual(first.read_for(0.2), b"")


class Starting(unittest.TestCase):
    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))

    def serial_options(self):
        """The options that keep the serial port of a started emulator, where there is one,
        off the link another emulator may hold."""
        return ("--serial-link", self.work / "serial") if support.HAS_SERIAL else ()

    @unittest.skipUnless(support.HAS_SERIAL, support.NO_SERIAL)
    def test_with_a_serial_port_and_without_the_option_no_line_port_is_opened(self):
        with support.Emulator(self.folder) as emulator:
            self.assertEqual(emulator.lines, [f"page: {emulator.url}", f"serial: {emulator.serial}"])
            self.assertIsNone(emulator.tcp)
            with support.EventStream(emulator.port) as stream:
                self.assertIsNone(json.loads(stream.read_until(lambda events: bool(events))[0].data)["tcp"])

    @unittest.skipIf(support.HAS_SERIAL, "this system has a pseudo-terminal")
    def test_without_a_pseudo_terminal_a_link_for_the_serial_port_ends_it_with_1(self):
        link = self.work / "serial"
        result = support.run_module(self.folder, "--port", 0, "--tcp-port", 0, "--serial-link", link)
        self.assertEqual((result.status, result.out), (1, ""))
        self.assertTrue(result.err.startswith(f"error: serial-unavailable: {link}: "), result.err)
        self.assertEqual(result.err.count("\n"), 1)
        self.assertFalse(link.exists())

    def test_a_line_port_that_is_taken_ends_it_with_1_and_leaves_nothing_behind(self):
        page = support.free_port()
        with socket.socket() as other:
            other.bind(("127.0.0.1", 0))
            other.listen()
            taken = other.getsockname()[1]
            result = support.run_module(self.folder, *self.serial_options(), "--port", page, "--tcp-port", taken)
        self.assertEqual((result.status, result.out), (1, ""))
        self.assertTrue(result.err.startswith(f"error: address-in-use: 127.0.0.1:{taken}: "), result.err)
        self.assertTrue(support.refused(page))
        self.assertFalse((self.work / "serial").exists())

    def test_the_line_port_does_not_go_with_record_mode(self):
        result = support.run(self.folder, "--record", self.work / "out.odrr", "--seconds", 1, "--tcp-port", 0)
        self.assertEqual(result.status, 2)
        self.assertIn("--tcp-port", result.err)
        self.assertFalse((self.work / "out.odrr").exists())

    def test_it_ends_with_0_on_the_signal_of_the_system_and_leaves_no_address(self):
        emulator = support.Emulator(self.folder, tcp_port=0)
        page, line_port = emulator.port, int(emulator.tcp.rsplit(":", 1)[1])
        with support.Lines(emulator.tcp) as program:
            self.assertEqual(program.ask("status").count(b"\n"), 1)
            result = emulator.stop()
            self.assertEqual(program.read_for(1), b"")
        self.assertEqual((result.status, result.err), (0, ""))
        self.assertTrue(support.refused(page))
        self.assertTrue(support.refused(line_port))


if __name__ == "__main__":
    unittest.main()

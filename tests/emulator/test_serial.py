import fcntl
import os
import pathlib
import stat
import tempfile
import termios
import time
import unittest

from emulator import failure, serialport
from tests.core.support import ReferencePlayer

from . import support
from .test_http import REFUSED, SESSION

OK = b'{"ok":true}\n'
TOO_LONG = b'{"ok":false,"error":"line-too-long"}\n'


class ThroughThePort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = support.entered(cls, support.example_show())
        cls.emulator = support.entered(cls, support.Emulator(cls.folder))

    def opened(self):
        return support.entered(self, support.Serial(self.emulator.serial))

    def test_each_command_gets_the_reply_of_the_reference(self):
        port = self.opened()
        player = ReferencePlayer(support.files_of(self.folder))
        player.poll(0)
        for line in (*SESSION, *REFUSED, ""):
            with self.subTest(line=line):
                reply = port.ask(line)
                expected = player.command(100, line.encode("ascii"))
                if line == "status":
                    self.assertEqual(support.without_fps(reply), support.without_fps(expected))
                else:
                    self.assertEqual(reply, expected)
        self.assertEqual(port.read_for(0.2), b"")

    def test_nothing_is_echoed_and_a_reply_ends_in_one_newline(self):
        port = self.opened()
        port.write(b"brightness 128\n")
        self.assertEqual(port.read_for(0.4), OK)
        port.write(b"on\r\n")
        self.assertEqual(port.read_for(0.4), OK)

    def test_a_line_split_over_three_writes_is_answered_once_when_it_ends(self):
        port = self.opened()
        port.write(b"brigh")
        self.assertEqual(port.read_for(0.2), b"")
        port.write(b"tness 1")
        self.assertEqual(port.read_for(0.2), b"")
        port.write(b"28\n")
        self.assertEqual(port.read_for(0.4), OK)

    def test_two_lines_in_one_write_get_two_replies_in_order(self):
        port = self.opened()
        port.write(b"play 99\nbrightness 128\ndance\n")
        self.assertEqual(port.read_lines(3), b'{"ok":false,"error":"unknown-id"}\n' + OK + b'{"ok":false,"error":"unknown-command"}\n')
        self.assertEqual(port.read_for(0.2), b"")

    def test_10000_bytes_without_a_newline_then_a_newline_get_one_line_too_long(self):
        port = self.opened()
        port.write(b"s" * 10000)
        self.assertEqual(port.read_for(0.3), b"")
        port.write(b"\n")
        self.assertEqual(port.read_for(0.4), TOO_LONG)
        self.assertEqual(port.ask("on"), OK)

    def test_the_port_is_opened_and_closed_20_times(self):
        for number in range(20):
            with support.Serial(self.emulator.serial) as port:
                self.assertEqual(port.ask(f"brightness {100 + number}"), OK)
        with support.Serial(self.emulator.serial) as port:
            self.assertEqual(support.without_fps(port.ask("status"))["brightness"], 119)
            self.assertEqual(port.ask("brightness 128"), OK)

    def test_a_line_begun_by_one_program_is_ended_by_the_next(self):
        with support.Serial(self.emulator.serial) as port:
            port.write(b"brightness")
            self.assertEqual(port.read_for(0.2), b"")
        with support.Serial(self.emulator.serial) as port:
            port.write(b" 128\n")
            self.assertEqual(port.read_for(0.4), OK)

    def test_setting_a_speed_and_changing_dtr_and_rts_do_no_harm(self):
        port = self.opened()
        for speed in (termios.B9600, termios.B115200):
            settings = termios.tcgetattr(port.fd)
            settings[4] = settings[5] = speed
            termios.tcsetattr(port.fd, termios.TCSANOW, settings)
            self.assertEqual(termios.tcgetattr(port.fd)[4:6], [speed, speed])
            for request in (termios.TIOCMBIC, termios.TIOCMBIS):
                for line in (termios.TIOCM_RTS, termios.TIOCM_DTR):
                    try:
                        fcntl.ioctl(port.fd, request, line.to_bytes(4, "little"))
                    except OSError:
                        pass
            port.write(b"brightness 128\n")
            self.assertEqual(port.read_for(0.4), OK)
        self.assertEqual(port.ask("dance"), b'{"ok":false,"error":"unknown-command"}\n')

    def test_replies_that_no_program_reads_do_not_stop_the_port(self):
        with support.Serial(self.emulator.serial) as port:
            for _ in range(60):
                port.write(b"status\n")
        time.sleep(0.2)
        with support.Serial(self.emulator.serial) as port:
            deadline = time.monotonic() + 15
            while port.read_for(0.3):
                self.assertLess(time.monotonic(), deadline, "the port never ran dry")
            self.assertEqual(port.ask("brightness 128"), OK)
        self.assertEqual(self.emulator.status()["brightness"], 128)


class Feed:
    """Stands in for the engine: keeps what the port passes on and answers with fixed bytes."""

    def __init__(self, answer=b""):
        self.received = b""
        self.answer = answer

    def __call__(self, data):
        self.received += data
        return self.answer if b"\n" in data else b""


class ThePortItself(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.link = self.work / "serial"

    def port(self, feed=None, link=None):
        port = serialport.Port(self.link if link is None else link, feed or Feed())
        self.addCleanup(port.close)
        port.start()
        return port

    def test_every_byte_value_passes_unchanged_in_both_directions(self):
        every = bytes(range(256))
        to_the_core = bytes(value for value in every if value != 0x0A) * 3 + b"\n"
        feed = Feed(answer=every * 2)
        self.port(feed)
        with support.Serial(self.link) as program:
            program.write(to_the_core)
            received = b""
            deadline = time.monotonic() + 5
            while len(received) < 512 and time.monotonic() < deadline:
                received += program.read_for(0.1)
        self.assertEqual(feed.received, to_the_core)
        self.assertEqual(received, every * 2)

    def test_the_link_is_a_symbolic_link_to_a_terminal_device(self):
        port = self.port()
        self.assertEqual(port.link, str(self.link))
        self.assertTrue(self.link.is_symlink())
        self.assertEqual(os.readlink(self.link), port.device)
        self.assertRegex(port.device, r"\A/dev/ttys[0-9]+\Z")
        self.assertTrue(stat.S_ISCHR(os.stat(self.link).st_mode))
        with support.Serial(self.link) as program:
            self.assertTrue(os.isatty(program.fd))

    def test_closing_removes_the_link(self):
        port = self.port()
        port.close()
        self.assertFalse(os.path.lexists(self.link))
        self.assertEqual(list(self.work.iterdir()), [])

    def test_closing_leaves_a_link_that_points_elsewhere(self):
        port = self.port()
        os.remove(self.link)
        os.symlink("/dev/null", self.link)
        port.close()
        self.assertEqual(os.readlink(self.link), "/dev/null")

    def test_a_link_left_by_an_earlier_run_is_replaced(self):
        os.symlink("/dev/ttys999", self.link)
        port = self.port()
        self.assertEqual(os.readlink(self.link), port.device)

    def test_the_folder_of_the_link_is_made(self):
        link = self.work / "build" / "emulator" / "serial"
        self.port(link=link)
        self.assertTrue(link.is_symlink())

    def test_a_relative_link_path_is_given_back_whole(self):
        before = os.getcwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, before)
        port = self.port(link="serial")
        self.assertEqual(os.path.realpath(os.path.dirname(port.link)), os.path.realpath(self.work))
        self.assertTrue(os.path.isabs(port.link))

    def test_a_path_that_holds_something_else_is_serial_unavailable_and_stays_untouched(self):
        self.link.write_bytes(b"not a link")
        folder = self.work / "folder"
        folder.mkdir()
        (folder / "kept").write_bytes(b"kept")
        for path in (self.link, folder):
            with self.assertRaises(failure.Failure) as caught:
                serialport.Port(path, Feed())
            self.assertEqual(caught.exception.reason, "serial-unavailable")
        self.assertEqual(self.link.read_bytes(), b"not a link")
        self.assertEqual([entry.name for entry in folder.iterdir()], ["kept"])

    def test_a_link_that_cannot_be_made_is_serial_unavailable(self):
        a_file = self.work / "file"
        a_file.write_bytes(b"")
        with self.assertRaises(failure.Failure) as caught:
            serialport.Port(a_file / "serial", Feed())
        self.assertEqual(caught.exception.reason, "serial-unavailable")
        self.assertEqual(a_file.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()

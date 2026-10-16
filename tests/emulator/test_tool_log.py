import os
import pathlib
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from odrigctl import cli

from . import support

if support.HAS_SERIAL:
    from emulator import serialport

# Ctrl-C to another program is SIGINT; Windows sends Ctrl+Break to the program's own group.
INTERRUPT = support.STOP if sys.platform == "win32" else signal.SIGINT

OK = '{"ok":true}\n'
READY = b"#log 0.001 test: ready\n"
SENT = (
    b"#log 1.000 usb: host started\n",
    b"boot: ready\n",
    b'{"ok":true}\n',
    b"#log 2.500 usb: a device came: maker 0781, product 5581, a stick\r\n",
    b"#lo",
    b"g 3.042 player: drive file a.odrg left out: size-mismatch\n",
    b"# log 4.000 not a line of the log\n",
    b"#log 5.000 usb: a device went\n",
)
PRINTED = [
    "#log 1.000 usb: host started",
    "#log 2.500 usb: a device came: maker 0781, product 5581, a stick",
    "#log 3.042 player: drive file a.odrg left out: size-mismatch",
    "#log 5.000 usb: a device went",
]


class Following:
    """The command tool with `--log` in a program of its own, and what it prints, line by
    line as it comes."""

    def __init__(self, *target):
        self.program = subprocess.Popen([sys.executable, "-m", "odrigctl", *target, "--log"], cwd=support.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                        creationflags=support.OWN_GROUP)
        self.lines = []
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self):
        for line in self.program.stdout:
            self.lines.append(line)

    def printed(self, count, seconds=10):
        """Waits until `count` lines other than READY were printed."""
        deadline = time.monotonic() + seconds
        while sum(line != READY.decode() for line in self.lines) < count and time.monotonic() < deadline and self.program.poll() is None:
            time.sleep(0.02)

    def until_ready(self, write, seconds=10):
        """Writes the line READY every tenth of a second until the tool prints it: from
        then on the tool reads what arrives."""
        deadline = time.monotonic() + seconds
        while not self.lines and time.monotonic() < deadline and self.program.poll() is None:
            write(READY)
            time.sleep(0.1)
        if not self.lines:
            raise AssertionError(f"the tool printed nothing: {self.program.poll()} {self.program.stderr.read() if self.program.poll() is not None else ''}")

    def stopped(self):
        """Interrupts the tool as Ctrl-C does, and gives its exit status, what it printed
        after the READY lines, and its errors."""
        if self.program.poll() is None:
            self.program.send_signal(INTERRUPT)
        status = self.program.wait(10)
        self._reader.join(5)
        error = self.program.stderr.read()
        self.program.stderr.close()
        self.program.stdout.close()
        return status, [line.rstrip("\n") for line in self.lines if line != READY.decode()], error

    def kill(self):
        if self.program.poll() is None:
            self.program.kill()
            self.program.wait(10)
        for pipe in (self.program.stdout, self.program.stderr):
            if not pipe.closed:
                pipe.close()


class LogTarget:
    """Stands in for a target that takes lines over TCP: accepts one connection, keeps what
    it is sent, and writes what the test gives it."""

    def __init__(self):
        self.received = b""
        self._listener = socket.socket()
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen()
        self.address = f"127.0.0.1:{self._listener.getsockname()[1]}"
        self._connected = threading.Event()
        self._connection = None
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        try:
            self._connection, _ = self._listener.accept()
        except OSError:
            return
        self._connected.set()
        while True:
            try:
                piece = self._connection.recv(4096)
            except OSError:
                return
            if not piece:
                return
            self.received += piece

    def write(self, data):
        if not self._connected.wait(10):
            raise AssertionError("the tool did not connect")
        self._connection.sendall(data)

    def hang_up(self):
        if not self._connected.wait(10):
            raise AssertionError("the tool did not connect")
        self._connection.shutdown(socket.SHUT_RDWR)
        self._connection.close()

    def close(self):
        self._listener.close()
        if self._connection is not None:
            try:
                self._connection.close()
            except OSError:
                pass
        self._thread.join(5)


class TheLog(unittest.TestCase):
    def follow(self, *target):
        following = Following(*target)
        self.addCleanup(following.kill)
        return following

    @support.needs_serial
    def test_it_prints_the_lines_of_the_log_of_a_serial_port_and_only_them_and_sends_nothing(self):
        work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        received = []
        port = serialport.Port(work / "serial", lambda data: received.append(data) or b"")
        self.addCleanup(port.close)
        port.start()
        following = self.follow("--port", port.link)
        following.until_ready(lambda data: os.write(port._near, data))
        for piece in SENT:
            os.write(port._near, piece)
            time.sleep(0.03)
        following.printed(len(PRINTED))
        status, printed, error = following.stopped()
        self.assertEqual((status, error), (0, ""))
        self.assertEqual(printed, PRINTED)
        self.assertEqual(b"".join(received), b"")

    def test_it_prints_the_lines_of_the_log_of_a_tcp_target_and_only_them_and_sends_nothing(self):
        target = LogTarget()
        self.addCleanup(target.close)
        following = self.follow("--tcp", target.address)
        following.until_ready(target.write)
        for piece in SENT:
            target.write(piece)
            time.sleep(0.03)
        following.printed(len(PRINTED))
        status, printed, error = following.stopped()
        self.assertEqual((status, error), (0, ""))
        self.assertEqual(printed, PRINTED)
        self.assertEqual(target.received, b"")

    def test_a_target_that_hangs_up_exits_with_3(self):
        target = LogTarget()
        self.addCleanup(target.close)
        following = self.follow("--tcp", target.address)
        following.until_ready(target.write)
        target.hang_up()
        status = following.program.wait(10)
        error = following.program.stderr.read()
        self.assertEqual(status, 3)
        self.assertRegex(error, r"\Aerror: unreachable: .+\n\Z")

    def test_a_target_that_cannot_be_reached_exits_with_3(self):
        with tempfile.TemporaryDirectory() as work:
            result = support.run_tool("--port", pathlib.Path(work) / "no-such-port", "--log")
        self.assertEqual((result.status, result.out), (3, ""))
        self.assertRegex(result.err, r"\Aerror: unreachable: .+no-such-port.+\n\Z")
        result = support.run_tool("--tcp", f"127.0.0.1:{support.free_port()}", "--log")
        self.assertEqual((result.status, result.out), (3, ""))
        self.assertRegex(result.err, r"\Aerror: unreachable: .+\n\Z")

    def test_it_goes_with_a_port_or_a_tcp_address_and_no_command(self):
        for argv, said in (
            (["--http", "a", "--log"], "--log goes with --port or --tcp"),
            (["--port", "a", "--log", "status"], "--log takes no command"),
            (["--tcp", "127.0.0.1:1", "--log", "play", "2"], "--log takes no command"),
            (["--log"], "one of the arguments --port --tcp --http is required"),
            (["--port", "a"], "a command is needed"),
        ):
            result = support.run_tool(*argv)
            self.assertEqual((result.status, result.out), (2, ""), argv)
            self.assertIn("usage:", result.err)
            self.assertIn(said, result.err)
        self.assertIn("--log", cli.parser().format_help())


class RepliesBetweenTheLog(unittest.TestCase):
    """A command takes its reply whatever lines of the log come before it."""

    def test_a_command_takes_the_reply_that_comes_after_lines_of_the_log_over_tcp(self):
        from .test_tool_tcp import Target

        with Target(b"#log 1.000 usb: host started\n", b"#log 1.200 usb: a dev", b"ice went\n" + OK.encode()) as target:
            result = support.run_tool("--tcp", target.address, "status")
        self.assertEqual((result.status, result.out, result.err), (0, OK, ""))

    @support.needs_serial
    def test_a_command_takes_the_reply_that_comes_after_lines_of_the_log_on_a_serial_port(self):
        work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        port = serialport.Port(work / "serial", lambda data: b"#log 1.000 usb: host started\n#log 1.001 player: x\n" + OK.encode() if b"\n" in data else b"")
        self.addCleanup(port.close)
        port.start()
        result = support.run_tool("--port", port.link, "status")
        self.assertEqual((result.status, result.out, result.err), (0, OK, ""))


if __name__ == "__main__":
    unittest.main()

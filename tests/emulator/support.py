"""Helpers shared by the tests of the emulator: where things are and how shows are packed."""

import base64
import collections
import contextlib
import http.client
import io
import json
import os
import pathlib
import select
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

from emulator import app
from odrig import pack
from tests.core import support as core_support
from tests.core.support import ReferencePlayer

from . import LIBRARY, ROOT

HEADER = ROOT / "core" / "include" / "odrig_core.h"
EXAMPLE_SHOW = ROOT / "shows" / "example" / "show.json"
TWO_LEGS = ROOT / "mapping" / "legs-2.json"
TARGET = ROOT / "mapping" / "legs-20.json"
DEMO_SHOW = ROOT / "shows" / "demo-20" / "show.json"

# Whether the emulator has its virtual serial port on this system, and the signal a test
# ends an emulator with: where a child cannot be sent a termination signal, the break of
# the console, which reaches a child in a process group of its own.
HAS_SERIAL = app.HAS_SERIAL
NO_SERIAL = "this system has no pseudo-terminal"
STOP = getattr(signal, "CTRL_BREAK_EVENT", signal.SIGTERM)
OWN_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


@contextlib.contextmanager
def packed(show, mapping, sources, compressed=True):
    """A temporary folder that holds a show as `python -m odrig pack` installs it."""
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder, "show")
        pack.pack(show, mapping, sources, out, compressed=compressed)
        yield out


def example_show():
    """The example show, packed on the two-leg mapping into a temporary folder."""
    return packed(EXAMPLE_SHOW, TWO_LEGS, ROOT / "animations")


@contextlib.contextmanager
def demo_show():
    """The demo show on the target file in a temporary folder: the files the converter
    packs from what its generators write for that file."""
    with tempfile.TemporaryDirectory() as folder:
        yield installed(pathlib.Path(folder, "show"), core_support.demo_show())


def files_of(folder):
    """The installed files of a folder: the content of each by its name."""
    return {path.name: path.read_bytes() for path in sorted(pathlib.Path(folder).iterdir()) if path.is_file()}


Result = collections.namedtuple("Result", "status out err")


def run(*argv):
    """Runs one command line of the emulator in this interpreter."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = app.main([str(argument) for argument in argv])
        except SystemExit as stopped:
            status = stopped.code
    return Result(status, out.getvalue(), err.getvalue())


def run_tool(*argv):
    """Runs one command line of the command tool in this interpreter."""
    from odrigctl import cli

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = cli.main([str(argument) for argument in argv])
        except SystemExit as stopped:
            status = stopped.code
    return Result(status, out.getvalue(), err.getvalue())


def run_module(*argv, module="emulator", cwd=ROOT):
    """Runs `python -m <module>` in a fresh interpreter, from the repository root."""
    done = subprocess.run(
        [sys.executable, "-m", module, *(str(argument) for argument in argv)], cwd=cwd, capture_output=True, text=True
    )
    return Result(done.returncode, done.stdout, done.stderr)


def reference(files, ticks, commands=()):
    """What the reference player of the core's suite does with an installed file set.

    `ticks` are the times at which a refresh is asked for, and `commands` holds
    `(time, line)` in the order they are sent: each is given with its own time before the
    first tick that is not earlier, and after the last tick when none is. Returns
    `(refreshes, replies)`: for each tick `None` when no refresh was due, or each leg's
    LED data in the order of the mapping file; and the reply to each command.
    """
    player = ReferencePlayer(files)
    waiting = collections.deque(commands)
    refreshes = []
    replies = []

    def send(until):
        while waiting and (until is None or waiting[0][0] <= until):
            time, line = waiting.popleft()
            replies.append(player.command(time, line if isinstance(line, bytes) else line.encode("utf-8")))

    for now in ticks:
        send(now)
        refresh = player.poll(now)
        refreshes.append(None if refresh is None else tuple(rgb for _, rgb in refresh))
    send(None)
    return refreshes, replies


def installed(folder, files):
    """Writes these files, given as a mapping from name to content, into a folder."""
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (folder / name).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return folder


def without_fps(reply):
    """A reply as a value, without the one member that depends on the speed of this Mac."""
    value = json.loads(reply)
    value.pop("fps", None)
    return value


Response = collections.namedtuple("Response", "status headers body")


class Emulator:
    """The emulator in real time, as a child process on a free port.

    `lines` holds what it has printed to standard output so far, `port` the port of the
    page address it named, `serial` the path of its serial port and `tcp` the address of
    its line port, each `None` when it has none. Without `serial_link` the link to the
    serial port is made in a temporary folder. Where there is no serial port the line port
    is opened on a free port; elsewhere `tcp_port` asks for it.
    """

    START_SECONDS = 15

    def __init__(self, folder, *options, port=0, serial_link=None, tcp_port=None):
        self._temporary = None
        command = [sys.executable, "-m", "emulator", str(folder), "--port", str(port)]
        if HAS_SERIAL:
            if serial_link is None:
                self._temporary = tempfile.TemporaryDirectory()
                serial_link = pathlib.Path(self._temporary.name, "serial")
            command += ["--serial-link", str(serial_link)]
        elif tcp_port is None:
            tcp_port = 0
        if tcp_port is not None:
            command += ["--tcp-port", str(tcp_port)]
        self.process = subprocess.Popen(
            [*command, *(str(option) for option in options)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=OWN_GROUP,
        )
        self.lines = []
        self._errors = []
        self._printed = threading.Condition()
        self._readers = [
            threading.Thread(target=self._read, args=(self.process.stdout, self.lines), daemon=True),
            threading.Thread(target=self._read, args=(self.process.stderr, self._errors), daemon=True),
        ]
        for reader in self._readers:
            reader.start()
        self._result = None
        try:
            self.url = self._printed_line("page: ")
            self.port = int(self.url.rstrip("/").rsplit(":", 1)[1])
            self.serial = self._printed_line("serial: ") if HAS_SERIAL else None
            self.tcp = self._printed_line("tcp: ") if tcp_port is not None else None
        except BaseException:
            self.stop()
            raise

    def _read(self, pipe, lines):
        for line in iter(pipe.readline, b""):
            with self._printed:
                lines.append(line.decode("utf-8", "replace").rstrip("\r\n"))
                self._printed.notify_all()
        with self._printed:
            self._printed.notify_all()

    def _printed_line(self, start):
        """What follows `start` in the line of standard output that begins with it."""
        deadline = time.monotonic() + self.START_SECONDS
        with self._printed:
            while True:
                for line in self.lines:
                    if line.startswith(start):
                        return line[len(start):]
                if self.process.poll() is not None and not any(reader.is_alive() for reader in self._readers):
                    raise AssertionError(f"the emulator ended with status {self.process.returncode}: {self._errors}")
                left = deadline - time.monotonic()
                if left <= 0:
                    raise AssertionError(f"the emulator printed no line that begins with {start!r}: {self.lines} {self._errors}")
                self._printed.wait(min(left, 0.05))

    def request(self, method="POST", path="/odrig", body=None, headers=None):
        """One HTTP request on a connection of its own."""
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            answer = connection.getresponse()
            return Response(answer.status, {name.lower(): value for name, value in answer.getheaders()}, answer.read())
        finally:
            connection.close()

    def command(self, line):
        """The reply to a command line sent over HTTP."""
        answer = self.request(body=line if isinstance(line, bytes) else line.encode("utf-8"))
        if answer.status != 200:
            raise AssertionError(f"POST /odrig gave status {answer.status}")
        return answer.body

    def status(self):
        """The status the core reports, as a value."""
        return json.loads(self.command("status"))

    def send_signal(self, number):
        self.process.send_signal(number)

    def stop(self, number=STOP):
        """Ends the emulator with a signal and gives its exit status and what it printed."""
        if self._result is None:
            if self.process.poll() is None:
                self.process.send_signal(number)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            for reader in self._readers:
                reader.join(timeout=5)
            self.process.stdout.close()
            self.process.stderr.close()
            self._result = Result(self.process.returncode, "".join(f"{line}\n" for line in self.lines), "".join(f"{line}\n" for line in self._errors))
            if self._temporary is not None:
                self._temporary.cleanup()
        return self._result

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stop()


def raw_request(port, data, seconds=5):
    """Sends bytes to the page address and gives everything that comes back until the
    server closes the connection or stays silent."""
    with socket.create_connection(("127.0.0.1", port), timeout=seconds) as connection:
        connection.sendall(data)
        received = b""
        try:
            while True:
                piece = connection.recv(65536)
                if not piece:
                    break
                received += piece
        except socket.timeout:
            pass
        return received


def free_port():
    """A port number on 127.0.0.1 that nothing listens on at this moment."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def refused(port, address="127.0.0.1"):
    """Whether nothing accepts a connection at that port."""
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    with socket.socket(family) as probe:
        probe.settimeout(2)
        try:
            probe.connect((address, port))
        except OSError:
            return True
        return False


def entered(case, context):
    """Enters a context for the length of a test class, or of a test, and gives its value."""
    value = context.__enter__()
    cleanup = case.addClassCleanup if isinstance(case, type) else case.addCleanup
    cleanup(context.__exit__, None, None, None)
    return value


class Serial:
    """A program's end of a serial port. Opening it changes none of the port's settings."""

    def __init__(self, path):
        self.fd = os.open(str(path), os.O_RDWR | os.O_NOCTTY)

    def write(self, data):
        while data:
            data = data[os.write(self.fd, data):]

    def read_lines(self, count=1, seconds=5):
        """What arrives until it holds `count` newlines, or until the time is over."""
        received = b""
        deadline = time.monotonic() + seconds
        while received.count(b"\n") < count:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([self.fd], [], [], left)[0]:
                break
            received += os.read(self.fd, 4096)
        return received

    def read_for(self, seconds):
        """Everything that arrives within a length of time."""
        received = b""
        deadline = time.monotonic() + seconds
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return received
            if select.select([self.fd], [], [], left)[0]:
                received += os.read(self.fd, 4096)

    def ask(self, line, seconds=5):
        """Sends one command line and gives its reply."""
        self.write(line if isinstance(line, bytes) else line.encode("utf-8") + b"\n")
        return self.read_lines(1, seconds)

    def close(self):
        os.close(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class Lines:
    """A program's end of a connection to a port that takes lines over TCP, named as
    `host:port`."""

    def __init__(self, address, seconds=5):
        host, _, port = address.rpartition(":")
        self.socket = socket.create_connection((host, int(port)), timeout=seconds)

    def write(self, data):
        self.socket.sendall(data)

    def read_lines(self, count=1, seconds=5):
        """What arrives until it holds `count` newlines, or until the time is over or the
        other end closes."""
        received = b""
        deadline = time.monotonic() + seconds
        while received.count(b"\n") < count:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([self.socket], [], [], left)[0]:
                break
            piece = self.socket.recv(4096)
            if not piece:
                break
            received += piece
        return received

    def read_for(self, seconds):
        """Everything that arrives within a length of time."""
        received = b""
        deadline = time.monotonic() + seconds
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return received
            if select.select([self.socket], [], [], left)[0]:
                piece = self.socket.recv(4096)
                if not piece:
                    return received
                received += piece

    def ask(self, line, seconds=5):
        """Sends one command line and gives its reply."""
        self.write(line if isinstance(line, bytes) else line.encode("utf-8") + b"\n")
        return self.read_lines(1, seconds)

    def close(self):
        self.socket.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

Event = collections.namedtuple("Event", "kind data")


class EventStream:
    """A page's end of the event stream, read only when a test asks.

    `receive_buffer` asks the system for a small buffer, so that a test which stops
    reading is soon felt by the emulator.
    """

    def __init__(self, port, receive_buffer=None, path="/events"):
        self.socket = socket.socket()
        if receive_buffer is not None:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receive_buffer)
        self.socket.settimeout(10)
        self.socket.connect(("127.0.0.1", port))
        self.socket.sendall(f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nAccept: text/event-stream\r\n\r\n".encode("ascii"))
        self._buffer = b""
        while b"\r\n\r\n" not in self._buffer:
            piece = self.socket.recv(4096)
            if not piece:
                raise AssertionError(f"the event stream ended inside its headers: {self._buffer!r}")
            self._buffer += piece
        head, self._buffer = self._buffer.split(b"\r\n\r\n", 1)
        status_line, *header_lines = head.decode("iso-8859-1").split("\r\n")
        self.status = int(status_line.split(" ")[1])
        self.headers = {name.strip().lower(): value.strip() for name, value in (line.split(":", 1) for line in header_lines)}
        self.ended = False

    def _parsed(self):
        events = []
        while b"\n\n" in self._buffer:
            block, self._buffer = self._buffer.split(b"\n\n", 1)
            lines = block.decode("utf-8").split("\n")
            if lines[0].startswith(":"):
                events.append(Event("comment", lines[0][1:].strip()))
                continue
            fields = dict(line.split(": ", 1) for line in lines)
            if set(fields) != {"event", "data"}:
                raise AssertionError(f"an event with other fields than event and data: {block!r}")
            events.append(Event(fields["event"], fields["data"]))
        return events

    def read_until(self, enough, seconds=10):
        """Reads events until `enough(events)` is true for the ones read by this call, or
        the time is over. Returns them."""
        events = self._parsed()
        deadline = time.monotonic() + seconds
        while not enough(events) and not self.ended:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([self.socket], [], [], left)[0]:
                break
            piece = self.socket.recv(65536)
            if not piece:
                self.ended = True
            self._buffer += piece
            events += self._parsed()
        return events

    def read_for(self, seconds):
        """The events that arrive within a length of time."""
        return self.read_until(lambda events: False, seconds)

    def close(self):
        self.socket.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def frames(events):
    """`(timestamp, LED bytes)` of every `frame` event among these events."""
    found = []
    for event in events:
        if event.kind == "frame":
            ms, _, encoded = event.data.partition(" ")
            found.append((int(ms), base64.b64decode(encoded, validate=True)))
    return found


def of_kind(events, kind):
    """The data of every event of one kind, read as JSON."""
    return [json.loads(event.data) for event in events if event.kind == kind]

"""Helpers shared by the tests of the emulator: where things are and how shows are packed."""

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
from tests.core.support import ReferencePlayer

from . import LIBRARY, ROOT

HEADER = ROOT / "core" / "include" / "odrig_core.h"
EXAMPLE_SHOW = ROOT / "shows" / "example" / "show.json"
TWO_LEGS = ROOT / "mapping" / "legs-2.json"
TEN_LEGS = ROOT / "mapping" / "legs-10.json"


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
    page address it named, and `serial` the path of its serial port. Without `serial_link`
    the link to the port is made in a temporary folder.
    """

    START_SECONDS = 15

    def __init__(self, folder, *options, port=0, serial_link=None):
        self._temporary = None
        if serial_link is None:
            self._temporary = tempfile.TemporaryDirectory()
            serial_link = pathlib.Path(self._temporary.name, "serial")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "emulator", str(folder), "--port", str(port), "--serial-link", str(serial_link), *(str(option) for option in options)],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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
            self.serial = self._printed_line("serial: ")
        except BaseException:
            self.stop()
            raise

    def _read(self, pipe, lines):
        for line in iter(pipe.readline, b""):
            with self._printed:
                lines.append(line.decode("utf-8", "replace").rstrip("\n"))
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

    def stop(self, number=signal.SIGTERM):
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

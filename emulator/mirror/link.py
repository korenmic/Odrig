"""The mirror's link to a board: its USB serial port, another emulator's line port, or HTTP.

A link over a serial port or TCP carries lines both ways on one stream, opened as the command
tool opens it, never resetting the chip. What arrives on it is cut into lines: a reply goes
to `replied`, a `#plan` line to `planned` without its mark, and every other line to `heard`;
`lost` is told once when the stream breaks. A link over HTTP posts each line as a request of
its own, as a phone does.
"""

import threading

from odrigctl import client

# How long the reader waits for bytes at a time, and how long a line may take to be written.
READ_SECONDS = 0.05
WRITE_SECONDS = 5.0
PLAN_MARK = b"#plan "
# A line that grows past this without its end is dropped; a reply is 1,024 bytes at most.
LINE_LIMIT = 65536


class Lost(Exception):
    """The link could not be opened, or it broke."""


class StreamLink:
    """A link that carries lines both ways on one stream. The stream's reader closes it when
    it ends, whoever asked for the end."""

    streamed = True

    def __init__(self, name):
        self.name = name
        self.replied = self.planned = self.heard = lambda line: None
        self.lost = lambda reason: None
        self._lock = threading.Lock()
        self._stream = None
        self._ending = None
        self._reader = None

    def open(self):
        """Opens the stream and starts its reader; `Lost` when it cannot be opened."""
        try:
            stream = self._open()
        except client.Unreachable as error:
            raise Lost(str(error)) from None
        ending = threading.Event()
        with self._lock:
            self._stream, self._ending = stream, ending
        self._reader = threading.Thread(target=self._read, args=(stream, ending), name="mirror-link", daemon=True)
        self._reader.start()

    def send(self, line):
        """Writes one line and its newline; `Lost` when the stream takes it no more."""
        with self._lock:
            stream, ending = self._stream, self._ending
        if stream is None:
            raise Lost(f"{self.name}: the link is not open")
        try:
            client._give(stream, line + b"\n", WRITE_SECONDS)
        except (OSError, client.Unreachable) as error:
            reason = f"{self.name}: {getattr(error, 'strerror', None) or error}"
            self._end(stream, ending, reason)
            raise Lost(reason) from None

    def close(self):
        """Ends the link without telling `lost`, and waits for its reader to close the
        stream."""
        with self._lock:
            stream, ending, self._stream = self._stream, self._ending, None
            reader = self._reader
        if stream is not None:
            ending.set()
        if reader is not None and reader is not threading.current_thread():
            reader.join(WRITE_SECONDS + 1)

    def _end(self, stream, ending, reason):
        """The stream broke: it is let go, and `lost` is told, once."""
        with self._lock:
            if self._stream is not stream:
                return
            self._stream = None
        ending.set()
        self.lost(reason)

    def _read(self, stream, ending):
        waiting = b""
        try:
            while not ending.is_set():
                try:
                    for piece in client._take(stream, READ_SECONDS):
                        *lines, waiting = (waiting + piece).split(b"\n")
                        for line in lines:
                            self._sort(line[:-1] if line.endswith(b"\r") else line)
                        if len(waiting) > LINE_LIMIT:
                            waiting = b""
                except (OSError, ValueError) as error:
                    self._end(stream, ending, f"{self.name}: {getattr(error, 'strerror', None) or error}")
                    return
                if getattr(stream, "closed", False):
                    self._end(stream, ending, f"{self.name}: the other end closed the connection")
                    return
        finally:
            try:
                client._shut(stream)
            except OSError:
                pass

    def _sort(self, line):
        if line.startswith(PLAN_MARK):
            self.planned(line[len(PLAN_MARK):])
        elif client.is_reply(line):
            self.replied(line)
        elif line:
            self.heard(line)


class SerialLink(StreamLink):
    """A serial port, opened as the command tool opens one and kept open."""

    kind = "serial"

    def _open(self):
        return client._ready(self.name)


class TcpLink(StreamLink):
    """The line port of another emulator, `host:port`."""

    kind = "tcp"

    def _open(self):
        return client._connected(self.name, WRITE_SECONDS)


class HttpLink:
    """A board or an emulator over HTTP: each line is a request of its own, `POST /odrig`."""

    streamed = False
    kind = "http"

    def __init__(self, address):
        self.name = address

    def exchange(self, line, seconds):
        """Posts one line and returns its reply with its line end; `Lost` when no response
        with status 200 came within the time."""
        try:
            return client.http_exchange(self.name, line, seconds) + b"\n"
        except client.Unreachable as error:
            raise Lost(str(error)) from None


def made(kind, name):
    """The link of an option of the emulator: `serial`, `tcp` or `http`, and its name."""
    return {"serial": SerialLink, "tcp": TcpLink, "http": HttpLink}[kind](name)


def checked_tcp(text):
    """The address of `--mirror-tcp`, `host:port`, or `ValueError`."""
    client.tcp_address(text)
    return text

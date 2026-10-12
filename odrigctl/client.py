"""Exchanges with a target: a line out and its reply back, over serial or over HTTP.

`serial_exchange` and `http_exchange` are one exchange each, for one command. A `Session`
is several exchanges with the same target, and through a serial port it keeps the port open
for all of them.
"""

import fcntl
import http.client
import json
import os
import select
import struct
import termios
import time

SETTLE_SECONDS = 0.2
DISCARD_SECONDS = 0.1
COMMAND_PATH = "/odrig"
CONTENT_TYPE = "application/octet-stream"


class Unreachable(Exception):
    """The target cannot be reached, or did not answer within the time limit."""


def is_reply(line):
    """Whether a received line is a reply: a JSON object that has a member `ok`."""
    try:
        value = json.loads(line)
    except ValueError:
        return False
    return isinstance(value, dict) and "ok" in value


def _open(port):
    """Opens a serial port without resetting what is behind it.

    The modem lines are lowered RTS first, DTR second: DTR low while RTS is still high is
    the combination that resets the chip. A port without modem lines refuses the requests,
    which is ignored.
    """
    descriptor = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        settings = termios.tcgetattr(descriptor)
        settings[0] = settings[1] = settings[3] = 0
        settings[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        settings[4] = settings[5] = termios.B115200
        settings[6][termios.VMIN] = 0
        settings[6][termios.VTIME] = 0
        termios.tcsetattr(descriptor, termios.TCSANOW, settings)
        for line in (termios.TIOCM_RTS, termios.TIOCM_DTR):
            try:
                fcntl.ioctl(descriptor, termios.TIOCMBIC, struct.pack("I", line))
            except OSError:
                pass
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _received(descriptor, seconds):
    """What arrives within a length of time, in pieces as they come."""
    deadline = time.monotonic() + seconds
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            return
        if select.select([descriptor], [], [], left)[0]:
            try:
                piece = os.read(descriptor, 65536)
            except BlockingIOError:
                continue
            if piece:
                yield piece
            else:
                time.sleep(0.01)


def _write(descriptor, data, seconds):
    deadline = time.monotonic() + seconds
    while data:
        try:
            data = data[os.write(descriptor, data):]
        except BlockingIOError:
            left = deadline - time.monotonic()
            if left <= 0:
                raise Unreachable("the port takes no more bytes") from None
            select.select([], [descriptor], [], left)


def _named(port, error):
    return Unreachable(f"{port}: {error.strerror or type(error).__name__}")


def _ready(port):
    """Opens a serial port, lets it settle, and discards what was waiting in it."""
    try:
        descriptor = _open(port)
    except OSError as error:
        raise _named(port, error) from None
    except termios.error:
        raise Unreachable(f"{port}: this is not a serial port") from None
    try:
        time.sleep(SETTLE_SECONDS)
        for _ in _received(descriptor, DISCARD_SECONDS):
            pass
    except OSError as error:
        os.close(descriptor)
        raise _named(port, error) from None
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _arrived(descriptor):
    """What a port has received and not given yet, without waiting for more."""
    received = b""
    while True:
        try:
            piece = os.read(descriptor, 65536)
        except BlockingIOError:
            return received
        if not piece:
            return received
        received += piece


def _exchanged(descriptor, port, data, timeout, accept, waiting=b""):
    """Sends bytes to an open port. Returns the first received line that `accept` takes,
    without its line end, and what arrived after it. Every other line is dropped.
    `waiting` is the beginning of a line that arrived before the bytes are sent."""
    try:
        _write(descriptor, data, timeout)
    except OSError as error:
        raise _named(port, error) from None
    try:
        for piece in _received(descriptor, timeout):
            waiting += piece
            while b"\n" in waiting:
                line, waiting = waiting.split(b"\n", 1)
                line = line.rstrip(b"\r")
                if accept(line):
                    return line, waiting
    except OSError as error:
        raise _named(port, error) from None
    raise Unreachable(f"{port}: no reply within {timeout:g} seconds")


def serial_exchange(port, data, timeout, accept=is_reply):
    """Sends bytes to a serial port and returns the first received line that `accept`
    takes, without its line end. Every other line is dropped.

    What was waiting in the port when it was opened is discarded first.
    """
    descriptor = _ready(port)
    try:
        return _exchanged(descriptor, port, data, timeout, accept)[0]
    finally:
        os.close(descriptor)


def http_exchange(address, line, timeout):
    """Sends one line as the body of `POST http://ADDRESS/odrig` and returns the reply,
    without its line end.

    The address is `host` or `host:port`, with or without `http://` in front and a `/` at
    its end.
    """
    host = address[len("http://"):] if address.startswith("http://") else address
    host = host[:-1] if host.endswith("/") else host
    try:
        connection = http.client.HTTPConnection(host, timeout=timeout)
    except (http.client.HTTPException, ValueError) as error:
        raise Unreachable(f"{address}: {error}") from None
    try:
        connection.request("POST", COMMAND_PATH, body=line, headers={"Content-Type": CONTENT_TYPE})
        answer = connection.getresponse()
        body = answer.read()
    except (OSError, http.client.HTTPException) as error:
        raise Unreachable(f"{address}: {getattr(error, 'strerror', None) or error or type(error).__name__}") from None
    finally:
        connection.close()
    if answer.status != 200:
        raise Unreachable(f"{address}: status {answer.status} for POST {COMMAND_PATH}")
    return body[:-1] if body.endswith(b"\n") else body


class Session:
    """Several exchanges with one target, one after the other.

    Through a serial port the port is opened once, as `serial_exchange` opens it, and stays
    open until `close`. A line that arrived whole before a line is sent is no answer to
    it and is dropped. Over HTTP every exchange is one request, and `close` does nothing.
    """

    def __init__(self, port=None, http=None, timeout=2.0):
        if (port is None) == (http is None):
            raise ValueError("a session is with a port or with an address, one of the two")
        self.port = port
        self.http = http
        self.timeout = timeout
        self._waiting = b""
        self._descriptor = None if port is None else _ready(port)

    def exchange(self, line):
        """Sends one line, with its newline, and returns the reply without its line end.
        Raises `Unreachable` when none arrives in time."""
        if self.http is not None:
            reply = http_exchange(self.http, line, self.timeout)
            if not is_reply(reply):
                raise Unreachable(f"{self.http}: the answer is not a reply")
            return reply
        if self._descriptor is None:
            raise Unreachable(f"{self.port}: the session is closed")
        try:
            # Of what arrived since the last reply, only the beginning of a line that has
            # not ended yet can still become part of the answer.
            fresh = (self._waiting + _arrived(self._descriptor)).rsplit(b"\n", 1)[-1]
        except OSError as error:
            raise _named(self.port, error) from None
        reply, self._waiting = _exchanged(self._descriptor, self.port, line, self.timeout, is_reply, fresh)
        return reply

    def discard(self, seconds):
        """Drops what arrives through the port within a length of time: a reply that comes
        after its exchange has given up would be taken for the answer of the next one."""
        if self._descriptor is not None:
            self._waiting = b""
            try:
                for _ in _received(self._descriptor, seconds):
                    pass
            except OSError as error:
                raise _named(self.port, error) from None

    def close(self):
        if self._descriptor is not None:
            os.close(self._descriptor)
            self._descriptor = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

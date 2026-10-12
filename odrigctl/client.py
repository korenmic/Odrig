"""Exchanges with a target: a line out and its reply back, over serial, over TCP or over
HTTP.

`serial_exchange`, `tcp_exchange` and `http_exchange` are one exchange each, for one
command. A `Session` is several exchanges with the same target, and through a serial port
or over TCP it keeps the port or the connection open for all of them.
"""

import http.client
import json
import os
import select
import socket
import struct
import time

from . import winserial

try:
    import fcntl
    import termios
except ImportError:
    fcntl = termios = None

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


class _Connection:
    """A connection to a target that takes lines over TCP, with what an open serial port
    of Windows has: `received`, `write`, `arrived` and `close`."""

    def __init__(self, address, timeout):
        self._socket = socket.create_connection(tcp_address(address), timeout=timeout)

    def received(self, seconds):
        """What arrives within a length of time, in pieces as they come. It ends early
        when the other end closes."""
        deadline = time.monotonic() + seconds
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return
            self._socket.settimeout(left)
            try:
                piece = self._socket.recv(65536)
            except TimeoutError:
                return
            if not piece:
                return
            yield piece

    def write(self, data, seconds):
        self._socket.settimeout(seconds)
        self._socket.sendall(data)

    def arrived(self):
        """What has arrived and was not given yet, without waiting for more."""
        received = b""
        self._socket.setblocking(False)
        while True:
            try:
                piece = self._socket.recv(65536)
            except BlockingIOError:
                return received
            if not piece:
                return received
            received += piece

    def close(self):
        self._socket.close()


# An open port is the descriptor `_open` gives where the system has `termios`, and elsewhere
# an object: the serial port of Windows, or a connection. These four do with either what
# the functions above do with a descriptor.

def _take(opened, seconds):
    return _received(opened, seconds) if isinstance(opened, int) else opened.received(seconds)


def _give(opened, data, seconds):
    if isinstance(opened, int):
        _write(opened, data, seconds)
    else:
        opened.write(data, seconds)


def _had(opened):
    return _arrived(opened) if isinstance(opened, int) else opened.arrived()


def _shut(opened):
    if isinstance(opened, int):
        os.close(opened)
    else:
        opened.close()


def _ready(port):
    """Opens a serial port in the way of this system, lets it settle, and discards what was
    waiting in it."""
    not_serial = () if termios is None else (termios.error,)
    try:
        descriptor = winserial.Port(port) if termios is None else _open(port)
    except OSError as error:
        raise _named(port, error) from None
    except not_serial:
        raise Unreachable(f"{port}: this is not a serial port") from None
    try:
        time.sleep(SETTLE_SECONDS)
        for _ in _take(descriptor, DISCARD_SECONDS):
            pass
    except OSError as error:
        _shut(descriptor)
        raise _named(port, error) from None
    except BaseException:
        _shut(descriptor)
        raise
    return descriptor


def tcp_address(address):
    """`(host, port)` of an address written as `host:port`, or `ValueError`."""
    host, colon, port = address.rpartition(":")
    host = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    if not colon or not host or not (port.isascii() and port.isdigit()) or not 0 < int(port) < 65536:
        raise ValueError(f"{address!r} is not host:port")
    return host, int(port)


def _connected(address, timeout):
    """Connects to a target that takes lines over TCP, at `host:port`."""
    try:
        return _Connection(address, timeout)
    except ValueError as error:
        raise Unreachable(str(error)) from None
    except OSError as error:
        raise _named(address, error) from None


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
        _give(descriptor, data, timeout)
    except OSError as error:
        raise _named(port, error) from None
    try:
        for piece in _take(descriptor, timeout):
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
        _shut(descriptor)


def tcp_exchange(address, data, timeout, accept=is_reply):
    """Sends bytes to a target that takes lines over TCP, at `host:port`, and returns the
    first received line that `accept` takes, without its line end. Every other line is
    dropped."""
    connection = _connected(address, timeout)
    try:
        return _exchanged(connection, address, data, timeout, accept)[0]
    finally:
        _shut(connection)


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
    open until `close`; over TCP the connection does. A line that arrived whole before a
    line is sent is no answer to it and is dropped. Over HTTP every exchange is one request,
    and `close` does nothing.
    """

    def __init__(self, port=None, http=None, timeout=2.0, tcp=None):
        if sum(target is not None for target in (port, tcp, http)) != 1:
            raise ValueError("a session is with a port or with an address, one of them")
        self.port = port if tcp is None else tcp
        self.http = http
        self.timeout = timeout
        self._waiting = b""
        self._descriptor = None if http is not None else _ready(port) if tcp is None else _connected(tcp, timeout)

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
            fresh = (self._waiting + _had(self._descriptor)).rsplit(b"\n", 1)[-1]
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
                for _ in _take(self._descriptor, seconds):
                    pass
            except OSError as error:
                raise _named(self.port, error) from None

    def close(self):
        if self._descriptor is not None:
            _shut(self._descriptor)
            self._descriptor = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

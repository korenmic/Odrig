"""One exchange with a target: a line out and its reply back, over serial, over TCP or
over HTTP."""

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


class _Posix:
    """A serial port of a system that has `termios`, as an exchange uses it."""

    def __init__(self, port):
        self._descriptor = _open(port)

    def received(self, seconds):
        return _received(self._descriptor, seconds)

    def write(self, data, seconds):
        _write(self._descriptor, data, seconds)

    def close(self):
        os.close(self._descriptor)


def _serial(port):
    """Opens a serial port in the way of this system."""
    not_serial = () if termios is None else (termios.error,)
    try:
        return winserial.Port(port) if termios is None else _Posix(port)
    except OSError as error:
        raise Unreachable(f"{port}: {error.strerror or type(error).__name__}") from None
    except not_serial:
        raise Unreachable(f"{port}: this is not a serial port") from None


def _first(pieces, accept):
    """The first line among received pieces that `accept` takes, without its line end, or
    `None` when the pieces end before one came."""
    waiting = b""
    for piece in pieces:
        waiting += piece
        while b"\n" in waiting:
            line, waiting = waiting.split(b"\n", 1)
            line = line.rstrip(b"\r")
            if accept(line):
                return line
    return None


def serial_exchange(port, data, timeout, accept=is_reply):
    """Sends bytes to a serial port and returns the first received line that `accept`
    takes, without its line end. Every other line is dropped.

    What was waiting in the port when it was opened is discarded first.
    """
    opened = _serial(port)
    try:
        try:
            time.sleep(SETTLE_SECONDS)
            for _ in opened.received(DISCARD_SECONDS):
                pass
            opened.write(data, timeout)
            line = _first(opened.received(timeout), accept)
        except OSError as error:
            raise Unreachable(f"{port}: {error.strerror or type(error).__name__}") from None
        if line is None:
            raise Unreachable(f"{port}: no reply within {timeout:g} seconds")
        return line
    finally:
        opened.close()


def tcp_address(address):
    """`(host, port)` of an address written as `host:port`, or `ValueError`."""
    host, colon, port = address.rpartition(":")
    host = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    if not colon or not host or not (port.isascii() and port.isdigit()) or not 0 < int(port) < 65536:
        raise ValueError(f"{address!r} is not host:port")
    return host, int(port)


def _from(connection, seconds):
    """What a connection sends within a length of time, in pieces as they come. It ends
    early when the other end closes."""
    deadline = time.monotonic() + seconds
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            return
        connection.settimeout(left)
        try:
            piece = connection.recv(65536)
        except TimeoutError:
            return
        if not piece:
            return
        yield piece


def tcp_exchange(address, data, timeout, accept=is_reply):
    """Sends bytes to a target that takes lines over TCP, at `host:port`, and returns the
    first received line that `accept` takes, without its line end. Every other line is
    dropped."""
    try:
        connection = socket.create_connection(tcp_address(address), timeout=timeout)
    except ValueError as error:
        raise Unreachable(str(error)) from None
    except OSError as error:
        raise Unreachable(f"{address}: {error.strerror or type(error).__name__}") from None
    try:
        try:
            connection.sendall(data)
            line = _first(_from(connection, timeout), accept)
        except OSError as error:
            raise Unreachable(f"{address}: {error.strerror or type(error).__name__}") from None
        if line is None:
            raise Unreachable(f"{address}: no reply within {timeout:g} seconds")
        return line
    finally:
        connection.close()

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

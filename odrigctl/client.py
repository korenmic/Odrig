"""One exchange with a target: a line out and its reply back, over serial or over HTTP."""

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


def serial_exchange(port, data, timeout, accept=is_reply):
    """Sends bytes to a serial port and returns the first received line that `accept`
    takes, without its line end. Every other line is dropped.

    What was waiting in the port when it was opened is discarded first.
    """
    try:
        descriptor = _open(port)
    except OSError as error:
        raise Unreachable(f"{port}: {error.strerror or type(error).__name__}") from None
    except termios.error:
        raise Unreachable(f"{port}: this is not a serial port") from None
    try:
        try:
            time.sleep(SETTLE_SECONDS)
            for _ in _received(descriptor, DISCARD_SECONDS):
                pass
            _write(descriptor, data, timeout)
        except OSError as error:
            raise Unreachable(f"{port}: {error.strerror or type(error).__name__}") from None
        waiting = b""
        try:
            for piece in _received(descriptor, timeout):
                waiting += piece
                while b"\n" in waiting:
                    line, waiting = waiting.split(b"\n", 1)
                    line = line.rstrip(b"\r")
                    if accept(line):
                        return line
        except OSError as error:
            raise Unreachable(f"{port}: {error.strerror or type(error).__name__}") from None
        raise Unreachable(f"{port}: no reply within {timeout:g} seconds")
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

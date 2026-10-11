"""The board on USB: which port it is, and what answers on it after a restart."""

import glob
import json
import os
import re
import time

from odrigctl import client

from . import Failure

PORT_VARIABLE = "ODRIG_BOARD_PORT"
PORT_PATTERN = "/dev/cu.usbmodem*"
WAIT_SECONDS = 20.0
EXCHANGE_SECONDS = 2.0


def find(port=None, environment=None, devices=None):
    """The port to use: the one given, else the one of the variable, else the only USB
    serial device there is."""
    environment = os.environ if environment is None else environment
    if port:
        return port
    if environment.get(PORT_VARIABLE):
        return environment[PORT_VARIABLE]
    devices = sorted(glob.glob(PORT_PATTERN)) if devices is None else list(devices)
    if not devices:
        raise Failure("no-board", f"there is no {PORT_PATTERN}; is the board connected?")
    if len(devices) > 1:
        raise Failure("no-board", f"there are {len(devices)} devices, {' and '.join(devices)}; name one with --port or {PORT_VARIABLE}")
    return devices[0]


def is_handshake(line):
    """Whether a line is WLED's answer to the byte `v`: `WLED ` and a number."""
    return re.fullmatch(rb"WLED \d+", line) is not None


def is_probe(line):
    """Whether a line is the probe build's report."""
    try:
        value = json.loads(line)
    except ValueError:
        return False
    return isinstance(value, dict) and "probe" in value


def ask(port, data, accept, wait=WAIT_SECONDS, what="an answer"):
    """Sends the bytes again and again until the board answers, for as long as `wait`."""
    deadline = time.monotonic() + wait
    last = "nothing was sent"
    while True:
        try:
            return client.serial_exchange(port, data, EXCHANGE_SECONDS, accept)
        except client.Unreachable as unreachable:
            last = str(unreachable)
        if time.monotonic() >= deadline:
            raise Failure("no-reply", f"no {what} within {wait:g} seconds: {last}")
        time.sleep(0.5)


def status(port, wait=WAIT_SECONDS):
    """The firmware's reply to `status`, as a line of text."""
    return ask(port, b"status\n", client.is_reply, wait, "reply to status").decode("utf-8", "replace")


def handshake(port, wait=WAIT_SECONDS):
    """WLED's answer to the byte `v`."""
    return ask(port, b"v", is_handshake, wait, "answer to WLED's handshake").decode("ascii")


def probe(port, wait=WAIT_SECONDS):
    """The probe build's report, as a line of text."""
    return ask(port, b"#probe\n", is_probe, wait, "answer to #probe").decode("utf-8", "replace")


EXPECTED = {"status": status, "wled": handshake, "probe": probe}

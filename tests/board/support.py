"""Helpers shared by the tests that need the board: running the tool, what the board runs,
and what it says on its port."""

import collections
import contextlib
import io
import json
import time

from odrigctl import client

from fwtool import Failure, board, build, cli

from . import PORT

Result = collections.namedtuple("Result", "status out err")

# What must answer after an image of each kind was flashed.
ANSWERS = {"probe": "probe", "stock": "wled"}

# The kind of image the suite leaves on the board.
LEFT_ON_THE_BOARD = "probe"

_running = None


def tool(*arguments):
    """Runs one command line of the firmware tool in this interpreter."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = cli.main([str(argument) for argument in arguments])
        except SystemExit as stopped:
            status = stopped.code
    return Result(status, out.getvalue(), err.getvalue())


def on_port(*arguments):
    """The same, on the board's port."""
    return tool(*arguments, "--port", PORT)


def built(kind):
    """The image of one kind, built now when the work folder does not hold it."""
    image = build.image_path(kind)
    try:
        return build.checked_image(image)
    except Failure:
        build.build(kind)
        return build.checked_image(image)


def answers(ask):
    try:
        ask(PORT, wait=1.0)
    except Failure:
        return False
    return True


def running():
    """The kind of image the board runs: `probe`, `stock`, or None when nothing known
    answers. The questions are asked in an order in which none disturbs the next."""
    global _running
    if _running is None:
        if answers(board.probe):
            _running = "probe"
        elif answers(board.handshake):
            _running = "stock"
    return _running


def flash(kind):
    """Flashes the image of one kind and waits for its answer."""
    global _running
    _running = None
    done = on_port("flash", "--image", built(kind), "--expect", ANSWERS[kind])
    if done.status != 0:
        raise AssertionError(f"flashing the {kind} image failed: {done.err}")
    _running = kind
    return done


def restore_stock():
    """Restores stock WLED and waits for its handshake."""
    global _running
    _running = None
    done = on_port("restore-stock")
    if done.status == 0:
        _running = "stock"
    return done


def ensure(kind):
    """Makes the board run the image of one kind, flashing only when it runs another."""
    if running() != kind:
        flash(kind)


def leave_the_board():
    """Puts on the board what the suite leaves there."""
    ensure(LEFT_ON_THE_BOARD)


def probe():
    """The probe build's report."""
    return json.loads(board.probe(PORT))


def heard(data, seconds):
    """Sends bytes, which may be none, and returns every line that arrives in a length of
    time. The board is not reset."""
    lines = []

    def keep(line):
        lines.append(line)
        return False

    with contextlib.suppress(client.Unreachable):
        client.serial_exchange(PORT, data, seconds, keep)
    return lines


def each_second(seconds, read=probe):
    """One report for each of a number of seconds in a row."""
    reports = []
    start = time.monotonic()
    for number in range(seconds):
        time.sleep(max(0.0, start + number + 1 - time.monotonic()))
        reports.append(read())
    return reports

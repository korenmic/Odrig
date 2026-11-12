"""Keeps the board's plan: joins the board, takes every plan it gives, asks again on a clock,
sees a restart, and keeps the offset between the board's clock and the emulator's."""

import json
import threading
import time

from . import middle

# With a push the plan is asked for every 10 seconds all the same; without one, over HTTP,
# every 2 seconds.
PUSHED_SECONDS = 10.0
ASKED_SECONDS = 2.0
# The board's status is asked for every 2 seconds while no client asks for it.
STATUS_SECONDS = 2.0
# A board time that went back by more than this is a restart.
BACK_MS = 1000
# The beginnings of the lines the chip's loader writes as the board starts.
LOADER = (b"ESP-ROM:", b"rst:", b"ets ", b"Build:")


def reads_only(line):
    """Whether a command line only reads, as the core counts the versions of its plan: a
    client's other lines may change what plays."""
    words = line.split(b" ")
    first = words[0]
    if first in (b"status", b"space", b"fault", b"list", b"read", b"saved"):
        return True
    if len(words) == 1:
        return first in (b"catalog", b"rotation", b"time", b"schedule", b"plan")
    if first == b"catalog":
        return words[1] == b"page"
    if first in (b"order", b"mapping"):
        return words[1] == b"get"
    return first == b"plan" and words[1] == b"since"


class Keeper:
    """The latest plan of the board and its clock.

    `plan` is the latest whole plan the board gave, a value as its reply reads, or `None`;
    `offset` the board's time less the emulator's, in milliseconds, or `None`; `status` the
    latest reply to a `status` the link carried. `found_off` says whether planning was off
    when the mirror first joined.
    """

    def __init__(self, middle_):
        self.middle = middle_
        self.clock_ms = None
        self.plan = None
        self.offset = None
        self.status = None
        self.found_off = None
        self.joined = False
        self._round_trip = None
        self._last_now = None
        self._status_at = None
        self._canvas_of = None
        self._canvas = None
        self._lock = threading.Lock()
        self._changed = threading.Condition(self._lock)
        self._poke = False
        self._stopping = False
        self._thread = threading.Thread(target=self._run, name="mirror-plan", daemon=True)
        middle_.watchers.append(self._link_changed)
        middle_.link.planned = self._pushed
        middle_.listeners.append(self._heard)

    def start(self, clock_ms):
        """Starts keeping the plan; `clock_ms` gives the emulator's time in milliseconds."""
        self.clock_ms = clock_ms
        self._thread.start()

    def board_canvas(self):
        """The board's canvas, `(width, height)`, from its latest status, or `None`."""
        with self._lock:
            status = self.status
            if status is self._canvas_of:
                return self._canvas
        try:
            value = json.loads(status) if status is not None else None
        except ValueError:
            value = None
        canvas = None
        if isinstance(value, dict) and isinstance(value.get("width"), int) and isinstance(value.get("height"), int):
            canvas = (value["width"], value["height"])
        with self._lock:
            self._canvas_of, self._canvas = status, canvas
        return canvas

    def stop(self):
        """Ends the keeper: the board's push is switched off, and planning when the mirror
        had found it off."""
        with self._changed:
            self._stopping = True
            self._changed.notify_all()
        self._thread.join(5.0)
        if self.joined and self.middle.state == middle.LINKED:
            if self.middle.link.streamed:
                self.middle.ask(b"plan push off", seconds=2.0)
            if self.found_off:
                self.middle.ask(b"plan off", seconds=2.0)

    def snapshot(self):
        """`(plan, offset)`, as they are now."""
        with self._lock:
            return self.plan, self.offset

    def client_line(self, line, reply):
        """A client's line and the board's reply: a status is kept, and over HTTP a line that
        may change what plays has the plan asked for at once."""
        if reply is None:
            return
        if line == b"status":
            with self._lock:
                self.status = reply
                self._status_at = self.clock_ms()
        if not self.middle.link.streamed and not reads_only(line):
            with self._changed:
                self._poke = True
                self._changed.notify_all()

    def _link_changed(self, state, reason):
        with self._changed:
            if state != middle.LINKED:
                self.joined = False
            self._changed.notify_all()

    def _heard(self, line):
        """The chip's loader writes as the board starts: the plan is to be joined anew."""
        if line.startswith(LOADER):
            with self._changed:
                self.joined = False
                self._changed.notify_all()
            self.middle.restarted()

    def _pushed(self, line):
        self._take(line, None, self.clock_ms())

    def _ask(self, line):
        """The mirror's own line, timed: `(reply, sent, received)`, the reply `None` when
        none came."""
        sent = self.clock_ms()
        reply = self.middle.ask(line)
        return reply, sent, self.clock_ms()

    def _join(self):
        """Reads the board's status, switches planning and the push on, and takes the plan.
        Says whether it got that far."""
        reply, _, _ = self._ask(b"status")
        if reply is None:
            return False
        with self._lock:
            self.status = reply
            self._status_at = self.clock_ms()
        reply, sent, received = self._ask(b"plan")
        if reply is None:
            return False
        value = self._take(reply, sent, received)
        if value is None:
            return False
        if self.found_off is None:
            self.found_off = not value.get("planning")
        for line in (b"plan on", b"plan push on") if self.middle.link.streamed else (b"plan on",):
            reply, _, _ = self._ask(line)
            if reply is None:
                return False
        reply, sent, received = self._ask(b"plan")
        if reply is None or self._take(reply, sent, received) is None:
            return False
        with self._lock:
            self.joined = True
        return True

    def _run(self):
        asked_at = None
        while True:
            with self._changed:
                if self._stopping:
                    return
                # A stream is opened by the middle; over HTTP the keeper's own requests are
                # what finds the board.
                if self.middle.link.streamed and self.middle.state != middle.LINKED:
                    self._changed.wait(0.5)
                    continue
                joined = self.joined
            if not joined:
                if not self._join():
                    with self._changed:
                        if not self._stopping:
                            self._changed.wait(middle.RETRY_SECONDS)
                asked_at = self.clock_ms()
                continue
            every = (PUSHED_SECONDS if self.middle.link.streamed else ASKED_SECONDS) * 1000
            now = self.clock_ms()
            with self._lock:
                status_due = self._status_at is None or now - self._status_at >= STATUS_SECONDS * 1000
                version = None if self.plan is None else self.plan.get("version")
            if status_due:
                reply, _, _ = self._ask(b"status")
                if reply is not None:
                    with self._lock:
                        self.status = reply
                        self._status_at = self.clock_ms()
            with self._lock:
                poked, self._poke = self._poke, False
            if poked or asked_at is None or now - asked_at >= every:
                line = b"plan" if version is None else b"plan since %d" % version
                reply, sent, received = self._ask(line)
                asked_at = self.clock_ms()
                if reply is not None:
                    self._take(reply, sent, received)
                continue
            with self._changed:
                if not self._stopping and not self._poke:
                    self._changed.wait(min(0.25, max(0.0, (every - (now - asked_at)) / 1000)))

    def _take(self, reply, sent, received):
        """Takes a reply to `plan` or `plan since`, or a `#plan` line. Returns its value, or
        `None` for a reply that is no plan."""
        try:
            value = json.loads(reply)
        except ValueError:
            return None
        if not isinstance(value, dict) or not value.get("ok") or not isinstance(value.get("now"), int):
            return None
        board = value["now"]
        with self._changed:
            if self._last_now is not None and board < self._last_now - BACK_MS:
                self.joined = False
            self._last_now = board
            if sent is not None:
                trip = received - sent
                estimate = board - (sent + received) // 2
                if self.offset is None or self._round_trip is None or trip <= self._round_trip + 2 or abs(estimate - self.offset) > trip // 2 + 20:
                    self.offset, self._round_trip = estimate, trip
                else:
                    self._round_trip += 1
            elif self.offset is None:
                self.offset = board - received
            if not value.get("planning") and self.joined:
                self.joined = False
            if not value.get("unchanged"):
                self.plan = value
            self._changed.notify_all()
        return value

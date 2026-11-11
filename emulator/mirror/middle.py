"""The man in the middle: every client's line goes to the board, and its reply comes back to
that client alone.

Over a stream one worker sends the waiting lines one at a time, a client's before the
mirror's own, and waits for each line's reply before it sends the next: a board answers the
lines of a way in their order, so the reply that comes is the answer of the line that waits.
Over HTTP every line is a request of its own.
"""

import collections
import threading
import time

from .link import Lost

# How long a line waits for its reply at most, and how long the worker still waits for it
# once its client stopped waiting, so that a late reply is not taken for the next line's.
CLIENT_SECONDS = 30.0
AFTER_SECONDS = 30.0
# How often a link that cannot be opened is tried again.
RETRY_SECONDS = 2.0
POLL_SECONDS = 0.05

# The states of a link: not open yet, open, and lost after it was open.
WAITING = "waiting"
LINKED = "linked"
LOST = "lost"


class Line:
    """A line that waits for its reply."""

    def __init__(self, data, own):
        self.data = data
        self.own = own
        self.reply = None
        self.done = threading.Event()
        self.given_up = None


class Middle:
    """Carries lines to the board over a link and the replies back.

    `send` is a client's line and `ask` the mirror's own; each returns the board's reply with
    its line end, or `None` when none came. `watchers` are told `(state, reason)` at every
    change of the link's state, and `listeners` every line of the board that is neither a
    reply nor a `#plan` line.
    """

    def __init__(self, link, clock=time.monotonic):
        self.link = link
        self.clock = clock
        self.state = WAITING
        self.reason = None
        self.since = clock()
        # The time of day the state began, as the page says it.
        self.since_text = time.strftime("%H:%M:%S")
        self.watchers = []
        self.listeners = []
        self._changed = threading.Condition()
        self._clients = collections.deque()
        self._own = collections.deque()
        self._current = None
        self._stopping = False
        self._threads = []
        if link.streamed:
            link.replied = self._replied
            link.heard = self._heard
            link.lost = self._lost

    def start(self):
        if self.link.streamed:
            self._threads = [threading.Thread(target=self._link, name="mirror-open", daemon=True),
                             threading.Thread(target=self._work, name="mirror-lines", daemon=True)]
            for thread in self._threads:
                thread.start()

    def stop(self):
        """Ends every wait and closes the link."""
        with self._changed:
            self._stopping = True
            self._end_waits()
            self._changed.notify_all()
        if self.link.streamed:
            self.link.close()
        for thread in self._threads:
            thread.join(2.0)

    def send(self, data, seconds=CLIENT_SECONDS):
        """A client's line, without its line end."""
        return self._wait(data, False, seconds)

    def ask(self, data, seconds=CLIENT_SECONDS):
        """The mirror's own line, which waits for every client's line that waits."""
        return self._wait(data, True, seconds)

    def restarted(self):
        """The board restarted: the line on the link gets no reply."""
        with self._changed:
            line, self._current = self._current, None
            if line is not None:
                line.done.set()
            self._changed.notify_all()

    def _wait(self, data, own, seconds):
        if not self.link.streamed:
            return self._exchange(data, seconds)
        line = Line(data, own)
        with self._changed:
            if self._stopping or self.state != LINKED:
                return None
            (self._own if own else self._clients).append(line)
            self._changed.notify_all()
        if not line.done.wait(seconds):
            with self._changed:
                line.given_up = self.clock()
                for queue in (self._clients, self._own):
                    if line in queue:
                        queue.remove(line)
                        line.done.set()
                self._changed.notify_all()
        return line.reply

    def _exchange(self, data, seconds):
        if self._stopping:
            return None
        try:
            reply = self.link.exchange(data, seconds)
        except Lost as error:
            self._set_state(WAITING if self.state == WAITING else LOST, str(error))
            return None
        self._set_state(LINKED, None)
        return reply

    def _set_state(self, state, reason):
        with self._changed:
            if (state, reason) == (self.state, self.reason):
                return
            if state != self.state:
                self.since = self.clock()
                self.since_text = time.strftime("%H:%M:%S")
            self.state, self.reason = state, reason
            self._changed.notify_all()
            watchers = list(self.watchers)
        for watcher in watchers:
            watcher(state, reason)

    def _link(self):
        """Opens the link, and opens it again every 2 seconds while it cannot be opened."""
        while True:
            with self._changed:
                while not self._stopping and self.state == LINKED:
                    self._changed.wait()
                if self._stopping:
                    return
            try:
                self.link.open()
            except Lost as error:
                self._set_state(WAITING if self.state == WAITING else LOST, str(error))
                with self._changed:
                    if not self._stopping:
                        self._changed.wait(RETRY_SECONDS)
                continue
            self._set_state(LINKED, None)

    def _work(self):
        """Sends the waiting lines one at a time, each once the reply of the one before came."""
        while True:
            with self._changed:
                while not self._stopping and (self.state != LINKED or not (self._clients or self._own)):
                    self._changed.wait()
                if self._stopping:
                    return
                line = (self._clients or self._own).popleft()
                self._current = line
            try:
                self.link.send(line.data)
            except Lost:
                continue
            with self._changed:
                while self._current is line and not self._stopping:
                    if line.given_up is not None and self.clock() - line.given_up >= AFTER_SECONDS:
                        break
                    self._changed.wait(POLL_SECONDS)
                if self._current is line:
                    self._current = None
                    line.done.set()

    def _replied(self, reply):
        """A reply from the board: the answer of the line on the link, or dropped when no
        line waits for one."""
        with self._changed:
            line, self._current = self._current, None
            if line is None:
                return
            line.reply = reply + b"\n"
            line.done.set()
            self._changed.notify_all()

    def _heard(self, line):
        for listener in list(self.listeners):
            listener(line)

    def _lost(self, reason):
        with self._changed:
            self._end_waits()
        self._set_state(LOST, reason)

    def _end_waits(self):
        """Every line that waits gets no reply."""
        lines = list(self._clients) + list(self._own) + ([self._current] if self._current is not None else [])
        self._clients.clear()
        self._own.clear()
        self._current = None
        for line in lines:
            line.done.set()

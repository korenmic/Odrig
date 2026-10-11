"""The one caller of the core once it has started, and the loop that keeps real time."""

import threading
import time

from . import binding

GRID_MS = 20
AFTER_GRID_NS = 200_000
LONG_WAIT_NS = 3_000_000
KEPT_BACK_NS = 2_000_000
SHORT_SLEEP_NS = 500_000


def wait_until(target_ns, clock=time.monotonic_ns, sleep=time.sleep):
    """Sleeps until a moment of the clock, and wakes within a fraction of a millisecond.

    One sleep of 20 ms wakes up to 10 ms late on a Mac, because the system lets a timer
    slip by a share of its length. So the wait is cut up: half of what is left each time,
    and at the end in steps of half a millisecond.
    """
    while True:
        left = target_ns - clock()
        if left <= 0:
            return
        if left > LONG_WAIT_NS:
            sleep((left - KEPT_BACK_NS) / 2 / 1_000_000_000)
        else:
            sleep(min(left, SHORT_SLEEP_NS) / 1_000_000_000)


class Engine:
    """Owns the core and its lock. Every method makes its calls to the core under the lock,
    and reads the timestamp after taking it, so the calls follow one another and their
    timestamps never go backwards."""

    def __init__(self, core, hub, clock=time.monotonic_ns):
        self.core = core
        self.hub = hub
        self.clock = clock
        self.start_ns = clock()
        self.t0 = None
        self._lock = threading.Lock()

    def now_ms(self):
        return (self.clock() - self.start_ns) // 1_000_000

    def tick(self):
        """Asks the core for a refresh and hands one it produced to the hub. The first call
        sets the power-on moment."""
        with self._lock:
            now = self.now_ms()
            if self.t0 is None:
                self.t0 = now
            if self.core.poll(now):
                self.hub.refresh(now, self.core.frame())

    def line(self, data, transport):
        """One command line, as HTTP delivers it. Returns the reply."""
        with self._lock:
            now = self.now_ms()
            reply = self.core.command(now, data)
        kept = data[:-1] if data.endswith(b"\n") else data
        kept = kept[:-1] if kept.endswith(b"\r") else kept
        self.hub.log(now, transport, kept[:binding.LINE_MAX], len(kept) > binding.LINE_MAX, reply)
        self.refresh_status()
        return reply

    def feed(self, data, transport):
        """Bytes of a transport, as a serial port delivers them. Returns the replies to the
        lines they finish, joined."""
        with self._lock:
            now = self.now_ms()
            answered = self.core.feed(now, data)
        for line, reply, cut in answered:
            self.hub.log(now, transport, line, cut, reply)
        if answered:
            self.refresh_status()
        return b"".join(reply for _, reply, _ in answered)

    def refresh_status(self):
        """Asks the core for its status, for the page. The request is not a command that
        arrived, so it is not entered in the log."""
        with self._lock:
            reply = self.core.command(self.now_ms(), b"status")
        self.hub.status(reply)

    def error(self):
        """The reason the show is invalid, as the core gives it now, or `None`."""
        with self._lock:
            return self.core.error()


class RealTime(threading.Thread):
    """Asks for a refresh at every grid time, 20 ms apart from the power-on moment.

    A wake-up that comes late asks with the current time. The core skips the grid times
    that were missed; nothing is replayed. Once in every second after the power-on moment
    the loop also has the status for the page asked for.
    """

    def __init__(self, engine, wait=None):
        super().__init__(name="real-time", daemon=True)
        self.engine = engine
        self.wait = wait if wait is not None else lambda target_ns: wait_until(target_ns, engine.clock)
        self._second = 0
        self._stopping = threading.Event()

    def step(self):
        """Waits until just after the next grid time and asks for one refresh."""
        engine = self.engine
        now = engine.now_ms()
        grid = engine.t0 + ((now - engine.t0) // GRID_MS + 1) * GRID_MS
        self.wait(engine.start_ns + grid * 1_000_000 + AFTER_GRID_NS)
        engine.tick()
        second = (engine.now_ms() - engine.t0) // 1000
        if second != self._second:
            self._second = second
            engine.refresh_status()

    def run(self):
        while not self._stopping.is_set():
            self.step()

    def stop(self):
        self._stopping.set()

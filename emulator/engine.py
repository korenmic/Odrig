"""The one caller of the core once it has started, the loop that keeps real time, what
the engine knows of the animation on the LEDs, the start of its loop and of its turn from
the core's opens of the played file and its length, and the seek that moves playback by
moving the clock."""

import re
import threading
import time

from . import binding
from .lengths import Lengths

GRID_MS = 20
# A seek moves the clock in strides of this much, so that the core comes to the picture
# of each stride's time within one refresh.
SEEK_STRIDE_MS = 400
# The two members of the status reply the engine reads, as the core writes them.
ANIMATION = re.compile(rb'"animation":([0-9]+|null)')
PLAYING = re.compile(rb'"playing":("all"|[0-9]+|null)')
# A cycle among the items of a list reply, and the position of the reply's next page.
CYCLE_ITEM = re.compile(rb'\{"id":([0-9]+),"cycle":')
NEXT_PAGE = re.compile(rb'"next":([0-9]+|null)')
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


class Playback:
    """Where the animation on the LEDs stands, as the engine knows it.

    `animation` and `playing` are the members of the latest status. `stream` is the name
    the core opened last for playing and `path` its file. `start` is the start of the
    loop that shows and `turn` the start of its turn, both on the engine's clock, at a
    grid time. `length` is the loop's length in milliseconds, or `None`, and `source`
    says where it came from: `catalog`, `check` or `seen`.
    """

    def __init__(self):
        self.animation = None
        self.playing = None
        self.stream = None
        self.path = None
        self.start = None
        self.turn = None
        self.length = None
        self.source = None
        self.cycles = set()

    def clear(self):
        self.stream = self.path = self.start = self.turn = self.length = self.source = None

    def cycle(self):
        """A cycle plays: `playing` names one of the show's cycles. Any other number in it
        is a folder of the card whose playlist plays."""
        return self.playing in self.cycles

    def event(self):
        """What the page is told: nothing while nothing plays or a cycle plays."""
        shown = self.animation is not None and not self.cycle()
        return {
            "animation": self.animation if shown else None,
            "start": self.start if shown else None,
            "turn": self.turn if shown else None,
            "length": self.length if shown else None,
        }


class Engine:
    """Owns the core and its lock. Every method makes its calls to the core under the lock,
    and reads the timestamp after taking it, so the calls follow one another and their
    timestamps never go backwards.

    With a `host`, the engine is told of every open of an animation file and keeps the
    playback state from it; `lengths` finds the lengths of the files.
    """

    def __init__(self, core, hub, clock=time.monotonic_ns, host=None, lengths=None):
        self.core = core
        self.hub = hub
        self.clock = clock
        self.start_ns = clock()
        self.t0 = None
        self._lock = threading.Lock()
        self.playback = Playback()
        self.lengths = lengths if lengths is not None else Lengths()
        self._answered = 0
        self._answered_at_open = 0
        self._listed_for = -1
        self._told_apart = set()
        self._seek_since_open = False
        self._restarting = False
        self._opened = None
        self._seen = {}
        # The page is told of the position once something is known of it.
        self._told = self.playback.event()
        if host is not None:
            host.on_open = self._note_open

    def now_ms(self):
        return (self.clock() - self.start_ns) // 1_000_000

    def grid_at(self, now):
        """The grid time at or before a timestamp, where a refresh asked for then begins."""
        return self.t0 + ((now - self.t0) // GRID_MS) * GRID_MS

    def tick(self):
        """Asks the core for a refresh and hands one it produced to the hub. The first call
        sets the power-on moment."""
        with self._lock:
            now = self.now_ms()
            if self.t0 is None:
                self.t0 = now
            self._opened = None
            if self.core.poll(now):
                self.hub.refresh(now, self.core.frame())
            if self._opened is not None:
                self._take_open(now)
            self._take_lengths()
            self._publish()

    def line(self, data, transport):
        """One command line, as HTTP delivers it. Returns the reply."""
        with self._lock:
            now = self.now_ms()
            before = getattr(self.core, "legs", ())
            reply = self.core.command(now, data)
            self._answered += 1
            if before != getattr(self.core, "legs", ()):
                self.hub.mapping(self.core.legs)
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
            before = getattr(self.core, "legs", ())
            answered = self.core.feed(now, data)
            self._answered += len(answered)
            if before != getattr(self.core, "legs", ()):
                self.hub.mapping(self.core.legs)
        for line, reply, cut in answered:
            self.hub.log(now, transport, line, cut, reply)
        if answered:
            self.refresh_status()
        return b"".join(reply for _, reply, _ in answered)

    def refresh_status(self):
        """Asks the core for its status, for the page. The request is not a command that
        arrived, so it is not entered in the log."""
        with self._lock:
            self._status_now(self.now_ms())
            self._publish()

    def seek(self, target):
        """Moves playback to a point of the loop of the animation on the LEDs, in
        milliseconds from its start: forward by a move of the clock, back by a restart of
        the animation, the engine's own `play`, and then a move. Returns the reply of the
        route: the position moved to, the starts, the length and the clock's move, or the
        refusal."""
        with self._lock:
            playback = self.playback
            if isinstance(target, bool) or not isinstance(target, int):
                return {"ok": False, "error": "bad-argument"}
            if playback.animation is None or playback.start is None:
                return {"ok": False, "error": "nothing-plays"}
            if playback.cycle():
                return {"ok": False, "error": "cycle"}
            if playback.length is None:
                return {"ok": False, "error": "length-unknown"}
            if target < 0 or target > playback.length - 2 * GRID_MS:
                return {"ok": False, "error": "beyond-length"}
            now = self.now_ms()
            moved = 0
            position = (now - playback.start) % playback.length
            if target < position:
                line = b"play %d" % playback.animation
                reply = self.core.command(now, line)
                self.hub.log(now, "seek", line, False, reply)
                self._restarting = True
                moved += self._move(GRID_MS)
                position = self.now_ms() - playback.start
            move = ((target - position) // GRID_MS) * GRID_MS
            if move > 0:
                moved += self._move(move)
            self._seek_since_open = True
            self._take_lengths()
            self._publish()
            return {
                "ok": True,
                "animation": playback.animation,
                "start": playback.start,
                "turn": playback.turn,
                "length": playback.length,
                "position": (self.now_ms() - playback.start) % playback.length,
                "moved": moved,
            }

    def _move(self, ms):
        """Moves the clock forward by a whole number of grid steps, in strides the core
        catches up with at one refresh, and asks it for the refresh of each; the hub gets
        the last. Returns the move.

        A refresh decodes a bounded part of a file and keeps the picture before until it
        has come to the picture of its time, so one long jump would leave the LEDs still
        for seconds; a stride of 400 ms holds fewer bytes than that bound for any file the
        converter writes, and the core's decoding of the whole way takes a fraction of the
        time it stands for.
        """
        left = ms
        frame = None
        while left > 0:
            stride = min(left, SEEK_STRIDE_MS)
            self.start_ns -= stride * 1_000_000
            left -= stride
            now = self.now_ms()
            self._opened = None
            if self.core.poll(now):
                frame = (now, self.core.frame())
            if self._opened is not None:
                self._take_open(now)
        if frame is not None:
            self.hub.refresh(*frame)
        return ms

    def take_lengths(self):
        """Takes in the lengths found since, and tells the page of a change."""
        with self._lock:
            self._take_lengths()
            self._publish()

    def error(self):
        """The reason the show is invalid, as the core gives it now, or `None`."""
        with self._lock:
            return self.core.error()

    def _note_open(self, name, path):
        """The host's word that the core opened an animation file; taken up after the poll."""
        self._opened = (name, path)

    def _take_open(self, now):
        """An open seen in the poll that just returned: the start of a turn, when the file
        differs from the one played, a command was answered since the previous open, or
        the engine restarted the animation itself; else the start of a loop."""
        name, path = self._opened
        self._opened = None
        grid = self.grid_at(now)
        playback = self.playback
        turn = name != playback.stream or self._answered != self._answered_at_open or self._restarting
        if turn:
            playback.stream, playback.path = name, path
            playback.start = playback.turn = grid
            playback.length, playback.source = self.lengths.known(path)
            if playback.length is None and path in self._seen:
                playback.length, playback.source = self._seen[path], "seen"
            if playback.length is None:
                self.lengths.request(path)
            self._status_now(now)
        else:
            if playback.length is None and not self._seek_since_open:
                playback.length, playback.source = grid - playback.start, "seen"
                self._seen[path] = playback.length
            playback.start = grid
        self._answered_at_open = self._answered
        self._seek_since_open = False
        self._restarting = False

    def _status_now(self, now):
        """Asks the core for its status, takes it in, and hands it to the hub. A number in
        `playing` that the engine has not told apart since the last command answered, a
        cycle or a folder of the card, has the cycles listed."""
        reply = self.core.command(now, b"status")
        self._take_status(reply)
        playing = self.playback.playing
        if isinstance(playing, int):
            if self._listed_for != self._answered:
                self._told_apart = set()
                self._listed_for = self._answered
            if playing not in self._told_apart:
                self._list_cycles(now)
                self._told_apart.add(playing)
        self.hub.status(reply)

    def _list_cycles(self, now):
        """The ids of the show's cycles, from the pages of `list`; the engine's own requests."""
        cycles = set()
        page = 0
        while page is not None:
            reply = self.core.command(now, b"list %d" % page)
            cycles.update(int(found) for found in CYCLE_ITEM.findall(reply))
            found = NEXT_PAGE.search(reply)
            page = int(found.group(1)) if found and found.group(1) != b"null" else None
        self.playback.cycles = cycles

    def _take_status(self, reply):
        """Reads `animation` and `playing` off the reply, as the core writes them."""
        animation = ANIMATION.search(reply)
        playing = PLAYING.search(reply)
        if animation is None or playing is None:
            return
        playback = self.playback
        playback.animation = int(animation.group(1)) if animation.group(1) != b"null" else None
        found = playing.group(1)
        playback.playing = None if found == b"null" else "all" if found == b'"all"' else int(found)
        if playback.animation is None:
            playback.clear()

    def _take_lengths(self):
        playback = self.playback
        for path, ms, source in self.lengths.take():
            if ms is None or path != playback.path:
                continue
            if playback.length is None or playback.source == "seen":
                playback.length, playback.source = ms, source

    def _publish(self):
        event = self.playback.event()
        if event != self._told:
            self._told = event
            self.hub.position(event)


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

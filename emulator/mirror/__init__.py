"""The mirror of a board: the emulator carries every client's line to a board and its reply
back, and shows what the board's plan says the board shows.

It is the emulator's client of a board, as the command tool is: it opens the board's serial
port with the command tool's client, and reads the board's replies.
"""

import threading

from . import driver, files, keeper, link, middle

# The lines of the board one way keeps for its client, the newest; a client that does not
# read loses the oldest, as a port nobody reads loses what waits in it.
HEARD_KEPT = 64


class Mirror:
    """The link, the man in the middle, the plan, the files and the turn on the LEDs, and the
    board's lines that wait for the clients of the emulator's serial ways. `names` is the
    host's table of the mirror's names; `root` holds the collections and `build/mirror/`."""

    def __init__(self, kind, name, root, names):
        self.kind = kind
        self.name = name
        self.link = link.made(kind, name)
        self.middle = middle.Middle(self.link)
        self.keeper = keeper.Keeper(self.middle)
        self.files = files.Files(root)
        self.fetcher = files.Fetcher(self.middle, self.files)
        self.driver = driver.Driver(self.keeper, self.files, self.fetcher, names)
        self._lock = threading.Lock()
        self._heard = {}
        self.middle.listeners.append(self._take_heard)

    @property
    def described(self):
        """The link as the emulator prints it: its kind and its name."""
        return f"{self.kind} {self.name}"

    def start(self, clock_ms, canvas):
        """Opens the link and keeps the board's plan. `clock_ms` gives the emulator's time,
        and `canvas` is the show folder's, `(width, height)`, or `None`."""
        self.driver.canvas = canvas
        self.middle.start()
        self.keeper.start(clock_ms)
        self.fetcher.start()

    def stop(self):
        self.fetcher.stop()
        self.keeper.stop()
        self.middle.stop()

    def drive(self, record, local_ms):
        return self.driver.drive(record, local_ms)

    def state(self):
        """What the page is told: the link, its state and since when, the plan's version,
        the offset of the board's clock, why the LEDs are dark, the item on them, a fetch
        under way, and both canvases when they differ."""
        plan, offset = self.keeper.snapshot()
        dark, item = self.driver.shown()
        fetching = self.fetcher.fetching
        board = self.keeper.board_canvas()
        parsed = None if fetching is None else files.parsed_key(fetching[1])
        return {
            "link": self.described,
            "state": self.middle.state,
            "reason": self.middle.reason,
            "since": self.middle.since_text,
            "version": None if plan is None else plan.get("version"),
            "offset": offset,
            "dark": dark,
            "item": None if item is None else {"id": item.get("id"), "key": item.get("key")},
            "fetch": None if fetching is None else {"id": fetching[0], "key": fetching[1], "bytes": fetching[2], "size": None if parsed is None else parsed[1]},
            "canvas": {"board": list(board), "show": list(self.driver.canvas)} if dark == "canvas" and board and self.driver.canvas else None,
        }

    def client_line(self, line, reply):
        self.keeper.client_line(line, reply)

    def heard_for(self, way):
        """The board's lines that wait for the client of a serial way, each with its line
        end, or `None`. A way is given the lines that came since it first asked."""
        if not way:
            return None
        with self._lock:
            waiting = self._heard.setdefault(way, [])
            if not waiting:
                return None
            self._heard[way] = []
        return b"".join(line + b"\n" for line in waiting)

    def way_ended(self, way):
        with self._lock:
            self._heard.pop(way, None)

    def _take_heard(self, line):
        with self._lock:
            for waiting in self._heard.values():
                waiting.append(line)
                del waiting[:-HEARD_KEPT]

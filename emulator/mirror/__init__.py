"""The mirror of a board: the emulator carries every client's line to a board and its reply
back, and shows what the board's plan says the board shows.

It is the emulator's client of a board, as the command tool is: it opens the board's serial
port with the command tool's client.
"""

import threading

from . import link, middle

# The lines of the board one way keeps for its client, the newest; a client that does not
# read loses the oldest, as a port nobody reads loses what waits in it.
HEARD_KEPT = 64


class Mirror:
    """The link, the man in the middle, and the board's lines that wait for the clients of
    the emulator's serial ways."""

    def __init__(self, kind, name):
        self.kind = kind
        self.name = name
        self.link = link.made(kind, name)
        self.middle = middle.Middle(self.link)
        self._lock = threading.Lock()
        self._heard = {}
        self.middle.listeners.append(self._take_heard)

    @property
    def described(self):
        """The link as the emulator prints it: its kind and its name."""
        return f"{self.kind} {self.name}"

    def start(self):
        self.middle.start()

    def stop(self):
        self.middle.stop()

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

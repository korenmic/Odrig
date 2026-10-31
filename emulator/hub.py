"""What the page is shown: the command log, the latest status, the position of the
animation on the LEDs and every refresh.

The hub keeps the last log entries and the latest status, and hands everything that
happens to the connections of the pages that are open.
"""

import base64
import collections
import datetime
import json
import threading

LOG_ENTRIES = 500
LINE_SHOWN = 200


def shown(line):
    """The bytes of a command line as text: every byte outside printable ASCII as `\\xNN`."""
    return "".join(chr(value) if 0x20 <= value <= 0x7E else f"\\x{value:02X}" for value in line)


def compact(value):
    return json.dumps(value, separators=(",", ":"))


class Connection:
    """What one open page is still to be sent.

    Log and status events wait in a queue and are never dropped. Refreshes do not queue:
    there is one slot for the newest one, and a newer refresh replaces it, so a page that
    cannot keep up skips refreshes instead of falling behind.
    """

    def __init__(self):
        self._changed = threading.Condition()
        self._events = collections.deque()
        self._refresh = None
        self._closed = False

    def put(self, kind, data):
        with self._changed:
            self._events.append((kind, data))
            self._changed.notify()

    def put_refresh(self, ms, frame, mini=None):
        with self._changed:
            self._refresh = (ms, frame, mini)
            self._changed.notify()

    def close(self):
        with self._changed:
            self._closed = True
            self._changed.notify()

    def take(self, seconds):
        """Waits for something to send, at most this long.

        Returns the events to send as `(kind, data)`, the queued ones in order and then the
        newest refresh as a `frame` event; an empty list when the time passed with nothing
        to send; `None` once the connection is closed.
        """
        with self._changed:
            if not self._events and self._refresh is None and not self._closed:
                self._changed.wait(seconds)
            if self._closed:
                return None
            events = list(self._events)
            self._events.clear()
            refresh, self._refresh = self._refresh, None
        if refresh is not None:
            ms, frame, mini = refresh
            events.append(("frame", f"{ms} {base64.b64encode(frame).decode('ascii')}"))
            if mini is not None:
                active, rgb = mini
                value = {"active": active}
                if active:
                    value["rgb"] = base64.b64encode(rgb).decode("ascii")
                events.append(("mini", compact(value)))
        return events


class Hub:
    """Keeps the last log entries and the latest status, and tells every connection."""

    def __init__(self):
        self._lock = threading.Lock()
        self._entries = collections.deque(maxlen=LOG_ENTRIES)
        self._seq = 0
        self._status = None
        self._position = None
        self._refresh = None
        self._connections = set()

    def log(self, ms, transport, line, cut, reply):
        """Enters one command that arrived: its timestamp, how it came, the line as the
        core read it, whether it was cut, and the reply. The entry keeps the first
        characters of the line and its length."""
        now = datetime.datetime.now()
        with self._lock:
            self._seq += 1
            entry = {
                "seq": self._seq,
                "ms": ms,
                "time": f"{now:%H:%M:%S}.{now.microsecond // 1000:03d}",
                "transport": transport,
                "line": shown(line[:LINE_SHOWN]),
                "length": len(line),
                "cut": bool(cut),
                "reply": reply.decode("ascii", "replace").rstrip("\n"),
            }
            self._entries.append(entry)
            data = compact(entry)
            for connection in self._connections:
                connection.put("log", data)
        return entry

    def status(self, reply):
        """Takes the core's reply to `status` as the latest status."""
        with self._lock:
            self._status = reply.decode("ascii", "replace").rstrip("\n")
            for connection in self._connections:
                connection.put("status", self._status)

    def position(self, event):
        """Takes where the animation on the LEDs stands: its id, the starts of its loop and
        of its turn on the engine's clock, and its length, each `None` while unknown."""
        data = compact(event)
        with self._lock:
            self._position = data
            for connection in self._connections:
                connection.put("position", data)

    def mapping(self, legs):
        """Publish a complete committed routing assignment."""
        data = compact([list(leg) for leg in legs])
        with self._lock:
            for connection in self._connections:
                connection.put("mapping", data)

    def refresh(self, ms, frame, mini=None):
        """Takes the refresh the core produced at a timestamp as the newest one."""
        with self._lock:
            self._refresh = (ms, frame)
            for connection in self._connections:
                connection.put_refresh(ms, frame, mini)

    def connect(self, hello):
        """A connection for a page that has just opened. It starts with `hello`, the log
        entries kept so far and the latest status, and then gets everything that happens."""
        connection = Connection()
        connection.put("hello", compact(hello))
        with self._lock:
            for entry in self._entries:
                connection.put("log", compact(entry))
            if self._status is not None:
                connection.put("status", self._status)
            if self._position is not None:
                connection.put("position", self._position)
            self._connections.add(connection)
        return connection

    def disconnect(self, connection):
        with self._lock:
            self._connections.discard(connection)
        connection.close()

    def close(self):
        """Ends every connection."""
        with self._lock:
            connections, self._connections = self._connections, set()
        for connection in connections:
            connection.close()

    def entries(self):
        """The log entries kept, oldest first."""
        with self._lock:
            return list(self._entries)

    def latest_status(self):
        with self._lock:
            return self._status

    def latest_position(self):
        with self._lock:
            return self._position

    def newest_refresh(self):
        with self._lock:
            return self._refresh

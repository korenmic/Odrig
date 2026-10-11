"""What the page is shown: the command log, the latest status and the newest refresh."""

import collections
import datetime
import threading

LOG_ENTRIES = 500


def shown(line):
    """The bytes of a command line as text: every byte outside printable ASCII as `\\xNN`."""
    return "".join(chr(value) if 0x20 <= value <= 0x7E else f"\\x{value:02X}" for value in line)


class Hub:
    """Keeps the last log entries, the latest status and the newest refresh."""

    def __init__(self):
        self._lock = threading.Lock()
        self._entries = collections.deque(maxlen=LOG_ENTRIES)
        self._seq = 0
        self._status = None
        self._refresh = None

    def log(self, ms, transport, line, cut, reply):
        """Enters one command that arrived: its timestamp, how it came, the line as the
        core read it, whether it was cut, and the reply."""
        now = datetime.datetime.now()
        with self._lock:
            self._seq += 1
            entry = {
                "seq": self._seq,
                "ms": ms,
                "time": f"{now:%H:%M:%S}.{now.microsecond // 1000:03d}",
                "transport": transport,
                "line": shown(line),
                "cut": bool(cut),
                "reply": reply.decode("ascii", "replace").rstrip("\n"),
            }
            self._entries.append(entry)
        return entry

    def status(self, reply):
        """Takes the core's reply to `status` as the latest status."""
        with self._lock:
            self._status = reply.decode("ascii", "replace").rstrip("\n")

    def refresh(self, ms, frame):
        """Takes the refresh the core produced at a timestamp as the newest one."""
        with self._lock:
            self._refresh = (ms, frame)

    def entries(self):
        """The log entries kept, oldest first."""
        with self._lock:
            return list(self._entries)

    def latest_status(self):
        with self._lock:
            return self._status

    def newest_refresh(self):
        with self._lock:
            return self._refresh

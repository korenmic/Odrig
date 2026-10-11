"""The virtual serial port: a pseudo-terminal, a link with a stable name, and its reader."""

import contextlib
import os
import select
import termios
import threading
import time
import tty

from . import failure

READ_SIZE = 4096
POLL_SECONDS = 0.1
RETRY_SECONDS = 0.05
WRITE_SECONDS = 1.0


class Port:
    """A pseudo-terminal whose far end programs open through a symbolic link.

    Both ends stay open for as long as the port lives, so the port stays in place while
    programs open and close it. Every byte a program writes goes to `feed`, and what
    `feed` returns is written back.
    """

    def __init__(self, link, feed):
        self.link = os.path.abspath(os.fspath(link))
        self._feed = feed
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._read, name="serial", daemon=True)
        try:
            self._near, self._far = os.openpty()
        except OSError as error:
            raise failure.Failure(failure.SERIAL_UNAVAILABLE, f"no pseudo-terminal: {error.strerror or type(error).__name__}") from None
        try:
            tty.setraw(self._far)
            os.set_blocking(self._near, False)
            self.device = os.ttyname(self._far)
            self._make_link()
        except OSError as error:
            self._close()
            raise failure.Failure(failure.SERIAL_UNAVAILABLE, f"{self.link}: {error.strerror or type(error).__name__}") from None
        except failure.Failure:
            self._close()
            raise

    def _make_link(self):
        os.makedirs(os.path.dirname(self.link), exist_ok=True)
        if os.path.islink(self.link):
            os.remove(self.link)
        elif os.path.lexists(self.link):
            raise failure.Failure(failure.SERIAL_UNAVAILABLE, f"{self.link}: the path holds something that is not a symbolic link")
        os.symlink(self.device, self.link)

    def start(self):
        self._thread.start()

    def _read(self):
        while not self._stopping.is_set():
            try:
                readable, _, _ = select.select([self._near], [], [], POLL_SECONDS)
                if not readable:
                    continue
                data = os.read(self._near, READ_SIZE)
            except BlockingIOError:
                continue
            except (OSError, ValueError):
                if self._stopping.is_set():
                    return
                time.sleep(RETRY_SECONDS)
                continue
            if data:
                self._write(self._feed(data))

    def _write(self, data):
        """Writes replies to the port. When no program has read for a while and the port is
        full, what waits unread is dropped to make room, as a board's output is lost when
        nobody listens."""
        deadline = time.monotonic() + WRITE_SECONDS
        flushed = False
        while data and not self._stopping.is_set():
            try:
                data = data[os.write(self._near, data):]
            except BlockingIOError:
                left = deadline - time.monotonic()
                if left > 0:
                    select.select([], [self._near], [], min(left, POLL_SECONDS))
                elif not flushed:
                    flushed = True
                    with contextlib.suppress(OSError):
                        termios.tcflush(self._far, termios.TCIFLUSH)
                else:
                    return
            except OSError:
                return

    def _close(self):
        for end in (self._near, self._far):
            with contextlib.suppress(OSError):
                os.close(end)

    def close(self):
        """Stops the reader, removes the link if it still points at this port, and closes
        the pseudo-terminal."""
        self._stopping.set()
        if self._thread.is_alive():
            self._thread.join()
        with contextlib.suppress(OSError):
            if os.path.islink(self.link) and os.readlink(self.link) == self.device:
                os.remove(self.link)
        self._close()

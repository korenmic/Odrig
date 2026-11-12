"""The line port: the line protocol of the serial port on a TCP port of the page's address."""

import contextlib
import socket
import socketserver
import threading

from . import failure, httpd

READ_SIZE = 4096
POLL_SECONDS = 0.05
WRITE_SECONDS = 5.0

# The serial ways a connection takes, the lowest free one; the serial port has way 1. A
# connection that finds none free has way 0, of no push.
FIRST_WAY = 2
LAST_WAY = 8


class Connection(socketserver.BaseRequestHandler):
    """One program's connection, with a serial way of its own. Every byte it sends goes to
    the port's `feed` with that way, and what `feed` returns is written back to it; between
    the replies it is given what the port's `pushed` has for its way."""

    def setup(self):
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.request.settimeout(POLL_SECONDS)
        self.taken, self.way = self.server.opened(self.request)

    def handle(self):
        while self.taken:
            try:
                data = self.request.recv(READ_SIZE)
            except socket.timeout:
                data = None
            except OSError:
                return
            if self.server.closing() or data == b"":
                return
            try:
                if data:
                    self._send(self.server.feed(data, self.way))
                self._send(self.server.pushed(self.way))
            except OSError:
                return

    def _send(self, data):
        """Writes what there is, waiting for a slow reader longer than for what arrives."""
        if data:
            self.request.settimeout(WRITE_SECONDS)
            try:
                self.request.sendall(data)
            finally:
                self.request.settimeout(POLL_SECONDS)

    def finish(self):
        self.server.closed(self.request, self.way)


class Port(socketserver.ThreadingTCPServer):
    """A TCP port that programs connect to, any number of them and any number of times.

    The bytes of every connection reach one `feed`, as the bytes of every program that
    opens a serial port do, with the serial way of the connection: `feed(data, way)`, and a
    reply goes to the connection whose bytes it answers. `pushed(way)` gives what a
    connection is written between replies, the `#plan` lines of its way, and `ended(way)`
    is told when a connection with a way closes.
    """

    daemon_threads = True
    allow_reuse_address = httpd.REUSE_ADDRESS

    def __init__(self, port, feed, pushed=None, ended=None):
        self.feed = feed
        self._pushed = pushed
        self._ended = ended
        self._connections = {}
        self._closing = False
        self._lock = threading.Lock()
        try:
            super().__init__((httpd.ADDRESS, port), Connection)
        except OSError as error:
            raise failure.Failure(failure.ADDRESS_IN_USE, f"{httpd.ADDRESS}:{port}: {error.strerror or type(error).__name__}") from None
        self._thread = threading.Thread(target=self.serve_forever, kwargs={"poll_interval": POLL_SECONDS}, name="tcp", daemon=True)

    @property
    def port(self):
        return self.server_address[1]

    @property
    def address(self):
        return f"{httpd.ADDRESS}:{self.port}"

    def opened(self, connection):
        """Takes a connection, unless the port is closing, and gives it the lowest free way.
        Says whether it was taken, and its way."""
        with self._lock:
            if self._closing:
                return False, 0
            used = set(self._connections.values())
            way = next((way for way in range(FIRST_WAY, LAST_WAY + 1) if way not in used), 0)
            self._connections[connection] = way
            return True, way

    def closing(self):
        with self._lock:
            return self._closing

    def pushed(self, way):
        """What a connection of this way is given between replies, or nothing."""
        return self._pushed(way) if self._pushed is not None and way else None

    def closed(self, connection, way=0):
        """Lets a connection go. Its way is told ended first and is free only then, so that
        the next connection that takes it is not ended with it."""
        if way and self._ended is not None:
            self._ended(way)
        with self._lock:
            self._connections.pop(connection, None)

    def start(self):
        self._thread.start()

    def close(self):
        """Stops taking connections and ends the ones that are open. From here on no
        connection is taken and no byte is handed to `feed`."""
        with self._lock:
            self._closing = True
        if self._thread.is_alive():
            self.shutdown()
            self._thread.join()
        self.server_close()
        with self._lock:
            connections = list(self._connections)
        for connection in connections:
            with contextlib.suppress(OSError):
                connection.shutdown(socket.SHUT_RDWR)

    def handle_error(self, request, client_address):
        """A connection that breaks ends only that connection."""

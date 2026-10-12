"""The line port: the line protocol of the serial port on a TCP port of the page's address."""

import contextlib
import socket
import socketserver
import threading

from . import failure, httpd

READ_SIZE = 4096
POLL_SECONDS = 0.05


class Connection(socketserver.BaseRequestHandler):
    """One program's connection. Every byte it sends goes to the port's `feed`, and what
    `feed` returns is written back to it."""

    def setup(self):
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.server.opened(self.request)

    def handle(self):
        while True:
            try:
                data = self.request.recv(READ_SIZE)
                if not data:
                    return
                reply = self.server.feed(data)
                if reply:
                    self.request.sendall(reply)
            except OSError:
                return

    def finish(self):
        self.server.closed(self.request)


class Port(socketserver.ThreadingTCPServer):
    """A TCP port that programs connect to, any number of them and any number of times.

    The bytes of every connection reach one `feed`, as the bytes of every program that
    opens a serial port do, and a reply goes to the connection whose bytes it answers.
    """

    daemon_threads = True
    allow_reuse_address = httpd.REUSE_ADDRESS

    def __init__(self, port, feed):
        self.feed = feed
        self._connections = set()
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
        with self._lock:
            self._connections.add(connection)

    def closed(self, connection):
        with self._lock:
            self._connections.discard(connection)

    def start(self):
        self._thread.start()

    def close(self):
        """Stops taking connections and ends the ones that are open."""
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

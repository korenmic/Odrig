"""The HTTP server on the page address: commands as `POST /odrig`."""

import http.server
import re
import sys
import threading

from . import failure

ADDRESS = "127.0.0.1"
COMMAND_PATH = "/odrig"
BODY_KEPT = 128
CHUNK = 65536

WHOLE_NUMBER = re.compile(r"[0-9]+")


class Handler(http.server.BaseHTTPRequestHandler):
    """Answers one connection. The server object carries the engine."""

    protocol_version = "HTTP/1.1"

    def version_string(self):
        return "odrig-emulator"

    def log_message(self, format, *arguments):
        pass

    def __getattr__(self, name):
        if name.startswith("do_"):
            return self.answer
        raise AttributeError(name)

    def answer(self):
        path = self.path.split("?", 1)[0]
        if path == COMMAND_PATH:
            if self.command == "POST":
                self.command_line()
            else:
                self.empty(405, {"Allow": "POST"})
        else:
            self.empty(404)

    def empty(self, status, headers=None):
        """An answer without a body. The connection is closed after it, because a body the
        request may carry is not read."""
        self.close_connection = True
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def command_line(self):
        length = self.headers.get("Content-Length")
        if length is None or not WHOLE_NUMBER.fullmatch(length.strip()):
            self.empty(411)
            return
        left = int(length.strip())
        kept = b""
        while left > 0:
            piece = self.rfile.read(min(left, CHUNK))
            if not piece:
                self.close_connection = True
                return
            left -= len(piece)
            if len(kept) < BODY_KEPT:
                kept += piece[:BODY_KEPT - len(kept)]
        reply = self.server.engine.line(kept, "http")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, engine):
        self.engine = engine
        try:
            super().__init__((ADDRESS, port), Handler)
        except OSError as error:
            raise failure.Failure(failure.ADDRESS_IN_USE, f"{ADDRESS}:{port}: {error.strerror or type(error).__name__}") from None
        self._thread = threading.Thread(target=self.serve_forever, kwargs={"poll_interval": 0.05}, name="http", daemon=True)

    @property
    def port(self):
        return self.server_address[1]

    @property
    def url(self):
        return f"http://{ADDRESS}:{self.port}/"

    def start(self):
        self._thread.start()

    def stop(self):
        if self._thread.is_alive():
            self.shutdown()
            self._thread.join()
        self.server_close()

    def handle_error(self, request, client_address):
        """A connection that breaks ends only that connection."""
        if not isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            super().handle_error(request, client_address)

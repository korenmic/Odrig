"""The HTTP server on the page address: the files of the page, commands as `POST /odrig`,
the event stream for the page, and the mapping file of the show."""

import http.server
import os
import re
import socket
import sys
import threading

from . import failure

ADDRESS = "127.0.0.1"
# Every IPv4 address of this computer: where the server listens when it is to be reached
# from the local network.
EVERY_ADDRESS = "0.0.0.0"
# An address reserved for documents. Nothing is sent to it.
NOWHERE = "192.0.2.1"
# Lets a server take its port again right after an earlier one closed. Windows needs no
# such leave, and there it would let a second server take a port that is in use.
REUSE_ADDRESS = sys.platform != "win32"
COMMAND_PATH = "/odrig"
EVENTS_PATH = "/events"
MAPPING_PATH = "/show/mapping.json"
MAPPING_NAME = "mapping.json"
BODY_KEPT = 4096
CHUNK = 65536
KEEP_ALIVE_SECONDS = 15
STREAM_SEND_BUFFER = 32768

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
INDEX = "index.html"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "text/javascript",
    ".json": "application/json",
}


def page_files(folder=WEB):
    """The files of the page by the path each is asked for: its place on disk and its
    content type. The table is made by listing the folder, so nothing outside it can be
    asked for."""
    files = {}
    for name in sorted(os.listdir(folder)):
        place = os.path.join(folder, name)
        content_type = CONTENT_TYPES.get(os.path.splitext(name)[1])
        if content_type is not None and os.path.isfile(place):
            files["/" + name] = (place, content_type)
    if "/" + INDEX in files:
        files["/"] = files["/" + INDEX]
    return files


def stream(connection, write, keep_alive_seconds=KEEP_ALIVE_SECONDS):
    """Writes what a connection of the hub has to send, each event at once, until the
    connection is closed or a write fails. A connection with nothing to send for a while
    is sent a comment line."""
    while True:
        events = connection.take(keep_alive_seconds)
        if events is None:
            return
        text = "".join(f"event: {kind}\ndata: {data}\n\n" for kind, data in events) if events else ": keep-alive\n\n"
        try:
            write(text.encode("utf-8"))
        except OSError:
            return

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
        elif self.command == "GET" and path == EVENTS_PATH:
            self.events()
        elif self.command == "GET" and path == MAPPING_PATH:
            self.mapping()
        elif self.command == "GET" and path in self.server.pages:
            self.page(*self.server.pages[path])
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

    def content(self, content_type, data):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def page(self, place, content_type):
        """One file of the page."""
        try:
            with open(place, "rb") as file:
                data = file.read()
        except OSError:
            self.empty(404)
            return
        self.content(content_type, data)

    def mapping(self):
        """The mapping file of the show folder, byte for byte."""
        try:
            with open(os.path.join(self.server.show_dir, MAPPING_NAME), "rb") as file:
                data = file.read()
        except OSError:
            self.empty(404)
            return
        self.content("application/json", data)

    def events(self):
        """The event stream: a response without a length that stays open."""
        self.close_connection = True
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, STREAM_SEND_BUFFER)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        connection = self.server.engine.hub.connect(self.server.hello())
        try:
            stream(connection, self.write_now)
        finally:
            self.server.engine.hub.disconnect(connection)

    def write_now(self, data):
        self.wfile.write(data)
        self.wfile.flush()


def lan_address():
    """The address this computer has on the network that carries its default route, or
    None when it is on no network. Connecting a datagram socket sends nothing: it asks
    the system which of the computer's addresses would be used."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect((NOWHERE, 9))
        except OSError:
            return None
        address = probe.getsockname()[0]
    return None if address.startswith("127.") else address


class Server(http.server.ThreadingHTTPServer):
    """The server on 127.0.0.1, or with `lan` on every address of this computer."""

    daemon_threads = True
    allow_reuse_address = REUSE_ADDRESS

    def __init__(self, port, engine, show_dir, hello, lan=False):
        self.engine = engine
        self.show_dir = os.fspath(show_dir)
        self.hello = hello
        self.pages = page_files()
        try:
            super().__init__((EVERY_ADDRESS if lan else ADDRESS, port), Handler)
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

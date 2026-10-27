"""The web code on 127.0.0.1, for a browser on this computer."""

import http.server
import re
import sys
import threading

from . import Failure, paths

ADDRESS = "127.0.0.1"
PORT = 8610
INDEX = "index.html"
# What the server hands out, by the ending of the file's name.
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
}
# What the server hands out of the default preview catalog, by the ending of the file's name.
THUMBNAIL_TYPES = {".js": "text/javascript; charset=utf-8", ".gif": "image/gif"}
# One part of a path: a name without a path separator that does not begin with a dot.
PART = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9._-]*")


def file_of(folder, path, types=TYPES):
    """The file of a folder that a request path names, or None. A path names a file by the
    names of the folders that lead to it; `/` is the index."""
    parts = [part for part in path.split("/") if part != ""] or [INDEX]
    if path.endswith("/") and path != "/":
        return None
    if not all(PART.fullmatch(part) for part in parts) or "." + parts[-1].rsplit(".", 1)[-1] not in types:
        return None
    found = folder.joinpath(*parts)
    return found if found.is_file() else None


def file_of_the_app(folder, path, library=paths.CONVERTER_LIB, thumbnails=paths.THUMBNAILS):
    """The file a request path names: one of the web code of a folder, under
    `/converter/` one of the converter's library, or under `/thumbnails/` the mapping or a GIF
    of the default preview catalog, none of a folder below it."""
    beside = "/" + paths.LIBRARY_FOLDER + "/"
    if path.startswith(beside):
        return file_of(library, path[len(beside) - 1:])
    previews = "/" + paths.THUMBNAILS_FOLDER + "/"
    if path.startswith(previews):
        rest = path[len(previews) - 1:]
        return file_of(thumbnails, rest, THUMBNAIL_TYPES) if rest.count("/") == 1 else None
    return file_of(folder, path)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *arguments):
        pass

    def answer(self, status, content_type=None, body=b""):
        self.send_response(status)
        if content_type is not None:
            self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        found = file_of_the_app(self.server.folder, self.path.split("?", 1)[0])
        if found is None:
            self.answer(404)
        else:
            self.answer(200, {**TYPES, **THUMBNAIL_TYPES}[found.suffix] if found.parent == paths.THUMBNAILS else TYPES[found.suffix], found.read_bytes())


class Server(http.server.ThreadingHTTPServer):
    """Hands out the files of the web code and of the converter's library beside it, each
    with its content type, and nothing else."""

    daemon_threads = True
    # On Windows the option would let a second program take a port another one holds.
    allow_reuse_address = sys.platform != "win32"

    def __init__(self, port=PORT, folder=paths.WWW, handler=Handler):
        self.folder = folder
        try:
            super().__init__((ADDRESS, port), handler)
        except OSError as error:
            raise Failure("address-in-use", f"{ADDRESS}:{port}: {error.strerror or type(error).__name__}") from None
        self._thread = threading.Thread(target=self.serve_forever, kwargs={"poll_interval": 0.05}, name="app", daemon=True)

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
        # A browser that went away in the middle of a request is no fault of the server.
        if not isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            super().handle_error(request, client_address)

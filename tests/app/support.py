"""What the tests of the app share: targets, the server of the web code, Chrome, and one
run of a scenario in it."""

import collections
import http.server
import json
import os
import pathlib
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "app"
WWW = APP / "www"
CONVERTER_LIBRARY = ROOT / "converter" / "lib"
PAGE = pathlib.Path(__file__).resolve().parent / "page"

if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from apptool import webserver  # noqa: E402

WAIT_SECONDS = 60
SIZE = (360, 740)
CHROMES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
)


def chrome():
    """The Chrome to start: the program the environment variable ODRIG_CHROME names, or
    the first of the usual places that has one."""
    named = os.environ.get("ODRIG_CHROME")
    places = ([named] if named else []) + list(CHROMES)
    for place in places:
        if os.path.exists(place):
            return place
    raise AssertionError("no Chrome was found; the suite looked at " + ", ".join(places) + "; name one with ODRIG_CHROME")


def free_port():
    """A port of 127.0.0.1 that nothing listens on now."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class _Answer(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *arguments):
        pass

    def do_POST(self):
        target = self.server.target
        line = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        reply = target.taken(self.path, line)
        try:
            time.sleep(target.delay)
            if reply is None:
                # No answer at all, until the target is stopped.
                target.stopping.wait()
                self.close_connection = True
                return
            status, body = reply
            body = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        finally:
            target.left()


class _Quiet(http.server.ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # A browser that went away in the middle of a request is no fault of the target.
        if not isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            super().handle_error(request, client_address)


class StandIn:
    """A target of the test's own on a free port of 127.0.0.1.

    It answers each `POST /odrig` with the next of the replies it was given, and with the
    last of them from then on, each after `delay` seconds. A reply is `(status, body)`,
    or None for no answer at all, or a mapping from the first word of a line to one of
    the two, in which a word that is missing is an unknown command. `lines` holds the
    lines it was sent, and `together` the most requests it had at one moment.
    """

    def __init__(self, *replies, delay=0.0):
        self.replies = list(replies)
        self.delay = delay
        self.lines = []
        self.together = 0
        self.stopping = threading.Event()
        self._now = 0
        self._lock = threading.Lock()
        self._server = _Quiet(("127.0.0.1", 0), _Answer)
        self._server.daemon_threads = True
        self._server.target = self
        self.address = f"127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)

    def taken(self, path, line):
        with self._lock:
            self._now += 1
            self.together = max(self.together, self._now)
            self.lines.append((path, line))
            reply = self.replies[min(len(self.lines), len(self.replies)) - 1]
        if isinstance(reply, dict):
            reply = reply.get(line.split(b" ")[0].decode("ascii", "replace"), (200, '{"ok":false,"error":"unknown-command"}\n'))
        return reply

    def left(self):
        with self._lock:
            self._now -= 1

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exception):
        self.stopping.set()
        self._server.shutdown()
        self._thread.join()
        self._server.server_close()


class _Pages(webserver.Handler):
    """The web code as the tool serves it, and for a test: the files of the driver under
    `/t/`, the result of a scenario, the steps a scenario asks the test for, and every
    request Chrome would have sent to another computer, which ends here and goes nowhere."""

    def elsewhere(self):
        """Whether the request is for another computer. It is answered with 502, and kept
        when a page asked for it: Chrome asks for things of its own, which name no page."""
        if self.path.startswith("/"):
            return False
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        asked_by = self.headers.get("Origin") or self.headers.get("Referer") or ""
        if asked_by.startswith(self.server.url.rstrip("/")):
            self.server.elsewhere.append((self.command, self.path, body))
        self.answer(502)
        return True

    def do_GET(self):
        if self.elsewhere():
            return
        path = self.path.split("?", 1)[0]
        if path.startswith("/t/"):
            found = webserver.file_of(PAGE, path[len("/t"):])
            if found is None:
                self.answer(404)
            else:
                self.answer(200, webserver.TYPES[found.suffix], found.read_bytes())
            return
        super().do_GET()

    def do_POST(self):
        if self.elsewhere():
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.path == "/result":
            self.server.results.put(body)
            self.answer(204)
        elif self.path == "/step":
            try:
                self.server.steps.pop(0)()
            except Exception as error:
                self.server.results.put(json.dumps({"ok": False, "error": f"a step of the test failed: {error!r}", "screen": ""}).encode())
            self.answer(204)
        else:
            self.answer(404)

    def do_CONNECT(self):
        self.answer(502)


# What `status` answers on a target where the playlist plays its first animation, what
# `list` answers there, and a target that answers both so.
PLAYING = (200, '{"ok":true,"on":true,"brightness":128,"playing":"all","animation":1,"fps":50,"error":null}\n')
LISTED = (200, '{"ok":true,"items":[{"id":1,"file":"one.odrg","bytes":1138},{"id":2,"file":"two.odrg","bytes":1612}],"next":null}\n')
SOUND = {"status": PLAYING, "list": LISTED}

Run = collections.namedtuple("Run", "seen elsewhere")


def commands_elsewhere(found):
    """The command lines a run sent to other computers than this one, each as
    `(address, line)`."""
    sent = []
    for method, url, body in found.elsewhere:
        parts = urllib.parse.urlsplit(url)
        if method == "POST" and parts.path == "/odrig":
            sent.append((parts.netloc, body))
    return sent


def run(scenario, address=None, settings=None, steps=(), size=SIZE):
    """Runs one scenario of `page/scenarios/` against the web code in Chrome without a
    window, and gives what the scenario found and what the pages asked other computers
    for, each as `(method, address, body)`.

    `address` is the address the app is to use, kept before the app starts; without one
    the app starts as on a new phone. `settings` reach the scenario as they are. Each
    time the scenario asks for a step, the next function of `steps` is called.
    """
    server = webserver.Server(0, handler=_Pages)
    server.results = queue.Queue()
    server.steps = list(steps)
    server.elsewhere = []
    server.start()
    profile = tempfile.mkdtemp(prefix="odrig-app-chrome-")
    asked = {"scenario": scenario, "settings": json.dumps(settings or {}), "width": str(size[0]), "height": str(size[1])}
    if address is not None:
        asked["address"] = address
    command = [
        chrome(), "--headless=new", "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-background-networking",
        "--disable-sync", "--disable-component-update", f"--window-size={size[0]},{size[1]}", f"--user-data-dir={profile}",
        # What is not for this computer goes to the suite's own server, and no further.
        f"--proxy-server=http://127.0.0.1:{server.port}",
        f"{server.url}t/driver.html?{urllib.parse.urlencode(asked)}",
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        try:
            result = json.loads(server.results.get(timeout=WAIT_SECONDS))
        except queue.Empty:
            raise AssertionError(f"the scenario {scenario} gave no result in {WAIT_SECONDS} seconds") from None
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        server.stop()
        shutil.rmtree(profile, ignore_errors=True)
    if not result["ok"]:
        raise AssertionError(f"the scenario {scenario} failed: {result['error']}\nOn the screen:\n{result['screen']}")
    return Run(result["seen"], list(server.elsewhere))

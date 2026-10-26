"""The seek bar on the emulator's page, seen in Chrome: its numbers move with the
animation, and a drag of the bar moves playback to the point.

Chrome without a window dumps a page's DOM once the page has loaded, and the emulator's
page is never done loading while its event stream is open. So Chrome is given a harness
page, served beside the emulator's page: it frames the page, reads the seek bar's numbers
into its own body every tenth of a second, drags the bar after a while with pointer
events of its own, and holds its load event back with an image that this test's server
answers late. The dump of the harness then holds the readings.
"""

import http.server
import json
import pathlib
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

from emulator import binding, engine, host, httpd, hub
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

HARNESS = """<!doctype html>
<html><head><meta charset="utf-8"><title>harness</title></head><body>
<iframe id="page" src="/" width="1000" height="600"></iframe>
<div id="out"></div>
<img src="http://127.0.0.1:%d/wait" alt="">
<script>
var frame = document.getElementById("page");
var out = document.getElementById("out");
var readings = [];
var dragged = null;
var started = performance.now();
setInterval(function () {
  var doc = frame.contentDocument;
  var time = doc && doc.getElementById("seek-time");
  if (!time || doc.getElementById("seek").hidden) return;
  readings.push([Math.round(performance.now() - started), time.textContent]);
  if (dragged === null && performance.now() - started > %d) {
    var bar = doc.getElementById("seek-bar");
    var box = bar.getBoundingClientRect();
    var x = box.left + box.width * 0.9;
    var y = box.top + box.height / 2;
    ["pointerdown", "pointermove", "pointerup"].forEach(function (type) {
      bar.dispatchEvent(new frame.contentWindow.PointerEvent(type, {bubbles: true, clientX: x, clientY: y, pointerId: 1, isPrimary: true}));
    });
    dragged = Math.round(performance.now() - started);
  }
  out.textContent = JSON.stringify({readings: readings, dragged: dragged, note: doc.getElementById("seek-note").textContent});
}, 100);
</script>
</body></html>
"""
DRAG_AFTER_MS = 2500
WAIT_SECONDS = 6
READINGS = __import__("re").compile(r'<div id="out">(\{.*?\})</div>')


class SlowImage(http.server.BaseHTTPRequestHandler):
    """Answers every request after a wait, so that a page with this image loads late."""

    def log_message(self, *_):
        pass

    def do_GET(self):
        time.sleep(WAIT_SECONDS)
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()


class TheSeekBar(unittest.TestCase):
    def setUp(self):
        self.folder = entered(self, emulator_support.demo_show())
        files = host.FolderHost(self.folder)
        self.addCleanup(files.close)
        core = binding.Core(emulator_support.LIBRARY, files)
        self.engine = engine.Engine(core, hub.Hub(), host=files)
        self.engine.tick()
        self.engine.refresh_status()
        self.loop = engine.RealTime(self.engine)
        self.loop.start()
        self.addCleanup(self.loop.stop)
        hello = lambda: {"show": str(self.folder), "drive": None, "page": self.server.url, "serial": None, "tcp": None, "legs": [list(leg) for leg in core.legs], "t0": self.engine.t0, "error": self.engine.error()}
        self.server = httpd.Server(0, self.engine, self.folder, hello)
        self.addCleanup(self.server.stop)
        self.server.start()
        self.slow = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SlowImage)
        threading.Thread(target=self.slow.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.addCleanup(self.slow.shutdown)
        self.harness = pathlib.Path(entered(self, tempfile.TemporaryDirectory()), "harness.html")
        self.harness.write_text(HARNESS % (self.slow.server_address[1], DRAG_AFTER_MS), encoding="utf-8")
        self.server.pages["/harness.html"] = (str(self.harness), "text/html; charset=utf-8")
        self.engine.line(b"play all", "http")

    def readings(self):
        """What the harness read of the seek bar until the dump."""
        profile = tempfile.mkdtemp(prefix="odrig-seek-chrome-")
        self.addCleanup(shutil.rmtree, profile, ignore_errors=True)
        command = [
            support.chrome(), "--headless=new", "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-background-networking",
            "--disable-sync", "--disable-component-update", "--hide-scrollbars", "--window-size=1200,800", f"--user-data-dir={profile}",
            "--dump-dom", f"http://127.0.0.1:{self.server.port}/harness.html",
        ]
        done = subprocess.run(command, capture_output=True, timeout=90)
        found = READINGS.search(done.stdout.decode("utf-8", "replace"))
        self.assertIsNotNone(found, "the harness read nothing of the seek bar")
        return json.loads(found.group(1).replace("&quot;", '"'))

    def seconds_of(self, text):
        minutes, seconds = text.split(" / ")[0].split(":")
        return int(minutes) * 60 + int(seconds)

    def test_the_numbers_move_with_the_animation_and_a_drag_moves_playback_to_the_point(self):
        read = self.readings()
        self.assertGreaterEqual(len(read["readings"]), 20)
        self.assertIsNotNone(read["dragged"])
        before = [text for ms, text in read["readings"] if ms < read["dragged"]]
        after = [text for ms, text in read["readings"] if read["dragged"] <= ms <= read["dragged"] + 400]
        self.assertGreater(len(set(before)), 1, before)
        self.assertGreaterEqual(len(after), 2, after)
        length = self.engine.playback.length
        self.assertIsNotNone(length)
        self.assertEqual(before[0].split(" / ")[1], after[-1].split(" / ")[1])
        self.assertLessEqual(abs(self.seconds_of(after[-1]) - 0.9 * length / 1000), 1, after)
        self.assertRegex(read["note"], r"\Aclock \+[0-9]+ s\Z|\A\Z")


if __name__ == "__main__":
    unittest.main()

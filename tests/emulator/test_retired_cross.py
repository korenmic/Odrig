"""The retired `mapping cross` in the emulator: refused, counted nowhere, and no reason to
send the page the mapping again; a mapping save still sends it."""

import json
import pathlib
import tempfile
import time
import unittest

from emulator import binding, engine, host, hub
from tests.core import support as core_support
from tests.mapping.test_core import PINS, crossed_files, files, set_line

from . import support


class Watched(hub.Hub):
    """A hub that keeps every routing it is sent."""

    def __init__(self):
        super().__init__()
        self.sent = []

    def mapping(self, legs):
        self.sent.append([list(leg) for leg in legs])
        super().mapping(legs)


class TheRetiredCross(unittest.TestCase):
    def started(self, source):
        root = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.folder = support.installed(root / "show", source)
        files_host = host.FolderHost(self.folder)
        self.addCleanup(files_host.close)
        self.hub = Watched()
        self.core = binding.Core(support.LIBRARY, files_host)
        self.engine = engine.Engine(self.core, self.hub)
        self.engine.tick()

    def checked(self):
        """Refreshes until the check after the start is over, which a mapping save waits for."""
        deadline = time.monotonic() + 60
        while json.loads(self.engine.line(b"status", "http"))["checking"] is not None:
            self.assertLess(time.monotonic(), deadline, "the check after the start did not end")
            time.sleep(0.02)
            self.engine.tick()

    def test_the_binding_keeps_no_count_of_it_and_the_routing_is_the_legs_alone(self):
        self.started(files())
        self.assertFalse(hasattr(self.core, "wiring_saves"))
        self.assertEqual(self.engine.routing(), self.core.legs)

    def test_it_is_refused_on_each_way_in_changes_nothing_and_sends_the_page_nothing(self):
        for source in (files(), crossed_files()):
            with self.subTest(crossed=source != files()):
                self.started(source)
                before = support.files_of(self.folder)
                mapping = json.loads(self.engine.line(b"mapping get", "http"))
                for line in (b"mapping cross on", b"mapping cross off"):
                    self.assertEqual(json.loads(self.engine.line(line, "http")), {"ok": False, "error": "bad-argument"})
                    self.assertEqual(json.loads(self.engine.feed(line + b"\n", "serial")), {"ok": False, "error": "bad-argument"})
                self.assertEqual(json.loads(self.engine.line(b"mapping get", "http")), mapping)
                self.assertEqual(support.files_of(self.folder), before)
                self.assertEqual(self.hub.sent, [])

    def test_a_mapping_save_still_sends_the_page_the_new_routing(self):
        self.started(files())
        self.checked()
        swapped = PINS.copy()
        swapped[0], swapped[19] = swapped[19], swapped[0]
        self.assertEqual(json.loads(self.engine.line(set_line(swapped).encode(), "http")), {"ok": True})
        self.assertEqual(len(self.hub.sent), 1)
        self.assertEqual(self.hub.sent[0], [list(leg) for leg in self.core.legs])
        self.assertEqual(json.loads(self.engine.feed(set_line(PINS, core_support.zlib.crc32(bytes(swapped))).encode() + b"\n", "serial")), {"ok": True})
        self.assertEqual(len(self.hub.sent), 2)


if __name__ == "__main__":
    unittest.main()

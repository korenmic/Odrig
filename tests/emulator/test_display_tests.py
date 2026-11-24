"""The display tests through the emulator: taken while the check after the start goes on,
in record mode, whose time is the script's, and an upload opened before a test ending under
it, over the emulator's TCP line."""

import json
import pathlib
import tempfile
import time
import unittest

from tests.core import support as core_support
from tests.core.test_snakes import PINS, REVISION, files

from . import support
from .test_record import script_text


class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))

    def test_a_test_and_a_mapping_save_are_taken_while_the_check_after_the_start_goes_on(self):
        folder = support.installed(self.work / "show", files())
        swapped = PINS.copy()
        swapped[0], swapped[19] = swapped[19], swapped[0]
        commands = [(0, "status"), (0, "mapping test snake 3"), (0, f"mapping set {REVISION} " + ",".join(map(str, swapped))), (2900, "status"), (2950, "mapping get")]
        script = self.work / "script.txt"
        script.write_text(script_text(commands), encoding="utf-8")
        result = support.run(folder, "--record", self.work / "out.odrr", "--seconds", 3, "--script", script)
        self.assertEqual((result.status, result.err), (0, ""))
        replies = [json.loads(line.split(" ", 2)[2]) for line in result.out.splitlines()]
        before, test, save, after, mapping = replies
        self.assertIsNotNone(before["checking"])
        self.assertEqual((test, save), ({"ok": True}, {"ok": True}))
        self.assertEqual((after["checking"], after["to_check"], after["playing"], after["animation"]), (None, 0, None, None))
        self.assertEqual((mapping["test"], mapping["snake"], mapping["pins"]), (True, 3, swapped))

    def test_an_upload_opened_before_a_test_ends_under_it_over_tcp(self):
        folder = support.installed(self.work / "show", files())
        emulator = support.entered(self, support.Emulator(folder, tcp_port=0))
        data = core_support.clip(11, 60, 60, (20, 20, 20))
        begin, *pieces = core_support.upload_lines(3, "new.odrg", data)
        with support.Lines(emulator.tcp) as port:
            self.assertEqual(json.loads(port.ask("play 2")), {"ok": True})
            self.assertTrue(json.loads(port.ask(begin))["ok"])
            self.assertEqual(json.loads(port.ask("mapping test on")), {"ok": True})
            for piece in pieces:
                self.assertTrue(json.loads(port.ask(piece))["ok"])
            deadline = time.monotonic() + 30
            while (ended := json.loads(port.ask(core_support.upload_end(data)))) == {"ok": False, "error": "busy"}:
                self.assertLess(time.monotonic(), deadline, "the upload's check did not end under the test")
                time.sleep(0.05)
            self.assertEqual(ended, {"ok": True})
            during = json.loads(port.ask("status"))
            listed = json.loads(port.ask("list"))
            self.assertEqual(json.loads(port.ask("mapping test off")), {"ok": True})
            after = json.loads(port.ask("status"))
        self.assertEqual((during["playing"], during["animation"]), (None, None))
        self.assertEqual([item["id"] for item in listed["items"]], [1, 2, 3])
        self.assertEqual((after["playing"], after["animation"]), ("all", 2))


if __name__ == "__main__":
    unittest.main()

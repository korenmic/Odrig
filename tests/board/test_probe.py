import pathlib
import shutil
import tempfile
import unittest

from . import PORT, support


class Probe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("probe")
        with support.dim_show() as folder:
            support.ensure_installed(folder)

    def test_wled_is_held_in_its_live_mode(self):
        self.assertEqual(support.probe()["realtime"], 1)

    def test_the_time_the_core_took_to_start_is_reported(self):
        report = support.probe()
        self.assertIsInstance(report["start_ms"], int)
        self.assertGreater(report["start_ms"], 0)

    def test_the_report_has_the_reason_that_status_has(self):
        self.assertIsNone(support.probe()["error"])
        self.assertIsNone(support.command(PORT, "status")[1]["error"])
        with support.dim_show() as packed, tempfile.TemporaryDirectory() as work:
            folder = pathlib.Path(work, "show")
            shutil.copytree(packed, folder)
            (folder / "show.json").unlink()
            self.addCleanup(self.put_back)
            self.assertEqual(support.install(folder, "--no-check").status, 1)
            self.assertEqual(support.probe()["error"], "show-missing")
            self.assertEqual(support.command(PORT, "status")[1]["error"], "show-missing")

    def put_back(self):
        with support.dim_show() as folder:
            support.ensure_installed(folder)

    def test_the_port_is_silent_without_a_command(self):
        self.assertEqual(support.heard(b"", 5.0), [])

    def test_wleds_handshake_gets_no_answer_and_the_byte_goes_to_the_core(self):
        self.assertEqual(support.heard(b"v", 3.0), [])
        self.assertEqual(support.heard(b"\n", 1.0), [b'{"ok":false,"error":"unknown-command"}'])
        self.assertEqual(support.command(PORT, "status")[0], 0)

    def test_the_probe_line_is_answered_by_the_usermod_and_every_other_byte_reaches_the_core(self):
        self.assertEqual(support.probe()["probe"], 1)
        self.assertEqual(support.heard(b"#prob\n", 1.0), [b'{"ok":false,"error":"unknown-command"}'])
        self.assertEqual(support.heard(b"#probes\n", 1.0), [b'{"ok":false,"error":"unknown-command"}'])
        self.assertEqual(support.heard(b"##probe\n", 1.0), [b'{"ok":false,"error":"unknown-command"}'])
        self.assertEqual(support.heard(b"on #probe\n", 1.0), [b'{"ok":false,"error":"bad-argument"}'])
        self.assertEqual(support.command(PORT, "status")[0], 0)

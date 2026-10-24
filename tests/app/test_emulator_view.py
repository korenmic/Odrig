import shutil
import subprocess
import tempfile
import unittest

from tests.emulator import support as emulator_support

from . import support
from .test_target import entered


class TheControllerViewOfTheEmulator(unittest.TestCase):
    """The emulator's page shows the app in a frame of its controller view. What runs
    there is the web code of `app/www/`, aimed at the emulator that serves it."""

    def lines_of(self, end, enough, seconds):
        """Opens the emulator's page in Chrome without a window, its address ending as
        given, and gives the command lines the emulator took, each with its transport,
        until `enough` of them came or the time was over. Also gives the emulator."""
        emulator = entered(self, emulator_support.Emulator(entered(self, emulator_support.demo_show())))
        profile = tempfile.mkdtemp(prefix="odrig-app-chrome-")
        self.addCleanup(shutil.rmtree, profile, ignore_errors=True)
        command = [
            support.chrome(), "--headless=new", "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-background-networking",
            "--disable-sync", "--disable-component-update", "--window-size=1200,800", f"--user-data-dir={profile}",
            f"http://127.0.0.1:{emulator.port}/{end}",
        ]
        with emulator_support.EventStream(emulator.port) as stream:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                events = stream.read_until(lambda events: len(emulator_support.of_kind(events, "log")) >= enough, seconds)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        return [(entry["transport"], entry["line"]) for entry in emulator_support.of_kind(events, "log")], emulator

    def test_in_the_controller_view_the_app_asks_this_emulator_for_its_status_and_its_list(self):
        lines, emulator = self.lines_of("#controller", 4, 30)
        self.assertGreaterEqual(len(lines), 4)
        self.assertEqual({transport for transport, _ in lines}, {"http"})
        self.assertEqual(lines[0], ("http", "status"))
        self.assertIn(("http", "list 0"), lines)
        self.assertLessEqual({line for _, line in lines}, {"status", "list 0", "space"})
        self.assertIsNone(emulator.status()["error"])

    def test_in_the_other_views_the_app_does_not_run(self):
        for end in ("", "#mapping"):
            with self.subTest(end=end):
                lines, _ = self.lines_of(end, 1, 5)
                self.assertEqual(lines, [])

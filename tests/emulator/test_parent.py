import os
import subprocess
import sys
import time
import unittest

from . import support


def ends_within(process, seconds):
    deadline = time.monotonic() + seconds
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)
    return process.poll() is not None


class TheStarterWatched(unittest.TestCase):
    def test_an_emulator_ends_within_seconds_after_the_process_it_watches_is_killed(self):
        starter = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(starter.wait)
        self.addCleanup(starter.kill)
        with support.example_show() as show, support.Emulator(show, "--parent", str(starter.pid)) as emulator:
            time.sleep(1.5)
            self.assertIsNone(emulator.process.poll(), "the emulator ended while the process it watches runs")
            starter.kill()
            starter.wait()
            self.assertTrue(ends_within(emulator.process, 5), "the emulator outlived the process it watches")
            self.assertEqual(emulator.stop().status, 0)

    @unittest.skipIf(os.name == "nt", "pgrep finds the emulator by its command line on macOS and Linux")
    def test_the_preview_s_emulator_ends_when_the_preview_is_killed(self):
        show = self.enterContext(support.example_show())
        preview = subprocess.Popen([sys.executable, "-m", "preview", str(next(show.glob("*.odrg"))), "--mapping", str(show / "mapping.json"), "--no-browser"],
                                   cwd=support.ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.addCleanup(preview.wait)
        self.addCleanup(preview.kill)
        deadline = time.monotonic() + 20
        seen = []
        while time.monotonic() < deadline:
            line = preview.stdout.readline()
            seen.append(line)
            if line.startswith("page: ") or not line:
                break
        self.assertTrue(any(line.startswith("page: ") for line in seen), "".join(seen))
        children = subprocess.run(["pgrep", "-f", f"emulator .*--parent {preview.pid}"], capture_output=True, text=True).stdout.split()
        self.assertEqual(len(children), 1, children)
        preview.kill()
        preview.wait()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and subprocess.run(["pgrep", "-f", f"emulator .*--parent {preview.pid}"], capture_output=True).returncode == 0:
            time.sleep(0.1)
        self.assertNotEqual(subprocess.run(["pgrep", "-f", f"emulator .*--parent {preview.pid}"], capture_output=True).returncode, 0, "the preview's emulator outlived the preview")

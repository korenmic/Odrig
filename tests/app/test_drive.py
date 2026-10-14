import json
import pathlib
import tempfile
import time

from tests.emulator import support as emulator_support

from .test_controls import Controls
from .test_target import entered

# How long the test waits for the emulator to read the drive's animation.
WAIT_SECONDS = 10


class TheAnimationsOfADrive(Controls):
    def test_they_are_buttons_after_the_installed_ones_and_play(self):
        folder = entered(self, emulator_support.example_show())
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        emulator_support.installed(top / "odrig", {"Sunrise.odrg": (folder / "hello.odrg").read_bytes()})
        emulator = entered(self, emulator_support.Emulator(folder, "--drive", top))
        deadline = time.monotonic() + WAIT_SECONDS
        while len(json.loads(emulator.command("list"))["items"]) < 4 and time.monotonic() < deadline:
            time.sleep(0.1)
        presses = [{"press": "60001 Sunrise.odrg", "until": "Now 60001 Sunrise\\.odrg"}]
        seen, lines = self.sent(emulator, "presses", lambda line: line == "play 60001", rows=3, presses=presses)
        self.assertEqual([line for line, _ in lines], ["play 60001"])
        self.assertEqual(seen[0]["buttons"], ["On", "Off", "Playlist from the start", "1 hello.odrg", "2 dvd.odrg", "60001 Sunrise.odrg"])
        self.assertEqual((seen[0]["playing"], seen[0]["now"], [row["id"] for row in seen[0]["rows"] if row["marked"]]), ("Playlist", "Now 60001 Sunrise.odrg", [60001]))
        status = emulator.status()
        self.assertEqual((status["playing"], status["animation"]), ("all", 60001))

import json
import pathlib
import tempfile
import time
import unittest

from odrig import jsonframes, odrg
from tests.core import huge_tail
from tests.core import support as core_support

from . import support

# The longest a call of the core may take on the board, which a command waits for at most:
# a reply over the line port comes within it here too.
LONGEST_MS = 50

TEXT = huge_tail.REASON


class ResponsiveWithTheReproducer(unittest.TestCase):
    """These tests measure real time: they depend on the speed and the load of this Mac."""

    def show(self):
        """A show on the target file that plays a cycle of a sound animation and the
        reproducer, in turns of 2 seconds, from the start. The sound animation has 3,000
        small frames, and the check after the start reads it before it comes to the
        reproducer, for some seconds."""
        work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        black, dot = bytes(10800), b"\x10" + bytes(10799)
        sound = odrg.encode(jsonframes.Animation(60, 60, tuple((20, dot if step % 2 else black) for step in range(3000))), compressed=False)
        items = [{"id": 1, "file": "sound.odrg"}, {"id": 2, "file": "huge.odrg"}, {"id": 3, "cycle": [1, 2], "seconds": 2}]
        return support.installed(work / "show", {
            "mapping.json": support.TARGET.read_bytes(),
            "show.json": core_support.show_text(items, brightness=255, start=3),
            "huge.odrg": huge_tail.huge_tail(),
            "sound.odrg": sound,
        })

    def test_status_over_the_line_port_comes_within_50_ms_through_the_start_the_playback_and_the_check(self):
        with support.Emulator(self.show(), checked=False) as emulator, support.lines(emulator) as port:
            waits = []
            fault = None
            # From the start, while the player settles the reproducer and the check after
            # the start settles it too, until the check comes to its reason, and a second
            # after it.
            until = time.monotonic() + 30
            ended = None
            while time.monotonic() < until and (ended is None or time.monotonic() < ended + 1):
                started = time.monotonic()
                reply = port.ask("status")
                waits.append((time.monotonic() - started) * 1000)
                self.assertIsNone(json.loads(reply)["error"])
                started = time.monotonic()
                listed = json.loads(port.ask("list"))
                waits.append((time.monotonic() - started) * 1000)
                found = [item.get("fault") for item in listed.get("items", []) if item.get("file") == "huge.odrg"]
                if found and found[0] is not None and ended is None:
                    fault = found[0]
                    ended = time.monotonic()
                time.sleep(0.02)
            self.assertLessEqual(max(waits), LONGEST_MS, f"the longest wait for status: {max(waits):.1f} ms of {len(waits)}")
            self.assertEqual(fault, TEXT)
            self.assertGreater(len(waits), 50)


if __name__ == "__main__":
    unittest.main()

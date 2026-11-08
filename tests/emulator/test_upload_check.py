"""The emulator checks the owner's clock of 14,399 frames within two minutes of its last
byte, at whatever rate this computer gives it."""
import json
import pathlib
import sys
import tempfile
import time
import unittest

from tests.core import support as core_support

from . import support

CLOCK = core_support.ROOT / "collection" / "card" / "clocks" / "time-original-5-every-row-another-time.odrg"
BUSY = b'{"ok":false,"error":"busy"}\n'
LIMIT_SECONDS = 120


class TheOwnersClock(unittest.TestCase):
    def test_the_owners_clock_is_checked_within_two_minutes_of_its_last_byte(self):
        data = CLOCK.read_bytes()
        self.assertEqual(len(data), 471095)
        folder = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        emulator = support.entered(self, support.Emulator(folder))
        # The rate of a whole second is known from the second after the start on.
        deadline = time.monotonic() + 5
        while emulator.status()["fps"] == 0 and time.monotonic() < deadline:
            time.sleep(0.05)
        lines = core_support.upload_lines(1, "clock.odrg", data)
        for line in lines[:-1]:
            self.assertTrue(json.loads(emulator.command(line))["ok"], line[:40])
        self.assertEqual(json.loads(emulator.command(lines[-1])), {"ok": True, "received": len(data)})
        last_byte = time.monotonic()
        rates = []
        while True:
            ended = emulator.command(core_support.upload_end(data))
            took = time.monotonic() - last_byte
            if ended != BUSY or took > LIMIT_SECONDS:
                break
            rates.append(emulator.status()["fps"])
            time.sleep(0.25)
        self.assertEqual(ended, b'{"ok":true}\n', f"after {took:.1f} s")
        self.assertLessEqual(took, LIMIT_SECONDS)
        listed = json.loads(emulator.command("list"))["items"]
        self.assertEqual([(item["id"], item["file"], item["bytes"]) for item in listed], [(1, "clock.odrg", 471095)])
        least, most = (min(rates), max(rates)) if rates else ("-", "-")
        print(f"the owner's clock was checked in {took:.1f} s at {least} to {most} refreshes a second", file=sys.stderr)


if __name__ == "__main__":
    unittest.main()

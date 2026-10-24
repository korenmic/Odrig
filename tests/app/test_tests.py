import json
import pathlib
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

ENTRIES = ["Diagonal"] + [f"Snake {number}" for number in range(1, 21)]


class TheTestAnimations(unittest.TestCase):
    def emulator(self, files):
        folder = entered(self, core_support.installed(files))
        return entered(self, emulator_support.Emulator(pathlib.Path(folder)))

    def mapping_get(self, emulator):
        return json.loads(emulator.command("mapping get"))

    def test_settings_shows_them_in_a_pinned_group_and_the_target_shows_them_by_hand(self):
        emulator = self.emulator(core_support.demo_show())
        checks = []

        def snake_three():
            got = self.mapping_get(emulator)
            checks.append(("snake 3", got["test"], got["snake"], json.loads(emulator.command("status"))["playing"]))

        def stopped():
            got = self.mapping_get(emulator)
            checks.append(("stopped", got["test"], got["snake"], json.loads(emulator.command("status"))["playing"]))

        def diagonal():
            got = self.mapping_get(emulator)
            checks.append(("diagonal", got["test"], got["snake"], json.loads(emulator.command("status"))["playing"]))

        def played():
            got = self.mapping_get(emulator)
            status = json.loads(emulator.command("status"))
            checks.append(("played", got["test"], got["snake"], status["playing"], status["animation"]))
        found = support.run("testgroup", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "play": 2}, steps=[snake_three, stopped, diagonal, played]).seen
        # Off at first: no test is listed.
        self.assertTrue(found["hidden"])
        self.assertEqual(found["entriesOff"], [])
        self.assertEqual(found["checkbox"], {"checked": False, "label": "Show test animations 20 snake tests + diagonal"})
        # On: exactly 21 entries, pinned above the list, and remembered across a reload.
        self.assertEqual(found["entries"], ENTRIES)
        self.assertEqual(found["head"], "Tests · 21")
        self.assertTrue(found["above"])
        self.assertTrue(found["kept"])
        self.assertEqual((found["collapsed"], found["opened"]), (0, 21))
        self.assertEqual(found["pressed"], ["Snake 3"])
        self.assertEqual(checks, [("snake 3", True, 3, None), ("stopped", False, None, "all"), ("diagonal", True, None, None), ("played", False, None, "all", 2)])
        self.assertEqual(found["namedHidden"], "Test: Diagonal is showing. Normal playback is paused.")
        # The tests are no rows: the list and the order hold the animations alone.
        self.assertEqual(found["rowsBefore"], [1, 2])
        self.assertEqual(found["rowsAfter"], [1, 2])
        self.assertEqual(found["inList"], 0)
        self.assertEqual(json.loads(emulator.command("order get"))["ids"], [1, 2])

    def test_a_test_another_controller_started_is_named_and_can_be_stopped(self):
        emulator = self.emulator(core_support.demo_show())
        self.assertEqual(json.loads(emulator.command("mapping test snake 17")), {"ok": True})
        found = support.run("testgroup", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "watch": True}).seen
        self.assertTrue(found["hidden"])
        self.assertEqual(found["named"], "Test: Snake 17 is showing. Normal playback is paused.")
        self.assertIsNone(found["after"])
        self.assertFalse(self.mapping_get(emulator)["test"])

    def test_a_mapping_of_another_installation_gets_an_explanation_and_no_test(self):
        emulator = self.emulator(core_support.example_show())
        found = support.run("testgroup", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "unsupported": True}).seen
        self.assertEqual(found["entries"], ENTRIES)
        self.assertEqual(found["note"], "These tests need the 60 × 60 installation of twenty three-column snakes; this installation's mapping is another one.")
        self.assertTrue(found["disabled"])


if __name__ == "__main__":
    unittest.main()

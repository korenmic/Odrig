import json
import pathlib
import tempfile
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

MAPPING = core_support.mapping_texts()["legs-2"]


def clip(seed, durations=(20, 20, 20)):
    return core_support.clip(seed, 60, 6, durations)


class UnavailableAnimations(unittest.TestCase):
    """An animation whose file had a fault is shown grayed, with its reason, and cannot be
    played; the others play, and the rest of the app works."""

    def started(self, drive=None):
        work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        items = [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "file": "c.odrg"}]
        files = {"mapping.json": MAPPING, "show.json": json.dumps({"version": 1, "brightness": 128, "items": items}),
                 "a.odrg": clip(1), "b.odrg": b"ODRX" + clip(2)[4:]}
        folder = emulator_support.installed(work / "show", files)
        options = []
        if drive is not None:
            emulator_support.installed(work / "card" / "odrig", drive)
            options = ["--drive", work / "card"]
        emulator = entered(self, emulator_support.Emulator(folder, *options))
        return emulator, f"127.0.0.1:{emulator.port}"

    def test_an_unavailable_animation_is_grayed_with_its_reason_and_cannot_be_played(self):
        emulator, address = self.started()
        found = support.run("unavailable", address=address, settings={"rows": 3, "unavailable": 2})
        rows = {row["id"]: row for row in found.seen}
        self.assertEqual([(row["unavailable"], row["disabled"]) for row in found.seen], [(False, False), (True, True), (True, True)])
        self.assertIn("Unavailable: the file is damaged (bad-magic)", rows[2]["text"])
        self.assertIn("Unavailable: the file is missing (file-missing)", rows[3]["text"])
        self.assertLess(rows[2]["opacity"], 1)
        self.assertEqual(rows[1]["opacity"], 1)
        # The usable animation plays, and the unavailable one is refused by the installation.
        self.assertEqual(emulator.command("play 1"), b'{"ok":true}\n')
        self.assertEqual(emulator.command("play 2"), b'{"ok":false,"error":"unavailable"}\n')

    def test_a_file_of_the_card_left_out_is_grayed_and_says_where_it_is_mended(self):
        emulator, address = self.started({"good.odrg": clip(5), "zz.odrg": clip(6)[:-3]})
        found = support.run("unavailable", address=address, settings={"rows": 5, "unavailable": 3})
        rows = {row["id"]: row for row in found.seen}
        self.assertEqual(sorted(rows), [1, 2, 3, 60001, 60002])
        self.assertFalse(rows[60001]["unavailable"])
        self.assertTrue(rows[60002]["disabled"])
        self.assertIn("Unavailable: the file is damaged (truncated)", rows[60002]["text"])
        self.assertIn("Fix it on a computer: the card is read-only here.", rows[60002]["text"])
        self.assertNotIn("Fix it on a computer", rows[2]["text"])


if __name__ == "__main__":
    unittest.main()

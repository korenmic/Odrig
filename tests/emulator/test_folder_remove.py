"""`folder remove` on the emulator: an empty folder of the board's own storage and of the card
removed over each transport and with the command tool, its folder gone from the disk."""

import json
import pathlib
import tempfile
import unittest

from odrig import catalog

from . import support
from .test_content import ROUTES
from .test_internal_folders import wait_for


def clip(seed):
    return support.core_support.clip(seed, 60, 6)


def paths(card):
    return [folder.path for folder in catalog.read(catalog.Storage(card, drive=True)).index.folders]


class OnTheEmulator(unittest.TestCase):
    def started(self, files):
        top = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        card = top / "odrig"
        for name, data in files.items():
            path = card.joinpath(*name.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        _, refused = catalog.rebuild(catalog.Storage(card, drive=True), names=sorted(files), canvas=(60, 6))
        self.assertEqual(refused, [])
        folder = pathlib.Path(support.entered(self, support.example_show()))
        emulator = support.entered(self, support.Emulator(folder, "--drive", top))
        wait_for(lambda: json.loads(emulator.command("catalog")), lambda reply: reply.get("external", {}).get("state") == "ok")
        return card, folder, emulator

    def test_empty_folders_of_both_storages_are_removed_over_each_transport(self):
        card, folder, emulator = self.started({"night/old.odrg": clip(1)})
        for route, ask in ROUTES.items():
            with self.subTest(route=route):
                inside = json.loads(emulator.command("folder make internal shows"))
                outside = json.loads(emulator.command("folder make external clocks"))
                self.assertTrue(inside["made"] and outside["made"], (inside, outside))
                number = (folder / "folders.txt").read_text(encoding="ascii").splitlines()[1].split(" ")[0]
                self.assertTrue((folder / number).is_dir())
                self.assertTrue((card / "clocks").is_dir())
                self.assertEqual(json.loads(ask(emulator, f"folder remove {inside['id']}")), {"ok": True})
                self.assertEqual(json.loads(ask(emulator, f"folder remove {outside['id']}")), {"ok": True})
                self.assertFalse((folder / number).exists())
                self.assertFalse((card / "clocks").exists())
                self.assertEqual((folder / "folders.txt").read_text(encoding="ascii").splitlines()[1:], [])
                self.assertEqual(paths(card), ["", "night"])
                self.assertEqual(json.loads(ask(emulator, f"folder remove {outside['id']}")), {"ok": False, "error": "unknown-id"})
        night = next(item["id"] for item in json.loads(emulator.command("list"))["items"] if item.get("playlist") == "night")
        self.assertEqual(json.loads(emulator.command(f"folder remove {night}")), {"ok": False, "error": "in-use"})
        self.assertTrue((card / "night" / "old.odrg").exists())

    def test_a_folder_on_the_card_that_holds_another_file_stays_on_the_disk(self):
        card, _, emulator = self.started({"night/old.odrg": clip(1)})
        made = json.loads(emulator.command("folder make external clocks"))
        (card / "clocks" / "notes.txt").write_bytes(b"notes")
        self.assertEqual(json.loads(emulator.command(f"folder remove {made['id']}")), {"ok": True})
        self.assertTrue((card / "clocks" / "notes.txt").exists())
        self.assertEqual(paths(card), ["", "night"])

    def test_the_command_tool_sends_a_removal_and_refuses_another_form(self):
        _, folder, emulator = self.started({"night/old.odrg": clip(1)})
        made = json.loads(emulator.command("folder make internal my shows".replace(" shows", "%20shows")))
        target = ["--http", f"127.0.0.1:{emulator.port}", "--timeout", "10"]
        sent = support.run_tool(*target, "folder", "remove", made["id"])
        self.assertEqual(sent.status, 0, sent.err)
        self.assertEqual(json.loads(sent.out), {"ok": True})
        self.assertFalse((folder / "1").exists())
        for wrong in (("folder", "remove"), ("folder", "remove", "1", "2"), ("folder", "remove", "1\n2"), ("folder", "drop", "1")):
            result = support.run_tool(*target, *wrong)
            self.assertEqual(result.status, 2, wrong)
            self.assertIn("usage:", result.err)


if __name__ == "__main__":
    unittest.main()

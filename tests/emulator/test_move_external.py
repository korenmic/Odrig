"""`move external` on the emulator: a file of the card moved into another of its folders over
each transport and with the command tool, keeping its id and its saved settings, with the
journal and the folder the move made left as the board leaves them."""

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


def ids(card):
    index = catalog.read(catalog.Storage(card, drive=True)).index
    return {entry.name: file_id for folder in index.folders for file_id, entry in folder.rows}


class OnTheEmulator(unittest.TestCase):
    def card(self, files):
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

    def test_a_file_is_moved_over_each_transport_with_its_id_and_its_saved_brightness(self):
        card, folder, emulator = self.card({"night/deep/old.odrg": clip(1), "space room/near.odrg": clip(2), "clocks/a.odrg": clip(3)})
        moved = ids(card)["space room/near.odrg"]
        self.assertEqual(json.loads(emulator.command(f"brightness {moved} 9 save")), {"ok": True})
        destinations = iter((("night/deep", "night/deep/near.odrg"), ("/", "near.odrg")))
        for route, ask in ROUTES.items():
            with self.subTest(route=route):
                destination, path = next(destinations)
                reply = json.loads(ask(emulator, f"move external {moved} {destination}"))
                self.assertEqual(reply, {"ok": True, "id": moved, "moved": True})
                self.assertEqual(ids(card)[path], moved)
                self.assertEqual(card.joinpath(*path.split("/")).read_bytes(), clip(2))
                self.assertEqual(json.loads(ask(emulator, f"move external {moved} {destination}")), {"ok": True, "id": moved, "moved": False})
                self.assertEqual(json.loads(emulator.command(f"saved {moved}"))["brightness"], 9)
                self.assertIn(f"9 x {path}\n", (folder / "brightness.txt").read_text(encoding="ascii"))
        self.assertFalse((card / "moving.txt").exists())
        self.assertTrue((card / "space room").is_dir())
        self.assertEqual(catalog.read(catalog.Storage(card, drive=True)).state, "ok")

    def test_the_command_tool_sends_a_move_and_refuses_another_form(self):
        card, _, emulator = self.card({"night/old songs/a b.odrg": clip(1), "night/old songs/c.odrg": clip(3), "clocks/x.odrg": clip(2)})
        moved = ids(card)["night/old songs/a b.odrg"]
        target = ["--http", f"127.0.0.1:{emulator.port}", "--timeout", "10"]
        sent = support.run_tool(*target, "move", "external", moved, "clocks")
        self.assertEqual(sent.status, 0, sent.err)
        self.assertEqual(json.loads(sent.out), {"ok": True, "id": moved, "moved": True})
        self.assertEqual(ids(card)["clocks/a b.odrg"], moved)
        back = support.run_tool(*target, "move", "external", moved, "night/old songs")
        self.assertEqual(json.loads(back.out), {"ok": True, "id": moved, "moved": True})
        self.assertEqual(ids(card)["night/old songs/a b.odrg"], moved)
        root = support.run_tool(*target, "move", "external", moved, "/")
        self.assertEqual(json.loads(root.out), {"ok": True, "id": moved, "moved": True})
        for wrong in (("move", "external", moved), ("move", "internal", moved, "/"), ("move", "external", moved, "a\nb")):
            self.assertEqual(support.run_tool(*target, *wrong).status, 2, wrong)


if __name__ == "__main__":
    unittest.main()

"""`move internal` on the emulator: a folder of the board's own storage moved and renamed over
each transport and with the command tool, its numbered folders and files where they were."""

import json
import pathlib
import unittest

from . import support
from .test_content import ROUTES


class OnTheEmulator(unittest.TestCase):
    def test_a_folder_is_moved_and_renamed_over_each_transport(self):
        folder = pathlib.Path(support.entered(self, support.example_show()))
        emulator = support.entered(self, support.Emulator(folder))
        made = [json.loads(emulator.command(f"folder make internal {path}")) for path in ("art", "shows", "shows/night")]
        self.assertTrue(all(answer["made"] for answer in made), made)
        art, shows, night = (answer["id"] for answer in made)
        before = sorted(path.name for path in folder.iterdir() if path.is_dir())
        lines = iter((f"move internal {night} art/night", f"move internal {night} art/evening"))
        texts = iter(("art/night", "art/evening"))
        for route, ask in ROUTES.items():
            with self.subTest(route=route):
                self.assertEqual(json.loads(ask(emulator, next(lines))), {"ok": True, "id": night, "moved": True})
                self.assertIn(f" {night} 0 {next(texts)}\n", (folder / "folders.txt").read_text(encoding="ascii"))
        self.assertEqual(json.loads(emulator.command(f"move internal {night} art/evening")), {"ok": True, "id": night, "moved": False})
        self.assertEqual(json.loads(emulator.command(f"move internal {night} shows")), {"ok": False, "error": "in-use"})
        self.assertEqual(json.loads(emulator.command(f"move internal {shows} shows/x")), {"ok": False, "error": "bad-argument"})
        self.assertEqual(sorted(path.name for path in folder.iterdir() if path.is_dir()), before)
        listed = json.loads(emulator.command(f"list in {art}"))
        self.assertEqual([item["playlist"] for item in listed["items"]], ["art/evening"])

    def test_the_command_tool_sends_a_move_with_each_name_escaped_and_refuses_another_form(self):
        folder = pathlib.Path(support.entered(self, support.example_show()))
        emulator = support.entered(self, support.Emulator(folder))
        made = json.loads(emulator.command("folder make internal my%20shows"))
        target = ["--http", f"127.0.0.1:{emulator.port}", "--timeout", "10"]
        sent = support.run_tool(*target, "move", "internal", made["id"], "old shows")
        self.assertEqual(sent.status, 0, sent.err)
        self.assertEqual(json.loads(sent.out), {"ok": True, "id": made["id"], "moved": True})
        self.assertIn(f" {made['id']} 0 old shows\n", (folder / "folders.txt").read_text(encoding="ascii"))
        for wrong in (("move", "internal", made["id"]), ("move", "internal", made["id"], "/"), ("move", "internal", made["id"], "a\nb"),
                      ("move", "sideways", made["id"], "x")):
            result = support.run_tool(*target, *wrong)
            self.assertEqual(result.status, 2, wrong)
            self.assertIn("usage:", result.err)


if __name__ == "__main__":
    unittest.main()

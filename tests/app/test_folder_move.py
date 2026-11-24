"""`Rename…` and `Move to…` of a folder of the board's own storage in the shared app: the menu
on both storages, the rename dialog and its checks, the chooser of one folder's move with the
destinations it disables and why, a selected folder moved inside the board's storage by the
same command, a refusal, a firmware without the command and a reply that did not arrive."""

import json
import pathlib
import tempfile
import threading
import unittest

from odrig import catalog

from tests.core import support as core_support
from tests.emulator import support as emulator_support
from . import support
from .test_target import entered

# Folders of the board's own storage, in the tree's order: `empty` holds nothing, `parent`
# holds only `parent/child`, and `shows` holds `1/face.odrg` and `shows/night`, which holds
# `2/deep.odrg`.
FOLDERS = "odrig-folders 1 6\n3 22 0 empty\n4 23 0 parent\n5 24 0 parent/child\n1 20 0 shows\n2 21 0 shows/night\n"


def clip(seed):
    return core_support.clip(seed, 60, 6, durations=(20,) * 3, compressed=False)


class FolderMoves(unittest.TestCase):
    def board(self):
        folder = emulator_support.installed(pathlib.Path(entered(self, tempfile.TemporaryDirectory()), "show"), {
            "mapping.json": core_support.mapping_texts()["legs-2"],
            "show.json": json.dumps({"version": 1, "brightness": 32, "items": [
                {"id": 1, "file": "root.odrg"}, {"id": 2, "file": "1/face.odrg"}, {"id": 3, "file": "2/deep.odrg"}]}),
            "folders.txt": FOLDERS,
            "root.odrg": clip(1),
        })
        for name, seed in (("1/face.odrg", 2), ("2/deep.odrg", 3)):
            path = folder.joinpath(*name.split("/"))
            path.parent.mkdir()
            path.write_bytes(clip(seed))
        for number in ("3", "4", "5"):
            (folder / number).mkdir()
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        card = top / "odrig"
        (card / "night").mkdir(parents=True)
        (card / "night" / "old.odrg").write_bytes(clip(4))
        _, refused = catalog.rebuild(catalog.Storage(card, drive=True), names=["night/old.odrg"], canvas=(60, 6))
        self.assertEqual(refused, [])
        emulator = entered(self, emulator_support.Emulator(folder, "--drive", top))
        for _ in range(200):
            if json.loads(emulator.command("catalog")).get("external", {}).get("state") == "ok":
                break
            threading.Event().wait(0.05)
        return folder, emulator

    def forwarding(self, emulator, answer=None):
        lock = threading.Lock()
        sent = []

        def reply(line):
            text = line.decode("ascii")
            if text.startswith("move internal ") and answer is not None:
                sent.append(text)
                given = answer(len(sent), text)
                if given != "forward":
                    return given
            with lock:
                return 200, emulator.command(text)

        return entered(self, support.StandIn(reply))

    def test_rename_move_to_and_a_selected_folder_moved_inside_the_boards_storage(self):
        folder, emulator = self.board()
        stand_in = self.forwarding(emulator)
        settings = {"rows": 1, "folders": ["empty", "parent", "shows", "night"], "acts": [
            {"kind": "rename", "path": "empty", "names": ["Shows", "fresh"], "gone": True},
            {"kind": "move", "path": "shows", "to": "parent", "gone": True},
            {"kind": "selected", "path": "fresh", "to": "parent", "gone": True},
        ]}
        found = support.run("folder-move", address=stand_in.address, settings=settings).seen
        for path in ("empty", "parent", "shows"):
            self.assertIn("Rename…", found["menus"][path], path)
            self.assertIn("Move to…", found["menus"][path], path)
        self.assertNotIn("Rename…", found["menus"]["night"])
        self.assertNotIn("Move to…", found["menus"]["night"])
        renamed, moved, selected = found["acts"]
        self.assertEqual((renamed["title"], renamed["where"], renamed["field"]), ("Rename folder", "In Internal /", "empty"))
        self.assertEqual(renamed["path Shows"], "New path: Internal /Shows")
        self.assertEqual(renamed["problem Shows"], "A folder there has that name.")
        self.assertEqual(renamed["message"], "Renamed the folder Internal /empty to Internal /fresh.")
        self.assertIn("fresh", renamed["rows"])
        self.assertEqual(moved["storages"], ["external (disabled)", "internal"])
        self.assertEqual(moved["choices"], ["/ — It is there already. (disabled)", "/fresh", "/parent",
                                            "/parent/child — It would pass 3 levels or 93 characters there. (disabled)"])
        self.assertIn("Folder Internal /shows/ → Internal /parent/shows/", moved["preview"])
        self.assertEqual(moved["message"], "Moved the folder Internal /shows/ to Internal /parent/shows/.")
        self.assertIn("Folder Internal /fresh/ → Internal /parent/fresh/", selected["preview"])
        self.assertIn("Internal /fresh/ is now Internal /parent/fresh/.", selected["message"])
        sent = [line.decode("ascii") for _, line in stand_in.lines if line.startswith(b"move internal")]
        self.assertEqual(sent, ["move internal 22 fresh", "move internal 20 parent/shows", "move internal 22 parent/fresh"])
        self.assertEqual((folder / "folders.txt").read_text(encoding="ascii"),
                         "odrig-folders 1 6\n4 23 0 parent\n5 24 0 parent/child\n3 22 0 parent/fresh\n1 20 0 parent/shows\n2 21 0 parent/shows/night\n")
        self.assertEqual((folder / "1" / "face.odrg").read_bytes(), clip(2))
        self.assertEqual((folder / "2" / "deep.odrg").read_bytes(), clip(3))

    def test_a_refusal_an_older_firmware_and_a_reply_that_did_not_arrive(self):
        folder, emulator = self.board()

        def answer(count, line):
            if count == 3:
                emulator.command(line)
                return None
            return {1: (200, '{"ok":false,"error":"bad-argument"}'), 2: (200, '{"ok":false,"error":"unknown-command"}')}[count]

        stand_in = self.forwarding(emulator, answer)
        settings = {"rows": 1, "folders": ["empty"], "acts": [
            {"kind": "rename", "path": "empty", "names": ["a"], "gone": False},
            {"kind": "rename", "path": "empty", "names": ["b"], "gone": False},
            {"kind": "rename", "path": "empty", "names": ["c"], "gone": True},
        ]}
        found = support.run("folder-move", address=stand_in.address, settings=settings).seen
        refused, older, lost = (act["message"] for act in found["acts"])
        self.assertEqual(refused, "The folder Internal /empty was not renamed. A folder or an animation inside would pass the limits of 3 levels or 100 bytes. (bad-argument)")
        self.assertEqual(older, "The folder Internal /empty was not renamed. This installation's firmware cannot move folders inside its storage. Install the newer firmware.")
        self.assertEqual(lost, "No confirmed reply. The folder is at Internal /c now.")
        sent = [line.decode("ascii") for _, line in stand_in.lines if line.startswith(b"move internal")]
        self.assertEqual(sent, ["move internal 22 a", "move internal 22 b", "move internal 22 c"])
        self.assertIn("3 22 0 c\n", (folder / "folders.txt").read_text(encoding="ascii"))


if __name__ == "__main__":
    unittest.main()

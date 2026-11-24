"""`Remove folder` in the shared app: the menu of a folder's row on both storages and on a card
the board may not write, the check of the folder's level, the question with `Cancel`, Escape
and `Remove`, the removal, a refusal, a firmware without the command, and a reply that did not
arrive, with the board's own storage and the card on the emulator."""

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

# Folders of the board's own storage, in the tree's order: `empty` and `parent/child` hold
# nothing, `parent` holds only `parent/child`, and `shows` holds `1/face.odrg`.
FOLDERS = "odrig-folders 1 6\n3 22 0 empty\n4 23 0 parent\n5 24 0 parent/child\n1 20 0 shows\n2 21 0 shows/night\n"


def clip(seed):
    return core_support.clip(seed, 60, 6, durations=(20,) * 3, compressed=False)


class RemoveFolder(unittest.TestCase):
    def board(self, read_only=False):
        """A board with FOLDERS, `root.odrg` at the root and `1/face.odrg`, `2/deep.odrg` in
        its first two folders, and a card with `night/old.odrg` and an empty `clocks`."""
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
        writable = entered(self, emulator_support.Emulator(folder, "--drive", top))
        self.wait(writable)
        self.assertTrue(json.loads(writable.command("folder make external clocks"))["made"])
        if read_only:
            writable.stop()
            emulator = entered(self, emulator_support.Emulator(folder, "--drive", top, "--drive-read-only"))
            self.wait(emulator)
        else:
            emulator = writable
        return folder, card, emulator

    def wait(self, emulator):
        for _ in range(200):
            if json.loads(emulator.command("catalog")).get("external", {}).get("state") == "ok":
                return
            threading.Event().wait(0.05)
        raise AssertionError("the card's catalog was never read")

    def forwarding(self, emulator, answer=None):
        """A target that hands each line to the emulator, but for `folder remove`, whose reply
        `answer` gives, by the number of the line among those sent, when it is given."""
        lock = threading.Lock()
        sent = []

        def reply(line):
            text = line.decode("ascii")
            if text.startswith("folder remove ") and answer is not None:
                sent.append(text)
                given = answer(len(sent), text)
                if given != "forward":
                    return given
            with lock:
                return 200, emulator.command(text)

        return entered(self, support.StandIn(reply))

    def test_the_menu_the_check_the_question_and_the_removal_on_both_storages(self):
        folder, card, emulator = self.board()
        stand_in = self.forwarding(emulator)
        settings = {"rows": 1, "folders": ["empty", "parent", "shows", "clocks", "night"], "acts": [
            {"path": "parent", "answer": "remove", "gone": False},
            {"path": "empty", "answer": "cancel"},
            {"path": "empty", "answer": "escape"},
            {"path": "empty", "answer": "remove", "gone": True},
            {"path": "clocks", "answer": "remove", "gone": True},
        ]}
        found = support.run("folder-remove", address=stand_in.address, settings=settings).seen
        menus = found["menus"]
        for path in ("empty", "parent", "clocks"):
            self.assertIn("Remove folder", menus[path], path)
        for path in ("shows", "night"):
            self.assertIn("Remove folder (disabled)", menus[path], path)
            self.assertIn("Only an empty folder can be removed.", menus[path], path)
        not_empty, cancelled, escaped, removed, removed_card = found["acts"]
        self.assertNotIn("question", not_empty)
        self.assertEqual(not_empty["message"], "The folder Internal /parent is not empty: only an empty folder can be removed.")
        self.assertIn("parent", not_empty["rows"])
        for asked in (cancelled, escaped):
            self.assertEqual(asked["question"], "Remove the empty folder Internal /empty? This cannot be undone.")
            self.assertTrue(asked["closed"])
        self.assertEqual(removed["question"], "Remove the empty folder Internal /empty? This cannot be undone.")
        self.assertEqual(removed["message"], "Removed the folder Internal /empty.")
        self.assertNotIn("empty", removed["rows"])
        self.assertEqual(removed_card["question"], "Remove the empty folder External /clocks? This cannot be undone.")
        self.assertEqual(removed_card["message"], "Removed the folder External /clocks.")
        sent = [line.decode("ascii") for _, line in stand_in.lines if line.startswith(b"folder remove")]
        self.assertEqual(sent, ["folder remove 22", sent[1]])
        self.assertGreater(int(sent[1].split(" ")[2]), 60000)
        self.assertNotIn(" empty\n", (folder / "folders.txt").read_text(encoding="ascii"))
        self.assertFalse((folder / "3").exists())
        self.assertFalse((card / "clocks").exists())
        self.assertNotIn("clocks", [each.path for each in catalog.read(catalog.Storage(card, drive=True)).index.folders])

    def test_a_refusal_an_older_firmware_and_a_reply_that_did_not_arrive(self):
        folder, _, emulator = self.board()

        def answer(count, line):
            # The first two are refused; the third is lost before the board has it, and the
            # fourth after the board removed the folder.
            if count == 4:
                emulator.command(line)
                return None
            return {1: (200, '{"ok":false,"error":"busy"}'), 2: (200, '{"ok":false,"error":"unknown-command"}'), 3: None}.get(count, "forward")

        stand_in = self.forwarding(emulator, answer)
        settings = {"rows": 1, "folders": ["empty"], "acts": [
            {"path": "empty", "answer": "remove", "gone": False},
            {"path": "empty", "answer": "remove", "gone": False},
            {"path": "empty", "answer": "remove", "gone": False},
            {"path": "empty", "answer": "remove", "gone": True},
        ]}
        found = support.run("folder-remove", address=stand_in.address, settings=settings).seen
        busy, older, kept, gone = (act["message"] for act in found["acts"])
        self.assertEqual(busy, "The folder Internal /empty was not removed. The installation is busy. Try again in a moment. (busy)")
        self.assertEqual(older, "The folder Internal /empty was not removed. This installation's firmware cannot remove folders. Install the newer firmware.")
        self.assertEqual(kept, "No confirmed reply. The folder Internal /empty is still there; press Remove folder again to remove it.")
        self.assertEqual(gone, "No confirmed reply. The folder Internal /empty was removed.")
        sent = [line.decode("ascii") for _, line in stand_in.lines if line.startswith(b"folder remove")]
        self.assertEqual(sent, ["folder remove 22"] * 4)
        self.assertNotIn(" empty\n", (folder / "folders.txt").read_text(encoding="ascii"))

    def test_a_card_the_board_may_not_write_says_why_and_offers_no_removal(self):
        _, card, emulator = self.board(read_only=True)
        found = support.run("folder-remove", address=f"127.0.0.1:{emulator.port}", settings={"rows": 1, "folders": ["clocks", "night", "empty"], "acts": []}).seen
        for path in ("clocks", "night"):
            self.assertNotIn("Remove folder", found["menus"][path], path)
            self.assertNotIn("Remove folder (disabled)", found["menus"][path], path)
            self.assertIn("External storage is read-only: this folder cannot be removed.", found["menus"][path], path)
        self.assertIn("Remove folder", found["menus"]["empty"])
        self.assertTrue((card / "clocks").is_dir())


if __name__ == "__main__":
    unittest.main()

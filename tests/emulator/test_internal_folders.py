"""The numbered folders of the emulator's storage: the names the core gives files in them, the
folders it makes and removes, the space they take, and the commands of internal folders over
the emulator's transports."""

import base64
import json
import pathlib
import tempfile
import time
import unittest
import zlib

from emulator import host
from tests.core.support import BOARD_STORAGE, STORAGE_BLOCK

from . import support
from .test_content import ROUTES


class TheHost(unittest.TestCase):
    def setUp(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        self.folder = pathlib.Path(made.name)

    def test_a_stored_name_is_a_file_of_a_numbered_folder(self):
        made = host.FolderHost(self.folder)
        self.assertEqual(made.make_folder("12"), 1)
        self.assertEqual(made.make_folder("12"), 1)
        self.assertTrue((self.folder / "12").is_dir())
        self.assertEqual(made.write_open("12/a.odrg"), 1)
        self.assertEqual(made.write(b"abc"), 1)
        self.assertEqual(made.write_close(), 1)
        self.assertEqual((self.folder / "12" / "a.odrg").read_bytes(), b"abc")
        self.assertEqual(made.open("12/a.odrg"), 1)
        made.close()
        for name in ("0/a.odrg", "012/a.odrg", "256/a.odrg", "a/b.odrg", "12/A.odrg", "12/x/a.odrg", "/a.odrg", "12/"):
            self.assertEqual(made.write_open(name), -1, name)
            self.assertEqual(made.open(name), -1, name)
        for name in ("0", "256", "012", "a", "1a"):
            self.assertEqual(made.make_folder(name), -1, name)

    def test_a_numbered_folder_is_removed_only_while_it_is_empty(self):
        made = host.FolderHost(self.folder)
        made.make_folder("3")
        (self.folder / "3" / "a.odrg").write_bytes(b"a")
        self.assertEqual(made.remove("3"), -1)
        self.assertEqual(made.remove("3/a.odrg"), 1)
        self.assertEqual(made.remove("3"), 1)
        self.assertEqual(made.remove("3"), 0)
        self.assertFalse((self.folder / "3").exists())

    def test_a_numbered_folder_takes_two_blocks_and_its_files_count(self):
        made = host.FolderHost(self.folder)
        (self.folder / "a.odrg").write_bytes(bytes(10))
        before = made.space()[0]
        made.make_folder("7")
        (self.folder / "7" / "b.odrg").write_bytes(bytes(STORAGE_BLOCK + 1))
        (self.folder / "other").mkdir()
        self.assertEqual(made.space(), (before - 2 * STORAGE_BLOCK - 2 * STORAGE_BLOCK, BOARD_STORAGE))


def clip():
    return support.core_support.clip(3, 60, 6)


def wait_for(ask, done, seconds=10):
    """Asks until the answer is done, or the time is up: the last answer."""
    end = time.monotonic() + seconds
    while True:
        answer = ask()
        if done(answer) or time.monotonic() > end:
            return answer
        time.sleep(0.05)


class OverTheTransports(unittest.TestCase):
    def setUp(self):
        self.folder = pathlib.Path(support.entered(self, support.example_show()))

    def test_a_folder_is_made_filled_listed_and_played(self):
        # The card's host keeps the current playlist, an internal folder's too.
        top = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        emulator = support.entered(self, support.Emulator(self.folder, "--drive", top))
        data = clip()
        for route, ask in ROUTES.items():
            with self.subTest(route=route):
                made = json.loads(ask(emulator, "folder make internal shows"))
                self.assertTrue(made["ok"], made)
        self.assertTrue((self.folder / "1").is_dir())
        self.assertEqual((self.folder / "folders.txt").read_text(encoding="ascii"), f"odrig-folders 1 2\n1 {made['id']} 0 shows\n")
        lines = [f"upload begin 9 shows/x.odrg {len(data)}"]
        lines += [f"upload data {offset} {base64.urlsafe_b64encode(data[offset:offset + 1500]).rstrip(b'=').decode('ascii')}" for offset in range(0, len(data), 1500)]
        for line in lines:
            self.assertTrue(json.loads(emulator.command(line))["ok"], line)
        ended = wait_for(lambda: json.loads(emulator.command(f"upload end {zlib.crc32(data):08x}")), lambda reply: reply != {"ok": False, "error": "busy"})
        self.assertEqual(ended, {"ok": True})
        self.assertEqual((self.folder / "1" / "x.odrg").read_bytes(), data)
        listed = json.loads(emulator.command(f"list in {made['id']}"))
        self.assertEqual([(item["id"], item["file"], item["stored"]) for item in listed["items"]], [(9, "shows/x.odrg", "1/x.odrg")])
        root = json.loads(emulator.command("list"))
        self.assertIn({"id": made["id"], "playlist": "shows", "external": False, "files": 1, "ignored": False, "inherited_ignored": False}, root["items"])
        self.assertEqual(json.loads(emulator.command(f"play {made['id']}")), {"ok": True})
        status = wait_for(lambda: json.loads(emulator.command("status")), lambda reply: reply["animation"] == 9)
        self.assertEqual((status["playing"], status["playlist"], status["file"]), (made["id"], "shows", "shows/x.odrg"))
        self.assertEqual(json.loads(emulator.command("remove 9")), {"ok": True})
        self.assertFalse((self.folder / "1").exists())
        self.assertEqual((self.folder / "folders.txt").read_text(encoding="ascii"), "odrig-folders 1 2\n")


class TheCommandTool(unittest.TestCase):
    def test_it_makes_an_internal_folder_and_uploads_a_file_into_it(self):
        folder = pathlib.Path(support.entered(self, support.example_show()))
        emulator = support.entered(self, support.Emulator(folder))
        target = ["--http", f"127.0.0.1:{emulator.port}", "--timeout", "10"]
        made = support.run_tool(*target, "folder", "make", "internal", "my shows")
        self.assertEqual(made.status, 0, made.err)
        self.assertTrue(json.loads(made.out)["made"])
        with tempfile.TemporaryDirectory() as holder:
            path = pathlib.Path(holder, "x.odrg")
            path.write_bytes(clip())
            sent = support.run_tool(*target, "--folder", "my shows", "upload", "9", path)
        self.assertEqual(sent.status, 0, sent.err)
        self.assertEqual((folder / "1" / "x.odrg").read_bytes(), clip())
        self.assertEqual(support.run_tool(*target, "--folder", "a", "status").status, 2)
        self.assertEqual(support.run_tool(*target, "--folder", "a", "--external", "upload", path).status, 2)


if __name__ == "__main__":
    unittest.main()

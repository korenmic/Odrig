"""The catalogs through the emulator and the command tool: `catalog`, `catalog rebuild`,
`upload --external` by each transport, and a card that the emulator wrote read by the PC
tool, and one that the PC tool wrote read by the emulator."""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from odrig import catalog
from tests.converter.test_catalog_format import animation
from tests.core import support as core_support

from . import support

# The emulator reads a card's marker again once in 10 seconds.
WAIT_SECONDS = 20


def pc_tool(*arguments):
    """Runs `python -m odrig.catalog` and returns what it did."""
    return subprocess.run([sys.executable, "-m", "odrig.catalog", *map(str, arguments)], cwd=support.ROOT, capture_output=True, text=True)


class WithACard(unittest.TestCase):
    """A show of one animation on the installation's canvas, and a card of one animation
    that the PC tool imported."""

    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.show = support.installed(self.work / "show", {
            "mapping.json": core_support.one_leg_mapping(60, 60),
            "show.json": json.dumps({"version": 1, "brightness": 128, "items": [{"id": 1, "file": "one.odrg"}]}),
            "one.odrg": animation(1),
        })
        self.top = self.work / "card"
        support.installed(self.top / "odrig", {"sun.odrg": animation(2)})

    def start(self, *options):
        return support.entered(self, support.Emulator(self.show, "--drive", self.top, *options))

    def catalog_when(self, emulator, condition):
        """The reply of `catalog` once it meets a condition, which the test waits for."""
        deadline = time.monotonic() + WAIT_SECONDS
        while True:
            reply = json.loads(emulator.command("catalog"))
            if condition(reply) or time.monotonic() > deadline:
                return reply
            time.sleep(0.1)

    def checked(self, emulator):
        """Waits until the start's check is over, the drive's catalog read with it, during
        which `catalog rebuild` answers `busy`."""
        deadline = time.monotonic() + WAIT_SECONDS
        while json.loads(emulator.command("status"))["checking"] is not None:
            self.assertLess(time.monotonic(), deadline, "the start's check did not end")
            time.sleep(0.05)

    def card_files(self):
        return {name: path.read_bytes() for name, path in ((path.name, path) for path in (self.top / "odrig").iterdir())}

    def targets(self, emulator):
        return {support.LINES: support.line_target(emulator), "http": ("--http", f"127.0.0.1:{emulator.port}")}


class ABigCard(WithACard):
    def test_a_card_of_300_files_in_40_folders_that_the_pc_tool_imported_is_read_from_its_index(self):
        clip = animation(1)
        folders = [path for top in range(13) for path in (f"t{top:02d}", f"t{top:02d}/a", f"t{top:02d}/b")] + ["t00/a/deep"]
        shutil.rmtree(self.top / "odrig")
        root = support.installed(self.top / "odrig", {f"r{number:02d}.odrg": clip for number in range(20)})
        for folder in folders:
            support.installed(root.joinpath(*folder.split("/")), {f"c{number}.odrg": clip for number in range(7)})
        imported = pc_tool(self.top, "import")
        self.assertEqual(imported.returncode, 0, imported.stderr)
        emulator = self.start()
        self.assertEqual(self.catalog_when(emulator, lambda reply: reply["external"]["state"] == "ok")["external"]["entries"], 300)
        items = []
        reply = {"next": 0}
        while reply["next"] is not None:
            reply = json.loads(emulator.command(f"list {reply['next']}"))
            items += [(item["id"], item.get("file")) for item in reply["items"] if item["id"] > 60000]
        # The root's level: its 13 folders, `t00` the table's first and each other after the
        # three lines of the one before, then its 20 files.
        self.assertEqual(items, [(60301, None)] + [(60302 + 3 * top, None) for top in range(1, 13)] + [(60001 + number, f"r{number:02d}.odrg") for number in range(20)])
        last = [(item["id"], item["file"]) for item in json.loads(emulator.command("list in 60340"))["items"]]
        self.assertEqual(last, [(60294 + number, f"t12/b/c{number}.odrg") for number in range(7)])
        self.assertEqual(json.loads(emulator.command("play 60300")), {"ok": True})
        status = emulator.status()
        self.assertEqual((status["animation"], status["file"]), (60300, "t12/b/c6.odrg"))
        # A removal through the emulator keeps the catalog and the index as the PC tool reads
        # them.
        self.assertEqual(json.loads(emulator.command("remove 60010")), {"ok": True})
        checked = pc_tool(self.top, "check")
        self.assertEqual((checked.returncode, checked.stdout.strip().splitlines()[-1]), (0, "checked: 299 entries, 0 differ"))
        self.assertNotIn("r09.odrg", [path.name for path in root.iterdir()])

    def test_a_card_that_is_read_only_lists_it_and_takes_no_removal(self):
        support.installed(self.top / "odrig" / "night", {f"c{number}.odrg": animation(1) for number in range(3)})
        self.assertEqual(pc_tool(self.top, "import").returncode, 0)
        emulator = self.start("--drive-read-only")
        self.catalog_when(emulator, lambda reply: reply["external"]["state"] == "ok")
        night = [(item["id"], item["file"]) for item in json.loads(emulator.command("list in 60005"))["items"]]
        self.assertEqual(night, [(60002, "night/c0.odrg"), (60003, "night/c1.odrg"), (60004, "night/c2.odrg")])
        self.assertEqual(json.loads(emulator.command("remove 60002")), {"ok": False, "error": "in-use"})


class Commands(WithACard):
    def test_catalog_prints_the_reply_by_each_transport(self):
        self.assertEqual(pc_tool(self.top, "import").returncode, 0)
        emulator = self.start()
        wanted = self.catalog_when(emulator, lambda reply: reply["external"]["state"] == "ok")
        for transport, target in self.targets(emulator).items():
            with self.subTest(transport=transport):
                result = support.run_tool(*target, "catalog")
                self.assertEqual((result.status, result.err), (0, ""))
                self.assertEqual(json.loads(result.out), wanted)
        self.assertEqual(wanted["external"], {"state": "ok", "generation": 1, "entries": 1, "writable": True})
        self.assertEqual(wanted["internal"]["state"], "none")

    def test_catalog_page_prints_the_pages_of_the_card_and_the_show_by_each_transport(self):
        self.assertEqual(pc_tool(self.top, "import").returncode, 0)
        # The show's own catalog, as `fw.py install-show` writes one.
        storage = catalog.MemoryStorage({path.name: path.read_bytes() for path in self.show.iterdir()})
        made, refused = catalog.rebuild(storage, names=["one.odrg"], canvas=(60, 60))
        self.assertEqual((made.state, refused), ("ok", []))
        for name, content in storage.files.items():
            (self.show / name).write_bytes(content)
        emulator = self.start()
        self.catalog_when(emulator, lambda reply: reply["external"]["state"] == "ok")
        card = {path.name: path.read_bytes() for path in (self.top / "odrig").iterdir()}
        for transport, target in self.targets(emulator).items():
            with self.subTest(transport=transport):
                for storage_name, held in (("external", card), ("internal", storage.files)):
                    page = next(number for number in range(16) if catalog.page_name(number) in held)
                    content = held[catalog.page_name(page)]
                    result = support.run_tool(*target, "catalog", "page", storage_name, str(page), "0")
                    self.assertEqual((result.status, result.err), (0, ""))
                    reply = json.loads(result.out)
                    self.assertEqual((reply["generation"], reply["text"].encode("ascii"), reply["next"]), (1, content, len(content)))
                    after = json.loads(support.run_tool(*target, "catalog", "page", storage_name, str(page), str(len(content))).out)
                    self.assertEqual(after, {"ok": True, "generation": 1, "text": "", "next": None})
        for wrong in (["page"], ["page", "both", "0", "0"], ["page", "internal", "0"], ["page", "internal", "a", "0"]):
            result = support.run_tool(*self.targets(emulator)["http"], "catalog", *wrong)
            self.assertEqual(result.status, 2, wrong)

    def test_uploads_to_the_card_by_each_transport_are_what_the_pc_tool_reads(self):
        self.assertEqual(pc_tool(self.top, "import").returncode, 0)
        emulator = self.start()
        self.catalog_when(emulator, lambda reply: reply["external"]["state"] == "ok")
        sent = {}
        for number, (transport, target) in enumerate(self.targets(emulator).items(), start=3):
            with self.subTest(transport=transport):
                path = self.work / f"clip-{number}.odrg"
                path.write_bytes(animation(number))
                sent[path.name] = path.read_bytes()
                result = support.run_tool(*target, "upload", "--external", path)
                self.assertEqual(result.status, 0, result.err)
                self.assertIn("upload: committed:", result.err)
                self.assertEqual(sorted(json.loads(result.out)), ["id", "ok"])
        files = self.card_files()
        for name, data in sent.items():
            self.assertEqual(files[name], data)
        checked = pc_tool(self.top, "check")
        self.assertEqual((checked.returncode, checked.stdout.strip().splitlines()[-1]), (0, "checked: 3 entries, 0 differ"))
        # The same uploads through the PC library on the card as it was leave the same files.
        storage = catalog.MemoryStorage({"sun.odrg": animation(2)}, drive=True)
        catalog.rebuild(storage)
        for name, data in sent.items():
            catalog.add(storage, name, data)
        self.assertEqual(files, storage.files)

    def test_a_card_that_is_read_only_takes_no_upload(self):
        self.assertEqual(pc_tool(self.top, "import").returncode, 0)
        emulator = self.start("--drive-read-only")
        self.catalog_when(emulator, lambda reply: reply["external"]["state"] == "ok")
        path = self.work / "clip.odrg"
        path.write_bytes(animation(3))
        result = support.run_tool("--http", f"127.0.0.1:{emulator.port}", "upload", "--external", path)
        self.assertEqual((result.status, json.loads(result.out)), (1, {"ok": False, "error": "read-only"}))
        self.assertNotIn("clip.odrg", self.card_files())

    def test_a_change_the_pc_tool_makes_is_taken_up_by_the_emulator(self):
        self.assertEqual(pc_tool(self.top, "import").returncode, 0)
        emulator = self.start()
        self.catalog_when(emulator, lambda reply: reply["external"]["state"] == "ok")
        path = self.work / "moon.odrg"
        path.write_bytes(animation(4))
        self.assertEqual(pc_tool(self.top, "add", path).returncode, 0)
        reply = self.catalog_when(emulator, lambda reply: reply["external"].get("generation") == 2 and reply["external"]["state"] == "ok")
        self.assertEqual(reply["external"]["entries"], 2)
        listed = [item["file"] for item in json.loads(emulator.command("list"))["items"] if item.get("external")]
        self.assertEqual(sorted(listed), ["moon.odrg", "sun.odrg"])

    def test_a_card_without_a_catalog_is_imported_through_the_emulator_as_the_pc_tool_imports_it(self):
        emulator = self.start()
        self.catalog_when(emulator, lambda reply: reply["external"]["state"] == "none")
        result = support.run_tool("--http", f"127.0.0.1:{emulator.port}", "catalog", "rebuild", "external")
        self.assertEqual((result.status, json.loads(result.out)), (0, {"ok": True}))
        self.catalog_when(emulator, lambda reply: reply["external"]["state"] == "ok" and reply["rebuild"] is None)
        copy = self.work / "copy"
        shutil.copytree(self.top, copy)
        for name in [name for name in self.card_files() if name.startswith(("catalog", "index-"))]:
            (copy / "odrig" / name).unlink()
        self.assertEqual(pc_tool(copy, "import").returncode, 0)
        self.assertEqual(self.card_files(), {path.name: path.read_bytes() for path in (copy / "odrig").iterdir()})

    def test_the_internal_catalog_is_rebuilt_through_the_emulator_as_the_pc_library_rebuilds_it(self):
        emulator = self.start()
        self.checked(emulator)
        result = support.run_tool(*support.line_target(emulator), "catalog", "rebuild", "internal")
        self.assertEqual((result.status, json.loads(result.out)), (0, {"ok": True}))
        self.catalog_when(emulator, lambda reply: reply["internal"]["state"] == "ok" and reply["rebuild"] is None)
        made = catalog.MemoryStorage({"one.odrg": animation(1)})
        catalog.rebuild(made, names=["one.odrg"])
        shown = {path.name: path.read_bytes() for path in self.show.iterdir() if path.name.startswith("catalog")}
        self.assertEqual(shown, {name: data for name, data in made.files.items() if name.startswith("catalog")})

    def test_catalog_cancel_without_a_rebuild_is_ok(self):
        emulator = self.start()
        result = support.run_tool("--http", f"127.0.0.1:{emulator.port}", "catalog", "cancel")
        self.assertEqual((result.status, json.loads(result.out)), (0, {"ok": True}))


if __name__ == "__main__":
    unittest.main()

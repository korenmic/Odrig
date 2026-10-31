import json
import os
import pathlib
import shutil
import tempfile
import time
import unittest

from emulator import app, host
from tests.core import support as core_support

from . import support

# How long a test waits for the emulator to take up a change of the drive's folder, which
# it looks for once a second.
WAIT_SECONDS = 10


def has(kind, count=1):
    return lambda events: sum(event.kind == kind for event in events) >= count


class TheOption(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))

    def test_it_names_a_folder_and_does_not_go_with_record_mode(self):
        self.assertEqual(app.parse([str(self.work), "--drive", "stick"]).drive, "stick")
        self.assertIsNone(app.parse([str(self.work)]).drive)
        for argv in ([self.work, "--drive"], [self.work, "--record", self.work / "out.odrr", "--seconds", 1, "--drive", self.work]):
            result = support.run(*argv)
            self.assertEqual(result.status, 2, argv)
            self.assertIn("usage:", result.err)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_the_list_of_a_folder_passes_over_hidden_and_other_files_and_keeps_the_order_of_names(self):
        folder = support.installed(self.work / "odrig", {"b.odrg": b"", "A.ODRG": b"", ".a.odrg": b"", "c.odrg.txt": b"", "notes.txt": b"",
                                                         "d.odrgx": b"", "C.ODRGX": b"", ".e.odrgx": b"", "f.odrgx.txt": b""})
        (folder / "inner.odrg").mkdir()
        self.assertEqual(host.drive_list(folder), ["A.ODRG", "C.ODRGX", "b.odrg", "d.odrgx"])
        support.installed(folder, {f"{index:03d}.odrg": b"" for index in range(300)})
        self.assertEqual(len(host.drive_list(folder)), 304)

    def test_the_list_walks_the_sub_folders_depth_first_to_three_levels(self):
        folder = support.installed(self.work / "odrig", {"b.odrg": b"", "A.ODRG": b""})
        names = ["night/comet.odrg", "night/deep/x.odrg", "night/deep/deeper/y.odrg", "night/deep/deeper/more/z.odrg", "a b/q.odrg", "a-b/r.odrg",
                 ".h/s.odrg", "System Volume Information/t.odrg", "bad./u.odrg", "night/.hidden.odrg", "only/sub/k.odrg"]
        if os.name == "nt":
            # Windows drops a trailing dot from a folder's name, so a folder bad. cannot be made there.
            names.remove("bad./u.odrg")
        for name in names:
            support.installed(folder.joinpath(*name.split("/")[:-1]), {name.split("/")[-1]: b""})
        (folder / "empty").mkdir()
        self.assertEqual(host.drive_list(folder), ["A.ODRG", "b.odrg", "a b/q.odrg", "a-b/r.odrg", "night/comet.odrg", "night/deep/x.odrg",
                                                   "night/deep/deeper/y.odrg", "only/sub/k.odrg"])

    def test_the_list_takes_every_sub_folder(self):
        folder = support.installed(self.work / "odrig", {f"r{index:03d}.odrg": b"" for index in range(5)})
        for index in range(40):
            support.installed(folder / f"f{index:02d}", {"x.odrg": b""})
        names = host.drive_list(folder)
        self.assertEqual((len(names), names[-1]), (45, "f39/x.odrg"))
        nested = support.installed(self.work / "nested" / "odrig", {})
        for index in range(40):
            support.installed(nested / "a" / f"b{index:02d}", {"x.odrg": b""})
        names = host.drive_list(nested)
        self.assertEqual((len(names), names[-1]), (40, "a/b39/x.odrg"))

    def test_the_folder_is_looked_for_once_a_second_and_listed_when_the_core_asks(self):
        now = [0.0]
        drive = host.Drive(self.work, clock=lambda: now[0])
        self.assertEqual(drive.look(), 0)
        support.installed(self.work / "odrig", {"a.odrg": b""})
        now[0] = 0.5
        self.assertEqual(drive.look(), 0)
        now[0] = 1.0
        self.assertEqual((drive.look(), drive.name(1, 0)), (1, None))
        self.assertEqual(drive.list(1), 1)
        self.assertEqual((drive.name(1, 0), drive.name(1, 1)), ("a.odrg", None))
        support.installed(self.work / "odrig", {"b.odrg": b""})
        now[0] = 2.0
        self.assertEqual((drive.look(), drive.names), (1, ["a.odrg"]))
        shutil.rmtree(self.work / "odrig")
        now[0] = 3.0
        self.assertEqual((drive.look(), drive.name(1, 0), drive.path("drive/0")), (0, None, None))
        support.installed(self.work / "odrig", {"b.odrg": b""})
        now[0] = 4.0
        self.assertEqual((drive.look(), drive.list(2), drive.names, drive.path("drive/0")), (2, 1, ["b.odrg"], str(self.work / "odrig" / "b.odrg")))


class AnEmulatorWithADrive(unittest.TestCase):
    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        self.top = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.animation = (self.folder / "hello.odrg").read_bytes()

    def start(self, *options):
        return support.entered(self, support.Emulator(self.folder, "--drive", self.top, *options))

    def listed_when(self, emulator, condition, command="list"):
        """The items of `list`, or of another level's command, once they meet a condition,
        which the test waits for."""
        deadline = time.monotonic() + WAIT_SECONDS
        while True:
            items = [(item["id"], item.get("file")) for item in json.loads(emulator.command(command))["items"]]
            if condition(items) or time.monotonic() > deadline:
                return items
            time.sleep(0.1)

    def drives(self, items):
        return [item for item in items if item[0] >= 60001]

    def test_its_animations_are_listed_after_the_shows_items_and_play(self):
        support.installed(self.top / "odrig", {"Sunrise.odrg": self.animation, "b.odrg": self.animation, "notes.txt": b"notes"})
        emulator = self.start()
        items = self.listed_when(emulator, lambda items: len(self.drives(items)) == 2)
        shows = [item for item in items if item[0] < 60001]
        self.assertEqual(items, shows + [(60001, "Sunrise.odrg"), (60002, "b.odrg")])
        self.assertEqual(json.loads(emulator.command("play 60002")), {"ok": True})
        self.assertEqual(emulator.status()["animation"], 60002)

    def test_the_folders_of_the_drive_are_listed_as_playlists_over_http_and_the_line_port(self):
        folder = support.installed(self.top / "odrig", {"b.odrg": self.animation})
        support.installed(folder / "night", {"comet.odrg": self.animation})
        support.installed(folder / "night" / "deep", {"x.odrg": self.animation})
        emulator = support.entered(self, support.Emulator(self.folder, "--drive", self.top, tcp_port=0))
        items = self.listed_when(emulator, lambda items: len(self.drives(items)) == 2)
        shows = [item for item in items if item[0] < 60001]
        self.assertEqual(items, shows + [(60004, None), (60001, "b.odrg")])
        self.assertEqual(self.listed_when(emulator, lambda items: len(items) == 2, "list in 60004"), [(60005, None), (60002, "night/comet.odrg")])
        self.assertEqual(self.listed_when(emulator, lambda items: len(items) == 1, "list in 60005"), [(60003, "night/deep/x.odrg")])
        reply = json.loads(emulator.command("list"))
        self.assertEqual([item for item in reply["items"] if "playlist" in item], [{"id": 60004, "playlist": "night", "external": True, "files": 1, "ignored": False, "inherited_ignored": False}])
        night = json.loads(emulator.command("list in 60004"))
        self.assertEqual(night["items"][0], {"id": 60005, "playlist": "night/deep", "external": True, "files": 1, "ignored": False, "inherited_ignored": False})
        with support.Lines(emulator.tcp) as port:
            self.assertEqual(json.loads(port.ask("list")), reply)
            self.assertEqual(json.loads(port.ask("list in 60004")), night)
        # The folder's playlist chosen: `playing` names it, and its first animation plays.
        self.assertEqual(json.loads(emulator.command("play 60004")), {"ok": True})
        status = emulator.status()
        self.assertEqual((status["playing"], status["animation"]), (60004, 60002))
        self.assertEqual(json.loads(emulator.command("play all")), {"ok": True})
        self.assertEqual(emulator.status()["playing"], "all")

    def test_external_ignore_is_durable_over_http_and_tcp_without_writing_the_card(self):
        folder = support.installed(self.top / 'odrig', {'b.odrg': self.animation})
        support.installed(folder / 'night', {'comet.odrg': self.animation})
        before = {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
        emulator = support.entered(self, support.Emulator(self.folder, '--drive', self.top, tcp_port=0))
        self.listed_when(emulator, lambda items: len(self.drives(items)) == 2)
        self.listed_when(emulator, lambda items: len(items) == 1, 'list in 60003')
        self.assertEqual(json.loads(emulator.command('ignore 60003 1')), {'ok': True})
        child = json.loads(emulator.command('list in 60003'))['items'][0]
        self.assertFalse(child['ignored'])
        self.assertTrue(child['inherited_ignored'])
        with support.Lines(emulator.tcp) as port:
            self.assertEqual(json.loads(port.ask('play 60002')), {'ok': True})
            self.assertEqual(json.loads(port.ask('ignore 60002 1')), {'ok': True})
            self.assertEqual(json.loads(port.ask('status'))['animation'], 60002)
        self.assertEqual((self.folder / 'ignored.txt').read_bytes(), b'odrig-ignored 1\nd night\nf night/comet.odrg\n')
        self.assertEqual({p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}, before)

    def test_a_damaged_file_and_one_of_another_canvas_are_left_out_and_logged(self):
        wide = core_support.clip(4, 3, 3, (100,))
        # The sound file is read last: once it is listed, the two before it have been read,
        # and they are listed too, with their faults.
        support.installed(self.top / "odrig", {"broken.odrg": self.animation[:-5], "wide.odrg": wide, "z.odrg": self.animation})
        emulator = self.start("--verbose")
        self.assertEqual(self.drives(self.listed_when(emulator, lambda items: len(self.drives(items)) == 3)), [(60001, "broken.odrg"), (60002, "wide.odrg"), (60003, "z.odrg")])
        faults = [item.get("fault") for item in json.loads(emulator.command("list"))["items"] if item["id"] > 60000]
        self.assertEqual(faults, ["truncated", "size-mismatch", None])
        err = emulator.stop().err
        self.assertIn("core: drive file broken.odrg left out: truncated\n", err)
        self.assertIn("core: drive file wide.odrg left out: size-mismatch\n", err)

    def test_the_folder_appearing_and_going_plugs_the_drive_in_and_pulls_it_out(self):
        emulator = self.start()
        time.sleep(1.5)
        self.assertEqual(self.drives(self.listed_when(emulator, lambda items: True)), [])
        support.installed(self.top / "odrig", {"a.odrg": self.animation})
        self.assertEqual(self.drives(self.listed_when(emulator, lambda items: self.drives(items))), [(60001, "a.odrg")])
        self.assertEqual(json.loads(emulator.command("play 60001")), {"ok": True})
        shutil.rmtree(self.top / "odrig")
        self.assertEqual(self.drives(self.listed_when(emulator, lambda items: not self.drives(items))), [])
        self.assertNotEqual(emulator.status()["animation"], 60001)

    def test_the_hello_of_the_page_names_the_drive(self):
        emulator = self.start()
        stream = support.entered(self, support.EventStream(emulator.port))
        hello = json.loads(stream.read_until(has("hello"))[0].data)
        self.assertEqual(hello["drive"], str(self.top))


class TheFolderOption(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))

    def test_it_names_a_folder_and_goes_neither_with_drive_nor_with_record_mode(self):
        arguments = app.parse([str(self.work), "--drive-folder", "collection/card"])
        self.assertEqual((arguments.drive_folder, arguments.drive), ("collection/card", None))
        self.assertIsNone(app.parse([str(self.work)]).drive_folder)
        for argv in ([self.work, "--drive-folder"], [self.work, "--drive", self.work, "--drive-folder", self.work],
                     [self.work, "--drive-folder", self.work, "--drive", self.work],
                     [self.work, "--record", self.work / "out.odrr", "--seconds", 1, "--drive-folder", self.work]):
            result = support.run(*argv)
            self.assertEqual(result.status, 2, argv)
            self.assertIn("usage:", result.err)
        self.assertIn("not allowed with argument", support.run(self.work, "--drive", self.work, "--drive-folder", self.work).err)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_the_folder_itself_is_the_drives_folder_odrig_and_is_listed_by_the_same_code(self):
        folder = support.installed(self.work / "card", {"b.odrg": b"b", "A.ODRG": b"a", "notes.txt": b""})
        support.installed(folder / "night", {"comet.odrg": b"c"})
        now = [0.0]
        drive = host.Drive(folder, clock=lambda: now[0], writable=False, itself=True)
        self.assertEqual((drive.folder, drive.look()), (str(folder), 1))
        self.assertEqual((drive.list(1), drive.names), (3, host.drive_list(folder)))
        self.assertEqual(drive.names, ["A.ODRG", "b.odrg", "night/comet.odrg"])
        self.assertEqual(pathlib.Path(drive.path("drive/2")), folder / "night" / "comet.odrg")
        self.assertIsNone(drive.path("drive/new.odrg", changing=True))
        self.assertFalse(drive.can_write(1))
        folder.rename(self.work / "away")
        now[0] = 2.0
        self.assertEqual(drive.look(), 0)


class AnEmulatorWithADriveFolder(unittest.TestCase):
    """A folder given as the card's folder `odrig` itself, as `collection/card` is."""

    listed_when = AnEmulatorWithADrive.listed_when
    drives = AnEmulatorWithADrive.drives

    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        self.top = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.animation = (self.folder / "hello.odrg").read_bytes()

    def start(self, *options):
        return support.entered(self, support.Emulator(self.folder, "--drive-folder", self.top / "card", *options))

    def test_its_animations_are_served_as_those_of_odrig_and_play(self):
        support.installed(self.top / "card", {"Sunrise.odrg": self.animation, "notes.txt": b"notes"})
        support.installed(self.top / "card" / "night", {"comet.odrg": self.animation})
        emulator = self.start()
        items = self.listed_when(emulator, lambda items: len(self.drives(items)) == 2)
        shows = [item for item in items if item[0] < 60001]
        self.assertEqual(items, shows + [(60003, None), (60001, "Sunrise.odrg")])
        self.assertEqual(self.listed_when(emulator, lambda items: len(items) == 1, "list in 60003"), [(60002, "night/comet.odrg")])
        self.assertEqual(json.loads(emulator.command("play 60002")), {"ok": True})
        self.assertEqual(emulator.status()["animation"], 60002)
        stream = support.entered(self, support.EventStream(emulator.port))
        self.assertEqual(json.loads(stream.read_until(has("hello"))[0].data)["drive"], str(self.top / "card"))

    def test_it_is_read_only(self):
        support.installed(self.top / "card", {"Sunrise.odrg": self.animation})
        emulator = self.start()
        self.listed_when(emulator, lambda items: len(self.drives(items)) == 1)
        self.assertEqual(json.loads(emulator.command("catalog rebuild external")), {"ok": False, "error": "read-only"})
        self.assertEqual(json.loads(emulator.command("upload begin external x.odrg 10")), {"ok": False, "error": "read-only"})
        self.assertEqual(sorted(path.name for path in (self.top / "card").iterdir()), ["Sunrise.odrg"])

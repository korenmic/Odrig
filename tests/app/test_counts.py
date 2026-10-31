import json
import pathlib
import shutil
import tempfile
import time
import unittest

from odrig import catalog
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

# The capacity of a medium, as the core reports it, in its words on the screen.
CAPACITY = r"free [0-9]+\.[0-9] (MB|GB) of [0-9]+\.[0-9] (MB|GB) \(read-only\)\."
# The same of a drive with a catalog, which the installation may write.
WRITABLE = r"free [0-9]+\.[0-9] (MB|GB) of [0-9]+\.[0-9] (MB|GB)\."
INTERNAL = r"free [0-9]+\.[0-9] MB of [0-9]+\.[0-9] MB"
BUSY = (200, '{"ok":false,"error":"busy"}\n')


def cataloged(top, files):
    """Puts these files into the folder `odrig` of a drive, with the catalog and the index
    the PC library makes of them for the example show's canvas: written beside it and moved
    into place at once, so that the drive is never plugged in half written."""
    storage = catalog.MemoryStorage(dict(files), drive=True)
    catalog.rebuild(storage, canvas=(60, 6))
    emulator_support.installed(top / "odrig.part", storage.files)
    (top / "odrig.part").rename(top / "odrig")


def space(animations, present, free=None, total=None):
    external = {"present": present, "free": free, "total": total, "read_only": True}
    return (200, json.dumps({"ok": True, "free": 8372224, "total": 10354688, "animations": animations, "external": external}) + "\n")


class Counts(unittest.TestCase):
    def emulator(self, *arguments):
        folder = entered(self, emulator_support.example_show())
        started = entered(self, emulator_support.Emulator(folder, *arguments))
        return started, f"127.0.0.1:{started.port}", folder

    def drive(self):
        """A folder that stands for the top of a drive, with no folder `odrig` yet."""
        return pathlib.Path(entered(self, tempfile.TemporaryDirectory()))

    def read(self, emulator, items):
        """Waits until the emulator lists so many items, a drive's among them."""
        deadline = time.monotonic() + 10
        while len(json.loads(emulator.command("list"))["items"]) < items and time.monotonic() < deadline:
            time.sleep(0.1)

    def lines(self, address, rows, untils, steps=(), ms=8000):
        return support.run("counts", address=address, settings={"rows": rows, "untils": untils, "ms": ms}, steps=steps).seen["seen"]


class OnTheShowScreen(Counts):
    def test_a_drive_without_a_catalog_has_no_number(self):
        emulator, address, folder = self.emulator("--drive", top := self.drive())
        emulator_support.installed(top / "odrig", {"a.odrg": (folder / "hello.odrg").read_bytes()})
        self.read(emulator, 4)
        seen = self.lines(address, 3, [rf"External storage: {CAPACITY}$"], ms=20000)
        self.assertRegex(seen[0]["external"], rf"\AExternal storage: {CAPACITY}\Z")

    def test_without_a_drive_the_board_s_own_animations_are_counted_and_the_drive_is_absent(self):
        emulator, address, _ = self.emulator()
        seen = self.lines(address, 2, [rf"^Internal storage: 2 animations, {INTERNAL} \| External storage: absent \(read-only\)\.$"])
        self.assertEqual(seen[0]["external"], "External storage: absent (read-only).")

    def test_a_drive_s_animations_are_counted_on_its_line(self):
        emulator, address, folder = self.emulator("--drive", top := self.drive())
        cataloged(top, {"a.odrg": (folder / "hello.odrg").read_bytes(), "b.odrg": (folder / "dvd.odrg").read_bytes()})
        self.read(emulator, 5)
        seen = self.lines(address, 4, [rf"^Internal storage: 2 animations, {INTERNAL} \| External storage: 2 animations, {WRITABLE}$"], ms=20000)
        self.assertRegex(seen[0]["external"], rf"\AExternal storage: 2 animations, {WRITABLE}\Z")

    def test_a_drive_without_animations_says_0(self):
        emulator, address, _ = self.emulator("--drive", top := self.drive())
        cataloged(top, {})
        seen = self.lines(address, 2, [rf"External storage: 0 animations, {WRITABLE}$"], ms=20000)
        self.assertRegex(seen[0]["external"], rf"\AExternal storage: 0 animations, {WRITABLE}\Z")

    def test_a_drive_plugged_in_and_pulled_out_while_the_app_runs_is_followed(self):
        emulator, address, folder = self.emulator("--drive", top := self.drive())
        plug = lambda: cataloged(top, {"a.odrg": (folder / "hello.odrg").read_bytes()})
        pull = lambda: shutil.rmtree(top / "odrig")
        untils = [r"External storage: absent \(read-only\)\.$", rf"External storage: 1 animation, {WRITABLE}$", r"External storage: absent \(read-only\)\.$"]
        seen = self.lines(address, 2, untils, steps=[plug, pull], ms=25000)
        self.assertEqual([line["internal"] for line in seen], [seen[0]["internal"]] * 3)
        self.assertRegex(seen[0]["internal"], rf"\AInternal storage: 2 animations, {INTERNAL}\Z")


class WhatIsNotKnown(Counts):
    def test_disconnect_drops_stale_absence_or_capacity_and_recovers_unknown_mounted_storage(self):
        listed = (200, json.dumps({"ok": True, "items": [
            {"id": 1, "file": "one.odrg", "bytes": 1138, "ignored": False, "external": False},
            {"id": 60001, "file": "card.odrg", "bytes": 52340, "ignored": False, "external": True},
        ], "next": None}))
        for mounted in (False, True):
            with self.subTest(mounted=mounted):
                mode = {"offline": False, "recovered": False}

                def reply(line):
                    if mode["offline"]:
                        return 503, ""
                    if line == b"space":
                        if mode["recovered"]:
                            return space(1, True)
                        return space(1, mounted, 77000000 if mounted else None, 99000000 if mounted else None)
                    return support.PLAYING if line == b"status" else listed

                def offline():
                    mode["offline"] = True

                def recover():
                    mode.update(offline=False, recovered=True)

                initial = r"free 77\.0 MB of 99\.0 MB" if mounted else r"External storage: absent \(read-only\)\.$"
                with support.StandIn({name: reply for name in ("status", "list", "space")}) as target:
                    seen = self.lines(target.address, 2, [initial, r"External storage: information unavailable\.$",
                                      r"External storage: 1 animation, capacity unavailable \(read-only\)\.$"],
                                      steps=[offline, recover], ms=12000)
                    self.assertEqual(target.together, 1)
                self.assertEqual(seen[1]["external"], "External storage: information unavailable.")
                self.assertEqual(seen[2]["external"], "External storage: 1 animation, capacity unavailable (read-only).")

    def test_while_the_list_is_busy_the_drive_s_number_is_not_known_yet_and_the_board_s_is(self):
        replies = {"status": support.PLAYING, "list": BUSY, "space": space(2, True, 3100000000, 31900000000)}
        with support.StandIn(replies) as target:
            seen = self.lines(target.address, 0, [r"animations not known yet"])
        self.assertEqual(seen[0], {"internal": "Internal storage: 2 animations, free 8.4 MB of 10.4 MB",
                                   "external": "External storage: animations not known yet, free 3.1 GB of 31.9 GB (read-only)."})

    def test_an_invalid_show_s_number_is_not_known(self):
        invalid = (200, '{"ok":true,"on":true,"brightness":128,"playing":null,"animation":null,"fps":0,"error":"file-missing"}\n')
        refused = (200, '{"ok":false,"error":"show-invalid"}\n')
        with support.StandIn({"status": invalid, "list": refused, "space": space(0, False)}) as target:
            seen = self.lines(target.address, 0, [r"animations not known"])
        self.assertEqual(seen[0], {"internal": "Internal storage: animations not known, free 8.4 MB of 10.4 MB",
                                   "external": "External storage: absent (read-only)."})

    def test_a_present_drive_whose_capacity_is_unknown_still_says_its_number(self):
        listed = (200, '{"ok":true,"items":[{"id":1,"file":"one.odrg","bytes":1138,"ignored":false},{"id":60001,"file":"card.odrg","bytes":52340}],"next":null}\n')
        with support.StandIn({"status": support.PLAYING, "list": listed, "space": space(1, True)}) as target:
            seen = self.lines(target.address, 2, [r"External storage: 1 animation"])
        self.assertEqual(seen[0]["external"], "External storage: 1 animation, capacity unavailable (read-only).")


class OnTheStorageScreen(Counts):
    def test_its_two_lines_say_the_same_words(self):
        listed = (200, '{"ok":true,"items":[{"id":1,"file":"one.odrg","bytes":1138,"ignored":false},{"id":2,"file":"two.odrg","bytes":1612,"ignored":false},{"id":60001,"file":"card.odrg","bytes":52340}],"next":null}\n')
        with support.StandIn({"status": support.PLAYING, "list": listed, "space": space(2, True, 3100000000, 31900000000)}) as target:
            found = support.run("storage", address=target.address, settings={"rows": 3}).seen
        self.assertEqual(found["before"]["space"], "Internal storage: 2 animations, free 8.4 MB of 10.4 MB")
        self.assertEqual(found["before"]["externalSpace"], "External storage: 1 animation, free 3.1 GB of 31.9 GB (read-only).")


if __name__ == "__main__":
    unittest.main()

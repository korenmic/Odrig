"""Downloads and backups of the shared app: one file saved as it is, one zip of a selection of
one storage with its manifest, read back by Python's own reader, a partial backup, a file
that changes while it is read, and an installation that reads 600 bytes at a time."""

import base64
import io
import json
import pathlib
import struct
import tempfile
import time
import unittest
import zipfile
import zlib

from odrig import catalog

from tests.core import support as core_support
from tests.emulator import support as emulator_support
from . import support
from .test_target import entered

MANIFEST = "odrig-backup.json"
STATUS = (200, '{"ok":true,"on":true,"brightness":128,"playing":"all","animation":1,"fps":50,"error":null}\n')


def archive(found):
    """The one file a scenario saved, as an open zip, and its name."""
    (saved,) = found["files"]
    return zipfile.ZipFile(io.BytesIO(base64.b64decode(saved["data"]))), saved["name"]


def crc(data):
    return f"{zlib.crc32(data):08x}"


def rows_of(emulator, line, wanted):
    """The rows a `list` line gives once they hold a row with this path, which a card without
    a catalog lists once it has read its files."""
    for _ in range(200):
        reply = json.loads(emulator.command(line))
        found = [row for row in reply.get("items", []) if wanted in (row.get("file"), row.get("playlist"))]
        if found:
            return reply["items"], found[0]
        time.sleep(0.05)
    raise AssertionError(f"{line} never listed {wanted}")


class TheZipWriter(unittest.TestCase):
    def test_an_archive_is_read_back_by_pythons_reader_with_data_descriptors_and_stored_entries(self):
        files = [("a.odrg", bytes(range(256)) * 9, 1000), ("deep/b.odrgx", b"", 7), ("naïve.odrg", b"x" * 5, 2)]
        settings = {"files": [{"name": name, "data": base64.b64encode(data).decode("ascii"), "piece": piece} for name, data, piece in files]}
        seen = support.run("zip-writer", settings=settings).seen
        data = base64.b64decode(seen["archive"])
        self.assertEqual((seen["size"], seen["measured"]), (len(data), len(data)))
        made = zipfile.ZipFile(io.BytesIO(data))
        self.assertIsNone(made.testzip())
        self.assertEqual(made.namelist(), ["empty/"] + [name for name, _, _ in files])
        for (name, content, _), entry in zip(files, seen["entries"]):
            info = made.getinfo(name)
            self.assertEqual(made.read(name), content)
            self.assertEqual((info.compress_type, info.flag_bits & 0x08, info.CRC, entry), (zipfile.ZIP_STORED, 0x08, zlib.crc32(content), {"crc": zlib.crc32(content), "size": len(content)}))
            self.assertEqual(info.flag_bits & 0x800, 0x800 if not name.isascii() else 0)
            self.assertEqual(info.date_time, (2026, 11, 8, 17, 30, 42))
            # The local header has no CRC-32 and no sizes; the descriptor after the bytes has them.
            local = info.header_offset
            self.assertEqual(struct.unpack_from("<IHHHHHIII", data, local)[6:], (0, 0, 0))
            start = local + 30 + len(name.encode("utf-8"))
            self.assertEqual(struct.unpack_from("<IIII", data, start + len(content)), (0x08074B50, zlib.crc32(content), len(content), len(content)))
        self.assertTrue(made.getinfo("empty/").is_dir())
        self.assertEqual(len(seen["refusals"]), 7)
        self.assertTrue(all(isinstance(reason, str) for reason in seen["refusals"]), seen["refusals"])
        self.assertIn("already", seen["refusals"][-1])
        self.assertEqual(seen["afterFinish"], "The archive is finished.")
        self.assertEqual(seen["fits"], [False, True, True, False])
        self.assertEqual(seen["mostEntries"], 65534)
        self.assertIn("65,535 entries", seen["tooMany"])


class Downloads(unittest.TestCase):
    def show(self, files=None):
        """The board's storage of a show of two animations, unless other files are given."""
        clip = core_support.clip(2, 60, 6, durations=(20,) * 12, compressed=False)
        given = files or {"show.json": json.dumps({"version": 1, "brightness": 32, "items": [{"id": 1, "file": "face.odrg"}, {"id": 2, "file": "night.odrg"}]}),
                          "face.odrg": clip, "night.odrg": core_support.clip(3, 60, 6, durations=(20,) * 3, compressed=False)}
        return emulator_support.installed(pathlib.Path(entered(self, tempfile.TemporaryDirectory()), "show"), {"mapping.json": core_support.mapping_texts()["legs-2"], **given})

    def card(self, folder, names, read_only=False):
        """A card of these files, a path and its bytes each, with its catalog; the emulator
        on the show and the card."""
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        drive = top / "odrig"
        for name, data in names.items():
            path = drive.joinpath(*name.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if not read_only:
            _, refused = catalog.rebuild(catalog.Storage(drive, drive=True), names=list(names), canvas=(60, 6))
            self.assertEqual(refused, [])
        return drive, entered(self, emulator_support.Emulator(folder, "--drive", top))

    def test_download_saves_an_animations_bytes_as_they_are_under_its_name(self):
        folder = self.show()
        emulator = entered(self, emulator_support.Emulator(folder))
        found = support.run("downloads", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "one": 1}).seen
        self.assertIn("Download", found["menu"])
        (saved,) = found["files"]
        self.assertEqual((saved["name"], base64.b64decode(saved["data"])), ("face.odrg", (folder / "face.odrg").read_bytes()))
        self.assertIn(f"Saved face.odrg: {len((folder / 'face.odrg').read_bytes())} bytes of Internal /face.odrg", found["message"])

    def test_a_file_of_a_read_only_card_is_downloaded_from_its_folder(self):
        folder = self.show()
        data = core_support.clip(4, 60, 6, durations=(20,) * 9, compressed=False)
        _, emulator = self.card(folder, {"night/deep/old.odrg": data}, read_only=True)
        _, night = rows_of(emulator, "list", "night")
        _, deep = rows_of(emulator, f"list in {night['id']}", "night/deep")
        _, old = rows_of(emulator, f"list in {deep['id']}", "night/deep/old.odrg")
        found = support.run("downloads", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "enter": ["night", "night/deep"], "rowsThere": 1, "one": old["id"]}).seen
        (saved,) = found["files"]
        self.assertEqual((saved["name"], base64.b64decode(saved["data"])), ("old.odrg", data))
        self.assertIn("Select", found["menu"])

    def test_download_selected_saves_one_zip_of_the_level_shown_with_its_manifest(self):
        folder = self.show()
        names = {"night/x.odrg": core_support.clip(5, 60, 6, durations=(20,) * 4, compressed=False),
                 "night/deep/old.odrg": core_support.clip(6, 60, 6, durations=(20,) * 5, compressed=False),
                 "loose.odrg": core_support.clip(7, 60, 6, durations=(20,) * 2, compressed=False)}
        drive, emulator = self.card(folder, names)
        self.assertEqual(json.loads(emulator.command("folder make external night/empty"))["made"], True)
        _, night = rows_of(emulator, "list", "night")
        _, x = rows_of(emulator, f"list in {night['id']}", "night/x.odrg")
        self.assertEqual(json.loads(emulator.command(f"brightness {x['id']} 9 save")), {"ok": True})
        found = support.run("downloads", address=f"127.0.0.1:{emulator.port}",
                            settings={"rows": 3, "enter": ["night"], "rowsThere": 1, "files": [x["id"]], "folders": ["night/deep", "night/empty"]}).seen
        self.assertEqual(found["summary"], "3 selected: 0 in Internal storage, 1 in External storage. 2 folders of External storage, with everything in them.")
        self.assertEqual((found["deleteDisabled"], found["moveDisabled"], found["downloadDisabled"]), (True, True, False))
        self.assertIsNone(found["choice"])
        self.assertEqual(found["source"], "From External /night/: entries are named from there.")
        self.assertEqual(found["what"], f"1 file and 2 folders with everything in them, saved as one zip with the manifest {MANIFEST}.")
        made, name = archive(found)
        self.assertRegex(name, r"\Aodrig-external-night-[0-9]{8}-[0-9]{6}\.zip\Z")
        self.assertIsNone(made.testzip())
        self.assertEqual(made.namelist(), ["empty/", "x.odrg", "deep/old.odrg", MANIFEST])
        self.assertEqual(made.read("x.odrg"), names["night/x.odrg"])
        self.assertEqual(made.read("deep/old.odrg"), names["night/deep/old.odrg"])
        manifest = json.loads(made.read(MANIFEST))
        self.assertEqual({key: manifest[key] for key in ("format", "version", "sourceStorage", "base", "partial")},
                         {"format": "odrig-backup", "version": 1, "sourceStorage": "external", "base": "night", "partial": False})
        self.assertEqual(manifest["catalog"], {"generation": catalog.read(catalog.Storage(drive, drive=True)).marker.generation})
        self.assertEqual([(file["path"], file["entry"], file["size"], file["crc32"], file["outcome"]) for file in manifest["files"]],
                         [(path, path[len("night/"):], len(names[path]), crc(names[path]), "saved") for path in ("night/x.odrg", "night/deep/old.odrg")])
        self.assertEqual(manifest["files"][0]["settings"], {"ignored": False, "inheritedIgnored": False, "brightness": 9, "repeat": None, "start": False, "savedUnknown": None})
        self.assertEqual([(entry["path"], entry["entry"]) for entry in manifest["folders"]], [("night/deep", "deep/"), ("night/empty", "empty/")])
        self.assertIn(f"Saved the backup {name} of External /night: 2 of 2 files.", found["message"])
        self.assertTrue(found["dialogHidden"])

    def test_a_selection_of_both_storages_is_backed_up_one_storage_at_a_time(self):
        folder = self.show()
        _, emulator = self.card(folder, {"loose.odrg": core_support.clip(7, 60, 6, durations=(20,) * 2, compressed=False)})
        _, loose = rows_of(emulator, "list", "loose.odrg")
        # Select all takes the board's files; the read-only card's is selected by hand.
        found = support.run("downloads", address=f"127.0.0.1:{emulator.port}", settings={"rows": 3, "selectAll": True, "files": [loose["id"]], "storage": "internal"}).seen
        self.assertEqual(found["summary"], "3 selected: 2 in Internal storage, 1 in External storage.")
        self.assertEqual(found["choice"], ["Internal storage: 2 files", "External storage: 1 file"])
        self.assertEqual(found["source"], "From Internal /: entries are named from there.")
        made, name = archive(found)
        self.assertRegex(name, r"\Aodrig-internal-root-")
        self.assertEqual(made.namelist(), ["face.odrg", "night.odrg", MANIFEST])
        manifest = json.loads(made.read(MANIFEST))
        self.assertEqual((manifest["sourceStorage"], manifest["base"], [file["stored"] for file in manifest["files"]]), ("internal", "", ["face.odrg", "night.odrg"]))
        self.assertEqual(made.read("night.odrg"), (folder / "night.odrg").read_bytes())

    def test_a_partial_backup_says_so_and_names_the_file_that_failed(self):
        clip = core_support.clip(2, 60, 6, durations=(20,) * 3, compressed=False)
        folder = self.show({"show.json": json.dumps({"version": 1, "brightness": 32, "items": [{"id": 1, "file": "good.odrg"}, {"id": 2, "file": "bad.odrg"}]}),
                            "good.odrg": clip, "bad.odrg": clip[:-7]})
        emulator = entered(self, emulator_support.Emulator(folder))
        found = support.run("downloads", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "selectAll": True}).seen
        made, _ = archive(found)
        self.assertEqual(made.namelist(), ["good.odrg", MANIFEST])
        manifest = json.loads(made.read(MANIFEST))
        self.assertTrue(manifest["partial"])
        good, bad = manifest["files"]
        self.assertEqual((good["outcome"], bad["outcome"], bad["crc32"]), ("saved", "failed", None))
        self.assertIsInstance(bad["fault"], str)
        self.assertIn("It is a partial backup.", found["message"])
        self.assertIn("Failed 1: bad.odrg", found["message"])


class StandIn(unittest.TestCase):
    """A target of the test's own: its files, its list and its reads, which may change."""

    def target(self, files, counts=True, changed=None, delay=0.0, counted=None):
        """`counts` false refuses every read with a count, and `counted` refuses those after
        so many, as another installation at the same address would."""
        data = dict(files)
        state = {"reads": 0, "counted": 0}

        def listed(line):
            sizes = {name: len(content) + (1 if name == changed and state["reads"] > 1 else 0) for name, content in data.items()}
            items = [{"id": number, "file": name, "bytes": sizes[name], "ignored": False, "external": False, "type": "frames"} for number, name in enumerate(data, start=1)]
            return 200, json.dumps({"ok": True, "items": items, "next": None})

        def read(line):
            words = line.decode("ascii").split(" ")
            if len(words) == 4:
                state["counted"] += 1
                if not counts or (counted is not None and state["counted"] > counted):
                    return 200, '{"ok":false,"error":"bad-argument"}'
            number, offset = int(words[1]), int(words[2])
            name = list(data)[number - 1]
            state["reads"] += 1
            piece = data[name][offset:offset + (int(words[3]) if len(words) == 4 else 600)]
            return 200, json.dumps({"ok": True, "bytes": len(data[name]), "data": base64.urlsafe_b64encode(piece).decode("ascii").rstrip("=")})

        replies = {"status": STATUS, "list": listed, "read": read, "space": (200, '{"ok":true,"free":1000000,"total":2000000}'),
                   "saved": (200, '{"ok":true,"brightness":null,"repeat":null,"start":false}')}
        return entered(self, support.StandIn(replies, delay=delay))

    def read_lines(self, target):
        return [line.decode("ascii") for _, line in target.lines if line.startswith(b"read ")]

    def test_a_file_is_read_720_bytes_at_a_time_after_one_probe(self):
        data = bytes(range(256)) * 7
        target = self.target({"a.odrg": data})
        found = support.run("downloads", address=target.address, settings={"rows": 1, "one": 1}).seen
        (saved,) = found["files"]
        self.assertEqual(base64.b64decode(saved["data"]), data)
        self.assertEqual(self.read_lines(target), ["read 1 0 1", "read 1 0 720", "read 1 720 720", "read 1 1440 720"])

    def test_a_download_waits_while_the_app_is_hidden_and_goes_on_when_it_is_shown(self):
        data = bytes(range(256)) * 20
        target = self.target({"a.odrg": data}, delay=0.1)
        found = support.run("downloads", address=target.address, settings={"rows": 1, "one": 1, "hide": True}).seen
        (saved,) = found["files"]
        self.assertEqual(base64.b64decode(saved["data"]), data)
        self.assertNotEqual(found["whileHidden"], f"Read {len(data)} of {len(data)} bytes.")

    def test_an_installation_without_the_count_is_read_600_bytes_at_a_time(self):
        data = bytes(range(256)) * 7
        target = self.target({"a.odrg": data}, counts=False)
        found = support.run("downloads", address=target.address, settings={"rows": 1, "one": 1}).seen
        (saved,) = found["files"]
        self.assertEqual(base64.b64decode(saved["data"]), data)
        self.assertEqual(self.read_lines(target), ["read 1 0 1", "read 1 0", "read 1 600", "read 1 1200"])

    def test_an_installation_that_no_longer_takes_the_count_is_asked_again_and_read_600_bytes_at_a_time(self):
        data = bytes(range(256)) * 7
        target = self.target({"a.odrg": data}, counted=1)
        found = support.run("downloads", address=target.address, settings={"rows": 1, "one": 1}).seen
        (saved,) = found["files"]
        self.assertEqual(base64.b64decode(saved["data"]), data)
        self.assertEqual(self.read_lines(target), ["read 1 0 1", "read 1 0 720", "read 1 0 1", "read 1 0", "read 1 600", "read 1 1200"])

    def test_a_file_that_changes_while_it_is_read_is_left_out_of_the_backup(self):
        steady = bytes(range(200))
        target = self.target({"a.odrg": bytes(range(256)) * 4, "b.odrg": steady}, changed="a.odrg")
        found = support.run("downloads", address=target.address, settings={"rows": 2, "selectAll": True}).seen
        made, _ = archive(found)
        self.assertEqual(made.namelist(), ["b.odrg", MANIFEST])
        self.assertEqual(made.read("b.odrg"), steady)
        manifest = json.loads(made.read(MANIFEST))
        changed, kept = manifest["files"]
        self.assertEqual((changed["path"], changed["outcome"], kept["outcome"], manifest["partial"]), ("a.odrg", "failed", "saved", True))
        self.assertIn("changed while it was read", changed["reason"])
        self.assertIn("Failed 1: a.odrg (It changed while it was read.", found["message"])


def row(number, path, data, external=False):
    return {"id": number, "file": path, "bytes": len(data), "ignored": False, "external": external, "type": "frames"}


class Levels(unittest.TestCase):
    """A target of the test's own whose `list` and `list in` give a level in parts of `page`
    rows from the position asked for, as the board does, and whose reads of some files are
    never answered."""

    def target(self, levels, contents, page=9, hang=(), saved=True, delay=0.0):
        def listed(line):
            words = line.decode("ascii").split(" ")
            level = int(words[2]) if words[1:2] == ["in"] else None
            start = int(words[-1]) if len(words) in (2, 4) else 0
            items = levels.get(level)
            if items is None:
                return 200, '{"ok":false,"error":"unknown-id"}'
            end = start + page
            return 200, json.dumps({"ok": True, "items": items[start:end], "next": end if end < len(items) else None})

        def read(line):
            words = line.decode("ascii").split(" ")
            number, offset = int(words[1]), int(words[2])
            if number in hang:
                return None
            data = contents[number]
            piece = data[offset:offset + (int(words[3]) if len(words) == 4 else 600)]
            return 200, json.dumps({"ok": True, "bytes": len(data), "data": base64.urlsafe_b64encode(piece).decode("ascii").rstrip("=")})

        replies = {"status": STATUS, "list": listed, "read": read,
                   "space": (200, '{"ok":true,"free":1000000,"total":2000000,"animations":1,"external":{"present":true,"free":1000000,"total":2000000,"read_only":false}}')}
        if saved:
            replies["saved"] = (200, '{"ok":true,"brightness":null,"repeat":null,"start":false}')
        return entered(self, support.StandIn(replies, delay=delay))

    def three(self):
        contents = {1: bytes(range(100)), 2: bytes(range(200)), 3: bytes(range(50))}
        return {None: [row(1, "a.odrg", contents[1]), row(2, "b.odrg", contents[2]), row(3, "c.odrg", contents[3])]}, contents

    def test_each_file_is_checked_against_the_part_of_its_level_that_holds_its_row(self):
        contents = {1: b"one" * 10}
        big = []
        for number in range(2, 42):
            contents[number] = bytes([number]) * (10 + number)
            big.append(row(number, f"big/f{number:02}.odrg", contents[number], external=True))
        levels = {None: [row(1, "one.odrg", contents[1]), {"id": 100, "playlist": "big", "external": True, "files": 40, "ignored": False}], 100: big}
        target = self.target(levels, contents, saved=False)
        found = support.run("downloads", address=target.address, settings={"rows": 1, "folders": ["big"]}).seen
        made, _ = archive(found)
        self.assertEqual(made.namelist(), [f"big/f{number:02}.odrg" for number in range(2, 42)] + [MANIFEST])
        self.assertEqual(made.read("big/f17.odrg"), contents[17])
        # The folder is listed whole once, in five parts of nine rows; then each file is
        # checked against the part from its row's position, before and after its read, the
        # part after one file serving before the next.
        lists = [line.decode("ascii") for _, line in target.lines if line.startswith(b"list in 100")]
        self.assertLessEqual(len(lists), 5 + 1 + 40, lists[:12])
        self.assertEqual(lists[:7], ["list in 100 0", "list in 100 9", "list in 100 18", "list in 100 27", "list in 100 36", "list in 100 0", "list in 100 0"])
        manifest = json.loads(made.read(MANIFEST))
        self.assertFalse(manifest["partial"])
        # A target that does not know `saved`: the settings it keeps are unknown, not none.
        self.assertEqual({file["settings"]["savedUnknown"] for file in manifest["files"]}, {"unknown-command"})

    def test_stop_while_a_piece_is_unanswered_saves_the_files_read_before_as_a_partial_backup(self):
        levels, contents = self.three()
        target = self.target(levels, contents, hang={2})
        found = support.run("downloads", address=target.address, settings={"rows": 3, "selectAll": True, "stopAt": 2, "afterMs": 1000}).seen
        self.assertEqual(len(found["files"]), 1, found["message"])
        made, _ = archive(found)
        self.assertEqual(made.namelist(), ["a.odrg", MANIFEST])
        manifest = json.loads(made.read(MANIFEST))
        self.assertTrue(manifest["partial"])
        self.assertEqual([(file["path"], file["outcome"]) for file in manifest["files"]], [("a.odrg", "saved"), ("b.odrg", "stopped"), ("c.odrg", "not-started")])
        self.assertIn("It is a partial backup.", found["message"])
        self.assertIn("Not read after Stop: 2.", found["message"])

    def test_another_target_chosen_during_a_backup_saves_nothing(self):
        levels, contents = self.three()
        first = self.target(levels, contents, delay=0.2)
        other = self.target(levels, contents)
        found = support.run("downloads", address=first.address, settings={"rows": 3, "selectAll": True, "switchAt": 2, "other": other.address}).seen
        self.assertEqual(found["files"], [])
        self.assertEqual([line for _, line in other.lines if line.startswith((b"read", b"saved"))], [])


if __name__ == "__main__":
    unittest.main()

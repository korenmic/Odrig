"""The board writes the card: uploads to it and removals of its animations keep its catalog,
as the PC library keeps it, through a cut or a failure at every storage call."""

import base64
import contextlib
import json
import pathlib
import tempfile
import unittest
import zlib

from odrig import catalog

from . import support
from .test_catalog_changes import commit_point, script_bytes
from .test_catalog_drive import card, drive_ids
from .test_drive import SHOW, asked, replies
from .test_playback import T0, refreshes
from .test_playlist import CANVAS, loop_of

POWER_CUT = 75
CARD = {"sun.odrg": loop_of(2, 5), "moon.odrg": loop_of(3, 6)}


def upload_external(name, data, at):
    """The lines of an upload of a file to the drive, with refreshes for its check."""
    lines = [support.line(at, f"upload begin external {name} {len(data)}")]
    for offset in range(0, len(data), 1500):
        piece = base64.urlsafe_b64encode(data[offset:offset + 1500]).rstrip(b"=").decode("ascii")
        lines.append(support.line(at, f"upload data {offset} {piece}"))
    lines += [f"poll {at + 20 * step}" for step in range(1, 30)]
    return lines + [support.line(at + 600, f"upload end {zlib.crc32(data):08x}")]


@contextlib.contextmanager
def a_card(files):
    with tempfile.TemporaryDirectory() as top:
        folder = pathlib.Path(top, "odrig")
        folder.mkdir()
        for name, data in files.items():
            path = folder.joinpath(*name.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        yield top


def folder_of(top):
    """The files of the card's folder `odrig` and of its sub-folders, by their paths."""
    return support.folder_files(pathlib.Path(top, "odrig"))


def run_on_card(files, script, options=()):
    with a_card(files) as top:
        run = support.start(SHOW, script, ["--drive", top, *options])
        return run, folder_of(top)


class Uploads(unittest.TestCase):
    def test_an_upload_to_the_card_gives_its_id_and_its_entry(self):
        data = loop_of(4, 9)
        run, left = run_on_card(card(CARD), upload_external("new.odrg", data, T0) + asked(1000, "list", "catalog"))
        ended = [reply for reply in replies(run) if "id" in reply and len(reply) == 2]
        self.assertEqual(ended, [{"ok": True, "id": 60003}])
        self.assertEqual(left["new.odrg"], data)
        found = catalog.read(catalog.MemoryStorage(left, drive=True))
        self.assertEqual(found.entry("new.odrg"), catalog.entry_of("new.odrg", data, canvas=CANVAS))
        self.assertEqual(found.marker.generation, 2)
        items = {item["file"]: item for item in replies(run)[-2]["items"] if item.get("external")}
        self.assertEqual(items["new.odrg"], {"id": 60003, "file": "new.odrg", "bytes": len(data), "external": True, "type": "frames", "ignored": False, "inherited_ignored": False})
        self.assertNotIn("upload.part", left)

    def test_a_replacement_keeps_its_id_and_a_removal_frees_its_place(self):
        first, second = loop_of(4, 9), loop_of(5, 10)
        script = upload_external("sun.odrg", first, T0) + asked(1000, "list") + asked(1020, "remove 60001", "list")
        script += upload_external("new.odrg", second, T0 + 1100) + asked(2000, "list")
        run, left = run_on_card(card(CARD), script)
        lists = [{item["file"]: item["id"] for item in reply["items"] if item.get("external")} for reply in replies(run) if "items" in reply]
        ids = drive_ids(card(CARD))
        self.assertEqual(lists[0], ids)
        sun_id = ids["sun.odrg"]
        self.assertEqual(lists[0]["sun.odrg"], sun_id)
        self.assertNotIn("sun.odrg" if sun_id == 60001 else "moon.odrg", lists[1])
        self.assertEqual(lists[2]["new.odrg"], 60001)
        self.assertNotIn("sun.odrg" if sun_id == 60001 else "moon.odrg", left)

    def test_the_card_is_not_read_again_after_a_change_of_its_own(self):
        data = loop_of(4, 9)
        script = upload_external("new.odrg", data, T0) + asked(1000, "remove 60001", "list")
        script += [f"poll {T0 + 1020 + 20 * step}" for step in range(1300)] + asked(27100, "list", "catalog")
        run, _ = run_on_card(card(CARD), script, ["--trace-drive"])
        self.assertFalse([line for line in run.lines if line.startswith(("drive bind", "drive list"))])
        lists = [reply["items"] for reply in replies(run) if "items" in reply]
        self.assertEqual(lists[0], lists[1])
        self.assertEqual(replies(run)[-1]["external"]["generation"], 3)

    def test_a_replacement_of_the_file_that_plays_plays_the_new_one_from_its_start(self):
        new = loop_of(5, 10)
        after = [f"poll {T0 + 920 + 20 * step}" for step in range(150)]
        sun = drive_ids(card(CARD))["sun.odrg"]
        script = asked(0, f"play {sun}") + [f"poll {T0 + 20 * step}" for step in range(1, 15)] + upload_external("sun.odrg", new, T0 + 300) + after
        replaced, _ = run_on_card(card(CARD), script)
        anew = [f"poll {T0 + 20 * step}" for step in range(1, 45)] + asked(900, f"play {sun}") + after
        played, _ = run_on_card(card({**CARD, "sun.odrg": new}), anew)

        def pictures(run):
            produced, _ = refreshes([line for line in run.lines if line.startswith(("refresh", "data"))])
            return [(time, picture) for time, picture in produced if time > T0 + 900]

        self.assertEqual(pictures(replaced), pictures(played))
        self.assertGreater(len({bytes(picture[1]) for _, picture in pictures(played)}), 2)

    def test_space_says_the_card_can_be_written(self):
        run, _ = run_on_card(card(CARD), asked(0, "space"))
        self.assertIs(replies(run)[0]["external"]["read_only"], False)
        run, _ = run_on_card(card(CARD), asked(0, "space"), ["--drive-read-only"])
        self.assertIs(replies(run)[0]["external"]["read_only"], True)
        run, _ = run_on_card(CARD, asked(0, "space"))
        self.assertIs(replies(run)[0]["external"]["read_only"], True)


class Refusals(unittest.TestCase):
    def begin(self, files, options=(), line="upload begin external new.odrg 100"):
        run, _ = run_on_card(files, asked(0, line), options)
        return replies(run)[0]

    def test_in_their_order(self):
        self.assertEqual(self.begin(card(CARD), line="upload begin external New.odrg 100")["error"], "bad-argument")
        self.assertEqual(self.begin(card(CARD), line="upload begin external new.txt 100")["error"], "bad-argument")
        self.assertEqual(self.begin(card(CARD), line="upload begin external new.odrg")["error"], "bad-argument")
        self.assertEqual(self.begin(card(CARD), ["--drive-read-only"])["error"], "read-only")
        self.assertEqual(self.begin(CARD)["error"], "read-only")
        run = support.start(SHOW, asked(0, "upload begin external new.odrg 100"))
        self.assertEqual(replies(run)[0]["error"], "read-only")
        run, _ = run_on_card(card(CARD), asked(0, "upload begin external a.odrg 100", "upload begin external b.odrg 100"))
        self.assertEqual(replies(run)[1]["error"], "busy")

    def test_a_removal_of_a_card_that_cannot_be_written_is_in_use_as_before(self):
        run, left = run_on_card(card(CARD), asked(0, "remove 60001"), ["--drive-read-only"])
        self.assertEqual(replies(run)[0]["error"], "in-use")
        self.assertEqual(left, card(CARD))


class SameAsThePcLibrary(unittest.TestCase):
    def test_uploads_replacements_and_removals_leave_the_same_files(self):
        start = card(CARD)
        new, again = loop_of(4, 9), loop_of(6, 11)
        removed = next(name for name, file_id in drive_ids(start).items() if file_id == 60001)
        script = upload_external("new.odrg", new, T0) + upload_external("sun.odrg", again, T0 + 700) + asked(1500, f"remove {60001}")
        _, left = run_on_card(start, script)
        storage = catalog.MemoryStorage(start, drive=True)
        catalog.add(storage, "new.odrg", new, canvas=CANVAS)
        catalog.add(storage, "sun.odrg", again, canvas=CANVAS)
        catalog.remove(storage, removed)
        self.assertEqual(left, storage.files)

    def test_a_card_with_sub_folders_leaves_the_same_files_too(self):
        start = card({"sun.odrg": loop_of(2, 5), "night/comet.odrg": loop_of(3, 6), "night/deep/x.odrg": loop_of(2, 7), "a b/c.odrg": loop_of(3, 8)})
        new = loop_of(4, 9)
        removed = drive_ids(start)["night/comet.odrg"]
        script = upload_external("new.odrg", new, T0) + asked(1500, f"remove {removed}")
        _, left = run_on_card(start, script)
        storage = catalog.MemoryStorage(start, drive=True)
        catalog.add(storage, "new.odrg", new, canvas=CANVAS)
        catalog.remove(storage, "night/comet.odrg")
        self.assertEqual(left, storage.files)
        self.assertNotIn("night/comet.odrg", left)
        self.assertIn("night/deep/x.odrg", left)


def card_calls(script, options=()):
    """The storage calls of a session with the card, the start's among them."""
    with a_card(card(CARD)) as top:
        run = support.start(SHOW, script, ["--drive", top, "--trace-store", *options])
    return list(run.stored) + [line[len("store "):] for line in run.lines if line.startswith("store ")]


def entries_agree(test, files, what):
    found = catalog.read(catalog.MemoryStorage(files, drive=True))
    test.assertEqual(found.state, "ok", what)
    for entry in found.entries:
        test.assertIn(entry.name, files, what)
        test.assertEqual((len(files[entry.name]), zlib.crc32(files[entry.name])), (entry.bytes, entry.crc), (what, entry.name))
    return found


class Failures(unittest.TestCase):
    """A storage call that fails, at every call of a change of the card: the core goes on, and
    the next plug-in finds the catalog after the change when the call came after the end of
    its commit record or the change succeeded, and before it otherwise."""

    def fail_everywhere(self, script):
        calls = card_calls(script)
        point = commit_point(calls, "drive/catalog.do")
        for at in range(1, len(calls) + 1):
            what = f"storage call {at}, `{calls[at - 1]}`, fails"
            with a_card(card(CARD)) as top, support.installed(SHOW) as show:
                result = support.host("session", show, support.CHECK_FIRST, "--drive", top, "--store-fails-at", at, stdin=script_bytes(script))
                self.assertEqual(result.status, 0, (what, result.out[-300:]))
                support.session(show, asked(0, "status"), ["--drive", top])
                after = folder_of(top)
            made = json.loads([line for line in result.out.splitlines() if line.startswith("reply ")][-1][len("reply "):]).get("ok")
            found = entries_agree(self, after, what)
            self.assertEqual(found.marker.generation, 2 if at > point or made else 1, what)
            self.assertNotIn("catalog.do", sorted(after), what)

    def test_an_upload_to_the_card(self):
        self.fail_everywhere(upload_external("new.odrg", loop_of(4, 9), T0))

    def test_a_replacement_on_the_card(self):
        self.fail_everywhere(upload_external("sun.odrg", loop_of(4, 9), T0))

    def test_a_removal_from_the_card(self):
        self.fail_everywhere(asked(0, "remove 60001"))


class LeftRecord(unittest.TestCase):
    def test_an_upload_after_a_failed_removal_of_the_record(self):
        first, second = loop_of(4, 9), loop_of(5, 10)
        script = upload_external("new.odrg", first, T0) + upload_external("other.odrg", second, T0 + 700)
        failing = card_calls(script).index("remove drive/catalog.do 1") + 1
        later = card_calls(script, ["--store-fails-at", str(failing)])
        part = [at for at, call in enumerate(later) if call == "write_open drive/upload.part 1"][1]
        self.assertIn("remove drive/catalog.do 1", later[failing:part], "the record is finished before the next upload's part")
        cut_at = next(at for at in range(part, len(later)) if later[at].startswith("write_close")) + 1
        with a_card(card(CARD)) as top, support.installed(SHOW) as show:
            result = support.host("session", show, support.CHECK_FIRST, "--drive", top, "--store-fails-at", failing, "--cut-at", cut_at,
                                  stdin=script_bytes(script))
            self.assertEqual(result.status, POWER_CUT, result.out[-300:])
            support.session(show, asked(0, "status"), ["--drive", top])
            after = folder_of(top)
        found = entries_agree(self, after, "after the cut")
        self.assertEqual(found.entry("new.odrg").crc, zlib.crc32(first))


class Cuts(unittest.TestCase):
    def cut_everywhere(self, script):
        start = card(CARD)
        outcomes = set()
        number = 1
        while True:
            with a_card(start) as top, support.installed(SHOW) as show:
                result = support.host("session", show, support.CHECK_FIRST, "--drive", top, "--cut-at", number,
                                      stdin="".join(f"{line}\n" for line in script).encode("ascii"))
                if result.status != POWER_CUT:
                    self.assertEqual(result.status, 0, result.out[-300:])
                    return number, outcomes
                support.session(show, asked(0, "status"), ["--drive", top])
                after = folder_of(top)
            found = catalog.read(catalog.MemoryStorage(after, drive=True))
            self.assertEqual(found.state, "ok", number)
            for entry in found.entries:
                self.assertEqual((len(after[entry.name]), zlib.crc32(after[entry.name])), (entry.bytes, entry.crc), (number, entry.name))
            outcomes.add("before" if found.marker.generation == 1 else "after")
            number += 1

    def test_an_upload_to_the_card(self):
        calls, outcomes = self.cut_everywhere(upload_external("new.odrg", loop_of(4, 9), T0))
        self.assertEqual(outcomes, {"before", "after"})
        self.assertGreater(calls, 8)

    def test_a_removal_from_the_card(self):
        _, outcomes = self.cut_everywhere(asked(0, "remove 60001"))
        self.assertEqual(outcomes, {"before", "after"})


if __name__ == "__main__":
    unittest.main()

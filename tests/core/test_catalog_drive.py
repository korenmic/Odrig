"""A drive's catalog: its record and its marker read without a listing and without reading
an animation or a page, the drive published from its index at once, looked at once in 10
seconds, read again when it changes, and what a damaged or interrupted catalog and a fault
of playback do."""

import contextlib
import json
import pathlib
import tempfile
import unittest

from odrig import catalog

from . import support
from .test_drive import SHOW, a_drive, asked, listed, logged, replies
from .test_playback import T0
from .test_playlist import CANVAS, loop_of

VECTORS = support.ROOT / "tests" / "vectors" / "index"
CASES = json.loads((VECTORS / "cases.json").read_text(encoding="ascii"))


def card(files, names=None):
    """The files of a card's folder `odrig` with the catalog and the index the PC library
    makes of them."""
    storage = catalog.MemoryStorage(files, drive=True)
    made, refused = catalog.rebuild(storage, names=names, canvas=CANVAS)
    assert refused == [], refused
    return storage.files


def drive_ids(files):
    """The id of each file of a card's index, by its path."""
    index = catalog.read(catalog.MemoryStorage(files, drive=True)).index
    return {entry.name: file_id for folder in index.folders for file_id, entry in folder.rows}


def polls(begin, count):
    return [f"poll {T0 + begin + 20 * step}" for step in range(count)]


def read_at_names(run):
    return [line.split(" ")[1] for line in run.lines if line.startswith("read_at ")]


def listing(time):
    """A refresh and `list` from every tenth position on, which together hold every item of a
    show and a drive of up to 80 items."""
    return asked(time, *(f"list {start}" for start in range(0, 80, 10)))


def externals(run):
    """The files of the drive that each `listing` found, by the time of its refresh."""
    found = []
    for reply in replies(run):
        if "items" not in reply:
            continue
        found.append({item["file"] for item in reply["items"] if item.get("external")})
    # Eight replies for each listing.
    return [set().union(*found[at:at + 8]) for at in range(0, len(found), 8)]


DENSE = {"sun.odrg": support.dense_clip(*CANVAS, 20), "moon.odrg": support.dense_clip(*CANVAS, 30), "Star Dust 2.ODRG": loop_of(3, 7)}


class Reading(unittest.TestCase):
    def session(self, drive, script, options=()):
        with a_drive(drive) as top:
            return support.start(SHOW, script, ["--drive", top, "--trace-drive", "--trace-read-at", *options], check_first=False)

    def test_the_drive_is_not_listed_and_none_of_its_animations_and_pages_is_read(self):
        run = self.session(card(DENSE), asked(0, "play 1") + polls(20, 300) + asked(6100, "list", "catalog"))
        self.assertFalse(any(line.startswith(("drive list", "drive bind")) for line in run.lines))
        drive_reads = {name for name in read_at_names(run) if name.startswith("drive/")}
        self.assertEqual(drive_reads - {"drive/catalog.do", "drive/catalog.txt", "drive/index-folders.txt", "drive/index-0.txt"}, set())
        items = replies(run)[-2]["items"]
        self.assertEqual(sorted(item["file"] for item in items if item.get("external")), sorted(DENSE))
        self.assertEqual({item["file"]: item["bytes"] for item in items if item.get("external")}, {name: len(data) for name, data in DENSE.items()})
        self.assertEqual(replies(run)[-1]["external"], {"state": "ok", "generation": 1, "entries": 3, "writable": True})

    def test_nothing_of_the_drive_is_listed_before_every_page_is_read_and_all_then(self):
        files = card({f"clip-{number:03d}.odrg": loop_of(2, number) for number in range(40)})
        script = []
        for step in range(120):
            script += listing(20 * step)
        run = self.session(files, script)
        counts = [len(found) for found in externals(run)]
        self.assertEqual(sorted(set(counts)), [0, 40])
        self.assertEqual(counts, sorted(counts))

    def test_the_reads_at_a_refresh_do_not_grow_with_the_library(self):
        most = []
        for count in (16, 64, 256):
            files = card({f"clip-{number:03d}.odrg": loop_of(2, number) for number in range(count)})
            run = self.session(files, polls(0, 400) + asked(8000, "catalog"), ["--trace-calls"])
            self.assertEqual(replies(run)[-1]["external"]["entries"], count)
            calls = [int(line.split()[1]) for line in run.lines if line.startswith("call ")]
            most.append(max(calls))
        self.assertLessEqual(max(most), 16 * 512 + 461 * 2)

    def test_an_unchanged_marker_is_read_once_in_10_seconds_and_nothing_else(self):
        run = self.session(card(DENSE), polls(0, 2000), ["--trace-calls"])
        names = read_at_names(run)
        published = max(at for at, name in enumerate(names) if name.startswith("drive/index-"))
        later = [name for name in names[published + 1:] if name.startswith("drive/")]
        self.assertEqual(set(later), {"drive/catalog.txt"})
        # From the fifth second to the fortieth, after the publication: three looks, each one
        # reading of the marker to its end.
        looks = []
        time = 0
        for line in run.lines:
            if line.startswith(("refresh ", "idle ")):
                time = int(line.split()[1])
            elif line == "read_at drive/catalog.txt 461 0" and time >= T0 + 5000:
                looks.append(time - T0)
        self.assertEqual(len(looks), 3, looks)
        self.assertEqual([later - earlier for earlier, later in zip(looks, looks[1:])], [10000, 10000])

    def test_another_marker_reloads_the_drive(self):
        with tempfile.TemporaryDirectory() as other:
            pathlib.Path(other, "odrig").mkdir()
            changed = card({**DENSE, "new.odrg": loop_of(2, 9)})
            for name, data in changed.items():
                pathlib.Path(other, "odrig", name).write_bytes(data)
            script = polls(0, 300) + asked(6000, "list") + [f"drive replace {other}"] + polls(6020, 800) + asked(22100, "list", "catalog")
            run = self.session(card(DENSE), script)
        before, after, state = replies(run)[-3:]
        self.assertEqual(len([item for item in before["items"] if item.get("external")]), 3)
        self.assertEqual(sorted(item["file"] for item in after["items"] if item.get("external")), sorted([*DENSE, "new.odrg"]))
        self.assertEqual(state["external"]["generation"], 1)

    def test_a_row_out_of_its_form_leaves_the_drive_without_animations(self):
        files = card(DENSE)
        files["index-0.txt"] = files["index-0.txt"].replace(b" frames ", b" frames,", 1)
        run = self.session(files, polls(0, 300) + asked(6000, "list") + polls(6020, 3) + asked(6100, "list", "catalog"))
        self.assertEqual([item for item in replies(run)[1]["items"] if item.get("external")], [])
        self.assertEqual(replies(run)[2]["external"], {"state": "damaged", "detail": "line", "writable": True})
        self.assertIn("catalog external damaged", logged(run))

    def test_a_file_of_the_index_shorter_than_its_rows_does_the_same(self):
        files = card(DENSE)
        files["index-0.txt"] = files["index-0.txt"][:-180]
        run = self.session(files, polls(0, 300) + asked(6000, "list") + polls(6020, 3) + asked(6100, "catalog"))
        self.assertEqual(replies(run)[1]["external"], {"state": "damaged", "detail": "line", "writable": True})

    def test_a_drive_pulled_out_while_its_catalog_is_read(self):
        files = card({f"clip-{number:03d}.odrg": loop_of(2, number) for number in range(64)})
        run = self.session(files, polls(0, 3) + ["drive pull"] + asked(60, "catalog") + ["drive plug"] + polls(80, 400) + asked(8100, "catalog") + listing(8120))
        self.assertEqual(replies(run)[0]["external"], {"state": "absent"})
        self.assertEqual(replies(run)[1]["external"]["state"], "ok")
        self.assertEqual(len(externals(run)[0]), 64)

    def test_an_interrupted_change_is_finished_on_a_drive_that_can_be_written_and_reported_on_one_that_cannot(self):
        files = card(DENSE)
        storage = catalog.MemoryStorage(files, drive=True)
        calls = []
        original = storage.rename

        class Cut(Exception):
            pass

        def renamed(old, new):
            calls.append(old)
            if len(calls) == 1:
                raise Cut()
            return original(old, new)

        storage.rename = renamed
        with contextlib.suppress(Cut):
            catalog.add(storage, "new.odrg", loop_of(2, 9), canvas=CANVAS)
        self.assertIn("catalog.do", storage.files)
        run = self.session(storage.files, polls(0, 300) + asked(6000, "catalog", "list"))
        self.assertEqual(replies(run)[0]["external"]["generation"], 2)
        self.assertIn("new.odrg", [item["file"] for item in replies(run)[1]["items"]])
        run = self.session(storage.files, polls(0, 300) + asked(6000, "catalog"), ["--drive-read-only"])
        self.assertEqual(replies(run)[0]["external"], {"state": "damaged", "detail": "interrupted", "writable": False})

    def test_a_drive_without_a_catalog_is_listed_and_read_as_before(self):
        run = self.session(DENSE, polls(0, 600) + asked(12000, "list", "catalog"))
        self.assertEqual(len([line for line in run.lines if line.startswith("drive list")]), 1)
        self.assertEqual(len([item for item in replies(run)[0]["items"] if item.get("external")]), 3)
        self.assertEqual(replies(run)[1]["external"], {"state": "none", "writable": True})


class Vectors(unittest.TestCase):
    """The index vectors as drives: the core reads their markers as the PC library does, and
    their rows only as it needs them, without the CRC-32s of the index's files. A row out of
    its form, or a file of the index shorter than its rows, is found once it is read."""

    LEVELS = ("list", "list in 60007", "list in 60008", "list in 60009", "list in 60010", "list in 60011")

    def test_every_vector_as_a_drive(self):
        lazy = {"damaged-index-folder-crc", "damaged-index-map-crc", "damaged-index-row-disagrees"}
        for name, case in sorted(CASES.items()):
            with self.subTest(vector=name):
                files = {path.name: path.read_bytes() for path in (VECTORS / name).iterdir()}
                with a_drive(files) as top:
                    run = support.start(SHOW, polls(0, 300) + asked(6000, *self.LEVELS) + polls(6020, 3) + asked(6100, "catalog"),
                                        ["--drive", top, "--drive-read-only"])
                found = replies(run)[-1]["external"]
                expected = {"state": "ok"} if name in lazy else dict(case, detail="line") if case["state"] == "damaged" else case
                self.assertEqual(found["state"], expected["state"])
                if "detail" in expected:
                    self.assertEqual(found["detail"], expected["detail"])
                if case["state"] == "ok":
                    self.assertEqual((found["generation"], found["entries"]), (case["generation"], len(case["entries"])))
                    walked = sorted((item["id"], item["file"]) for reply in replies(run)[:-1] if "items" in reply for item in reply["items"] if "file" in item and item.get("external"))
                    self.assertEqual(walked, [tuple(pair) for pair in case["walk"]])


class Remembered(unittest.TestCase):
    def test_a_file_left_out_by_the_player_stays_out_until_its_entry_is_another(self):
        good = loop_of(3, 7)
        files = card({"sun.odrg": good, "moon.odrg": loop_of(2, 5)})
        files["sun.odrg"] = good[:-6]
        with tempfile.TemporaryDirectory() as mended:
            pathlib.Path(mended, "odrig").mkdir()
            fixed = card({"sun.odrg": loop_of(4, 8), "moon.odrg": loop_of(2, 5)})
            for name, data in fixed.items():
                pathlib.Path(mended, "odrig", name).write_bytes(data)
            with a_drive(files) as top:
                script = polls(0, 300) + asked(6000, "list")
                run = support.start(SHOW, script, ["--drive", top], check_first=False)
                sun = [item["id"] for item in replies(run)[0]["items"] if item.get("file") == "sun.odrg"][0]
                script += asked(6020, f"play {sun}") + polls(6040, 300) + asked(12100, "list")
                script += ["drive pull"] + asked(12120) + ["drive plug"] + polls(12140, 300) + asked(18200, "list")
                script += [f"drive plug {mended}"] + polls(18220, 300) + asked(24300, "list")
                run = support.start(SHOW, script, ["--drive", top], check_first=False)
        faults = [{item["file"]: item.get("fault") for item in reply["items"] if item.get("external")} for reply in replies(run) if "items" in reply]
        self.assertEqual(faults[1]["sun.odrg"], "truncated")
        self.assertEqual(faults[2]["sun.odrg"], "truncated")
        self.assertIsNone(faults[3]["sun.odrg"])


if __name__ == "__main__":
    unittest.main()

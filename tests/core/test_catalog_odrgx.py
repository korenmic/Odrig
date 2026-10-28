"""The catalogs of seed 35 with the texts and clocks of seed 37: an entry gives a file its
type and its loop, at the start and on a drive, and an upload records them."""

import json
import unittest

from odrig import catalog, odrgx

from . import support
from .test_catalog_writes import a_card, folder_of, upload_external
from .test_clocks import clock_of
from .test_drive import asked, replies
from .test_incremental import upload
from .test_playback import T0
from .test_texts import CANVAS, text_of

TEXT = None
CLOCK = clock_of()


def text():
    global TEXT
    if TEXT is None:
        TEXT = text_of()
    return TEXT


def show_files(with_files=True):
    items = [{"id": 1, "file": "hello.odrgx"}, {"id": 2, "file": "clock.odrgx"}]
    files = {"mapping.json": support.one_leg_mapping(*CANVAS), "show.json": json.dumps({"version": 1, "brightness": 255, "items": items})}
    if with_files:
        files.update({"hello.odrgx": text(), "clock.odrgx": CLOCK})
    return files


def cataloged(files, names=("hello.odrgx", "clock.odrgx"), drive=False):
    storage = catalog.MemoryStorage({name: data.encode() if isinstance(data, str) else data for name, data in files.items()}, drive=drive)
    made, refused = catalog.rebuild(storage, names=names, canvas=CANVAS)
    assert refused == [], refused
    return storage.files


def pictures(run):
    return [line for line in run.lines if line.startswith(("refresh", "data", "idle"))]


class AtTheStart(unittest.TestCase):
    def test_a_cataloged_text_and_clock_are_not_opened_and_play_as_without_a_catalog(self):
        script = asked(0, "list") + [f"poll {T0 + 20 * step}" for step in range(1, 300)]
        plain = support.start(show_files(), script, check_first=False)
        run = support.start(cataloged(show_files()), script, ["--trace-files"], check_first=False)
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrgx")], [])
        items = replies(run)[0]["items"]
        self.assertEqual([(item["file"], item["type"], item["bytes"]) for item in items], [("hello.odrgx", "text", len(text())), ("clock.odrgx", "widget", len(CLOCK))])
        self.assertEqual(pictures(run), pictures(plain))


class OnADrive(unittest.TestCase):
    def test_the_entries_give_the_types(self):
        card = cataloged({"hello.odrgx": text(), "clock.odrgx": CLOCK}, names=None, drive=True)
        files = {"mapping.json": support.one_leg_mapping(*CANVAS), "show.json": json.dumps({"version": 1, "brightness": 255, "items": []})}
        with a_card(card) as top:
            run = support.start(files, asked(0, "list"), ["--drive", top])
        self.assertEqual(sorted((item["file"], item["type"]) for item in replies(run)[0]["items"]), [("clock.odrgx", "widget"), ("hello.odrgx", "text")])


class Uploads(unittest.TestCase):
    def test_an_upload_of_a_text_records_its_type_and_its_loop(self):
        files = cataloged(show_files(), names=("clock.odrgx",))
        run, left = support.start_and_keep({name: data for name, data in files.items() if name != "hello.odrgx"}, upload(1, "hello.odrgx", text()))
        entry = catalog.read(catalog.MemoryStorage(left)).entry("hello.odrgx")
        self.assertEqual((entry.type, entry.total_ms), ("text", odrgx.read_header(text()).loop_ms))

    def test_an_upload_of_a_clock_to_the_card_records_it_as_the_pc_library_does(self):
        card = cataloged({"hello.odrgx": text()}, names=None, drive=True)
        files = {"mapping.json": support.one_leg_mapping(*CANVAS), "show.json": json.dumps({"version": 1, "brightness": 255, "items": []})}
        with a_card(card) as top:
            support.start(files, upload_external("clock.odrgx", CLOCK, T0), ["--drive", top])
            left = folder_of(top)
        storage = catalog.MemoryStorage(card, drive=True)
        catalog.add(storage, "clock.odrgx", CLOCK, canvas=CANVAS)
        self.assertEqual(left, storage.files)
        self.assertEqual(catalog.read(catalog.MemoryStorage(left, drive=True)).entry("clock.odrgx").type, "widget")


if __name__ == "__main__":
    unittest.main()

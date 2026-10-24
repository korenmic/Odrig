import json
import pathlib
import shutil
import tempfile
import time
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

MAPPING = core_support.mapping_texts()["legs-2"]
SPACE = (200, '{"ok":true,"free":8372224,"total":10354688,"animations":4,"external":{"present":true,"free":1000000,"total":2000000,"read_only":true}}\n')
# A list whose items say their types: two normal internal animations, one of them without
# `type`, a text one, a widget, and a text and a normal one on the card.
TYPED = {"ok": True, "items": [
    {"id": 1, "file": "one.odrg", "bytes": 1000, "ignored": False, "external": False},
    {"id": 2, "file": "clock.odrgx", "bytes": 1000, "ignored": False, "external": False, "type": "widget"},
    {"id": 3, "file": "hello.odrgx", "bytes": 1000, "ignored": False, "external": False, "type": "text"},
    {"id": 4, "file": "four.odrg", "bytes": 1000, "ignored": False, "external": False, "type": "frames"},
    {"id": 60001, "file": "card.odrgx", "bytes": 1000, "external": True, "type": "text"},
    {"id": 60002, "file": "card.odrg", "bytes": 1000, "external": True}], "next": None}
ORDER = (200, json.dumps({"ok": True, "ids": [1, 2, 3, 4, 60001, 60002], "next": None, "revision": 7}))


def typed_target(**more):
    return support.StandIn({"status": support.PLAYING, "list": (200, json.dumps(TYPED)), "space": SPACE, "order": ORDER, **more})


class TheFilters(unittest.TestCase):
    def test_every_combination_with_its_counts_and_the_empty_list(self):
        with typed_target() as target:
            found = support.run("filters", address=target.address, settings={"rows": 6, "every": True}).seen
        self.assertEqual(found["first"]["storage"], {"shown": ["All 6", "Internal 4", "External 2"], "chosen": ["All"]})
        self.assertEqual(found["first"]["type"], {"shown": ["All 6", "Normal 3", "Text 2", "Widget 1"], "chosen": ["All"]})
        rows = {key: value["rows"] for key, value in found["combinations"].items()}
        self.assertEqual(rows, {
            "All All": [1, 2, 3, 4, 60001, 60002], "All Normal": [1, 4, 60002], "All Text": [3, 60001], "All Widget": [2],
            "Internal All": [1, 2, 3, 4], "Internal Normal": [1, 4], "Internal Text": [3], "Internal Widget": [2],
            "External All": [60001, 60002], "External Normal": [60002], "External Text": [60001], "External Widget": []})
        # Each choice counts the rows it would show with the other filter as it is.
        self.assertEqual(found["combinations"]["External Normal"]["storage"], ["All 3", "Internal 2", "External 1"])
        self.assertEqual(found["combinations"]["External Normal"]["type"], ["All 2", "Normal 1", "Text 1", "Widget 0"])
        self.assertEqual(found["combinations"]["Internal Widget"]["type"], ["All 4", "Normal 2", "Text 1", "Widget 1"])
        self.assertEqual(" ".join(found["combinations"]["External Widget"]["empty"].split()), "No animation matches the filters. Show all")
        self.assertIsNone(found["combinations"]["External Widget"]["none"])
        self.assertIsNone(found["combinations"]["All All"]["empty"])
        self.assertEqual(found["reset"], {"rows": [1, 2, 3, 4, 60001, 60002], "storage": ["All"], "type": ["All"], "empty": None})

    def test_the_choices_are_kept_across_a_reload(self):
        with typed_target() as target:
            found = support.run("filters", address=target.address, settings={"rows": 6, "kept": True}).seen
        self.assertEqual(found["kept"], {"storage": ["Internal"], "type": ["Normal"], "rows": [1, 4]})

    def test_while_a_filter_hides_rows_moving_is_off_and_says_why(self):
        with typed_target() as target:
            found = support.run("filters", address=target.address, settings={"rows": 6, "moving": True}).seen
            lines = [line for _, line in target.lines]
        self.assertEqual(found["note"], "Set both filters to All to move animations: hidden rows would make the places unclear.")
        self.assertEqual(found["menu"], ["Ignore in playlist", "Move up (disabled)", "Move down (disabled)", "Select", "Delete"])
        self.assertFalse(found["lifted"])
        self.assertEqual(found["noteAll"], "Hold a row to move it, or use Move up and Move down in its menu.")
        self.assertEqual([line for line in lines if line.startswith(b"order move")], [])

    def test_select_all_takes_the_shown_rows_and_a_hidden_row_leaves_the_selection(self):
        with typed_target() as target:
            found = support.run("filters", address=target.address, settings={"rows": 6, "selecting": True}).seen
        self.assertEqual(found["selectedInternal"], [1, 4])
        self.assertEqual(found["afterHiding"], [])
        self.assertEqual(found["question"], "Delete 2 animations from internal storage? 1 one.odrg, 4 four.odrg")

    def test_the_tests_group_is_not_filtered(self):
        with typed_target(mapping=(200, json.dumps({"ok": True, "editable": True, "pins": list(range(1, 19)) + [21, 47], "revision": 1, "test": False, "snake": None}))) as target:
            found = support.run("filters", address=target.address, settings={"rows": 6, "tests": True}).seen
        self.assertEqual(found["tests"], 21)

    def test_a_card_pulled_out_counts_0_and_plugged_in_again_counts_its_animations(self):
        work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        items = [{"id": number, "file": "a.odrg"} for number in (1, 2)]
        files = {"mapping.json": MAPPING, "show.json": json.dumps({"version": 1, "brightness": 32, "items": items}), "a.odrg": core_support.clip(1, 60, 6)}
        folder = emulator_support.installed(work / "show", files)
        emulator_support.installed(work / "card" / "odrig", {"b.odrg": core_support.clip(2, 60, 6), "c.odrg": core_support.clip(3, 60, 6)})
        emulator = entered(self, emulator_support.Emulator(folder, "--drive", str(work / "card")))
        deadline = time.monotonic() + 30
        while len(json.loads(emulator.command("list"))["items"]) < 4 and time.monotonic() < deadline:
            time.sleep(0.1)

        def pull():
            shutil.move(str(work / "card" / "odrig"), str(work / "away"))

        def plug():
            shutil.move(str(work / "away"), str(work / "card" / "odrig"))
        settings = {"rows": 4, "card": {"out": ["All 2", "Internal 2", "External 0"], "in": ["All 4", "Internal 2", "External 2"]}}
        found = support.run("filters", address=f"127.0.0.1:{emulator.port}", settings=settings, steps=[pull, plug]).seen
        self.assertEqual(found["first"]["storage"]["shown"], ["All 4", "Internal 2", "External 2"])
        self.assertEqual(found["first"]["type"]["shown"], ["All 4", "Normal 4", "Text 0", "Widget 0"])
        self.assertEqual(found["out"]["rows"], [1, 2])
        self.assertEqual(found["back"]["rows"], [1, 2, 60001, 60002])

    def test_the_filters_ask_the_target_for_nothing_more(self):
        with typed_target() as target:
            support.run("filters", address=target.address, settings={"rows": 6, "every": True})
            words = {line.split(b" ")[0] for _, line in target.lines}
        self.assertLessEqual(words, {b"status", b"list", b"space", b"order"})


if __name__ == "__main__":
    unittest.main()

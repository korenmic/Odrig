"""The card's folders on Animations, as a file explorer shows them: one level at a time, the
root's rows and the folder rows with their counts, entering a folder and Back, the heading
of a level with its button, the marks of the current playlist, and the line that says what
plays with the time left."""

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

OK = (200, '{"ok":true}\n')
# A card of two loose files and the folders `night`, `night/deep` and `only`, which has a
# file in its sub-folder `only/sub` and none of its own, as the list gives them: the
# folders after the show's items, then the files by their paths.
LISTED = {"ok": True, "items": [
    {"id": 1, "file": "one.odrg", "bytes": 1000, "ignored": False, "external": False},
    {"id": 2, "file": "two.odrg", "bytes": 1000, "ignored": False, "external": False},
    {"id": 60007, "playlist": "night", "external": True},
    {"id": 60008, "playlist": "night/deep", "external": True},
    {"id": 60009, "playlist": "only", "external": True},
    {"id": 60010, "playlist": "only/sub", "external": True},
    {"id": 60001, "file": "a.odrg", "bytes": 1000, "external": True},
    {"id": 60002, "file": "b.odrg", "bytes": 1000, "external": True},
    {"id": 60003, "file": "night/comet.odrg", "bytes": 1000, "external": True},
    {"id": 60004, "file": "night/zeta.odrg", "bytes": 1000, "external": True},
    {"id": 60005, "file": "night/deep/x.odrg", "bytes": 1000, "external": True},
    {"id": 60006, "file": "only/sub/y.odrg", "bytes": 1000, "external": True}], "next": None}
ORDER = (200, json.dumps({"ok": True, "ids": [1, 2, 60001, 60002, 60003, 60004, 60005, 60006], "next": None, "revision": 3}))
SPACE = (200, '{"ok":true,"free":8372224,"total":10354688,"animations":2,"external":{"present":true,"free":1000000,"total":2000000,"read_only":true}}\n')


def status(playing, animation, left=83520):
    """A status reply that plays this, with so many seconds left in the window."""
    value = {"ok": True, "on": True, "brightness": 128, "playing": playing, "animation": animation, "fps": 50, "error": None}
    if left is not None:
        value["left"] = left
    return (200, json.dumps(value) + "\n")


def target(playing, animation, left=83520, **more):
    return support.StandIn({"status": status(playing, animation, left), "list": (200, json.dumps(LISTED) + "\n"), "order": ORDER, "space": SPACE, "play": OK, **more})


def folders(found):
    return [(folder["path"], folder["id"], folder["meta"]) for folder in found["folders"]]


def ids(found):
    return [row["id"] for row in found["rows"]]


def marked(found):
    """What is marked on the screen: the level's head, the folder rows and the rows."""
    return {"level": found["level"]["marked"], "folders": [folder["path"] for folder in found["folders"] if folder["marked"]], "rows": [row["id"] for row in found["rows"] if row["marked"]]}


class TheLevels(unittest.TestCase):
    def test_the_root_holds_its_own_rows_and_a_row_for_each_folder_of_the_card(self):
        with target(60007, 60003) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 4, "folders": 2}).seen["first"]
        self.assertEqual(found["level"], {"title": "Root", "back": False, "marked": False, "button": "Play this folder"})
        self.assertEqual([(row["id"], row["group"]) for row in found["rows"]], [(1, ""), (2, ""), (60001, ""), (60002, "")])
        self.assertEqual(folders(found), [("night", 60007, "2 animations"), ("only", 60009, "0 animations")])
        self.assertEqual([folder["name"] for folder in found["folders"]], ["night", "only"])
        self.assertEqual(marked(found), {"level": False, "folders": ["night"], "rows": []})
        self.assertEqual(found["playing"], "Playlist night \u00b7 23 h 12 min left")
        self.assertEqual(found["buttons"][:4], ["On", "Off", "Add animation", "Select"])
        self.assertEqual([name for name in found["buttons"] if name.startswith(("Play", "Open", "Back"))],
                         ["Play this folder", "Play 1 one.odrg", "Play 2 two.odrg", "Play 60001 a.odrg", "Play 60002 b.odrg", "Open folder night", "Open folder only"])

    def test_a_tap_enters_a_folder_and_back_goes_up_to_the_root(self):
        steps = [{"enter": "night", "level": "night", "rows": 2}, {"enter": "night/deep", "level": "night/deep", "rows": 1}, {"back": True, "level": "night", "rows": 2},
                 {"back": True, "level": "Root", "rows": 4}, {"enter": "only", "level": "only", "rows": 0}, {"enter": "only/sub", "level": "only/sub", "rows": 1}]
        with target(60008, 60005) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 4, "folders": 2, "steps": steps}).seen
        night, deep, night_again, root, only, sub = found["steps"]
        self.assertEqual((night["level"], ids(night), folders(night)), ({"title": "night", "back": True, "marked": False, "button": "Play this folder"}, [60003, 60004], [("night/deep", 60008, "1 animation")]))
        self.assertEqual([(row["id"], row["group"]) for row in night["rows"]], [(60003, "night"), (60004, "night")])
        self.assertEqual((deep["level"]["title"], deep["level"]["back"], ids(deep), folders(deep)), ("night/deep", True, [60005], []))
        self.assertEqual((night_again["level"]["title"], ids(night_again)), ("night", [60003, 60004]))
        self.assertEqual((root["level"]["title"], root["level"]["back"], ids(root)), ("Root", False, [1, 2, 60001, 60002]))
        self.assertEqual((only["level"]["title"], ids(only), folders(only)), ("only", [], [("only/sub", 60010, "1 animation")]))
        self.assertEqual((sub["level"]["title"], ids(sub)), ("only/sub", [60006]))
        # `night/deep` is current: marked at the root on `night`, in `night` on `night/deep`, and in `night/deep` on the head.
        self.assertEqual(marked(found["first"]), {"level": False, "folders": ["night"], "rows": []})
        self.assertEqual(marked(night), {"level": False, "folders": ["night/deep"], "rows": []})
        self.assertEqual(marked(deep), {"level": True, "folders": [], "rows": [60005]})

    def test_the_line_names_the_root_a_folder_the_root_in_its_place_and_an_unknown_folder(self):
        cases = [
            (("all", 1, 86400), "Playlist \u00b7 24 h 0 min left", {"level": True, "folders": []}),
            (("all", 1, None), "Playlist", {"level": True, "folders": []}),
            ((60008, 60005, 3661), "Playlist night/deep \u00b7 1 h 1 min left", {"level": False, "folders": ["night"]}),
            ((60007, 1, 83520), "Playlist night, the root plays for now \u00b7 23 h 12 min left", {"level": False, "folders": ["night"]}),
            ((60007, 60005, 83520), "Playlist night \u00b7 23 h 12 min left", {"level": False, "folders": ["night"]}),
            ((60009, 60001, 59), "Playlist only, the root plays for now \u00b7 0 h 0 min left", {"level": False, "folders": ["only"]}),
            ((60099, 1, 83520), "Playlist 60099 \u00b7 23 h 12 min left", {"level": False, "folders": []}),
        ]
        for (playing, animation, left), words, marks in cases:
            with self.subTest(playing=playing, animation=animation, left=left):
                with target(playing, animation, left) as stand_in:
                    found = support.run("folders", address=stand_in.address, settings={"rows": 4, "folders": 2, "wait": 1500 if playing == 60099 else 0}).seen["first"]
                    lists = [line for _, line in stand_in.lines if line.startswith(b"list")]
                self.assertEqual(found["playing"], words)
                self.assertEqual({key: marked(found)[key] for key in marks}, marks)
                if playing == 60099:
                    # A playlist the list does not hold: the list is asked for again at once.
                    self.assertGreaterEqual(len(lists), 2)

    def test_a_cycle_and_a_card_without_folders_read_as_before(self):
        flat = {"ok": True, "items": [{"id": 1, "file": "one.odrg", "bytes": 1000, "ignored": False}, {"id": 3, "cycle": [1], "seconds": 5}], "next": None}
        with support.StandIn({"status": status(3, 1), "list": (200, json.dumps(flat) + "\n"), "space": SPACE}) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 1}).seen["first"]
        self.assertEqual((found["playing"], found["level"], folders(found)), ("Cycle 3", {"title": "Root", "back": False, "marked": False, "button": "Play this folder"}, []))
        with support.StandIn({"status": status("all", 1), "list": (200, json.dumps(flat) + "\n"), "space": SPACE}) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 1}).seen["first"]
        self.assertEqual((found["playing"], found["level"]["marked"]), ("Playlist", True))

    def test_the_tests_group_stays_above_the_list_untouched(self):
        mapping = (200, json.dumps({"ok": True, "editable": True, "pins": list(range(1, 19)) + [21, 47], "revision": 1, "test": False, "snake": None}))
        with target(60007, 60003, mapping=mapping) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 4, "folders": 2, "tests": True, "steps": [{"enter": "night", "level": "night", "rows": 2}]}).seen
        self.assertEqual((found["first"]["tests"], found["first"]["testsHead"]), (21, "Tests \u00b7 21"))
        self.assertEqual((found["steps"][0]["tests"], found["steps"][0]["testsHead"]), (21, "Tests \u00b7 21"))


class AgainstTheEmulator(unittest.TestCase):
    def card(self, zeta=False):
        """The example show with a card of nested folders: `a.odrg` loose, `night/comet.odrg`
        and with `zeta` `night/zeta.odrg`, `night/deep/x.odrg`, `only/sub/y.odrg`, and an
        empty folder that is no folder of the list."""
        folder = entered(self, emulator_support.example_show())
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        animation = (folder / "hello.odrg").read_bytes()
        emulator_support.installed(top / "odrig", {"a.odrg": animation})
        emulator_support.installed(top / "odrig" / "night", {"comet.odrg": animation, **({"zeta.odrg": animation} if zeta else {})})
        emulator_support.installed(top / "odrig" / "night" / "deep", {"x.odrg": animation})
        emulator_support.installed(top / "odrig" / "only" / "sub", {"y.odrg": animation})
        (top / "odrig" / "empty").mkdir()
        emulator = entered(self, emulator_support.Emulator(folder, "--drive", top))
        deadline = time.monotonic() + 15
        while len(json.loads(emulator.command("list"))["items"]) < (11 if zeta else 10) and time.monotonic() < deadline:
            time.sleep(0.1)
        items = json.loads(emulator.command("list"))["items"]
        folders_ = {item["playlist"]: item["id"] for item in items if "playlist" in item}
        return emulator, top, folders_

    def test_play_this_folder_inside_a_folder_and_at_the_root_and_a_row_outside_the_folder(self):
        emulator, _, folders_ = self.card()
        night = folders_["night"]
        steps = [
            {"enter": "night", "level": "night", "rows": 1},
            {"top": True, "until": "Playlist night \u00b7 2[34] h [0-9]+ min left"},
            {"back": True, "level": "Root", "rows": 3},
            {"row": 1, "until": "Playlist night, the root plays for now \u00b7 2[34] h [0-9]+ min left"},
            {"top": True, "until": "Now 1 hello\\.odrg Playlist \u00b7 2[34] h [0-9]+ min left"},
        ]
        found = support.run("folders", address=f"127.0.0.1:{emulator.port}", settings={"rows": 3, "folders": 2, "steps": steps}).seen
        # The example show begins with its cycle: no playlist is marked, the row on the LEDs is.
        self.assertEqual(found["first"]["playing"], "Cycle 3")
        self.assertEqual(ids(found["first"]), [1, 2, 60001])
        self.assertEqual(folders(found["first"]), [("night", night, "1 animation"), ("only", folders_["only"], "0 animations")])
        self.assertEqual(marked(found["first"]), {"level": False, "folders": [], "rows": [1]})
        entered_night, chosen, root, jumped, root_chosen = found["steps"]
        self.assertEqual((ids(entered_night), folders(entered_night)), ([60002], [("night/deep", folders_["night/deep"], "1 animation")]))
        self.assertEqual(marked(chosen), {"level": True, "folders": [], "rows": [60002]})
        self.assertEqual(marked(root), {"level": False, "folders": ["night"], "rows": []})
        self.assertEqual(marked(jumped), {"level": False, "folders": ["night"], "rows": [1]})
        self.assertEqual(marked(root_chosen), {"level": True, "folders": [], "rows": [1]})
        status_ = emulator.status()
        self.assertEqual((status_["playing"], status_["animation"]), ("all", 1))

    def test_the_card_out_brings_the_list_to_the_root_and_the_card_in_shows_the_folders_again(self):
        emulator, top, folders_ = self.card()
        self.assertEqual(json.loads(emulator.command(f"play {folders_['night']}")), {"ok": True})

        def pull():
            shutil.move(str(top / "odrig"), str(top / "away"))

        def plug():
            shutil.move(str(top / "away"), str(top / "odrig"))
        steps = [{"enter": "night", "level": "night", "rows": 1}, {"step": True, "level": "Root", "rows": 2, "wait": 500}, {"step": True, "until": "Playlist night", "rows": 3, "wait": 500}]
        found = support.run("folders", address=f"127.0.0.1:{emulator.port}", settings={"rows": 3, "folders": 2, "until": "Playlist night", "steps": steps}, steps=[pull, plug]).seen
        inside, out, back = found["steps"]
        self.assertEqual((inside["level"]["title"], marked(inside)["level"]), ("night", True))
        self.assertEqual((out["level"]["title"], out["level"]["back"], ids(out), folders(out), out["playing"]), ("Root", False, [1, 2], [], "Playlist"))
        self.assertEqual(marked(out), {"level": True, "folders": [], "rows": [1]})
        self.assertRegex(back["playing"], r"\APlaylist night(, the root plays for now)? \u00b7 2[34] h [0-9]+ min left\Z")
        self.assertEqual(([folder["path"] for folder in back["folders"]], marked(back)["folders"]), (["night", "only"], ["night"]))


if __name__ == "__main__":
    unittest.main()

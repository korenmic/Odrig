"""The playlists of the card's folders on Animations: the groups in the order they play, the
heading of each with its count and its button, the mark of the current playlist's group,
and the line that says what plays with the time left."""

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
HEADS = [("", None, "Root \u00b7 4"), ("night", 60007, "night \u00b7 2"), ("night/deep", 60008, "night/deep \u00b7 1"), ("only", 60009, "only \u00b7 0"),
         ("only/sub", 60010, "only/sub \u00b7 1")]


def status(playing, animation, left=83520):
    """A status reply that plays this, with so many seconds left in the window."""
    value = {"ok": True, "on": True, "brightness": 128, "playing": playing, "animation": animation, "fps": 50, "error": None}
    if left is not None:
        value["left"] = left
    return (200, json.dumps(value) + "\n")


def target(playing, animation, left=83520, **more):
    return support.StandIn({"status": status(playing, animation, left), "list": (200, json.dumps(LISTED) + "\n"), "order": ORDER, "space": SPACE, "play": OK, **more})


def summary(found):
    return [(head["group"], head["id"], head["title"]) for head in found["heads"]]


class TheGroups(unittest.TestCase):
    def test_the_groups_stand_in_the_order_they_play_with_their_counts_and_buttons(self):
        with target(60007, 60003) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 8, "heads": 5}).seen["first"]
        self.assertEqual(summary(found), HEADS)
        self.assertEqual([head["shown"] for head in found["heads"]], [True] * 5)
        self.assertEqual([head["button"] for head in found["heads"]], ["Play this folder", "Play folder night", "Play folder night/deep", "Play folder only", "Play folder only/sub"])
        self.assertEqual([(row["id"], row["group"]) for row in found["rows"]],
                         [(1, ""), (2, ""), (60001, ""), (60002, ""), (60003, "night"), (60004, "night"), (60005, "night/deep"), (60006, "only/sub")])
        self.assertEqual([head["group"] for head in found["heads"] if head["marked"]], ["night"])
        self.assertEqual([row["id"] for row in found["rows"] if row["marked"]], [60003])
        self.assertEqual(found["playing"], "Playlist night \u00b7 23 h 12 min left")
        self.assertEqual(found["buttons"][:4], ["On", "Off", "Add animation", "Select"])
        self.assertEqual([name for name in found["buttons"] if name.startswith("Play")],
                         ["Play this folder", "Play 1 one.odrg", "Play 2 two.odrg", "Play 60001 a.odrg", "Play 60002 b.odrg", "Play folder night", "Play 60003 night/comet.odrg",
                          "Play 60004 night/zeta.odrg", "Play folder night/deep", "Play 60005 night/deep/x.odrg", "Play folder only", "Play folder only/sub", "Play 60006 only/sub/y.odrg"])

    def test_the_line_names_the_root_a_folder_the_root_in_its_place_and_an_unknown_folder(self):
        cases = [
            (("all", 1, 86400), "Playlist \u00b7 24 h 0 min left", ""),
            (("all", 1, None), "Playlist", ""),
            ((60008, 60005, 3661), "Playlist night/deep \u00b7 1 h 1 min left", "night/deep"),
            ((60007, 1, 83520), "Playlist night, the root plays for now \u00b7 23 h 12 min left", "night"),
            ((60007, 60005, 83520), "Playlist night \u00b7 23 h 12 min left", "night"),
            ((60009, 60001, 59), "Playlist only, the root plays for now \u00b7 0 h 0 min left", "only"),
            ((60099, 1, 83520), "Playlist 60099 \u00b7 23 h 12 min left", None),
        ]
        for (playing, animation, left), words, marked in cases:
            with self.subTest(playing=playing, animation=animation, left=left):
                with target(playing, animation, left) as stand_in:
                    found = support.run("folders", address=stand_in.address, settings={"rows": 8, "heads": 5, "wait": 1500 if playing == 60099 else 0}).seen["first"]
                    lists = [line for _, line in stand_in.lines if line.startswith(b"list")]
                self.assertEqual(found["playing"], words)
                self.assertEqual([head["group"] for head in found["heads"] if head["marked"]], [] if marked is None else [marked])
                if playing == 60099:
                    # A playlist the list does not hold: the list is asked for again at once.
                    self.assertGreaterEqual(len(lists), 2)

    def test_a_cycle_and_a_card_without_folders_read_as_before(self):
        flat = {"ok": True, "items": [{"id": 1, "file": "one.odrg", "bytes": 1000, "ignored": False}, {"id": 3, "cycle": [1], "seconds": 5}], "next": None}
        with support.StandIn({"status": status(3, 1), "list": (200, json.dumps(flat) + "\n"), "space": SPACE}) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 1}).seen["first"]
        self.assertEqual((found["playing"], summary(found)), ("Cycle 3", [("", None, "Root \u00b7 1")]))
        self.assertEqual([head["marked"] for head in found["heads"]], [False])
        with support.StandIn({"status": status("all", 1), "list": (200, json.dumps(flat) + "\n"), "space": SPACE}) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 1}).seen["first"]
        self.assertEqual((found["playing"], [head["marked"] for head in found["heads"]]), ("Playlist", [True]))

    def test_the_tests_group_stays_above_the_groups_untouched(self):
        mapping = (200, json.dumps({"ok": True, "editable": True, "pins": list(range(1, 19)) + [21, 47], "revision": 1, "test": False, "snake": None}))
        with target(60007, 60003, mapping=mapping) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 8, "heads": 5, "tests": True}).seen["first"]
        self.assertEqual((found["tests"], found["testsHead"]), (21, "Tests \u00b7 21"))
        self.assertEqual(summary(found), HEADS)


class AgainstTheEmulator(unittest.TestCase):
    def card(self):
        """The example show with a card of nested folders: `a.odrg` loose, `night/comet.odrg`,
        `night/deep/x.odrg`, `only/sub/y.odrg`, and an empty folder that is no group."""
        folder = entered(self, emulator_support.example_show())
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        animation = (folder / "hello.odrg").read_bytes()
        emulator_support.installed(top / "odrig", {"a.odrg": animation})
        emulator_support.installed(top / "odrig" / "night", {"comet.odrg": animation})
        emulator_support.installed(top / "odrig" / "night" / "deep", {"x.odrg": animation})
        emulator_support.installed(top / "odrig" / "only" / "sub", {"y.odrg": animation})
        (top / "odrig" / "empty").mkdir()
        emulator = entered(self, emulator_support.Emulator(folder, "--drive", top))
        deadline = time.monotonic() + 15
        while len(json.loads(emulator.command("list"))["items"]) < 10 and time.monotonic() < deadline:
            time.sleep(0.1)
        items = json.loads(emulator.command("list"))["items"]
        folders = {item["playlist"]: item["id"] for item in items if "playlist" in item}
        return emulator, top, folders

    def test_play_this_folder_on_a_folder_and_on_the_root_and_a_row_outside_the_folder(self):
        emulator, _, folders = self.card()
        night = folders["night"]
        presses = [
            {"pressIn": '[data-group="night"]', "until": "Playlist night \u00b7 2[34] h [0-9]+ min left"},
            {"row": 1, "until": "Playlist night, the root plays for now \u00b7 2[34] h [0-9]+ min left"},
            {"pressIn": "#root-head", "until": "Now 1 hello\\.odrg Playlist \u00b7 2[34] h [0-9]+ min left"},
        ]
        found = support.run("folders", address=f"127.0.0.1:{emulator.port}", settings={"rows": 6, "heads": 5, "presses": presses}).seen
        self.assertEqual(summary(found["first"]), [("", None, "Root \u00b7 3"), ("night", night, "night \u00b7 1"), ("night/deep", folders["night/deep"], "night/deep \u00b7 1"),
                                                   ("only", folders["only"], "only \u00b7 0"), ("only/sub", folders["only/sub"], "only/sub \u00b7 1")])
        # The example show begins with its cycle: no group is marked until a playlist is chosen.
        self.assertEqual((found["first"]["playing"], [head["marked"] for head in found["first"]["heads"]]), ("Cycle 3", [False] * 5))
        chosen, jumped, root = found["steps"]
        self.assertEqual([head["group"] for head in chosen["heads"] if head["marked"]], ["night"])
        self.assertEqual([row["id"] for row in chosen["rows"] if row["marked"]], [60002])
        self.assertEqual([head["group"] for head in jumped["heads"] if head["marked"]], ["night"])
        self.assertEqual([row["id"] for row in jumped["rows"] if row["marked"]], [1])
        self.assertEqual([head["group"] for head in root["heads"] if head["marked"]], [""])
        status = emulator.status()
        self.assertEqual((status["playing"], status["animation"]), ("all", 1))

    def test_the_card_out_and_in(self):
        emulator, top, folders = self.card()
        self.assertEqual(json.loads(emulator.command(f"play {folders['night']}")), {"ok": True})

        def pull():
            shutil.move(str(top / "odrig"), str(top / "away"))

        def plug():
            shutil.move(str(top / "away"), str(top / "odrig"))
        settings = {"rows": 6, "heads": 5, "until": "Playlist night", "card": {"outRows": 2, "heads": 5, "until": "Playlist night"}}
        found = support.run("folders", address=f"127.0.0.1:{emulator.port}", settings=settings, steps=[pull, plug]).seen
        self.assertEqual(found["out"]["playing"], "Playlist")
        self.assertEqual(summary(found["out"]), [("", None, "Root \u00b7 2")])
        self.assertEqual([head["marked"] for head in found["out"]["heads"]], [True])
        # The root plays in the folder's place until the turn in progress ends.
        self.assertRegex(found["back"]["playing"], r"\APlaylist night(, the root plays for now)? \u00b7 2[34] h [0-9]+ min left\Z")
        self.assertEqual([head["group"] for head in found["back"]["heads"]], ["", "night", "night/deep", "only", "only/sub"])
        self.assertEqual([head["group"] for head in found["back"]["heads"] if head["marked"]], ["night"])


if __name__ == "__main__":
    unittest.main()

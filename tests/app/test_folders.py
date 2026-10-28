"""The card's folders on Animations, as a file explorer shows them: one level at a time,
each read when it is entered, the root's rows and the folder rows with their counts,
entering a folder and Back, the heading of a level with its button, the marks of the
current playlist, and the line that says what plays with the time left."""

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


def external(id_, file):
    return {"id": id_, "file": file, "bytes": 1000, "external": True}


# A card of two loose files and the folders `night`, `night/deep` and `only`, which has a
# file in its sub-folder `only/sub` and none of its own, level by level as `list` and `list
# in` give them: the show's items at the root, then a level's folders, then its files.
LEVELS = {
    None: [{"id": 1, "file": "one.odrg", "bytes": 1000, "ignored": False, "external": False},
           {"id": 2, "file": "two.odrg", "bytes": 1000, "ignored": False, "external": False},
           {"id": 60007, "playlist": "night", "external": True, "files": 2}, {"id": 60009, "playlist": "only", "external": True, "files": 0},
           external(60001, "a.odrg"), external(60002, "b.odrg")],
    60007: [{"id": 60008, "playlist": "night/deep", "external": True, "files": 1}, external(60003, "night/comet.odrg"), external(60004, "night/zeta.odrg")],
    60008: [external(60005, "night/deep/x.odrg")],
    60009: [{"id": 60010, "playlist": "only/sub", "external": True, "files": 1}],
    60010: [external(60006, "only/sub/y.odrg")],
}
FILES = {item["id"]: item["file"] for items in LEVELS.values() for item in items if "file" in item}
PATHS = {item["id"]: item["playlist"] for items in LEVELS.values() for item in items if "playlist" in item}
SPACE = (200, '{"ok":true,"free":8372224,"total":10354688,"animations":2,"external":{"present":true,"free":1000000,"total":2000000,"read_only":true}}\n')


def level_of(line, words):
    """The level a line of `list` or `order get` names: None for the root, else the folder's
    id after `in`."""
    rest = line.decode("ascii").split(" ")[words:]
    return int(rest[1]) if rest[:1] == ["in"] else None


def answer(value):
    return (200, json.dumps(value) + "\n")


def listing(levels=None):
    """`list` and `list in` of the card's levels, `unknown-id` for a folder that is no more."""
    def listed(line):
        level = level_of(line, 1)
        found = (levels or LEVELS).get(level)
        if found is None:
            return answer({"ok": False, "error": "unknown-id"})
        return answer({"ok": True, "items": found, "next": None})
    return listed


def ordering(levels=None):
    """`order get` and `order get in` of the card's levels: each level's animations as listed."""
    def ordered(line):
        level = level_of(line, 2)
        found = (levels or LEVELS).get(level)
        if found is None:
            return answer({"ok": False, "error": "unknown-id"})
        ids = [item["id"] for item in found if "file" in item]
        return answer({"ok": True, "ids": ids, "next": None, "revision": 3 + (level or 0)})
    return ordered


def status(playing, animation, left=83520, playlist=None):
    """A status reply that plays this, with so many seconds left in the window, naming the
    file on the LEDs and the path of a folder that plays."""
    value = {"ok": True, "on": True, "brightness": 128, "playing": playing, "animation": animation, "fps": 50, "error": None,
             "file": FILES.get(animation), "playlist": playlist if playlist is not None else PATHS.get(playing)}
    if left is not None:
        value["left"] = left
    return answer(value)


def target(playing, animation, left=83520, **more):
    return support.StandIn({"status": status(playing, animation, left), "list": listing(), "order": ordering(), "space": SPACE, "play": OK, **more})


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
        self.assertEqual(found["buttons"][:2], ["LEDs on or off", "Collapse the panel"])
        for gone in ("On", "Off", "Add animation", "Select"):
            self.assertNotIn(gone, found["buttons"])
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
            ((60099, 1, 83520), "Playlist new, the root plays for now \u00b7 23 h 12 min left", {"level": False, "folders": []}),
        ]
        for (playing, animation, left), words, marks in cases:
            with self.subTest(playing=playing, animation=animation, left=left):
                with target(playing, animation, left, status=status(playing, animation, left, "new" if playing == 60099 else None)) as stand_in:
                    found = support.run("folders", address=stand_in.address, settings={"rows": 4, "folders": 2, "wait": 2500 if playing == 60099 else 0}).seen["first"]
                    lists = [line for _, line in stand_in.lines if line.startswith(b"list")]
                self.assertEqual(found["playing"], words)
                self.assertEqual({key: marked(found)[key] for key in marks}, marks)
                if playing == 60099:
                    # A playlist the list does not hold: the list is asked for again at once.
                    self.assertGreaterEqual(len(lists), 2)

    def test_a_cycle_and_a_card_without_folders_read_as_before(self):
        flat = {"ok": True, "items": [{"id": 1, "file": "one.odrg", "bytes": 1000, "ignored": False}, {"id": 3, "cycle": [1], "seconds": 5}], "next": None}
        self.assertEqual(json.loads(status(3, 1)[1])["playlist"], None)
        with support.StandIn({"status": status(3, 1), "list": (200, json.dumps(flat) + "\n"), "space": SPACE}) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 1}).seen["first"]
        self.assertEqual((found["playing"], found["level"], folders(found)), ("Cycle 3", {"title": "Root", "back": False, "marked": False, "button": "Play this folder"}, []))
        with support.StandIn({"status": status("all", 1), "list": (200, json.dumps(flat) + "\n"), "space": SPACE}) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 1}).seen["first"]
        self.assertEqual((found["playing"], found["level"]["marked"]), ("Playlist", True))

    def test_a_folder_gone_brings_the_list_to_the_root(self):
        # The folder's list after the card was changed answers `unknown-id`: the list shown
        # comes back to the root, as it does for a new target and for the card out.
        flat = {None: [item for item in LEVELS[None] if "playlist" not in item]}
        asked = []

        def listed(line):
            asked.append(line)
            return listing(LEVELS if len(asked) < 3 else flat)(line)
        steps = [{"enter": "night", "level": "night", "rows": 2}, {"level": "Root", "rows": 4, "wait": 100}]
        with support.StandIn({"status": status(60007, 60003), "list": listed, "order": ordering(), "space": SPACE}) as stand_in:
            found = support.run("folders", address=stand_in.address, settings={"rows": 4, "folders": 2, "steps": steps}).seen
        inside, root = found["steps"]
        self.assertEqual((inside["level"]["title"], ids(inside)), ("night", [60003, 60004]))
        self.assertEqual((root["level"]["title"], root["level"]["back"], ids(root), folders(root)), ("Root", False, [1, 2, 60001, 60002], []))

    def test_a_level_is_read_when_it_is_entered_and_no_other_is_asked_for(self):
        steps = [{"enter": "night", "level": "night", "rows": 2}, {"enter": "night/deep", "level": "night/deep", "rows": 1}, {"back": True, "level": "night", "rows": 2}]
        with target(60007, 60003) as stand_in:
            support.run("folders", address=stand_in.address, settings={"rows": 4, "folders": 2, "steps": steps})
            lists = [line.decode("ascii") for _, line in stand_in.lines if line.startswith((b"list", b"order get"))]
        self.assertEqual({line.split(" in ")[1].split(" ")[0] for line in lists if " in " in line}, {"60007", "60008"})
        self.assertTrue(all(line.startswith(("list 0", "order get")) or " in 6000" in line for line in lists))
        self.assertLess(lists.index("list in 60007 0"), lists.index("list in 60008 0"))

    def test_the_tests_group_stays_above_the_list_untouched(self):
        mapping = (200, json.dumps({"ok": True, "editable": True, "pins": list(range(1, 19)) + [21, 47], "revision": 1, "test": False, "snake": None}))
        with target(60007, 60003, mapping=mapping) as stand_in:
            steps = [{"enter": "night", "level": "night", "rows": 2}, {"back": True, "level": "Root", "rows": 4}, {"enter": "only", "level": "only", "rows": 0}]
            found = support.run("folders", address=stand_in.address, settings={"rows": 4, "folders": 2, "tests": True, "steps": steps}).seen
        self.assertEqual((found["first"]["tests"], found["first"]["testsHead"]), (21, "Tests \u00b7 21"))
        self.assertEqual((found["steps"][0]["tests"], found["steps"][0]["testsHead"]), (21, "Tests \u00b7 21"))
        # The note under the list speaks of the level: a level with one row or none does
        # not invite a move.
        invitation = "Hold a row to move it, or use Move up and Move down in its menu."
        self.assertEqual([step["orderNote"] for step in (found["first"], *found["steps"])], [invitation, invitation, invitation, ""])


class WithACard:
    """A test with the example show and a card of nested folders in the emulator."""

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
        # The levels grow as the card's files are read: the root's, with the show's three
        # items, two folders and its file; `night`'s, with its folder and its files.
        deadline = time.monotonic() + 15
        while len(json.loads(emulator.command("list"))["items"]) < 6 and time.monotonic() < deadline:
            time.sleep(0.1)
        folders_ = {item["playlist"]: item["id"] for item in json.loads(emulator.command("list"))["items"] if "playlist" in item}
        while len(json.loads(emulator.command(f"list in {folders_['night']}"))["items"]) < (3 if zeta else 2) and time.monotonic() < deadline:
            time.sleep(0.1)
        for path in ("night", "only"):
            folders_.update({item["playlist"]: item["id"] for item in json.loads(emulator.command(f"list in {folders_[path]}"))["items"] if "playlist" in item})
        return emulator, top, folders_


class AgainstTheEmulator(WithACard, unittest.TestCase):
    def test_play_this_folder_inside_a_folder_and_at_the_root_and_a_row_outside_the_folder(self):
        emulator, _, folders_ = self.card()
        night = folders_["night"]
        steps = [
            {"enter": "night", "level": "night", "rows": 1},
            {"top": True, "line": "^Playlist night \u00b7 2[34] h [0-9]+ min left$"},
            {"back": True, "level": "Root", "rows": 3},
            {"row": 1, "line": "^Playlist night, the root plays for now \u00b7 2[34] h [0-9]+ min left$"},
            {"top": True, "until": "Now 1 hello\\.odrg", "line": "^Playlist \u00b7 2[34] h [0-9]+ min left$"},
        ]
        found = support.run("folders", address=f"127.0.0.1:{emulator.port}", settings={"rows": 3, "folders": 2, "steps": steps}).seen
        # The example show begins with its cycle of 1 and 2, 15 s each: no playlist is
        # marked, the row on the LEDs is.
        self.assertEqual(found["first"]["playing"], "Cycle 3")
        self.assertEqual(ids(found["first"]), [1, 2, 60001])
        self.assertEqual(folders(found["first"]), [("night", night, "1 animation"), ("only", folders_["only"], "0 animations")])
        self.assertEqual((marked(found["first"])["level"], marked(found["first"])["folders"]), (False, []))
        self.assertIn(marked(found["first"])["rows"], ([1], [2]))
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
        steps = [{"enter": "night", "level": "night", "rows": 1}, {"step": True, "level": "Root", "rows": 2, "wait": 500}, {"step": True, "line": "^Playlist night", "rows": 3, "wait": 500}]
        found = support.run("folders", address=f"127.0.0.1:{emulator.port}", settings={"rows": 3, "folders": 2, "line": "^Playlist night", "steps": steps}, steps=[pull, plug]).seen
        inside, out, back = found["steps"]
        self.assertEqual((inside["level"]["title"], marked(inside)["level"]), ("night", True))
        self.assertEqual((out["level"]["title"], out["level"]["back"], ids(out), folders(out), out["playing"]), ("Root", False, [1, 2], [], "Playlist"))
        self.assertEqual(marked(out), {"level": True, "folders": [], "rows": [1]})
        self.assertRegex(back["playing"], r"\APlaylist night(, the root plays for now)? \u00b7 2[34] h [0-9]+ min left\Z")
        self.assertEqual(([folder["path"] for folder in back["folders"]], marked(back)["folders"]), (["night", "only"], ["night"]))


class WithinTheLevel(WithACard, unittest.TestCase):
    def root_order(self, emulator):
        reply = json.loads(emulator.command("order get"))
        return reply["ids"], reply["revision"]

    def test_move_up_and_move_down_stay_within_the_level(self):
        emulator, _, _ = self.card(zeta=True)
        address = f"127.0.0.1:{emulator.port}"
        # At the root the first row cannot move up and the card's file, the last, cannot move
        # down; the first moved down goes after the second. Inside `night`, comet (60002)
        # cannot move up and zeta (60003) cannot move down.
        steps = [{"menus": [1, 60001]}, {"menu": [1, "Move down", [2, 1, 60001]], "rows": 3}, {"enter": "night", "level": "night", "rows": 2},
                 {"menus": [60002, 60003]}]
        found = support.run("folders", address=address, settings={"rows": 3, "folders": 2, "steps": steps}).seen
        self.assertEqual(found["steps"][0]["menus"]["1"][:3], ["Ignore in playlist", "Move up (disabled)", "Move down"])
        self.assertEqual(found["steps"][0]["menus"]["60001"][:2], ["Move up", "Move down (disabled)"])
        self.assertEqual(ids(found["steps"][1]), [2, 1, 60001])
        self.assertEqual(self.root_order(emulator)[0], [2, 1, 60001])
        self.assertEqual(found["steps"][3]["menus"]["60002"][:2], ["Move up (disabled)", "Move down"])
        self.assertEqual(found["steps"][3]["menus"]["60003"][:2], ["Move up", "Move down (disabled)"])
        support.run("folders", address=address, settings={"rows": 3, "folders": 2, "steps": [{"menu": [1, "Move up", [1, 2, 60001]], "rows": 3}]})
        self.assertEqual(self.root_order(emulator)[0], [1, 2, 60001])

    def test_a_drag_lands_within_the_level_and_a_drop_in_place_sends_nothing(self):
        emulator, _, _ = self.card(zeta=True)
        address = f"127.0.0.1:{emulator.port}"
        _, revision = self.root_order(emulator)
        # At the root the second row dragged to the top of the first lands before it; then
        # dragged to the top of the card's file it lands before it, last of the show's
        # animations; dragged there again it stays where it is and sends nothing, and a row
        # brought back where it began sends nothing either.
        steps = [{"drag": {"id": 2, "to": 1, "expected": [2, 1, 60001]}}]
        first, = support.run("folders", address=address, settings={"rows": 3, "folders": 2, "steps": steps}).seen["steps"]
        self.assertEqual((first["landing"], ids(first)), ({"lifted": True, "before": 1}, [2, 1, 60001]))
        ids_, moved = self.root_order(emulator)
        self.assertEqual(ids_, [2, 1, 60001])
        self.assertNotEqual(moved, revision)
        steps = [{"drag": {"id": 2, "to": 60001, "expected": [1, 2, 60001]}}]
        second, = support.run("folders", address=address, settings={"rows": 3, "folders": 2, "steps": steps}).seen["steps"]
        self.assertEqual((second["landing"], ids(second)), ({"lifted": True, "before": 60001}, [1, 2, 60001]))
        ids_, moved_again = self.root_order(emulator)
        self.assertEqual(ids_, [1, 2, 60001])
        self.assertNotEqual(moved_again, moved)
        steps = [{"drag": {"id": 2, "to": 60001, "expected": [1, 2, 60001]}}, {"back_drag": {"id": 1, "to": 2}}]
        third, back = support.run("folders", address=address, settings={"rows": 3, "folders": 2, "steps": steps}).seen["steps"]
        self.assertEqual(ids(third), [1, 2, 60001])
        self.assertEqual(ids(back), [1, 2, 60001])
        self.assertEqual(self.root_order(emulator), (ids_, moved_again))

    def test_the_filters_count_the_levels_rows_and_leave_the_folder_rows_and_selection_takes_the_levels_rows(self):
        emulator, _, folders_ = self.card()
        address = f"127.0.0.1:{emulator.port}"
        steps = [{"filter": ["storage", "Internal"]}, {"filter": ["storage", "All"]}, {"select": [1, 2, 60002]},
                 {"enter": "night", "level": "night", "rows": 1}, {"filter": ["storage", "Internal"]}, {"filter": ["storage", "External"]},
                 {"filter": ["storage", "All"]}, {"select": [1, 2, 60002]}]
        found = support.run("folders", address=address, settings={"rows": 3, "folders": 2, "steps": steps}).seen
        root_internal, _, root_select, _, night_internal, night_external, _, night_select = found["steps"]
        self.assertEqual(root_internal["filters"]["storage"], ["All 3", "Internal 2", "External 1"])
        self.assertEqual((ids(root_internal), [(folder["path"], folder["shown"]) for folder in root_internal["folders"]]), ([1, 2], [("night", True), ("only", True)]))
        self.assertEqual((root_select["selected"], root_select["held"], root_select["offered"]), ([1, 2], [1, 2], True))
        self.assertEqual(night_internal["filters"]["storage"], ["All 1", "Internal 0", "External 1"])
        self.assertEqual((ids(night_internal), [(folder["path"], folder["shown"]) for folder in night_internal["folders"]], night_internal["filterEmpty"]),
                         ([], [("night/deep", True)], "No animation matches the filters.\nShow all"))
        self.assertEqual(night_internal["orderNote"], "")
        self.assertEqual((ids(night_external), night_external["filterEmpty"]), ([60002], None))
        self.assertEqual((night_select["selected"], night_select["held"], night_select["offered"]), ([], [], False))
        # A card without a catalog is not counted: the list holds one level of it.
        self.assertTrue(found["first"]["externalLine"].startswith("External storage: free "), found["first"]["externalLine"])


if __name__ == "__main__":
    unittest.main()

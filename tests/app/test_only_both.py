"""Clocks only on a target that plays the clocks of both storages, in the shared app: the
Clocks level of the root's two Clocks folders, whose Back stops there; the folders of the
board's own Clocks subtree browsed, played and uploaded into as the card's, by the single
upload, the batch and the archive, each offering only the storage of the folder explored; no
upload at the Clocks level; the line of the animation playing now with its storage, and the
Clocks folder of that storage marked; the words of an upload Only stopped; moves kept on the
phone, those that moved nothing ended in Only and the others finished once it is left; and a
target without `clock_storage`, whose Clocks only holds the card's Clocks folder alone, with
its own words."""

import io
import json
import pathlib
import tempfile
import time
import unittest
import zipfile

from odrig import catalog

from tests.core import support as core_support
from tests.core.test_clock_modes import mode_file
from tests.core.test_clocks import clock_of
from tests.emulator import support as emulator_support
from . import support
from .test_clock_modes import ModeTarget
from .test_target import entered

# The board's folders: `clocks` (number 1, id 20) and `clocks/message` (2, 21).
FOLDERS = "odrig-folders 1 3\n1 20 0 clocks\n2 21 0 clocks/message\n"
ONLY_BOTH = "Clocks only: choose a folder inside Clocks, a writable one on the card, or leave this mode in Settings."


def clip(seed):
    return core_support.clip(seed, 60, 6, durations=(20,) * 3, compressed=False)


def zipped(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries:
            archive.writestr(zipfile.ZipInfo(name, (2026, 11, 9, 0, 0, 0)), data)
    return buffer.getvalue()


class Board:
    """A board whose own storage has `root.odrg` at the root, the face `clocks/face.odrg`
    (id 2) and the message `clocks/message/m.odrg` (id 3), and a card with the face
    `clocks/cface.odrg` and `outside.odrg`, in the emulator behind a stand-in that keeps the
    lines the app sends."""

    def __init__(self, test, mode="off"):
        self.test = test
        top = pathlib.Path(entered(test, tempfile.TemporaryDirectory()))
        self.folder = emulator_support.installed(top / "show", {
            "mapping.json": core_support.mapping_texts()["legs-2"],
            "show.json": json.dumps({"version": 1, "brightness": 32, "items": [
                {"id": 1, "file": "root.odrg"}, {"id": 2, "file": "1/face.odrg"}, {"id": 3, "file": "2/m.odrg"}]}),
            "folders.txt": FOLDERS,
            "clocks.txt": mode_file(mode),
            "root.odrg": clip(1),
        })
        # The message's loop lasts long enough for a status to name its turn.
        message = core_support.clip(3, 60, 6, durations=(1500,) * 3, compressed=False)
        for name, data in (("1/face.odrg", clock_of(canvas=(60, 6))), ("2/m.odrg", message)):
            path = self.folder.joinpath(*name.split("/"))
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(data)
        card = top / "card" / "odrig"
        drive = {"clocks/cface.odrg": clock_of(canvas=(60, 6)), "outside.odrg": clip(5)}
        for name, data in drive.items():
            path = card.joinpath(*name.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        _, refused = catalog.rebuild(catalog.Storage(card, drive=True), names=sorted(drive), canvas=(60, 6))
        test.assertEqual(refused, [])
        self.emulator = entered(test, emulator_support.Emulator(self.folder, "--drive", top / "card"))
        root = self.answered("list", lambda reply: any(row.get("external") for row in reply.get("items", [])))["items"]
        self.card_clocks = next(row["id"] for row in root if row.get("playlist") == "clocks" and row["external"])
        self.card_face = next(row["id"] for row in json.loads(self.emulator.command(f"list in {self.card_clocks}"))["items"] if "file" in row)
        # A function of each line, called before the line goes to the emulator.
        self.before = None
        self.proxy = entered(test, support.StandIn(self.relay))
        self.address = self.proxy.address

    def relay(self, line):
        text = line.decode("utf-8")
        if self.before is not None:
            self.before(text)
        return 200, self.emulator.command(text).decode("utf-8")

    def only_at_upload(self):
        """Clocks only is chosen, as by another controller, as the first upload begins, and the
        upload's beginning answered after the app's next status is due."""
        def before(text):
            if text.startswith("upload begin"):
                self.before = None
                self.test.assertEqual(json.loads(self.emulator.command("clocks only")), {"ok": True})
                time.sleep(1.2)
        self.before = before

    def answered(self, line, wanted):
        for _ in range(200):
            reply = json.loads(self.emulator.command(line))
            if wanted(reply):
                return reply
            time.sleep(0.05)
        raise AssertionError(f"{line} never answered as wanted: {reply}")

    def lines(self, word):
        return [line.decode() for _, line in self.proxy.lines if line.startswith(word.encode())]


def run(address, acts, rows=0, media=None, steps=()):
    return support.run("only-both", address=address, settings={"rows": rows, "acts": acts}, media=media, steps=steps).seen


class OnTheEmulator(unittest.TestCase):
    def test_only_opens_the_clocks_level_whose_back_stops_there_and_both_subtrees_are_browsed_and_played(self):
        board = Board(self)
        acts = [{"mode": "only", "until": {"screen": "animations", "level": "Clocks", "folders": 2}, "look": "level"},
                {"enter": 20, "until": {"level": "clocks", "files": ["clocks/face.odrg"]}, "look": "internal"},
                {"enter": 21, "until": {"level": "clocks/message", "files": ["clocks/message/m.odrg"]}, "look": "message"},
                {"play": 3, "wait": 400},
                {"back": True, "until": {"level": "clocks"}},
                {"back": True, "until": {"level": "Clocks", "folders": 2}, "look": "again"},
                {"enter": board.card_clocks, "until": {"level": "clocks", "files": ["clocks/cface.odrg"]}, "look": "card"},
                {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"restart": True, "wait": 400}]
        seen = run(board.address, acts, rows=2)
        level = seen["level"]
        self.assertEqual([(row["name"], row["storage"], row["id"]) for row in level["folders"]],
                         [("Internal /clocks", "internal", 20), ("External /clocks", "external", board.card_clocks)])
        self.assertEqual([row["label"] for row in level["folders"]], ["Open folder Internal /clocks", "Open folder External /clocks"])
        self.assertTrue(all(row["open"] for row in level["folders"]))
        self.assertTrue(level["backHidden"])
        self.assertEqual(level["rows"], [])
        self.assertEqual(level["restart"], {"text": "Restart clocks", "disabled": False})
        self.assertIn("Browsing stays inside Clocks", level["boundary"])
        internal = seen["internal"]
        self.assertFalse(internal["backHidden"])
        self.assertEqual([(row["name"], row["storage"]) for row in internal["folders"]], [("message", "internal")])
        self.assertEqual(internal["rows"], [{"id": 2, "file": "clocks/face.odrg", "external": False, "disabled": False}])
        self.assertEqual(seen["message"]["rows"], [{"id": 3, "file": "clocks/message/m.odrg", "external": False, "disabled": False}])
        self.assertTrue(seen["again"]["backHidden"])
        self.assertEqual(seen["card"]["rows"], [{"id": board.card_face, "file": "clocks/cface.odrg", "external": True, "disabled": False}])
        self.assertFalse(seen["card"]["backHidden"])
        self.assertEqual(board.lines("play"), ["play 3", f"play {board.card_clocks}"])
        self.assertEqual(json.loads(board.emulator.command("status"))["clock_mode"], "only")

    def test_a_start_in_only_opens_the_folder_the_status_names_and_puts_the_clocks_level_under_it(self):
        board = Board(self, "only")
        acts = [{"until": {"backHidden": False}, "look": "under"},
                {"back": True, "until": {"level": "Clocks", "folders": 2}, "look": "level"}]
        seen = run(board.address, acts, rows=1)
        self.assertEqual(seen["first"]["level"], "clocks")
        self.assertEqual([row["file"] for row in seen["first"]["rows"]], ["clocks/cface.odrg"])
        self.assertEqual(seen["under"]["level"], "clocks")
        self.assertEqual([row["file"] for row in seen["under"]["rows"]], ["clocks/cface.odrg"])
        self.assertEqual([row["name"] for row in seen["level"]["folders"]], ["Internal /clocks", "External /clocks"])
        self.assertTrue(seen["level"]["backHidden"])
        self.assertEqual(board.lines("play"), [])

    def test_an_upload_goes_into_the_boards_message_folder_and_none_is_taken_at_the_clocks_level(self):
        board = Board(self, "only")
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media / "ready.odrg").write_bytes(clip(7))
        acts = [{"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"upload": {"file": "ready.odrg", "as": "level"}},
                {"enter": 20, "until": {"level": "clocks", "rows": 1}},
                {"enter": 21, "until": {"level": "clocks/message", "rows": 1}},
                {"upload": {"file": "ready.odrg", "store": "external", "send": True, "as": "inside"}},
                {"until": {"files": ["clocks/message/m.odrg", "clocks/message/ready.odrg"]}, "within": 20000, "look": "listed"}]
        seen = run(board.address, acts, rows=1, media=media)
        level = seen["level"]
        self.assertTrue(level["uploadDisabled"])
        self.assertEqual(level["reason"], ONLY_BOTH)
        self.assertTrue(level["internalDisabled"])
        inside = seen["inside"]
        self.assertEqual((inside["storage"], inside["externalDisabled"], inside["internalDisabled"], inside["uploadDisabled"]), ("internal", True, False, False))
        self.assertEqual(inside["stored"], "internal")
        self.assertEqual(inside["destination"], "Internal /clocks/message/ready.odrg")
        self.assertIn("Uploaded as animation 4 clocks/message/ready.odrg", inside["message"])
        self.assertEqual((board.folder / "2" / "ready.odrg").read_bytes(), clip(7))
        self.assertFalse((board.folder / "ready.odrg").exists())
        self.assertEqual(len(board.lines("upload begin ")), 1)

    def test_a_batch_and_an_archive_go_into_the_boards_message_folder_with_only_that_storage_offered(self):
        board = Board(self, "only")
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media / "a.odrg").write_bytes(clip(7))
        (media / "b.odrg").write_bytes(clip(8))
        (media / "set.png").write_bytes(zipped([("x/c.odrg", clip(9)), ("d.odrg", clip(10))]))
        acts = [{"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"enter": 20, "until": {"level": "clocks", "rows": 1}},
                {"enter": 21, "until": {"level": "clocks/message", "rows": 1}},
                {"batch": {"files": ["a.odrg", "b.odrg"], "send": True, "as": "batch"}},
                {"archive": {"zip": ["set.png", "set.zip"], "send": True, "as": "archive"}}]
        seen = run(board.address, acts, rows=1, media=media)
        batch = seen["batch"]
        self.assertEqual((batch["storage"], batch["externalDisabled"], batch["internalDisabled"]), ("internal", True, False))
        self.assertEqual(batch["destination"], "Internal /clocks/message/")
        self.assertEqual(batch["rows"], ["uploaded as animation 4", "uploaded as animation 5"])
        archive = seen["archive"]
        self.assertEqual((archive["storage"], archive["externalDisabled"], archive["internalDisabled"]), ("internal", True, False))
        self.assertEqual(archive["names"], ["c.odrg", "d.odrg"])
        self.assertEqual(archive["rows"], ["uploaded as animation 6", "uploaded as animation 7"])
        for name, seed in (("a.odrg", 7), ("b.odrg", 8), ("c.odrg", 9), ("d.odrg", 10)):
            self.assertEqual((board.folder / "2" / name).read_bytes(), clip(seed), name)
            self.assertFalse((board.folder / name).exists(), name)

    def test_neither_a_batch_nor_an_archive_is_taken_at_the_clocks_level(self):
        board = Board(self, "only")
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media / "a.odrg").write_bytes(clip(7))
        (media / "b.odrg").write_bytes(clip(8))
        (media / "set.png").write_bytes(zipped([("c.odrg", clip(9))]))
        acts = [{"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"batch": {"files": ["a.odrg", "b.odrg"], "as": "batch"}},
                {"archive": {"zip": ["set.png", "set.zip"], "as": "archive"}}]
        seen = run(board.address, acts, rows=1, media=media)
        for kind in ("batch", "archive"):
            self.assertTrue(seen[kind]["disabled"], kind)
            self.assertEqual(seen[kind]["reason"], ONLY_BOTH, kind)
            self.assertTrue(seen[kind]["internalDisabled"], kind)
        self.assertEqual(board.lines("upload begin "), [])

    def test_the_line_of_the_animation_playing_now_names_the_storage_of_a_clocks_file(self):
        board = Board(self, "only")
        acts = [{"play": board.card_face, "until": {"now": f"Now {board.card_face} External /clocks/cface.odrg"}, "look": "card"},
                {"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"enter": 20, "until": {"level": "clocks", "rows": 1}}, {"enter": 21, "until": {"level": "clocks/message", "rows": 1}},
                {"play": 3, "until": {"now": "Now 3 Internal /clocks/message/m.odrg"}, "look": "internal"}]
        seen = run(board.address, acts, rows=1)
        self.assertEqual(seen["card"]["file"], f"Animation {board.card_face}: External /clocks/cface.odrg")
        self.assertEqual(seen["internal"]["file"], "Animation 3: Internal /clocks/message/m.odrg")

    def test_a_text_whose_upload_clocks_only_stopped_is_said_in_the_words_of_both_storages(self):
        board = Board(self)
        board.only_at_upload()
        seen = support.run("author-text", address=board.address,
                           settings={"rows": 2, "fields": [["text-words", "Hi"], ["text-motion", "up"]], "upload": True, "listed": False}).seen
        self.assertEqual(seen["message"], f"{ONLY_BOTH} (in-use)")
        self.assertEqual(json.loads(board.emulator.command("status"))["clock_mode"], "only")
        self.assertEqual(len(board.lines("upload begin ")), 1)
        self.assertEqual(board.lines("upload cancel"), ["upload cancel"])

    def test_a_move_that_clocks_only_stopped_is_said_in_the_words_of_both_storages(self):
        board = Board(self)
        board.only_at_upload()
        seen = support.run("explore", address=board.address, settings={"rows": 2, "folder": "night", "id": 1, "ends": "Moved 0 of 1"}).seen
        self.assertEqual(seen["message"], f"Moved 0 of 1. Failed 1: root.odrg: {ONLY_BOTH} (in-use).")
        self.assertTrue((board.folder / "root.odrg").exists())

    def test_move_to_offers_the_clocks_folders_of_both_storages_alone_and_a_face_moved_stays_inside(self):
        board = Board(self, "only")
        acts = [{"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"enter": 20, "until": {"level": "clocks", "files": ["clocks/face.odrg"]}},
                {"move": {"as": "offered", "rows": [2]}},
                {"move": {"as": "moved", "rows": [2], "storage": "external", "folder": "clocks"}}]
        seen = run(board.address, acts, rows=1)
        self.assertEqual(seen["offered"]["storages"], {"external": {"disabled": False, "folders": ["clocks"]},
                                                       "internal": {"disabled": False, "folders": ["clocks", "clocks/message"]}})
        self.assertEqual(seen["moved"]["message"], "Moved 1 of 1.")
        card = board.folder.parent / "card" / "odrig"
        self.assertEqual((card / "clocks" / "face.odrg").read_bytes(), clock_of(canvas=(60, 6)))
        self.assertFalse((board.folder / "1" / "face.odrg").exists())
        self.assertEqual([line for line in board.lines("upload begin ") if "clocks/" not in line], [])

    def test_a_move_out_of_clocks_that_clocks_only_stopped_once_the_dialog_was_open_sends_nothing(self):
        board = Board(self)

        def only():
            self.assertEqual(json.loads(board.emulator.command("clocks only")), {"ok": True})

        acts = [{"enter": board.card_clocks, "until": {"level": "clocks", "files": ["clocks/cface.odrg"]}},
                {"move": {"as": "moved", "rows": [board.card_face], "storage": "external", "folder": "", "step": True}}]
        seen = run(board.address, acts, rows=2, steps=[only])
        self.assertEqual(seen["moved"]["message"], f"Moved 0 of 1. Failed 1: clocks/cface.odrg: {ONLY_BOTH} (in-use).")
        self.assertEqual(board.lines("move external"), [])
        card = board.folder.parent / "card" / "odrig"
        self.assertTrue((card / "clocks" / "cface.odrg").exists())
        self.assertFalse((card / "cface.odrg").exists())

    def test_a_kept_move_that_moved_nothing_ends_in_only_and_one_that_would_take_a_file_out_waits_until_only_is_left(self):
        board = Board(self, "only")
        face = (board.folder / "1" / "face.odrg").stat().st_size
        root = (board.folder / "root.odrg").stat().st_size
        # The face moved under its own id towards the root, its upload never installed, its
        # saved brightness 20 taken; and a file whose upload under its own id did put it at the
        # root, its saved brightness 25 not given yet.
        jobs = [{"source": {"id": 2, "storage": "internal", "path": "clocks/face.odrg", "folder": "clocks", "bytes": face, "ignored": False},
                 "destination": {"storage": "internal", "folder": "", "name": "face.odrg", "path": "face.odrg"},
                 "stage": "sending", "sameId": True, "settings": {"ignored": False, "brightness": 20, "repeat": None}},
                {"source": {"id": 1, "storage": "internal", "path": "clocks/root.odrg", "folder": "clocks", "bytes": root, "ignored": False},
                 "destination": {"storage": "internal", "folder": "", "name": "root.odrg", "path": "root.odrg"},
                 "stage": "sending", "sameId": True, "settings": {"ignored": False, "brightness": 25, "repeat": None}}]
        during = {}

        def leave():
            during["saved"] = json.loads(board.emulator.command("saved 2"))["brightness"]
            during["lines"] = board.lines("brightness")
            self.assertEqual(json.loads(board.emulator.command("clocks on")), {"ok": True})

        seen = support.run("only-kept-moves", address=board.address, settings={"jobs": jobs, "kept": ["clocks/root.odrg"]}, steps=[leave]).seen
        self.assertEqual(seen["only"]["mode"], "only")
        self.assertEqual(seen["only"]["kept"], ["clocks/root.odrg"])
        self.assertEqual(during, {"saved": 20, "lines": ["brightness 2 20 save"]})
        self.assertEqual(seen["only"]["message"], "Not moved, left where they were: clocks/face.odrg.")
        self.assertEqual(seen["left"]["message"], "Finished the interrupted move of clocks/root.odrg.")
        self.assertEqual(board.lines("brightness"), ["brightness 2 20 save", "brightness 1 25 save"])
        self.assertEqual(json.loads(board.emulator.command("saved 1"))["brightness"], 25)
        self.assertTrue((board.folder / "1" / "face.odrg").exists())

    def test_an_archive_opened_in_only_keeps_its_folder_and_says_why_without_only_once_only_is_left(self):
        board = Board(self, "only")
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media / "set.png").write_bytes(zipped([("x/c.odrg", clip(9))]))
        acts = [{"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"enter": 20, "until": {"level": "clocks", "rows": 1}},
                {"enter": 21, "until": {"level": "clocks/message", "rows": 1}},
                {"archive": {"zip": ["set.png", "set.zip"], "renames": [[0, "x/c.odrg"]], "leave": "between", "as": "left"}}]
        seen = run(board.address, acts, rows=1, media=media)
        left = seen["left"]
        self.assertEqual(left["storage"], "internal")
        self.assertEqual(left["why"], ["An archive opened in a folder goes into that folder: use a name without /."])


class BothTarget(ModeTarget):
    """The stand-in of Clocks only with the folders `clocks` (id 20) and `clocks/message` (21)
    of the board's own storage beside the card's, and `clock_storage` in its status; `card`
    false gives a card without its Clocks folder. `now` names the animation and the file the
    status gives, and `storage` false makes a target that does not report `clock_storage`."""

    def __init__(self, test, mode="only", card=True, storage=True):
        self.storage = "sd" if storage else None
        self.now = None
        # The beginnings of lines answered `busy` once each.
        self.busy_once = set()
        super().__init__(test, mode)
        self.card_clocks = ([row for row in self.levels[None] if row["id"] == 60007], {level: self.levels[level] for level in (60007, 60008)})
        self.levels[None].insert(1, dict(id=20, playlist="clocks", files=1, external=False, ignored=False, inherited_ignored=False))
        self.levels[20] = [dict(id=21, playlist="clocks/message", files=1, external=False, ignored=False, inherited_ignored=False),
                           dict(id=2, file="clocks/face.odrg", bytes=100, external=False, ignored=False, inherited_ignored=False)]
        self.levels[21] = [dict(id=3, file="clocks/message/m.odrg", bytes=100, external=False, ignored=False, inherited_ignored=False)]
        if not card:
            self.drop_card_clocks()
            self.only_folder = 20

    def drop_card_clocks(self):
        self.levels[None] = [row for row in self.levels[None] if row["id"] != 60007]
        for level in (60007, 60008):
            self.levels.pop(level, None)

    def put_card_clocks(self):
        rows, levels = self.card_clocks
        self.levels[None] = self.levels[None] + [dict(row) for row in rows]
        self.levels.update({level: list(items) for level, items in levels.items()})

    def reply(self, line):
        words = line.decode().split()
        refused = next((start for start in self.busy_once if line.decode().startswith(start)), None)
        if refused is not None:
            self.busy_once.discard(refused)
            return self.answer(dict(ok=False, error="busy"))
        if words[:2] == ["list", "in"] and int(words[2]) not in self.levels:
            return self.answer(dict(ok=False, error="unknown-id"))
        if words[:2] == ["clocks", "storage"]:
            self.change_seen.set()
            if self.refusal:
                return self.answer(dict(ok=False, error=self.refusal))
            self.storage = words[2]
            return self.answer(dict(ok=True))
        status, body = super().reply(line)
        if words[0] == "status":
            reply = json.loads(body)
            if self.storage is not None:
                reply["clock_storage"] = self.storage
            if self.now is not None and reply["animation"] is not None:
                reply["animation"], reply["file"] = self.now
            if self.mode == "only" and self.only_folder == 20 and reply["animation"] == 60003:
                reply["animation"], reply["file"] = 2, "clocks/face.odrg"
            return self.answer(reply)
        return status, body


class OnAStandIn(unittest.TestCase):
    def test_the_boards_clocks_folder_alone_is_the_level_of_only(self):
        target = BothTarget(self, card=False)
        acts = [{"wait": 1500, "look": "later"},
                {"enter": 21, "until": {"level": "clocks/message", "rows": 1}, "look": "message"},
                {"play": 3, "wait": 300},
                {"back": True, "until": {"level": "clocks", "rows": 1}, "look": "back"},
                {"restart": True, "wait": 300}]
        seen = run(target.stand_in.address, acts, rows=1)
        first = seen["first"]
        self.assertEqual(first["level"], "clocks")
        self.assertTrue(first["backHidden"])
        self.assertEqual(first["rows"], [{"id": 2, "file": "clocks/face.odrg", "external": False, "disabled": False}])
        self.assertEqual([(row["name"], row["storage"], row["open"]) for row in first["folders"]], [("message", "internal", True)])
        self.assertTrue(seen["later"]["backHidden"])
        self.assertEqual(seen["later"]["level"], "clocks")
        self.assertFalse(seen["message"]["backHidden"])
        self.assertEqual(seen["message"]["rows"][0]["disabled"], False)
        self.assertTrue(seen["back"]["backHidden"])
        self.assertEqual(target.lines("play"), ["play 3", "play 20"])

    def test_a_root_list_without_the_cards_clocks_folder_takes_the_trail_to_the_boards(self):
        target = BothTarget(self)

        def pulled():
            target.drop_card_clocks()
            target.only_folder = 20
        acts = [{"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}, "look": "level"},
                {"step": True, "until": {"level": "clocks", "files": ["clocks/face.odrg"]}, "look": "remaining"},
                {"wait": 1200, "look": "later"}]
        seen = run(target.stand_in.address, acts, rows=1, steps=[pulled])
        self.assertEqual([row["id"] for row in seen["level"]["folders"]], [20, 60007])
        self.assertTrue(seen["remaining"]["backHidden"])
        self.assertEqual(seen["later"]["level"], "clocks")
        self.assertTrue(seen["later"]["backHidden"])

    def test_a_root_list_without_the_boards_clocks_folder_takes_the_clocks_level_away(self):
        target = BothTarget(self)

        def removed():
            target.levels[None] = [row for row in target.levels[None] if row["id"] != 20]
        acts = [{"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"step": True, "refresh": True, "until": {"level": "clocks", "files": ["clocks/c.odrg"]}, "look": "remaining"}]
        seen = run(target.stand_in.address, acts, rows=1, steps=[removed])
        self.assertTrue(seen["remaining"]["backHidden"])

    def test_a_gone_folder_of_the_boards_clocks_takes_only_to_the_cards_clocks_folder(self):
        target = BothTarget(self)

        def gone():
            target.levels[None] = [row for row in target.levels[None] if row["id"] != 20]
            for level in (20, 21):
                del target.levels[level]
        acts = [{"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"enter": 20, "until": {"level": "clocks", "rows": 1}},
                {"enter": 21, "until": {"level": "clocks/message", "rows": 1}},
                {"step": True, "refresh": True, "until": {"level": "clocks", "files": ["clocks/c.odrg"]}, "look": "card"}]
        seen = run(target.stand_in.address, acts, rows=1, steps=[gone])
        self.assertTrue(seen["card"]["backHidden"])
        self.assertEqual(seen["card"]["folders"][0]["storage"], "external")

    def test_a_root_list_without_the_cards_clocks_folder_before_the_status_keeps_the_boards_level_shown(self):
        target = BothTarget(self)

        def named():
            target.only_folder = 20
        acts = [{"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"enter": 20, "until": {"level": "clocks", "rows": 1}},
                {"enter": 21, "until": {"level": "clocks/message", "rows": 1}},
                {"step": True, "until": {"rootClocks": json.dumps({"internal": 20, "external": None}, separators=(",", ":"))}, "within": 20000},
                {"wait": 1500, "look": "after"},
                {"step": True, "until": {"level": "clocks", "files": ["clocks/face.odrg"]}, "look": "named"}]
        seen = run(target.stand_in.address, acts, rows=1, steps=[target.drop_card_clocks, named])
        after = seen["after"]
        self.assertEqual((after["level"], after["unavailable"], after["backHidden"]), ("clocks/message", False, False))
        self.assertEqual([row["file"] for row in after["rows"]], ["clocks/message/m.odrg"])
        self.assertEqual(after["restart"], {"text": "Restart clocks", "disabled": False})
        self.assertTrue(seen["named"]["backHidden"])
        self.assertFalse(seen["named"]["unavailable"])

    def test_a_cards_clocks_folder_put_in_while_the_boards_message_folder_is_shown_opens_the_clocks_level(self):
        target = BothTarget(self, card=False)

        def put_in():
            target.put_card_clocks()
            target.only_folder = 60007
        acts = [{"until": {"rootClocks": json.dumps({"internal": 20, "external": None}, separators=(",", ":"))}},
                {"enter": 21, "until": {"level": "clocks/message", "rows": 1}},
                {"step": True, "until": {"level": "Clocks", "folders": 2}, "look": "level"}]
        seen = run(target.stand_in.address, acts, rows=1, steps=[put_in])
        self.assertTrue(seen["level"]["backHidden"])
        self.assertEqual([row["name"] for row in seen["level"]["folders"]], ["Internal /clocks", "External /clocks"])

    def test_the_clocks_folder_of_the_storage_whose_file_plays_is_the_one_marked(self):
        target = BothTarget(self)
        target.now = (3, "clocks/message/m.odrg")
        acts = [{"until": {"backHidden": False}}, {"back": True, "until": {"level": "Clocks", "folders": 2}, "look": "level"},
                {"enter": 60007, "until": {"level": "clocks", "files": ["clocks/c.odrg"]}, "look": "card"},
                {"back": True, "until": {"level": "Clocks", "folders": 2}},
                {"enter": 20, "until": {"level": "clocks", "files": ["clocks/face.odrg"]}, "look": "board"}]
        seen = run(target.stand_in.address, acts, rows=1)
        self.assertEqual([(row["name"], row["marked"]) for row in seen["level"]["folders"]], [("Internal /clocks", True), ("External /clocks", False)])
        self.assertFalse(seen["card"]["headMarked"])
        self.assertTrue(seen["board"]["headMarked"])

    def test_turns_of_the_boards_faces_read_the_cards_clocks_folder_no_more_often(self):
        target = BothTarget(self)
        target.levels[20].append(dict(id=4, file="clocks/face4.odrg", bytes=100, external=False, ignored=False, inherited_ignored=False))
        counts = []

        def turn(now):
            def step():
                counts.append(len([line for line in target.lines("list") if line.startswith("list in 60007")]))
                if now is not None:
                    target.now = now
            return step
        turns = [(2, "clocks/face.odrg"), (4, "clocks/face4.odrg"), (2, "clocks/face.odrg"), (4, "clocks/face4.odrg"), None]
        acts = [{"until": {"backHidden": False}}, {"until": {"level": "clocks", "files": ["clocks/c.odrg"]}}]
        acts += [{"step": True, "wait": 1300} for _ in turns[:-1]] + [{"step": True}]
        run(target.stand_in.address, acts, rows=1, steps=[turn(now) for now in turns])
        # At most the one read of the list that comes every ten seconds, none for a turn of the
        # board's own faces.
        self.assertLessEqual(counts[-1] - counts[0], 1)

    def test_a_busy_answer_to_the_read_of_a_clocks_files_storage_is_asked_again(self):
        target = BothTarget(self, mode="between")
        target.busy_once = {"list in 60007"}
        steps = [lambda: setattr(target, "now", (60003, "clocks/c.odrg"))]
        acts = [{"step": True, "until": {"now": "Now 60003 External /clocks/c.odrg"}, "within": 10000, "look": "card"}]
        seen = run(target.stand_in.address, acts, rows=2, steps=steps)
        self.assertEqual(seen["card"]["file"], "Animation 60003: External /clocks/c.odrg")
        self.assertEqual(target.busy_once, set())

    def test_a_target_without_clock_storage_keeps_the_cards_clocks_folder_alone_and_its_words(self):
        target = BothTarget(self, storage=False)
        acts = [{"wait": 1500, "look": "later"}]
        seen = run(target.stand_in.address, acts, rows=1)
        for look in (seen["first"], seen["later"]):
            self.assertEqual(look["level"], "clocks")
            self.assertTrue(look["backHidden"])
            self.assertEqual([row["file"] for row in look["rows"]], ["clocks/c.odrg"])
        self.assertEqual(seen["later"]["reason"], "Only the Clocks folder plays. Browsing stays inside Clocks; leave this mode to browse elsewhere.")
        self.assertEqual(seen["later"]["now"], "Now 60003 clocks/c.odrg")
        self.assertFalse(any(line.startswith("list in 20") for line in target.lines("list")))

    def test_the_words_of_only_name_both_storages(self):
        target = BothTarget(self)
        seen = run(target.stand_in.address, [{"wait": 1200, "look": "later"}], rows=1)
        self.assertEqual(seen["later"]["reason"], "Only the clocks folders play. Browsing stays inside Clocks; leave this mode to browse elsewhere.")

    def test_the_storage_of_a_clocks_file_playing_between_the_animations_is_asked_for_once(self):
        target = BothTarget(self, mode="between")
        target.levels[20].append(dict(id=60010, file="clocks/big.odrg", bytes=100, external=False, ignored=False, inherited_ignored=False))
        steps = [lambda now=now: setattr(target, "now", now) for now in ((60003, "clocks/c.odrg"), (60010, "clocks/big.odrg"), (3, "clocks/message/m.odrg"), (60003, "clocks/c.odrg"))]
        acts = [{"step": True, "until": {"now": "Now 60003 External /clocks/c.odrg"}, "look": "card"},
                {"step": True, "until": {"now": "Now 60010 Internal /clocks/big.odrg"}, "look": "big"},
                {"step": True, "until": {"now": "Now 3 Internal /clocks/message/m.odrg"}, "look": "message"},
                {"step": True, "until": {"now": "Now 60003 External /clocks/c.odrg"}, "wait": 1200}]
        seen = run(target.stand_in.address, acts, rows=2, steps=steps)
        self.assertEqual(seen["card"]["file"], "Animation 60003: External /clocks/c.odrg")
        self.assertEqual(seen["big"]["level"], "Root")
        # The card's folder is read for each of the two files a list had not named; the board's
        # for the second; nothing for the message, whose id is the board's, nor for the first
        # file again.
        asked = [line for line in target.lines("list") if line.startswith("list in")]
        self.assertEqual(sorted(asked), ["list in 20 0", "list in 60007 0", "list in 60007 0"])

    def test_an_old_target_names_a_clocks_file_without_its_storage(self):
        target = BothTarget(self, mode="between", storage=False)
        steps = [lambda: setattr(target, "now", (60003, "clocks/c.odrg"))]
        seen = run(target.stand_in.address, [{"step": True, "wait": 1500, "look": "now"}], rows=2, steps=steps)
        self.assertEqual(seen["now"]["now"], "Now 60003 clocks/c.odrg")
        self.assertEqual(seen["now"]["file"], "Animation 60003: clocks/c.odrg")
        self.assertFalse(any(line.startswith("list in") for line in target.lines("list")))


if __name__ == "__main__":
    unittest.main()


class FolderMovesInOnly(unittest.TestCase):
    """`Rename…` and `Move to…` of a folder of the board's own storage while Clocks only is on:
    the folder stays inside Clocks, and a rename or a move that would take it out is said in
    Clocks only's words and sends nothing."""

    def test_a_rename_of_the_boards_clocks_folder_is_refused_and_sends_nothing(self):
        board = Board(self, "only")
        seen = support.run("only-folder-moves", address=board.address, settings={"id": 20, "rename": "faces"}).seen
        self.assertIn("Rename\u2026", seen["menu"])
        self.assertEqual(seen["message"], f"The folder Internal /clocks was not renamed. {ONLY_BOTH}")
        self.assertEqual(board.lines("move internal"), [])
        self.assertIn("1 20 0 clocks\n", (board.folder / "folders.txt").read_text(encoding="ascii"))

    def test_move_to_of_a_folder_inside_clocks_offers_the_clocks_folders_alone(self):
        board = Board(self, "only")
        self.assertTrue(json.loads(board.emulator.command("folder make internal clocks/old"))["made"])
        seen = support.run("only-folder-moves", address=board.address, settings={"enter": 20, "id": 21}).seen
        self.assertEqual(seen["choices"], ["/clocks \u2014 It is there already. (disabled)", "/clocks/old"])
        self.assertEqual(board.lines("move internal"), [])

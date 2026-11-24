"""A rehearsal on the emulator of the board session that puts the seven approved message
widgets into the board's own folder `clocks/message`: the session's commands, run with the
command tool over TCP against an emulator whose card has a clock face in `clocks/` and a
message of its own in `clocks/message/`, and whose board holds an animation two folders
down. It puts nothing on a board, and it is no deployment."""

import base64
import hashlib
import json
import pathlib
import tempfile
import time
import unittest

from odrig import catalog
from tests.core.test_clocks import clock_of
from tests.core.test_drive import a_drive
from tests.core.test_mini import files_for

from . import support

MESSAGES = support.ROOT / "collection" / "card" / "clocks" / "message"

# The seven message widgets as they are tracked: the size and the SHA-256 of each.
SEVEN = {
    "v7-consciousness.odrgx": (9588, "592977056b2b7473d7c7b860f9a4f1e786d9abfe4cbd16962e9954cf461fed3d"),
    "v7-symmetry.odrgx": (7737, "911f857d47a3d972d549566d54a57d794307b5e33f9be41d6becc4ebd6bb1347"),
    "v7-temperature.odrgx": (9574, "a34aada473c03d6146fcb46da9a35001e0ecadd23d77d60cc98d2844f6285487"),
    "v7-the-time.odrgx": (9594, "108fa62aabf425ca39f29dec7b6b8c9fed7457f6c16dfdc9536a49a2daa6fc0c"),
    "v7-countdown.odrgx": (22515, "8cb82ff0b2fcd2cc35fb6f3507889b633d02bacc5673bd10a1b39e2352786d6c"),
    "v7-the-clock.odrgx": (7747, "4963cc42d63ecec1dfca9f407e48dab39c6db61c08e435e405f238687d6a1256"),
    "v7-mistakes.odrgx": (12480, "4aa1bfa59dcb8ce53f136cfc9229961cac11dbd454aa6e33c26f689a665bcf1f"),
}
PATHS = {f"clocks/message/{name}" for name in SEVEN}
# The free bytes the session needs before it writes: the files, 23 blocks of 4,096 bytes,
# the two folders, an upload's staging and the catalog's records, 40 blocks in all.
ROOM = 163_840
FACE = "clocks/face.odrgx"
# A message of the card that is not one of the seven.
OLD = "clocks/message/old.odrg"
# An animation of the board two folders down, under an id that the seven would take if the
# walk of the ids in use did not go into `a/b`.
NESTED = ("a/b", "stars.odrg", 6)
# The highest id of the board's own storage; the card's ids are above it.
INTERNAL_IDS = 60_000
# The brightness the session plays at, at most.
BRIGHTNESS = 40
MODES = {"off": "off", "between": "on", "only": "only"}
STORAGES = ("sd", "internal")


def show_folder(root):
    """A show of one animation of a second on the target's canvas, at full brightness and
    with turns of a second, installed with its own catalog as the firmware tool installs
    one."""
    files = files_for()
    files["show.json"] = json.dumps({"version": 1, "brightness": 255, "min_seconds": 1, "items": [{"id": 1, "file": "picture.odrg"}]})
    storage = catalog.MemoryStorage({name: content if isinstance(content, bytes) else content.encode("utf-8") for name, content in files.items()})
    made, refused = catalog.rebuild(storage, names=["picture.odrg"], canvas=(60, 60))
    if (made.state, refused) != ("ok", []):
        raise AssertionError(f"the show's catalog: {made.state} {refused}")
    return support.installed(root / "show", storage.files)


def another_picture():
    return files_for(pixels=[[(x * 4, 200 - y * 3, 90) for x in range(60)] for y in range(60)])["picture.odrg"]


def decoded(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def kept(folder):
    """Every file under a folder, by its path from the folder."""
    return {path.relative_to(folder).as_posix(): path.read_bytes() for path in folder.rglob("*") if path.is_file()}


class TheSevenMessages(unittest.TestCase):
    def start(self, card):
        """An emulator with that card, which has its catalog as the installation's card has,
        and whose board holds the show's picture at its root and the animation `NESTED` in
        the folder `a/b` of its own storage."""
        root = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.folder = show_folder(root)
        self.top = pathlib.Path(support.entered(self, a_drive(card)))
        _, refused = catalog.rebuild(catalog.Storage(self.top / "odrig", drive=True), names=sorted(card), canvas=(60, 60))
        self.assertEqual(refused, [])
        self.emulator = support.entered(self, support.Emulator(self.folder, "--drive", self.top, tcp_port=0))
        self.target = ("--tcp", self.emulator.tcp, "--timeout", "10")
        self.assertEqual(self.reply("folder", "make", "internal", "a")["id"], 2)
        self.assertEqual(self.reply("folder", "make", "internal", "a/b")["id"], 3)
        path, name, number = NESTED
        stars = root / name
        stars.write_bytes(another_picture())
        self.assertEqual(self.replies("--folder", path, "upload", number, stars), [{"ok": True}])

    def replies(self, *words):
        """Each reply the command tool prints for a command it ends with success."""
        result = support.run_tool(*self.target, *words)
        self.assertEqual(result.status, 0, (words, result.out, result.err))
        return [json.loads(line) for line in result.out.splitlines()]

    def reply(self, *words):
        replies = self.replies(*words)
        self.assertEqual(len(replies), 1, (words, replies))
        return replies[0]

    def listed(self, *words):
        """The rows of every part of a level."""
        return [row for part in self.replies(*words) for row in part["items"]]

    def walked(self):
        """Every row of `list` and of `list in` of each folder row that a reply shows, at
        every depth."""
        rows = []
        levels = [self.listed("list")]
        while levels:
            for row in levels.pop():
                rows.append(row)
                if "playlist" in row:
                    levels.append(self.listed("list", "in", row["id"]))
        return rows

    def catalogs(self, seconds=10):
        """`catalog` once the card's catalog is read whole: `list` shows the card's rows only
        then."""
        deadline = time.monotonic() + seconds
        while True:
            reply = self.reply("catalog")
            if reply["external"]["state"] != "loading":
                self.assertEqual(reply["external"]["state"], "ok", reply)
                return reply
            if time.monotonic() > deadline:
                self.fail(f"the card's catalog was still loading after {seconds} seconds: {reply}")
            time.sleep(0.05)

    def read_back(self, number):
        """A file of the target read whole, 720 bytes at a time. A read answered `busy` is
        asked again a moment later."""
        data = b""
        deadline = time.monotonic() + 10
        while True:
            result = support.run_tool(*self.target, "read", number, len(data), 720)
            reply = json.loads(result.out)
            if reply == {"ok": False, "error": "busy"} and time.monotonic() < deadline:
                time.sleep(0.05)
                continue
            self.assertEqual(result.status, 0, (number, len(data), result.out))
            piece = decoded(reply["data"])
            if not piece:
                self.assertEqual(reply["bytes"], len(data))
                return data
            self.assertLessEqual(len(piece), 720)
            data += piece

    def a_message_after_the_face(self, ordinary=False, seconds=90):
        """Asks for the status until a turn of a message of the board's own storage follows
        a turn of the card's face, and with `ordinary` until that face follows a turn of an
        animation outside `clocks/`: that status, and the turns seen on the way."""
        seen = []
        before = not ordinary
        face = False
        deadline = time.monotonic() + seconds
        while True:
            status = self.reply("status")
            name = status["file"]
            seen.append((name, status["animation"]))
            if name and not name.startswith("clocks/"):
                before = True
            elif before and name == FACE and status["animation"] > INTERNAL_IDS:
                face = True
            elif face and name in PATHS and status["animation"] <= INTERNAL_IDS:
                return status, seen
            if time.monotonic() > deadline:
                face_seen = "the card's face after an ordinary turn" if ordinary else "the card's face"
                self.fail(f"no message of the board's own storage followed {face_seen} within {seconds} seconds: {status}")
            time.sleep(0.05)

    def session(self, check):
        """The board session, the storage that it checks the modes with being `check`."""
        for name, (size, digest) in SEVEN.items():
            tracked = (MESSAGES / name).read_bytes()
            self.assertEqual((len(tracked), hashlib.sha256(tracked).hexdigest()), (size, digest), name)
        self.assertEqual(sum(size for size, _ in SEVEN.values()), 79_235)
        card = kept(self.top)
        picture = (self.folder / "picture.odrg").read_bytes()

        # The settings found are written down, and the brightness brought down to 40. Only
        # a target that plays the board's own clocks reports the preferred storage.
        found = self.reply("status")
        self.assertIn(found.get("clock_storage"), STORAGES, found)
        if found["brightness"] > BRIGHTNESS:
            self.assertEqual(self.reply("brightness", BRIGHTNESS), {"ok": True})
        self.assertEqual(self.reply("status")["brightness"], BRIGHTNESS)
        space = self.reply("space")
        self.assertGreaterEqual(space["free"], ROOM)
        before = self.catalogs()["internal"]
        self.assertEqual(before["state"], "ok")

        # The ids in use, the board's rows and the card's messages, from the walk.
        rows = self.walked()
        board = {row["id"]: row for row in rows if not row["external"]}
        self.assertEqual({row.get("file") for row in board.values()} - {None}, {"picture.odrg", "/".join(NESTED[:2])})
        on_the_card = {row["file"].rsplit("/", 1)[1] for row in rows if row["external"] and row.get("file", "").startswith("clocks/message/")}
        self.assertIn(OLD.rsplit("/", 1)[1], on_the_card)
        # A board message whose name the card's `clocks/message` has is a copy, which `SD
        # card` passes over: the modes are then checked with `Internal storage`.
        self.assertEqual("internal" if on_the_card & set(SEVEN) else "sd", check)
        used = {row["id"] for row in rows}
        free = [number for number in range(1, INTERNAL_IDS + 1) if number not in used]

        clocks = self.reply("folder", "make", "internal", "clocks")
        self.assertEqual((clocks["ok"], clocks["made"]), (True, True))
        made = self.reply("folder", "make", "internal", "clocks/message")
        self.assertEqual((made["ok"], made["made"]), (True, True))
        message_id = made["id"]
        # A new folder takes the lowest free id, so the seven are chosen after both replies.
        self.assertEqual([clocks["id"], message_id], free[:2])
        ids = free[2:2 + len(SEVEN)]

        for number, name in zip(ids, SEVEN):
            result = support.run_tool(*self.target, "--folder", "clocks/message", "upload", number, MESSAGES / name)
            self.assertEqual(result.status, 0, (name, result.out, result.err))
            self.assertEqual(json.loads(result.out), {"ok": True}, name)
            self.assertIn(f"upload: committed: {SEVEN[name][0]} bytes", result.err)

        lines = (self.folder / "folders.txt").read_text(encoding="ascii").splitlines()
        numbers = {line.split(" ", 3)[3]: line.split(" ", 3)[0] for line in lines[1:]}
        self.assertEqual(sorted(numbers), ["a", "a/b", "clocks", "clocks/message"])
        number = numbers["clocks/message"]
        rows = self.listed("list", "in", message_id)
        self.assertEqual(
            [(row["id"], row["file"], row["stored"], row["bytes"], row["type"], row["external"]) for row in rows],
            [(each, f"clocks/message/{name}", f"{number}/{name}", SEVEN[name][0], "widget", False) for each, name in zip(ids, SEVEN)],
        )
        after = self.reply("catalog")["internal"]
        self.assertEqual(after["state"], "ok")
        self.assertGreater(after["generation"], before["generation"])
        self.assertEqual(after["entries"], before["entries"] + len(SEVEN))
        for each, name in zip(ids, SEVEN):
            self.assertEqual(hashlib.sha256(self.read_back(each)).hexdigest(), SEVEN[name][1], name)

        # Clocks only with the message on: a message of the board follows the card's face.
        self.assertEqual(self.reply("clocks", "storage", check), {"ok": True})
        self.assertEqual(self.reply("status")["clock_storage"], check)
        self.assertEqual(self.reply("clocks", "message", "on"), {"ok": True})
        self.assertEqual(self.reply("clocks", "only"), {"ok": True})
        only, seen = self.a_message_after_the_face()
        self.assertIn(only["animation"], ids)
        card_clocks = only["clock_only"]["folder"]
        self.assertGreater(card_clocks, INTERNAL_IDS)
        self.assertEqual((only["clock_mode"], only["clock_message"], only["clock_storage"], only["playing"], only["playlist"], only["clock_only"]),
                         ("only", True, check, card_clocks, "clocks", {"folder": card_clocks, "state": "playing"}))
        # Between the animations: an ordinary turn, a break's face and a message of the board.
        self.assertEqual(self.reply("clocks", "on"), {"ok": True})
        between, more = self.a_message_after_the_face(ordinary=True)
        self.assertIn(between["animation"], ids)
        self.assertEqual((between["clock_mode"], between["clock_message"], between["clock_storage"]), ("between", True, check))
        # The card's copy of one of the seven never plays while the board's is preferred.
        if check == "internal":
            self.assertEqual([turn for turn in seen + more if turn[0] in PATHS and turn[1] > INTERNAL_IDS], [])

        # The settings written down at the start are given back, but for the brightness,
        # which stays at 40 or less.
        self.assertEqual(self.reply("clocks", MODES[found["clock_mode"]]), {"ok": True})
        self.assertEqual(self.reply("clocks", "message", "on" if found["clock_message"] else "off"), {"ok": True})
        self.assertEqual(self.reply("clocks", "storage", found["clock_storage"]), {"ok": True})
        given_back = self.reply("status")
        self.assertEqual((given_back["clock_mode"], given_back["clock_message"], given_back["clock_storage"]),
                         (found["clock_mode"], found["clock_message"], found["clock_storage"]))
        self.assertLessEqual(given_back["brightness"], BRIGHTNESS)
        settings = (self.folder / "clocks.txt").read_text(encoding="ascii").splitlines()
        self.assertEqual("storage internal" in settings, found["clock_storage"] == "internal", settings)

        # The storage read back: each file under the number its folder has, with the bytes
        # of the tracked file; the board's content and the card kept.
        stored = {path.relative_to(self.folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(self.folder.glob("*/v7-*.odrgx"))}
        self.assertEqual(stored, {f"{number}/{name}": digest for name, (_, digest) in SEVEN.items()})
        self.assertEqual((self.folder / "picture.odrg").read_bytes(), picture)
        now = {row["id"]: row for row in self.walked() if not row["external"]}
        self.assertEqual({each: now.get(each) for each in board}, board)
        self.assertEqual(kept(self.top), card)
        self.assertLessEqual(space["free"] - self.reply("space")["free"], ROOM)

    def test_the_board_prefers_its_own_storage_and_the_card_has_none_of_the_seven(self):
        self.start({FACE: clock_of(canvas=(60, 60)), OLD: another_picture()})
        # The owner's settings before the session: Between, the message off, the board's
        # own storage preferred.
        for words in (("clocks", "on"), ("clocks", "message", "off"), ("clocks", "storage", "internal")):
            self.assertEqual(self.reply(*words), {"ok": True})
        self.session(check="sd")

    def test_the_card_holds_the_seven_and_the_sd_card_is_preferred(self):
        self.start({FACE: clock_of(canvas=(60, 60)), OLD: another_picture(),
                    **{f"clocks/message/{name}": (MESSAGES / name).read_bytes() for name in SEVEN}})
        self.session(check="internal")


if __name__ == "__main__":
    unittest.main()

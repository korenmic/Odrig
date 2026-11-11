"""The mirror of a board, with an emulator as the board: the mirror's LEDs show what the
board's show, each refresh's picture within two refreshes of the board's, over the line port
and over HTTP, joined late, after a `play` through either, with a file fetched from the board,
through a lost link and a restart."""

import base64
import binascii
import json
import pathlib
import threading
import time
import types
import unittest

from emulator import binding
from emulator.mirror import driver, files, keeper, middle
from odrig import jsonframes, odrg

from . import support

# How far apart in time the same picture may be on the board and on its mirror: two
# refreshes.
CLOSE_MS = 40
# How long the frames of both are read for one comparison.
WATCH_SECONDS = 3.0


def frames_of(port, seconds):
    """`(ms, picture)` of every refresh an emulator gives within a time, the newest of each
    batch as the page gets them."""
    with support.EventStream(port) as stream:
        events = stream.read_until(lambda events: False, seconds)
    return [(int(event.data.split(" ", 1)[0]), base64.b64decode(event.data.split(" ", 1)[1])) for event in events if event.kind == "frame"]


def changes(frames):
    """The moments the picture changed, `(ms, picture)`, the first one left out."""
    found = []
    for (_, before), (ms, picture) in zip(frames, frames[1:]):
        if picture != before:
            found.append((ms, picture))
    return found


def matched(board, mirror):
    """The share of the mirror's changes of picture that the board made within two refreshes,
    at the one shift of time between their clocks that most of them agree on."""
    board_changes = changes(board)
    mirror_changes = changes(mirror)
    if not mirror_changes:
        return 0.0
    shifts = [b_ms - m_ms for m_ms, picture in mirror_changes for b_ms, other in board_changes if other == picture]
    if not shifts:
        return 0.0
    best = max(shifts, key=lambda shift: sum(1 for other in shifts if abs(other - shift) <= CLOSE_MS))
    near = 0
    for m_ms, picture in mirror_changes:
        if any(other == picture and abs(b_ms - m_ms - best) <= CLOSE_MS for b_ms, other in board_changes):
            near += 1
    return near / len(mirror_changes)


def unique_animation(folder):
    """A file of frames no collection holds: 12 frames of colours of this moment."""
    stamp = time.time_ns()
    width, height = 60, 6
    frames = tuple((100, bytes(((stamp >> 8) & 0xFF, (stamp >> 16) & 0xFF, 20 * n)) * (width * height)) for n in range(12))
    path = pathlib.Path(folder, f"mirror{stamp % 100000}.odrg")
    path.write_bytes(odrg.encode(jsonframes.Animation(width, height, frames)))
    return path


def catalogued(board):
    """Has the board's own storage catalogued, so that its plan names the files' keys."""
    board.command("catalog rebuild internal")
    deadline = time.monotonic() + 30
    while True:
        reply = json.loads(board.command("catalog"))
        if reply["internal"]["state"] == "ok" and reply["rebuild"] is None:
            return
        if time.monotonic() > deadline:
            raise AssertionError(f"the board's catalog was not made: {reply}")
        time.sleep(0.1)


def wait_for_a_picture(mirrored, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if any(any(picture) for _, picture in frames_of(mirrored.port, 0.5)):
            return
    raise AssertionError(f"the mirror showed nothing: {mirrored.lines}")


def watched(*ports):
    """The frames of several emulators over the same few seconds."""
    got = [None] * len(ports)
    threads = [threading.Thread(target=lambda at=at, port=port: got.__setitem__(at, frames_of(port, WATCH_SECONDS))) for at, port in enumerate(ports)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return got


class TheMirrorOfAnEmulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packed = support.example_show()
        cls.folder = cls.packed.__enter__()
        cls.board = support.Emulator(cls.folder, tcp_port=0)
        catalogued(cls.board)

    @classmethod
    def tearDownClass(cls):
        cls.board.stop()
        cls.packed.__exit__(None, None, None)

    def mirror(self, *option):
        mirrored = support.Emulator(self.folder, *option, checked=False)
        self.addCleanup(mirrored.stop)
        wait_for_a_picture(mirrored)
        return mirrored

    def assert_in_step(self, mirrored):
        board, mirror = watched(self.board.port, mirrored.port)
        self.assertGreaterEqual(matched(board, mirror), 0.9)

    def test_over_the_line_port_the_mirror_joined_late_shows_the_boards_pictures_within_two_refreshes(self):
        mirrored = self.mirror("--mirror-tcp", self.board.tcp)
        self.assert_in_step(mirrored)

    def test_over_http_the_mirror_shows_the_boards_pictures_within_two_refreshes(self):
        mirrored = self.mirror("--mirror-http", f"127.0.0.1:{self.board.port}")
        self.assert_in_step(mirrored)

    def test_a_play_through_the_mirror_and_through_the_board_is_followed(self):
        mirrored = self.mirror("--mirror-tcp", self.board.tcp)
        self.assertEqual(json.loads(mirrored.command("play 2")), {"ok": True})
        time.sleep(1)
        self.assert_in_step(mirrored)
        self.assertEqual(json.loads(self.board.command("play 3")), {"ok": True})
        time.sleep(1)
        self.assert_in_step(mirrored)

    def test_a_file_found_nowhere_is_fetched_from_the_board_and_kept(self):
        made = unique_animation(self.folder.parent)
        self.addCleanup(made.unlink)
        result = support.run_tool("--http", f"127.0.0.1:{self.board.port}", "upload", "77", made)
        self.assertEqual(result.status, 0, result)
        self.addCleanup(self.board.command, "remove 77")
        data = made.read_bytes()
        key = f"{binascii.crc32(data):08x}-{len(data)}"
        kept = support.ROOT / files.KEPT / f"{key}.odrg"
        self.addCleanup(lambda: kept.unlink(missing_ok=True))
        mirrored = self.mirror("--mirror-tcp", self.board.tcp)
        self.assertEqual(json.loads(mirrored.command("play 77")), {"ok": True})
        deadline = time.monotonic() + 20
        while not kept.is_file():
            self.assertLess(time.monotonic(), deadline, "the file was not fetched")
            time.sleep(0.1)
        self.assertEqual(kept.read_bytes(), data)
        time.sleep(1)
        self.assert_in_step(mirrored)


class ALostLinkAndARestart(unittest.TestCase):
    def test_the_mirror_goes_on_while_the_board_is_gone_and_follows_it_again_after_its_restart(self):
        with support.example_show() as folder:
            tcp = support.free_port()
            board = support.Emulator(folder, tcp_port=tcp)
            catalogued(board)
            mirrored = support.Emulator(folder, "--mirror-tcp", f"127.0.0.1:{tcp}", checked=False)
            self.addCleanup(mirrored.stop)
            wait_for_a_picture(mirrored)
            board.stop()
            self.assertTrue(any(any(picture) for _, picture in frames_of(mirrored.port, 1.0)))
            board = support.Emulator(folder, tcp_port=tcp)
            try:
                time.sleep(4)
                frames, mirror = watched(board.port, mirrored.port)
                self.assertGreaterEqual(matched(frames, mirror), 0.9)
            finally:
                board.stop()


class StandInKeeper:
    def __init__(self, plan, offset, canvas=None):
        self.plan, self.offset, self.canvas = plan, offset, canvas

    def snapshot(self):
        return self.plan, self.offset

    def board_canvas(self):
        return self.canvas


class StandInFiles:
    def __init__(self, found):
        self.found = found

    def known(self, key):
        return self.found.get(key)


class StandInFetcher:
    def __init__(self):
        self.wanted = []

    def want(self, item_id, key):
        self.wanted.append((item_id, key))


FIRST = {"start": 1000, "end": 5000, "id": 2, "key": "0c11d2e4-40", "loop": 3000}
SECOND = {"start": 5000, "end": None, "from": 700, "id": 3, "key": "77ab0f10-1052", "loop": 1000, "seed": 42, "brightness": 30}


def plan_of(*items, **members):
    return {"ok": True, "planning": True, "version": 7, "now": 2000, "on": True, "brightness": 128, "rotation": 90, "mini": False, "test": False, "snake": None,
            "items": list(items), **members}


class TheDriver(unittest.TestCase):
    def driven(self, plan, offset=100, canvas=None, found=None):
        found = {"0c11d2e4-40": (pathlib.Path("a.odrg"), 1), "77ab0f10-1052": (pathlib.Path("b.odrgx"), 3)} if found is None else found
        self.fetcher = StandInFetcher()
        self.names = {}
        self.keeper = StandInKeeper(plan, offset, canvas)
        made = driver.Driver(self.keeper, StandInFiles(found), self.fetcher, self.names)
        made.canvas = (60, 6)
        return made

    def test_the_item_whose_part_holds_the_boards_time_shows_from_its_turns_point(self):
        made = self.driven(plan_of(FIRST, SECOND))
        record = binding.MirrorRecord()
        self.assertFalse(made.drive(record, 2000))
        self.assertEqual((record.name, record.type, record.on, record.brightness, record.rotation, record.loop_ms, record.seed, record.zero_ms, record.test),
                         (b"0c11d2e4-40.odrg", 1, 1, 128, 1, 3000, 0, 900, 0))
        self.assertEqual(self.names, {"0c11d2e4-40.odrg": pathlib.Path("a.odrg")})
        first = record.serial
        made.drive(record, 6000)
        self.assertEqual((record.name, record.type, record.brightness, record.loop_ms, record.seed, record.zero_ms),
                         (b"77ab0f10-1052.odrg", 3, 30, 1000, 42, 5000 - 700 - 100))
        self.assertNotEqual(record.serial, first)
        self.assertEqual(made.shown(), (None, SECOND))

    def test_a_new_plan_that_keeps_the_turn_on_the_leds_does_not_open_it_again(self):
        made = self.driven(plan_of(FIRST))
        record = binding.MirrorRecord()
        made.drive(record, 2000)
        serial = record.serial
        self.keeper.plan = plan_of(dict(FIRST, end=6000), SECOND, version=8)
        self.keeper.offset = 103
        made.drive(record, 2040)
        self.assertEqual(record.serial, serial)
        self.assertEqual(record.zero_ms, 897)

    def test_the_leds_are_dark_and_say_why(self):
        record = binding.MirrorRecord()
        for plan, offset, canvas, found, why in ((None, None, None, None, "no-plan"), (plan_of(FIRST), 100, (60, 60), None, "canvas"),
                                                 (plan_of(FIRST), 100, None, None, "nothing"), (plan_of(dict(FIRST, key=None)), 0, None, None, "no-key"),
                                                 (plan_of(FIRST), 0, None, {}, "fetching")):
            made = self.driven(plan, offset, canvas, found)
            record.name = b"x.odrg"
            made.drive(record, 9000 if why == "nothing" else 2000)
            self.assertEqual((record.name, made.shown()[0]), (b"", why), why)
        self.assertEqual(self.fetcher.wanted, [(2, "0c11d2e4-40")])

    def test_a_test_the_leds_off_and_the_miniature_output_are_the_boards(self):
        record = binding.MirrorRecord()
        self.assertTrue(self.driven(plan_of(FIRST, on=False, test=True, snake=5, mini=True)).drive(record, 2000))
        self.assertEqual((record.on, record.test, record.snake), (0, 2, 5))
        self.driven(plan_of(FIRST, test=True)).drive(record, 2000)
        self.assertEqual((record.on, record.test, record.snake), (1, 1, 0))

    def test_an_item_is_found_by_its_part(self):
        plan = plan_of(FIRST, SECOND)
        self.assertIsNone(driver.item_at(plan, 999))
        self.assertIs(driver.item_at(plan, 1000), FIRST)
        self.assertIs(driver.item_at(plan, 4999), FIRST)
        self.assertIs(driver.item_at(plan, 5000), SECOND)
        self.assertIs(driver.item_at(plan, 10 ** 9), SECOND)
        self.assertIsNone(driver.item_at(plan_of(FIRST), 5000))


class StandInMiddle:
    def __init__(self):
        self.watchers, self.listeners = [], []
        self.link = types.SimpleNamespace(streamed=True, planned=None)
        self.state = middle.LINKED


class TheKeeper(unittest.TestCase):
    def setUp(self):
        self.keeper = keeper.Keeper(StandInMiddle())

    def test_the_offset_is_the_boards_time_less_the_middle_of_the_round_trip(self):
        self.keeper._take(json.dumps(plan_of(FIRST, now=5000)).encode(), 100, 110)
        self.assertEqual(self.keeper.snapshot(), (plan_of(FIRST, now=5000), 4895))

    def test_a_plan_unchanged_keeps_the_plan_and_moves_the_clock(self):
        self.keeper._take(json.dumps(plan_of(FIRST, now=5000)).encode(), 100, 110)
        self.keeper._take(b'{"ok":true,"planning":true,"version":7,"now":5200,"unchanged":true}', 300, 310)
        self.assertEqual(self.keeper.snapshot(), (plan_of(FIRST, now=5000), 4895))

    def test_a_time_that_went_back_or_planning_off_means_joining_anew(self):
        self.keeper.joined = True
        self.keeper._take(json.dumps(plan_of(FIRST, now=50000)).encode(), 100, 110)
        self.assertTrue(self.keeper.joined)
        self.keeper._take(json.dumps(plan_of(FIRST, now=3000)).encode(), 200, 210)
        self.assertFalse(self.keeper.joined)
        self.keeper.joined = True
        self.keeper._take(json.dumps(plan_of(FIRST, now=3500, planning=False)).encode(), 300, 310)
        self.assertFalse(self.keeper.joined)

    def test_the_lines_that_only_read_are_those_of_the_core(self):
        for line in (b"status", b"space", b"fault", b"list", b"list 5", b"read 1 0 720", b"saved 3", b"catalog", b"catalog page internal 0 0",
                     b"order get", b"mapping get", b"rotation", b"time", b"schedule", b"plan", b"plan since 41"):
            self.assertTrue(keeper.reads_only(line), line)
        for line in (b"play 2", b"on", b"catalog rebuild internal", b"rotation set 1 90", b"time set 1 2", b"plan on", b"plan push on", b"order move 1 2 3", b"mapping test on"):
            self.assertFalse(keeper.reads_only(line), line)

    def test_the_boards_canvas_is_that_of_its_latest_status(self):
        self.assertIsNone(self.keeper.board_canvas())
        self.keeper.status = b'{"ok":true,"on":true,"width":60,"height":6}\n'
        self.assertEqual(self.keeper.board_canvas(), (60, 6))


if __name__ == "__main__":
    unittest.main()

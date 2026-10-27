"""The seek: a move of the emulator's clock forward, a restart for a move back, the
refusals, the log line of a restart, and the route `POST /seek`."""

import ast
import json
import pathlib
import tempfile
import unittest

from emulator import binding, engine, host, hub, lengths
from tests.core.support import ReferencePlayer

from . import support

GRID = engine.GRID_MS
HELLO_MS = 5100
ZERO = 40
RECORD = pathlib.Path(__file__).resolve().parents[2] / "emulator" / "record.py"


class Seeks(unittest.TestCase):
    """An engine on the example show with an injected clock, the playlist playing and the
    length of the first animation seen."""

    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        self.now = 0
        self.files = host.FolderHost(self.folder)
        self.addCleanup(self.files.close)
        self.core = binding.Core(support.LIBRARY, self.files)
        self.hub = hub.Hub()
        self.connection = self.hub.connect({})
        self.reference = ReferencePlayer(support.files_of(self.folder))
        self.engine = engine.Engine(self.core, self.hub, clock=lambda: self.now * 1_000_000, host=self.files, lengths=lengths.Lengths(node=None))

    def tick_until(self, ms):
        while self.now < ms:
            self.now += GRID
            self.engine.tick()
            self.reference.poll(self.now)

    def command(self, line):
        self.reference.command(self.now, line)
        return self.engine.line(line, "http")

    def known(self):
        """The playlist from 20 ms and the first loop seen, so that the length is known."""
        self.tick_until(GRID)
        self.command(b"play all")
        self.tick_until(ZERO + HELLO_MS + GRID)
        self.assertEqual(self.engine.playback.length, HELLO_MS)

    def frames_follow_the_reference(self, ticks):
        """Ticks on and checks every refresh against the reference player at the engine's
        timestamps, the reference told of the same moves of the clock."""
        for _ in range(ticks):
            self.now += GRID
            self.engine.tick()
            ms, frame = self.hub.newest_refresh()
            self.assertEqual(ms, self.engine.now_ms())
            refresh = self.reference.poll(ms)
            self.assertIsNotNone(refresh, f"no refresh of the reference at {ms}")
            self.assertEqual(frame, b"".join(rgb for _, rgb in refresh), f"the refresh at {ms} differs from the reference")

    def test_a_seek_forward_moves_the_clock_by_whole_grid_steps_to_the_point(self):
        self.known()
        before = self.engine.now_ms()
        reply = self.engine.seek(3000)
        self.assertEqual(reply["ok"], True)
        self.assertEqual(reply["moved"], 2980)
        self.assertEqual(reply["position"], 3000)
        self.assertEqual(reply["start"], ZERO + HELLO_MS)
        self.assertEqual(reply["length"], HELLO_MS)
        self.assertEqual(self.engine.now_ms(), before + 2980)
        self.assertEqual(self.hub.newest_refresh()[0], self.engine.now_ms())
        self.assertEqual(len(self.hub.entries()), 1)
        self.frames_follow_the_reference(50)

    def test_a_seek_back_restarts_the_animation_and_moves_the_clock_to_the_point(self):
        self.known()
        self.tick_until(ZERO + HELLO_MS + 3000)
        sent = self.engine.now_ms()
        reply = self.engine.seek(1000)
        self.assertEqual(reply["ok"], True)
        self.assertEqual(reply["start"], sent + GRID)
        self.assertEqual(reply["turn"], sent + GRID)
        self.assertEqual(reply["moved"], GRID + 1000)
        self.assertEqual(reply["position"], 1000)
        entries = self.hub.entries()
        self.assertEqual([(entry["transport"], entry["line"], entry["ms"]) for entry in entries[-1:]], [("seek", "play 1", sent)])
        self.reference.command(sent, b"play 1")
        self.now = self.engine.now_ms()
        self.reference.poll(sent + GRID)
        self.reference.poll(self.now)
        self.frames_follow_the_reference(50)
        event = json.loads(self.hub.latest_position())
        self.assertEqual(event, {"animation": 1, "start": sent + GRID, "turn": sent + GRID, "length": HELLO_MS})

    def test_a_seek_back_sees_no_loop_length_across_it(self):
        self.tick_until(GRID)
        self.command(b"play all")
        self.tick_until(ZERO + HELLO_MS + GRID)
        self.engine.playback.length = None
        self.engine.playback.source = None
        self.engine.playback.length = HELLO_MS
        self.engine.seek(100)
        self.engine.playback.length = None
        self.tick_until(self.now + HELLO_MS + GRID)
        self.assertIsNone(self.engine.playback.length)

    def test_a_seek_to_the_point_it_is_at_moves_nothing(self):
        self.known()
        reply = self.engine.seek(20)
        self.assertEqual((reply["ok"], reply["moved"], reply["position"]), (True, 0, 20))

    def test_the_refusals(self):
        self.tick_until(3 * GRID)
        self.assertEqual(self.engine.seek(100), {"ok": False, "error": "cycle"})
        self.command(b"play all")
        self.tick_until(self.now + 2 * GRID)
        self.assertEqual(self.engine.seek(100), {"ok": False, "error": "length-unknown"})
        self.tick_until(self.engine.playback.start + HELLO_MS + GRID)
        self.assertEqual(self.engine.playback.length, HELLO_MS)
        self.assertEqual(self.engine.seek(HELLO_MS - GRID), {"ok": False, "error": "beyond-length"})
        self.assertEqual(self.engine.seek(-1), {"ok": False, "error": "beyond-length"})
        self.assertEqual(self.engine.seek("100"), {"ok": False, "error": "bad-argument"})
        self.assertEqual(self.engine.seek(True), {"ok": False, "error": "bad-argument"})
        self.assertEqual(self.engine.seek(HELLO_MS - 2 * GRID)["ok"], True)


class NothingPlays(unittest.TestCase):
    def test_a_seek_while_nothing_plays_is_refused(self):
        show = support.entered(self, tempfile.TemporaryDirectory())
        show_file = pathlib.Path(show, "show.json")
        show_file.write_text('{"version": 1, "brightness": 128, "items": [{"id": 1, "file": "hello.odrg"}]}\n', encoding="utf-8")
        folder = support.entered(self, support.packed(show_file, support.TWO_LEGS, support.ROOT / "animations"))
        files = host.FolderHost(folder)
        self.addCleanup(files.close)
        core = binding.Core(support.LIBRARY, files)
        now = [0]
        running = engine.Engine(core, hub.Hub(), clock=lambda: now[0] * 1_000_000, host=files, lengths=lengths.Lengths(node=None))
        for _ in range(3):
            now[0] += GRID
            running.tick()
        self.assertEqual(running.playback.animation, 1)
        running.line(b"remove 1", "http")
        for _ in range(3):
            now[0] += GRID
            running.tick()
        self.assertEqual(running.seek(100), {"ok": False, "error": "nothing-plays"})


class Route(unittest.TestCase):
    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        self.emulator = support.entered(self, support.Emulator(self.folder, checked=False))

    def test_post_seek_moves_playback_and_answers_the_position(self):
        self.emulator.command("play all")
        stream = support.entered(self, support.EventStream(self.emulator.port))
        stream.read_until(lambda events: any(event.kind == "position" and json.loads(event.data)["length"] is not None for event in events), 15)
        answer = self.emulator.request("POST", "/seek", body=b'{"ms": 2000}')
        self.assertEqual(answer.status, 200)
        self.assertEqual(answer.headers["content-type"], "application/json")
        reply = json.loads(answer.body)
        self.assertEqual(reply["ok"], True)
        self.assertEqual(reply["length"], HELLO_MS)
        self.assertLessEqual(abs(reply["position"] - 2000), 2 * GRID)
        self.assertEqual(reply["moved"] % GRID, 0)
        answer = self.emulator.request("POST", "/seek", body=b'{"ms": 99999}')
        self.assertEqual((answer.status, json.loads(answer.body)), (200, {"ok": False, "error": "beyond-length"}))
        answer = self.emulator.request("POST", "/seek", body=b'ms=1')
        self.assertEqual((answer.status, json.loads(answer.body)), (200, {"ok": False, "error": "bad-argument"}))

    def test_another_method_is_405_and_a_missing_length_411(self):
        answer = self.emulator.request("GET", "/seek")
        self.assertEqual((answer.status, answer.headers.get("allow")), (405, "POST"))
        received = support.raw_request(self.emulator.port, b"POST /seek HTTP/1.1\r\nHost: x\r\n\r\n")
        self.assertIn(b" 411 ", received.split(b"\r\n", 1)[0])


class RecordMode(unittest.TestCase):
    def test_record_mode_has_no_engine_no_hub_and_so_no_position_and_no_seek(self):
        tree = ast.parse(RECORD.read_text(encoding="utf-8"))
        names = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
        self.assertEqual(names & {"engine", "hub", "lengths"}, set())


if __name__ == "__main__":
    unittest.main()


class HeavyFile(unittest.TestCase):
    """A file whose seconds hold more bytes than the core decodes at one refresh: a seek
    far into it must show the frame of the point at once, not seconds later."""

    def setUp(self):
        import random
        from odrig import jsonframes, odrg
        rng = random.Random("noise for the seek")
        frames = tuple((GRID, bytes(rng.randrange(256) for _ in range(60 * 6 * 3))) for _ in range(500))
        self.folder = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()), "show")
        self.folder.mkdir()
        (self.folder / "noise.odrg").write_bytes(odrg.encode(jsonframes.Animation(60, 6, frames)))
        (self.folder / "mapping.json").write_bytes(support.TWO_LEGS.read_bytes())
        (self.folder / "show.json").write_text('{"version": 1, "brightness": 128, "items": [{"id": 1, "file": "noise.odrg"}]}\n', encoding="utf-8")
        self.assertGreater((self.folder / "noise.odrg").stat().st_size, 400_000)
        self.now = 0
        self.files = host.FolderHost(self.folder)
        self.addCleanup(self.files.close)
        self.core = binding.Core(support.LIBRARY, self.files)
        self.hub = hub.Hub()
        self.reference = ReferencePlayer(support.files_of(self.folder))
        self.engine = engine.Engine(self.core, self.hub, clock=lambda: self.now * 1_000_000, host=self.files, lengths=lengths.Lengths(node=None))

    def test_a_seek_far_into_it_shows_the_frame_of_the_point_at_once(self):
        for _ in range(50):
            self.now += GRID
            self.engine.tick()
            self.reference.poll(self.now)
        self.engine.playback.length = 10_000
        reply = self.engine.seek(8_000)
        self.assertEqual(reply["ok"], True)
        ms, frame = self.hub.newest_refresh()
        self.assertEqual(ms, self.engine.now_ms())
        self.assertEqual(frame, b"".join(rgb for _, rgb in self.reference.poll(ms)), "the frame after the seek is not the frame of the point")

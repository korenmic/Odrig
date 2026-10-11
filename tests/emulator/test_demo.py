import json
import pathlib
import struct
import subprocess
import tempfile
import unittest

from emulator import recfile
from odrig import mapping, odrg
from odrig.generators import dvd_bounce, hello_world
from tests.core import support as core_support
from tests.core.support import ReferencePlayer

from . import support

SHOW = support.DEMO_SHOW

# Leg N of the target file is on pin N, but for the last two.
LEGS = tuple((number, pin, 180) for number, pin in enumerate((*range(1, 19), 21, 47), start=1))


def lit_pixels(canvas, data):
    """The canvas pixels `(x, y)` whose LED is not dark in the LED data of one refresh, the
    legs one after the other in the order of the mapping file."""
    lit = set()
    offset = 0
    for leg in canvas.legs:
        for n, place in enumerate(core_support.led_pixels(canvas, leg)):
            if any(data[offset + 3 * n:offset + 3 * n + 3]):
                lit.add((place % canvas.width + 1, place // canvas.width + 1))
        offset += 3 * canvas.led_count(leg)
    return lit


class DemoShow(unittest.TestCase):
    """The demo show for the target file: generated and packed into a temporary folder, and
    31 seconds of it recorded, once."""

    @classmethod
    def setUpClass(cls):
        cls.work = pathlib.Path(support.entered(cls, tempfile.TemporaryDirectory()))
        cls.sources = cls.work / "sources"
        cls.sources.mkdir()
        cls.statuses = [
            hello_world.main([str(cls.sources / "hello.json"), "--mapping", str(support.TARGET)]),
            dvd_bounce.main([str(cls.sources / "dvd.json"), "--mapping", str(support.TARGET)]),
        ]
        cls.folder = cls.work / "show"
        cls.packed = support.run_module("pack", "--show", SHOW, "--mapping", support.TARGET, "--sources", cls.sources, "--out", cls.folder, module="odrig")
        cls.canvas = mapping.read(support.TARGET)
        cls.recorded = support.run(cls.folder, "--record", cls.work / "demo.odrr", "--seconds", 31)
        cls.recording = recfile.read(cls.work / "demo.odrr")

    def test_the_tracked_show_file_has_the_two_animations_the_cycle_the_start_and_the_brightness(self):
        show = json.loads(SHOW.read_text(encoding="utf-8"))
        self.assertEqual(show, {
            "version": 1,
            "brightness": 128,
            "items": [{"id": 1, "file": "hello.odrg"}, {"id": 2, "file": "dvd.odrg"}, {"id": 3, "cycle": [1, 2], "seconds": 15}],
            "start": 3,
        })

    def test_no_canvas_size_is_written_for_the_show(self):
        text = SHOW.read_text(encoding="utf-8")
        for word in ("width", "height", "60", "legs", "mapping", "rows", "columns"):
            self.assertNotIn(word, text)
        self.assertEqual(sorted(path.name for path in SHOW.parent.iterdir()), ["show.json"])

    def test_only_the_show_file_is_tracked_and_nothing_generated(self):
        tracked = subprocess.run(["git", "ls-files", "shows/demo-20", "build"], cwd=support.ROOT, capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(tracked, ["shows/demo-20/show.json"])
        ignored = subprocess.run(["git", "check-ignore", "build/demo-20/sources/hello.json", "build/demo-20/show/show.json"], cwd=support.ROOT, capture_output=True, text=True)
        self.assertEqual(ignored.stdout.split(), ["build/demo-20/sources/hello.json", "build/demo-20/show/show.json"])

    def test_the_generators_and_pack_give_a_60_x_60_show_from_the_target_file_alone(self):
        self.assertEqual(self.statuses, [0, 0])
        self.assertEqual((self.packed.status, self.packed.out, self.packed.err), (0, "", ""))
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])
        self.assertEqual((self.folder / "mapping.json").read_bytes(), support.TARGET.read_bytes())
        self.assertEqual((self.folder / "show.json").read_bytes(), SHOW.read_bytes())
        self.assertEqual((self.canvas.width, self.canvas.height), (60, 60))
        for name, frames, ms in (("hello", 255, 20), ("dvd", 116, 180)):
            source = json.loads((self.sources / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual((source["width"], source["height"]), (60, 60))
            packed = (self.folder / f"{name}.odrg").read_bytes()
            self.assertEqual(struct.unpack_from("<HH", packed, 6), (60, 60))
            self.assertEqual([duration for duration, _ in odrg.decode(packed).records], [ms] * frames)

    def test_the_packed_folder_holds_the_files_the_other_tests_of_the_suites_play(self):
        self.assertEqual(support.files_of(self.folder), core_support.demo_show())

    def test_31_seconds_of_it_equal_the_reference_at_every_tick(self):
        self.assertEqual((self.recorded.status, self.recorded.out, self.recorded.err), (0, "", ""))
        recording = self.recording
        self.assertEqual(recording.legs, LEGS)
        self.assertEqual(recording.led_bytes, 10800)
        self.assertEqual(len(recording.ticks), 1550)
        refreshes, _ = support.reference(support.files_of(self.folder), range(0, 31000, 20))
        for tick, refresh in zip(recording.ticks, refreshes):
            self.assertTrue(tick.produced, tick.ms)
            for (leg, _, _), got, wanted in zip(recording.legs, recfile.split(recording, tick.data), refresh):
                if got != wanted:
                    self.fail(f"tick {tick.ms}: the LED data of leg {leg} differs from the reference")
        by_time = {tick.ms: tick.data for tick in recording.ticks}
        self.assertNotEqual(by_time[14980], by_time[15000])
        self.assertEqual(by_time[30000], by_time[0])
        self.assertTrue(any(by_time[0]))
        self.assertEqual(max(by_time[0]), 128)

    def test_hello_world_stands_upright_and_centred_in_the_rows_28_to_33(self):
        by_time = {tick.ms: tick.data for tick in self.recording.ticks}
        words = lit_pixels(self.canvas, by_time[0])
        self.assertEqual((min(y for _, y in words), max(y for _, y in words)), (28, 33))
        self.assertEqual((min(x for x, _ in words), max(x for x, _ in words)), (4, 56))
        # As many dark columns on the left as on the right, and as many dark rows below as above.
        self.assertEqual((4 - 1, 28 - 1), (60 - 56 - 1, 60 - 33))
        rows = ["".join("X" if (x, y) in words else "." for x in range(4, 57)) for y in range(33, 27, -1)]
        self.assertEqual(rows, [
            "X..X.XXXX.X....X.....XX.....X...X..XX..XXX..X....XXX.",
            "X..X.X....X....X....X..X....X...X.X..X.X..X.X....X..X",
            "XXXX.XXX..X....X....X..X....X...X.X..X.X..X.X....X..X",
            "X..X.X....X....X....X..X....X.X.X.X..X.XXX..X....X..X",
            "X..X.X....X....X....X..X....XX.XX.X..X.X.X..X....X..X",
            "X..X.XXXX.XXXX.XXXX..XX.....X...X..XX..X..X.XXXX.XXX.",
        ])
        # The same pixels are lit for as long as the words play, at every tick of the first turn.
        for ms in (20, 5080, 5100, 14980):
            self.assertEqual(lit_pixels(self.canvas, by_time[ms]), words, ms)
        # On a leg the rows 28 to 33 are the LEDs 28 to 33 of its first column, which runs
        # up, 88 to 93 of its second, which runs down, and 148 to 153 of its third.
        in_the_rows = {*range(28, 34), *range(88, 94), *range(148, 154)}
        lit_legs = set()
        for (leg, _, _), data in zip(self.recording.legs, recfile.split(self.recording, by_time[0])):
            lit = {n for n in range(1, 181) if any(data[3 * n - 3:3 * n])}
            self.assertLessEqual(lit, in_the_rows, f"leg {leg}")
            if lit:
                lit_legs.add(leg)
        # The words are on the legs 2 to 19; the gap between them is the columns of leg 10.
        self.assertEqual(lit_legs, set(range(2, 20)) - {10})

    def test_the_square_of_dvd_bounce_passes_over_leds_of_all_twenty_legs(self):
        # The second turn of the cycle, from 15 to 30 seconds, plays DVD bounce from its start.
        turn = [tick for tick in self.recording.ticks if 15000 <= tick.ms < 30000]
        self.assertEqual(len(turn), 750)
        lit_legs = set()
        corners = []
        for tick in turn:
            square = lit_pixels(self.canvas, tick.data)
            left, bottom = min(x for x, _ in square), min(y for _, y in square)
            self.assertEqual(square, {(left, bottom), (left + 1, bottom), (left, bottom + 1), (left + 1, bottom + 1)}, tick.ms)
            if not corners or corners[-1] != (left, bottom):
                corners.append((left, bottom))
            lit_legs |= {leg for (leg, _, _), data in zip(self.recording.legs, recfile.split(self.recording, tick.data)) if any(data)}
        self.assertEqual(lit_legs, set(range(1, 21)))
        # It starts in the top-left corner and reaches the bottom-right one.
        self.assertEqual(corners[0], (1, 59))
        self.assertIn((59, 1), corners)
        self.assertEqual({x for x, _ in corners} | {x + 1 for x, _ in corners}, set(range(1, 61)))

    def test_the_emulator_started_on_it_reports_twenty_legs_of_180_leds_and_refreshes_of_10800_bytes(self):
        with support.Emulator(self.folder) as emulator, support.EventStream(emulator.port) as stream:
            events = stream.read_until(lambda events: sum(event.kind == "frame" for event in events) >= 5)
            hello = json.loads(events[0].data)
            self.assertEqual(hello["legs"], [list(leg) for leg in LEGS])
            self.assertEqual(len(hello["legs"]), 20)
            self.assertIsNone(hello["error"])
            self.assertEqual(emulator.request("GET", "/show/mapping.json").body, support.TARGET.read_bytes())
            frames = support.frames(events)
            self.assertEqual({len(data) for _, data in frames}, {10800})
            status = emulator.status()
            self.assertEqual((status["playing"], status["animation"], status["brightness"], status["error"]), (3, 1, 128, None))
            player = ReferencePlayer(support.files_of(self.folder))
            player.poll(hello["t0"])
            for ms, data in frames:
                self.assertEqual(data, b"".join(rgb for _, rgb in player.poll(ms)), ms)


if __name__ == "__main__":
    unittest.main()

import json
import pathlib
import struct
import subprocess
import tempfile
import unittest

from emulator import recfile
from odrig import mapping
from odrig.generators import dvd_bounce, hello_world
from tests.core.support import ReferencePlayer

from . import support

SHOW = support.ROOT / "shows" / "demo-10" / "show.json"


class DemoShow(unittest.TestCase):
    """The ten-leg demo show, generated and packed into a temporary folder once."""

    @classmethod
    def setUpClass(cls):
        cls.work = pathlib.Path(support.entered(cls, tempfile.TemporaryDirectory()))
        cls.sources = cls.work / "sources"
        cls.sources.mkdir()
        cls.statuses = [
            hello_world.main([str(cls.sources / "hello.json"), "--mapping", str(support.TEN_LEGS)]),
            dvd_bounce.main([str(cls.sources / "dvd.json"), "--mapping", str(support.TEN_LEGS)]),
        ]
        cls.folder = cls.work / "show"
        cls.packed = support.run_module("pack", "--show", SHOW, "--mapping", support.TEN_LEGS, "--sources", cls.sources, "--out", cls.folder, module="odrig")

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
        for word in ("width", "height", "60", "30", "legs", "mapping"):
            self.assertNotIn(word, text)
        self.assertEqual(sorted(path.name for path in SHOW.parent.iterdir()), ["show.json"])

    def test_only_the_show_file_is_tracked_and_nothing_generated(self):
        tracked = subprocess.run(["git", "ls-files", "shows/demo-10", "build"], cwd=support.ROOT, capture_output=True, text=True, check=True).stdout.split()
        self.assertLessEqual(set(tracked), {"shows/demo-10/show.json"})
        ignored = subprocess.run(["git", "check-ignore", "build/demo-10/sources/hello.json", "build/demo-10/show/show.json"], cwd=support.ROOT, capture_output=True, text=True)
        self.assertEqual(ignored.stdout.split(), ["build/demo-10/sources/hello.json", "build/demo-10/show/show.json"])

    def test_the_generators_and_pack_give_a_60_x_30_show_from_the_ten_leg_mapping_alone(self):
        self.assertEqual(self.statuses, [0, 0])
        self.assertEqual((self.packed.status, self.packed.out, self.packed.err), (0, "", ""))
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])
        self.assertEqual((self.folder / "mapping.json").read_bytes(), support.TEN_LEGS.read_bytes())
        self.assertEqual((self.folder / "show.json").read_bytes(), SHOW.read_bytes())
        canvas = mapping.read(support.TEN_LEGS)
        self.assertEqual((canvas.width, canvas.height), (60, 30))
        for name in ("hello", "dvd"):
            source = json.loads((self.sources / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual((source["width"], source["height"]), (60, 30))
            self.assertEqual(struct.unpack_from("<HH", (self.folder / f"{name}.odrg").read_bytes(), 6), (60, 30))

    def test_31_seconds_of_it_equal_the_reference_at_every_tick(self):
        out = self.work / "demo.odrr"
        result = support.run(self.folder, "--record", out, "--seconds", 31)
        self.assertEqual((result.status, result.out, result.err), (0, "", ""))
        recording = recfile.read(out)
        self.assertEqual(recording.legs, tuple((number, number, 180) for number in range(1, 11)))
        self.assertEqual(recording.led_bytes, 5400)
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

    def test_hello_world_is_in_the_middle_rows_and_the_square_moves_over_the_whole_canvas(self):
        player = ReferencePlayer(support.files_of(self.folder))
        lit_legs = {leg for leg, rgb in player.poll(0) if any(rgb)}
        self.assertEqual(lit_legs, {5, 6})
        seen = set()
        player.command(0, b"play 2")
        for now in range(20, 31000, 200):
            seen |= {leg for leg, rgb in player.poll(now) if any(rgb)}
        self.assertEqual(seen, set(range(1, 11)))

    def test_the_emulator_started_on_it_reports_ten_legs_on_pins_1_to_10(self):
        with support.Emulator(self.folder) as emulator, support.EventStream(emulator.port) as stream:
            events = stream.read_until(lambda events: sum(event.kind == "frame" for event in events) >= 5)
            hello = json.loads(events[0].data)
            self.assertEqual(hello["legs"], [[number, number, 180] for number in range(1, 11)])
            self.assertIsNone(hello["error"])
            self.assertEqual(emulator.request("GET", "/show/mapping.json").body, support.TEN_LEGS.read_bytes())
            frames = support.frames(events)
            self.assertEqual({len(data) for _, data in frames}, {5400})
            status = emulator.status()
            self.assertEqual((status["playing"], status["animation"], status["brightness"], status["error"]), (3, 1, 128, None))
            player = ReferencePlayer(support.files_of(self.folder))
            player.poll(hello["t0"])
            for ms, data in frames:
                self.assertEqual(data, b"".join(rgb for _, rgb in player.poll(ms)), ms)


if __name__ == "__main__":
    unittest.main()

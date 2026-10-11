import json
import unittest

from . import support
from .test_playback import T0, Playback, every_20_ms, polls, refreshes


def animation_item(number, file):
    return {"id": number, "file": file}


def cycle_item(number, ids, seconds):
    return {"id": number, "cycle": list(ids), "seconds": seconds}


def example_with(items, start):
    """The example show's two files with another list of items, on the two-leg mapping."""
    files = support.example_show()
    files["show.json"] = support.show_text(items, 255, start)
    return files


HELLO = animation_item(1, "hello.odrg")
DVD = animation_item(2, "dvd.odrg")
HELLO_MS = 5100


class Cycles(Playback):
    @classmethod
    def setUpClass(cls):
        # The pictures of each animation when it plays alone, by elapsed time.
        cls.alone = {}
        for number, item in ((1, HELLO), (2, DVD)):
            produced, _ = refreshes(support.start(example_with([item], number), every_20_ms(800)).lines)
            cls.alone[number] = {time - T0: legs for time, legs in produced}

    def pictures(self, files, times):
        produced, idle = refreshes(self.assert_as_the_reference(files, polls(times)))
        self.assertEqual(idle, [])
        return {time - T0: legs for time, legs in produced}

    def test_the_example_show_changes_turns_at_15_30_45_and_60_seconds(self):
        files = support.example_show()
        listed = json.loads(files["show.json"])
        self.assertEqual((listed["start"], listed["items"][2]), (3, cycle_item(3, [1, 2], 15)))
        shown = self.pictures(files, range(T0, T0 + 65000, 20))
        self.assertEqual(len(shown), 3250)
        # The example show has brightness 128; the lone runs have 255.
        dimmed = {
            number: {elapsed: {leg: bytes((value * 128 + 127) // 255 for value in rgb) for leg, rgb in legs.items()} for elapsed, legs in alone.items()}
            for number, alone in self.alone.items()
        }
        for turn_start, animation in ((0, 1), (15000, 2), (30000, 1), (45000, 2), (60000, 1)):
            with self.subTest(turn_start=turn_start):
                # Each turn starts from the first frame and runs on from there.
                for elapsed in (0, 20, 40, 1000, 4980):
                    self.assertEqual(shown[turn_start + elapsed], dimmed[animation][elapsed], f"{elapsed} ms into the turn")
        # The last refresh of a turn still belongs to it: Hello world loops every 5.1 s.
        self.assertEqual(shown[14980], dimmed[1][14980 % HELLO_MS])
        self.assertEqual(shown[29980], dimmed[2][14980])
        self.assertEqual(shown[44980], dimmed[1][14980 % HELLO_MS])
        self.assertNotEqual(shown[14980], shown[15000])
        self.assertNotEqual(shown[29980], shown[30000])

    def test_an_animation_listed_twice_starts_again_at_the_turn_change(self):
        files = example_with([HELLO, cycle_item(7, [1, 1], 2)], 7)
        shown = self.pictures(files, range(T0, T0 + 6100, 20))
        for elapsed in range(0, 6100, 20):
            self.assertEqual(shown[elapsed], self.alone[1][elapsed % 2000], f"at {elapsed} ms")
        self.assertNotEqual(shown[1980], shown[2000])
        self.assertEqual(shown[2000], shown[0])
        self.assertEqual(shown[4000], shown[0])

    def test_a_cycle_of_one_entry_starts_its_animation_again_every_turn(self):
        files = example_with([DVD, HELLO, cycle_item(3, [2], 3)], 3)
        shown = self.pictures(files, range(T0, T0 + 9100, 20))
        for elapsed in range(0, 9100, 20):
            self.assertEqual(shown[elapsed], self.alone[2][elapsed % 3000], f"at {elapsed} ms")

    def test_an_animation_of_3400_ms_in_a_turn_of_5_seconds_loops_and_is_cut_at_the_turn_change(self):
        files = example_with([animation_item(1, "short.odrg"), DVD, cycle_item(3, [1, 2], 5)], 3)
        files["short.odrg"] = support.clip(1, 60, 6, (20,) * 170)
        alone = example_with([animation_item(1, "short.odrg")], 1)
        alone["short.odrg"] = files["short.odrg"]
        short, _ = refreshes(support.start(alone, every_20_ms(171)).lines)
        short = {time - T0: legs for time, legs in short}
        self.assertEqual(short[3400], short[0])
        self.assertEqual(len({tuple(sorted(legs.items())) for legs in short.values()}), 170)

        shown = self.pictures(files, range(T0, T0 + 15100, 20))
        for elapsed in range(0, 5000, 20):
            self.assertEqual(shown[elapsed], short[elapsed % 3400], f"at {elapsed} ms")
        self.assertEqual(shown[3400], short[0])
        self.assertEqual(shown[4980], short[1580])
        for elapsed in range(5000, 10000, 20):
            self.assertEqual(shown[elapsed], self.alone[2][elapsed - 5000], f"at {elapsed} ms")
        for elapsed in range(10000, 15000, 20):
            self.assertEqual(shown[elapsed], short[(elapsed - 10000) % 3400], f"at {elapsed} ms")
        self.assertEqual(shown[15000], self.alone[2][0])

    def test_a_turn_of_1_second(self):
        files = example_with([HELLO, DVD, cycle_item(3, [2, 1, 1], 1)], 3)
        shown = self.pictures(files, range(T0, T0 + 7000, 20))
        for elapsed in range(0, 7000, 20):
            animation = (2, 1, 1)[elapsed // 1000 % 3]
            self.assertEqual(shown[elapsed], self.alone[animation][elapsed % 1000], f"at {elapsed} ms")

    def test_a_turn_of_65535_seconds(self):
        turn = 65535 * 1000
        files = example_with([HELLO, DVD, cycle_item(3, [1, 2], 65535)], 3)
        times = [0, 20, turn - 20, turn, turn + 20, turn + 12340, 2 * turn - 20, 2 * turn, 2 * turn + 5100, 7 * turn + 40, 8 * turn]
        shown = self.pictures(files, [T0 + time for time in times])
        dvd_ms = 41760
        self.assertEqual(shown[0], self.alone[1][0])
        self.assertEqual(shown[turn - 20], self.alone[1][(turn - 20) % HELLO_MS])
        self.assertEqual(shown[turn], self.alone[2][0])
        self.assertEqual(shown[turn + 20], self.alone[2][20])
        self.assertEqual(shown[turn + 12340], self.alone[2][12340])
        self.assertEqual(shown[2 * turn - 20], self.alone[2][(turn - 20) % dvd_ms])
        self.assertEqual(shown[2 * turn], self.alone[1][0])
        self.assertEqual(shown[2 * turn + 5100], self.alone[1][0])
        self.assertEqual(shown[7 * turn + 40], self.alone[2][40])
        self.assertEqual(shown[8 * turn], self.alone[1][0])

    def test_a_cycle_goes_on_for_as_long_as_it_plays(self):
        files = example_with([HELLO, DVD, cycle_item(3, [1, 2, 2], 2)], 3)
        far = 10 ** 12
        times = [0] + [far * 6000 + offset for offset in (0, 20, 1980, 2000, 3980, 4000, 5980, 6000)]
        shown = self.pictures(files, [T0 + time for time in times])
        base = far * 6000
        self.assertEqual(shown[base], self.alone[1][0])
        self.assertEqual(shown[base + 1980], self.alone[1][1980])
        self.assertEqual(shown[base + 2000], self.alone[2][0])
        self.assertEqual(shown[base + 3980], self.alone[2][1980])
        self.assertEqual(shown[base + 4000], self.alone[2][0])
        self.assertEqual(shown[base + 6000], self.alone[1][0])

    def test_late_and_skipped_polls_across_a_turn_change(self):
        files = example_with([HELLO, DVD, cycle_item(3, [1, 2], 1)], 3)
        times = [0, 990, 999, 1000, 1013, 1020, 2950, 3007, 3020, 9999, 10000]
        produced, idle = refreshes(self.assert_as_the_reference(files, polls(T0 + time for time in times)))
        self.assertEqual(idle, [T0 + 999, T0 + 1013])
        shown = {time - T0: legs for time, legs in produced}
        self.assertEqual(shown[990], self.alone[1][980])
        self.assertEqual(shown[1000], self.alone[2][0])
        self.assertEqual(shown[3007], self.alone[2][0])
        self.assertEqual(shown[9999], self.alone[2][980])
        self.assertEqual(shown[10000], self.alone[1][0])

    def test_a_cycle_plays_files_with_and_without_a_palette_in_turn(self):
        text = support.mapping_texts()["legs-10"]
        files = {
            "mapping.json": text,
            "show.json": support.show_text([animation_item(1, "few.odrg"), animation_item(2, "dense.odrg"), cycle_item(3, [1, 2], 1)], 200, 3),
            "few.odrg": support.clip(2, 60, 30, (20,) * 10),
            "dense.odrg": support.dense_clip(60, 30, 1),
        }
        self.assertNotEqual(files["few.odrg"][10:12], b"\0\0")
        self.assertEqual(files["dense.odrg"][10:12], b"\0\0")
        self.assert_as_the_reference(files, every_20_ms(260))


if __name__ == "__main__":
    unittest.main()

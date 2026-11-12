"""The mirror's entry: a turn the host describes, shown in place of the show at every poll, as
the core would play the file itself, with nothing written."""

import json
import unittest

from . import support
from .test_clocks import CANVAS, clock_of, show_of
from .test_drive import replies
from .test_playback import T0

TIMES = [0, 300, 1000, 1700, 2500, 4100]


def loop_of(seconds, seed):
    """An animation of the canvas whose loop lasts this many seconds."""
    return support.clip(seed, *CANVAS, (1000,) * seconds)


def mirror(name, kind, zero, loop=0, seed=0, brightness=255, on=1, rotation=0, test=0, snake=0, serial=1):
    """The test host's line that sets a mirror's turn."""
    return f"mirror {name or '-'} {kind} {zero} {loop} {seed} {brightness} {on} {rotation} {test} {snake} {serial}"


def frames(run):
    """The LED data of each refresh of a session, by its timestamp."""
    shown = {}
    at = None
    for line in run.lines:
        word, _, rest = line.partition(" ")
        if word == "refresh":
            at = int(rest)
            shown[at] = []
        elif word == "data" and at is not None:
            shown[at].append(rest.split(" ", 1)[1])
        elif word == "idle":
            at = None
    return {time: tuple(data) for time, data in shown.items()}


def polls(*times, base=T0):
    return [f"poll {base + time}" for time in times]


def two_animations():
    return show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": loop_of(2, 1), "b.odrg": loop_of(3, 7)}, min_seconds=60)


def target(**files):
    """A show of the installation's mapping, 60 x 60 on twenty legs."""
    show = {"version": 1, "brightness": 255, "items": [{"id": 1, "file": "a.odrg"}]}
    return {"mapping.json": support.mapping_texts()["legs-20"], "show.json": json.dumps(show), "a.odrg": support.clip(3, 60, 60, (1000, 1000)), **files}


class Pictures(unittest.TestCase):
    def test_a_file_of_frames_shows_as_its_own_playback_shows_it(self):
        played = frames(support.start(two_animations(), polls(*TIMES)))
        mirrored = frames(support.start(two_animations(), [mirror("b.odrg", 1, T0, 3000), *polls(*TIMES)]))
        alone = show_of([{"id": 2, "file": "b.odrg"}], {"b.odrg": loop_of(3, 7)}, min_seconds=60)
        self.assertEqual(mirrored, frames(support.start(alone, polls(*TIMES))))
        self.assertNotEqual(mirrored, played)

    def test_a_turn_joined_late_shows_the_point_it_has_come_to(self):
        played = frames(support.start(two_animations(), polls(0, *(4000 + time for time in TIMES))))
        joined = T0 + 10000
        mirrored = frames(support.start(two_animations(), [mirror("a.odrg", 1, joined - 4000, 2000), *polls(*TIMES, base=joined)]))
        self.assertEqual([mirrored[joined + time] for time in TIMES], [played[T0 + 4000 + time] for time in TIMES])

    def test_a_loop_not_known_is_decoded_as_its_first_loop(self):
        played = frames(support.start(two_animations(), polls(0, 300, 1000, 1700)))
        mirrored = frames(support.start(two_animations(), [mirror("a.odrg", 1, T0), *polls(0, 300, 1000, 1700)]))
        self.assertEqual(mirrored, played)

    def test_a_clock_shows_with_the_seed_it_is_given(self):
        show = {"version": 1, "brightness": 255, "min_seconds": 60, "items": [{"id": 3, "file": "c.odrgx"}]}
        files = {"mapping.json": support.mapping_texts()["legs-20"], "show.json": json.dumps(show), "c.odrgx": clock_of(seconds=2, canvas=(60, 60))}
        run = support.start(files, [*polls(*TIMES), support.line(T0 + 4100, "status")])
        seed = [reply for reply in replies(run) if "on" in reply][-1]["seed"]
        self.assertIsInstance(seed, int)
        mirrored = frames(support.start(files, [mirror("c.odrgx", 3, T0, 2000, seed), *polls(*TIMES)]))
        self.assertEqual(mirrored, frames(run))
        other = frames(support.start(files, [mirror("c.odrgx", 3, T0, 2000, seed + 1), *polls(*TIMES)]))
        self.assertNotEqual(other, frames(run))

    def test_the_brightness_it_is_given_and_the_leds_off(self):
        dimmed = frames(support.start(two_animations(), [support.line(T0, "brightness 100"), *polls(*TIMES)]))
        mirrored = frames(support.start(two_animations(), [mirror("a.odrg", 1, T0, 2000, brightness=100), *polls(*TIMES)]))
        self.assertEqual(mirrored, dimmed)
        dark = frames(support.start(two_animations(), [mirror("a.odrg", 1, T0, 2000, on=0), *polls(*TIMES)]))
        self.assertEqual(set(dark), {T0 + time for time in TIMES})
        self.assertTrue(all(set(data) == {"0"} for picture in dark.values() for data in picture))

    def test_nothing_or_a_missing_file_is_dark(self):
        for line in (mirror("", 1, T0), mirror("missing.odrg", 1, T0)):
            with self.subTest(line=line):
                dark = frames(support.start(two_animations(), [line, *polls(*TIMES)]))
                self.assertTrue(all(set(data) == {"0"} for picture in dark.values() for data in picture))

    def test_the_tests_show_as_the_board_shows_them(self):
        for command, test, snake in (("mapping test on", 1, 0), ("mapping test snake 3", 2, 3)):
            with self.subTest(command=command):
                shown = frames(support.start(target(), [support.line(T0, command), *polls(*TIMES)]))
                mirrored = frames(support.start(target(), [mirror("a.odrg", 1, T0, 2000, test=test, snake=snake), *polls(*TIMES)]))
                self.assertEqual(mirrored, shown)

    def test_a_rotation_turns_the_picture_as_the_show_turns_it(self):
        rotated = target(**{"rotation.txt": "1 90\n"})
        turned = frames(support.start(rotated, polls(*TIMES)))
        mirrored = frames(support.start(target(), [mirror("a.odrg", 1, T0, 2000, rotation=1), *polls(*TIMES)]))
        self.assertEqual(mirrored, turned)
        self.assertNotEqual(mirrored, frames(support.start(target(), polls(*TIMES))))

    def test_nothing_is_written_and_none_gives_the_show_back(self):
        script = [mirror("b.odrg", 1, T0, 3000), *polls(*TIMES), "mirror none", *polls(5000, 5300)]
        run, kept = support.start_and_keep(two_animations(), script)
        _, left = support.start_and_keep(two_animations(), [])
        self.assertEqual(kept, left)
        shown = frames(run)
        played = frames(support.start(two_animations(), polls(0)))
        self.assertEqual(shown[T0 + 5000], played[T0])


if __name__ == "__main__":
    unittest.main()

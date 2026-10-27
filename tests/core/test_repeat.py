import json
import unittest

from . import support
from .test_clocks import CANVAS as DRAWN_CANVAS
from .test_clocks import clock_of
from .test_clocks import show_of as drawn_show_of
from .test_drive import DONE, DRIVE, SHOW, asked, pictures, refusal, replies, with_drive
from .test_folders import WINDOW, WINDOWED
from .test_playback import T0, Playback
from .test_playlist import CANVAS, show_of, three, with_a_cycle
from .test_texts import pass_of, text_of
from .test_upload import Script


def counts(run_or_lines):
    """The animation, `repeat` and `loop` of each `status` of a session."""
    lines = run_or_lines if isinstance(run_or_lines, list) else run_or_lines.lines
    states = [json.loads(line[len("reply "):]) for line in lines if line.startswith('reply {"ok":true,"on"')]
    return [(state["animation"], state["repeat"], state["loop"]) for state in states]


def answers(lines):
    """The replies of a session that are no `status`, as values."""
    return [json.loads(line[len("reply "):]) for line in lines if line.startswith("reply ") and not line.startswith('reply {"ok":true,"on"')]


def first_poll():
    """The refresh at power-on, where the first turn begins."""
    return [f"poll {T0}"]


class TheForm(Playback):
    BAD = ["repeat", "repeat 1", "repeat 0 5", "repeat 1 0", "repeat 1 65536", "repeat x 5", "repeat 1 5x", "repeat 1 5 keep", "repeat 1 default 2",
           "repeat 1  5", "repeat 1 5 save x", "repeat 70000 1"]

    def test_words_out_of_its_forms_are_refused_first_and_an_invalid_show_next(self):
        invalid = support.with_show_fault(three())
        for files in (three(), invalid):
            run = support.start(files, first_poll() + asked(100, *self.BAD))
            self.assertEqual(replies(run), [refusal("bad-argument")] * len(self.BAD))
        run = support.start(invalid, first_poll() + asked(100, "repeat 1 5"))
        self.assertEqual(replies(run), [refusal("show-invalid")])

    def test_it_is_stale_while_no_turn_of_the_animation_is_reported(self):
        script = [support.line(T0, "repeat 1 2")] + first_poll() + asked(100, "repeat 2 2", "repeat 99 2", "repeat 3 2") + asked(32_000, "repeat 1 2")
        printed = self.assert_as_the_reference(three(), script)
        # Before the first refresh, the turns of other animations, an id of nothing, and a
        # turn that has moved on.
        self.assertEqual(answers(printed), [refusal("stale")] * 5)
        cycle = with_a_cycle(three(), {"id": 4, "cycle": [1, 2], "seconds": 5}, start=4)
        self.assertEqual(answers(self.assert_as_the_reference(cycle, first_poll() + asked(100, "repeat 1 2", "repeat 4 2"))), [refusal("stale")] * 2)
        empty = show_of([], {})
        self.assertEqual(answers(self.assert_as_the_reference(empty, first_poll() + asked(100, "repeat 1 2"))), [refusal("stale")])

    def test_it_is_stale_while_a_test_of_the_mapping_shows(self):
        files = dict(support.demo_show())
        run = support.start(files, first_poll() + asked(100, "mapping test on", "repeat 1 2", "status") + asked(200, "mapping test snake 3", "repeat 1 2"))
        self.assertEqual([reply.get("error") for reply in replies(run) if "on" not in reply], [None, "stale", None, "stale"])
        self.assertEqual(counts(run), [(None, None, None)])


class TheTurn(Playback):
    def test_a_turn_is_made_n_loops_long_from_its_first_frame(self):
        # The turn of animation 1, loops of 4 seconds, has 8 loops by `min_seconds`.
        script = first_poll() + asked(1000, "status", "repeat 1 2", "status") + asked(7980, "status") + asked(8000, "status")
        printed = self.assert_as_the_reference(three(), script)
        self.assertEqual(answers(printed), [DONE])
        self.assertEqual(counts(printed), [(1, 8, 1), (1, 2, 1), (1, 2, 2), (2, 3, 1)])

    def test_a_count_at_or_below_the_loop_in_progress_ends_the_turn_at_that_loops_end(self):
        script = first_poll() + asked(9000, "repeat 1 1", "status") + asked(11_980, "status") + asked(12_000, "status")
        printed = self.assert_as_the_reference(three(), script)
        self.assertEqual(counts(printed), [(1, 3, 3), (1, 3, 3), (2, 3, 1)])

    def test_the_longest_time_does_not_cut_it(self):
        # A longest time of 6 seconds cuts the turn in its second loop: 2 loops, the cut one
        # counted.
        files = three(first={"max_seconds": 6})
        script = first_poll() + asked(1000, "status", "repeat 1 3", "status") + asked(6000, "status") + asked(11_980, "status") + asked(12_000, "status")
        printed = self.assert_as_the_reference(files, script)
        self.assertEqual(counts(printed), [(1, 2, 1), (1, 3, 1), (1, 3, 2), (1, 3, 3), (2, 3, 1)])

    def test_nothing_restarts(self):
        times = [T0 + 20 * step for step in range(1, 300)]
        plain = support.start(three(), first_poll() + [f"poll {time}" for time in times])
        repeated = support.start(three(), first_poll() + [f"poll {T0 + 20}", support.line(T0 + 20, "repeat 1 2")] + [f"poll {time}" for time in times[1:]])
        self.assertEqual(pictures(plain), pictures(repeated))

    def test_a_text_counts_its_passes(self):
        text = text_of()
        total = pass_of(text)
        files = drawn_show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": text, "b.odrg": support.clip(2, *DRAWN_CANVAS, (1000,))}, min_seconds=3)
        script = first_poll() + asked(100, "repeat 1 5", "status") + asked(5 * total - 20, "status") + asked(5 * total, "status")
        printed = self.assert_as_the_reference(files, script)
        self.assertEqual(counts(printed), [(1, 5, 1), (1, 5, 5), (2, 3, 1)])

    def test_a_clock_counts_the_loops_of_its_seconds_and_keeps_its_seed(self):
        files = drawn_show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": clock_of(seconds=2), "b.odrg": support.clip(2, *DRAWN_CANVAS, (1000,))},
                              min_seconds=3)
        script = first_poll() + asked(1000, "status", "repeat 1 4", "status") + asked(7980, "status") + asked(8000, "status")
        printed = self.assert_as_the_reference(files, script)
        self.assertEqual(counts(printed), [(1, 2, 1), (1, 4, 1), (1, 4, 4), (2, 3, 1)])
        seeds = [json.loads(line[len("reply "):])["seed"] for line in printed if line.startswith('reply {"ok":true,"on"')]
        self.assertIsNotNone(seeds[0])
        self.assertEqual(seeds[:3], [seeds[0]] * 3)

    def test_a_card_animation_takes_it_as_an_item_does(self):
        # The card's `A.ODRG` loops in 3 seconds and has 2 loops by the show's 4 seconds.
        script = asked(0, "play 60001") + asked(20, "status") + asked(1000, "repeat 60001 3", "status") + asked(9_000, "status") + asked(9_020, "status")
        run = with_drive(SHOW, DRIVE, script)
        self.assertEqual(counts(run), [(60001, 2, 1), (60001, 3, 1), (60001, 3, 3), (60002, 2, 1)])

    def test_after_a_jump_it_acts_on_the_jumped_turn(self):
        # The jump to 3 begins its turn at 1,020; 2 loops of 45 seconds end it at 91,020.
        script = first_poll() + asked(1000, "play 3") + asked(1020, "repeat 1 2", "repeat 3 2", "status") + asked(91_000, "status") + asked(91_020, "status")
        printed = self.assert_as_the_reference(three(), script)
        self.assertEqual(answers(printed), [DONE, refusal("stale"), DONE])
        self.assertEqual(counts(printed), [(3, 2, 1), (3, 2, 2), (1, 8, 1)])

    def test_a_count_above_65535(self):
        # A loop of 1 ms: 100,000 loops last the show's 100 seconds; at 70 seconds the loop
        # in progress is above 65,535, and a smaller count ends the turn with it.
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": support.clip(1, *CANVAS, (1,)), "b.odrg": support.clip(2, *CANVAS, (1000,))},
                        min_seconds=100)
        script = first_poll() + asked(70_000, "status", "repeat 1 5", "status") + asked(70_020, "status")
        printed = self.assert_as_the_reference(files, script)
        self.assertEqual(counts(printed), [(1, 100_000, 70_001), (1, 70_001, 70_001), (2, 100, 1)])


class ItsLifetime(Playback):
    def repeated_then(self, *commands, at=2000):
        """`repeat 1 2` at 1 second, these commands at `at`, and the counts of the turns
        after them."""
        script = first_poll() + asked(1000, "repeat 1 2") + asked(at, *commands) + asked(at + 20, "status") + asked(at + 40, "status")
        return support.start(three(), script)

    def test_a_new_turn_drops_it(self):
        for commands in (["play 1"], ["play all"], ["ignore 1 1", "ignore 1 0", "play 1"]):
            with self.subTest(commands=commands):
                run = self.repeated_then(*commands)
                self.assertEqual(counts(run)[-1], (1, 8, 1))

    def test_ignore_ends_the_turn_at_once_and_its_next_turn_has_its_own_count(self):
        script = first_poll() + asked(1000, "repeat 1 2") + asked(2000, "ignore 1 1", "status") + asked(2020, "status", "ignore 1 0") + asked(77_020, "status")
        run = support.start(three(), script)
        self.assertEqual(counts(run), [(2, None, None), (2, 3, 1), (1, 8, 1)])

    def test_power_and_brightness_keep_it_and_the_loops_run_on_in_the_dark(self):
        run = self.repeated_then("off", "brightness 0", "on", "off")
        self.assertEqual(counts(run), [(1, 2, 1), (1, 2, 1)])
        later = support.start(three(), first_poll() + asked(1000, "repeat 1 2", "off", "brightness 0") + asked(7980, "status") + asked(8000, "status"))
        self.assertEqual(counts(later), [(1, 2, 2), (2, 3, 1)])

    def test_a_move_of_the_order_keeps_it(self):
        revision = replies(support.start(three(), asked(0, "order get")))[0]["revision"]
        run = support.start(three(), first_poll() + asked(1000, "repeat 1 2") + asked(2000, f"order move {revision} 3 2", "status") + asked(8000, "status"))
        self.assertEqual(replies(run)[1], DONE)
        self.assertEqual(counts(run), [(1, 2, 1), (3, 1, 1)])

    def test_a_removal_an_upload_and_a_quarantine_drop_it(self):
        data = support.clip(9, *CANVAS, (4000,))
        removed = support.start(three(), first_poll() + asked(1000, "repeat 1 2") + asked(2000, "remove 1") + asked(2020, "status"))
        self.assertEqual(counts(removed), [(2, 3, 1)])
        uploaded = support.start(three(), Script().polls(1).line("repeat 1 2").polls(5).upload(1, "four.odrg", data).polls(2).line("status").lines)
        self.assertEqual(counts(uploaded), [(1, 8, 1)])
        quarantined = support.start(three(), first_poll() + asked(1000, "repeat 1 2") + asked(4100, "status"), ["--remove-after", "four.odrg", "1"])
        self.assertEqual(counts(quarantined)[-1][0], 2)

    def test_a_card_pulled_out_drops_it(self):
        script = asked(0, "play 60001") + asked(20, "repeat 60001 3") + ["drive pull"] + asked(40, "status") + ["drive plug"]
        script += [f"poll {T0 + 40 + 20 * step}" for step in range(1, 40)] + asked(1000, "play 60001") + asked(1020, "status")
        run = with_drive(SHOW, DRIVE, script)
        self.assertEqual(counts(run), [(1, 1, 1), (60001, 2, 1)])

    def test_a_test_of_the_mapping_drops_it(self):
        files = dict(support.demo_show())
        before = counts(support.start(files, first_poll() + asked(100, "status")))[0]
        run = support.start(files, first_poll() + asked(100, "repeat 1 1", "mapping test on") + asked(200, "mapping test off") + asked(220, "status"))
        self.assertEqual(counts(run), [before[:2] + (1,)])

    def test_a_restart_drops_it(self):
        files = three()
        with support.installed(files) as folder:
            support.session(folder, first_poll() + asked(1000, "repeat 1 2"))
            again = support.session(folder, first_poll() + asked(1000, "status"))
        self.assertEqual(counts(again), [(1, 8, 1)])

    def test_a_folders_window_that_ends_during_the_turn_waits_for_its_end(self):
        # The turn of `night/comet.odrg`, 5,000 ms a loop, begins at 86,398,020; 3 loops
        # end it at 86,413,020, past the window's end at 86,400,000.
        script = asked(0, "play 60008") + asked(20) + asked(WINDOW - 1000, "repeat 60004 3", "status") + asked(WINDOW + 3_100, "status") + asked(WINDOW + 13_100, "status")
        run = with_drive(SHOW, WINDOWED, script)
        states = [reply for reply in replies(run) if "on" in reply]
        self.assertEqual([(state["playing"], state["animation"], state["repeat"], state["left"]) for state in states],
                         [(60008, 60004, 3, 1), (60008, 60004, 3, 0), (60009, 60005, 2, 86399)])

    def test_the_rounds_after_a_long_gap_stay_exact(self):
        script = first_poll() + asked(1000, "repeat 1 2", "status") + asked(10 * 3_600_000, "status") + asked(10 * 3_600_000 + 50_000, "status")
        self.assert_as_the_reference(three(), script)


if __name__ == "__main__":
    unittest.main()

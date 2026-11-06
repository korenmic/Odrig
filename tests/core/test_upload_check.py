"""The check of an uploaded file takes its steps at every refresh, in step or late, each
charged by its work, within a budget that the refresh rate paces."""
import itertools
import json
import random
import unittest

from odrig import jsonframes, odrg

from . import huge_tail, support
from .test_body_faults import show_with
from .test_bounded import small
from .test_content import OK, refused, replies, small_show
from .test_playback import T0
from .test_upload import ITEMS, Script, Uploads

CLOCK = support.ROOT / "collection" / "card" / "clocks" / "time-original-5-every-row-another-time.odrg"
BUSY = refused("busy")


def runs(texts):
    """Replies in runs of equal ones, for a failure to show."""
    return ", ".join(f"{text} x{len(list(group))}" for text, group in itertools.groupby(texts))


def ends_after_each_poll(script, data, count, every):
    """Polls at this period, `upload end` after each."""
    for _ in range(count):
        script.polls(1, every).end(data)
    return script


def by_schedule(periods, until):
    """The times of polls, from T0 on, that come at each period of a schedule from its
    start, a time after T0, up to `until` after T0: `[(0, 20), (3000, 50)]`."""
    times = []
    at = 0
    for number, (start, every) in enumerate(periods):
        end = periods[number + 1][0] if number + 1 < len(periods) else until
        at = max(at, start)
        while at < end:
            times.append(T0 + at)
            at += every
    return times


def checks_of(printed):
    """`(time, pace, debt, fell)` of each refresh of the check: the `check` lines of
    `--trace-check` with the time of their refresh."""
    found = []
    time = None
    for line in printed:
        if line.startswith("refresh "):
            time = int(line.split()[1])
        elif line.startswith("check "):
            pace, debt, fell = (int(word) for word in line.split()[1:])
            found.append((time, pace, debt, fell))
    return found


def most_read(printed):
    """The most bytes of `upload.part` that `read_at` gave within one refresh of a run with
    `--trace-read-at`."""
    read = most = 0
    for line in printed:
        if line.startswith("read_at upload.part "):
            read += int(line.split()[3])
        elif line.startswith("refresh "):
            most = max(most, read)
            read = 0
        elif line.startswith(("idle ", "reply ")):
            read = 0
    return most


def tiny_records():
    """A clip of 60 x 6 with a palette in which one pixel changes at each of 2,000 frames:
    records of a few bytes."""
    palette = [bytes((0, 0, 0)), bytes((255, 64, 0)), bytes((0, 200, 80)), bytes((40, 40, 255)), bytes((255, 255, 255))]
    picture = [palette[0]] * 360
    frames = []
    for number in range(2000):
        picture[number * 7 % 360] = palette[1 + number // 360 % 4]
        frames.append((20, b"".join(picture)))
    return odrg.encode(jsonframes.Animation(60, 6, tuple(frames)))


def noise():
    """A clip of 60 x 60, three bytes a pixel, uncompressed, of ten pictures of noise: stored
    records of 10,805 bytes."""
    rng = random.Random(81)
    return odrg.encode(jsonframes.Animation(60, 60, tuple((20, rng.randbytes(10800)) for _ in range(10))), compressed=False)


class AtEveryRefresh(Uploads):
    def test_a_host_that_refreshes_every_45_ms_ends_the_check(self):
        # No refresh of this host is in step with the one before it.
        files = small_show(ITEMS, start=6)
        clip = support.clip(54, 60, 6, (20,) * 300)
        script = Script().send(9, "new.odrg", clip)
        sent = len(script.sent)
        count = 60000 // 45 + 10
        ends_after_each_poll(script, clip, count, 45)
        ends = replies(support.start(files, script.lines).lines)[sent:]
        at = support.check_end(support.check_steps(clip), script.refreshes(), T0, 0)
        self.assertEqual(at + 1, 76)
        self.assertEqual(ends, [BUSY] * at + [OK] + [refused("no-upload")] * (count - at - 1), runs(ends))
        self.play(files, script)
        self.assertEqual(self.answers("upload end"), ends)
        self.assertEqual(self.left["new.odrg"], clip)


class TheOwnersClock(unittest.TestCase):
    """The tracked clock of 14,399 frames of 60 x 60, uploaded to a board without show
    files, `upload end` after every refresh from its last byte on."""

    def check_within(self, every, most):
        data = CLOCK.read_bytes()
        self.assertEqual(len(data), 471095)
        steps = support.check_steps(data, (60, 60))
        self.assertEqual(len(steps), 14401)
        polls = [T0 + every * step for step in range(most)]
        at = support.check_end(steps, support.refresh_times(polls, T0), T0, 0)
        self.assertIsNotNone(at, f"the rule ends no check within {most} refreshes of {every} ms")
        script = Script().send(1, "clock.odrg", data)
        sent = len(script.sent)
        ends_after_each_poll(script, data, at + 3, every).line("list")
        given = replies(support.start({}, script.lines).lines)[sent:]
        ends, listed = given[:-1], json.loads(given[-1])
        self.assertEqual(ends, [BUSY] * at + [OK] + [refused("no-upload")] * 2, runs(ends))
        self.assertEqual([(item["id"], item["file"], item["bytes"]) for item in listed["items"]], [(1, "clock.odrg", 471095)])
        return at + 1

    def test_a_host_at_50_a_second_has_it_checked_within_400_refreshes(self):
        self.assertLessEqual(self.check_within(20, 400), 400)

    def test_a_host_at_33_a_second_has_it_checked_within_400_refreshes(self):
        self.assertLessEqual(self.check_within(30, 400), 400)

    def test_a_host_at_22_a_second_has_it_checked_within_1300_refreshes(self):
        self.assertLessEqual(self.check_within(45, 1300), 1300)

    def test_a_host_at_20_a_second_has_it_checked_within_2400_refreshes(self):
        self.assertLessEqual(self.check_within(50, 2400), 2400)


class TheFade(Uploads):
    """A fade of 60 x 60, three bytes a pixel, uncompressed, whose every record walks the
    picture, on a board without show files and a host that refreshes every 20 ms."""

    def script(self):
        fade = support.fade()
        steps = support.check_steps(fade, (60, 60))
        at = support.check_end(steps, support.refresh_times([T0 + 20 * step for step in range(2000)], T0), T0, 0)
        script = ends_after_each_poll(Script().send(1, "fade.odrg", fade), fade, at + 3, 20).line("list")
        return fade, script, at

    def test_its_check_is_the_reference_players_refresh_for_refresh(self):
        fade, script, at = self.script()
        self.play({}, script, ["--trace-check"])
        self.assertEqual(self.answers("upload end"), [BUSY] * at + [OK] + [refused("no-upload")] * 2)
        checks = checks_of(self.printed)
        self.assertEqual(len(checks), at + 1)
        self.assertEqual(max(pace for _, pace, _, _ in checks), 3)
        self.assertEqual(json.loads(self.answers("list")[0])["items"][0]["bytes"], len(fade))

    def test_a_refresh_reads_of_the_file_its_budget_and_one_step_at_most(self):
        fade, script, _ = self.script()
        most = most_read(support.start({}, script.lines, ["--trace-read-at"]).lines)
        largest = max(call.charge for call in support.taken_in(fade))
        self.assertGreater(most, 0)
        self.assertLessEqual(most, 2048 + largest + 256)


class ThePace(Uploads):
    """The dense clip of 30 s on the two-leg show, under hosts whose rate changes during
    the check."""

    def run_schedule(self, periods):
        clip = support.dense_clip(60, 6, 30)
        polls = by_schedule(periods, 60000)
        refreshes = support.refresh_times(polls, T0)
        at = support.check_end(support.check_steps(clip), refreshes, T0, 0)
        script = Script().send(9, "new.odrg", clip)
        for time in polls[:polls.index(refreshes[at]) + 2]:
            script.time = time
            script.polls(1).end(clip)
        self.play(small_show(ITEMS, start=6), script, ["--trace-check"])
        ends = self.answers("upload end")
        self.assertEqual(ends[ends.index(OK) - 1:ends.index(OK) + 1], [BUSY, OK])
        return checks_of(self.printed)

    def test_a_host_that_slows_to_20_a_second_lowers_the_pace_and_raises_it_again_from_50(self):
        checks = self.run_schedule([(0, 20), (3000, 50), (6000, 20)])
        # At 50 a second the pace rises to 3 by the third second.
        self.assertEqual([pace for time, pace, _, _ in checks if time < T0 + 3000][-1], 3)
        fell = next(number for number, (_, _, _, mark) in enumerate(checks) if mark)
        self.assertGreaterEqual(checks[fell][0], T0 + 3000)
        self.assertLess(checks[fell][1], 3)
        lowest = min(pace for _, pace, _, _ in checks[fell:])
        self.assertEqual(lowest, 0)
        after = [pace for time, pace, _, _ in checks if time >= T0 + 7000]
        self.assertGreater(max(after), lowest)
        self.assertTrue(all(mark for _, _, _, mark in checks[fell:]))

    def test_a_trial_that_costs_the_rate_is_taken_back_at_the_middle_of_its_second(self):
        checks = self.run_schedule([(0, 30), (3000, 60), (3500, 30)])
        self.assertEqual([pace for time, pace, _, _ in checks if time < T0 + 3000][-1], 3)
        fell = next(number for number, (_, _, _, mark) in enumerate(checks) if mark)
        time, pace, _, _ = checks[fell]
        self.assertTrue(T0 + 3500 <= time < T0 + 4000, time)
        self.assertEqual(pace, 2)
        # At 33 a second it does not rise again.
        self.assertEqual({pace for _, pace, _, _ in checks[fell:]}, {2})
        self.assertGreater(checks[-1][0], T0 + 6000)


class TheBounds(Uploads):
    def test_a_refresh_takes_at_most_64_steps_of_small_records(self):
        clip = tiny_records()
        steps = support.check_steps(clip)
        self.assertEqual(len(steps), 2002)
        # The first record takes the palette and the header of the stream's block as well.
        self.assertLess(steps[1][0], 256)
        self.assertLess(max(charge for charge, _ in steps[2:]), 32)
        # The check begins late in the first second, and the pace is 2 in the second.
        script = Script().polls(45).send(9, "new.odrg", clip)
        ends_after_each_poll(script, clip, script.needed(clip) + 1, 20)
        self.play(small_show(ITEMS, start=6), script, ["--trace-check"])
        self.assertIn(OK, self.answers("upload end"))
        pace = support.CheckPace(steps)
        refreshes = script.refreshes()
        counts = {}
        taken = []
        for number, time in enumerate(refreshes):
            second = (time - T0) // 1000
            counts[second] = counts.get(second, 0) + 1
            if number < 45 or pace.ended:
                continue
            new_second = number > 0 and second != (refreshes[number - 1] - T0) // 1000
            took = pace.refresh((time - T0) % 1000, new_second, counts.get(second - 1, 0), counts[second])
            taken.append((pace.pace, took, pace.ended))
        fast = [took for at_pace, took, ended in taken if at_pace >= 2 and not ended]
        self.assertGreater(len(fast), 5)
        self.assertEqual(set(fast), {64})
        self.assertLess(max(took for at_pace, took, _ in taken if at_pace == 1), 64)
        self.assertEqual([line for line in self.printed if line.startswith("check ")], [f"check {at_pace} 0 0" for at_pace, _, _ in taken])

    def test_a_refresh_reads_of_a_stream_of_empty_blocks_its_budget_and_one_step_at_most(self):
        # Each record lies behind 2,000 bytes of the stream that inflate to nothing.
        clip = support.with_empty_blocks(support.clip(81, 60, 6, (20,) * 100), 400)
        script = Script().send(9, "blocks.odrg", clip)
        ends_after_each_poll(script, clip, script.needed(clip) + 1, 20)
        run = support.start(small_show(ITEMS, start=6), script.lines, ["--trace-read-at"])
        largest = max(charge for charge, _ in support.check_steps(clip))
        self.assertLessEqual(most_read(run.lines), 2048 + largest + 256)
        self.assertGreater(largest, 2000)
        self.assertEqual(replies(run.lines)[len(script.sent) - 2:], [OK, refused("no-upload")])

    def test_a_slice_of_settling_ends_the_steps_of_its_refresh_and_leaves_no_debt(self):
        data = small()
        script = Script().send(9, "new.odrg", data)
        ends_after_each_poll(script, data, 40, 20)
        run = support.start(show_with(support.clip(1, 4, 4), sound=2), script.lines, ["--trace-check"])
        checks = checks_of(run.lines)
        self.assertEqual(len(checks), 33)
        self.assertEqual({(pace, debt) for _, pace, debt, _ in checks}, {(1, 0)})
        ends = replies(run.lines)[len(script.sent) - 40:]
        self.assertEqual(ends[31:34], [BUSY, json.dumps({"ok": False, "error": "bad-file", "reason": huge_tail.REASON}, separators=(",", ":")), refused("no-upload")])

    def test_a_host_that_rests_to_pay_a_debt_keeps_the_upload(self):
        # Records of 10,805 bytes leave a debt of 15 at pace 0: sixteen refreshes, 62.4 s at
        # a refresh every 3,900 ms, from one step to the next.
        clip = noise()
        self.assertEqual({charge for charge, _ in support.check_steps(clip, (60, 60))[1:-1]}, {10805})
        script = Script().send(1, "noise.odrg", clip)
        at = support.check_end(support.check_steps(clip, (60, 60)), support.refresh_times([T0 + 3900 * step for step in range(2000)], T0), T0, 0)
        ends_after_each_poll(script, clip, at + 2, 3900)
        self.play({}, script, ["--trace-check"])
        self.assertEqual(self.answers("upload end"), [BUSY] * at + [OK, refused("no-upload")])
        stepped = [time for time, _, debt, _ in checks_of(self.printed) if debt == 15]
        gaps = {later - earlier for earlier, later in zip(stepped, stepped[1:])}
        self.assertEqual(gaps, {16 * 3900})
        self.assertGreater(16 * 3900, 60000)

    def test_a_host_that_asks_for_no_refresh_for_60_seconds_loses_the_upload(self):
        clip = support.dense_clip(60, 6, 1)
        for quiet, kept in ((59980, True), (60000, False)):
            with self.subTest(quiet=quiet):
                script = Script().polls(3).send(9, "new.odrg", clip).polls(3)
                script.wait(quiet - 20).polls(1).end(clip)
                self.play(small_show(ITEMS, start=6), script)
                self.assertEqual(self.answers("upload end"), [BUSY if kept else refused("no-upload")])
                self.assertEqual("upload.part" in self.left, kept)


if __name__ == "__main__":
    unittest.main()

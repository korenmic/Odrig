"""The check of an uploaded file takes its steps at every refresh, in step or late, each
charged by its work, within a budget that the refresh rate paces."""
import itertools
import json
import unittest

from . import support
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


if __name__ == "__main__":
    unittest.main()

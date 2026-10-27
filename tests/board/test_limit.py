import json
import pathlib
import tempfile
import time
import unittest

from fwtool import board, limit, storage

from odrig import limits as current_limits

from . import PORT, support

# What the firmware gives the core as the wall's budget, while no budgets are saved, with
# WLED's maximum of 850 mA: the maximum less what WLED keeps for the chip. The probe reads
# it as `limit_ma`. It is also the largest wall budget the bench takes.
ALLOWED_WITH_850 = 730
LEDS_OF_THE_TARGET = 3600
LEDS_OF_A_LEG = 180
SECONDS = 5


def reports_while_it_plays():
    """One report for each of some seconds in a row, once the show plays after a restart.
    The counts that run from one report to the next start with the first of them."""
    deadline = time.monotonic() + support.START_SECONDS
    while support.probe()["sent"] == 0 and time.monotonic() < deadline:
        time.sleep(0.5)
    time.sleep(2.0)
    support.probe()
    return support.each_second(SECONDS)


def saved(*words):
    """Sends a command that saves budgets, once the board has read its animations: until
    then a save is refused with `busy`."""
    board.settled(PORT, board.SETTLE_SECONDS)
    return support.command(PORT, "limits", *words)


class TheLimits(unittest.TestCase):
    """WLED's stored maximum and the core's limiting on the board, with Hello world for the
    target at the brightest the wired strip allows. First with the limit of the limit file;
    then the wall's budget of 730 mA is saved and `set-limit` stores a maximum of 0, so that
    the bench never plays without a wall budget across the restart; then the limit of the
    limit file is stored again, and `limits default` ends the run. The runs are made once,
    before the tests, which look at what they left. WLED's own limiter dims nothing in any
    of them: the core limits."""

    @classmethod
    def setUpClass(cls):
        support.ensure("probe")
        with support.show_folder(support.TARGET, [("hello.odrg", support.hello_for(support.TARGET))], support.BRIGHTEST) as folder:
            support.ensure_installed(folder)
        cls.saving, cls.ended = False, False
        cls.addClassCleanup(cls.end_a_run_that_stopped)
        holder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(holder.cleanup)
        off = pathlib.Path(holder.name, "limit.json")
        off.write_text(json.dumps({"milliamps": 0}))

        cls.tracked = support.on_port("set-limit", "--wait", support.START_SECONDS)
        cls.tracked_reports = reports_while_it_plays()
        cls.at_start = support.limits()
        cls.leg_budgets = [leg[2] for leg in cls.at_start["legs"]]

        cls.saving = True
        cls.saved_wall = saved("wall", str(ALLOWED_WITH_850))
        if cls.saved_wall != (0, {"ok": True}):
            raise AssertionError(f"`limits wall {ALLOWED_WITH_850}` was not saved, so the maximum of 0 is not stored: {cls.saved_wall}")
        cls.after_the_save = support.limits()

        started = time.monotonic()
        cls.off = support.on_port("set-limit", "--settings", off, "--wait", support.START_SECONDS)
        cls.seconds = time.monotonic() - started
        cls.off_reports = reports_while_it_plays()
        cls.off_limits = support.limits()
        cls.off_read = support.on_port("read-limit")
        cls.off_image = support.storage_image()

        cls.on = support.on_port("set-limit", "--wait", support.START_SECONDS)
        cls.on_reports = reports_while_it_plays()
        cls.on_limits = support.limits()
        cls.on_read = support.on_port("read-limit")
        cls.on_image = support.storage_image()

        cls.defaulted = saved("default")
        cls.at_the_end = support.limits()
        cls.ended = True
        seen = {name: [[report[member] for report in reports] for member in ("sent", "limited", "limit_ma", "used_ma")]
                for name, reports in (("tracked", cls.tracked_reports), ("off", cls.off_reports), ("with_850", cls.on_reports))}
        walls = {name: reply["wall"] for name, reply in (("at_start", cls.at_start), ("off", cls.off_limits), ("with_850", cls.on_limits), ("at_the_end", cls.at_the_end))}
        print(json.dumps({"set_limit_seconds": round(cls.seconds, 1), "sent_limited_limit_ma_used_ma": seen, "walls": walls, "saved_at_start": cls.at_start["saved"]}))

    @classmethod
    def end_a_run_that_stopped(cls):
        """After a run that stopped once it began to save budgets: the limit of the limit
        file is stored again before the defaults are put back, so that the bench never plays
        without a wall budget."""
        if not cls.saving or cls.ended:
            return
        support.ensure_settings()
        saved("default")

    def lines(self, done, first):
        """What `set-limit` prints: the layout of the board's table, the line of the limit
        and the board's reply to `status`."""
        self.assertEqual(done.status, 0, done.err)
        lines = done.out.splitlines()
        self.assertEqual(len(lines), 3, done.out)
        self.assertTrue(lines[0].startswith("layout: "), lines[0])
        self.assertEqual(lines[1], first)
        reply = json.loads(lines[2])
        self.assertTrue(reply["ok"])
        self.assertLessEqual(reply["brightness"], support.BRIGHTEST)

    def read_as(self, done, line):
        """What `read-limit` prints: the layout of the board's table and the line of the
        limit."""
        self.assertEqual(done.status, 0, done.err)
        lines = done.out.splitlines()
        self.assertTrue(lines[0].startswith("layout: "), lines[0])
        self.assertEqual(lines[1:], [line])

    def wled_dims_nothing(self, reports, limit_ma):
        """WLED's limiter is off: the probe counts no send as dimmed, WLED estimates nothing,
        and `limit_ma` still reads WLED's maximum less 120 mA."""
        for report in reports:
            self.assertGreaterEqual(report["sent"], 20, report)
            self.assertEqual(report["limited"], 0, report)
            self.assertEqual((report["limit_ma"], report["used_ma"]), (limit_ma, 0), report)
            self.assertIsNone(report["error"])

    def held_by_the_wall(self, reply, saved_budgets):
        """The core holds the wall at its lowest level: the budget of 730 mA is below the
        3,600 mA the target's LEDs draw at rest, and every lit channel is sent as 1. The
        legs keep the budgets they had at the start, and a leg without one is not limited
        by a budget of its own."""
        self.assertEqual(reply["saved"], saved_budgets)
        self.assertIsNone(reply["next"])
        legs = reply["legs"]
        self.assertEqual([(leg[0], leg[1], leg[2]) for leg in legs], [(number, LEDS_OF_A_LEG, budget) for number, budget in enumerate(self.leg_budgets, 1)])
        for leg in legs:
            self.assertLessEqual(LEDS_OF_A_LEG, leg[3])
            self.assertLessEqual(leg[3], current_limits.estimate(bytes([1] * 3 * LEDS_OF_A_LEG)), leg)
            if leg[2] == 0:
                self.assertEqual(leg[4], 0, leg)
        self.assertEqual(reply["wall"], [LEDS_OF_THE_TARGET, ALLOWED_WITH_850, sum(leg[3] for leg in legs), 1])

    def test_with_the_limit_of_the_limit_file_wled_dims_nothing(self):
        self.assertEqual(limit.read(), 850)
        self.lines(self.tracked, "limit: 850 mA")
        self.wled_dims_nothing(self.tracked_reports, ALLOWED_WITH_850)

    def test_without_saved_budgets_the_core_holds_the_wall_within_the_default(self):
        if self.at_start["saved"]:
            self.skipTest("budgets were saved on the board at the start, so the board's default was not in force and is not checked")
        self.held_by_the_wall(self.at_start, False)

    def test_the_wall_budget_is_saved_before_the_maximum_of_0_is_stored(self):
        self.assertEqual(self.saved_wall, (0, {"ok": True}))
        self.held_by_the_wall(self.after_the_save, True)
        kept = current_limits.loads(storage.show_of(self.off_image)[current_limits.NAME])
        self.assertEqual(kept.wall, ALLOWED_WITH_850)
        self.assertEqual([kept.of(number) for number in range(1, 21)], self.leg_budgets)

    def test_with_a_maximum_of_0_wled_dims_nothing_and_the_saved_wall_budget_holds(self):
        self.lines(self.off, "limit: off")
        self.wled_dims_nothing(self.off_reports, 0)
        self.held_by_the_wall(self.off_limits, True)

    def test_the_maximum_of_0_is_what_storage_holds_and_what_the_tool_reports(self):
        self.read_as(self.off_read, "limit: off")
        self.assertEqual(limit.stored(self.off_image), 0)

    def test_with_the_limit_of_the_limit_file_again_wled_dims_nothing_and_the_saved_wall_budget_holds(self):
        self.lines(self.on, "limit: 850 mA")
        self.wled_dims_nothing(self.on_reports, ALLOWED_WITH_850)
        self.held_by_the_wall(self.on_limits, True)

    def test_the_limit_of_the_limit_file_is_what_storage_holds_and_what_the_tool_reports(self):
        self.read_as(self.on_read, "limit: 850 mA")
        self.assertEqual(limit.stored(self.on_image), 850)

    def test_only_the_limit_changed_in_storage(self):
        old, new = storage.files_in(storage.mount(self.off_image)), storage.files_in(storage.mount(self.on_image))
        self.assertEqual(sorted(new), sorted(old))
        for path in old:
            if path != "/cfg.json":
                self.assertTrue(new[path] == old[path], path)
        was, now = json.loads(old["/cfg.json"]), json.loads(new["/cfg.json"])
        self.assertEqual((was["hw"]["led"].pop("maxpwr"), now["hw"]["led"].pop("maxpwr")), (0, 850))
        self.assertEqual(json.dumps(now), json.dumps(was))

    def test_the_run_ends_with_the_defaults(self):
        self.assertEqual(self.defaulted, (0, {"ok": True}))
        self.assertFalse(self.at_the_end["saved"])
        self.assertEqual([leg[2] for leg in self.at_the_end["legs"]], [0] * len(self.leg_budgets))


if __name__ == "__main__":
    unittest.main()

import json
import pathlib
import tempfile
import time
import unittest

from fwtool import limit

from . import support

# What WLED's limiter allows the LEDs with a maximum of 850 mA: the maximum less what it
# counts for the chip.
ALLOWED_WITH_850 = 730
LEDS_OF_THE_TARGET = 3600
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


class TheLimiter(unittest.TestCase):
    """`set-limit` on the board, with Hello world for the target at the brightest the wired
    strip allows: first with the limiter off, then with the limit of the limit file. Both
    runs are made once, before the tests, which look at what they left."""

    @classmethod
    def setUpClass(cls):
        support.ensure("probe")
        with support.show_folder(support.TARGET, [("hello.odrg", support.hello_for(support.TARGET))], support.BRIGHTEST) as folder:
            support.ensure_installed(folder)
        holder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(holder.cleanup)
        off = pathlib.Path(holder.name, "limit.json")
        off.write_text(json.dumps({"milliamps": 0}))

        started = time.monotonic()
        cls.off = support.on_port("set-limit", "--settings", off, "--wait", support.START_SECONDS)
        cls.seconds = time.monotonic() - started
        cls.off_reports = reports_while_it_plays()
        cls.off_read = support.on_port("read-limit")
        cls.off_image = support.storage_image()

        cls.on = support.on_port("set-limit", "--wait", support.START_SECONDS)
        cls.on_reports = reports_while_it_plays()
        cls.on_read = support.on_port("read-limit")
        cls.on_image = support.storage_image()
        seen = {name: [[report[member] for report in reports] for member in ("sent", "limited", "limit_ma", "used_ma")]
                for name, reports in (("off", cls.off_reports), ("with_850", cls.on_reports))}
        print(json.dumps({"set_limit_seconds": round(cls.seconds, 1), "sent_limited_limit_ma_used_ma": seen}))

    def lines(self, done, first):
        self.assertEqual(done.status, 0, done.err)
        lines = done.out.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], first)
        reply = json.loads(lines[1])
        self.assertTrue(reply["ok"])
        self.assertLessEqual(reply["brightness"], support.BRIGHTEST)

    def test_with_the_limiter_off_no_send_is_dimmed(self):
        self.lines(self.off, "limit: off")
        for report in self.off_reports:
            self.assertGreaterEqual(report["sent"], 20, report)
            self.assertEqual(report["limited"], 0, report)
            self.assertEqual((report["limit_ma"], report["used_ma"]), (0, 0), report)
            self.assertIsNone(report["error"])

    def test_the_limiter_off_is_what_storage_holds_and_what_the_tool_reports(self):
        self.assertEqual(self.off_read.out, "limit: off\n")
        self.assertEqual(limit.stored(self.off_image), 0)

    def test_with_the_limit_of_the_limit_file_every_send_is_dimmed(self):
        self.assertEqual(limit.read(), 850)
        self.lines(self.on, "limit: 850 mA")
        for report in self.on_reports:
            self.assertGreaterEqual(report["sent"], 20, report)
            self.assertGreaterEqual(report["limited"], report["sent"] - 5, report)
            self.assertEqual((report["limit_ma"], report["used_ma"]), (ALLOWED_WITH_850, LEDS_OF_THE_TARGET), report)

    def test_the_limit_of_the_limit_file_is_what_storage_holds_and_what_the_tool_reports(self):
        self.assertEqual(self.on_read.out, "limit: 850 mA\n")
        self.assertEqual(limit.stored(self.on_image), 850)

    def test_only_the_limit_changed_in_storage(self):
        from fwtool import storage
        old, new = storage.files_in(storage.mount(self.off_image)), storage.files_in(storage.mount(self.on_image))
        self.assertEqual(sorted(new), sorted(old))
        for path in old:
            if path != "/cfg.json":
                self.assertTrue(new[path] == old[path], path)
        was, now = json.loads(old["/cfg.json"]), json.loads(new["/cfg.json"])
        self.assertEqual((was["hw"]["led"].pop("maxpwr"), now["hw"]["led"].pop("maxpwr")), (0, 850))
        self.assertEqual(json.dumps(now), json.dumps(was))


if __name__ == "__main__":
    unittest.main()

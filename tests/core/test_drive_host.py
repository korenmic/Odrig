"""The host's side of a drive: it is listed only when the core asks, and says whether the core
may write it."""

import json
import unittest

from . import support
from .test_drive import DRIVE, SHOW, a_drive, asked, listed, loop_of, replies
from .test_playback import T0


def polls(begin, count):
    """Refreshes from a time after power-on on, so many: the drive's check takes them."""
    return [f"poll {T0 + begin + 20 * step}" for step in range(count)]


def drive_lines(run):
    return [line for line in run.lines if line.startswith("drive ")]


class Listing(unittest.TestCase):
    def test_a_drive_without_a_catalog_is_listed_once_when_it_is_plugged_in(self):
        with a_drive(DRIVE) as top:
            run = support.start(SHOW, ["drive plug"] + polls(0, 200) + asked(4000, "list"), ["--drive", top, "--trace-drive", "--drive-pulled"])
        self.assertEqual(drive_lines(run), ["drive list 2"])
        self.assertEqual(listed(replies(run)[0]), [(1, "four.odrg"), (60001, "A.ODRG"), (60002, "b.odrg")])

    def test_a_drive_with_sub_folders_is_listed_depth_first_by_the_paths_of_its_files(self):
        drive = {**DRIVE, "night/comet.odrg": loop_of(2, 9), "night/deep/x.odrg": loop_of(3, 10), "a b/c.odrg": loop_of(2, 11), ".hid/h.odrg": loop_of(2, 12),
                 "night/deep/deeper/more/z.odrg": loop_of(2, 13), "System Volume Information/s.odrg": loop_of(2, 14)}
        with a_drive(drive) as top:
            run = support.start(SHOW, ["drive plug"] + polls(0, 500) + asked(10100, "list"), ["--drive", top, "--trace-drive", "--drive-pulled"])
        self.assertEqual(drive_lines(run), ["drive list 5"])
        self.assertEqual(listed(replies(run)[0]), [(1, "four.odrg"), (60001, "A.ODRG"), (60002, "b.odrg"), (60003, "a b/c.odrg"), (60004, "night/comet.odrg"),
                                                   (60005, "night/deep/x.odrg")])

    def test_each_plug_in_is_listed_again(self):
        with a_drive(DRIVE) as top:
            run = support.start(SHOW, ["drive plug"] + polls(0, 200) + asked(4000, "list") + ["drive pull"] + asked(4020, "list") + ["drive plug"] + polls(4040, 200) + asked(8040, "list"),
                                ["--drive", top, "--trace-drive", "--drive-pulled"])
        self.assertEqual(drive_lines(run), ["drive list 2", "drive list 2"])
        self.assertEqual([len(reply["items"]) for reply in replies(run)], [3, 1, 3])


class Writable(unittest.TestCase):
    def catalog(self, options):
        with a_drive(DRIVE) as top:
            run = support.start(SHOW, asked(0, "catalog"), ["--drive", top, *options])
        return [reply for reply in replies(run) if "external" in reply][0]["external"]

    def test_catalog_says_whether_the_core_may_write_the_drive(self):
        self.assertEqual(self.catalog([]), {"state": "none", "writable": True})
        self.assertEqual(self.catalog(["--drive-read-only"]), {"state": "none", "writable": False})

    def test_without_a_drive_there_is_none_to_write(self):
        run = support.start(SHOW, asked(0, "catalog"))
        self.assertEqual(json.loads(run.lines[-1][len("reply "):])["external"], {"state": "absent"})


if __name__ == "__main__":
    unittest.main()

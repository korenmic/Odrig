"""The suite that needs the board.

It needs the ESP32-S3 board connected over USB, and it writes to the board: it flashes
images and restores stock WLED. `python3 firmware/fw.py test-board` runs it with the work
folder's Python. Without a board the package cannot be imported, so no test runs. After the
last test the suite puts back what it leaves on the board.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "firmware"

if str(FIRMWARE) not in sys.path:
    sys.path.insert(0, str(FIRMWARE))

from fwtool import board  # noqa: E402

# The board's port. Looking for it fails with `no-board` when there is none.
PORT = board.find()


class LeaveTheBoard(unittest.TestCase):
    """The last step of the suite, whatever the tests before it did."""

    def test_the_board_is_left_as_the_suite_leaves_it(self):
        from . import support
        from fwtool import wifi
        support.leave_the_board()
        self.assertEqual(support.running(), support.LEFT_ON_THE_BOARD)
        self.assertTrue(wifi.holds(support.storage_image(), wifi.read()), "storage does not hold the name and the password of the settings file")
        # The show is the bench show and nothing else: the three items of the example
        # show, at a brightness the wired strip allows, playing from its start.
        _, listed = support.command(PORT, "list")
        self.assertEqual([(item["id"], item.get("file")) for item in listed["items"]], [(1, "hello.odrg"), (2, "dvd.odrg"), (3, None)])
        _, status = support.command(PORT, "status")
        self.assertEqual((status["playing"], status["error"]), (3, None))
        self.assertLessEqual(status["brightness"], support.BRIGHTEST)
        self.assertEqual(support.command(PORT, "space")[1]["animations"], 2)


def load_tests(loader, standard_tests, pattern):
    """Every test file of this folder, found by discovery, and then the last step."""
    found = loader.discover(str(pathlib.Path(__file__).parent), pattern or "test*.py", top_level_dir=str(ROOT))
    return unittest.TestSuite([found, LeaveTheBoard("test_the_board_is_left_as_the_suite_leaves_it")])

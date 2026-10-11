import unittest

from fwtool import board

from . import PORT, support


class FlashAndRestore(unittest.TestCase):
    def test_stock_wled_is_restored_and_an_image_is_flashed_after_it(self):
        self.addCleanup(support.restore_stock)

        restored = support.restore_stock()
        self.assertEqual(restored.status, 0, restored.err)
        self.assertRegex(restored.out, r"^WLED \d+\n$")
        self.assertRegex(board.handshake(PORT), r"^WLED \d+$")

        flashed = support.flash("stock")
        self.assertRegex(flashed.out, r"^WLED \d+\n$")
        self.assertNotEqual(flashed.out, restored.out)

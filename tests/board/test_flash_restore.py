import unittest

from fwtool import board, storage

from . import PORT, support


class FlashAndRestore(unittest.TestCase):
    def test_stock_wled_is_restored_and_the_firmware_is_flashed_after_it(self):
        support.ensure("firmware")
        self.addCleanup(support.ensure, "firmware")
        before = support.storage_image()

        restored = support.restore_stock()
        self.assertEqual(restored.status, 0, restored.err)
        self.assertRegex(restored.out, r"^WLED \d+\n$")
        self.assertRegex(board.handshake(PORT), r"^WLED \d+$")

        flashed = support.flash("firmware")
        self.assertRegex(flashed.out, r'^\{"ok":true,"on":true,.*\}\n$')
        self.assertIn('"ok":true', board.status(PORT))

        after = support.storage_image()
        self.assertEqual(storage.files_in(storage.mount(after)), storage.files_in(storage.mount(before)))
        self.assertGreater(len(storage.show_of(after)), 0)

import unittest

from . import support


class UnavailableBoundary(unittest.TestCase):
    def test_missing_folder_does_not_retry_its_stale_id_in_a_tight_loop(self):
        seen = support.run('only-boundary-unavailable').seen
        self.assertEqual(seen['path'], 'clocks')
        self.assertIsNone(seen['id'])
        self.assertLessEqual(seen['attempts'], 1)


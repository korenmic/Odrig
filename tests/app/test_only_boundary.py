import unittest

from . import support
from .test_clock_modes import ModeTarget


class OnlyBoundary(unittest.TestCase):
    def test_direct_navigation_cannot_leave_clocks_or_enter_an_unresolved_id(self):
        seen = support.run('only-recovery', settings=dict(case='navigation')).seen
        self.assertEqual((seen['back'], seen['outside'], seen['prefix']), ('clocks',) * 3)
        self.assertEqual(seen['level'], dict(path='clocks', id=60007))
        self.assertTrue(all(path == 'clocks' for path in seen['paths']))

    def test_visible_back_stops_at_clocks_and_the_boundary_is_explained(self):
        target = ModeTarget(self, 'only')
        seen = support.run('only-boundary-ui', address=target.stand_in.address).seen
        self.assertTrue(seen['backHidden'])
        self.assertEqual(seen['level'], 'clocks')
        self.assertNotIn('', seen['paths'])
        self.assertIn('Browsing stays inside', seen['note'])

    def test_reused_folder_id_cannot_publish_an_outside_list_inside_clocks(self):
        seen = support.run('only-recovery', settings=dict(case='reused')).seen
        self.assertFalse(seen['outsideVisible'])
        self.assertEqual(seen['level'], dict(path='clocks', id=60017))

    def test_unknown_mode_metadata_keeps_the_last_confirmed_browsing_boundary(self):
        seen = support.run('only-recovery', settings=dict(case='uncertain')).seen
        self.assertEqual(seen['level'], dict(path='clocks', id=60007))
        self.assertTrue(seen['only'])
        self.assertNotIn('', seen['paths'])

    def test_lost_connection_does_not_release_the_boundary(self):
        seen = support.run('only-recovery', settings=dict(case='uncertain', offline=True)).seen
        self.assertEqual(seen['level'], dict(path='clocks', id=60007))
        self.assertTrue(seen['only'])
        self.assertNotIn('', seen['paths'])

    def test_confirmed_between_releases_the_boundary(self):
        seen = support.run('only-recovery', settings=dict(case='release')).seen
        self.assertEqual(seen['level'], dict(path='', id=None))
        self.assertFalse(seen['only'])

    def test_reload_establishes_the_same_visible_boundary(self):
        target = ModeTarget(self, 'only')
        seen = support.run('only-boundary-ui', address=target.stand_in.address,
                           settings=dict(reload=True)).seen
        self.assertTrue(seen['backHidden'])
        self.assertEqual(seen['level'], 'clocks')
        self.assertNotIn('', seen['paths'])

    def test_restart_rejected_for_stale_only_status_does_not_claim_a_board_reply(self):
        seen = support.run('only-recovery', settings=dict(case='uncertain', offline=True, restart=True)).seen
        self.assertEqual(seen, dict(link='no-answer', sent=0, claimedReply=False))

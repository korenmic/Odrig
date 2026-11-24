import unittest

from . import support
from .test_clock_modes import ModeTarget


class BoundaryTarget(ModeTarget):
    def __init__(self, test, case):
        self.case = case
        self.statuses = 0
        super().__init__(test, 'only')
        if case == 'missing':
            self.only_folder = None
            self.only_state = 'missing-folder'

    def reply(self, line):
        if line.decode().strip() == 'status':
            self.statuses += 1
            if self.statuses > 1 and self.case == 'uncertain':
                self.mode_members = False
            if self.statuses > 1 and self.case == 'offline':
                return 500, ''
        return super().reply(line)


class OnlyBoundary(unittest.TestCase):
    def scenario(self, case='navigation', **settings):
        target = BoundaryTarget(self, case)
        target.levels[60007].append(dict(id=60010, playlist='clocks/child', files=1, external=True))
        target.levels[60010] = [dict(id=60011, file='clocks/child/a.odrg', bytes=100, external=True)]
        return support.run('only-boundary', address=target.stand_in.address,
                           settings=dict(case=case, **settings)).seen

    def test_direct_navigation_and_back_cannot_leave_clocks(self):
        seen = self.scenario()
        self.assertEqual(seen['paths'], ['clocks'] * len(seen['paths']))
        self.assertEqual(seen['levels'], ['clocks', 'clocks', 'clocks'])

    def test_visible_back_stops_at_clocks_and_explains_the_boundary(self):
        seen = self.scenario()
        self.assertTrue(seen['backHidden'])
        self.assertIn('Browsing stays inside', seen['note'])

    def test_valid_descendant_can_be_entered_and_back_stops_at_clocks(self):
        seen = self.scenario('child')
        self.assertEqual(seen['levels'], ['clocks/child', 'clocks', 'clocks'])

    def test_confirmed_between_releases_navigation(self):
        seen = self.scenario('release')
        self.assertEqual(seen['level'], '')

    def test_reload_restores_the_boundary(self):
        seen = self.scenario(reload=True)
        self.assertTrue(seen['backHidden'])
        self.assertEqual(seen['levels'], ['clocks'] * 3)

    def test_unknown_mode_metadata_keeps_last_confirmed_boundary(self):
        seen = self.scenario('uncertain')
        self.assertEqual(seen['level'], 'clocks')
        self.assertTrue(seen['only'])

    def test_lost_connection_keeps_last_confirmed_boundary(self):
        seen = self.scenario('offline')
        self.assertEqual(seen['level'], 'clocks')
        self.assertTrue(seen['only'])

    def test_missing_clocks_does_not_publish_root_content(self):
        seen = self.scenario('missing')
        self.assertEqual(seen['level'], 'clocks')
        self.assertEqual(seen['files'], [])


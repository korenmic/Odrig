import unittest

from . import support
from .test_clock_modes import ModeTarget


class MissingIdTarget(ModeTarget):
    def reply(self, line):
        if line.startswith(b'list in 60007 '):
            return self.answer(dict(ok=False, error='unknown-id'))
        return super().reply(line)


class OnlyRecovery(unittest.TestCase):
    def test_an_unavailable_clock_folder_never_publishes_root(self):
        seen = support.run('only-recovery').seen
        self.assertNotIn('', seen['paths'])
        self.assertEqual(seen['level'], dict(path='clocks', id=None))
        self.assertTrue(seen['retained'])
        self.assertFalse(seen['fresh'])

    def test_missing_clocks_from_first_connection_is_an_unavailable_clocks_view(self):
        seen = support.run('only-recovery', settings=dict(case='initial')).seen
        self.assertNotIn('', seen['paths'])
        self.assertEqual(seen['level'], dict(path='clocks', id=None))
        self.assertFalse(seen['fresh'])
        self.assertLessEqual(seen['rootRequests'], 3)

    def test_repeated_only_status_keeps_a_valid_descendant(self):
        seen = support.run('only-recovery', settings=dict(case='child')).seen
        self.assertEqual(set(seen['paths']), {'clocks/message'})
        self.assertEqual(seen['level'], dict(path='clocks/message', id=60008))

    def test_remapped_folder_ids_resolve_the_descendant_without_root(self):
        seen = support.run('only-recovery', settings=dict(case='remap')).seen
        self.assertNotIn('', seen['paths'])
        self.assertEqual(seen['level'], dict(path='clocks/message', id=60018))

    def test_clock_storage_return_restores_clocks_with_its_new_id(self):
        seen = support.run('only-recovery', settings=dict(restore=True)).seen
        self.assertNotIn('', seen['paths'])
        self.assertEqual(seen['restored'], dict(path='clocks', id=60017))

    def test_unknown_policy_does_not_release_the_last_confirmed_only_context(self):
        seen = support.run('only-recovery', settings=dict(case='unknown')).seen
        self.assertNotIn('', seen['paths'])
        self.assertEqual(seen['afterUnknown'], dict(path='clocks', id=None))

    def test_late_folder_reply_cannot_restore_a_previous_targets_only_policy(self):
        seen = support.run('only-recovery', settings=dict(case='target')).seen
        self.assertEqual(set(seen['paths']), {''})
        self.assertEqual(seen['level'], dict(path='', id=None))
        self.assertEqual(seen['mode'], 'off')

    def test_unavailable_view_explains_recovery_and_keeps_target_settings_and_mode_exit_usable(self):
        target = ModeTarget(self, 'only')
        target.only_folder = None
        target.only_state = 'no-clocks'
        target.levels = {None: []}
        seen = support.run('only-unavailable', address=target.stand_in.address).seen
        self.assertIn('Clocks folder unavailable', seen['notice'])
        self.assertTrue(seen['restartDisabled'])
        self.assertEqual((seen['target'], seen['mode'], seen['level']), ('target', 'off', ''))

    def test_a_fresh_status_with_a_now_missing_id_does_not_enable_restart(self):
        target = MissingIdTarget(self, 'only')
        target.levels[None] = target.levels[None][:2]
        seen = support.run('only-unavailable', address=target.stand_in.address).seen
        self.assertTrue(seen['restartDisabled'])

    def test_direct_restart_cannot_send_the_unresolved_only_folder_id(self):
        seen = support.run('only-recovery', settings=dict(restart=True)).seen
        self.assertEqual(seen['sent'], 0)

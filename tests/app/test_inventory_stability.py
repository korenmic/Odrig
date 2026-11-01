import unittest

from . import support


class StableInventory(unittest.TestCase):
    def test_reconnect_retains_snapshots_and_explicit_identical_validation_does_not_replace_them(self):
        found = support.run('inventory-stability').seen
        self.assertEqual(found['stale'], dict(listRetained=True, marked=True))
        self.assertEqual(found['reconnect'], dict(sameList=True, sameOrder=True, sameKeys=True,
                                                lostKeys=False, version=True, lists=0, pages=0))
        self.assertEqual(found['explicit'], dict(sameList=True, sameOrder=True, sameKeys=True, version=True))

    def test_periodic_authoritative_validation_does_not_reload_lists_or_keys(self):
        found = support.run('inventory-stability', settings=dict(poll=True)).seen
        self.assertEqual(found['periodic'], dict(lists=0, sameList=True, sameKeys=True))

    def test_a_real_change_replaces_the_affected_list_and_preview_keys(self):
        found = support.run('inventory-stability', settings=dict(change='data')).seen
        self.assertEqual(found, dict(partial=None, newList=True, newKeys=True, bytes=101,
                                     file='one.odrg', newTarget=False, rows=1))

    def test_a_new_board_at_the_same_address_discards_old_identity_and_keys(self):
        found = support.run('inventory-stability', settings=dict(change='board')).seen
        self.assertEqual(found, dict(partial=None, newList=True, newKeys=True, bytes=100,
                                     file='other.odrg', newTarget=True, rows=1))

    def test_a_failed_later_page_preserves_the_last_complete_snapshot(self):
        found = support.run('inventory-stability', settings=dict(change='partial')).seen
        self.assertEqual(found, dict(partial=dict(retained=True, bytes=100), newList=True,
                                     newKeys=True, bytes=101, file='one.odrg', newTarget=False, rows=2))

    def test_legacy_validation_keeps_stale_data_visible_until_full_validation(self):
        found = support.run('inventory-stability', settings=dict(change='legacy')).seen
        self.assertEqual(found['stale'], dict(listRetained=True, marked=True))
        self.assertTrue(found['retained'])
        self.assertTrue(found['fresh'])
        self.assertGreaterEqual(found['reconnect']['lists'], 1)
        self.assertEqual(found['reconnect']['pages'], 0)

    def test_a_permanently_failing_page_has_a_bounded_retry_rate(self):
        found = support.run('inventory-stability', settings=dict(change='partial', permanent=True)).seen
        self.assertEqual(found['partial'], dict(retained=True, bytes=100))
        self.assertTrue(found['retained'])
        self.assertLessEqual(found['lists'], 8)

    def test_stale_id_rejection_does_not_claim_a_reply_from_the_board(self):
        found = support.run('inventory-stability', settings=dict(guard=True)).seen
        self.assertEqual(found['guard'], dict(sent=0, stillDisconnected=True))

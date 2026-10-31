import base64
import json
import unittest

from tests.emulator import support as emulator_support
from tests.core.test_civil_time import snapshot
from . import support
from .test_target import entered


class ConnectionTime(unittest.TestCase):
    def test_a_new_connection_sets_an_invalid_clock_with_auto_sync_on_by_default(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        self.assertFalse(json.loads(emulator.command('time'))['valid'])
        seen = support.run('timing-auto', address=f'127.0.0.1:{emulator.port}', auto_time=None).seen
        self.assertTrue(seen['clock']['valid'])
        self.assertIsNotNone(seen['clock']['zone'])
        self.assertEqual(seen['connected'], 'Answers')


def clock_reply(**changes):
    return dict(ok=True, valid=False, utc=None, zone=None, offset=None, revision=None,
                **{'from': None}, until=None, board='board-a', error=None) | changes


def schedule_reply(**changes):
    return dict(ok=True, enabled=True, on='18:00', off='06:00', override=None,
                revision='01234567', power=True, active=False, reason='time-unset',
                saved=True, error=None) | changes


def protocol(entries):
    return support.run('clock-mode-protocol', settings=dict(replies=entries)).seen


class TimingProtocol(unittest.TestCase):
    def test_reads_and_mutations_use_the_exact_guarded_wire_forms(self):
        encoded = base64.urlsafe_b64encode(snapshot()).decode().rstrip('=')
        read = clock_reply()
        schedule = schedule_reply()
        entries = [dict(command='timeRead', reply=read),
                   dict(command='timeRead', args=['board-a'], reply=read),
                   dict(command='scheduleRead', args=['board-a'], reply=schedule),
                   dict(command='timeZone', args=['board-a', encoded], reply=dict(ok=True)),
                   dict(command='timeSet', args=['board-a', 1800000000, '01234567'], reply=dict(ok=True)),
                   dict(command='scheduleSet', args=['board-a', '01234567', '09:00', '17:00', False], reply=dict(ok=True)),
                   dict(command='scheduleResume', args=['board-a', '01234567'], reply=dict(ok=True))]
        seen = protocol(entries)
        self.assertEqual(seen['results'], [read, read, schedule, None, None, None, None])
        self.assertEqual(seen['sent'], ['time', 'guard board-a time', 'guard board-a schedule',
            'guard board-a time zone ' + encoded, 'guard board-a time set 1800000000 01234567',
            'guard board-a schedule set 01234567 09:00 17:00 off', 'guard board-a schedule resume 01234567'])

    def test_invalid_readback_and_wrong_identity_are_rejected(self):
        valid = clock_reply(valid=True, utc=1800000000, zone='UTC', offset=0,
                            revision='01234567', **{'from': 946684800}, until=4102444800)
        damaged = [clock_reply(board='other'), clock_reply(board=None), clock_reply(utc=1),
                   valid | dict(utc=4102444800), valid | dict(offset=86401),
                   valid | dict(zone='/UTC'), valid | dict(revision='ABCDEF12'),
                   valid | {'from': 1800000001}, valid | dict(board='x' * 32)]
        entries = [dict(command='timeRead', args=['board-a'], reply=row) for row in damaged]
        entries += [dict(command='scheduleRead', args=['board-a'], reply=schedule_reply(**row)) for row in (
            dict(on='24:00'), dict(off='18:00'), dict(saved='yes'),
            dict(enabled=False, active=True, reason=None), dict(override='other'))]
        seen = protocol(entries)
        self.assertEqual(seen['results'], [dict(error='bad-reply')] * len(entries))

    def test_invalid_mutations_send_nothing_including_missing_target_guards(self):
        encoded = base64.urlsafe_b64encode(snapshot()).decode().rstrip('=')
        arguments = [
            ('timeSet', [None, 1800000000, '01234567']),
            ('timeSet', ['unsafe id', 1800000000, '01234567']),
            ('timeSet', ['board-a', 4102444800, '01234567']),
            ('timeSet', ['board-a', 1800000000, 'ABCDEF12']),
            ('timeZone', [None, encoded]), ('timeZone', ['board-a', 'A' * 2001]),
            ('scheduleSet', [None, '01234567', '09:00', '17:00', True]),
            ('scheduleSet', ['board-a', '01234567', '09:00', '09:00', True]),
            ('scheduleSet', ['board-a', '01234567', '9:00', '17:00', True]),
            ('scheduleSet', ['board-a', '01234567', '09:00', '17:00', 1]),
            ('scheduleResume', [None, '01234567']), ('scheduleResume', ['board-a', 'invalid']),
        ]
        seen = protocol([dict(command=name, args=args, reply=dict(ok=True)) for name, args in arguments])
        self.assertEqual(seen['sent'], [])
        self.assertEqual(seen['results'], [dict(error='bad-argument')] * len(arguments))

    def test_legacy_status_shape_is_preserved_and_capability_is_typed(self):
        status = dict(ok=True, on=True, brightness=128, playing='all', animation=1, fps=50, error=None)
        seen = protocol([dict(command='status', reply=status),
                         dict(command='status', reply=status | dict(timing=True)),
                         dict(command='status', reply=status | dict(timing='yes'))])
        self.assertNotIn('timing', seen['results'][0])
        self.assertTrue(seen['results'][1]['timing'])
        self.assertEqual(seen['results'][2], dict(error='bad-reply'))


def model(operations, **options):
    return support.run('timing-model', settings=dict(operations=operations, options=options)).seen


def writes(snapshot, board=None):
    return [entry for entry in snapshot['sent'] if entry['kind'] == 'time' and (board is None or entry['board'] == board)]


class TimingConnections(unittest.TestCase):
    def test_fifteen_minutes_is_checked_on_next_connection_and_never_by_status_polls(self):
        seen = model([dict(connect=True, look='first'), dict(advance=899999, connect=True, look='before'),
                      dict(advance=1, poll=True, look='poll'),
                      dict(connect=True, look='again')])
        self.assertEqual(len(writes(seen['first'])), 1)
        self.assertEqual(len(writes(seen['before'])), 1)
        self.assertEqual(len(writes(seen['poll'])), 1)
        self.assertEqual(len(writes(seen['again'])), 2)

    def test_recent_valid_clock_skips_utc_but_clock_loss_bypasses_cooldown(self):
        seen = model([dict(connect=True, look='first'), dict(connect=True, look='recent'),
                      dict(lostClock=True, connect=True, look='lost')])
        self.assertEqual(len(writes(seen['recent'])), 1)
        self.assertEqual(len(writes(seen['lost'])), 2)

    def test_manual_sync_and_auto_off_share_the_same_confirmation_record(self):
        seen = model([dict(connect=True, look='off'), dict(sync=True, look='manual'),
                      dict(auto=True, look='enabled'), dict(connect=True, look='recent')], auto=False)
        self.assertEqual(writes(seen['off']), [])
        self.assertEqual(len(writes(seen['manual'])), 1)
        self.assertEqual(len(writes(seen['recent'])), 1)
        self.assertEqual(seen['manual']['confirmed'], seen['recent']['confirmed'])

    def test_changed_phone_zone_updates_rules_without_resetting_utc_cooldown(self):
        seen = model([dict(connect=True, look='first'),
                      dict(zone='Test/Other', revision='22222222', connect=True, look='zone')])
        self.assertEqual(len(writes(seen['zone'])), 1)
        self.assertEqual([entry['kind'] for entry in seen['zone']['sent']], ['time', 'zone'])
        self.assertEqual(seen['zone']['confirmed'], seen['first']['confirmed'])

    def test_backwards_phone_time_is_due_and_confirmations_are_persisted_per_board(self):
        seen = model([dict(connect=True, look='recent'), dict(advance=-1000, connect=True, look='backwards'),
                      dict(board='board-b', connect=True, look='other')],
                     valid=True, confirmed=[['board-a', 1800000000000]])
        self.assertEqual(writes(seen['recent']), [])
        self.assertEqual(len(writes(seen['backwards'])), 1)
        self.assertEqual(len(writes(seen['other'], 'board-b')), 1)
        self.assertEqual({entry[0] for entry in seen['other']['confirmed']}, {'board-a', 'board-b'})

    def test_a_phone_zone_change_while_connected_updates_rules_without_periodic_utc_sync(self):
        seen = model([dict(connect=True, look='first'),
                      dict(advance=1200000, zone='Test/Other', revision='22222222', poll=True, look='zone'),
                      dict(poll=True, look='again')])
        self.assertEqual(seen['zone']['state']['clock']['zone'], 'Test/Other')
        self.assertEqual([entry['kind'] for entry in seen['zone']['sent']], ['time', 'zone'])
        self.assertEqual(seen['zone']['confirmed'], seen['first']['confirmed'])
        self.assertEqual(seen['again']['sent'], seen['zone']['sent'])

    def test_a_failed_initial_time_read_is_not_retried_by_ordinary_polls(self):
        seen = model([dict(fault='read', connect=True, look='failed'), dict(poll=True, look='poll')])
        self.assertEqual(seen['failed']['reads'], 1)
        self.assertEqual(seen['poll']['reads'], 1)
        self.assertEqual(seen['poll']['state']['error'], seen['failed']['state']['error'])

    def test_failed_lost_and_unconfirmed_writes_never_start_a_cooldown_or_retry_on_polls(self):
        for fault in ('refused', 'lost', 'unconfirmed'):
            with self.subTest(fault=fault):
                seen = model([dict(fault=fault, connect=True, look='failed'), dict(poll=True, look='poll'),
                              dict(connect=True, look='retry')])
                self.assertEqual(seen['failed']['confirmed'], [])
                self.assertIsNotNone(seen['failed']['state']['error'])
                self.assertEqual(seen['poll']['sent'], seen['failed']['sent'])
                self.assertEqual(len(seen['retry']['confirmed']), 1)

    def test_same_address_physical_switch_during_zone_preparation_never_receives_old_writes(self):
        seen = model([dict(connect=True, phase='preparing', wait=False),
                      dict(board='board-b', releasePreparation=True, look='switched')], holdPreparation=True)
        self.assertEqual(seen['switched']['sent'], [])
        self.assertEqual(seen['switched']['confirmed'], [])
        self.assertIsNotNone(seen['switched']['state']['error'])

    def test_target_switch_before_a_queued_job_starts_only_syncs_the_new_target(self):
        seen = model([dict(connect=True, wait=False),
                      dict(board='board-b', connect=True, newTarget=True, releaseQueue=True, look='new')], holdQueue=True)
        self.assertEqual([entry['board'] for entry in writes(seen['new'])], ['board-b'])
        self.assertEqual([entry[0] for entry in seen['new']['confirmed']], ['board-b'])

    def test_late_reply_from_previous_target_is_not_a_confirmation_for_either_target(self):
        seen = model([dict(connect=True, phase='synchronizing', sentCount=1, wait=False),
                      dict(board='board-b', connect=True, newTarget=True, wait=False),
                      dict(releaseSet=True, look='new')], holdSet=True)
        self.assertEqual([entry[0] for entry in seen['new']['confirmed']], ['board-b'])
        self.assertEqual([entry['board'] for entry in writes(seen['new'])], ['board-a', 'board-b'])

    def test_auto_off_during_preparation_cancels_all_waiting_writes(self):
        seen = model([dict(connect=True, phase='preparing', wait=False),
                      dict(auto=False, releasePreparation=True, look='off')], holdPreparation=True)
        self.assertEqual(seen['off']['sent'], [])
        self.assertEqual(seen['off']['confirmed'], [])

    def test_new_unsupported_connection_clears_the_previous_boards_metadata(self):
        seen = model([dict(connect=True, look='first'),
                      dict(board='board-b', connect=True, legacy=True, look='old-firmware')])
        self.assertIsNone(seen['old-firmware']['state']['clock'])
        self.assertIsNone(seen['old-firmware']['state']['board'])
        self.assertFalse(seen['old-firmware']['state']['busy'])

    def test_a_new_manual_sync_is_pending_until_confirmed(self):
        seen = model([dict(connect=True), dict(sync=True, pending='pending', look='finished')])
        self.assertTrue(seen['pending']['state']['busy'])
        self.assertIsNone(seen['pending']['state']['lastResult'])
        self.assertEqual(seen['finished']['state']['lastResult'], 'synchronized')

    def test_confirmation_records_are_bounded_and_evict_by_insertion_order(self):
        kept = [[f'old-{number}', 1800000000000] for number in range(32)]
        seen = model([dict(connect=True, look='confirmed')], valid=True, confirmed=kept)
        self.assertEqual(len(seen['confirmed']['confirmed']), 32)
        self.assertEqual(seen['confirmed']['confirmed'][0][0], 'old-1')
        self.assertEqual(seen['confirmed']['confirmed'][-1][0], 'board-a')

    def test_a_phone_storage_failure_keeps_the_preference_usable_but_reports_it_volatile(self):
        seen = model([dict(auto=False, look='off'), dict(connect=True, look='connected')], storageFails=True)
        self.assertFalse(seen['off']['state']['auto'])
        self.assertFalse(seen['off']['state']['preferenceSaved'])
        self.assertEqual(seen['connected']['sent'], [])


def client_case(kind):
    encoded = base64.urlsafe_b64encode(snapshot()).decode().rstrip('=')
    return support.run('timing-client', settings=dict(kind=kind, zone=encoded)).seen


class SharedTimingQueue(unittest.TestCase):
    def test_target_switch_before_send_cancels_waiting_mutations(self):
        seen = client_case('queued')
        self.assertNotEqual(seen['result'], 'ok')
        self.assertEqual(seen['mutations'], [])
        self.assertEqual(seen['maximum'], 1)

    def test_target_switch_while_awaiting_reply_never_sends_the_next_step_to_new_address(self):
        seen = client_case('reply')
        self.assertNotEqual(seen['result'], 'ok')
        self.assertEqual(len(seen['mutations']), 1)
        self.assertEqual(seen['mutations'][0]['address'], '127.0.0.1:11111')
        self.assertIn('time zone', seen['mutations'][0]['line'])
        self.assertEqual(seen['maximum'], 1)

    def test_preference_guard_is_rechecked_at_send_without_marking_connection_failed(self):
        seen = client_case('cancel')
        self.assertEqual(seen['result'], 'stale')
        self.assertEqual(seen['connected'], 'answers')
        self.assertEqual(seen['mutations'], [])
        self.assertEqual(seen['maximum'], 1)

    def test_timing_failure_does_not_create_a_false_reconnection_or_self_retry(self):
        seen = client_case('failure')
        self.assertEqual(seen['result'], 'no-answer')
        self.assertEqual(seen['afterTimeFailure'], seen['initial'])
        self.assertEqual(seen['reconnected'], seen['initial'] + 1)
        self.assertEqual(seen['timeRequests'], 1)
        self.assertEqual(seen['maximum'], 1)

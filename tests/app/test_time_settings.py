import json
import base64
import struct
import threading
import unittest
import zlib

from tests.emulator import support as emulator_support
from . import support
from .test_target import entered
from .test_clocks import Target as ClocksTarget
from .test_look import SIZES


class Target(ClocksTarget):
    def __init__(self, test, board='board-a', legacy=False):
        self.board = board
        self.legacy = legacy
        self.hours = ['18:00', '06:00']
        self.enabled = True
        self.override = None
        self.saved = True
        self.schedule_error = None
        self.accept = True
        self.lose = False
        self.read_fails = False
        self.command_seen = threading.Event()
        self.clock = dict(ok=True, valid=False, utc=None, zone=None, offset=None, revision=None,
                          **{'from': None}, until=None, error=None)
        super().__init__(test)

    def status(self):
        code, text = super().status()
        return code, json.dumps(json.loads(text) | ({} if self.legacy else dict(timing=True)))

    def schedule(self):
        minutes = lambda text: int(text[:2]) * 60 + int(text[3:])
        mode = {None: 0, 'on': 1, 'off': 2}[self.override]
        data = f'odrig-schedule 1\n{int(self.enabled)} {minutes(self.hours[0])} {minutes(self.hours[1])} {mode}\n'.encode()
        return dict(ok=True, enabled=self.enabled, on=self.hours[0], off=self.hours[1],
                    override=self.override, revision=f'{zlib.crc32(data):08x}', power=True,
                    active=self.enabled and self.override is None and self.clock['valid'],
                    reason='manual' if self.override else 'disabled' if not self.enabled else
                    'time-unset' if not self.clock['valid'] else None,
                    saved=self.saved, error=self.schedule_error)

    def reply(self, line):
        words = line.decode().split()
        if not self.answering:
            return 500, ''
        if words[0] == 'guard':
            if words[1] != self.board:
                return 200, json.dumps(dict(ok=False, error='stale'))
            words = words[2:]
        if words[0] not in ('time', 'schedule'):
            return super().reply(line)
        if self.read_fails and len(words) == 1:
            return 200, json.dumps(dict(ok=False, error='storage-error'))
        if len(words) == 1:
            value = self.clock | dict(board=self.board) if words[0] == 'time' else self.schedule()
            return 200, json.dumps(value)
        if self.refusal:
            return 200, json.dumps(dict(ok=False, error=self.refusal))
        if words[0] == 'schedule':
            if words[2] != self.schedule()['revision']:
                return 200, json.dumps(dict(ok=False, error='stale'))
            if self.accept:
                if words[1] == 'resume': self.override = None
                else:
                    self.hours = words[3:5]
                    self.enabled = words[5] == 'on'
        elif words[1] == 'zone':
            data = base64.urlsafe_b64decode(words[2] + '=' * (-len(words[2]) % 4))
            self.clock.update(zone=data[56:56 + data[20]].decode(), revision=f'{zlib.crc32(data):08x}',
                              **{'from': struct.unpack_from('<I', data, 8)[0]}, until=struct.unpack_from('<I', data, 12)[0], offset=0)
        else:
            self.clock.update(utc=int(words[2]), valid=True)
        self.command_seen.set()
        if self.lose:
            self.answering = False
            return 500, ''
        return 200, '{"ok":true}'

    def mutations(self):
        return [line.decode() for _, line in self.stand_in.lines if b' schedule set ' in line or b' schedule resume ' in line]


def run(target, acts=(), **kwargs):
    return support.run('time-settings', address=target.stand_in.address,
                       settings=dict(acts=acts, legacy=target.legacy), **kwargs).seen


class NativeTimeSettings(unittest.TestCase):
    def test_the_automatic_sync_checkbox_is_saved_and_off_survives_reopening(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        acts = [dict(tap='time-auto', look='off'),
                dict(reload=True, until=dict(auto=False, syncDisabled=False), look='reloaded')]
        with emulator_support.EventStream(emulator.port) as stream:
            seen = support.run('time-settings', address=f'127.0.0.1:{emulator.port}',
                               settings=dict(acts=acts), auto_time=None).seen
            logs = emulator_support.of_kind(stream.read_for(.2), 'log')
        self.assertTrue(seen['first']['auto'])
        self.assertFalse(seen['off']['auto'])
        self.assertFalse(seen['reloaded']['auto'])
        self.assertEqual(sum(' time set ' in entry['line'] for entry in logs), 1)

    def test_settings_shows_default_hours_and_default_on_automatic_phone_time(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        seen = support.run('time-settings', address=f'127.0.0.1:{emulator.port}', auto_time=None).seen['first']
        self.assertTrue(seen['auto'])
        self.assertTrue(seen['enabled'])
        self.assertEqual((seen['on'], seen['off']), ('18:00', '06:00'))
        self.assertIn('Board time:', seen['readout'])
        self.assertNotIn('not set', seen['readout'])
        self.assertTrue(json.loads(emulator.command('time'))['valid'])
        self.assertTrue(seen['saveDisabled'])
        self.assertTrue(seen['resumeDisabled'])

    def test_saved_hours_black_out_then_manual_on_wins_until_explicit_resume(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        acts = [dict(nowOff=True), dict(tap='schedule-save', until=dict(text='Saved scheduled hours'), look='saved'),
                dict(step=True), dict(tap='time-refresh', until=dict(text='Manual On'), look='manual'),
                dict(tap='schedule-resume', until=dict(text='Schedule resumed'), look='resumed')]
        def manual_on():
            self.assertFalse(emulator.status()['on'])
            self.assertTrue(json.loads(emulator.command('on'))['ok'])
        seen = support.run('time-settings', address=f'127.0.0.1:{emulator.port}',
                           auto_time=None, settings=dict(acts=acts), steps=[manual_on]).seen
        self.assertIn('LEDs are off', seen['saved']['scheduleState'])
        self.assertFalse(seen['manual']['resumeDisabled'])
        self.assertIn('LEDs are off', seen['resumed']['scheduleState'])
        self.assertFalse(emulator.status()['on'])
        self.assertIsNone(json.loads(emulator.command('schedule'))['override'])
        self.assertTrue((folder / 'schedule.txt').read_text().endswith(' 0\n'))

    def test_manual_sync_works_with_auto_off_and_the_phone_preference_survives_reload(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        acts = [dict(fill={'schedule-on': '17:30'}), dict(tap='time-sync', until=dict(syncDisabled=False), look='synced'),
                dict(reload=True, until=dict(auto=False, syncDisabled=False), look='reloaded')]
        seen = support.run('time-settings', address=f'127.0.0.1:{emulator.port}', settings=dict(acts=acts)).seen
        self.assertIn('not set', seen['first']['readout'])
        self.assertNotIn('not set', seen['synced']['readout'])
        self.assertEqual(seen['synced']['on'], '17:30')
        self.assertIn('synchronized', seen['synced']['said'])
        self.assertFalse(seen['reloaded']['auto'])
        self.assertTrue(json.loads(emulator.command('time'))['valid'])


class TimeSettings(unittest.TestCase):
    def test_an_external_revision_change_is_not_overwritten_and_refresh_reloads_it(self):
        target = Target(self)
        def elsewhere(): target.hours = ['08:00', '16:00']
        seen = run(target, [dict(fill={'schedule-on': '17:30'}), dict(step=True), dict(tap='schedule-save'),
                            dict(until=dict(text='changed', saveDisabled=False), look='stale'),
                            dict(tap='time-refresh', until=dict(on='08:00', saveDisabled=True), look='fresh')], steps=[elsewhere])
        self.assertEqual(seen['stale']['on'], '17:30')
        self.assertEqual(target.hours, ['08:00', '16:00'])
        self.assertEqual(seen['fresh']['off'], '16:00')
        self.assertEqual(len(target.mutations()), 1)

    def test_unsaved_manual_mode_is_shown_as_temporary(self):
        target = Target(self)
        target.override = 'off'
        target.saved = False
        target.schedule_error = 'storage-error'
        seen = run(target)['first']
        self.assertIn('Manual Off', seen['scheduleState'])
        self.assertIn('may be lost on restart', seen['scheduleState'])
        self.assertFalse(seen['resumeDisabled'])

    def test_invalid_or_equal_hours_send_nothing_and_valid_edits_are_explicitly_unsaved(self):
        target = Target(self)
        seen = run(target, [dict(fill={'schedule-on': '06:00'}, look='equal'),
                            dict(tap='schedule-save'), dict(fill={'schedule-on': '25:00'}, look='invalid'),
                            dict(fill={'schedule-on': '17:30'}, look='edited')])
        self.assertTrue(seen['equal']['saveDisabled'])
        self.assertIn('different valid', seen['equal']['said'])
        self.assertTrue(seen['invalid']['saveDisabled'])
        self.assertFalse(seen['edited']['saveDisabled'])
        self.assertIn('Save to apply', seen['edited']['said'])
        self.assertEqual(target.mutations(), [])

    def test_save_is_pending_then_confirms_both_hours_and_enabled_as_one_change(self):
        target = Target(self)
        target.stand_in.delay = .15
        seen = run(target, [dict(fill={'schedule-on': '09:00', 'schedule-off': '17:00'}),
                            dict(tap='schedule-enabled'), dict(tap='schedule-save', look='pending'),
                            dict(until=dict(text='Saved scheduled hours', saveDisabled=True), look='saved')])
        self.assertTrue(seen['pending']['saveDisabled'])
        self.assertIn('Saving', seen['pending']['said'])
        self.assertEqual((seen['saved']['on'], seen['saved']['off'], seen['saved']['enabled']), ('09:00', '17:00', False))
        self.assertEqual(len(target.mutations()), 1)
        self.assertTrue(target.mutations()[0].endswith('09:00 17:00 off'))

    def test_refusal_or_unconfirmed_save_preserves_the_draft_and_never_claims_success(self):
        for fault in ('busy', 'unconfirmed'):
            with self.subTest(fault=fault):
                target = Target(self)
                if fault == 'busy': target.refusal = 'busy'
                else: target.accept = False
                expected = 'busy' if fault == 'busy' else 'could not be confirmed'
                seen = run(target, [dict(fill={'schedule-on': '17:30'}), dict(tap='schedule-save'),
                                    dict(until=dict(text=expected, saveDisabled=False), look='failed')])['failed']
                self.assertEqual(seen['on'], '17:30')
                self.assertNotIn('Saved scheduled hours', seen['said'])
                self.assertEqual(target.hours, ['18:00', '06:00'])
                self.assertEqual(len(target.mutations()), 1)

    def test_refresh_preserves_edits_on_failure_and_reloads_only_after_confirmation(self):
        target = Target(self)
        def fail(): target.read_fails = True
        def recover():
            target.read_fails = False
            target.hours = ['08:00', '16:00']
        seen = run(target, [dict(fill={'schedule-on': '17:30'}), dict(wait=2200, look='poll'),
                            dict(step=True), dict(tap='time-refresh', until=dict(text='could not save'), look='failed'),
                            dict(step=True), dict(tap='time-refresh', until=dict(on='08:00', saveDisabled=True), look='refreshed')],
                   steps=[fail, recover])
        self.assertEqual(seen['poll']['on'], '17:30')
        self.assertEqual(seen['failed']['on'], '17:30')
        self.assertEqual(seen['refreshed']['off'], '16:00')
        self.assertEqual(target.mutations(), [])

    def test_lost_save_reply_is_visible_and_reconnect_never_replays_the_save(self):
        target = Target(self)
        target.lose = True
        def recover():
            target.answering = True
            target.lose = False
        seen = run(target, [dict(fill={'schedule-on': '17:30'}), dict(tap='schedule-save'),
                            dict(until=dict(text='could not', syncDisabled=True), look='lost'),
                            dict(step=True), dict(wait=6000, until=dict(syncDisabled=False), look='recovered')], steps=[recover])
        self.assertEqual(seen['lost']['on'], '17:30')
        self.assertNotIn('Saved scheduled hours', seen['recovered']['said'])
        self.assertEqual(len(target.mutations()), 1)

    def test_target_change_drops_old_draft_and_a_late_reply(self):
        first, second = Target(self), Target(self, board='board-b')
        first.stand_in.delay = .5
        second.hours = ['08:00', '16:00']
        def sent(): self.assertTrue(first.command_seen.wait(5))
        seen = run(first, [dict(fill={'schedule-on': '17:30'}), dict(tap='schedule-save'), dict(step=True),
                           dict(target=second.stand_in.address, until=dict(on='08:00', syncDisabled=False), look='second')], steps=[sent])
        self.assertEqual(seen['changed']['on'], '')
        self.assertNotIn('Board time:', seen['changed']['readout'])
        self.assertEqual(second.mutations(), [])
        self.assertEqual(seen['second']['off'], '16:00')

    def test_reconnect_to_same_board_preserves_draft_but_another_board_clears_it(self):
        target = Target(self)
        def disconnect(): target.answering = False
        def reconnect(): target.answering = True
        def replace():
            target.board = 'board-b'
            target.hours = ['08:00', '16:00']
        seen = run(target, [dict(fill={'schedule-on': '17:30'}), dict(step=True),
                            dict(until=dict(syncDisabled=True)), dict(step=True), dict(wait=6000, until=dict(syncDisabled=False), look='same'),
                            dict(step=True), dict(tap='time-refresh', until=dict(on='08:00'), look='other')], steps=[disconnect, reconnect, replace])
        self.assertEqual(seen['same']['on'], '17:30')
        self.assertEqual(seen['other']['off'], '16:00')
        self.assertEqual(target.mutations(), [])

    def test_unsupported_firmware_and_unreadable_schedule_disable_mutations(self):
        old = Target(self, legacy=True)
        seen = run(old)['first']
        self.assertTrue(seen['syncDisabled'])
        self.assertTrue(seen['saveDisabled'])
        self.assertIn('firmware', seen['said'])
        broken = Target(self)
        broken.schedule_error = 'settings-unreadable'
        seen = run(broken, [dict(fill={'schedule-on': '17:30'}, look='blocked')])['blocked']
        self.assertTrue(seen['saveDisabled'])
        self.assertIn('could not be read', seen['scheduleState'])
        self.assertEqual(old.mutations() + broken.mutations(), [])

    def test_controls_are_labelled_and_fit_phone_sizes(self):
        target = Target(self)
        for size in SIZES:
            with self.subTest(size=size):
                layout = run(target, [dict(measure='layout')], size=size)['layout']
                self.assertLessEqual(layout['scrollWidth'], layout['width'])
                names = {'time-auto', 'schedule-enabled', 'schedule-on', 'schedule-off', 'time-sync', 'time-refresh', 'schedule-save', 'schedule-resume'}
                self.assertEqual({entry['what'] for entry in layout['controls']} & names, names)
                self.assertEqual({entry['id'] for entry in layout['timingLabels']}, {'time-auto', 'schedule-enabled', 'schedule-on', 'schedule-off'})
                self.assertTrue(all(entry['label'] for entry in layout['timingLabels']))
                for control in layout['controls']:
                    if control['what'] in ('time-auto', 'schedule-enabled', 'schedule-on', 'schedule-off', 'time-sync', 'time-refresh', 'schedule-save', 'schedule-resume'):
                        self.assertGreaterEqual(control['bottom'] - control['top'], 48)

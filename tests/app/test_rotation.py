import json
from pathlib import Path
import threading
import unittest

from tests.core import support as native
from tests.core.test_mini import files_for
from tests.core.test_rotation import revision
from tests.emulator import support as emulator
from . import support
from .test_clocks import Target as ClocksTarget


class Target(ClocksTarget):
    def __init__(self, test, angle=0, legacy=False):
        self.angle = angle
        self.legacy = legacy
        self.supported = True
        self.status_values = {}
        self.lose = False
        self.changed = threading.Event()
        self.hold = threading.Event()
        self.entered = threading.Event()
        self.release = threading.Event()
        test.addCleanup(self.release.set)
        super().__init__(test)

    def reply(self, line):
        if line == b'status' and self.hold.is_set():
            self.hold.clear()
            self.entered.set()
            if not self.release.wait(10):
                return 500, ''
        words = line.decode().split()
        if words[0] != 'rotation' or self.legacy or not self.answering:
            return super().reply(line)
        if len(words) > 1:
            if self.refusal:
                return 200, json.dumps(dict(ok=False, error=self.refusal))
            if int(words[2]) != revision(self.angle):
                return 200, json.dumps(dict(ok=False, error='rotation-conflict'))
            self.angle = int(words[3])
            self.changed.set()
            if self.lose:
                self.answering = False
                return 500, ''
        return 200, json.dumps(dict(ok=True, supported=self.supported, degrees=self.angle,
                                    revision=revision(self.angle), error=None))

    def status(self):
        status, body = super().status()
        return status, json.dumps({**json.loads(body), **self.status_values})

    def mutations(self):
        return [line.decode() for _, line in self.stand_in.lines if line.startswith(b'rotation set ')]


def run(target, acts=(), **kwargs):
    return support.run('rotation', address=target.stand_in.address,
                       settings=dict(acts=acts), **kwargs).seen


class RotationControls(unittest.TestCase):
    def test_native_configuration_can_be_saved_without_a_usable_installation(self):
        square = files_for()
        cases = {
            'missing mapping and show': {},
            'malformed show': {'mapping.json': square['mapping.json'], 'show.json': b'broken'},
        }
        for label, files in cases.items():
            with self.subTest(label=label), native.installed(files) as folder, emulator.Emulator(folder, checked=False) as target:
                status = json.loads(target.command('status'))
                self.assertEqual(status['readiness'], 'recovery')
                self.assertIsNotNone(status['error'])
                acts = [dict(choose=90, until=dict(value='90', disabled=False), look='saved'),
                        dict(reload=True, until=dict(value='90', disabled=False), look='again')]
                seen = support.run('rotation', address=f'127.0.0.1:{target.port}',
                                   settings=dict(rows=0, acts=acts)).seen
                self.assertFalse(seen['first']['disabled'])
                self.assertFalse(seen['again']['disabled'])
                self.assertEqual(json.loads(target.command('rotation'))['degrees'], 90)
                self.assertEqual(Path(folder, 'rotation.txt').read_bytes(), b'1 90\n')

    def test_a_configuration_fault_is_not_reported_as_unsupported_rotation(self):
        for reason in ('mapping-missing', 'show-invalid broken'):
            with self.subTest(reason=reason):
                target = Target(self)
                target.supported = False
                target.status_values = dict(error=reason, width=60, height=60)
                seen = run(target)
                self.assertTrue(seen['first']['disabled'])
                self.assertIn('configuration', seen['first']['said'])
                self.assertIn(reason, seen['first']['said'])
                self.assertNotIn('does not support', seen['first']['said'])
                self.assertEqual(target.mutations(), [])

    def test_an_unconfirmed_canvas_is_not_reported_as_unsupported_rotation(self):
        target = Target(self)
        target.supported = False
        seen = run(target)
        self.assertTrue(seen['first']['disabled'])
        self.assertIn('configuration', seen['first']['said'])
        self.assertNotIn('does not support', seen['first']['said'])
        self.assertEqual(target.mutations(), [])

    def test_a_legacy_rectangular_canvas_remains_unsupported(self):
        target = Target(self)
        target.supported = False
        target.status_values = dict(width=60, height=6)
        seen = run(target)
        self.assertTrue(seen['first']['disabled'])
        self.assertIn('does not support', seen['first']['said'])
        self.assertEqual(target.mutations(), [])

    def test_a_fresh_legacy_refusal_replaces_an_older_configuration_diagnosis(self):
        target = Target(self)
        target.supported = False
        target.status_values = dict(error='mapping-missing', width=None, height=None)
        seen = run(target, [dict(step=True), dict(refresh=True, wait=500, look='legacy')],
                   steps=[lambda: setattr(target, 'legacy', True)])
        self.assertTrue(seen['legacy']['disabled'])
        self.assertIn('does not support', seen['legacy']['said'])
        self.assertNotIn('configuration', seen['legacy']['said'])
        self.assertEqual(target.mutations(), [])

    def test_four_choices_apply_and_survive_reopening_on_the_native_core(self):
        with native.installed(files_for()) as folder, emulator.Emulator(folder) as target:
            acts = [dict(choose=90, look='pending'), dict(until=dict(value='90', disabled=False))]
            acts += [dict(choose=angle, until=dict(value=str(angle), disabled=False), look=str(angle))
                     for angle in (180, 270, 0)]
            acts += [dict(reload=True, until=dict(value='0', disabled=False), look='again')]
            seen = support.run('rotation', address=f'127.0.0.1:{target.port}',
                               settings=dict(rows=1, acts=acts)).seen
            self.assertTrue(seen['first']['present'])
            self.assertEqual(seen['first']['options'], ['0', '90', '180', '270'])
            self.assertEqual(seen['pending']['value'], '0')
            self.assertTrue(seen['pending']['disabled'])
            self.assertFalse(seen['again']['disabled'])
            self.assertEqual(json.loads(target.command('rotation'))['degrees'], 0)
            self.assertEqual(Path(folder, 'rotation.txt').read_bytes(), b'1 0\n')

    def test_refusal_retains_confirmed_value_and_does_not_replay(self):
        target = Target(self)
        target.refusal = 'busy'
        seen = run(target, [dict(choose=90, until=dict(disabled=False, text='busy'), look='refused')])
        self.assertEqual(seen['refused']['value'], '0')
        self.assertEqual(len(target.mutations()), 1)

    def test_unknown_reply_is_reconciled_on_reconnect_without_replaying_the_save(self):
        target = Target(self)
        target.lose = True
        def recover():
            self.assertTrue(target.changed.wait(5))
            target.answering = True
            target.lose = False
        seen = run(target, [dict(choose=90, until=dict(disabled=True, text='Connect'), look='lost'),
                           dict(step=True, until=dict(value='90', disabled=False), look='back')], steps=[recover])
        self.assertEqual(seen['back']['value'], '90')
        self.assertEqual(len(target.mutations()), 1)

    def test_an_old_target_reply_cannot_write_or_confirm_for_the_new_target(self):
        first, second = Target(self), Target(self, angle=180)
        first.stand_in.delay = .3
        seen = run(first, [dict(choose=90), dict(target=second.stand_in.address,
                    until=dict(value='180', disabled=False), look='other')])
        self.assertEqual(seen['other']['value'], '180')
        self.assertEqual(second.mutations(), [])

    def test_legacy_firmware_disables_only_rotation_and_keeps_the_app_connected(self):
        target = Target(self, legacy=True)
        seen = run(target)
        self.assertTrue(seen['first']['disabled'])
        self.assertIn('does not support', seen['first']['said'])
        self.assertEqual(target.mutations(), [])

    def test_leaving_settings_cancels_a_save_waiting_behind_another_reply(self):
        target = Target(self)
        def blocked():
            self.assertTrue(target.entered.wait(5))
        seen = run(target, [dict(step=True, wait=2500), dict(step=True),
            dict(choose=90, look='queued'), dict(screen='Animations'), dict(step=True, wait=200),
            dict(screen='Settings', until=dict(value='0', disabled=False), look='back')],
            steps=[target.hold.set, blocked, target.release.set])
        self.assertTrue(seen['queued']['disabled'])
        self.assertEqual(seen['queued']['value'], '0')
        self.assertEqual(target.mutations(), [])
        self.assertEqual(seen['back']['value'], '0')

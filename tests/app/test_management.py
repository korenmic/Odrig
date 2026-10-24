import json
import pathlib
import tempfile
import unittest
import threading
import time
from tests.core import support as core_support
from tests.emulator import support as emulator_support
from . import support


class AnimationManagement(unittest.TestCase):
    def folder(self, root, count=39, protected=False, first=1):
        items = [{'id': first + n, 'file': 'a.odrg'} for n in range(count)]
        if protected:
            items.append({'id': 99, 'cycle': [first], 'seconds': 1})
        return emulator_support.installed(pathlib.Path(root, 'show'), {
            'mapping.json': core_support.mapping_texts()['legs-2'],
            'show.json': json.dumps({'version': 1, 'brightness': 32, 'items': items}),
            'a.odrg': core_support.clip(1, 60, 6, durations=(20,) * (1000 if count == 39 else 3), compressed=False),
        })

    def test_shared_toggle_persists_and_bulk_selection_crosses_the_batch_limit(self):
        with tempfile.TemporaryDirectory() as root:
            folder = self.folder(root)
            with emulator_support.Emulator(folder) as emulator:
                found = support.run('manage', address=f'127.0.0.1:{emulator.port}', settings={'rows': 39, 'selectable': 39, 'toggle': True}, steps=[lambda: emulator.command('ignore 1 0')]).seen
                self.assertTrue(found['before'])
                self.assertEqual(found['menu'], ['Ignore in playlist', 'Move up (disabled)', 'Move down', 'Select', 'Delete'])
                self.assertTrue(found['pending'])
                self.assertEqual(found['ignoredNote'], '\u2298 Ignored')
                self.assertEqual(found['ignoredMenu'], ['Restore to playlist', 'Move up (disabled)', 'Move down', 'Select', 'Delete'])
                self.assertTrue(found['restored'])
                self.assertEqual(found['hiddenBefore'], 0)
                self.assertEqual(found['selected'], 39)
                self.assertIn('39 animations', found['question'])
                self.assertIn('a.odrg', found['question'])
                self.assertEqual(found['remaining'], 0)
                self.assertTrue(found['deleteDisabled'])
                self.assertEqual(json.loads(emulator.command('list'))['items'], [])
                self.assertFalse((folder / 'a.odrg').exists())
                self.assertIn('Internal', found['dashboard'])

    def test_refused_batch_preserves_selection_after_refresh(self):
        with tempfile.TemporaryDirectory() as root:
            folder = self.folder(root, 2, protected=True)
            with emulator_support.Emulator(folder) as emulator:
                found = support.run('manage', address=f'127.0.0.1:{emulator.port}', settings={'rows': 2, 'selectable': 2, 'refused': True}).seen
                self.assertEqual((found['remaining'], found['kept']), (2, 2))
                self.assertIn('in-use', found['message'])
                self.assertTrue((folder / 'a.odrg').exists())

    def test_lost_reply_after_second_commit_is_reconciled_without_retry(self):
        with tempfile.TemporaryDirectory() as root:
            folder = self.folder(root)
            with emulator_support.Emulator(folder) as emulator:
                calls = []
                def forward(line):
                    reply = emulator.command(line.decode())
                    if line.startswith(b'remove many '):
                        calls.append(line)
                        if len(calls) == 2:
                            return 200, ''
                    return 200, reply
                with support.StandIn({name: forward for name in ['status', 'list', 'space', 'remove']}) as target:
                    found = support.run('manage', address=target.address, settings={'rows': 39, 'selectable': 39, 'uncertain': True}).seen
                    self.assertEqual(target.together, 1)
                self.assertEqual(len(calls), 2)
                self.assertEqual((found['remaining'], found['kept']), (0, 0))
                self.assertIn('32 of 39', found['message'])
                self.assertIn('No confirmed reply', found['message'])

    def test_external_items_have_no_mutation_controls_even_beside_high_installed_ids(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as drive:
            folder = self.folder(root, 1, first=60001)
            emulator_support.installed(pathlib.Path(drive, 'odrig'), {'external.odrg': (folder / 'a.odrg').read_bytes()})
            with emulator_support.Emulator(folder, '--drive', drive) as emulator:
                found = support.run('manage', address=f'127.0.0.1:{emulator.port}', settings={'rows': 2, 'selectable': 1, 'cancel': True}).seen
                self.assertEqual((found['selected'], found['removable']), (1, 1))
                self.assertIn('External', found['external'])
                self.assertNotIn('unavailable', found['external'])
                self.assertTrue(pathlib.Path(drive, 'odrig', 'external.odrg').exists())

    def test_target_change_clears_the_confirmation_and_selection(self):
        with tempfile.TemporaryDirectory() as root:
            with emulator_support.Emulator(self.folder(root, 2)) as emulator:
                found = support.run('manage-target', address=f'127.0.0.1:{emulator.port}').seen
                self.assertIn('2 animations', found['confirmed'])
                self.assertEqual(found['selected'], 0)
                self.assertTrue(found['disabled'])
                self.assertEqual(len(json.loads(emulator.command('list'))['items']), 2)

    def test_protocol_validates_inclusion_and_large_nullable_external_capacity(self):
        capacities = [
            {'present': True, 'free': 2**34, 'total': 2**35, 'read_only': True},
            {'present': False, 'free': None, 'total': None, 'read_only': True},
            {'present': True, 'free': None, 'total': None, 'read_only': True},
            {'present': False, 'free': 0, 'total': 1, 'read_only': True},
            {'present': True, 'free': 2**53, 'total': 2**54, 'read_only': True},
            {'present': True, 'free': 2, 'total': 1, 'read_only': True},
            {'present': True, 'free': None, 'total': 1, 'read_only': True},
        ]
        replies = [{'command': 'space', 'reply': {'ok': True, 'free': 1, 'total': 2, 'external': drive}} for drive in capacities]
        for ignored in [False, True, 'false', 0, None]:
            replies.append({'command': 'list', 'reply': {'ok': True, 'items': [{'id': 60001, 'file': 'a.odrg', 'bytes': 1, 'ignored': ignored}], 'next': None}})
        found = support.run('management-protocol', settings={'replies': replies}).seen
        self.assertEqual([item.get('error') for item in found['results'][:7]], [None]*3 + ['bad-reply']*4)
        self.assertEqual([item.get('error') for item in found['results'][7:]], [None]*2 + ['bad-reply']*3)
        self.assertEqual(found['sent'][-3:], ['ignore 60001 1', 'ignore 60001 0', 'remove many 1,60001'])

    def test_dashboard_refreshes_capacity_on_boot_reconnect_and_return(self):
        mode = {'offline': False, 'free': 1000000}
        def reply(line):
            if mode['offline']:
                return 503, ''
            if line == b'space':
                return 200, json.dumps({'ok': True, 'free': mode['free'], 'total': 4000000})
            return support.PLAYING if line == b'status' else support.LISTED
        def offline():
            mode['offline'] = True
        def recover():
            mode.update(offline=False, free=2000000)
        def foreground():
            mode['free'] = 3000000
        with support.StandIn({key: reply for key in ['status', 'list', 'space']}) as target:
            found = support.run('manage-refresh', address=target.address, steps=[offline, recover, foreground]).seen
            self.assertEqual(target.together, 1)
        self.assertIn('1.0 MB', found['before'])
        self.assertIn('2.0 MB', found['recovered'])
        self.assertIn('3.0 MB', found['foreground'])

    def test_target_change_during_a_batch_drops_the_reply_and_stops_remaining_batches(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            with emulator_support.Emulator(self.folder(first)) as old, emulator_support.Emulator(self.folder(second, 2)) as new:
                started = threading.Event()
                calls = []
                def forward(line):
                    reply = old.command(line.decode())
                    if line.startswith(b'remove many '):
                        calls.append(line)
                        started.set()
                        time.sleep(0.8)
                    return 200, reply
                with support.StandIn({key: forward for key in ['status', 'list', 'space', 'remove']}) as proxy:
                    found = support.run('manage-switch', address=proxy.address, settings={'other': f'127.0.0.1:{new.port}'}, steps=[lambda: self.assertTrue(started.wait(5))]).seen
                self.assertEqual(len(calls), 1)
                self.assertEqual(len(json.loads(old.command('list'))['items']), 7)
                self.assertEqual(len(json.loads(new.command('list'))['items']), 2)
                self.assertEqual(found, {'selected': 0, 'message': None, 'disabled': True})

    def test_refused_toggle_keeps_the_confirmed_value_and_refreshes(self):
        listed = {'ok': True, 'items': [{'id': 1, 'file': 'a.odrg', 'bytes': 1, 'ignored': False}], 'next': None}
        replies = {**support.SOUND, 'list': (200, json.dumps(listed)), 'ignore': (200, '{"ok":false,"error":"busy"}')}
        with support.StandIn(replies, delay=0.05) as target:
            found = support.run('manage', address=target.address, settings={'rows': 1, 'refuseToggle': True}).seen
        self.assertTrue(found['pending'])
        self.assertTrue(found['checked'])
        lines = [line for _, line in target.lines]
        self.assertEqual(lines.count(b'ignore 1 1'), 1)
        self.assertIn(b'list 0', lines[lines.index(b'ignore 1 1') + 1:])

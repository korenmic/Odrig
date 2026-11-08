import json
import pathlib
import tempfile
import unittest

from emulator import binding, host
from tests.core.test_clocks import clock_of
from tests.core.test_mini import files_for
from . import support


SETTINGS = b'odrig-clocks 2\nmode only\nmessage off\n'


class PolicyFiles(host.FolderHost):
    fault = None
    attempts = 0

    def open(self, name):
        if name == 'clocks.txt' and self.fault == 'open':
            return -1
        return super().open(name)

    def read_at(self, name, offset, capacity):
        if name == 'clocks.txt':
            self.attempts += 1
            if self.fault == 'first' or self.fault == 'partial' and offset > 0:
                return None
            if self.fault == 'partial':
                capacity = min(capacity, 8)
        return super().read_at(name, offset, capacity)


class SavedPolicyRecovery(unittest.TestCase):
    def start(self, *, fault=None, data=SETTINGS):
        root = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        source = files_for()
        if data is not None:
            source['clocks.txt'] = data
        folder = support.installed(root / 'show', source)
        card = root / 'card' / 'odrig' / 'clocks'
        card.mkdir(parents=True)
        (card / 'face.odrgx').write_bytes(clock_of(canvas=(60, 60)))
        files = PolicyFiles(folder, drive=host.Drive(card.parent.parent))
        files.fault = fault
        self.addCleanup(files.release)
        core = binding.Core(support.LIBRARY, files)
        return core, files, folder

    def status(self, core, now):
        return json.loads(core.command(now, b'status'))

    def dark(self, core, end=600):
        for now in range(0, end + 1, 20):
            core.poll(now)
            self.assertFalse(any(core.frame()), f'normal frame at {now}')
        status = self.status(core, end)
        self.assertEqual(status['clock_mode'], 'only')
        self.assertEqual(status.get('clock_error'), 'unreadable')
        self.assertIsNone(status['animation'])
        return status

    def test_initial_and_partial_read_errors_never_play_root(self):
        for fault in ('first', 'partial', 'open'):
            with self.subTest(fault=fault):
                core, files, folder = self.start(fault=fault)
                self.dark(core)
                self.assertEqual((folder / 'clocks.txt').read_bytes(), SETTINGS)
                self.assertIn('clocks unreadable', files.logged)

    def test_corrupt_and_empty_saved_policy_never_play_root(self):
        for data in (b'', SETTINGS[:-1], SETTINGS + b'x', b'bad', b'x' * 65):
            with self.subTest(data=data):
                core, _, _ = self.start(data=data)
                self.dark(core)

    def test_authoritatively_missing_policy_keeps_normal_default(self):
        core, _, _ = self.start(data=None)
        for now in range(0, 1001, 20):
            core.poll(now)
        status = self.status(core, 1000)
        self.assertEqual(status['clock_mode'], 'off')
        self.assertIsNone(status.get('clock_error'))
        self.assertEqual(status['file'], 'picture.odrg')

    def test_retry_is_bounded_and_recovers_without_changing_saved_bytes(self):
        core, files, folder = self.start(fault='first')
        self.dark(core)
        attempts = files.attempts
        for now in range(620, 981, 20):
            core.poll(now)
        self.assertEqual(files.attempts, attempts)
        files.fault = None
        for now in range(1000, 4001, 20):
            core.poll(now)
        status = self.status(core, 4000)
        self.assertEqual(status['clock_mode'], 'only')
        self.assertIsNone(status.get('clock_error'))
        self.assertEqual(status['file'], 'clocks/face.odrgx')
        self.assertEqual((folder / 'clocks.txt').read_bytes(), SETTINGS)

    def test_explicit_mode_replaces_corrupt_policy_even_if_effective_mode_matches(self):
        for mode in ('only', 'off', 'between'):
            with self.subTest(mode=mode):
                core, _, folder = self.start(data=b'bad')
                self.dark(core)
                self.assertEqual(json.loads(core.command(600, b'clocks message on')),
                                 dict(ok=False, error='storage-error'))
                word = 'on' if mode == 'between' else mode
                self.assertEqual(json.loads(core.command(600, f'clocks {word}'.encode())), dict(ok=True))
                for now in range(620, 2001, 20):
                    core.poll(now)
                status = self.status(core, 2000)
                self.assertEqual(status['clock_mode'], mode)
                self.assertIsNone(status.get('clock_error'))
                self.assertEqual((folder / 'clocks.txt').read_bytes(),
                                 f'odrig-clocks 2\nmode {mode}\nmessage off\n'.encode())

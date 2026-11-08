import base64
import json
import pathlib
import tempfile
import unittest

from emulator import binding, host
from tests.core.test_civil_time import snapshot, revision

from . import support


class NativeTiming(unittest.TestCase):
    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        self.files = host.FolderHost(self.folder)
        self.addCleanup(self.files.release)
        self.core = binding.Core(support.LIBRARY, self.files)

    def ask(self, line, now=0):
        return json.loads(self.core.command(now, line.encode('ascii')))

    def test_identity_is_stable_per_board_and_not_an_address_or_build_name(self):
        board = self.ask('time').get('board')
        self.assertIsInstance(board, str)
        self.assertRegex(board, r'\Aemu-[0-9a-f]{24}\Z')
        self.assertEqual(host.FolderHost(self.folder).identity(), board)
        self.assertNotEqual(host.FolderHost(self.folder.parent).identity(), board)
        self.assertEqual(self.ask('time', 1000)['board'], board)

    def test_guarded_mutations_cannot_reach_another_board_at_the_same_address(self):
        board = self.ask('time')['board']
        zone = snapshot()
        before = self.ask('schedule')
        wrong = 'guard another-board '
        operations = [f'time zone {base64.urlsafe_b64encode(zone).decode().rstrip("=")}',
                      f'time set 1800000000 {revision(zone)}',
                      f'schedule set {before["revision"]} 09:00 17:00 on',
                      f'schedule resume {before["revision"]}']
        for line in operations:
            self.assertEqual(self.ask(wrong + line), dict(ok=False, error='stale'))
        self.assertFalse((self.folder / 'timezone.bin').exists())
        self.assertFalse((self.folder / 'schedule.txt').exists())
        self.assertEqual(self.ask(f'guard {board} schedule'), before)
        self.assertEqual(self.ask(f'guard {board} time')['board'], board)
        self.assertEqual(self.ask(f'guard {board} ' + operations[0]), dict(ok=True))
        self.assertEqual(self.ask(f'guard {board} ' + operations[1]), dict(ok=True))
        self.assertTrue(self.ask(f'guard {board} time')['valid'])

    def test_longest_guarded_zone_still_fits_the_original_line_limit(self):
        board = 'b' * 31
        self.files.identity = lambda: board
        zone = snapshot('Test/Zone', (0, 3600),
                        tuple((1800000000 + n * 60, (n + 1) % 2) for n in range(276)))
        line = f'guard {board} time zone {base64.urlsafe_b64encode(zone).decode().rstrip("=")}'
        self.assertEqual(len(line), 2048)
        replies = self.core.feed(0, line[:1000].encode('ascii'))
        self.assertEqual(replies, [])
        replies = self.core.feed(0, line[1000:].encode('ascii') + b'\n')
        self.assertEqual(len(replies), 1)
        self.assertEqual(json.loads(replies[0][1]), dict(ok=True))
        self.assertEqual((self.folder / 'timezone.bin').read_bytes(), zone)

    def test_missing_or_malformed_identity_is_explicit_and_not_truncated(self):
        for identity in (None, '', 'x' * 32, 'not one word', 'é'):
            self.files.identity = lambda identity=identity: identity
            self.assertIsNone(self.ask('time')['board'])
            self.assertEqual(self.ask('guard board time'), dict(ok=False, error='unsupported'))

    def test_guard_syntax_and_scope_are_strict(self):
        board = self.ask('time')['board']
        for line in ('guard', 'guard board', 'guard  time', 'guard ' + 'x' * 32 + ' time',
                     f'guard {board} status', f'guard {board} guard {board} time'):
            self.assertEqual(self.ask(line), dict(ok=False, error='bad-argument'), line)

    def test_read_only_power_api_reports_the_core_without_creating_an_override(self):
        power = lambda: self.core._library.odrig_core_power(self.core._core)
        self.assertEqual(power(), 1)
        self.assertIsNone(self.ask('schedule')['override'])
        self.assertTrue(self.ask('off')['ok'])
        self.assertEqual(power(), 0)
        self.assertEqual(self.ask('schedule')['override'], 'off')
        self.assertTrue(self.ask('on')['ok'])
        self.assertEqual(power(), 1)

    def test_identity_and_timing_reads_remain_available_during_show_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            files = host.FolderHost(pathlib.Path(directory))
            try:
                core = binding.Core(support.LIBRARY, files)
                self.assertIsNotNone(core.error())
                board = json.loads(core.command(0, b'time'))['board']
                clock = json.loads(core.command(0, f'guard {board} time'.encode('ascii')))
                self.assertFalse(clock['valid'])
                state = json.loads(core.command(0, f'guard {board} schedule'.encode('ascii')))
                self.assertEqual((state['on'], state['off'], state['reason']), ('18:00', '06:00', 'time-unset'))
            finally:
                files.release()

    def test_reset_keeps_zone_and_manual_mode_but_never_restores_the_epoch(self):
        board = self.ask('time')['board']
        zone = snapshot()
        encoded = base64.urlsafe_b64encode(zone).decode().rstrip('=')
        self.assertTrue(self.ask(f'guard {board} time zone {encoded}')['ok'])
        self.assertTrue(self.ask(f'guard {board} time set 1800000000 {revision(zone)}')['ok'])
        self.assertTrue(self.ask('off')['ok'])
        self.files.release()
        files = host.FolderHost(self.folder)
        self.addCleanup(files.release)
        restarted = binding.Core(support.LIBRARY, files)
        clock = json.loads(restarted.command(0, b'time'))
        schedule = json.loads(restarted.command(0, b'schedule'))
        self.assertEqual((clock['board'], clock['revision'], clock['valid']), (board, revision(zone), False))
        self.assertEqual((schedule['override'], schedule['power']), ('off', False))


class ToolTiming(unittest.TestCase):
    def test_http_and_tcp_tools_share_guarded_time_and_schedule_state(self):
        with support.example_show() as folder, support.Emulator(folder) as emulator:
            board = json.loads(emulator.command('time'))['board']
            zone = snapshot()
            encoded = base64.urlsafe_b64encode(zone).decode().rstrip('=')
            for target in (('--http', f'127.0.0.1:{emulator.port}'), support.line_target(emulator)):
                def ask(*words):
                    result = support.run_tool(*target, 'guard', board, *words)
                    self.assertEqual(result.err, '')
                    self.assertEqual(result.status, 0, result.out)
                    return json.loads(result.out)
                self.assertTrue(ask('time', 'zone', encoded)['ok'])
                self.assertTrue(ask('time', 'set', '1800036000', revision(zone))['ok'])
                clock = ask('time')
                self.assertEqual(clock['board'], board)
                self.assertTrue(clock['valid'])
                self.assertLess(abs(clock['utc'] - 1800036000), 5)
                state = ask('schedule')
                self.assertTrue(ask('schedule', 'set', state['revision'], '09:00', '17:00', 'off')['ok'])
                state = ask('schedule')
                self.assertEqual((state['on'], state['off'], state['enabled']), ('09:00', '17:00', False))
                self.assertTrue(ask('schedule', 'resume', state['revision'])['ok'])

import base64
import json
import struct
import unittest
import zlib

from . import support

FIRST = 946684800
UNTIL = 4102444800


def snapshot(name='UTC', offsets=(0,), transitions=(), initial=0):
    header = bytearray(120)
    header[:8] = b'ODTZ0001'
    struct.pack_into('<IIBBH', header, 8, FIRST, UNTIL, initial, len(offsets), len(transitions))
    encoded = name.encode('ascii')
    header[20] = len(encoded)
    for at, offset in enumerate(offsets):
        struct.pack_into('<i', header, 24 + 4 * at, offset)
    header[56:56 + len(encoded)] = encoded
    return bytes(header) + b''.join(struct.pack('<IB', utc, offset) for utc, offset in transitions)


def revision(data):
    return f'{zlib.crc32(data):08x}'


def install(data):
    return 'time zone ' + base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def replies(run):
    return [json.loads(line[6:]) for line in run.lines if line.startswith('reply ')]


def run_commands(commands, files=None, options=()):
    script = [support.line(at, line) for at, line in commands]
    return support.start(support.example_show() if files is None else files, script, list(options))


class CivilTime(unittest.TestCase):
    def test_unset_time_is_explicit_and_status_advertises_support(self):
        state, status = replies(run_commands([(0, 'time'), (0, 'status')]))
        self.assertTrue(state['ok'])
        self.assertFalse(state['valid'])
        self.assertIsNone(state['utc'])
        self.assertIsNone(state['zone'])
        self.assertTrue(status['timing'])

    def test_accepted_clock_advances_without_poll_or_network(self):
        data = snapshot()
        values = replies(run_commands([(100, install(data)),
            (100, f'time set 1800000000 {revision(data)}'), (3100, 'time')]))
        self.assertEqual(values[:2], [dict(ok=True)] * 2)
        self.assertEqual((values[2]['utc'], values[2]['offset'], values[2]['zone']),
                         (1800000003, 0, 'UTC'))
        self.assertEqual(values[2]['revision'], revision(data))

    def test_clock_set_requires_a_known_zone_and_matching_revision(self):
        data = snapshot()
        values = replies(run_commands([(0, 'time set 1800000000 00000000'),
            (0, install(data)), (0, 'time set 1800000000 00000000'), (0, 'time')]))
        self.assertEqual(values[0], dict(ok=False, error='zone-unset'))
        self.assertEqual(values[2], dict(ok=False, error='stale'))
        self.assertFalse(values[3]['valid'])

    def test_bad_time_forms_never_change_accepted_time(self):
        data = snapshot()
        bad = ['time extra', 'time set -1 ' + revision(data),
               f'time set {FIRST - 1} {revision(data)}', f'time set {UNTIL} {revision(data)}',
               f'time set 4294967296 {revision(data)}', 'time set 1800000000 xxxxxxxx',
               f'time set 1800000000 {revision(data)} extra', 'time zone']
        commands = [(0, install(data)), (0, f'time set 1800000000 {revision(data)}')]
        commands += [(0, line) for line in bad] + [(0, 'time')]
        values = replies(run_commands(commands))
        self.assertEqual(values[2:-1], [dict(ok=False, error='bad-argument')] * len(bad))
        self.assertEqual(values[-1]['utc'], 1800000000)

    def test_epoch_corrections_are_independent_of_monotonic_time(self):
        data = snapshot()
        values = replies(run_commands([(0, install(data)),
            (100, f'time set 1800000000 {revision(data)}'),
            (2100, f'time set 1700000000 {revision(data)}'), (3100, 'time'),
            (3100, f'time set 1900000000 {revision(data)}'), (4100, 'time')]))
        self.assertEqual((values[3]['utc'], values[5]['utc']), (1700000001, 1900000001))

    def test_dst_changes_work_offline_and_corrections_rewind_the_zone_cursor(self):
        data = snapshot('Europe/Test', (3600, 7200), ((1800000010, 1), (1800000020, 0)))
        values = replies(run_commands([(0, install(data)),
            (0, f'time set 1800000000 {revision(data)}'), (9000, 'time'),
            (10000, 'time'), (20000, 'time'),
            (20000, f'time set 1800000000 {revision(data)}'), (20000, 'time')]))
        self.assertEqual([values[n]['offset'] for n in (2, 3, 4, 6)], [3600, 7200, 3600, 3600])

    def test_zone_survives_restart_but_time_never_does(self):
        data = snapshot('Asia/Test', (19800,))
        with support.installed(support.example_show()) as folder:
            first = support.session(folder, [support.line(0, install(data)),
                support.line(0, f'time set 1800000000 {revision(data)}')])
            self.assertEqual(replies(first), [dict(ok=True)] * 2)
            self.assertEqual(support.folder_files(folder)['timezone.bin'], data)
            state = replies(support.session(folder, [support.line(0, 'time')]))[0]
            self.assertFalse(state['valid'])
            self.assertIsNone(state['utc'])
            self.assertEqual((state['zone'], state['revision']), ('Asia/Test', revision(data)))

    def test_zone_update_preserves_the_current_epoch(self):
        old, new = snapshot(), snapshot('Etc/Test', (-3600,))
        values = replies(run_commands([(0, install(old)),
            (0, f'time set 1800000000 {revision(old)}'), (2000, install(new)), (2000, 'time')]))
        self.assertEqual(values[-1]['utc'], 1800000002)
        self.assertEqual((values[-1]['zone'], values[-1]['offset']), ('Etc/Test', -3600))

    def test_unchanged_zone_and_routine_time_set_write_nothing(self):
        data = snapshot()
        files = {**support.example_show(), 'timezone.bin': data}
        run = run_commands([(0, install(data)), (0, f'time set 1800000000 {revision(data)}'),
                            (1000, 'time'), (2000, 'time')], files, ['--trace-store'])
        self.assertEqual(replies(run)[:2], [dict(ok=True)] * 2)
        self.assertFalse(any(line.startswith('store ') for line in run.lines))

    def test_corrupt_zone_is_reported_and_an_abandoned_part_is_not_published(self):
        for data in (b'', snapshot()[:-1], b'not-a-zone', snapshot() + b'x'):
            with self.subTest(data=data[:8]):
                files = {**support.example_show(), 'timezone.bin': data, 'timezone.part': snapshot()}
                value = replies(run_commands([(0, 'time')], files))[0]
                self.assertFalse(value['valid'])
                self.assertEqual(value['error'], 'zone-unreadable')

    def test_malformed_snapshots_cannot_replace_the_previous_zone(self):
        data = snapshot()
        bad = [data[:-1], data + b'\0', snapshot('', (0,)), snapshot('../outside'),
               snapshot('UTC', (0, 0)), snapshot('UTC', (86401,)),
               snapshot('UTC', (0,), ((FIRST, 0),)),
               snapshot('UTC', (0,), ((UNTIL, 0),)),
               snapshot('UTC', (0,), ((1800000001, 0), (1800000000, 0))),
               snapshot('UTC', (0,), ((1800000001, 1),))]
        for content in bad:
            with self.subTest(content=content[:30]):
                files = {**support.example_show(), 'timezone.bin': data}
                run, kept = support.start_and_keep(files, [support.line(0, install(content)), support.line(0, 'time')])
                self.assertEqual(replies(run)[0], dict(ok=False, error='bad-argument'))
                self.assertEqual(kept['timezone.bin'], data)
                self.assertEqual(replies(run)[1]['revision'], revision(data))

    def test_noncanonical_or_oversized_base64_is_refused(self):
        for encoded in ('A', '=', '!!!!', 'AA=', 'AA+', 'A' * 2004):
            with self.subTest(encoded=encoded[:12]):
                value = replies(run_commands([(0, 'time zone ' + encoded)]))[0]
                self.assertEqual(value, dict(ok=False, error='bad-argument'))

    def test_clock_range_end_never_wraps_to_another_date(self):
        data = snapshot()
        state = replies(run_commands([(0, install(data)),
            (0, f'time set {UNTIL - 1} {revision(data)}'), (1000, 'time')]))[-1]
        self.assertFalse(state['valid'])
        self.assertIsNone(state['utc'])

    def test_zone_save_faults_keep_previous_published_rules(self):
        old, new = snapshot(), snapshot('Other/Zone', (7200,))
        source = {**support.example_show(), 'timezone.bin': old}
        script = [support.line(0, install(new)), support.line(0, 'time')]
        baseline, kept = support.start_and_keep(source, script, ['--trace-store'])
        self.assertEqual(kept['timezone.bin'], new)
        first = len(baseline.stored) + 1
        calls = sum(line.startswith('store ') for line in baseline.lines)
        self.assertGreaterEqual(calls, 4)
        for at in range(first, first + calls):
            with self.subTest(at=at):
                run, files = support.start_and_keep(source, script, ['--store-fails-at', str(at)])
                self.assertEqual(replies(run)[0], dict(ok=False, error='storage-error'))
                self.assertEqual(files['timezone.bin'], old)
                self.assertEqual(replies(run)[1]['revision'], revision(old))

    def test_monotonic_low_word_rollover_and_backwards_inputs_do_not_rewind_time(self):
        data = snapshot()
        start = (1 << 32) - 500
        values = replies(run_commands([(start, install(data)),
            (start, f'time set 1800000000 {revision(data)}'),
            (start + 1000, 'time'), (200, 'time'), (start + 2000, 'time')]))
        self.assertEqual([v['utc'] for v in values[2:]], [1800000001, 1800000001, 1800000002])

    def test_the_largest_snapshot_fits_the_existing_command_and_reply_bounds(self):
        data = snapshot('A' * 63, (0, 3600), tuple((1800000000 + n * 1000, n % 2) for n in range(276)))
        self.assertEqual(len(data), 1500)
        line = install(data)
        self.assertLessEqual(len(line), 2048)
        values = replies(run_commands([(0, line), (0, 'time')]))
        self.assertEqual(values[0], dict(ok=True))
        self.assertEqual(values[1]['zone'], 'A' * 63)

    def test_each_zone_publication_cut_leaves_the_old_or_new_complete_snapshot(self):
        old, new = snapshot(), snapshot('Etc/Test', (3600,))
        source = {**support.example_show(), 'timezone.bin': old}
        script = [support.line(0, install(new))]
        baseline, _ = support.start_and_keep(source, script, ['--trace-store'])
        first = len(baseline.stored) + 1
        calls = sum(line.startswith('store ') for line in baseline.lines)
        for at in range(first, first + calls):
            for keeps in (0, 1):
                with self.subTest(at=at, keeps=keeps):
                    _, left = support.start_and_keep(source, script,
                        ['--cut-at', str(at), '--cut-keeps', str(keeps)], status=75)
                    self.assertIn(left['timezone.bin'], (old, new))
                    state = replies(run_commands([(0, 'time')], left))[0]
                    self.assertFalse(state['valid'])
                    self.assertEqual(state['revision'], revision(left['timezone.bin']))

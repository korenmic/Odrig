import unittest

from . import support
from .test_civil_time import install, replies, revision, snapshot

DAY = 1800000000 // 86400 * 86400
UTC = snapshot()


def settings(enabled=1, on=1080, off=360, mode=0):
    return f'odrig-schedule 1\n{enabled} {on} {off} {mode}\n'.encode('ascii')


def source(config=None, zone=UTC):
    files = {**support.example_show(), 'timezone.bin': zone}
    if config is not None:
        files['schedule.txt'] = config
    return files


def run(commands, files=None, options=()):
    return support.start(source() if files is None else files,
                         [support.line(at, line) for at, line in commands], list(options))


def clock(utc, zone=UTC):
    return f'time set {utc} {revision(zone)}'


class DailySchedule(unittest.TestCase):
    def test_scheduled_off_blacks_out_leds_but_playback_keeps_advancing(self):
        files = {'mapping.json': support.mapping_texts()['legs-2'],
                 'show.json': support.show_text([{'id': 1, 'file': 'x.odrg'}]),
                 'x.odrg': support.clip(1, 60, 6, (20, 20)), 'timezone.bin': UTC}
        script = ['poll 0', support.line(0, 'repeat 1 99'), support.line(0, clock(DAY + 12 * 3600)),
                  'poll 2000', support.line(2000, 'status'),
                  support.line(2000, clock(DAY + 18 * 3600)), 'poll 2020', support.line(2020, 'status')]
        result = support.start(files, script)
        values = replies(result)
        off, on = values[2], values[4]
        self.assertFalse(off['on'])
        self.assertTrue(on['on'])
        self.assertGreater(off['loop'], 1)
        self.assertGreaterEqual(on['loop'], off['loop'])
        self.assertEqual((off['animation'], on['animation'], on['repeat']), (1, 1, 99))
        frames = [bytes.fromhex(line.split()[2]) for line in result.lines if line.startswith('data 1 ')]
        self.assertFalse(any(frames[-2]))
        self.assertTrue(any(frames[-1]))

    def test_normal_refreshes_neither_read_zone_rules_nor_write_timing_settings(self):
        script = [support.line(0, clock(DAY + 12 * 3600))]
        script += [f'poll {tick}' for tick in range(0, 1020, 20)]
        script += [support.line(1020, 'status')]
        result = support.start(source(settings()), script, ['--trace-read-at', '--trace-store'])
        first = next(index for index, line in enumerate(result.lines) if line.startswith('reply '))
        following = result.lines[first + 1:]
        self.assertFalse(any(line.startswith('read_at timezone.bin') for line in following))
        self.assertFalse(any(line.startswith('store ') and ('schedule.' in line or 'timezone.' in line) for line in following))

    def test_manual_off_during_upload_is_immediate_without_destroying_the_upload(self):
        before = settings(mode=1)
        values = replies(run([(0, 'upload begin 1 hello.odrg 100'), (0, 'off'),
                              (0, 'schedule'), (0, 'upload cancel')], source(before)))
        self.assertTrue(values[0]['ok'])
        self.assertEqual(values[1], dict(ok=False, error='busy'))
        self.assertEqual((values[2]['power'], values[2]['override'], values[2]['saved']), (False, 'off', False))
        self.assertTrue(values[-1]['ok'])

    def test_defaults_are_visible_but_unset_time_bypasses_scheduling(self):
        state = replies(run([(0, 'schedule')]))[0]
        self.assertTrue(state['ok'])
        self.assertEqual((state['enabled'], state['on'], state['off']), (True, '18:00', '06:00'))
        self.assertIsNone(state['override'])
        self.assertFalse(state['active'])
        self.assertEqual(state['reason'], 'time-unset')
        self.assertTrue(state['power'])
        self.assertEqual(state['revision'], revision(settings()))

    def test_overnight_boundaries_are_inclusive_on_and_exclusive_off(self):
        values = replies(run([(0, clock(DAY + 18 * 3600 - 1)), (0, 'schedule'),
                              (1000, 'schedule'), (43201000, 'schedule')]))
        self.assertEqual(values[0], dict(ok=True))
        self.assertEqual([v['power'] for v in values[1:]], [False, True, False])
        self.assertTrue(all(v['active'] for v in values[1:]))

    def test_same_day_window_and_settings_are_confirmed_and_persisted(self):
        before = revision(settings())
        changed = settings(on=9 * 60, off=17 * 60)
        with support.installed(source()) as folder:
            saved = support.session(folder, [support.line(0, f'schedule set {before} 09:00 17:00 on'),
                support.line(0, clock(DAY + 9 * 3600 - 1)), support.line(0, 'schedule'),
                support.line(1000, 'schedule'), support.line(28801000, 'schedule')])
            values = replies(saved)
            self.assertEqual(values[:2], [dict(ok=True)] * 2)
            self.assertEqual([v['power'] for v in values[2:]], [False, True, False])
            self.assertEqual(values[-1]['revision'], revision(changed))
            self.assertEqual(support.folder_files(folder)['schedule.txt'], changed)
            again = replies(support.session(folder, [support.line(0, 'schedule')]))[0]
            self.assertEqual((again['on'], again['off'], again['reason']), ('09:00', '17:00', 'time-unset'))

    def test_manual_on_survives_boundaries_corrections_and_settings_edits_until_resume(self):
        manual = revision(settings(mode=1))
        changed = revision(settings(on=1200, off=300, mode=1))
        values = replies(run([(0, clock(DAY + 12 * 3600)), (0, 'on'),
            (0, 'schedule'), (86400000, 'schedule'),
            (86400000, clock(DAY + 10 * 3600)),
            (86400000, f'schedule set {manual} 20:00 05:00 on'),
            (86400000, 'schedule'), (86400000, f'schedule resume {changed}'),
            (86400000, 'schedule')]))
        for index in (2, 3, 6):
            self.assertEqual((values[index]['override'], values[index]['power']), ('on', True))
            self.assertFalse(values[index]['active'])
        self.assertIsNone(values[-1]['override'])
        self.assertFalse(values[-1]['power'])
        self.assertTrue(values[-1]['active'])

    def test_manual_off_survives_zone_and_time_updates(self):
        other = snapshot('Etc/Test', (3600,))
        values = replies(run([(0, clock(DAY + 21 * 3600)), (0, 'off'),
            (0, install(other)), (0, clock(DAY + 22 * 3600, other)), (0, 'schedule')]))
        self.assertEqual(values[-1]['override'], 'off')
        self.assertFalse(values[-1]['power'])
        self.assertFalse(values[-1]['active'])

    def test_manual_modes_survive_reset_while_epoch_validity_does_not(self):
        for command, mode, expected in (('on', 1, True), ('off', 2, False)):
            with self.subTest(command=command), support.installed(source()) as folder:
                saved = replies(support.session(folder, [support.line(0, command)]))
                self.assertEqual(saved, [dict(ok=True)])
                self.assertEqual(support.folder_files(folder)['schedule.txt'], settings(mode=mode))
                after = replies(support.session(folder, [support.line(0, 'time'), support.line(0, 'schedule')]))
                self.assertFalse(after[0]['valid'])
                self.assertEqual((after[1]['override'], after[1]['power']), (command, expected))

    def test_disabled_schedule_retains_times_and_manual_mode(self):
        data = settings(enabled=0, on=600, off=900, mode=2)
        values = replies(run([(0, clock(DAY + 12 * 3600)), (0, 'schedule'),
                              (0, f'schedule resume {revision(data)}'), (0, 'schedule')], source(data)))
        self.assertEqual((values[1]['enabled'], values[1]['override']), (False, 'off'))
        self.assertEqual((values[-1]['on'], values[-1]['off']), ('10:00', '15:00'))
        self.assertEqual(values[-1]['reason'], 'disabled')
        self.assertFalse(values[-1]['power'])

    def test_equal_invalid_or_stale_settings_never_publish(self):
        current = revision(settings())
        bad = [f'schedule set {current} 24:00 06:00 on',
               f'schedule set {current} 5:00 06:00 on',
               f'schedule set {current} 05:60 06:00 on',
               f'schedule set {current} 05:00 05:00 on',
               f'schedule set {current} 05:00 06:00 yes',
               'schedule extra', 'schedule resume', f'schedule resume {current} extra']
        commands = [(0, line) for line in bad]
        commands += [(0, 'schedule set 00000000 09:00 17:00 on'),
                     (0, 'schedule resume 00000000'), (0, 'schedule')]
        result, kept = support.start_and_keep(source(), [support.line(t, line) for t, line in commands])
        values = replies(result)
        self.assertEqual(values[:len(bad)], [dict(ok=False, error='bad-argument')] * len(bad))
        self.assertEqual(values[len(bad):-1], [dict(ok=False, error='stale')] * 2)
        self.assertEqual(values[-1]['revision'], current)
        self.assertNotIn('schedule.txt', kept)

    def test_corrupt_settings_disable_scheduling_without_blocking_manual_off(self):
        for damaged in (b'', b'odrig-schedule 2\n1 1080 360 0\n',
                        b'odrig-schedule 1\n1 1080 360 0',
                        b'odrig-schedule 1\n1 1080 1080 0\n',
                        b'odrig-schedule 1\n1 1080 360 0\nextra\n'):
            with self.subTest(damaged=damaged):
                values = replies(run([(0, clock(DAY + 12 * 3600)), (0, 'schedule'),
                                      (0, 'off'), (0, 'status')], source(damaged)))
                self.assertFalse(values[1]['active'])
                self.assertEqual(values[1]['error'], 'settings-unreadable')
                self.assertEqual(values[2], dict(ok=False, error='storage-error'))
                self.assertFalse(values[3]['on'])

    def test_unchanged_edits_and_resume_write_nothing(self):
        current = revision(settings())
        result = run([(0, f'schedule set {current} 18:00 06:00 on'),
                      (0, f'schedule resume {current}'), (0, clock(DAY)),
                      (1000, 'schedule'), (2000, 'schedule')], options=['--trace-store'])
        self.assertEqual(replies(result)[:3], [dict(ok=True)] * 3)
        self.assertFalse(any(line.startswith('store ') for line in result.lines))

    def test_read_only_hosts_keep_working_manual_controls(self):
        values = replies(run([(0, 'off'), (0, 'status'), (0, 'on'), (0, 'status')],
                              options=['--no-storage']))
        self.assertEqual((values[0], values[2]), (dict(ok=True), dict(ok=True)))
        self.assertEqual((values[1]['on'], values[3]['on']), (False, True))

    def test_failed_manual_save_does_not_undo_the_requested_led_state(self):
        before = settings(mode=1)
        script = [support.line(0, 'off'), support.line(0, 'schedule')]
        baseline, _ = support.start_and_keep(source(before), script, ['--trace-store'])
        first = len(baseline.stored) + 1
        calls = sum(line.startswith('store ') for line in baseline.lines)
        self.assertGreaterEqual(calls, 4)
        for at in range(first, first + calls):
            with self.subTest(at=at):
                result, kept = support.start_and_keep(source(before), script,
                                                      ['--store-fails-at', str(at)])
                values = replies(result)
                self.assertEqual(values[0], dict(ok=False, error='storage-error'))
                self.assertEqual((values[1]['override'], values[1]['power']), ('off', False))
                self.assertFalse(values[1]['saved'])
                self.assertEqual(kept['schedule.txt'], before)

    def test_failed_pair_save_retains_both_published_settings_and_runtime_settings(self):
        before = settings()
        line = f'schedule set {revision(before)} 09:00 17:00 on'
        script = [support.line(0, line), support.line(0, 'schedule')]
        baseline, _ = support.start_and_keep(source(before), script, ['--trace-store'])
        first = len(baseline.stored) + 1
        calls = sum(line.startswith('store ') for line in baseline.lines)
        for at in range(first, first + calls):
            with self.subTest(at=at):
                result, kept = support.start_and_keep(source(before), script, ['--store-fails-at', str(at)])
                values = replies(result)
                self.assertEqual(values[0], dict(ok=False, error='storage-error'))
                self.assertEqual((values[1]['on'], values[1]['off']), ('18:00', '06:00'))
                self.assertEqual(kept['schedule.txt'], before)

    def test_dst_skipped_and_repeated_hours_evaluate_the_resulting_local_window(self):
        transition = DAY + 2 * 3600
        zone = snapshot('Test/DST', (0, 3600), ((transition, 1), (transition + 3600, 0)))
        data = settings(on=150, off=240)
        values = replies(run([(0, clock(transition - 1, zone)), (0, 'schedule'),
                              (1000, 'schedule'), (3601000, 'schedule'),
                              (7201000, 'schedule')], source(data, zone)))
        self.assertEqual([value['power'] for value in values[1:]], [False, True, True, False])

    def test_each_pair_save_cut_retains_a_complete_old_or_new_file(self):
        before, after = settings(), settings(on=600, off=900)
        line = f'schedule set {revision(before)} 10:00 15:00 on'
        script = [support.line(0, line)]
        baseline, _ = support.start_and_keep(source(before), script, ['--trace-store'])
        first = len(baseline.stored) + 1
        calls = sum(line.startswith('store ') for line in baseline.lines)
        for at in range(first, first + calls):
            for keeps in (0, 1):
                with self.subTest(at=at, keeps=keeps):
                    _, left = support.start_and_keep(source(before), script,
                        ['--cut-at', str(at), '--cut-keeps', str(keeps)], status=75)
                    self.assertIn(left['schedule.txt'], (before, after))
                    state = replies(run([(0, 'schedule')], left))[0]
                    self.assertEqual(state['revision'], revision(left['schedule.txt']))

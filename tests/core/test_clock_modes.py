import json
import unittest

from . import support
from .test_drive import a_drive, asked, replies
from .test_clocks import SHOW4, CARD, CLOCK_FILES, clocks_file, on_card, at_times, states_of


def mode_file(mode, message=False):
    return f"odrig-clocks 2\nmode {mode}\nmessage {'on' if message else 'off'}\n"


def distinct(files):
    return [name for i, name in enumerate(files) if i == 0 or name != files[i - 1]]


class ClockModes(unittest.TestCase):
    def test_only_is_durable_and_immediately_enters_the_resolved_clock_folder(self):
        with a_drive(CARD) as top:
            run, kept = support.start_and_keep(SHOW4, asked(0, 'clocks only') + asked(20, 'status'), ['--drive', top])
        self.assertEqual(replies(run)[0], dict(ok=True))
        status = replies(run)[1]
        self.assertEqual(status['clock_mode'], 'only')
        self.assertTrue(status['clocks'])
        self.assertEqual(status['clock_only'], dict(folder=60007, state='playing'))
        self.assertTrue(status['file'].startswith('clocks/'))
        self.assertEqual(kept['clocks.txt'], b'odrig-clocks 2\nmode only\nmessage off\n')
        self.assertEqual(kept['show.json'], SHOW4['show.json'].encode())

    def test_only_without_a_card_stays_dark_and_reports_why(self):
        run = support.start(SHOW4, asked(0, 'clocks only') + asked(20, 'status'))
        self.assertEqual(replies(run)[0], dict(ok=True))
        status = replies(run)[1]
        self.assertEqual(status['clock_mode'], 'only')
        self.assertEqual(status['clock_only'], dict(folder=None, state='no-card'))
        self.assertIsNone(status['animation'])

    def test_old_settings_map_to_the_explicit_mode_without_losing_the_message_flag(self):
        for clocks, expected in [('off', 'off'), ('on', 'between')]:
            with self.subTest(clocks=clocks):
                run = support.start({**SHOW4, 'clocks.txt': clocks_file(clocks, 'on')}, asked(0, 'status'))
                status = replies(run)[0]
                self.assertEqual(status['clock_mode'], expected)
                self.assertTrue(status['clock_message'])
                self.assertIsNone(status['clock_only'])

    def test_message_changes_keep_only_and_noop_modes_write_nothing(self):
        source = {**SHOW4, 'clocks.txt': mode_file('only')}
        with a_drive(CARD) as top:
            noop = support.start(source, asked(0, 'clocks only'), ['--drive', top, '--trace-store'])
            self.assertFalse(any(line.startswith('store ') for line in noop.lines))
            run, kept = support.start_and_keep(source, asked(0, 'clocks message on') + asked(20, 'status'), ['--drive', top])
        self.assertEqual(replies(run)[-1]['clock_mode'], 'only')
        self.assertTrue(replies(run)[-1]['clock_message'])
        self.assertEqual(kept['clocks.txt'], mode_file('only', True).encode())

    def test_invalid_settings_are_off_with_a_diagnostic(self):
        for data in ('odrig-clocks 2\nmode on\nmessage off\n', mode_file('only') + 'extra\n',
                     'odrig-clocks 1\nclocks only\nmessage off\n', 'odrig-clocks 2\nmode only\n'):
            with self.subTest(data=data):
                run = support.start({**SHOW4, 'clocks.txt': data}, asked(0, 'status'))
                self.assertEqual(replies(run)[-1]['clock_mode'], 'off')
                self.assertIn('clocks unreadable', run.logs)

    def test_failed_saves_and_readback_never_publish_a_mode_change(self):
        source = {**SHOW4, 'clocks.txt': mode_file('between', True)}
        script = asked(0, 'clocks only', 'status')
        observed = support.start(source, script, ['--trace-store'])
        first = len(observed.stored) + 1
        calls = sum(line.startswith('store ') for line in observed.lines)
        for at in range(first, first + calls):
            with self.subTest(at=at):
                run, kept = support.start_and_keep(source, script, ['--store-fails-at', str(at)])
                self.assertEqual(replies(run)[0], dict(ok=False, error='storage-error'))
                self.assertEqual(replies(run)[1]['clock_mode'], 'between')
                self.assertEqual(kept['clocks.txt'], source['clocks.txt'].encode())
        run, kept = support.start_and_keep(source, script, ['--command-read-fails', 'clocks.part', '0'])
        self.assertEqual(replies(run)[0], dict(ok=False, error='storage-error'))
        self.assertEqual(replies(run)[1]['clock_mode'], 'between')
        self.assertEqual(kept['clocks.txt'], source['clocks.txt'].encode())

    def test_each_storage_cut_preserves_old_or_new_complete_migrated_settings(self):
        source = {**SHOW4, 'clocks.txt': clocks_file('on', 'on')}
        old, new = source['clocks.txt'], mode_file('only', True).encode()
        script = asked(0, 'clocks only')
        observed = support.start(source, script, ['--trace-store'])
        first = len(observed.stored) + 1
        calls = sum(line.startswith('store ') for line in observed.lines)
        self.assertEqual(calls, 4)
        for at in range(first, first + calls):
            for keeps in (0, 1):
                with self.subTest(at=at, keeps=keeps):
                    _, left = support.start_and_keep(source, script, ['--cut-at', str(at), '--cut-keeps', str(keeps)], status=75)
                    run, kept = support.start_and_keep(left, asked(0, 'status'))
                    self.assertIn(kept['clocks.txt'], (old, new))
                    self.assertEqual(replies(run)[0]['clock_mode'], 'only' if kept['clocks.txt'] == new else 'between')
                    self.assertTrue(replies(run)[0]['clock_message'])
                    self.assertNotIn('clocks.part', kept)


class OnlyBoundary(unittest.TestCase):
    def test_outside_files_cycles_and_diagnostics_are_refused_without_changing_playback(self):
        show = json.loads(SHOW4['show.json'])
        show['items'].append({'id': 9, 'cycle': [1], 'seconds': 3})
        source = {**SHOW4, 'show.json': json.dumps(show), 'clocks.txt': mode_file('only')}
        commands = ['play 1', 'play 9', 'play 60001', 'play 60002', 'play all', 'mapping test on', 'mapping test snake 1']
        run = on_card(source, CARD, asked(20, 'status', *commands, 'status'))
        answers = replies(run)
        self.assertEqual(answers[1:-1], [dict(ok=False, error='in-use')] * len(commands))
        self.assertEqual(answers[0]['animation'], answers[-1]['animation'])
        self.assertEqual(answers[-1]['clock_mode'], 'only')

    def test_inside_restart_and_refused_global_play_preserve_the_saved_normal_playlist(self):
        source = {**SHOW4, 'playlist.txt': 'odrig-playlist 1\nnight\n1234\n'}
        card = {**CARD, 'night/comet.odrg': CARD['a.odrg']}
        script = asked(0, 'status', 'clocks only') + asked(20, 'status', 'play all', 'play 60008')
        script += asked(40, 'status') + asked(4000000, 'status', 'clocks off') + asked(4000020, 'status')
        with a_drive(card) as top:
            run, kept = support.start_and_keep(source, script, ['--drive', top])
        states = states_of(run)
        self.assertEqual([reply for reply in replies(run) if 'on' not in reply],
                         [dict(ok=True), dict(ok=False, error='in-use'), dict(ok=True), dict(ok=True)])
        self.assertEqual(states[0]['playlist'], 'night')
        self.assertEqual([state['playlist'] for state in states[1:-1]], ['clocks'] * 3)
        self.assertEqual(states[-1]['playlist'], 'night')
        self.assertEqual(states[-1]['file'], 'night/comet.odrg')
        self.assertLessEqual(abs(states[-1]['left'] - states[0]['left']), 1)
        self.assertEqual(kept['playlist.txt'].splitlines()[1], b'night')

    def test_leaving_only_resolves_a_missing_normal_folder_to_root(self):
        source = {**SHOW4, 'playlist.txt': 'odrig-playlist 1\nnight\n1234\n'}
        original = {**CARD, 'night/comet.odrg': CARD['a.odrg']}
        with a_drive(original) as first, a_drive(CARD) as second:
            script = asked(0, 'clocks only') + at_times(20)
            script += ['drive pull', 'drive plug ' + second]
            script += [f'poll {1100 + n * 20}' for n in range(1, 60)]
            script += asked(2400, 'clocks off') + at_times(2420)
            run, kept = support.start_and_keep(source, [f'poll 1000'] + script, ['--drive', first])
        state = states_of(run)[-1]
        self.assertEqual(state['clock_mode'], 'off')
        self.assertIsNone(state['playlist'])
        self.assertEqual(state['file'], 'four.odrg')
        self.assertEqual(kept['playlist.txt'].splitlines()[1], b'')

    def test_ignored_messages_still_allow_explicit_inside_play_with_messages_off(self):
        source = {**SHOW4, 'clocks.txt': mode_file('only'), 'ignored.txt': 'odrig-ignored 1\nd clocks/message\n'}
        run = on_card(source, CARD, asked(20, 'play 60008') + asked(40, 'status', 'play 60006') + asked(60, 'status'))
        self.assertEqual([reply for reply in replies(run) if 'animation' not in reply], [dict(ok=True), dict(ok=True)])
        self.assertEqual([state['file'] for state in states_of(run)], ['clocks/message/m.odrg'] * 2)

    def test_only_keeps_the_normal_path_across_a_temporary_card_without_that_folder(self):
        source = {**SHOW4, 'playlist.txt': 'odrig-playlist 1\nnight\n1234\n'}
        original = {**CARD, 'night/comet.odrg': CARD['a.odrg']}
        returned = {**original, 'aaa.odrg': CARD['b.odrg']}
        with a_drive(original) as first, a_drive(CARD) as middle, a_drive(returned) as last:
            script = asked(0, 'clocks only') + at_times(20)
            for time, card in ((100, middle), (2000, last)):
                script += ['drive pull', 'drive plug ' + card]
                script += [f'poll {1000 + time + n * 20}' for n in range(1, 60)]
                script += at_times(time + 1200)
            script += asked(3400, 'clocks off') + at_times(3420)
            run, kept = support.start_and_keep(source, [f'poll 1000'] + script, ['--drive', first])
        states = states_of(run)
        self.assertEqual([state['clock_mode'] for state in states[:-1]], ['only'] * 3)
        self.assertEqual(states[-1]['playlist'], 'night')
        self.assertEqual(states[-1]['file'], 'night/comet.odrg')
        self.assertEqual(kept['playlist.txt'].splitlines()[1], b'night')

    def test_missing_branch_and_missing_faces_never_fall_back_outside(self):
        for card, state in [({'a.odrg': CARD['a.odrg']}, 'missing-folder'),
                            ({'clocks/message/m.odrg': CARD['clocks/message/m.odrg']}, 'no-clocks')]:
            with self.subTest(state=state):
                run = on_card({**SHOW4, 'clocks.txt': mode_file('only', True)}, card, at_times(20, 1000, 10000000))
                self.assertEqual([status['clock_only']['state'] for status in states_of(run)], [state] * 3)
                self.assertTrue(all(status['animation'] is None for status in states_of(run)))

    def test_exclusions_black_out_and_reinclusion_restarts_without_leaving_only(self):
        source = {**SHOW4, 'clocks.txt': mode_file('only', True)}
        run = on_card(source, CARD, asked(20, 'ignore 60007 1') + asked(40, 'status', 'ignore 60007 0') + asked(60, 'status'))
        first, second = states_of(run)
        self.assertEqual(first['clock_only']['state'], 'no-clocks')
        self.assertIsNone(first['animation'])
        self.assertEqual(second['clock_only']['state'], 'playing')
        self.assertIn(second['file'], CLOCK_FILES)

    def test_remount_resolves_exclusive_branch_again_and_does_not_restore_outside(self):
        source = {**SHOW4, 'clocks.txt': mode_file('only')}
        script = at_times(20) + ['drive pull'] + at_times(40) + ['drive plug']
        script += [f'poll {1040 + n * 20}' for n in range(1, 50)] + at_times(1100)
        run = on_card(source, CARD, script)
        states = states_of(run)
        self.assertEqual(states[1]['clock_only']['state'], 'no-card')
        self.assertIsNone(states[1]['animation'])
        self.assertTrue(all(state['file'] in CLOCK_FILES for state in (states[0], states[2])))

    def test_all_excluded_faces_are_physically_dark_on_start(self):
        from .test_brightness import last_rgb
        source = {**SHOW4, 'clocks.txt': mode_file('only', True), 'ignored.txt': 'odrig-ignored 1\nd clocks\n'}
        run = on_card(source, CARD, at_times(20, 1000))
        self.assertEqual(states_of(run)[-1]['clock_only']['state'], 'no-clocks')
        self.assertFalse(any(last_rgb(run)))

    def test_excluding_the_current_message_skips_it_at_the_next_refresh(self):
        source = {**SHOW4, 'clocks.txt': mode_file('only', True)}
        run = on_card(source, CARD, at_times(100, 6100) + asked(6120, 'ignore 60008 1') + at_times(6140))
        states = states_of(run)
        self.assertEqual(states[-2]['file'], 'clocks/message/m.odrg')
        self.assertIn(states[-1]['file'], CLOCK_FILES)

    def test_entering_only_ends_the_active_diagonal_without_restoring_it_later(self):
        from .test_mini import files_for
        from .test_clocks import clock_of
        source = files_for()
        card = {'clocks/c.odrgx': clock_of(canvas=(60, 60))}
        run = on_card(source, card, asked(0, 'mapping test on', 'clocks only') + asked(20, 'status', 'mapping test off') + at_times(40))
        self.assertEqual([reply for reply in replies(run) if 'on' not in reply], [dict(ok=True)] * 3)
        self.assertEqual([state['file'] for state in states_of(run)], ['clocks/c.odrgx'] * 2)

    def test_quarantined_faces_stay_dark_and_a_new_media_generation_recovers(self):
        source = {**SHOW4, 'clocks.txt': mode_file('only')}
        bad = {'a.odrg': CARD['a.odrg'], 'clocks/c.odrg': b'bad'}
        good = {'a.odrg': CARD['a.odrg'], 'b.odrg': CARD['b.odrg'], 'clocks/c.odrg': CARD['a.odrg']}
        with a_drive(bad) as first, a_drive(good) as second:
            script = at_times(20) + ['drive pull', 'drive plug ' + second]
            script += [f'poll {1040 + n * 20}' for n in range(1, 50)] + at_times(1100)
            run = support.start(source, [f'poll 1000'] + script, ['--drive', first])
        states = states_of(run)
        self.assertEqual(states[0]['clock_only']['state'], 'no-clocks')
        self.assertIsNone(states[0]['animation'])
        self.assertEqual(states[1]['file'], 'clocks/c.odrg')
        self.assertNotEqual(states[0]['clock_only']['folder'], states[1]['clock_only']['folder'])

    def test_a_runtime_fault_in_the_last_cataloged_face_stays_dark_inside_only(self):
        from .test_catalog_drive import card, polls
        from .test_drive import logged
        from .test_brightness import last_rgb
        source = {**SHOW4, 'clocks.txt': mode_file('only', True)}
        files = card({'clocks/c.odrg': CARD['clocks/c1.odrg'],
                      'clocks/message/m.odrg': CARD['clocks/message/m.odrg'], 'a.odrg': CARD['a.odrg']})
        files['clocks/c.odrg'] = files['clocks/c.odrg'][:-3]
        with a_drive(files) as top:
            run = support.start(source, polls(0, 400) + at_times(8100), ['--drive', top], check_first=False)
        self.assertEqual(states_of(run)[0]['clock_only']['state'], 'no-clocks')
        self.assertIsNone(states_of(run)[0]['animation'])
        self.assertFalse(any(last_rgb(run)))
        self.assertTrue(any('left out' in line for line in logged(run)))

    def test_content_cleanup_cannot_restore_an_internal_fallback_in_only(self):
        source = {**SHOW4, 'clocks.txt': mode_file('only')}
        run = on_card(source, CARD, at_times(20) + asked(40, 'remove 1') + at_times(60))
        self.assertEqual([reply for reply in replies(run) if 'on' not in reply], [dict(ok=True)])
        self.assertTrue(all(state['file'] in CLOCK_FILES for state in states_of(run)))


class MessageBags(unittest.TestCase):
    def test_each_delivered_message_finishes_its_complete_loop_in_both_modes(self):
        from odrig import messageclock
        from .test_mini import files_for
        from .test_clocks import clock_of
        folder = support.ROOT / 'collection/card/clocks/message'
        paths = sorted(folder.glob('v7-*.odrgx'))
        self.assertEqual(len(paths), 7)
        for path in paths:
            data = path.read_bytes()
            loop = messageclock.decode(data)['loopMs']
            for mode, begin, after in (('only', 2000, 'clocks/c.odrgx'), ('between', 7000, 'picture.odrg')):
                with self.subTest(file=path.name, mode=mode):
                    source = files_for()
                    show = json.loads(source['show.json']); show['min_seconds'] = 1
                    source.update({'show.json': json.dumps(show), 'clocks.txt': mode_file(mode, True)})
                    card = {'clocks/c.odrgx': clock_of(canvas=(60, 60)),
                            'clocks/message/' + path.name: data}
                    run = on_card(source, card, at_times(begin + 700, begin + loop - 100, begin + loop + 100))
                    self.assertEqual([state['file'] for state in states_of(run)],
                                     ['clocks/message/' + path.name] * 2 + [after])

    def test_both_modes_exhaust_independent_clock_and_message_bags(self):
        card = {**CARD, 'clocks/message/n.odrg': CARD['clocks/message/m.odrg'],
                'clocks/message/o.odrg': CARD['clocks/message/m.odrg'],
                'clocks/nested/other.odrg': CARD['a.odrg'], 'clocks/message/deep/other.odrg': CARD['a.odrg']}
        messages = {name for name in card if name.rsplit('/', 1)[0] == 'clocks/message'}
        for mode in ('only', 'between'):
            with self.subTest(mode=mode):
                source = {**SHOW4, 'clocks.txt': mode_file(mode, True)}
                run = on_card(source, card, at_times(*range(100, 300100, 500)))
                files = distinct([state['file'] for state in states_of(run)])
                faces = [name for name in files if name in CLOCK_FILES]
                words = [name for name in files if name in messages]
                self.assertNotIn('clocks/nested/other.odrg', files)
                self.assertNotIn('clocks/message/deep/other.odrg', files)
                self.assertGreaterEqual(len(faces), 6)
                self.assertGreaterEqual(len(words), 6)
                for values, expected in ((faces, CLOCK_FILES), (words, messages)):
                    for i in range(0, len(values) - 2, 3): self.assertEqual(set(values[i:i + 3]), expected)

    def test_a_procedural_message_longer_than_thirty_seconds_finishes_its_whole_loop(self):
        from .test_mini import files_for
        from .test_clocks import clock_of
        from .test_message_clock import message_file
        source = files_for()
        show = json.loads(source['show.json']); show['min_seconds'] = 1
        source.update({'show.json': json.dumps(show), 'clocks.txt': mode_file('only', True)})
        card = {'clocks/c.odrgx': clock_of(canvas=(60, 60)),
                'clocks/message/long.odrgx': message_file([('words', 0)] * 9)}
        run = on_card(source, card, at_times(100, 2100, 32000, 56800, 57000))
        self.assertEqual([state['file'] for state in states_of(run)], ['clocks/c.odrgx',
                         'clocks/message/long.odrgx', 'clocks/message/long.odrgx', 'clocks/message/long.odrgx', 'clocks/c.odrgx'])

    def test_between_animations_also_finishes_a_long_message_loop(self):
        from .test_mini import files_for
        from .test_clocks import clock_of
        from .test_message_clock import message_file
        source = files_for()
        show = json.loads(source['show.json']); show['min_seconds'] = 1
        source.update({'show.json': json.dumps(show), 'clocks.txt': mode_file('between', True)})
        card = {'clocks/c.odrgx': clock_of(canvas=(60, 60)),
                'clocks/message/long.odrgx': message_file([('words', 0)] * 9)}
        run = on_card(source, card, at_times(100, 5100, 7100, 40000, 61800, 62100))
        self.assertEqual([state['file'] for state in states_of(run)], ['picture.odrg', 'clocks/c.odrgx',
                         'clocks/message/long.odrgx', 'clocks/message/long.odrgx', 'clocks/message/long.odrgx', 'picture.odrg'])


class StatusRoom(unittest.TestCase):
    def test_long_supported_paths_and_escaped_host_keep_a_complete_bounded_status(self):
        directory = '/'.join(['x' * 30] * 3)
        name = directory + '/d.odrg'
        with a_drive({name: CARD['a.odrg']}) as top:
            run = support.start(SHOW4, asked(0, 'play 60004') + asked(20, 'status'),
                                ['--drive', top, '--about', '\x01' * 95])
        status = replies(run)[-1]
        self.assertEqual(status['animation'], 60001)
        self.assertEqual(status['file'], name)
        self.assertEqual(status['playlist'], directory)
        self.assertIn('left', status)
        for line in run.lines:
            if line.startswith('reply '): self.assertLessEqual(len(line[6:]) + 1, 1024)

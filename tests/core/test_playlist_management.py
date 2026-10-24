import json
import unittest
from . import support
from .test_content import small_show, replies

def listed(run):
    return [json.loads(value) for value in replies(run.lines)]

class PlaylistManagement(unittest.TestCase):

    def files(self, **extra):
        items = [{'id': n, 'file': f'a{n}.odrg', 'repeat': 1} for n in range(1, 4)]
        return small_show(items, **extra)

    def test_ignore_is_durable_idempotent_and_resumes_from_idle(self):
        files = self.files()
        script = [support.line(1000, x) for x in ('ignore 1 1', 'ignore 2 1', 'ignore 3 1', 'status', 'list', 'play all', 'ignore 2 0', 'status', 'ignore 2 0')]
        run, left = support.start_and_keep(files, script, ['--trace-store'])
        values = listed(run)
        self.assertEqual(values[:3], [{'ok': True}] * 3)
        self.assertIsNone(values[3]['playing'])
        self.assertEqual([x['ignored'] for x in values[4]['items']], [True] * 3)
        self.assertEqual(values[5], {'ok': False, 'error': 'unknown-id'})
        self.assertEqual(values[7]['animation'], 2)
        written = json.loads(left['show.json'])['items']
        self.assertEqual([x['ignored'] for x in written], [True, False, True])
        self.assertEqual(listed(support.start(left, [support.line(0, 'status')]))[0]['animation'], 2)
        self.assertEqual(sum((line.startswith('store rename show.part show.json 1') for line in run.lines)), 4)

    def test_ignored_manual_turn_does_not_repeat_and_cycles_keep_it(self):
        files = self.files()
        show = json.loads(files['show.json'])
        show['items'][0]['ignored'] = True
        files['show.json'] = json.dumps(show)
        run = support.start(files, [support.line(0, 'play 1'), 'poll 0', 'poll 1000', support.line(1000, 'status')])
        self.assertNotEqual(listed(run)[-1]['animation'], 1)
        show['items'].append({'id': 9, 'cycle': [1], 'seconds': 1})
        show['start'] = 9
        files['show.json'] = json.dumps(show)
        self.assertEqual(listed(support.start(files, ['poll 0', 'poll 1000', support.line(1000, 'status')]))[0]['animation'], 1)

    def test_bulk_is_one_commit_and_retains_shared_file(self):
        files = self.files()
        show = json.loads(files['show.json'])
        show['items'][2]['file'] = 'a1.odrg'
        files['show.json'] = json.dumps(show)
        run, left = support.start_and_keep(files, [support.line(0, 'remove many 1,2'), support.line(0, 'list'), support.line(0, 'status')], ['--trace-store'])
        values = listed(run)
        self.assertEqual(values[0], {'ok': True})
        self.assertEqual([i['id'] for i in values[1]['items']], [3])
        self.assertEqual(values[2]['animation'], 3)
        self.assertIn('a1.odrg', left)
        self.assertNotIn('a2.odrg', left)
        self.assertEqual(sum((line.startswith('store rename show.part show.json 1') for line in run.lines)), 1)

    def test_invalid_batch_does_not_remove_anything(self):
        for command, reason in [('remove many 1,999', 'unknown-id'), ('remove many 1,1', 'bad-argument'), ('remove many 1,', 'bad-argument'), ('remove many 0,1', 'bad-argument'), ('remove many ' + ','.join(map(str, range(1, 34))), 'bad-argument')]:
            with self.subTest(command=command):
                files = self.files()
                run, left = support.start_and_keep(files, [support.line(0, command)])
                self.assertEqual(listed(run), [{'ok': False, 'error': reason}])
                self.assertEqual(left, {k: v.encode() if isinstance(v, str) else v for k, v in files.items()})

    def test_in_use_batch_and_diagonal_busy(self):
        files = self.files()
        show = json.loads(files['show.json'])
        show['items'].append({'id': 9, 'cycle': [2], 'seconds': 1})
        files['show.json'] = json.dumps(show)
        for command in ['remove many 1,2', 'remove many 1,9', 'ignore 9 1']:
            self.assertEqual(listed(support.start(files, [support.line(0, command)]))[0], {'ok': False, 'error': 'in-use'})

    def test_ignore_failure_preserves_show_and_playback(self):
        files = self.files()
        run, left = support.start_and_keep(files, [support.line(0, 'ignore 1 1'), support.line(0, 'status')], ['--store-fails-at', '6'])
        self.assertEqual(listed(run)[0], {'ok': False, 'error': 'storage-error'})
        self.assertEqual(json.loads(left['show.json']), json.loads(files['show.json']))
        self.assertEqual(listed(run)[1]['animation'], 1)

    def test_bulk_and_ignore_survive_every_storage_cut(self):
        from .test_powercut import PowerCut, storage_calls, as_bytes
        helper = PowerCut()
        for command in ('ignore 1 1', 'remove many 1,2,3'):
            files = self.files()
            script = [support.line(0, command)]
            _, new = support.start_and_keep(files, script)
            calls = storage_calls(files, script)
            for at, keeps in helper.cuts_of(calls):
                with self.subTest(command=command, at=at, keeps=keeps):
                    _, again, after = helper.cut(files, script, at, keeps)
                    self.assertIsNone(again.error)
                    self.assertIn(after, (as_bytes(files), new))

    def test_large_cleanup_journal_and_cleanup_debt_are_safe(self):
        items = [{'id': n, 'file': f'{n:02d}' + 'x' * 25 + '.odrg'} for n in range(1, 33)]
        files = small_show(items)
        command = 'remove many ' + ','.join((str(n) for n in range(1, 33)))
        from .test_powercut import storage_calls
        calls = storage_calls(files, [support.line(0, command)])
        self.assertTrue(any((x.startswith('write 1056') for x in calls)))
        fail = next((n for n, x in enumerate(calls, 1) if x.startswith('remove 01')))
        run, left = support.start_and_keep(files, [support.line(0, command), support.line(0, 'ignore 999 0')], ['--store-fails-at', str(fail)])
        self.assertEqual(listed(run)[0], {'ok': True})
        self.assertIn('pending.txt', left)
        _, clean = support.start_and_keep(left, [])
        self.assertEqual(set(clean), {'mapping.json', 'show.json'})

    def test_all_ignored_manual_turn_ends_black_even_after_a_long_gap(self):
        files = self.files()
        show = json.loads(files['show.json'])
        for item in show['items']:
            item['ignored'] = True
        files['show.json'] = json.dumps(show)
        script = [support.line(0, 'status'), support.line(0, 'off'), support.line(0, 'play 1'), 'poll 0', support.line(0, 'status'), 'poll 100000000', support.line(100000000, 'status'), support.line(100000000, 'ignore 3 0'), support.line(100000000, 'status')]
        values = listed(support.start(files, script))
        self.assertIsNone(values[0]['playing'])
        self.assertEqual(values[3]['animation'], 1)
        self.assertIsNone(values[4]['animation'])
        self.assertFalse(values[4]['on'])
        self.assertEqual(values[6]['animation'], 3)
        self.assertFalse(values[6]['on'])

    def test_start_and_long_rounds_skip_ignored_items(self):
        files = self.files(start=1)
        show = json.loads(files['show.json'])
        show['items'][0]['ignored'] = True
        files['show.json'] = json.dumps(show)
        values = listed(support.start(files, [support.line(0, 'status'), 'poll 0', 'poll 100000000', support.line(100000000, 'status')]))
        self.assertEqual(values[0]['animation'], 2)
        self.assertIn(values[1]['animation'], [2, 3])

    def test_toggle_other_item_preserves_active_turn_and_noop_does_not_write(self):
        files = self.files()
        script = ['poll 0', 'poll 20', support.line(21, 'ignore 2 1'), support.line(22, 'ignore 2 1'), support.line(23, 'status')]
        run = support.start(files, script, ['--trace-store'])
        values = listed(run)
        self.assertEqual(values[:2], [{'ok': True}] * 2)
        self.assertEqual(values[-1]['animation'], 1)
        self.assertEqual(sum((line.startswith('store rename show.part show.json 1') for line in run.lines)), 1)

    def test_core_boolean_validation_matches_the_tools(self):
        for value in [0, 1, 'true', None, [], {}]:
            files = self.files()
            show = json.loads(files['show.json'])
            show['items'][0]['ignored'] = value
            files['show.json'] = json.dumps(show)
            with self.subTest(value=value):
                self.assertEqual(support.start(files).error, 'show-malformed')

    def test_replacement_keeps_inclusion_and_removed_id_defaults_included(self):
        from .test_upload import Script
        files = self.files()
        show = json.loads(files['show.json'])
        show['items'][0]['ignored'] = True
        files['show.json'] = json.dumps(show)
        clip = files['a2.odrg']
        script = Script(0).upload(1, 'a1.odrg', clip).lines
        run, left = support.start_and_keep(files, script)
        self.assertTrue(json.loads(left['show.json'])['items'][0]['ignored'])
        script = Script(0).line('remove 1').upload(1, 'restored.odrg', clip).line('list').lines
        run, left = support.start_and_keep(left, script)
        self.assertEqual(listed(run)[-1]['items'][-1]['ignored'], False)
        self.assertNotIn('ignored', json.loads(left['show.json'])['items'][-1])

    def test_commands_through_byte_entry_and_during_the_startup_check(self):
        files = self.files()
        run = support.start(files, [support.fed(0, b'ignore 1 1\nremove many 2,3\n'), support.line(0, 'list')])
        self.assertEqual(listed(run)[:2], [{'ok': True}] * 2)
        self.assertEqual([i['id'] for i in listed(run)[-1]['items']], [1])
        run = support.start(files, [support.line(0, 'ignore 1 1'), support.line(0, 'remove many 1,2')], check_first=False)
        self.assertEqual(listed(run), [{'ok': True}] * 2)

    def test_bulk_failure_before_metadata_commit_retains_old_show(self):
        from .test_powercut import storage_calls, as_bytes
        files = self.files()
        script = [support.line(0, 'remove many 1,2')]
        calls = storage_calls(files, script)
        commit = calls.index('rename show.part show.json 1') + 1
        for at in range(3, commit + 1):
            with self.subTest(at=at):
                run, left = support.start_and_keep(files, script, ['--store-fails-at', str(at)])
                self.assertEqual(listed(run), [{'ok': False, 'error': 'storage-error'}])
                self.assertEqual(left, as_bytes(files))

    def test_cleanup_debt_cannot_be_overwritten_by_a_later_mutation(self):
        from .test_powercut import storage_calls
        files = self.files()
        script = [support.line(0, 'remove many 1,2')]
        calls = storage_calls(files, script)
        at = next(n for n, line in enumerate(calls, 1) if line.startswith('remove a1.odrg'))
        script += [support.line(0, 'ignore 3 1'), support.line(0, 'remove many 3')]
        run, left = support.start_and_keep(files, script, ['--store-fails-at', str(at)])
        self.assertEqual(listed(run), [{'ok': True}] + [{'ok': False, 'error': 'storage-error'}] * 2)
        self.assertIn(b'a1.odrg\n', left['pending.txt'])

    def test_diagonal_refuses_both_mutations_and_does_not_change_show(self):
        from tests.mapping.test_core import files
        source = files()
        run, left = support.start_and_keep(source, [support.line(0, line) for line in ['mapping test on', 'ignore 1 1', 'remove many 1,2', 'mapping get']])
        values = listed(run)
        self.assertEqual(values[0], {'ok': True})
        self.assertEqual(values[1:3], [{'ok': False, 'error': 'busy'}] * 2)
        self.assertTrue(values[3]['test'])
        self.assertEqual(left, source)

    def test_bulk_cleanup_preserves_a_drive_animation_being_checked(self):
        from .test_drive import a_drive
        drive = {'long.odrg': support.clip(17, 60, 6, (20,) * 80)}
        script = ['drive plug', 'poll 0', 'poll 20', support.line(21, 'remove many 1,2')]
        script += [f'poll {time}' for time in range(40, 4000, 20)]
        script += [support.line(4000, 'list')]
        with a_drive(drive) as top:
            run = support.start(self.files(), script, ['--drive', top, '--drive-pulled'])
        self.assertEqual(listed(run)[0], {'ok': True})
        self.assertEqual([item['id'] for item in listed(run)[1]['items']], [3, 60001])

    def test_mixed_inclusion_flags_paginate_within_reply_limit(self):
        from .test_content import List
        items = [{'id': n, 'file': f'{n:03d}' + 'x' * 24 + '.odrg', 'ignored': n % 2 == 0} for n in range(1, 133)]
        clip = support.clip(1, 60, 6)
        files = small_show(items, files={item['file']: clip for item in items})
        helper = List()
        found, pages = helper.walk(files)
        self.assertEqual([item['ignored'] for item in found], [item['ignored'] for item in items])
        self.assertTrue(all(len(page) + 1 <= 1024 for page in pages))
        self.assertGreater(len(pages), 1)

import json
import pathlib
import unittest

from . import support
from .test_drive import SHOW, DRIVE, a_drive, asked, replies, with_drive
from .test_folders import NESTED, LEVELS


def preferences(*lines):
    return 'odrig-ignored 1\n' + ''.join(line + '\n' for line in lines)


def rows(run):
    return {item.get('file', item.get('playlist')): item
            for reply in replies(run) if 'items' in reply for item in reply['items']}


class ExternalInclusion(unittest.TestCase):
    def test_file_ignore_saves_in_internal_storage_and_survives_id_reassignment(self):
        with a_drive(DRIVE) as top:
            before = support.folder_files(pathlib.Path(top, 'odrig'))
            run, kept = support.start_and_keep(SHOW, asked(0, 'ignore 60001 1', 'list'), ['--drive', top])
            self.assertEqual(replies(run)[0], dict(ok=True))
            self.assertTrue(rows(run)['A.ODRG']['ignored'])
            self.assertFalse(rows(run)['A.ODRG']['inherited_ignored'])
            self.assertEqual(kept['ignored.txt'], preferences('f A.ODRG').encode())
            changed = json.loads(kept['show.json'])
            changed['items'][0]['id'] = 60001
            if changed.get('start') == 1: changed['start'] = 60001
            again = support.start({**kept, 'show.json': json.dumps(changed)}, asked(0, 'list'), ['--drive', top])
            self.assertEqual(rows(again)['A.ODRG']['id'], 60002)
            self.assertTrue(rows(again)['A.ODRG']['ignored'])
            self.assertEqual(support.folder_files(pathlib.Path(top, 'odrig')), before)

    def test_folder_exclusion_is_inherited_without_overwriting_child_choices(self):
        source = {**SHOW, 'ignored.txt': preferences('d night', 'f night/deep/x.odrg')}
        run = with_drive(source, NESTED, asked(0, *LEVELS))
        found = rows(run)
        self.assertTrue(found['night']['ignored'])
        self.assertFalse(found['night']['inherited_ignored'])
        self.assertFalse(found['night/deep']['ignored'])
        self.assertTrue(found['night/deep']['inherited_ignored'])
        self.assertTrue(found['night/deep/x.odrg']['ignored'])
        self.assertTrue(found['night/deep/x.odrg']['inherited_ignored'])
        self.assertFalse(found['a b/c.odrg']['ignored'])
        self.assertFalse(found['a b/c.odrg']['inherited_ignored'])

    def test_ignored_external_file_remains_manually_playable(self):
        run = with_drive({**SHOW, 'ignored.txt': preferences('f A.ODRG')}, DRIVE,
                         asked(0, 'play 60001') + asked(20, 'status'))
        self.assertEqual(replies(run)[0], dict(ok=True))
        self.assertEqual(replies(run)[1]['animation'], 60001)

    def test_retained_absent_paths_fill_capacity_without_eviction(self):
        source = {**SHOW, 'ignored.txt': preferences(*(f'f absent-{n}.odrg' for n in range(128)))}
        with a_drive(DRIVE) as top:
            run, kept = support.start_and_keep(source, asked(0, 'ignore 60001 1'), ['--drive', top])
        self.assertEqual(replies(run)[0], dict(ok=False, error='no-space'))
        self.assertEqual(kept['ignored.txt'], source['ignored.txt'].encode())

    def test_including_a_parent_keeps_a_childs_own_exclusion(self):
        source = {**SHOW, 'ignored.txt': preferences('d night', 'f night/deep/x.odrg')}
        run = with_drive(source, NESTED, asked(0, 'ignore 60008 0', *LEVELS))
        self.assertEqual(replies(run)[0], dict(ok=True))
        found = rows(run)
        self.assertFalse(found['night']['ignored'])
        self.assertFalse(found['night/deep/x.odrg']['inherited_ignored'])
        self.assertTrue(found['night/deep/x.odrg']['ignored'])

    def test_an_excluded_current_automatic_turn_moves_to_an_eligible_file(self):
        run = with_drive(SHOW, DRIVE, asked(0) + asked(4100, 'status', 'ignore 60001 1') + asked(4120, 'status'))
        states = [reply for reply in replies(run) if 'animation' in reply]
        self.assertEqual([state['animation'] for state in states], [60001, 60002])

    def test_an_ignore_change_does_not_interrupt_an_explicit_manual_turn(self):
        run = with_drive(SHOW, DRIVE, asked(0, 'play 60001', 'ignore 60001 1') + asked(20, 'status'))
        self.assertEqual(replies(run)[-1]['animation'], 60001)

    def test_a_newly_checked_drive_file_does_not_start_when_every_file_is_excluded(self):
        show = json.loads(SHOW['show.json'])
        show['items'][0]['ignored'] = True
        source = {**SHOW, 'show.json': json.dumps(show), 'ignored.txt': preferences('f A.ODRG', 'f b.odrg')}
        run = with_drive(source, DRIVE, asked(0, 'status'))
        self.assertIsNone(replies(run)[0]['animation'])

    def test_absent_paths_are_retained_and_noop_choices_write_nothing(self):
        source = {**SHOW, 'ignored.txt': preferences('f absent.odrg', 'f A.ODRG')}
        with a_drive(DRIVE) as top:
            run, kept = support.start_and_keep(source, asked(0, 'ignore 60001 1'), ['--drive', top, '--trace-store'])
        self.assertEqual(replies(run)[0], dict(ok=True))
        self.assertFalse(any(line.startswith('store ') for line in run.lines))
        self.assertEqual(kept['ignored.txt'], source['ignored.txt'].encode())

    def test_removal_at_capacity_keeps_every_other_absent_path(self):
        source = {**SHOW, 'ignored.txt': preferences('f A.ODRG', *(f'f absent-{n}.odrg' for n in range(127)))}
        with a_drive(DRIVE) as top:
            run, kept = support.start_and_keep(source, asked(0, 'ignore 60001 0', 'list'), ['--drive', top])
        self.assertEqual(replies(run)[0], dict(ok=True))
        self.assertFalse(rows(run)['A.ODRG']['ignored'])
        self.assertEqual(kept['ignored.txt'], preferences(*(f'f absent-{n}.odrg' for n in range(127))).encode())

    def test_corrupt_settings_discard_partial_exclusions_and_refuse_mutation(self):
        bad = [preferences('f A.ODRG') + 'unfinished', 'odrig-ignored 2\n', preferences('z A.ODRG'),
               preferences('f A.ODRG', *(f'f absent-{n}.odrg' for n in range(128)))]
        for data in bad:
            with self.subTest(data=data[:50]):
                run = with_drive({**SHOW, 'ignored.txt': data}, DRIVE, asked(0, 'list', 'ignore 60001 1'))
                self.assertFalse(rows(run)['A.ODRG']['ignored'])
                self.assertEqual(replies(run)[-1], dict(ok=False, error='storage-error'))
                self.assertIn('ignored unreadable', run.logs)

    def test_remount_resolves_paths_again(self):
        source = {**SHOW, 'ignored.txt': preferences('f A.ODRG')}
        script = asked(0, 'list') + ['drive pull'] + asked(20, 'list') + ['drive plug']
        script += [f'poll {1040 + 20 * n}' for n in range(1, 40)] + asked(1000, 'list')
        run = with_drive(source, DRIVE, script)
        listed = [reply for reply in replies(run) if 'items' in reply]
        self.assertTrue(listed[0]['items'][-2]['ignored'])
        self.assertEqual(len(listed[1]['items']), 1)
        self.assertTrue(listed[2]['items'][-2]['ignored'])

    def test_cataloged_cards_resolve_folder_and_file_exclusions_across_index_refills(self):
        from .test_catalog_drive import card, polls
        source = {**SHOW, 'ignored.txt': preferences('d night', 'f a b/c.odrg')}
        with a_drive(card(NESTED)) as top:
            run = support.start(source, polls(0, 400) + asked(8100, *LEVELS), ['--drive', top], check_first=False)
        found = rows(run)
        self.assertTrue(found['night/deep/deeper/y.odrg']['inherited_ignored'])
        self.assertTrue(found['a b/c.odrg']['ignored'])
        self.assertFalse(found['A.ODRG']['ignored'])

    def test_clock_and_message_candidates_apply_ancestor_exclusions(self):
        from .test_clocks import SHOW4, CARD, ABreak, with_clocks, on_card, at_times, states_of, MESSAGE
        for line in ('d clocks', 'd clocks/message', 'f clocks/c1.odrg'):
            with self.subTest(line=line):
                source = {**with_clocks(SHOW4), 'ignored.txt': preferences(line)}
                states = states_of(on_card(source, CARD, at_times(*ABreak.TIMES)))
                files = [state['file'] for state in states]
                if line == 'd clocks': self.assertFalse(any(name.startswith('clocks/') for name in files))
                elif line == 'd clocks/message': self.assertNotIn(MESSAGE, files)
                else: self.assertNotIn('clocks/c1.odrg', files)

    def test_excluding_the_active_clock_branch_leaves_its_automatic_break(self):
        from .test_clocks import SHOW4, CARD, with_clocks, on_card, at_times, states_of
        run = on_card(with_clocks(SHOW4), CARD, at_times(1000, 5000, 9000, 13000, 17000, 21000)
                      + asked(21020, 'ignore 60007 1') + at_times(21040))
        states = states_of(run)
        self.assertTrue(states[-2]['file'].startswith('clocks/'))
        self.assertFalse(states[-1]['file'].startswith('clocks/'))


class InclusionFailures(unittest.TestCase):
    def test_failed_storage_calls_and_readback_preserve_published_file_and_cache(self):
        source = {**SHOW, 'ignored.txt': preferences('f A.ODRG', 'f absent.odrg')}
        with a_drive(DRIVE) as top:
            script = asked(0, 'ignore 60001 0', 'list')
            observed = support.start(source, script, ['--drive', top, '--trace-store'])
            first = len(observed.stored) + 1
            calls = sum(line.startswith('store ') for line in observed.lines)
            for at in range(first, first + calls):
                with self.subTest(at=at):
                    run, kept = support.start_and_keep(source, script, ['--drive', top, '--store-fails-at', str(at)])
                    self.assertEqual(replies(run)[0], dict(ok=False, error='storage-error'))
                    self.assertTrue(rows(run)['A.ODRG']['ignored'])
                    self.assertEqual(kept['ignored.txt'], source['ignored.txt'].encode())
                    self.assertNotIn('ignored.part', kept)
            for name, offset in [('ignored.txt', '0'), ('ignored.txt', '20'), ('ignored.part', '0')]:
                run, kept = support.start_and_keep(source, script, ['--drive', top, '--command-read-fails', name, offset])
                self.assertEqual(replies(run)[0], dict(ok=False, error='storage-error'))
                self.assertTrue(rows(run)['A.ODRG']['ignored'])
                self.assertEqual(kept['ignored.txt'], source['ignored.txt'].encode())

    def test_each_storage_cut_recovers_only_old_or_new_complete_preferences(self):
        source = {**SHOW, 'ignored.txt': preferences('f A.ODRG', 'f absent.odrg')}
        old = source['ignored.txt'].encode()
        new = preferences('f absent.odrg').encode()
        with a_drive(DRIVE) as top:
            script = asked(0, 'ignore 60001 0')
            observed, whole = support.start_and_keep(source, script, ['--drive', top, '--trace-store'])
            self.assertEqual(whole['ignored.txt'], new)
            first = len(observed.stored) + 1
            calls = sum(line.startswith('store ') for line in observed.lines)
            self.assertEqual(calls, 4)
            for at in range(first, first + calls):
                for keeps in (0, 1):
                    with self.subTest(at=at, keeps=keeps):
                        _, left = support.start_and_keep(source, script, ['--drive', top, '--cut-at', str(at), '--cut-keeps', str(keeps)], status=75)
                        recovered, settled = support.start_and_keep(left, asked(0, 'list'), ['--drive', top])
                        self.assertIn(settled['ignored.txt'], (old, new))
                        self.assertEqual(rows(recovered)['A.ODRG']['ignored'], settled['ignored.txt'] == old)
                        self.assertNotIn('ignored.part', settled)

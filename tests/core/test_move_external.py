"""`move external <id> <folder>`: a file of the card moved into another of its folders by
renaming, in one commit of its catalog, with its id, last among the folder's own files, and
with the saved settings that name it by its path."""

import pathlib
import unittest
import zlib

from odrig import catalog

from . import support
from .test_catalog_drive import card, drive_ids
from .test_catalog_writes import POWER_CUT, a_card, folder_of
from .test_drive import SHOW, asked, replies
from .test_playback import T0
from .test_playlist import loop_of

FILES = {'root.odrg': loop_of(2, 5), 'night/deep/old.odrg': loop_of(3, 6), 'night/near.odrg': loop_of(3, 7),
         'space room/old.odrg': loop_of(3, 8), 'a/b/c/far.odrg': loop_of(2, 9)}
IDS = drive_ids(card(FILES))
SETTINGS = ('brightness.txt', 'repeats.txt', 'ignored.txt')


def moved(lines, files=FILES, options=(), show=SHOW):
    """Runs these lines on a card of these files: the replies, the card's files and the
    show's folder's files afterwards."""
    with a_card(card(files)) as top:
        run, kept = support.start_and_keep(show, asked(0, *lines), ['--drive', top, *options])
        return replies(run), folder_of(top), kept


def index_of(files):
    """The rows of each folder of a card's index, by the folder's path, and the generation."""
    found = catalog.read(catalog.MemoryStorage(files, drive=True))
    assert found.state == 'ok', found
    return {folder.path: [(file_id, entry.name) for file_id, entry in folder.rows] for folder in found.index.folders}, found.marker.generation


def animations(files):
    return {name: data for name, data in files.items() if name.endswith('.odrg')}


class Moving(unittest.TestCase):
    def test_a_file_goes_last_among_the_files_of_its_new_folder_with_its_id(self):
        answers, left, _ = moved([f'move external {IDS["root.odrg"]} night', 'list'])
        self.assertEqual(answers[0], {'ok': True, 'id': IDS['root.odrg'], 'moved': True})
        rows, generation = index_of(left)
        self.assertEqual(generation, 2)
        self.assertEqual(rows['night'], [(IDS['night/near.odrg'], 'night/near.odrg'), (IDS['root.odrg'], 'night/root.odrg')])
        self.assertEqual(rows[''], [])
        self.assertEqual(left['night/root.odrg'], FILES['root.odrg'])
        self.assertNotIn('root.odrg', left)
        for name in ('catalog.do', 'upload.part', 'moving.txt', 'moving.part'):
            self.assertNotIn(name, left)
        self.assertEqual({path: ids for path, ids in drive_ids(left).items()},
                         {('night/root.odrg' if path == 'root.odrg' else path): ids for path, ids in IDS.items()})
        night = next(item for item in answers[1]['items'] if item.get('playlist') == 'night')
        self.assertEqual(night['files'], 2)

    def test_a_file_moved_to_the_root_goes_last_among_its_files(self):
        answers, left, _ = moved([f'move external {IDS["night/near.odrg"]} /'])
        self.assertEqual(answers[0], {'ok': True, 'id': IDS['night/near.odrg'], 'moved': True})
        rows, _ = index_of(left)
        self.assertEqual(rows[''], [(IDS['root.odrg'], 'root.odrg'), (IDS['night/near.odrg'], 'near.odrg')])
        self.assertEqual(rows['night'], [])
        self.assertEqual(rows['night/deep'], [(IDS['night/deep/old.odrg'], 'night/deep/old.odrg')])

    def test_the_folders_left_without_a_file_leave_the_index_and_their_directories_stay(self):
        answers, left, _ = moved([f'move external {IDS["a/b/c/far.odrg"]} /'])
        self.assertTrue(answers[0]['moved'], answers)
        rows, _ = index_of(left)
        self.assertEqual(sorted(rows), ['', 'night', 'night/deep', 'space room'])
        self.assertEqual(rows[''], [(IDS['root.odrg'], 'root.odrg'), (IDS['a/b/c/far.odrg'], 'far.odrg')])
        self.assertEqual(left['far.odrg'], FILES['a/b/c/far.odrg'])
        with a_card(card(FILES)) as top:
            support.start(SHOW, asked(0, f'move external {IDS["a/b/c/far.odrg"]} /'), ['--drive', top])
            self.assertTrue(pathlib.Path(top, 'odrig', 'a', 'b', 'c').is_dir())

    def test_moves_into_a_child_a_parent_a_cousin_a_sibling_and_out_of_a_folder_it_empties(self):
        lines = [f'move external {IDS["night/near.odrg"]} night/deep', f'move external {IDS["night/deep/old.odrg"]} night',
                 f'move external {IDS["space room/old.odrg"]} night/deep', f'move external {IDS["night/deep/old.odrg"]} a',
                 f'move external {IDS["root.odrg"]} a/b', f'move external {IDS["a/b/c/far.odrg"]} night']
        answers, left, _ = moved(lines)
        self.assertEqual([answer.get('moved') for answer in answers], [True] * 6, answers)
        rows, generation = index_of(left)
        self.assertEqual(generation, 7)
        self.assertEqual(rows, {
            '': [],
            'a': [(IDS['night/deep/old.odrg'], 'a/old.odrg')],
            'a/b': [(IDS['root.odrg'], 'a/b/root.odrg')],
            'night': [(IDS['a/b/c/far.odrg'], 'night/far.odrg')],
            'night/deep': [(IDS['night/near.odrg'], 'night/deep/near.odrg'), (IDS['space room/old.odrg'], 'night/deep/old.odrg')],
        })
        self.assertEqual(sorted(animations(left).values()), sorted(FILES.values()))

    def test_a_file_in_the_folder_already_is_answered_not_moved_and_nothing_is_written(self):
        answers, left, _ = moved([f'move external {IDS["night/near.odrg"]} night', f'move external {IDS["root.odrg"]} /'])
        self.assertEqual(answers, [{'ok': True, 'id': IDS['night/near.odrg'], 'moved': False}, {'ok': True, 'id': IDS['root.odrg'], 'moved': False}])
        self.assertEqual(left, card(FILES))

    def test_refusals_leave_the_card_as_it_was(self):
        night = next(folder.id for folder in catalog.read(catalog.MemoryStorage(card(FILES), drive=True)).index.folders if folder.path == 'night')
        cases = {
            'move external': 'bad-argument', f'move external {IDS["root.odrg"]}': 'bad-argument', f'move internal {IDS["root.odrg"]} /': 'bad-argument',
            'move external x /': 'bad-argument', f'move external {IDS["root.odrg"]} night/': 'bad-argument',
            f'move external {IDS["root.odrg"]} a/b/c/d': 'bad-argument', f'move external {IDS["root.odrg"]} night/x.odrg': 'bad-argument',
            f'move external {IDS["root.odrg"]} //': 'bad-argument', 'move external 99999 /': 'unknown-id', 'move external 1 /': 'unknown-id',
            f'move external {IDS["root.odrg"]} gone': 'unknown-id', f'move external {night} /': 'in-use',
            f'move external {IDS["space room/old.odrg"]} night/deep': 'in-use',
        }
        for line, error in cases.items():
            with self.subTest(line=line):
                answers, left, _ = moved([line])
                self.assertEqual(answers[0], {'ok': False, 'error': error})
                self.assertEqual(left, card(FILES))

    def test_a_name_the_destination_has_in_another_case_is_in_use(self):
        files = {**FILES, 'NEAR.odrg': loop_of(2, 11)}
        ids = drive_ids(card(files))
        answers, left, _ = moved([f'move external {ids["night/near.odrg"]} /'], files)
        self.assertEqual(answers[0], {'ok': False, 'error': 'in-use'})
        self.assertEqual(left, card(files))

    def test_a_new_path_over_100_bytes_is_refused(self):
        folder = 'f' * 90
        files = {'abcdefghijklmn.odrg': loop_of(2, 5), f'{folder}/a.odrg': loop_of(3, 6)}
        ids = drive_ids(card(files))
        answers, left, _ = moved([f'move external {ids["abcdefghijklmn.odrg"]} {folder}'], files)
        self.assertEqual(answers[0], {'ok': False, 'error': 'bad-argument'})
        self.assertEqual(left, card(files))

    def test_a_read_only_card_and_an_open_upload_are_refused(self):
        line = f'move external {IDS["root.odrg"]} night'
        answers, left, _ = moved([line], options=('--drive-read-only',))
        self.assertEqual(answers[0], {'ok': False, 'error': 'read-only'})
        with a_card(card(FILES)) as top:
            run = support.start(SHOW, [*asked(0, 'upload begin external x.odrg 100'), support.line(T0, line)], ['--drive', top])
            self.assertEqual(replies(run)[-1], {'ok': False, 'error': 'busy'})
            self.assertEqual(index_of(folder_of(top))[1], 1)

    def test_a_file_whose_name_begins_with_the_name_of_the_upload_part_moves_with_its_settings(self):
        for name in ('upload.part.odrg', 'upload.part x.odrg'):
            with self.subTest(name=name):
                files = {name: loop_of(2, 5), 'night/near.odrg': loop_of(3, 7)}
                file_id = drive_ids(card(files))[name]
                with a_card(card(files)) as top, support.installed(SHOW) as show:
                    run = support.session(show, asked(0, f'brightness {file_id} 9 save', f'move external {file_id} night'), ['--drive', top])
                    self.assertEqual(replies(run)[1], {'ok': True, 'id': file_id, 'moved': True})
                    left = folder_of(top)
                    rows, generation = index_of(left)
                    self.assertEqual(generation, 2)
                    self.assertEqual(rows['night'], [(drive_ids(card(files))['night/near.odrg'], 'night/near.odrg'), (file_id, f'night/{name}')])
                    self.assertEqual(left[f'night/{name}'], files[name])
                    self.assertEqual([other for other in left if other.endswith('.new') or other in ('catalog.do', 'upload.part', 'moving.txt', 'moving.part')], [])
                    again = replies(support.session(show, asked(0, f'saved {file_id}', 'catalog'), ['--drive', top]))
                    self.assertEqual(again[0], {'ok': True, 'brightness': 9, 'repeat': None, 'start': False})

    def test_the_file_that_plays_goes_on_under_its_new_path(self):
        file_id = IDS['space room/old.odrg']
        answers, _, _ = moved([f'play {file_id}', f'move external {file_id} night', 'status'])
        self.assertTrue(answers[1]['moved'], answers)
        self.assertEqual(answers[2]['file'], 'night/old.odrg')


class Settings(unittest.TestCase):
    def test_the_saved_settings_follow_the_file_and_stay_after_a_restart(self):
        file_id = IDS['space room/old.odrg']
        with a_card(card(FILES)) as top, support.installed(SHOW) as show:
            run = support.session(show, asked(0, f'brightness {file_id} 9 save', f'repeat {file_id} 3 save', f'ignore {file_id} 1',
                                              f'move external {file_id} night', f'saved {file_id}', f'list in {night_id(top)}'), ['--drive', top])
            answers = replies(run)
            self.assertTrue(answers[3]['moved'], answers)
            self.assertEqual(answers[4], {'ok': True, 'brightness': 9, 'repeat': 3, 'start': False})
            row = next(item for item in answers[5]['items'] if item.get('id') == file_id)
            self.assertTrue(row['ignored'])
            kept = support.folder_files(show)
            for name in SETTINGS:
                self.assertIn(b' night/old.odrg\n', kept[name], name)
                self.assertNotIn(b'space room/old.odrg', kept[name], name)
            again = replies(support.session(show, asked(0, f'saved {file_id}'), ['--drive', top]))
            self.assertEqual(again[0], {'ok': True, 'brightness': 9, 'repeat': 3, 'start': False})

    def test_a_stale_setting_of_the_new_path_is_dropped(self):
        show = {**SHOW, 'brightness.txt': 'odrig-brightness 1\n5 x night/root.odrg\n9 x root.odrg\n7 f four.odrg\n'}
        _, _, kept = moved([f'move external {IDS["root.odrg"]} night'], show=show)
        self.assertEqual(kept['brightness.txt'], b'odrig-brightness 1\n9 x night/root.odrg\n7 f four.odrg\n')

    def test_a_journal_of_the_cards_generation_is_finished_at_the_mount_and_another_is_dropped(self):
        files = {'night/x.odrg': loop_of(2, 5)}
        show = {**SHOW, 'brightness.txt': 'odrig-brightness 1\n9 x x.odrg\n'}
        for generation, settled in (('00000001', b'odrig-brightness 1\n9 x night/x.odrg\n'), ('00000002', b'odrig-brightness 1\n9 x x.odrg\n')):
            with self.subTest(generation=generation):
                journal = f'odrig-moving 1 {generation}\nx.odrg\nnight/x.odrg\n'.encode('ascii')
                with a_card({**card(files), 'moving.txt': journal}) as top:
                    run, kept = support.start_and_keep(show, asked(0, f'saved {drive_ids(card(files))["night/x.odrg"]}'), ['--drive', top])
                    left = folder_of(top)
                self.assertEqual(kept['brightness.txt'], settled)
                self.assertNotIn('moving.txt', left)
                self.assertEqual(replies(run)[0]['brightness'], 9 if generation == '00000001' else None)


class PowerCuts(unittest.TestCase):
    def test_a_move_survives_a_power_cut_at_every_storage_call(self):
        file_id = IDS['space room/old.odrg']
        start = card(FILES)
        outcomes = set()
        with a_card(start) as top, support.installed(SHOW) as show:
            support.session(show, asked(0, f'brightness {file_id} 9 save'), ['--drive', top])
            settings = support.folder_files(show)
        for number in range(1, 120):
            with a_card(start) as top, support.installed(settings) as show:
                result = support.host('session', show, support.CHECK_FIRST, '--drive', top, '--cut-at', number,
                                      stdin=(support.line(T0, f'move external {file_id} night') + '\n').encode('ascii'))
                if result.status != POWER_CUT:
                    self.assertEqual(result.status, 0, result.out[-300:])
                    break
                answers = replies(support.session(show, asked(0, f'saved {file_id}'), ['--drive', top]))
                after = folder_of(top)
                kept = support.folder_files(show)
            rows, generation = index_of(after)
            outcomes.add(generation)
            path = 'night/old.odrg' if generation == 2 else 'space room/old.odrg'
            self.assertIn((file_id, path), [row for folder in rows.values() for row in folder], number)
            self.assertEqual(after[path], FILES['space room/old.odrg'], number)
            self.assertEqual(sorted(animations(after)), sorted(name if name != 'space room/old.odrg' else path for name in FILES), number)
            # Traces of a change that was not committed may stay; nothing of a move does.
            for name in ('upload.part', 'moving.txt', 'moving.part'):
                self.assertNotIn(name, after, number)
            for entry in catalog.read(catalog.MemoryStorage(after, drive=True)).entries:
                self.assertEqual(zlib.crc32(after[entry.name]), entry.crc, number)
            self.assertEqual(kept['brightness.txt'], f'odrig-brightness 1\n9 x {path}\n'.encode('ascii'), number)
            self.assertEqual(answers[0]['brightness'], 9, number)
        else:
            self.fail('storage operation count exceeded the test bound')
        self.assertEqual(outcomes, {1, 2})


class Record(unittest.TestCase):
    def test_the_pc_library_finishes_a_record_that_moves_a_name_with_spaces(self):
        files = card(FILES)
        record = 'odrig-catalog-do 1 generation 00000002\npages 0000\nmove space room/old.odrg upload.part\nmove upload.part night/old.odrg\n'
        data = record.encode('ascii') + f'crc {zlib.crc32(record.encode("ascii")):08x}\n'.encode('ascii')
        _, _, actions = catalog.parse_do(data)
        self.assertEqual(actions, [('move', 'space room/old.odrg', 'upload.part'), ('move', 'upload.part', 'night/old.odrg')])
        storage = catalog.MemoryStorage({**files, 'catalog.do': data}, drive=True)
        self.assertTrue(catalog.finish(storage))
        self.assertEqual(storage.files['night/old.odrg'], FILES['space room/old.odrg'])
        self.assertNotIn('space room/old.odrg', storage.files)

    def test_the_pc_library_reads_a_name_that_begins_with_the_name_of_the_upload_part(self):
        for name in ('upload.part.odrg', 'upload.part x.odrg'):
            with self.subTest(name=name):
                record = f'odrig-catalog-do 1 generation 00000002\npages 0000\nmove {name} upload.part\nmove upload.part night/{name}\n'.encode('ascii')
                _, _, actions = catalog.parse_do(record + f'crc {zlib.crc32(record):08x}\n'.encode('ascii'))
                self.assertEqual(actions, [('move', name, 'upload.part'), ('move', 'upload.part', f'night/{name}')])


def night_id(top):
    index = catalog.read(catalog.Storage(pathlib.Path(top, 'odrig'), drive=True)).index
    return next(folder.id for folder in index.folders if folder.path == 'night')


if __name__ == '__main__':
    unittest.main()

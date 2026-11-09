"""Moves inside the card and of folders in the shared app: a file of the card moved on the
card by the board with `move external`, keeping its id and its saved settings; a folder of
the card moved on the card file by file, its files keeping theirs; folders moved between the
board's own storage and the card; a folder never moved into itself; the playlist of a moved
folder following it, but not into a Clocks folder between animations; and a folder's move
cut short finished when the app is opened again."""

import json
import pathlib
import tempfile
import time
import unittest

from odrig import catalog

from tests.core import support as core_support
from tests.emulator import support as emulator_support
from . import support
from .test_target import entered


def clip(seed):
    return core_support.clip(seed, 60, 6, durations=(20,) * 3, compressed=False)


CARD = {'night/near.odrg': clip(1), 'night/deep/old.odrg': clip(2), 'clocks/face.odrg': clip(3)}
FOLDERS = "odrig-folders 1 3\n1 20 0 shows\n2 21 0 shows/night\n"
CLOCKS_FOLDERS = "odrig-folders 1 3\n1 20 0 clocks\n2 21 0 clocks/message\n"


class Moves(unittest.TestCase):
    def board(self, card=CARD, folders=None):
        """A board with `root.odrg` in its own storage, and with `folders` also `1/face.odrg`
        and `2/deep.odrg` in its folders; and a card of these files whose catalog is made."""
        items = [{'id': 1, 'file': 'root.odrg'}]
        files = {'mapping.json': core_support.mapping_texts()['legs-2'], 'root.odrg': clip(4)}
        if folders is not None:
            items += [{'id': 2, 'file': '1/face.odrg'}, {'id': 3, 'file': '2/deep.odrg'}]
            files['folders.txt'] = folders
        files['show.json'] = json.dumps({'version': 1, 'brightness': 32, 'items': items})
        folder = emulator_support.installed(pathlib.Path(entered(self, tempfile.TemporaryDirectory()), 'show'), files)
        if folders is not None:
            for name, seed in (('1/face.odrg', 5), ('2/deep.odrg', 6)):
                path = folder.joinpath(*name.split('/'))
                path.parent.mkdir()
                path.write_bytes(clip(seed))
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        self.card = top / 'odrig'
        for name, data in card.items():
            path = self.card.joinpath(*name.split('/'))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        _, refused = catalog.rebuild(catalog.Storage(self.card, drive=True), names=sorted(card), canvas=(60, 6))
        self.assertEqual(refused, [])
        emulator = entered(self, emulator_support.Emulator(folder, '--drive', top))
        return folder, emulator

    def answered(self, emulator, line, wanted=lambda reply: reply.get('ok') is True):
        for _ in range(200):
            reply = json.loads(emulator.command(line))
            if wanted(reply):
                return reply
            time.sleep(0.05)
        raise AssertionError(f'{line} never answered as wanted: {reply}')

    def every(self, emulator):
        """Every row of every level of both storages, by the path of a file or a folder."""
        found = {}
        self.answered(emulator, 'list', lambda reply: any(row.get('external') is True for row in reply.get('items', [])))
        waiting = ['list']
        while waiting:
            line = waiting.pop(0)
            for row in self.answered(emulator, line)['items']:
                path = row.get('playlist') or row.get('file')
                found[(row.get('external') is True, path)] = row
                if 'playlist' in row:
                    waiting.append(f'list in {row["id"]}')
        return found

    def ids(self):
        index = catalog.read(catalog.Storage(self.card, drive=True)).index
        return {entry.name: file_id for folder in index.folders for file_id, entry in folder.rows}

    def test_a_file_of_the_card_moved_on_the_card_keeps_its_id_and_its_saved_settings(self):
        _, emulator = self.board()
        file_id = self.ids()['night/deep/old.odrg']
        self.answered(emulator, f'brightness {file_id} 9 save')
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={
            'rows': 1, 'enter': ['night', 'night/deep'], 'files': [file_id], 'storage': 'external', 'folder': 'clocks'}).seen
        self.assertIn('External /night/deep/old.odrg → External /clocks/old.odrg', found['preview'])
        self.assertEqual(found['go'], 'Move 1 file')
        self.assertIn('Moved 1 of 1', found['message'])
        self.assertEqual(self.ids()['clocks/old.odrg'], file_id)
        self.assertEqual((self.card / 'clocks' / 'old.odrg').read_bytes(), CARD['night/deep/old.odrg'])
        self.assertFalse((self.card / 'night' / 'deep' / 'old.odrg').exists())
        self.assertEqual(json.loads(emulator.command(f'saved {file_id}'))['brightness'], 9)
        self.assertEqual(catalog.read(catalog.Storage(self.card, drive=True)).state, 'ok')

    def test_a_folder_of_the_card_moved_on_the_card_keeps_the_ids_of_its_files_and_its_ignore(self):
        _, emulator = self.board()
        before = self.ids()
        night = self.every(emulator)[(True, 'night')]['id']
        self.answered(emulator, f'ignore {night} 1')
        self.answered(emulator, f'brightness {before["night/near.odrg"]} 7 save')
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={
            'rows': 1, 'folders': ['night'], 'storage': 'external', 'folder': 'clocks'}).seen
        self.assertIn('1 folder of External storage, with everything in it.', found['summary'])
        self.assertIn('Folder External /night/ → External /clocks/night/', found['preview'])
        self.assertIn('External /night/deep/old.odrg → External /clocks/night/deep/old.odrg', found['preview'])
        self.assertEqual(found['go'], 'Move 1 folder with 2 files')
        self.assertIn('Moved 2 of 2', found['message'])
        self.assertIn('External /night/ is now External /clocks/night/.', found['message'])
        after = self.ids()
        self.assertEqual(after, {'clocks/face.odrg': before['clocks/face.odrg'], 'clocks/night/near.odrg': before['night/near.odrg'],
                                 'clocks/night/deep/old.odrg': before['night/deep/old.odrg']})
        rows = self.every(emulator)
        self.assertNotIn((True, 'night'), rows)
        self.assertTrue(rows[(True, 'clocks/night')]['ignored'])
        self.assertFalse(rows[(True, 'clocks/night/deep')]['ignored'])
        self.assertEqual(json.loads(emulator.command(f'saved {before["night/near.odrg"]}'))['brightness'], 7)
        self.assertEqual(catalog.read(catalog.Storage(self.card, drive=True)).state, 'ok')

    def test_a_folder_of_the_board_moved_to_the_card_takes_its_settings(self):
        folder, emulator = self.board(folders=FOLDERS)
        self.answered(emulator, 'brightness 2 9 save')
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={
            'rows': 1, 'folders': ['shows'], 'storage': 'external', 'folder': ''}).seen
        self.assertIn('Folder Internal /shows/ → External /shows/', found['preview'])
        self.assertIn('Internal /shows/night/deep.odrg → External /shows/night/deep.odrg', found['preview'])
        self.assertIn('Moved 2 of 2', found['message'])
        self.assertEqual((self.card / 'shows' / 'face.odrg').read_bytes(), clip(5))
        self.assertEqual((self.card / 'shows' / 'night' / 'deep.odrg').read_bytes(), clip(6))
        rows = self.every(emulator)
        self.assertNotIn((False, 'shows'), rows)
        self.assertFalse((folder / '1' / 'face.odrg').exists())
        moved = rows[(True, 'shows/face.odrg')]
        self.assertEqual(json.loads(emulator.command(f'saved {moved["id"]}'))['brightness'], 9)

    def test_a_folder_of_the_card_moved_to_the_board(self):
        folder, emulator = self.board()
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={
            'rows': 1, 'folders': ['night'], 'storage': 'internal', 'folder': ''}).seen
        self.assertIn('Folder External /night/ → Internal /night/', found['preview'])
        self.assertIn('Moved 2 of 2', found['message'])
        rows = self.every(emulator)
        self.assertIn((False, 'night'), rows)
        self.assertIn((False, 'night/deep'), rows)
        self.assertEqual(rows[(False, 'night/deep/old.odrg')]['bytes'], len(CARD['night/deep/old.odrg']))
        self.assertNotIn((True, 'night'), rows)
        self.assertFalse((self.card / 'night' / 'near.odrg').exists())
        stored = rows[(False, 'night/near.odrg')]['stored']
        self.assertEqual(folder.joinpath(*stored.split('/')).read_bytes(), CARD['night/near.odrg'])

    def test_a_folder_is_not_moved_into_itself_nor_below_itself(self):
        _, emulator = self.board()
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={
            'rows': 1, 'folders': ['night'], 'storage': 'external', 'folder': 'night/deep', 'skipped': True}).seen
        self.assertTrue(any('not moved into itself' in line for line in found['preview']), found['preview'])
        self.assertEqual(found['go'], 'Move 0 files')
        self.assertIn('night/deep', found['options'])

    def test_a_folder_whose_name_the_destination_has_is_moved_under_another_name(self):
        _, emulator = self.board(card={**CARD, 'clocks/night/x.odrg': clip(7)})
        before = self.ids()
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={
            'rows': 1, 'folders': ['night'], 'storage': 'external', 'folder': 'clocks', 'rename': {'night': 'evening'}}).seen
        self.assertIn('Folder External /night/ → External /clocks/evening/', found['preview'])
        self.assertIn('Moved 2 of 2', found['message'])
        self.assertEqual(self.ids()['clocks/evening/deep/old.odrg'], before['night/deep/old.odrg'])

    def test_a_folders_move_cut_short_is_finished_when_the_app_is_opened_again(self):
        _, emulator = self.board()
        rows = self.every(emulator)
        night = rows[(True, 'night')]
        source = [rows[(True, 'night/near.odrg')], rows[(True, 'night/deep/old.odrg')]]
        journal = [{'kind': 'folder', 'source': {'id': night['id'], 'storage': 'external', 'path': 'night'},
                    'destination': {'storage': 'external', 'path': 'clocks/night'},
                    'folders': [{'path': 'clocks/night', 'ignored': False}, {'path': 'clocks/night/deep', 'ignored': False}],
                    'files': [{'source': row, 'storage': 'external', 'folder': f'clocks/{row["file"].rpartition("/")[0]}', 'name': row['file'].rpartition('/')[2],
                               'path': f'clocks/{row["file"]}'} for row in source]}]
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={'rows': 1, 'journal': journal}).seen
        self.assertIn('Finished the interrupted move of night/ (2 files)', found['message'])
        self.assertIsNone(found['kept'] and json.loads(found['kept']).get(f'127.0.0.1:{emulator.port}'))
        self.assertEqual(self.ids()['clocks/night/deep/old.odrg'], source[1]['id'])
        self.assertEqual(self.ids()['clocks/night/near.odrg'], source[0]['id'])

    def test_the_playlist_of_a_folder_follows_it_to_its_new_place(self):
        _, emulator = self.board()
        night = self.every(emulator)[(True, 'night')]['id']
        self.answered(emulator, f'play {night}')
        self.assertEqual(json.loads(emulator.command('status'))['playlist'], 'night')
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={
            'rows': 1, 'folders': ['night'], 'storage': 'external', 'folder': 'clocks'}).seen
        self.assertIn('Moved 2 of 2', found['message'])
        moved = self.every(emulator)[(True, 'clocks/night')]['id']
        status = self.answered(emulator, 'status', lambda reply: reply.get('playlist') is not None)
        self.assertEqual((status['playing'], status['playlist']), (moved, 'clocks/night'))

    def test_between_animations_the_playlist_of_a_folder_does_not_follow_it_into_clocks(self):
        _, emulator = self.board()
        self.answered(emulator, 'clocks on')
        night = self.every(emulator)[(True, 'night')]['id']
        self.answered(emulator, f'play {night}')
        self.assertEqual(json.loads(emulator.command('status'))['playlist'], 'night')
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={
            'rows': 1, 'folders': ['night'], 'storage': 'external', 'folder': 'clocks'}).seen
        self.assertIn('Moved 2 of 2. External /night/ is now External /clocks/night/.', found['message'])
        self.assertNotIn('Its playlist plays there.', found['message'])
        status = json.loads(emulator.command('status'))
        self.assertEqual((status['clock_mode'], status['playing'], status['playlist']), ('between', 'all', None))

    def test_between_animations_the_playlist_of_a_folder_does_not_follow_it_into_the_boards_clocks(self):
        _, emulator = self.board(folders=CLOCKS_FOLDERS)
        self.answered(emulator, 'clocks on')
        night = self.every(emulator)[(True, 'night')]['id']
        self.answered(emulator, f'play {night}')
        self.assertEqual(json.loads(emulator.command('status'))['playlist'], 'night')
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={
            'rows': 1, 'folders': ['night'], 'storage': 'internal', 'folder': 'clocks'}).seen
        self.assertIn('Moved 2 of 2. External /night/ is now Internal /clocks/night/.', found['message'])
        self.assertNotIn('Its playlist plays there.', found['message'])
        self.assertIn((False, 'clocks/night'), self.every(emulator))
        status = json.loads(emulator.command('status'))
        self.assertEqual((status['clock_mode'], status['playing'], status['playlist']), ('between', 'all', None))

    def test_a_kept_folders_job_that_the_board_refuses_is_given_up_once(self):
        _, emulator = self.board()
        rows = self.every(emulator)
        night = rows[(True, 'night')]
        # The parent `missing` is not there: `folder make internal missing/night` is unknown-id.
        journal = [{'kind': 'folder', 'source': {'id': night['id'], 'storage': 'external', 'path': 'night'},
                    'destination': {'storage': 'internal', 'path': 'missing/night'},
                    'folders': [{'path': 'missing/night', 'ignored': False}],
                    'files': [{'source': rows[(True, 'night/near.odrg')], 'storage': 'internal', 'folder': 'missing/night', 'name': 'near.odrg', 'path': 'missing/night/near.odrg'}]}]
        found = support.run('move-selected', address=f'127.0.0.1:{emulator.port}', settings={'rows': 1, 'journal': journal, 'watch': 2000}).seen
        self.assertIn('The interrupted move of night/ was given up: The folder above /missing/night is not on the installation any more.', found['message'])
        self.assertEqual([line for line in found['sentAfter'] if line.startswith('folder make')], [])
        self.assertIsNone(found['kept'] and json.loads(found['kept']).get(f'127.0.0.1:{emulator.port}'))
        self.assertTrue((self.card / 'night' / 'near.odrg').exists())


class Jobs(unittest.TestCase):
    """The jobs of moves without the app, against a board the scenario plays."""

    @classmethod
    def setUpClass(cls):
        cls.found = support.run('move-jobs').seen

    def test_a_folders_job_cut_by_a_lost_link_is_kept_for_the_next_connection(self):
        case = self.found['cut after the folder is made']
        self.assertIsNone(case['error'])
        self.assertEqual(case['result'], {'moved': [], 'failed': 0, 'unstarted': 2, 'cut': 'no-answer'})
        self.assertEqual(case['kept'], [{'kind': 'folder', 'path': 'night', 'files': [60021, 60022]}])
        self.assertEqual(case['sent'], ['folder make external day/night', 'move external 60021 day/night', 'move external 60021 day/night'])

    def test_a_folders_job_whose_folder_is_refused_is_given_up(self):
        case = self.found['the folder refused']
        self.assertEqual(case['error'], 'read-only')
        self.assertEqual(case['kept'], [])
        self.assertEqual(case['sent'], ['folder make external day/night'])

    def test_a_kept_folders_job_whose_folder_is_refused_is_given_up_and_said(self):
        case = self.found['a kept job whose folder is refused']
        self.assertIsNone(case['error'])
        self.assertEqual(case['result'], {'finished': [], 'notMoved': [], 'givenUp': [['night', 'unknown-id']]})
        self.assertEqual(case['kept'], [])

    def test_the_files_a_kept_folders_job_could_not_move_are_said(self):
        case = self.found['a kept job whose files are refused']
        self.assertIsNone(case['error'])
        self.assertEqual(case['result']['failed'], [['night/f1.odrg', 'in-use'], ['night/f2.odrg', 'in-use']])
        self.assertEqual(case['kept'], [])

    def test_a_kept_folders_job_stopped_by_another_target_is_kept(self):
        case = self.found['a kept job stopped by another target']
        self.assertIsNone(case['error'])
        self.assertEqual(case['result']['cut'], ['night'])
        self.assertEqual(case['kept'], [{'kind': 'folder', 'path': 'night', 'files': [60022]}])
        self.assertNotIn('move external 60022 day/night', case['sent'])

    def test_a_lost_reply_of_a_move_on_the_card_is_sent_once_more(self):
        case = self.found['a lost reply of a move on the card']
        self.assertIsNone(case['error'])
        self.assertEqual(case['result'], 60021)
        self.assertEqual(case['sent'], ['move external 60021 day', 'move external 60021 day'])

    def test_in_clocks_only_a_kept_job_whose_destination_is_closed_waits_and_its_source_keeps_its_settings(self):
        case = self.found['kept jobs in Clocks only']
        self.assertIsNone(case['error'])
        self.assertEqual(case['result'], {'finished': [], 'notMoved': ['clocks/face.odrg'], 'held': ['clocks/cface.odrg', 'clocks/dial.odrg', 'clocks/night/'],
                                          'givenUp': [], 'stages': ['sending', 'folder', 'sent']})
        self.assertEqual([line for line in case['sent'] if not line.startswith('list')],
                         ['brightness 2 20 save', 'brightness 60030 30 save', 'repeat 60030 2 save'])
        self.assertEqual(case['kept'], [{'kind': 'file', 'path': 'clocks/dial.odrg', 'files': None}, {'kind': 'folder', 'path': 'clocks/night', 'files': [60032]},
                                        {'kind': 'file', 'path': 'clocks/cface.odrg', 'files': None}])

    def test_once_clocks_only_is_left_a_kept_job_that_waited_takes_its_sources_settings_again_and_finishes(self):
        case = self.found['kept jobs once Clocks only is left']
        self.assertIsNone(case['error'])
        self.assertEqual(case['result'], {'finished': ['clocks/dial.odrg', 'clocks/cface.odrg'], 'notMoved': [], 'held': [], 'givenUp': [], 'stages': []})
        self.assertEqual([line for line in case['sent'] if not line.startswith('list')],
                         ['brightness 8 40 save', 'brightness 60031 default', 'remove 60031',
                          'brightness 7 30 save', 'repeat 7 2 save', 'brightness 60030 default', 'repeat 60030 default', 'remove 60030'])
        self.assertEqual(case['kept'], [])

    def test_two_selected_folders_of_one_name_are_not_merged(self):
        case = self.found['two folders of one name']
        self.assertIsNone(case['first'])
        self.assertEqual(case['second'], 'Another selected folder takes this name. Give it another name to move it.')


if __name__ == '__main__':
    unittest.main()

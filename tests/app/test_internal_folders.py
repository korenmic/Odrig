"""The folders of the board's own storage in the shared app: their rows at the root, a folder
entered with the paths of its files, `New folder` at the root and inside one, the reply of
`list` the app takes from a target that has them, and moves of files out of a folder of
either storage while both have folders of one path."""

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

FOLDERS = "odrig-folders 1 3\n1 20 0 shows\n2 21 0 shows/night\n"


def clip(seed):
    return core_support.clip(seed, 60, 6, durations=(20,) * 3, compressed=False)


class InternalFolders(unittest.TestCase):
    def board(self, text=FOLDERS, items=(), drive=None):
        """A board whose storage has the folders of `text`: `root.odrg` at the root,
        `1/face.odrg` and `2/deep.odrg` in its first two, and the items given after them;
        and with `drive`, the files of a card whose catalog is made."""
        folder = emulator_support.installed(pathlib.Path(entered(self, tempfile.TemporaryDirectory()), 'show'), {
            'mapping.json': core_support.mapping_texts()['legs-2'],
            'show.json': json.dumps({'version': 1, 'brightness': 32, 'items': [
                {'id': 1, 'file': 'root.odrg'}, {'id': 2, 'file': '1/face.odrg'}, {'id': 3, 'file': '2/deep.odrg'}, *items]}),
            'folders.txt': text,
            'root.odrg': clip(1),
        })
        for name, seed in (('1/face.odrg', 2), ('2/deep.odrg', 3)):
            path = folder.joinpath(*name.split('/'))
            path.parent.mkdir()
            path.write_bytes(clip(seed))
        options = ()
        if drive is not None:
            top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
            card = top / 'odrig'
            for name, data in drive.items():
                path = card.joinpath(*name.split('/'))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            _, refused = catalog.rebuild(catalog.Storage(card, drive=True), names=sorted(drive), canvas=(60, 6))
            self.assertEqual(refused, [])
            options = ('--drive', top)
            self.card = card
        emulator = entered(self, emulator_support.Emulator(folder, *options))
        return folder, emulator

    def listed(self, emulator, folder=None):
        return json.loads(emulator.command('list' if folder is None else f'list in {folder}'))['items']

    def answered(self, emulator, line, wanted=lambda reply: reply.get('ok') is True):
        """The reply to a line once it is the one wanted, asked again while the board reads
        what it keeps and takes the card up."""
        for _ in range(200):
            reply = json.loads(emulator.command(line))
            if wanted(reply):
                return reply
            time.sleep(0.05)
        raise AssertionError(f'{line} never answered as wanted: {reply}')

    def test_the_root_and_a_folder_of_the_boards_storage_are_walked_and_folders_made_in_them(self):
        folder, emulator = self.board()
        found = support.run('internal', address=f'127.0.0.1:{emulator.port}', settings={'rows': 1, 'folders': 1, 'enter': 'shows', 'inside': 1}).seen
        self.assertEqual(found['root']['rows'], ['1 root.odrg'])
        self.assertEqual(found['root']['folders'], [{'path': 'shows', 'id': 20, 'meta': '1 animation'}])
        self.assertTrue(found['atRoot']['offered'])
        self.assertIn('Made the folder Internal /made', found['atRoot']['made'])
        self.assertEqual(found['inside']['rows'], ['2 shows/face.odrg'])
        self.assertEqual(found['inside']['folders'], [{'path': 'shows/night', 'id': 21, 'meta': '1 animation'}])
        self.assertFalse(found['inFolder']['offered'])
        self.assertEqual(found['inFolder']['where'], 'In Internal /shows/')
        self.assertIn('Made the folder Internal /shows/inner', found['inFolder']['made'])
        self.assertEqual((folder / 'folders.txt').read_text(encoding='ascii'),
                         'odrig-folders 1 5\n3 4 0 made\n1 20 0 shows\n4 5 0 shows/inner\n2 21 0 shows/night\n')

    def batch(self, emulator, files, path=None):
        """Runs a batch of the ready-made `files`, `{name: bytes}`, picked on Upload after
        browsing to the folder `path`."""
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        for name, data in files.items():
            (media / name).write_bytes(data)
        return support.run('batch', address=f'127.0.0.1:{emulator.port}', media=media,
                           settings={'mode': 'run', 'rows': 1, 'path': path, 'files': list(files)}).seen

    def test_a_batch_at_the_root_takes_an_id_that_no_folder_holds(self):
        folder, emulator = self.board()
        face = (folder / '1' / 'face.odrg').read_bytes()
        found = self.batch(emulator, {'new.odrg': clip(8), 'other.odrg': clip(9)})
        self.assertEqual(found['destination'], 'Internal /')
        self.assertEqual(found['rows'], ['uploaded as animation 4', 'uploaded as animation 5'])
        self.assertEqual([(row['id'], row['file']) for row in self.listed(emulator, 20) if 'file' in row], [(2, 'shows/face.odrg')])
        self.assertEqual((folder / '1' / 'face.odrg').read_bytes(), face)
        self.assertEqual((folder / 'new.odrg').read_bytes(), clip(8))
        self.assertEqual((folder / 'other.odrg').read_bytes(), clip(9))

    def test_a_batch_browsed_to_an_internal_folder_goes_into_it_named_against_its_files(self):
        folder, emulator = self.board()
        face = (folder / '1' / 'face.odrg').read_bytes()
        found = self.batch(emulator, {'face.odrg': clip(7), 'new.odrg': clip(8)}, path='shows')
        self.assertEqual(found['names'], ['face-2.odrg', 'new.odrg'])
        self.assertEqual(found['destination'], 'Internal /shows/')
        self.assertEqual(found['rows'], ['uploaded as animation 4', 'uploaded as animation 5'])
        self.assertEqual(sorted((row['id'], row['file']) for row in self.listed(emulator, 20) if 'file' in row),
                         [(2, 'shows/face.odrg'), (4, 'shows/face-2.odrg'), (5, 'shows/new.odrg')])
        self.assertEqual((folder / '1' / 'face.odrg').read_bytes(), face)
        self.assertEqual((folder / '1' / 'face-2.odrg').read_bytes(), clip(7))
        self.assertEqual((folder / '1' / 'new.odrg').read_bytes(), clip(8))

    def test_a_batch_whose_internal_folder_goes_at_a_files_turn_ends_the_run(self):
        folder, emulator = self.board()
        pruned = []

        def answer(line):
            reply = emulator.command(line.decode('utf-8')).decode('utf-8')
            if not pruned and line.startswith(b'upload end ') and reply.startswith('{"ok":true'):
                # The folder loses its last files to another controller: it goes.
                ids = ','.join(str(row['id']) for row in self.listed(emulator, 21) if 'file' in row)
                pruned.append(self.answered(emulator, f'remove many {ids}'))
            return 200, reply

        stand_in = entered(self, support.StandIn(answer))
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        for name, seed in (('a.odrg', 7), ('b.odrg', 8), ('c.odrg', 9)):
            (media / name).write_bytes(clip(seed))
        found = support.run('batch', address=stand_in.address, media=media,
                            settings={'mode': 'run', 'rows': 1, 'path': 'shows/night', 'files': ['a.odrg', 'b.odrg', 'c.odrg']}).seen
        self.assertEqual(found['destination'], 'Internal /shows/night/')
        self.assertEqual(found['rows'], ['uploaded as animation 4', 'failed: The explored folder changed or disappeared.', 'not sent'])
        self.assertEqual(found['end'], '1 of 3 uploaded, 1 failed, 1 not sent.')
        self.assertEqual([row.get('playlist') for row in self.listed(emulator, 20) if 'playlist' in row], [])
        self.assertFalse(any(line.startswith(b'upload begin') and b'b.odrg' in line for _, line in stand_in.lines))

    def test_a_batch_whose_internal_folder_goes_between_the_check_and_the_begin_ends_the_run(self):
        folder, emulator = self.board()

        def answer(line):
            if line.startswith(b'upload begin ') and b'/b.odrg ' in line:
                return 200, '{"ok":false,"error":"unknown-id"}\n'
            return 200, emulator.command(line.decode('utf-8')).decode('utf-8')

        stand_in = entered(self, support.StandIn(answer))
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        for name, seed in (('a.odrg', 7), ('b.odrg', 8), ('c.odrg', 9)):
            (media / name).write_bytes(clip(seed))
        found = support.run('batch', address=stand_in.address, media=media,
                            settings={'mode': 'run', 'rows': 1, 'path': 'shows/night', 'files': ['a.odrg', 'b.odrg', 'c.odrg']}).seen
        self.assertEqual(found['rows'], ['uploaded as animation 4', 'failed: The folder of this upload is not on the installation any more. (unknown-id)', 'not sent'])
        self.assertFalse((folder / '2' / 'c.odrg').exists())

    def test_an_upload_prepared_at_an_internal_folder_that_went_since_is_refused_in_words(self):
        folder, emulator = self.board()
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media / 'ready.odrg').write_bytes(clip(7))

        def prune():
            ids = ','.join(str(row['id']) for row in self.listed(emulator, 21) if 'file' in row)
            self.answered(emulator, f'remove many {ids}')

        found = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}', media=media,
                            settings={'rows': 1, 'path': 'shows/night', 'file': 'ready.odrg', 'stepBeforeSend': True}, steps=[prune]).seen
        self.assertEqual(found['destination'], 'Internal /shows/night/ready.odrg')
        self.assertEqual(found['message'], 'The explored folder changed or disappeared. Select the destination again.')
        self.assertFalse((folder / 'ready.odrg').exists())
        self.assertEqual([path.name for path in folder.rglob('ready.odrg')], [])

    def test_an_upload_at_an_internal_folder_is_checked_against_the_files_of_that_folder(self):
        folder, emulator = self.board()
        face = (folder / '1' / 'face.odrg').read_bytes()
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media / 'face.odrg').write_bytes(clip(7))
        found = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}', media=media,
                            settings={'rows': 1, 'path': 'shows', 'file': 'face.odrg'}).seen
        self.assertEqual(found['destination'], 'Internal /shows/face.odrg')
        self.assertEqual(found['message'], 'A file already exists at this destination. Choose another filename; nothing was replaced.')
        self.assertEqual((folder / '1' / 'face.odrg').read_bytes(), face)
        self.assertEqual([(row['id'], row['file']) for row in self.listed(emulator, 20) if 'file' in row], [(2, 'shows/face.odrg')])

    def test_a_file_moved_out_of_an_internal_folder_leaves_it_and_takes_its_settings(self):
        folder, emulator = self.board()
        data = (folder / '1' / 'face.odrg').read_bytes()
        self.answered(emulator, 'brightness 2 9 save')
        found = support.run('move-out', address=f'127.0.0.1:{emulator.port}', settings={'rows': 1, 'enter': [[20, 'shows']], 'id': 2, 'storage': 'internal'}).seen
        self.assertIn('Internal /shows/face.odrg \u2192 Internal /face.odrg', found['preview'])
        self.assertIn('Moved 1 of 1', found['message'])
        moved = [row for row in self.listed(emulator) if row.get('file') == 'face.odrg']
        self.assertEqual(len(moved), 1)
        self.assertNotIn(2, [row['id'] for row in self.listed(emulator, 20)])
        self.assertFalse((folder / '1' / 'face.odrg').exists())
        self.assertEqual((folder / 'face.odrg').read_bytes(), data)
        self.assertEqual(json.loads(emulator.command(f'saved {moved[0]["id"]}'))['brightness'], 9)

    def test_a_file_of_an_internal_folder_that_another_item_names_stays(self):
        folder, emulator = self.board(items=[{'id': 4, 'file': '1/face.odrg'}])
        found = support.run('move-out', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 1, 'enter': [[20, 'shows']], 'id': 2, 'storage': 'internal', 'skipped': True}).seen
        self.assertIn('Another item of the show names the same file; it stays.', found['preview'])
        self.assertEqual(found['go'], 'Move 0 files')

    def test_a_cards_file_moves_out_of_its_folder_when_the_boards_storage_has_a_folder_of_that_path(self):
        text = 'odrig-folders 1 4\n1 20 0 night\n2 21 0 night/deep\n3 22 0 shows\n'
        data = clip(9)
        folder, emulator = self.board(text, drive={'night/deep/old.odrg': data})
        card = lambda row: row.get('playlist') == 'night' and row.get('external') is True
        card_night = next(row for row in self.answered(emulator, 'list', lambda reply: any(card(row) for row in reply.get('items', [])))['items'] if card(row))
        card_deep = next(row for row in self.listed(emulator, card_night['id']) if row.get('playlist') == 'night/deep')
        old = next(row for row in self.listed(emulator, card_deep['id']) if row.get('file') == 'night/deep/old.odrg')
        found = support.run('move-out', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 1, 'enter': [[card_night['id'], 'night'], [card_deep['id'], 'night/deep']], 'id': old['id'], 'storage': 'internal'}).seen
        self.assertEqual(found['cardFolders'], ['', 'night', 'night/deep'])
        self.assertIn('External /night/deep/old.odrg \u2192 Internal /old.odrg', found['preview'])
        self.assertIn('Moved 1 of 1', found['message'])
        self.assertFalse((self.card / 'night' / 'deep' / 'old.odrg').exists())
        self.assertEqual((folder / 'old.odrg').read_bytes(), data)
        self.assertTrue((folder / '2' / 'deep.odrg').exists())

    def test_a_selected_folder_of_the_boards_storage_is_not_called_the_cards(self):
        folder, emulator = self.board()
        found = support.run('downloads', address=f'127.0.0.1:{emulator.port}', settings={'rows': 1, 'folders': ['shows']}).seen
        self.assertTrue(found['deleteDisabled'])
        self.assertEqual(found['deleteTitle'], "Delete selected removes internal animations; clear the folders and the card's files from the selection.")
        self.assertIn('Saved the backup', found['message'])


if __name__ == '__main__':
    unittest.main()

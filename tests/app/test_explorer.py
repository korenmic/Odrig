"""The explorer of the shared app: a folder of the card made, and a file moved into it."""

import json
import pathlib
import tempfile
import unittest

from odrig import catalog

from tests.core import support as core_support
from tests.emulator import support as emulator_support
from . import support
from .test_target import entered


class Explorer(unittest.TestCase):
    def card(self):
        folder = emulator_support.installed(pathlib.Path(entered(self, tempfile.TemporaryDirectory()), 'show'), {
            'mapping.json': core_support.mapping_texts()['legs-2'],
            'show.json': json.dumps({'version': 1, 'brightness': 32, 'items': [
                {'id': 1, 'file': 'held.odrg'}, {'id': 2, 'file': 'face.odrg'}, {'id': 3, 'cycle': [1], 'seconds': 5}]}),
            'held.odrg': core_support.clip(1, 60, 6, durations=(20,) * 3, compressed=False),
            'face.odrg': core_support.clip(2, 60, 6, durations=(20,) * 3, compressed=False),
        })
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        drive = top / 'odrig'
        old = drive / 'night' / 'deep' / 'old.odrg'
        old.parent.mkdir(parents=True)
        old.write_bytes((folder / 'held.odrg').read_bytes())
        _, refused = catalog.rebuild(catalog.Storage(drive, drive=True), names=['night/deep/old.odrg'], canvas=(60, 6))
        self.assertEqual(refused, [])
        emulator = entered(self, emulator_support.Emulator(folder, '--drive', top))
        return folder, drive, emulator

    def test_a_folder_is_made_and_an_internal_file_moved_into_it_with_its_settings(self):
        folder, drive, emulator = self.card()
        item = {'id': 2, 'file': 'face.odrg'}
        data = (folder / item['file']).read_bytes()
        self.assertEqual(json.loads(emulator.command(f'brightness {item["id"]} 9 save')), {'ok': True})
        found = support.run('explore', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 2, 'folder': 'clocks', 'id': item['id']}).seen
        self.assertEqual(found['where'], 'In External /')
        self.assertIn('Made the folder External /clocks', found['made'])
        self.assertIn('1 selected: 1 in Internal storage, 0 in External storage', found['summary'])
        self.assertIn(f'Internal /{item["file"]} → External /clocks/{item["file"]}', found['preview'])
        self.assertEqual(found['go'], 'Move 1 file')
        self.assertIn('Moved 1 of 1', found['message'])
        self.assertEqual((drive / 'clocks' / item['file']).read_bytes(), data)
        listed = json.loads(emulator.command('list'))['items']
        self.assertNotIn(item['id'], [row['id'] for row in listed if row.get('external') is False])
        clocks = next(row for row in listed if row.get('playlist') == 'clocks')
        moved = json.loads(emulator.command(f'list in {clocks["id"]}'))['items']
        self.assertEqual([row['file'] for row in moved], [f'clocks/{item["file"]}'])
        self.assertEqual(json.loads(emulator.command(f'saved {moved[0]["id"]}'))['brightness'], 9)
        self.assertEqual(catalog.read(catalog.Storage(drive, drive=True)).state, 'ok')


    def test_a_file_of_a_writable_card_is_selected_for_a_move_but_not_for_delete_selected(self):
        folder, drive, emulator = self.card()
        found = support.run('explore', address=f'127.0.0.1:{emulator.port}', settings={'rows': 2, 'selectAll': True}).seen
        self.assertEqual(found['summary'], '1 selected: 0 in Internal storage, 1 in External storage.')
        self.assertTrue(found['deleteDisabled'])
        self.assertFalse(found['moveDisabled'])


if __name__ == '__main__':
    unittest.main()

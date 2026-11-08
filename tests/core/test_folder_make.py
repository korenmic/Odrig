"""`folder make external <path>`: a real folder of the card, listed while it is empty."""

import pathlib
import unittest
import zlib

from odrig import catalog

from . import support
from .test_catalog_drive import card, drive_ids
from .test_catalog_writes import POWER_CUT, a_card, folder_of, run_on_card, upload_external
from .test_drive import SHOW, asked, replies
from .test_folders import every_level
from .test_playback import T0
from .test_playlist import loop_of

FILES = {'root.odrg': loop_of(2, 5), 'night/deep/old.odrg': loop_of(3, 6),
         'night/near.odrg': loop_of(3, 7), 'space room/old.odrg': loop_of(3, 8)}


def made(path, files=FILES, more=()):
    """Makes a folder on a card of these files: the replies, the card's files afterwards and
    whether the folder is there."""
    with a_card(card(files)) as top:
        run = support.start(SHOW, asked(0, f'folder make external {path}', *more), ['--drive', top])
        there = pathlib.Path(top, 'odrig', *path.replace('%20', ' ').split('/')).is_dir()
        return replies(run), folder_of(top), there


def levels(files):
    return {item.get('playlist') or item.get('file'): item for item in every_level(files)}


class Making(unittest.TestCase):
    def test_a_folder_at_the_root_is_made_and_listed_empty(self):
        answers, left, there = made('clocks')
        self.assertEqual(answers[0], {'ok': True, 'id': answers[0]['id'], 'made': True})
        self.assertTrue(there)
        listed = levels(left)
        self.assertEqual(listed['clocks']['files'], 0)
        self.assertEqual(listed['clocks']['id'], answers[0]['id'])
        found = catalog.read(catalog.MemoryStorage(left, drive=True))
        self.assertEqual(found.state, 'ok', found)
        self.assertEqual(found.marker.generation, 2)
        for path, data in FILES.items():
            self.assertEqual(left[path], data)
        self.assertEqual({path: ids for path, ids in drive_ids(left).items()}, drive_ids(card(FILES)))

    def test_folders_are_made_one_level_at_a_time_in_the_listing_order(self):
        answers, left, there = made('clocks', more=('folder make external clocks/message', 'folder make external night/aaa',
                                                     'folder make external night/zzz', 'folder make external space%20room/mid'))
        self.assertTrue(all(answer['ok'] and answer['made'] for answer in answers), answers)
        found = catalog.read(catalog.MemoryStorage(left, drive=True))
        self.assertEqual(found.state, 'ok', found)
        paths = [folder.path for folder in found.index.folders]
        self.assertEqual(paths, ['', 'clocks', 'clocks/message', 'night', 'night/aaa', 'night/deep', 'night/zzz', 'space room', 'space room/mid'])
        listed = levels(left)
        for path in ('clocks/message', 'night/aaa', 'night/zzz', 'space room/mid'):
            self.assertEqual(listed[path]['files'], 0, path)
        self.assertEqual(listed['night/deep/old.odrg']['bytes'], len(FILES['night/deep/old.odrg']))

    def test_a_folder_the_index_has_is_answered_without_a_change(self):
        answers, left, _ = made('night', more=('folder make external clocks', 'folder make external clocks'))
        self.assertEqual(answers[0], {'ok': True, 'id': drive_folder_id(card(FILES), 'night'), 'made': False})
        self.assertTrue(answers[1]['made'])
        self.assertEqual(answers[2], {'ok': True, 'id': answers[1]['id'], 'made': False})
        self.assertEqual(catalog.read(catalog.MemoryStorage(left, drive=True)).marker.generation, 2)

    def test_refusals(self):
        cases = {'gone/new': 'unknown-id', 'root.odrg': 'bad-argument', 'night/near.odrg': 'bad-argument',
                 'Night': 'in-use', '../up': 'bad-argument', 'a/b/c/d': 'bad-argument', '.hidden': 'bad-argument',
                 'night/': 'bad-argument', '': 'bad-argument'}
        for path, error in cases.items():
            with self.subTest(path=path):
                answers, left, _ = made(path)
                self.assertEqual(answers[0], {'ok': False, 'error': error})
                self.assertEqual(left, card(FILES))
        answers, _, _ = made('x', more=('folder make internal x', 'folder make', 'folder make external a b'))
        self.assertEqual([answer.get('error') for answer in answers[1:]], ['unsupported', 'bad-argument', 'bad-argument'])

    def test_an_upload_into_an_empty_folder_becomes_its_first_file(self):
        data = loop_of(4, 9)
        with a_card(card(FILES)) as top:
            run = support.start(SHOW, [support.line(0, 'folder make external clocks'), *upload_external('clocks/face.odrg', data, T0)], ['--drive', top])
            self.assertTrue(replies(run)[0]['made'], replies(run)[0])
            self.assertTrue(replies(run)[-1]['ok'], replies(run)[-1])
            after = folder_of(top)
        self.assertEqual(after['clocks/face.odrg'], data)
        found = catalog.read(catalog.MemoryStorage(after, drive=True))
        self.assertEqual(found.state, 'ok', found)
        self.assertEqual(levels(after)['clocks']['files'], 1)

    def test_an_upload_makes_again_an_empty_folder_removed_from_the_card(self):
        data = loop_of(4, 9)
        _, left, _ = made('clocks', more=('folder make external clocks/message',))
        with a_card(left) as top:
            self.assertFalse(pathlib.Path(top, 'odrig', 'clocks').exists())
            run = support.start(SHOW, upload_external('clocks/message/hello.odrg', data, T0), ['--drive', top])
            self.assertTrue(replies(run)[-1]['ok'], replies(run)[-1])
            after = folder_of(top)
        self.assertEqual(after['clocks/message/hello.odrg'], data)
        self.assertNotIn('catalog.do', after)
        self.assertEqual(catalog.read(catalog.MemoryStorage(after, drive=True)).state, 'ok')

    def test_a_host_without_folders_is_unsupported(self):
        with a_card(card(FILES)) as top:
            run = support.start(SHOW, asked(0, 'folder make external clocks'), ['--drive', top, '--no-folders'])
        self.assertEqual(replies(run)[0], {'ok': False, 'error': 'unsupported'})

    def test_a_read_only_card_is_refused(self):
        with a_card(card(FILES)) as top:
            run = support.start(SHOW, asked(0, 'folder make external clocks'), ['--drive', top, '--drive-read-only'])
        self.assertEqual(replies(run)[0], {'ok': False, 'error': 'read-only'})

    def test_an_empty_folder_plays_nothing_and_the_root_plays(self):
        answers, left, _ = made('clocks')
        folder = answers[0]['id']
        with a_card(left) as top:
            run = support.start(SHOW, asked(0, f'play {folder}', 'status', 'list'), ['--drive', top])
        answers = replies(run)
        self.assertIn(answers[0].get('error'), (None, 'unknown-id', 'unavailable'))
        self.assertTrue(answers[1]['ok'])
        self.assertIn({'id': folder, 'playlist': 'clocks', 'external': True, 'files': 0},
                      [{key: item[key] for key in ('id', 'playlist', 'external', 'files') if key in item} for item in answers[2]['items']])

    def test_making_survives_a_power_cut_at_every_storage_call(self):
        start = card(FILES)
        outcomes = set()
        for number in range(1, 80):
            with a_card(start) as top, support.installed(SHOW) as show:
                result = support.host('session', show, support.CHECK_FIRST, '--drive', top, '--cut-at', number,
                                      stdin=(support.line(T0, 'folder make external clocks') + '\n').encode('ascii'))
                if result.status != POWER_CUT:
                    self.assertEqual(result.status, 0, result.out[-300:])
                    break
                support.session(show, asked(0, 'status'), ['--drive', top])
                after = folder_of(top)
            found = catalog.read(catalog.MemoryStorage(after, drive=True))
            self.assertEqual(found.state, 'ok', number)
            outcomes.add(found.marker.generation)
            for entry in found.entries:
                self.assertEqual(zlib.crc32(after[entry.name]), entry.crc, number)
            self.assertEqual('clocks' in [folder.path for folder in found.index.folders], found.marker.generation == 2, number)
        else:
            self.fail('storage operation count exceeded the test bound')
        self.assertEqual(outcomes, {1, 2})

    def test_the_last_file_out_of_a_folder_with_an_empty_sub_folder_keeps_it(self):
        answers, left, _ = made('night/deep/empty')
        self.assertTrue(answers[0]['made'])
        removed = drive_ids(left)['night/deep/old.odrg']
        with a_card(left) as top:
            run = support.start(SHOW, asked(0, f'remove {removed}'), ['--drive', top])
            self.assertEqual(replies(run)[0], {'ok': True})
            after = folder_of(top)
        found = catalog.read(catalog.MemoryStorage(after, drive=True))
        self.assertEqual(found.state, 'ok', found)
        listed = levels(after)
        self.assertEqual(listed['night/deep']['files'], 0)
        self.assertEqual(listed['night/deep/empty']['files'], 0)


def drive_folder_id(files, path):
    index = catalog.read(catalog.MemoryStorage(files, drive=True)).index
    return next(folder.id for folder in index.folders if folder.path == path)


if __name__ == '__main__':
    unittest.main()

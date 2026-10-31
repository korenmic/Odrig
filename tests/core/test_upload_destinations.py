"""Managed creation in a browsed external folder preserves bytes and index identity."""

import unittest
import urllib.parse
import zlib

from odrig import catalog, odrg, odrgx

from . import support
from .test_catalog_drive import card, drive_ids
from .test_catalog_writes import POWER_CUT, a_card, folder_of, run_on_card, upload_external
from .test_drive import SHOW, asked, replies
from .test_folders import every_level
from .test_playback import T0
from .test_playlist import CANVAS, loop_of

FILES = {'root.odrg': loop_of(2, 5), 'night/deep/old.odrg': loop_of(3, 6),
         'night/near.odrg': loop_of(3, 7), 'space room/old.odrg': loop_of(3, 8)}


def guarded(name, data, at=T0):
    lines = upload_external(urllib.parse.quote(name, safe='/'), data, at)
    lines.insert(1, support.line(at, 'upload expect 00000000'))
    return lines


class Destinations(unittest.TestCase):
    def test_nested_create_has_identical_bytes_and_pc_catalog(self):
        start = card(FILES)
        for path in ('night/deep/new.odrg', 'space room/new.odrg', 'new.odrg'):
            with self.subTest(path=path):
                data = loop_of(4, 9)
                run, left = run_on_card(start, guarded(path, data))
                self.assertTrue(replies(run)[-1]['ok'], replies(run)[-1])
                self.assertEqual(left[path], data)
                found = catalog.read(catalog.MemoryStorage(left, drive=True))
                self.assertEqual(found.state, 'ok')
                self.assertEqual(found.marker.generation, 2)
                self.assertEqual(found.entry(path), catalog.entry_of(path, data, canvas=CANVAS))
                for old, content in FILES.items():
                    self.assertEqual(left[old], content)
                    self.assertEqual(drive_ids(left)[old], drive_ids(start)[old])
                listed = every_level(left)
                self.assertEqual(len([row for row in listed if row.get('file') == path]), 1)

    def test_nested_container_preserves_bytes_and_frame_type(self):
        payload = loop_of(4, 9)
        ms = sum(duration for duration, _ in odrg.decode(payload).records)
        data = odrgx.wrap(1, *CANVAS, ms, payload)
        run, left = run_on_card(card(FILES), guarded('night/new.odrgx', data))
        self.assertTrue(replies(run)[-1]['ok'], replies(run)[-1])
        self.assertEqual(left['night/new.odrgx'], data)
        found = catalog.read(catalog.MemoryStorage(left, drive=True))
        self.assertEqual(found.entry('night/new.odrgx').type, 'frames')

    def test_nested_explicit_replacement_keeps_id(self):
        start = card(FILES)
        data = loop_of(4, 9)
        run, left = run_on_card(start, upload_external('night/deep/old.odrg', data, T0))
        self.assertTrue(replies(run)[-1]['ok'], replies(run)[-1])
        self.assertEqual(drive_ids(left), drive_ids(start))
        self.assertEqual(left['night/deep/old.odrg'], data)

    def test_nested_publication_recovers_at_every_storage_cut(self):
        start = card(FILES)
        path, data = 'night/deep/new.odrg', loop_of(4, 9)
        script = guarded(path, data)
        outcomes = set()
        for number in range(1, 200):
            with a_card(start) as top, support.installed(SHOW) as show:
                result = support.host('session', show, support.CHECK_FIRST, '--drive', top, '--cut-at', number,
                                      stdin=''.join(line+'\n' for line in script).encode('ascii'))
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
            self.assertEqual(len([row for row in every_level(after) if row.get('file') == path]),
                             int(found.marker.generation == 2), number)
        else:
            self.fail('storage operation count exceeded the test bound')
        self.assertEqual(outcomes, {1, 2})

    def test_absence_guard_refuses_root_collision_without_changing_files(self):
        start = card(FILES)
        script = asked(0, 'upload begin external root.odrg 100', 'upload expect 00000000')
        run, left = run_on_card(start, script)
        self.assertEqual(replies(run)[1], {'ok': False, 'error': 'stale'})
        self.assertEqual(left, start)

    def test_absence_guard_refuses_nested_collision(self):
        start = card(FILES)
        run, left = run_on_card(start, asked(0, 'upload begin external night/deep/old.odrg 100', 'upload expect 00000000'))
        self.assertEqual(replies(run)[1], {'ok': False, 'error': 'stale'})
        self.assertEqual(left, start)

    def test_missing_folder_is_not_the_root(self):
        start = card(FILES)
        run, left = run_on_card(start, asked(0, 'upload begin external gone/new.odrg 100'))
        self.assertEqual(replies(run)[0], {'ok': False, 'error': 'unknown-id'})
        self.assertEqual(left, start)

    def test_cancelled_nested_upload_preserves_catalog_and_other_files(self):
        start = card(FILES)
        run, left = run_on_card(start, asked(0, 'upload begin external night/new.odrg 100', 'upload expect 00000000', 'upload cancel'))
        self.assertTrue(all(reply['ok'] for reply in replies(run)), replies(run))
        self.assertEqual(left, start)

    def test_unsafe_paths_are_refused_before_storage(self):
        for path in ('../new.odrg', '/new.odrg', 'night//new.odrg', 'night/./new.odrg',
                     'night/%2e%2e/new.odrg', 'night%5cnew.odrg', 'night/%00.odrg'):
            with self.subTest(path=path):
                start = card(FILES)
                run, left = run_on_card(start, asked(0, f'upload begin external {path} 100'))
                self.assertEqual(replies(run)[0]['error'], 'bad-argument')
                self.assertEqual(left, start)

    def test_removal_ends_external_transaction_before_reinsertion(self):
        script = asked(0, 'upload begin external new.odrg 100')
        script += ['drive pull'] + asked(20, 'status') + ['drive plug']
        script += [f'poll {T0+40+20*i}' for i in range(40)]
        script += asked(900, 'upload data 0 AQ', 'upload end 00000000')
        run, left = run_on_card(card(FILES), script)
        self.assertEqual(replies(run)[-2]['error'], 'no-upload')
        self.assertEqual(replies(run)[-1]['error'], 'no-upload')
        self.assertNotIn('new.odrg', left)

    def test_read_only_nested_target_does_not_fallback(self):
        run, left = run_on_card(card(FILES), asked(0, 'upload begin external night/new.odrg 100'), ['--drive-read-only'])
        self.assertEqual(replies(run)[0]['error'], 'read-only')
        self.assertEqual(left, card(FILES))

    def test_quiet_timeout_crosses_the_low_timestamp_wrap(self):
        start = (1 << 32) - 20
        script = [support.line(start, 'upload begin external new.odrg 100'),
                  support.line(start + 30, 'upload data 0 AQ'),
                  support.line(start + 60031, 'upload data 1 AQ')]
        run, left = run_on_card(card(FILES), script)
        self.assertEqual(replies(run)[1], {'ok': True, 'received': 1})
        self.assertEqual(replies(run)[2], {'ok': False, 'error': 'no-upload'})
        self.assertNotIn('new.odrg', left)

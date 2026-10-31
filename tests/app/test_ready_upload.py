"""Ready-made animations use their original bytes through the shared app."""

import pathlib
import tempfile
import unittest

from odrig import catalog, odrg, odrgx

from tests.emulator import support as emulator_support
from . import support
from .test_target import entered
from .test_upload import target, taken


class ReadyUploads(unittest.TestCase):
    def test_a_ready_container_is_sent_without_reencoding(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        payload = (folder/'hello.odrg').read_bytes()
        loop = sum(ms for ms, _ in odrg.decode(payload).records)
        data = odrgx.wrap(1, 60, 6, loop, payload)
        (media/'ready.odrgx').write_bytes(data)
        found = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 2, 'file': 'ready.odrgx'}, media=media).seen
        self.assertIn('Uploaded as animation', found['message'])
        self.assertEqual((folder/'ready.odrgx').read_bytes(), data)

    def test_an_internal_id_claimed_during_begin_never_receives_data(self):
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        with emulator_support.example_show() as folder:
            (media/'ready.odrg').write_bytes((folder/'hello.odrg').read_bytes())
        replies = target(begin=(200, '{"ok":true,"chunk":1500,"replacing":true}\n'), data=taken)
        with support.StandIn(replies) as stand_in:
            found = support.run('ready-upload', address=stand_in.address,
                                settings={'rows': 2, 'file': 'ready.odrg'}, media=media).seen
            lines = [line for _, line in stand_in.lines if line.startswith(b'upload data ')]
        self.assertNotIn('Uploaded', found['message'])
        self.assertEqual(lines, [])

    def card(self):
        folder = entered(self, emulator_support.example_show())
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        drive = top / 'odrig'
        old = drive / 'night' / 'deep' / 'old.odrg'
        old.parent.mkdir(parents=True)
        data = (folder/'hello.odrg').read_bytes()
        old.write_bytes(data)
        _, refused = catalog.rebuild(catalog.Storage(drive, drive=True), names=['night/deep/old.odrg'], canvas=(60, 6))
        self.assertEqual(refused, [])
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media/'ready.odrg').write_bytes(data)
        emulator = entered(self, emulator_support.Emulator(folder, '--drive', top))
        return folder, drive, media, data, emulator

    def test_nested_external_upload_uses_browsing_and_survives_navigation(self):
        folder, drive, media, data, emulator = self.card()
        found = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 2, 'path': 'night/deep', 'file': 'ready.odrg', 'navigate': True}, media=media).seen
        self.assertEqual(found['default'], 'external')
        self.assertFalse(found['externalDisabled'])
        self.assertEqual(found['destination'], 'External /night/deep/ready.odrg')
        self.assertEqual(found['afterNavigation'], found['destination'])
        self.assertIn('Uploaded to the card', found['message'])
        self.assertEqual((drive/'night/deep/ready.odrg').read_bytes(), data)
        self.assertFalse((folder/'ready.odrg').exists())
        self.assertFalse((drive/'ready.odrg').exists())

    def test_internal_choice_from_folder_visibly_uses_flat_root(self):
        folder, drive, media, data, emulator = self.card()
        found = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 2, 'path': 'night/deep', 'file': 'ready.odrg', 'store': 'internal'}, media=media).seen
        self.assertEqual(found['destination'], 'Internal /ready.odrg')
        self.assertIn('flat root', found['reason'])
        self.assertIn('Uploaded as animation', found['message'])
        self.assertEqual((folder/'ready.odrg').read_bytes(), data)
        self.assertFalse((drive/'night/deep/ready.odrg').exists())

    def test_existing_nested_name_is_not_replaced(self):
        _, drive, media, data, emulator = self.card()
        found = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 2, 'path': 'night/deep', 'file': 'ready.odrg', 'basename': 'old.odrg'}, media=media).seen
        self.assertIn('already exists', found['message'])
        self.assertEqual((drive/'night/deep/old.odrg').read_bytes(), data)

    def test_preparation_and_destination_invariants(self):
        found = support.run('ready-checks').seen
        self.assertGreaterEqual(len(found), 20)
        self.assertTrue(all(found.values()), found)

    def test_internal_fallback_uploads_original_bytes_without_conversion(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        data = (folder / 'hello.odrg').read_bytes()
        (media / 'ready.odrg').write_bytes(data)
        found = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 2, 'file': 'ready.odrg'}, media=media).seen
        self.assertIn('default', found, found)
        self.assertEqual(found['default'], 'internal')
        self.assertTrue(found['externalDisabled'])
        self.assertEqual(found['destination'], 'Internal /ready.odrg')
        self.assertIn('Uploaded as animation', found['message'])
        self.assertEqual((folder / 'ready.odrg').read_bytes(), data)

    def test_a_renamed_video_is_refused_before_upload(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media / 'fake.odrg').write_bytes(b'not an animation' * 3)
        found = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 2, 'file': 'fake.odrg'}, media=media).seen
        self.assertIsNone(found['facts'])
        self.assertIn('animation', found['message'].lower())
        self.assertFalse((folder / 'fake.odrg').exists())

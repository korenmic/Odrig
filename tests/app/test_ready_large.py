"""Large encoded movies are prepared without expanding their complete frame body."""
import json
import pathlib
import tempfile
import unittest

from odrig import catalog
from tests.emulator import support as emulator_support
from tests.emulator.test_ready_content import ROOT, SPACE_SCAN, SPACE_SHA
from . import support
from .test_target import entered


class LargeReadyFile(unittest.TestCase):
    def test_the_actual_space_scan_has_bounded_preflight_and_original_encoded_bytes(self):
        found = support.run('ready-large', settings={'file': SPACE_SCAN.name}, media=SPACE_SCAN.parent).seen
        self.assertEqual(found, {'bytes': 34410601, 'sha256': SPACE_SHA, 'prefixReads': [[0, 36]],
                                'encodedReads': 1, 'previewSafe': False, 'frames': 18004, 'materializedFrames': False})

    def test_the_shared_app_reuses_the_large_files_known_preview(self):
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        show = top/'show'
        show.mkdir()
        (show/'mapping.json').write_bytes((ROOT/'mapping/legs-20.json').read_bytes())
        (show/'show.json').write_text(json.dumps({'version': 1, 'brightness': 40, 'items': []}), encoding='utf-8', newline='\n')
        drive = top/'card'/'odrig'
        (drive/'space').mkdir(parents=True)
        (drive/'space/anchor.odrgx').write_bytes((ROOT/'collection/card/clocks/message/v7-consciousness.odrgx').read_bytes())
        _, refused = catalog.rebuild(catalog.Storage(drive, drive=True), names=['space/anchor.odrgx'], canvas=(60, 60))
        self.assertEqual(refused, [])
        emulator = entered(self, emulator_support.Emulator(show, '--drive', drive.parent))
        found = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 0, 'file': SPACE_SCAN.name, 'path': 'space', 'send': False}, media=SPACE_SCAN.parent).seen
        self.assertEqual(found['default'], 'external')
        self.assertEqual(found['destination'], 'External /space/space-scan-10x.odrg')
        self.assertIn('without conversion', found['facts'])
        self.assertIn('Preview from the animation catalog', found['preview'])

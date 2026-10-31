"""The supplied page is the independent caption/timing oracle for the widgets."""
import base64
import json
import tempfile
import pathlib
import unittest

from tests.app.message_review import SOURCE, capture


class MessageSource(unittest.TestCase):
    def test_all_source_captions_and_stopped_motion_are_reviewed_at_fixed_times(self):
        with tempfile.TemporaryDirectory(prefix='odrig-message-review-') as directory:
            result = capture(pathlib.Path(directory))
        manifest = json.loads((SOURCE / 'source/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(result['samples']), 58)
        for item in manifest['files']:
            samples = [s for s in result['samples'] if s['tab'] == item['tab']]
            at = 0
            for index, caption in enumerate(item['captions']):
                sample, = [s for s in samples if s['t'] == at + 700]
                self.assertEqual((sample['section'], sample['index'], sample['caption']),
                                 (item['tab'], index, caption['text']))
                self.assertAlmostEqual(sample['elapsed'], (at + 700) / 1000, places=6)
                self.assertEqual(len(base64.b64decode(sample['rgb'])), 10800)
                self.assertEqual(len(base64.b64decode(sample['portable'])), 10800)
                at += caption['duration']
        stop = [s for s in result['samples'] if s['tab'] == 1 and s['t'] in (21900, 23300)]
        self.assertEqual(len(stop), 2)
        self.assertEqual(stop[0]['digits'], stop[1]['digits'])
        for key in ('rgb', 'portable'):
            self.assertEqual(base64.b64decode(stop[0][key])[30*180:],
                             base64.b64decode(stop[1][key])[30*180:])

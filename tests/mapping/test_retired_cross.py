import json
import unittest

from tests.app import support as browser
from tests.core import support
from tests.emulator.support import Emulator
from .test_core import PINS, answers, crossed_files, files, set_line


class RetiredCrossControls(unittest.TestCase):
    def test_retired_operations_cannot_change_the_mapping(self):
        for source in (files(), crossed_files()):
            with self.subTest(saved_custom_geometry=source != files()):
                run, left = support.start_and_keep(source, [
                    support.line(1000, 'mapping cross on'),
                    support.line(1001, 'mapping cross off'),
                    support.line(1002, 'mapping get')])
                replies = answers(run)
                self.assertEqual(replies[:2], [dict(ok=False, error='bad-argument')] * 2)
                self.assertNotIn('cross', replies[2])
                self.assertEqual(left, source)

    def test_pin_save_preserves_generic_custom_strip_order_and_starts(self):
        source = files()
        mapping = json.loads(source['mapping.json'])
        leg = mapping['legs'][3]
        leg.update(first_led='top', columns=[12, 10, 11], starts=['top', 'bottom', 'bottom'])
        source['mapping.json'] = json.dumps(mapping).encode()
        run, left = support.start_and_keep(source, [support.line(1000, set_line(PINS[::-1])),
                                                   support.line(1001, 'mapping get')])
        self.assertEqual(answers(run)[0], dict(ok=True))
        self.assertEqual(answers(run)[1]['pins'], PINS[::-1])
        saved = json.loads(left['mapping.json'])
        self.assertEqual([{k: v for k, v in item.items() if k != 'pin'} for item in saved['legs']],
                         [{k: v for k, v in item.items() if k != 'pin'} for item in mapping['legs']])

    def test_settings_and_app_api_no_longer_offer_the_retired_control(self):
        folder = self.enterContext(support.installed(files()))
        emulator = self.enterContext(Emulator(folder))
        seen = browser.run('mapping-retired', address=f'127.0.0.1:{emulator.port}').seen
        self.assertEqual(seen, dict(checkbox=False, api=False, clientApi=False))

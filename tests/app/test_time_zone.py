import base64
import struct
import unittest
import zlib

from tests.core import support as core_support
from tests.core.test_civil_time import snapshot, replies
from . import support


def run(action, zone='UTC'):
    return support.run('time-zone', settings=dict(action=action, zone=zone)).seen


class PhoneZone(unittest.TestCase):
    def test_utc_has_exact_canonical_core_bytes_and_crc(self):
        seen = run('snapshot')
        data = base64.b64decode(seen['base64'])
        self.assertEqual(data, snapshot())
        self.assertEqual(seen['revision'], f'{zlib.crc32(data):08x}')

    def test_named_zone_transitions_agree_with_phone_intl_and_the_native_core(self):
        for zone in ('Asia/Jerusalem', 'America/New_York', 'Australia/Lord_Howe'):
            with self.subTest(zone=zone):
                seen = run('snapshot', zone)
                data = base64.b64decode(seen['base64'])
                self.assertLessEqual(len(data), 1500)
                count = struct.unpack_from('<H', data, 18)[0]
                self.assertGreater(count, 100)
                files = {**core_support.example_show(), 'timezone.bin': data}
                script = []
                for check in seen['checks']:
                    script.extend([core_support.line(0, f'time set {check["utc"]} {seen["revision"]}'),
                                   core_support.line(0, 'time')])
                values = replies(core_support.start(files, script))
                self.assertTrue(all(row['ok'] for row in values))
                self.assertEqual([row['offset'] for row in values[1::2]], [check['offset'] for check in seen['checks']])

    def test_maximum_snapshot_is_complete_and_not_truncated(self):
        seen = run('maximum')
        data = base64.b64decode(seen['base64'])
        self.assertEqual(len(data), 1500)
        self.assertEqual(struct.unpack_from('<H', data, 18)[0], 276)

    def test_unsupported_names_offsets_and_transition_counts_fail_explicitly(self):
        seen = run('errors')
        self.assertEqual([entry['name'] for entry in seen], ['ZoneFailure'] * 4)
        self.assertTrue(all(entry['message'] for entry in seen))

    def test_full_zone_preparation_leaves_the_browser_event_loop_running(self):
        seen = run('worker', 'Asia/Jerusalem')
        self.assertGreater(seen['ticks'], 1)
        self.assertLessEqual(len(base64.b64decode(seen['base64'])), 1500)

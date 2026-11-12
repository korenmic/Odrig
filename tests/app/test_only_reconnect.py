import threading
import time
import unittest

from tests.emulator import support as emulator_support
from tests.emulator.only_assets import installed_only
from . import support
from .test_target import entered


class OnlyNativeReconnect(unittest.TestCase):
    def test_delayed_and_dropped_native_reply_keeps_only_rows_keys_and_dom(self):
        folder, card, _ = installed_only(self)
        emulator = entered(self, emulator_support.Emulator(folder, '--drive', card))
        fail_next = threading.Event()

        def reply(line):
            if line == b'status':
                if fail_next.is_set():
                    fail_next.clear()
                    return 500, ''
                time.sleep(.15)
            return 200, emulator.command(line.decode('utf-8')).decode('utf-8')

        proxy = entered(self, support.StandIn(reply))
        boundary = []

        def drop():
            boundary.append(len(proxy.lines))
            fail_next.set()

        seen = support.run('only-reconnect', address=proxy.address, steps=[drop]).seen
        self.assertEqual(seen['stale'], dict(retained=True, disabled=True, marked=True))
        self.assertNotIn('', seen['paths'])
        self.assertEqual((seen['level'], seen['mode']), ('clocks', 'only'))
        for flag in ('sameFiles', 'sameKeys', 'sameRow'):
            self.assertTrue(seen[flag], flag)
        later = [line for _, line in proxy.lines[boundary[0]:]]
        self.assertFalse(any(line.startswith(b'catalog page ') for line in later), later)
        lists = [line for line in later if line.startswith(b'list')]
        self.assertTrue(lists, later)
        self.assertTrue(all(line.startswith(b'list in ') for line in lists), lists)

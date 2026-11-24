import json
import pathlib
import subprocess
import unittest


class AutomaticClocksRecovery(unittest.TestCase):
    def test_production_recovery_keeps_unresolved_clocks_out_of_root(self):
        helper = pathlib.Path(__file__).with_name('only_recovery.cjs')
        for case in ('missing', 'initial', 'unknown', 'damaged', 'loading', 'busy'):
            with self.subTest(case=case):
                done = subprocess.run(['node', str(helper), case], capture_output=True, text=True, timeout=10)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                seen = json.loads(done.stdout)
                self.assertNotIn('', seen['paths'])
                self.assertEqual(seen['level'], dict(path='clocks', id=None))
                self.assertTrue(seen['unavailable'])

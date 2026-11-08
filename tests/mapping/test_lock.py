import json
import socket
import threading
import unittest

from tests.app import support as browser
from tests.core import support
from tests.emulator.support import Emulator
from .test_core import PINS, files


class MappingLock(unittest.TestCase):
    maxDiff = None
    def opened(self, pins=PINS):
        source = files()
        mapping = json.loads(source['mapping.json'])
        for leg, pin in zip(mapping['legs'], pins):
            leg['pin'] = pin
        source['mapping.json'] = json.dumps(mapping).encode()
        folder = self.enterContext(support.installed(source))
        return self.enterContext(Emulator(folder))

    def test_the_operators_choice_is_kept_through_hiding_leaving_a_new_start_and_a_reload(self):
        target = self.opened()
        seen = browser.run('mapping-lock', address=f'127.0.0.1:{target.port}', settings=dict(mode='kept')).seen
        self.assertEqual(seen, dict(afterHide=True, afterLeave=True, afterBegin=True, afterReload=True, locked=True, lockKept=True))
        self.assertEqual(json.loads(target.command('mapping get'))['pins'], PINS)

    def test_the_control_answers_without_a_board_and_says_why_edits_wait(self):
        with socket.socket() as unused:
            unused.bind(('127.0.0.1', 0))
            port = unused.getsockname()[1]
        seen = browser.run('mapping-lock', address=f'127.0.0.1:{port}', settings=dict(mode='noboard')).seen
        self.assertEqual(seen, dict(enabled=True, cancelKeepsLocked=True, unlocked=True, waits=True, stored=True))

    def test_a_choice_the_phone_cannot_keep_holds_for_the_run_and_is_said(self):
        target = self.opened()
        seen = browser.run('mapping-lock', address=f'127.0.0.1:{target.port}', settings=dict(mode='refused')).seen
        self.assertEqual(seen, dict(unlocked=True, said=True, lockedAfterReload=True))

    def test_a_stored_value_the_app_does_not_know_is_locked(self):
        target = self.opened()
        seen = browser.run('mapping-lock', address=f'127.0.0.1:{target.port}', settings=dict(mode='unknown')).seen
        self.assertEqual(seen, dict(locked=True, canEdit=False))

    def test_the_lock_is_a_checkbox_of_the_kept_value_with_or_without_a_board(self):
        want = dict(kind='checkbox', label='Lock mapping edits', checked=True, inPanel=True, keptWhileAsked=True, cancelKeeps=True, unchecked=True, stored=True)
        target = self.opened()
        self.assertEqual(browser.run('mapping-lock', address=f'127.0.0.1:{target.port}', settings=dict(mode='checkbox')).seen, want)
        with socket.socket() as unused:
            unused.bind(('127.0.0.1', 0))
            port = unused.getsockname()[1]
        self.assertEqual(browser.run('mapping-lock', address=f'127.0.0.1:{port}', settings=dict(mode='checkbox', noBoard=True)).seen, want)

    def test_default_lock_blocks_accidental_edits_and_photo_save_handler(self):
        target = self.opened(PINS[::-1])
        seen = browser.run('mapping-lock-default', address=f'127.0.0.1:{target.port}').seen
        seen['pins'] = json.loads(target.command('mapping get'))['pins']
        self.assertEqual(seen, dict(handlesDisabled=True, defaultsDisabled=True,
                                    photoAccepted=False, lifted=False, pins=PINS[::-1]))

    def test_confirm_cancel_and_escape_keep_edits_deliberate_and_leaving_or_hiding_keeps_the_choice(self):
        target = self.opened()
        seen = browser.run('mapping-lock', address=f'127.0.0.1:{target.port}').seen
        self.assertIn('Are you sure', seen.pop('question'))
        self.assertTrue(all(seen.values()), seen)
        self.assertEqual(json.loads(target.command('mapping get'))['pins'], [PINS[1], PINS[0], *PINS[2:]])

    def test_leaving_settings_for_another_target_closes_the_confirmation_unanswered(self):
        first = self.opened()
        other = self.opened(PINS[::-1])
        seen = browser.run('mapping-lock', address=f'127.0.0.1:{first.port}',
                           settings=dict(mode='target', other=f'127.0.0.1:{other.port}', first=PINS[-1])).seen
        self.assertEqual(seen, dict(locked=True, promptClosed=True, handlesDisabled=True))
        self.assertEqual(json.loads(first.command('mapping get'))['pins'], PINS)
        self.assertEqual(json.loads(other.command('mapping get'))['pins'], PINS[::-1])

    def test_a_lost_reply_and_the_reconnection_keep_the_choice_and_edits_come_back(self):
        target = self.opened()
        armed = threading.Event()
        def answer(line):
            if line == b'status' and armed.is_set():
                armed.clear()
                return 500, ''
            return 200, target.command(line.decode()).decode()
        proxy = self.enterContext(browser.StandIn(answer))
        seen = browser.run('mapping-lock', address=proxy.address, settings=dict(mode='disconnect'),
                           steps=[armed.set]).seen
        self.assertEqual(seen, dict(locked=False, canEdit=True))

    def test_photo_analysis_remains_available_but_apply_and_other_reading_require_unlock(self):
        target = self.opened(PINS[::-1])
        def unchanged():
            self.assertEqual(json.loads(target.command('mapping get'))['pins'], PINS[::-1])
        seen = browser.run('mapping-lock', address=f'127.0.0.1:{target.port}',
                           settings=dict(mode='photo'), steps=[unchanged]).seen
        self.assertEqual(seen, dict(analysisVisible=True, applyDisabled=True, otherDisabled=True, locked=True))
        self.assertEqual(json.loads(target.command('mapping get'))['pins'], PINS)

    def test_leaving_settings_cancels_a_mapping_save_queued_behind_a_reply(self):
        target = self.opened()
        armed = threading.Event()
        entered = threading.Event()
        release = threading.Event()
        def answer(line):
            if line == b'status' and armed.is_set():
                armed.clear()
                entered.set()
                if not release.wait(10):
                    return 500, ''
            return 200, target.command(line.decode()).decode()
        proxy = self.enterContext(browser.StandIn(answer))
        self.addCleanup(release.set)
        def blocked():
            self.assertTrue(entered.wait(8), 'status did not reach controlled peer')
        seen = browser.run('mapping-lock', address=proxy.address, settings=dict(mode='queued'),
                           steps=[armed.set, blocked, release.set]).seen
        self.assertEqual(seen, dict(locked=False, link='answers'))
        self.assertFalse(any(line.startswith(b'mapping set ') for _, line in proxy.lines))
        self.assertEqual(json.loads(target.command('mapping get'))['pins'], PINS)

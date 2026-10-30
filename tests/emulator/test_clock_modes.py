import json
import pathlib
import tempfile
import time
import unittest

from tests.core.test_clocks import CARD, CLOCK_FILES, SHOW4
from tests.core.test_drive import a_drive
from . import support


class ClockModes(unittest.TestCase):
    def setUp(self):
        root = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.folder = support.installed(root / 'show', SHOW4)
        self.top = support.entered(self, a_drive(CARD))
        self.emulator = support.entered(self, support.Emulator(self.folder, '--drive', self.top, tcp_port=0))

    def wait_for(self, predicate):
        deadline = time.monotonic() + 10
        while True:
            status = self.emulator.status()
            if predicate(status): return status
            if time.monotonic() > deadline: self.fail(f'expected clock state, got {status}')
            time.sleep(0.02)

    def only(self):
        self.assertEqual(json.loads(self.emulator.command('clocks only')), dict(ok=True))
        return self.wait_for(lambda state: state['clock_mode'] == 'only' and state['file'] in CLOCK_FILES)

    def test_mode_and_message_forms_reach_the_same_core_over_http_and_tcp_cli(self):
        target = ('--http', f'127.0.0.1:{self.emulator.port}')
        result = support.run_tool(*target, 'clocks', 'only')
        self.assertEqual((result.status, json.loads(result.out), result.err), (0, dict(ok=True), ''))
        status = self.wait_for(lambda state: state['file'] in CLOCK_FILES)
        self.assertEqual(status['clock_only'], dict(folder=60007, state='playing'))
        with support.Lines(self.emulator.tcp) as port:
            self.assertEqual(json.loads(port.ask('clocks message on')), dict(ok=True))
            self.assertEqual(json.loads(port.ask('status'))['clock_mode'], 'only')
        result = support.run_tool(*support.line_target(self.emulator), 'clocks', 'on')
        self.assertEqual((result.status, json.loads(result.out), result.err), (0, dict(ok=True), ''))
        status = self.emulator.status()
        self.assertEqual(status['clock_mode'], 'between')
        self.assertTrue(status['clock_message'])
        self.assertEqual((self.folder / 'clocks.txt').read_bytes(), b'odrig-clocks 2\nmode between\nmessage on\n')

    def test_only_survives_restart(self):
        self.only()
        self.emulator.stop()
        self.emulator = support.entered(self, support.Emulator(self.folder, '--drive', self.top, tcp_port=0))
        status = self.wait_for(lambda state: state['clock_mode'] == 'only' and state['file'] in CLOCK_FILES)
        self.assertEqual(status['playing'], status['clock_only']['folder'])

    def test_browsing_stays_open_but_outside_play_and_diagnostics_are_refused_on_both_transports(self):
        self.only()
        self.assertIn(1, [item['id'] for item in json.loads(self.emulator.command('list'))['items']])
        for command in ('play 1', 'play 60001', 'play all', 'mapping test on', 'mapping test snake 1'):
            self.assertEqual(json.loads(self.emulator.command(command)), dict(ok=False, error='in-use'))
            with support.Lines(self.emulator.tcp) as port:
                self.assertEqual(json.loads(port.ask(command)), dict(ok=False, error='in-use'))
        folder = self.emulator.status()['clock_only']['folder']
        self.assertEqual(json.loads(self.emulator.command(f'play {folder}')), dict(ok=True))
        with support.Lines(self.emulator.tcp) as port:
            self.assertEqual(json.loads(port.ask(f'play {folder}')), dict(ok=True))
        self.assertEqual(self.emulator.status()['clock_mode'], 'only')

    def test_excluding_and_reincluding_faces_stays_in_only_without_changing_the_card(self):
        folder = pathlib.Path(self.top, 'odrig')
        before = {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
        self.only()
        with support.Lines(self.emulator.tcp) as port:
            self.assertEqual(json.loads(port.ask('ignore 60007 1')), dict(ok=True))
        status = self.wait_for(lambda state: state['clock_only']['state'] == 'no-clocks')
        self.assertIsNone(status['animation'])
        self.assertEqual(json.loads(self.emulator.command('play 1')), dict(ok=False, error='in-use'))
        self.assertEqual(json.loads(self.emulator.command('ignore 60007 0')), dict(ok=True))
        self.wait_for(lambda state: state['file'] in CLOCK_FILES)
        self.assertEqual({p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}, before)


class DeliveredMessages(unittest.TestCase):
    def test_real_assets_manual_play_and_ancestor_inclusion_on_live_emulator(self):
        from tests.core.test_mini import files_for
        from tests.core.test_clocks import clock_of
        from tests.core.test_clock_modes import mode_file
        root = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        source = {**files_for(), 'clocks.txt': mode_file('only')}
        folder = support.installed(root / 'show', source)
        assets = support.ROOT / 'collection/card/clocks/message'
        card = {'clocks/c.odrgx': clock_of(canvas=(60, 60)),
                **{'clocks/message/' + p.name: p.read_bytes() for p in assets.glob('v7-*.odrgx')}}
        self.assertEqual(len(card), 8)
        top = support.entered(self, a_drive(card))
        emulator = support.entered(self, support.Emulator(folder, '--drive', top, tcp_port=0))
        def wait_for(predicate):
            end = time.monotonic() + 10
            while time.monotonic() < end:
                state = emulator.status()
                if predicate(state): return state
                time.sleep(0.02)
            self.fail(f'expected state; got {state}')
        state = wait_for(lambda s: s['file'] == 'clocks/c.odrgx')
        clocks = state['clock_only']['folder']
        items = json.loads(emulator.command(f'list in {clocks}'))['items']
        messages, = [i['id'] for i in items if i.get('playlist') == 'clocks/message']
        items = json.loads(emulator.command(f'list in {messages}'))['items']
        countdown, = [i['id'] for i in items if i.get('file', '').endswith('v7-countdown.odrgx')]
        for line in (f'ignore {messages} 1', f'play {countdown}'):
            self.assertEqual(json.loads(emulator.command(line)), dict(ok=True))
        state = wait_for(lambda s: s['file'] == 'clocks/message/v7-countdown.odrgx')
        self.assertFalse(state['clock_message'])
        self.assertEqual(json.loads(emulator.command('play all')), dict(ok=False, error='in-use'))
        self.assertEqual(json.loads(emulator.command(f'ignore {clocks} 1')), dict(ok=True))
        self.assertEqual(json.loads(emulator.command(f'play {clocks}')), dict(ok=True))
        wait_for(lambda s: s['clock_only']['state'] == 'no-clocks')
        self.assertEqual(json.loads(emulator.command(f'ignore {clocks} 0')), dict(ok=True))
        wait_for(lambda s: s['file'] == 'clocks/c.odrgx')
        actual = {p.relative_to(pathlib.Path(top, 'odrig')).as_posix(): p.read_bytes()
                  for p in pathlib.Path(top, 'odrig').rglob('*') if p.is_file()}
        self.assertEqual(actual, card)

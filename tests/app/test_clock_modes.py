import json
import pathlib
import tempfile
import threading
import time
import unittest

from tests.emulator import support as emulator_support
from . import support
from .test_clocks import Target, run
from .test_target import entered


STATUS = dict(ok=True, on=True, brightness=128, playing='all', animation=1,
              fps=50, error=None, clocks=True, clock_message=False)


class ModeTarget:
    def __init__(self, test, mode='off'):
        self.mode = mode
        self.message = False
        self.ignored = set()
        self.refusal = None
        self.answering = True
        self.mode_members = True
        self.apply_changes = True
        self.lose_reply = False
        self.change_seen = threading.Event()
        self.change_gate = None
        self.only_folder = 60007
        self.only_state = 'playing'
        self.levels = {
            None: [dict(id=1, file='one.odrg', bytes=100, external=False, ignored=False),
                   dict(id=60001, file='outside.odrg', bytes=100, external=True),
                   dict(id=60007, playlist='clocks', files=1, external=True),
                   dict(id=60009, playlist='other', files=1, external=True)],
            60007: [dict(id=60003, file='clocks/c.odrg', bytes=100, external=True),
                    dict(id=60008, playlist='clocks/message', files=1, external=True)],
            60008: [dict(id=60006, file='clocks/message/m.odrg', bytes=100, external=True)],
            60009: [dict(id=60002, file='other/x.odrg', bytes=100, external=True)],
        }
        self.stand_in = entered(test, support.StandIn(self.reply))

    @staticmethod
    def answer(value):
        return 200, json.dumps(value) + '\n'

    def reply(self, line):
        if not self.answering:
            return 500, ''
        words = line.decode().split()
        if words[0] == 'status':
            extra = dict(clock_mode=self.mode, clock_only=dict(folder=self.only_folder, state=self.only_state) if self.mode == 'only' else None) if self.mode_members else {}
            playing = self.mode != 'only' or self.only_state == 'playing'
            return self.answer({**STATUS, 'clocks': self.mode != 'off', 'clock_message': self.message,
                                'playing': (self.only_folder if self.mode == 'only' else 'all') if playing else None,
                                'animation': (60003 if self.mode == 'only' else 1) if playing else None,
                                'file': ('clocks/c.odrg' if self.mode == 'only' else 'one.odrg') if playing else None,
                                'playlist': 'clocks' if self.mode == 'only' and playing else None, **extra})
        if words[0] == 'list':
            level = int(words[2]) if len(words) > 2 and words[1] == 'in' else None
            items = []
            for original in self.levels.get(level, []):
                item = dict(original)
                if item['external']:
                    path = item.get('file', item.get('playlist'))
                    item['ignored'] = item['id'] in self.ignored
                    ancestors = [folder for entries in self.levels.values() for folder in entries if 'playlist' in folder]
                    item['inherited_ignored'] = any(folder['id'] in self.ignored and path.startswith(folder['playlist'] + '/') for folder in ancestors)
                items.append(item)
            return self.answer(dict(ok=True, items=items, next=None))
        if words[0] == 'clocks':
            self.change_seen.set()
            if self.change_gate is not None:
                self.change_gate.wait(5)
            if self.refusal:
                return self.answer(dict(ok=False, error=self.refusal))
            if self.apply_changes:
                if words[1] == 'message':
                    self.message = words[2] == 'on'
                else:
                    self.mode = 'between' if words[1] == 'on' else words[1]
            if self.lose_reply:
                self.lose_reply = False
                return 500, ''
            return self.answer(dict(ok=True))
        if words[0] == 'ignore':
            if self.refusal:
                return self.answer(dict(ok=False, error=self.refusal))
            if words[2] == '1':
                self.ignored.add(int(words[1]))
            else:
                self.ignored.discard(int(words[1]))
            return self.answer(dict(ok=True))
        if words[0] == 'play':
            return self.answer(dict(ok=True))
        if words[0] == 'space':
            return self.answer(dict(ok=True, free=1000, total=2000,
                                    external=dict(present=True, free=1000, total=2000, read_only=True)))
        return self.answer(dict(ok=False, error='unknown-command'))

    def lines(self, kind):
        return [line.decode() for _, line in self.stand_in.lines if line.startswith((kind + ' ').encode())]


def ui(target, acts, **kwargs):
    return support.run('clock-mode-ui', address=target.stand_in.address,
                       settings=dict(rows=kwargs.pop('rows', 2), acts=acts), **kwargs).seen


class ModeProtocol(unittest.TestCase):
    def protocol(self, replies):
        return support.run('clock-mode-protocol', settings={'replies': replies}).seen

    def test_status_keeps_explicit_mode_and_maps_legacy_booleans(self):
        replies = [dict(command='status', reply={**STATUS, 'clock_mode': 'only',
                                               'clock_only': dict(folder=60007, state='playing')}),
                   dict(command='status', reply=STATUS),
                   dict(command='status', reply={**STATUS, 'clocks': False})]
        seen = self.protocol(replies)['results']
        self.assertEqual([s.get('clockMode') for s in seen], ['only', 'between', 'off'])
        self.assertEqual([s.get('hasClockMode') for s in seen], [True, False, False])
        self.assertEqual(seen[0]['clockOnly'], dict(folder=60007, state='playing'))

    def test_external_folders_and_files_keep_own_and_inherited_inclusion(self):
        items = [dict(id=60007, playlist='clocks', files=2, external=True, ignored=True, inherited_ignored=False),
                 dict(id=60003, file='clocks/c.odrg', bytes=123, external=True, ignored=False, inherited_ignored=True)]
        seen = self.protocol([dict(command='list', reply=dict(ok=True, items=items, next=None))])['results'][0]
        self.assertEqual([i.get('ignored') for i in seen.get('items', [])], [True, False])
        self.assertEqual([i.get('inheritedIgnored') for i in seen['items']], [False, True])

    def test_only_uses_the_approved_command_form(self):
        seen = self.protocol([dict(command='clockMode', args=['only'], reply=dict(ok=True))])
        self.assertEqual(seen['sent'], ['clocks only'])
        self.assertNotIn('error', seen['results'][0] or {})

    def test_invalid_mode_metadata_is_not_published_as_confirmed_state(self):
        bad = [dict(clock_mode='random', clock_only=None), dict(clock_mode='only', clock_only=None),
               dict(clock_mode='off', clock_only=None),
               dict(clock_mode='only', clock_only=dict(folder=None, state='playing')),
               dict(clock_mode='only', clock_only=dict(folder=60007, state='unknown'))]
        seen = self.protocol([dict(command='status', reply={**STATUS, **extra}) for extra in bad])
        self.assertEqual(seen['results'], [dict(error='bad-reply')] * len(bad))

    def test_malformed_inherited_flags_are_refused(self):
        bad = [dict(id=1, file='x.odrg', bytes=100, external=True, inherited_ignored='yes'),
               dict(id=2, playlist='clocks', files=1, external=True, ignored=1),
               dict(id=3, cycle=[1], inherited_ignored=True)]
        seen = self.protocol([dict(command='list', reply=dict(ok=True, items=[item], next=None)) for item in bad])
        self.assertEqual(seen['results'], [dict(error='bad-reply')] * len(bad))

    def test_each_dropdown_value_uses_its_existing_or_approved_form(self):
        seen = self.protocol([dict(command='clockMode', args=[mode], reply=dict(ok=True)) for mode in ('off', 'between', 'only', 'random')])
        self.assertEqual(seen['sent'], ['clocks off', 'clocks on', 'clocks only'])
        self.assertEqual(seen['results'][-1], dict(error='RangeError'))

    def test_outside_play_and_display_test_refusals_explain_the_mode_boundary(self):
        lines = ['play 60001', 'play all', 'mapping test on']
        seen = support.run('texts', settings=dict(refusals=[['in-use', line, None] for line in lines], failures=[])).seen
        for line in lines:
            text = seen['refusals'][f'in-use | {line} | null']
            self.assertIn('Clocks only', text)
            self.assertNotIn('removed', text)


class ModePanel(unittest.TestCase):
    def test_legacy_target_has_mode_dropdown_with_only_unavailable(self):
        seen = run(Target(self), [])['first']
        self.assertEqual(seen['kind'], 'SELECT')
        self.assertEqual(seen['mode'], 'off')
        self.assertEqual(seen['options'], [dict(value='off', text='Off', disabled=False),
                                           dict(value='between', text='Between animations', disabled=False),
                                           dict(value='only', text='Clocks only', disabled=True)])

    def test_only_opens_clocks_once_and_browsing_outside_keeps_play_disabled(self):
        target = ModeTarget(self)
        acts = [dict(screen='Settings'), dict(mode='only', pending='pending', until=dict(mode='only', disabled=False, screen='animations', level='clocks', rows=1), look='only'),
                dict(back=True, until=dict(level='Root', rows=2), look='root'),
                dict(wait=1800, look='later'), dict(enter='other', until=dict(level='other', rows=1), look='other'),
                dict(restart=True, wait=500)]
        seen = ui(target, acts)
        self.assertTrue(seen['pending']['disabled'])
        self.assertEqual(seen['only']['level'], 'clocks')
        self.assertEqual(seen['later']['level'], 'Root')
        self.assertTrue(all(row['disabled'] for row in seen['root']['rows']))
        self.assertEqual(seen['root']['global']['text'], 'Restart clocks')
        self.assertTrue(seen['other']['rows'][0]['disabled'])
        self.assertEqual(target.lines('play'), ['play 60007'])

    def test_folder_ignore_is_available_on_read_only_media_and_inherited_by_children(self):
        target = ModeTarget(self)
        seen = ui(target, [dict(folderMenu='clocks', look='menu'), dict(choose='Ignore folder', until=dict(ignored=60007), look='ignored'),
                           dict(enter='clocks', until=dict(level='clocks', rows=1), look='child')])
        self.assertIn(dict(text='Ignore folder', disabled=False), seen['menu']['menu'])
        self.assertIn('Ignored', seen['ignored']['folders'][0]['note'])
        self.assertIn('parent', seen['child']['rows'][0]['note'])
        self.assertTrue(seen['child']['rows'][0]['ignored'])
        self.assertFalse(seen['child']['rows'][0]['disabled'])
        self.assertEqual(target.lines('ignore'), ['ignore 60007 1'])

    def test_external_file_ignore_and_restore_uses_the_same_persistent_setting(self):
        target = ModeTarget(self)
        seen = ui(target, [dict(menu=60001, look='menu'), dict(choose='Ignore in playlist', until=dict(ignored=60001), look='ignored'),
                           dict(menu=60001), dict(choose='Restore to playlist', until=dict(included=60001), look='included')])
        self.assertTrue(seen['ignored']['rows'][1]['ignored'])
        self.assertFalse(seen['included']['rows'][1]['ignored'])
        self.assertEqual(target.lines('ignore'), ['ignore 60001 1', 'ignore 60001 0'])

    def test_child_own_ignore_survives_including_its_parent(self):
        target = ModeTarget(self)
        target.ignored.add(60007)
        acts = [dict(enter='clocks', until=dict(level='clocks', rows=1)),
                dict(folderMenu='clocks/message', look='inherited'),
                dict(choose='Ignore folder', until=dict(ignored=60008)),
                dict(back=True, until=dict(level='Root', rows=2)),
                dict(folderMenu='clocks'), dict(choose='Include folder', until=dict(included=60007)),
                dict(enter='clocks', until=dict(level='clocks', rows=1), look='own'),
                dict(enter='clocks/message', until=dict(level='clocks/message', rows=1), look='child')]
        seen = ui(target, acts)
        self.assertTrue(any('parent' in note for note in seen['inherited']['menuNotes']))
        self.assertEqual(target.ignored, {60008})
        self.assertEqual(seen['own']['folders'][0]['note'], '⊘ Ignored')
        self.assertIn('parent', seen['child']['rows'][0]['note'])

    def test_refused_and_contradicted_changes_show_the_confirmed_mode(self):
        target = ModeTarget(self)
        target.refusal = 'storage-error'
        def contradict():
            target.refusal = None
            target.apply_changes = False
        acts = [dict(screen='Settings'), dict(mode='only', until=dict(disabled=False, mode='off', said='could not save'), look='refused'),
                dict(step=True), dict(mode='only', until=dict(disabled=False, mode='off', said='different setting'), look='contradicted')]
        seen = ui(target, acts, steps=[contradict])
        self.assertEqual(seen['refused']['screen'], 'settings')
        self.assertEqual(seen['contradicted']['level'], 'Root')
        self.assertEqual(target.mode, 'off')

    def test_an_unconfirmed_reply_can_recover_from_authoritative_status(self):
        target = ModeTarget(self)
        target.lose_reply = True
        seen = ui(target, [dict(screen='Settings'), dict(mode='only',
                  until=dict(mode='only', disabled=False, level='clocks', rows=1, screen='animations'), look='recovered')])
        self.assertIn('not confirmed', seen['recovered']['said'])
        self.assertNotIn('Saved:', seen['recovered']['said'])
        self.assertEqual(target.mode, 'only')

    def test_other_clients_change_mode_but_reconnect_does_not_repeat_navigation(self):
        target = ModeTarget(self)
        steps = [lambda: setattr(target, 'mode', 'only'), lambda: setattr(target, 'answering', False),
                 lambda: setattr(target, 'answering', True), lambda: setattr(target, 'mode', 'between'),
                 lambda: setattr(target, 'mode', 'only')]
        acts = [dict(step=True, until=dict(mode='only', level='clocks', rows=1)),
                dict(back=True, until=dict(level='Root', rows=2)),
                dict(step=True, until=dict(disabled=True)),
                dict(step=True, until=dict(disabled=False, mode='only', level='Root'), look='reconnected'),
                dict(step=True, until=dict(mode='between', level='Root')),
                dict(step=True, until=dict(mode='only', level='clocks', rows=1), look='newTransition')]
        seen = ui(target, acts, steps=steps)
        self.assertEqual(seen['reconnected']['level'], 'Root')
        self.assertEqual(seen['newTransition']['level'], 'clocks')
        self.assertEqual(target.lines('clocks'), [])

    def test_late_reply_from_an_old_target_cannot_publish_mode_or_success(self):
        first, second = ModeTarget(self), ModeTarget(self, 'between')
        second.mode_members = False
        first.change_gate = threading.Event()
        self.addCleanup(first.change_gate.set)
        def arrived():
            self.assertTrue(first.change_seen.wait(3))
        acts = [dict(screen='Settings'), dict(mode='only', pending='pending'), dict(step=True),
                dict(target=second.stand_in.address), dict(step=True),
                dict(until=dict(mode='between', disabled=False, level='Root', rows=2), look='second')]
        seen = ui(first, acts, steps=[arrived, first.change_gate.set])
        self.assertTrue(seen['pending']['disabled'])
        self.assertTrue(seen['second']['onlyDisabled'])
        self.assertEqual(seen['second']['said'], '')
        self.assertEqual(second.lines('clocks'), [])

    def test_missing_clocks_keeps_only_visible_and_restart_disabled(self):
        target = ModeTarget(self, 'only')
        target.only_folder = None
        target.only_state = 'missing-folder'
        target.levels[None] = target.levels[None][:2]
        seen = ui(target, [dict(screen='Settings', look='missing')])
        self.assertEqual(seen['missing']['mode'], 'only')
        self.assertIn('missing', seen['missing']['reason'])
        self.assertTrue(seen['missing']['global']['disabled'])

    def test_refused_external_inclusion_keeps_the_previous_choice_until_a_retry(self):
        target = ModeTarget(self)
        target.refusal = 'storage-error'
        acts = [dict(menu=60001), dict(choose='Ignore in playlist', until=dict(included=60001), look='refused'),
                dict(step=True), dict(menu=60001), dict(choose='Ignore in playlist', until=dict(ignored=60001), look='saved')]
        seen = ui(target, acts, steps=[lambda: setattr(target, 'refusal', None)])
        self.assertFalse(seen['refused']['rows'][1]['ignored'])
        self.assertTrue(seen['refused']['notice'])
        self.assertTrue(seen['saved']['rows'][1]['ignored'])
        self.assertEqual(target.lines('ignore'), ['ignore 60001 1', 'ignore 60001 1'])

    def test_new_controls_and_folder_actions_fit_narrow_and_landscape_layouts(self):
        for size in ((320, 568), (640, 360)):
            with self.subTest(size=size):
                target = ModeTarget(self, 'only')
                acts = [dict(screen='Settings', measure='settings'), dict(screen='Animations'),
                        dict(folderMenu='clocks/message', measure='folderMenu')]
                seen = ui(target, acts, rows=1, size=size)
                self.assertLessEqual(seen['settings']['scrollWidth'], seen['settings']['width'])
                self.assertLessEqual(seen['folderMenu']['scrollWidth'], seen['folderMenu']['width'])
                controls = [c for c in seen['settings']['controls'] if c['what'] in ('clocks', 'clock-message')]
                self.assertEqual(len(controls), 2)
                self.assertTrue(all(c['bottom'] - c['top'] >= 47.99 for c in controls))


class RealEmulator(unittest.TestCase):
    def test_mode_manual_message_and_read_only_inclusion_use_the_shared_player(self):
        folder = entered(self, emulator_support.example_show())
        card = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        animation = (folder / 'hello.odrg').read_bytes()
        emulator_support.installed(card / 'odrig', {'outside.odrg': animation})
        emulator_support.installed(card / 'odrig' / 'clocks', {'c.odrg': animation})
        emulator_support.installed(card / 'odrig' / 'clocks' / 'message', {'m.odrg': animation})
        before = {p.relative_to(card): p.read_bytes() for p in card.rglob('*') if p.is_file()}
        emulator = entered(self, emulator_support.Emulator(folder, '--drive', card, '--drive-read-only'))
        deadline = time.monotonic() + 10
        clock_folder = None
        children = []
        message_children = []
        while time.monotonic() < deadline:
            listing = json.loads(emulator.command('list'))['items']
            clock_folder = next((item['id'] for item in listing if item.get('playlist') == 'clocks'), None)
            if clock_folder is not None:
                children = json.loads(emulator.command(f'list in {clock_folder}'))['items']
                message_folder = next((item['id'] for item in children if item.get('playlist') == 'clocks/message'), None)
                if message_folder is not None:
                    message_children = json.loads(emulator.command(f'list in {message_folder}'))['items']
                    if message_children:
                        break
            time.sleep(.05)
        self.assertIsNotNone(clock_folder)
        self.assertTrue(message_children)
        message_folder = next(item['id'] for item in children if item.get('playlist') == 'clocks/message')
        message = message_children[0]['id']
        acts = [dict(screen='Settings'), dict(mode='only', until=dict(mode='only', disabled=False, level='clocks', rows=1, screen='animations')),
                dict(enter='clocks/message', until=dict(level='clocks/message', rows=1)),
                dict(play=message, wait=300), dict(back=True, until=dict(level='clocks', rows=1)),
                dict(folderMenu='clocks/message'), dict(choose='Ignore folder', until=dict(ignored=message_folder)),
                dict(back=True, until=dict(level='Root', rows=3), look='root'), dict(restart=True, wait=300)]
        self.assertEqual(json.loads(emulator.command('status'))['clock_mode'], 'off')
        with emulator_support.EventStream(emulator.port) as stream:
            result = support.run('clock-mode-ui', address=f'127.0.0.1:{emulator.port}', settings=dict(rows=3, acts=acts))
            events = stream.read_until(lambda events: any(event.kind == 'log' and json.loads(event.data)['line'] == f'play {clock_folder}' for event in events), 10)
        self.assertTrue(all(row['disabled'] for row in result.seen['root']['rows']))
        sent = [entry['line'] for entry in emulator_support.of_kind(events, 'log')]
        self.assertIn(f'play {clock_folder}', sent)
        self.assertIn(f'play {message}', sent)
        self.assertNotIn('play all', sent)
        self.assertEqual(json.loads(emulator.command('play all')), dict(ok=False, error='in-use'))
        self.assertEqual(json.loads(emulator.command('status'))['clock_mode'], 'only')
        self.assertIn(b'd clocks/message\n', (folder / 'ignored.txt').read_bytes())
        self.assertEqual(before, {p.relative_to(card): p.read_bytes() for p in card.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()

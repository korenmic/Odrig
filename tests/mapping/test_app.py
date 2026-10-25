import json
import unittest
from tests.app import support as browser
from tests.emulator.support import Emulator
from tests.core import support
from .test_core import PINS, files, set_line

class MappingApp(unittest.TestCase):
    def opened(self, data=None):
        folder = self.enterContext(support.installed(files() if data is None else data))
        return self.enterContext(Emulator(folder))

    def test_app_moves_pins_by_drag_and_saves_each_new_place_while_held(self):
        target = self.opened()
        live = []
        found = browser.run("mapping", address=f"127.0.0.1:{target.port}", steps=[lambda: live.append(json.loads(target.command('mapping get'))['pins'])]).seen
        moved = [PINS[1], PINS[2], PINS[0], *PINS[3:]]
        second = [PINS[1], PINS[0], *PINS[2:]]
        self.assertEqual(found['before'], PINS)
        self.assertEqual(found['snakes'][0], 'Snake 1 \u00b7 columns 1\u20133')
        self.assertIn('Snake 20 \u00b7 columns 58\u201360', found['snakes'][-1])
        self.assertEqual(found['words'], [f"GPIO {pin}" for pin in PINS])
        self.assertEqual(found['buttons'], ['Restore defaults', 'Reload'])
        self.assertTrue(found['lifted'])
        self.assertTrue(found['placeholder'])
        # Saved on the target while the finger still held the pin.
        self.assertTrue(found['stillLifted'])
        self.assertEqual(live, [moved])
        self.assertEqual(found['dragged'], moved)
        self.assertIn(f'Saved: GPIO {PINS[0]} drives snake 3', found['dragNote'])
        self.assertEqual(found['held'], second)
        self.assertEqual(found['keyed'], PINS)
        self.assertTrue(found['focusKept'])
        self.assertEqual(found['unmoved'], PINS)
        self.assertEqual(found['keyedDown'], second)
        self.assertEqual(found['defaults'], PINS)
        self.assertEqual(json.loads(target.command('mapping get'))['pins'], PINS)
        self.assertFalse(json.loads(target.command('mapping get'))['test'])
        self.assertEqual(found['playback'], 0)
        self.assertTrue(found['inLine'])
        self.assertLessEqual(found['scrollWidth'], found['width'])
        self.assertEqual([tab['text'] for tab in found['tabs']], ['Animations', 'Upload', 'Settings', 'Target'])
        self.assertTrue(all(tab['width'] >= 56 for tab in found['tabs']))

    def test_background_reads_neither_take_the_focus_nor_disturb_a_held_pin(self):
        target = self.opened()
        found = browser.run("mapping-steady", address=f"127.0.0.1:{target.port}").seen
        self.assertTrue(found['focused'], found)
        self.assertEqual(found['blurredByReads'], 0, found)
        self.assertTrue(found['stillHeld'], found)
        self.assertTrue(found['savedWhileHeld'], found)
        self.assertEqual(found['whileHeld'], {'disabled': 0, 'redrawn': 0, 'reading': 0}, found)
        self.assertEqual(found['order'], [PINS[1], PINS[0], *PINS[2:]])
        self.assertEqual(json.loads(target.command('mapping get'))['pins'], [PINS[1], PINS[0], *PINS[2:]])

    def test_a_change_elsewhere_after_a_pin_is_taken_is_said_and_shown(self):
        target = self.opened()
        other = PINS[::-1]
        found = browser.run('mapping', address=f'127.0.0.1:{target.port}', settings={'conflict': True, 'first': other[0]}, steps=[lambda: target.command(set_line(other))]).seen
        self.assertEqual(found['after'], other)
        self.assertEqual(json.loads(target.command('mapping get'))['pins'], other)

    def test_lost_save_reply_reconciles_without_repeating_the_mutation(self):
        state = {"ok": True, "editable": True, "pins": PINS, "revision": 123, "test": False}
        mutations = []
        def mapping(line):
            words = line.decode().split()
            if words[1] == 'set':
                mutations.append(line)
                state['pins'] = list(map(int, words[3].split(',')))
                state['revision'] += 1
                return (200, 'lost reply')
            return (200, json.dumps(state))
        with browser.StandIn({**browser.SOUND, 'mapping': mapping}, delay=.08) as target:
            found = browser.run('mapping', address=target.address, settings={'uncertain': True}).seen
            self.assertEqual(len(mutations), 1)
            self.assertIn('No confirmed reply', found['uncertain'])
            self.assertEqual(found['after'], [PINS[1], PINS[0], *PINS[2:]])
            self.assertEqual(found['kept'], found['after'])
            self.assertEqual(target.together, 1)

    def test_older_target_has_readable_unsupported_message(self):
        with browser.StandIn(browser.SOUND) as target:
            found = browser.run('mapping',address=target.address,settings={'unsupported':True}).seen
            self.assertIn('does not support',found['error'])
            self.assertEqual(found['count'],0)

    def test_mapping_protocol_checks_full_replies_through_the_native_bridge_contract(self):
        good = {"ok":True,"editable":True,"pins":PINS,"revision":0xffffffff,"test":True}
        replies = [good, {**good,'pins':[1]*20}, {**good,'revision':-1}, {**good,'test':'on'}, {**good,'pins':PINS[:-1]}, {**good,'pins':[*PINS[:-1],256]}, {"ok":False,"error":"mapping-conflict"}, {**good,"editable":False,"pins":[]}, {**good,"editable":False},
                   {**good,'snake':7}, {**good,'snake':21}, {**good,'snake':'7'}, {**good,'test':False,'snake':7}]
        found = browser.run('mapping-protocol',settings={'replies':replies}).seen
        self.assertEqual(found['found'][0],{**{k:v for k,v in good.items() if k!='ok'},'snake':None})
        self.assertEqual(found['found'][9]['snake'],7)
        self.assertEqual(found['found'][10:],[{'error':'bad-reply'}]*3)
        self.assertEqual(found['found'][1:6],[{'error':'bad-reply'}]*5)
        self.assertEqual(found['found'][6],{'error':'mapping-conflict'})
        self.assertEqual(found['found'][7]['pins'],[])
        self.assertEqual(found['found'][8],{'error':'bad-reply'})
        self.assertEqual(found['sent'][-4:],['mapping set 123 1,2,3','mapping test on','mapping test off','mapping test snake 9'])


    def test_target_change_shows_the_new_targets_assignment(self):
        first = self.opened()
        second = self.opened()
        other = PINS[::-1]
        self.assertTrue(json.loads(second.command(set_line(other)))['ok'])
        found = browser.run('mapping',address=f'127.0.0.1:{first.port}',settings={'other':f'127.0.0.1:{second.port}','first':other[0]}).seen
        self.assertEqual(found['after'],other)
        self.assertEqual(json.loads(first.command('mapping get'))['pins'],PINS)

    def test_mapping_controls_fit_landscape_with_the_same_shared_screen(self):
        target = self.opened()
        found = browser.run('mapping',address=f'127.0.0.1:{target.port}',settings={'layoutOnly':True},size=(740,360)).seen
        self.assertLessEqual(found['scrollWidth'],740)
        self.assertTrue(all(tab['width']>=56 for tab in found['tabs']))

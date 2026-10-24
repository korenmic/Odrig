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

    def test_app_swaps_saves_cancels_and_restores_defaults_in_settings(self):
        target = self.opened()
        found = browser.run("mapping", address=f"127.0.0.1:{target.port}").seen
        swapped = [PINS[1],PINS[0],*PINS[2:]]
        self.assertEqual(found['before'], PINS)
        self.assertEqual(found['draft'], swapped)
        self.assertEqual(found['kept'], swapped)
        self.assertEqual(found['cancelled'], PINS)
        self.assertEqual(found['saved'], swapped)
        self.assertEqual(found['defaults'], PINS)
        self.assertEqual(json.loads(target.command('mapping get'))['pins'], swapped)
        self.assertFalse(json.loads(target.command('mapping get'))['test'])
        self.assertEqual(found['playback'], 0)
        self.assertEqual(len(found['labels']),20)
        self.assertIn('58–60',found['labels'][-1])
        self.assertLessEqual(found['scrollWidth'],found['width'])
        self.assertEqual([tab['text'] for tab in found['tabs']],['Animations','Upload','Settings','Target'])
        self.assertTrue(all(tab['width']>=56 for tab in found['tabs']))

    def test_external_change_preserves_dirty_draft_and_requires_reload(self):
        target = self.opened()
        other = PINS[::-1]
        found = browser.run('mapping', address=f'127.0.0.1:{target.port}', settings={'conflict':True,'first':other[0]}, steps=[lambda:target.command(set_line(other))]).seen
        self.assertTrue(found['disabled'])
        self.assertEqual(found['conflict'],[PINS[1],PINS[0],*PINS[2:]])
        self.assertEqual(found['after'],other)


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
        with browser.StandIn({**browser.SOUND,'mapping':mapping}, delay=.08) as target:
            found = browser.run('mapping',address=target.address,settings={'uncertain':True}).seen
            self.assertEqual(len(mutations),1)
            self.assertTrue(found['disabled'])
            self.assertEqual(found['after'],[PINS[1],PINS[0],*PINS[2:]])
            self.assertEqual(found['kept'],found['after'])
            self.assertEqual(target.together,1)

    def test_older_target_has_readable_unsupported_message(self):
        with browser.StandIn(browser.SOUND) as target:
            found = browser.run('mapping',address=target.address,settings={'unsupported':True}).seen
            self.assertIn('does not support',found['error'])
            self.assertEqual(found['count'],0)

    def test_mapping_protocol_checks_full_replies_through_the_native_bridge_contract(self):
        good = {"ok":True,"editable":True,"pins":PINS,"revision":0xffffffff,"test":True}
        replies = [good, {**good,'pins':[1]*20}, {**good,'revision':-1}, {**good,'test':'on'}, {**good,'pins':PINS[:-1]}, {**good,'pins':[*PINS[:-1],256]}, {"ok":False,"error":"mapping-conflict"}, {**good,"editable":False,"pins":[]}, {**good,"editable":False}]
        found = browser.run('mapping-protocol',settings={'replies':replies}).seen
        self.assertEqual(found['found'][0],{k:v for k,v in good.items() if k!='ok'})
        self.assertEqual(found['found'][1:6],[{'error':'bad-reply'}]*5)
        self.assertEqual(found['found'][6],{'error':'mapping-conflict'})
        self.assertEqual(found['found'][7]['pins'],[])
        self.assertEqual(found['found'][8],{'error':'bad-reply'})
        self.assertEqual(found['sent'][-3:],['mapping set 123 1,2,3','mapping test on','mapping test off'])


    def test_target_change_drops_the_old_draft(self):
        first = self.opened()
        second = self.opened()
        other = PINS[::-1]
        self.assertTrue(json.loads(second.command(set_line(other)))['ok'])
        found = browser.run('mapping',address=f'127.0.0.1:{first.port}',settings={'other':f'127.0.0.1:{second.port}','first':other[0]}).seen
        self.assertEqual(found['after'],other)
        self.assertTrue(found['saveDisabled'])
        self.assertEqual(json.loads(first.command('mapping get'))['pins'],PINS)

    def test_mapping_controls_fit_landscape_with_the_same_shared_screen(self):
        target = self.opened()
        found = browser.run('mapping',address=f'127.0.0.1:{target.port}',size=(740,360)).seen
        self.assertLessEqual(found['scrollWidth'],740)
        self.assertTrue(all(tab['width']>=56 for tab in found['tabs']))

import json
import pathlib
import unittest
import zlib

from tests.core import support
from tests.core.test_playback import refreshes

PINS = list(range(1, 19)) + [21, 47]
REVISION = zlib.crc32(bytes(PINS))


def answers(run):
    return [json.loads(line[6:]) for line in run.lines if line.startswith('reply ')]


def set_line(pins, revision=REVISION):
    return f'mapping set {revision} ' + ','.join(map(str, pins))


def files():
    result = support.demo_show()
    show=json.loads(result["show.json"]); show["brightness"]=32
    result["show.json"]=json.dumps(show).encode()
    return result


class MappingCommands(unittest.TestCase):
    def test_get_returns_current_assignments_and_bench_is_unsupported(self):
        reply = answers(support.start(files(), [support.line(1000, 'mapping get')]))[0]
        self.assertEqual(reply, dict(ok=True, editable=True, pins=PINS, revision=REVISION, test=False))
        reply = answers(support.start(support.example_show(), [support.line(1000, 'mapping get')]))[0]
        self.assertEqual(reply, dict(ok=True, editable=False, pins=[], revision=0, test=False))

    def test_save_is_durable_and_does_not_change_the_show_or_animations(self):
        source = files()
        swapped = PINS.copy(); swapped[0], swapped[19] = swapped[19], swapped[0]
        run, left = support.start_and_keep(source, [support.line(1000, set_line(swapped)), support.line(1001, 'mapping get')])
        self.assertEqual(answers(run)[0], dict(ok=True))
        self.assertEqual(answers(run)[1]['pins'], swapped)
        self.assertEqual([leg['pin'] for leg in json.loads(left['mapping.json'])['legs']], swapped)
        self.assertEqual({k: v for k,v in source.items() if k!='mapping.json'}, {k: v for k,v in left.items() if k!='mapping.json'})
        self.assertEqual(answers(support.start(left, [support.line(1000,'mapping get')]))[0]['pins'], swapped)

    def test_invalid_permutations_and_stale_revisions_leave_the_mapping_alone(self):
        malformed = [PINS[:-1], PINS+[48], [1]*20, PINS[:-1]+[19], PINS[:-1]+[255]]
        for pins in malformed:
            with self.subTest(pins=pins):
                run,left=support.start_and_keep(files(),[support.line(1000,set_line(pins))])
                self.assertEqual(answers(run)[0],dict(ok=False,error='bad-argument'))
                self.assertEqual(left,files())
        reply=answers(support.start(files(),[support.line(1000,set_line(PINS,REVISION+1))]))[0]
        self.assertEqual(reply,dict(ok=False,error='mapping-conflict'))

    def test_noop_save_makes_no_storage_calls(self):
        run=support.start(files(),[support.line(1000,set_line(PINS))],['--trace-store'])
        self.assertEqual(answers(run),[dict(ok=True)])
        self.assertFalse(any(x.startswith('store ') for x in run.lines))

    def test_storage_failures_leave_live_and_persisted_mapping_unchanged(self):
        swapped=PINS[::-1]
        for at in range(2,7):
            with self.subTest(at=at):
                run,left=support.start_and_keep(files(),[support.line(1000,set_line(swapped)),support.line(1001,'mapping get')],['--store-fails-at',str(at)])
                if not answers(run)[0]['ok']:
                    self.assertEqual(answers(run)[0]['error'],'storage-error')
                    self.assertEqual(left['mapping.json'],files()['mapping.json'])
                    self.assertEqual(answers(run)[1]['pins'],PINS)

    def test_diagonal_has_exact_pixels_and_exits_to_the_previous_animation(self):
        script=['poll 1000',support.line(1020,'mapping test on'),'poll 1020','poll 62000',support.line(62001,'status'),support.line(62002,'mapping test off'),'poll 62020',support.line(62021,'status')]
        run=support.start(files(),script)
        replies=answers(run)
        self.assertEqual(replies[0],dict(ok=True))
        self.assertIsNone(replies[1]['playing']); self.assertIsNone(replies[1]['animation'])
        self.assertEqual(replies[2],dict(ok=True))
        self.assertEqual(replies[3]['playing'],'all'); self.assertEqual(replies[3]['animation'],1)
        produced,_=refreshes([l for l in run.lines if l.startswith(('refresh ','data ','idle '))])
        for _,legs in produced[1:3]:
            for leg,data in legs.items():
                for n in range(180):
                    column=(leg-1)*3+n//60+1
                    y=n%60+1 if n//60!=1 else 60-n%60
                    self.assertEqual(data[n*3:n*3+3],bytes([32 if column==y else 0])*3)

    def test_test_is_idempotent_does_not_mutate_show_and_respects_power(self):
        run,left=support.start_and_keep(files(),[support.line(1000,'mapping test on'),support.line(1001,'mapping test on'),support.line(1002,'off'),'poll 1020',support.line(1021,'remove 1'),support.line(1022,'mapping get'),support.line(1023,'mapping test off'),support.line(1024,'mapping test off')])
        self.assertEqual(answers(run)[3],dict(ok=False,error='busy'))
        self.assertTrue(answers(run)[4]['test']); self.assertEqual(left,files())
        produced,_=refreshes([l for l in run.lines if l.startswith(('refresh ','data ','idle '))])
        self.assertTrue(all(not any(data) for data in produced[0][1].values()))

    def test_mapping_parts_are_removed_after_an_interrupted_save(self):
        source=files(); source['mapping.part']=b'broken'
        _,left=support.start_and_keep(source)
        self.assertNotIn('mapping.part',left)
        self.assertEqual(left['mapping.json'],files()['mapping.json'])

    def test_power_loss_at_every_save_step_recovers_a_whole_assignment(self):
        swapped=PINS[::-1]
        command=support.line(1000,set_line(swapped))
        observed=support.start(files(),[command],['--trace-store'])
        calls=sum(line.startswith('store ') for line in observed.lines)
        for at in range(3,3+calls):
            for keeps in (0,1):
                with self.subTest(at=at,keeps=keeps):
                    _,left=support.start_and_keep(files(),[command],['--cut-at',str(at),'--cut-keeps',str(keeps)],status=75)
                    recovered,settled=support.start_and_keep(left,[support.line(1000,'mapping get')])
                    self.assertIn(answers(recovered)[0]['pins'],[PINS,swapped])
                    self.assertNotIn('mapping.part',settled)
                    self.assertEqual(settled['show.json'],files()['show.json'])

    def test_a_reordered_mapping_preserves_file_entry_order(self):
        source=files();mapping=json.loads(source['mapping.json']);mapping['legs'].reverse()
        source['mapping.json']=json.dumps(mapping).encode()
        swapped=PINS[::-1]
        run,left=support.start_and_keep(source,[support.line(1000,set_line(swapped))])
        self.assertEqual(answers(run)[0],dict(ok=True))
        kept=json.loads(left['mapping.json'])['legs']
        self.assertEqual([leg['leg'] for leg in kept],list(range(20,0,-1)))
        self.assertEqual([leg['pin'] for leg in reversed(kept)],swapped)

    def test_cycle_resume_keeps_the_animation_that_was_current(self):
        source=files();show=json.loads(source['show.json'])
        show['items'].append(dict(id=3,cycle=[1,2],seconds=1));show['start']=3
        source['show.json']=json.dumps(show).encode()
        run=support.start(source,['poll 1000','poll 2020',support.line(2021,'mapping test on'),'poll 100000',support.line(100001,'mapping test off'),'poll 100020',support.line(100021,'status')])
        self.assertEqual(answers(run)[-1]['playing'],3)
        self.assertEqual(answers(run)[-1]['animation'],2)

    def test_packaged_asset_is_the_converter_output(self):
        import subprocess
        subprocess.run(['python3',str(support.ROOT/'core/diagonal.py'),'--check'],check=True,capture_output=True)

    def test_malformed_commands_do_not_change_storage(self):
        commands=['mapping','mapping get extra','mapping test','mapping test maybe','mapping set 0','mapping set -1 '+','.join(map(str,PINS)),'mapping set 4294967296 '+','.join(map(str,PINS)),'mapping set 0 '+','.join(map(str,PINS))+',']
        run,left=support.start_and_keep(files(),[support.line(1000,line) for line in commands])
        self.assertEqual(answers(run),[dict(ok=False,error='bad-argument')]*len(commands))
        self.assertEqual(left,files())

    def test_diagnostic_is_not_saved_and_explicit_play_exits_it(self):
        source=files()
        run,left=support.start_and_keep(source,[support.line(1000,'mapping test on'),support.line(1001,'play 2'),'poll 1020',support.line(1021,'mapping get'),support.line(1022,'status')])
        self.assertFalse(answers(run)[2]['test']);self.assertEqual(answers(run)[3]['animation'],2)
        run=support.start(left,[support.line(1000,'mapping get')])
        self.assertFalse(answers(run)[0]['test']);self.assertEqual(left,source)

    def test_brightness_scales_diagonal_and_upload_is_busy(self):
        run=support.start(files(),[support.line(1000,'mapping test on'),support.line(1001,'brightness 7'),support.line(1002,'upload begin 99 new.odrg 100'),'poll 1020'])
        self.assertEqual(answers(run)[2],dict(ok=False,error='busy'))
        produced,_=refreshes([l for l in run.lines if l.startswith(('refresh ','data ','idle '))])
        self.assertEqual({v for data in produced[0][1].values() for v in data},{0,7})

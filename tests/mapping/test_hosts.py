import json
import pathlib
import subprocess
import tempfile
import unittest

from emulator import binding, engine, host, hub
from tests.core import support
from .test_core import PINS, files, set_line

LIBRARY=support.CORE/'build'/binding.LIBRARY_NAME


class HostRouting(unittest.TestCase):
    def opened(self):
        folder=self.enterContext(support.installed(files()))
        source=host.FolderHost(folder)
        self.addCleanup(source.close)
        self.addCleanup(source._drop_second)
        core=binding.Core(LIBRARY,source)
        for now in range(0,1001,20):core.poll(now)
        return core

    def test_binding_reports_live_pins_after_command_and_feed(self):
        for feed in (False,True):
            with self.subTest(feed=feed):
                core=self.opened();swapped=PINS[::-1]
                data=set_line(swapped).encode()
                reply=core.feed(1020,data+b'\n')[0][1] if feed else core.command(1020,data)
                self.assertTrue(json.loads(reply)['ok'])
                self.assertEqual([leg.pin for leg in core.legs],swapped)

    def test_engine_announces_complete_mapping_for_every_command_transport(self):
        for transport in ('http','serial','tcp'):
            with self.subTest(transport=transport):
                core=self.opened();events=hub.Hub();running=engine.Engine(core,events,clock=lambda:0)
                connection=events.connect({})
                if transport=='http':running.line(set_line(PINS[::-1]).encode(),transport)
                else:running.feed((set_line(PINS[::-1])+'\n').encode(),transport)
                published=connection.take(.01)
                changed=[json.loads(value) for kind,value in published if kind=='mapping']
                self.assertEqual(len(changed),1)
                self.assertEqual([leg[1] for leg in changed[0]],PINS[::-1])
                events.disconnect(connection)

    def test_pin_bytes_follow_the_saved_assignment_without_changing_canvas_data(self):
        core=self.opened();core.command(1001,b'mapping test on');core.poll(1020)
        picture=core.frame();before={leg.pin:picture[i*540:(i+1)*540] for i,leg in enumerate(core.legs)}
        core.command(1021,set_line(PINS[::-1]).encode());core.poll(1040)
        picture=core.frame();after={leg.pin:picture[i*540:(i+1)*540] for i,leg in enumerate(core.legs)}
        self.assertEqual(after[PINS[0]],before[PINS[-1]])
        self.assertEqual(after[PINS[-1]],before[PINS[0]])
        self.assertNotEqual(before[PINS[0]],before[PINS[-1]])

    def test_firmware_pin_routing_matches_both_core_and_table_sources(self):
        program=r'''
#include <cassert>
#include "odrig_routing.h"
static const unsigned char red[3]={1,0,0},blue[3]={0,0,1};
static odrig_leg legs[2]={{1,2,1,red},{2,1,1,blue}};
extern "C" uint32_t odrig_core_leg_count(const odrig_core *) {return 2;}
extern "C" int odrig_core_leg(const odrig_core *,uint32_t i,odrig_leg *out) {if(i>=2)return 0;*out=legs[i];return 1;}
int main() {
 odrig_leg found;
 assert(OdrigRouting::onPin((odrig_core *)1,1,&found) && found.rgb==blue);
 assert(OdrigRouting::onPin(legs,2,2)->rgb==red);
 assert(OdrigRouting::onPin(legs,2,47)==nullptr);
}
'''
        with tempfile.TemporaryDirectory() as folder:
            source=pathlib.Path(folder)/'routing.cpp';source.write_text(program)
            target=pathlib.Path(folder)/'routing'
            done=subprocess.run(['c++','-std=c++11','-Wall','-Werror','-I'+str(support.ROOT/'firmware/usermod'),'-I'+str(support.CORE/'include'),str(source),'-o',str(target)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            subprocess.run([str(target)],check=True)

class MappingCli(unittest.TestCase):
    def test_mapping_forms_are_sent_without_reinterpreting_pins(self):
        from odrigctl import cli
        for words in [('mapping','get'),('mapping','test','on'),('mapping','test','off'),('mapping','set','123','1,2,3')]:
            parser=cli.parser()
            parsed=parser.parse_args(['--port','unused',*words])
            self.assertEqual(cli.command_line(parser,parsed),(' '.join(words)+'\n').encode())

class FallbackDriver(unittest.TestCase):
    def test_compiled_output_bytes_follow_pins_after_a_swap(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=pathlib.Path(folder)
            (folder/'NeoPixelBus.h').write_text(r'''
#pragma once
#include <stdint.h>
#include <vector>
struct NeoGrbFeature {};
struct NeoEsp32RmtNWs2812xMethod {};
struct NeoEsp32LcdX16Ws2812xMethod {};
typedef int NeoBusChannel;
template<class Feature,class Method> struct NeoPixelBus {
 std::vector<uint8_t> data;
 NeoPixelBus(uint16_t n,uint8_t):data(n*3){}
 NeoPixelBus(uint16_t n,uint8_t,NeoBusChannel):data(n*3){}
 void Begin(){} uint8_t *Pixels(){return data.data();}
 bool CanShow(){return true;} void Dirty(){} void Show(){}
};
''')
            (folder/'driver.cpp').write_text(r'''
#include <cassert>
#include "outputs.h"
int main(){
 const uint8_t red[]={9,0,0},blue[]={0,0,7};
 odrig_leg legs[]={{1,1,1,red},{2,2,1,blue}};
 OdrigOutputs::begin(legs,2);OdrigOutputs::fill();
 assert(OdrigOutputs::bytes(0)[1]==9);
 legs[0].pin=2;legs[1].pin=1;OdrigOutputs::fill();
 assert(OdrigOutputs::pin(0)==1 && OdrigOutputs::pin(1)==2);
 assert(OdrigOutputs::bytes(0)[2]==7 && OdrigOutputs::bytes(0)[1]==0);
 assert(OdrigOutputs::bytes(1)[1]==9 && OdrigOutputs::bytes(1)[2]==0);
}
''')
            source=support.ROOT/'firmware/standalone/src/outputs.cpp'
            program=folder/'driver'
            args=['c++','-std=c++11','-Wall','-Werror','-I'+str(folder),'-I'+str(source.parent),'-I'+str(support.ROOT/'firmware/usermod'),'-I'+str(support.CORE/'include'),str(folder/'driver.cpp'),str(source),'-o',str(program)]
            done=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            done=subprocess.run([str(program)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)


class WireTransports(unittest.TestCase):
    def test_complete_mapping_and_test_commands_over_actual_connections(self):
        from tests.emulator.support import Emulator, HAS_SERIAL, run_tool
        folder = self.enterContext(support.installed(files()))
        running = self.enterContext(Emulator(folder, tcp_port=0))
        targets = [("--http", running.url), ("--tcp", running.tcp)]
        if HAS_SERIAL:
            targets.append(("--port", running.serial))
        for offset, target in enumerate(targets, 1):
            with self.subTest(target=target[0]):
                read = run_tool(*target, "mapping", "get")
                self.assertEqual(read.status, 0, read.err)
                current = json.loads(read.out)
                pins = PINS[offset:] + PINS[:offset]
                saved = run_tool(*target, "mapping", "set", str(current["revision"]), ",".join(map(str,pins)))
                self.assertEqual(saved.status, 0, saved.err)
                after = json.loads(running.command("mapping get"))
                self.assertEqual(after["pins"], pins)
                for mode in ("on", "off"):
                    result = run_tool(*target, "mapping", "test", mode)
                    self.assertEqual(result.status, 0, result.err)
                    self.assertEqual(json.loads(running.command("mapping get"))["test"], mode == "on")

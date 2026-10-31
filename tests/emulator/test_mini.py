import base64
import json
import pathlib
import subprocess
import tempfile
import unittest

from emulator import binding, host, hub, recfile
from tests.core import support as core_support
from tests.core.test_mini import files_for, projected

from . import support


class VirtualMiniature(unittest.TestCase):
    def setUp(self):
        self.folder = support.entered(self, core_support.installed(files_for()))
        self.files = host.FolderHost(self.folder)
        self.addCleanup(self.files.close)
        self.core = binding.Core(support.LIBRARY, self.files)

    def status(self):
        return json.loads(self.core.command(0, b"status"))["mini"]

    def test_virtual_setup_acknowledges_only_supported_geometry(self):
        self.assertEqual(self.core.miniature(), (False, b""))
        self.assertFalse(self.status()["on"])
        self.assertTrue(json.loads(self.core.command(0, b"debug mini on"))["ok"])
        self.assertTrue(self.status()["on"])
        self.assertFalse(self.status()["pending"])
        self.core.feed(0, b"debug mini off\n")
        self.assertFalse(self.status()["on"])

    def test_miniature_rgb_comes_from_the_core_without_changing_normal_legs(self):
        self.core.poll(0)
        normal = self.core.frame()
        legs = self.core.legs
        self.core.command(1, b"debug mini on")
        self.core.poll(20)
        active, rgb = self.core.miniature()
        self.assertTrue(active)
        self.assertEqual(len(rgb), 180)
        self.assertLessEqual(max(rgb), 40)
        self.assertEqual(self.core.frame(), normal)
        self.assertEqual(self.core.legs, legs)
        self.assertEqual(len(normal), 10800)

    def test_switching_changes_no_files_and_reboot_starts_off(self):
        before = support.files_of(self.folder)
        self.core.command(0, b"debug mini on")
        self.core.poll(0)
        self.core.command(20, b"debug mini off")
        self.assertEqual(support.files_of(self.folder), before)
        other_files = host.FolderHost(self.folder)
        self.addCleanup(other_files.close)
        other = binding.Core(support.LIBRARY, other_files)
        self.assertFalse(json.loads(other.command(0, b"status"))["mini"]["on"])


class SlowViewer(unittest.TestCase):
    def test_normal_and_miniature_refreshes_are_coalesced_together(self):
        connection = hub.Connection()
        for n in range(10000):
            value = bytes([n % 256])
            connection.put_refresh(n, value, (True, value * 180))
        events = connection.take(0)
        self.assertEqual([kind for kind, _ in events], ["frame", "mini"])
        self.assertTrue(events[0][1].startswith("9999 "))
        miniature = json.loads(events[1][1])
        self.assertTrue(miniature["active"])
        self.assertEqual(base64.b64decode(miniature["rgb"]), bytes([9999 % 256]) * 180)
        self.assertEqual(connection.take(0), [])
        connection.put_refresh(10000, b"x", (False, b""))
        self.assertEqual(json.loads(connection.take(0)[-1][1]), {"active": False})


class MiniatureOverTransports(unittest.TestCase):
    def test_recording_keeps_full_canvas_geometry_while_miniature_is_active(self):
        with core_support.installed(files_for()) as folder, tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary, "mini.odrr")
            script = pathlib.Path(temporary, "commands.txt")
            script.write_text("0 debug mini on\n20 status\n", encoding="utf-8", newline="\n")
            done = support.run_module(folder, "--record", output, "--seconds", "1", "--script", script)
            self.assertEqual(done.status, 0, done.err)
            recorded = recfile.read(output)
            self.assertEqual(recorded.led_bytes, 10800)
            self.assertEqual(len(recorded.legs), 20)
            self.assertTrue(recorded.ticks)
            self.assertTrue(all(len(tick.data) == 10800 for tick in recorded.ticks))
            replies = [json.loads(line.split(" ", 2)[2]) for line in done.out.splitlines() if line.startswith("reply ")]
            self.assertTrue(next(reply["mini"]["on"] for reply in replies if "mini" in reply))

    def test_http_and_line_clients_share_mode_and_preview_without_changing_canvas(self):
        with core_support.installed(files_for()) as folder, support.Emulator(folder) as emulator:
            with support.EventStream(emulator.port) as stream:
                self.assertTrue(json.loads(emulator.command("debug mini on"))["ok"])
                events = stream.read_until(lambda received: any(
                    e.kind == "mini" and json.loads(e.data).get("active") for e in received), 4)
                mini = next(json.loads(e.data) for e in events
                            if e.kind == "mini" and json.loads(e.data).get("active"))
                physical = base64.b64decode(mini["rgb"])
                pixels = [[(x * 4, y * 4, (x + y) * 2) for x in range(60)] for y in range(60)]
                preview = projected(pixels)
                expected = bytes(preview[3 * (y * 10 + x) + c]
                                 for x in range(10) for y in range(6) for c in range(3))
                self.assertEqual(physical, expected)
                normal = next(e.data.split(" ", 1)[1] for e in events if e.kind == "frame")
                self.assertEqual(len(base64.b64decode(normal)), 10800)
                with support.lines(emulator) as port:
                    self.assertTrue(json.loads(port.ask("debug mini off"))["ok"])
                self.assertFalse(json.loads(emulator.command("status"))["mini"]["on"])
                off = stream.read_until(lambda received: any(
                    e.kind == "mini" and not json.loads(e.data).get("active") for e in received), 4)
                self.assertTrue(any(e.kind == "mini" for e in off))


def function_source(text, name):
    start = text.index(f"function {name}(")
    opening = text.index("{", start)
    depth = 0
    for n in range(opening, len(text)):
        depth += (text[n] == "{") - (text[n] == "}")
        if depth == 0:
            return text[start:n + 1]
    raise AssertionError("function does not end")


class MiniatureDrawing(unittest.TestCase):
    def test_front_orientation_and_hidden_or_invalid_frames(self):
        source = (support.ROOT / "emulator" / "web" / "app.js").read_text(encoding="utf-8")
        function = function_source(source, "onMini")
        script = r"""
const vm = require('node:vm');
const panel = {hidden: true};
const operations = [];
const context = {fillStyle: '', clearRect() { operations.length = 0; },
  fillRect(x,y,w,h) { operations.push([x,y,w,h,this.fillStyle]); }};
const canvas = {width:200,height:120,getContext() {return context;}};
const scope = {JSON,byId(id) {return id === 'mini-preview' ? panel : canvas;},
  bytesOf(text) {return new Uint8Array(Buffer.from(text,'base64'));}};
vm.runInNewContext(process.argv[1], scope);
const rgb = Buffer.alloc(180);
rgb[3*(2*6+0)] = 40;
rgb[3*(7*6+5)+2] = 40;
scope.onMini({data:JSON.stringify({active:true,rgb:rgb.toString('base64')})});
const active = {hidden:panel.hidden,operations:[...operations]};
scope.onMini({data:JSON.stringify({active:false})});
const off = {hidden:panel.hidden,count:operations.length};
scope.onMini({data:JSON.stringify({active:true,rgb:'AA=='})});
console.log(JSON.stringify({active,off,invalid:panel.hidden}));
"""
        done = subprocess.run(["node", "-e", script, function], capture_output=True,
                              timeout=20, check=True)
        result = json.loads(done.stdout)
        self.assertFalse(result["active"]["hidden"])
        operations = result["active"]["operations"]
        self.assertEqual(len(operations), 60)
        self.assertEqual({(w, h) for x, y, w, h, colour in operations}, {(20, 20)})
        cells = {(x, y): colour for x, y, w, h, colour in operations}
        self.assertEqual(cells[40, 100], "rgb(40,0,0)")
        self.assertEqual(cells[140, 0], "rgb(0,0,40)")
        self.assertEqual(cells[0, 0], "rgb(0,0,0)")
        self.assertEqual(result["off"], {"hidden": True, "count": 0})
        self.assertTrue(result["invalid"])


if __name__ == "__main__":
    unittest.main()

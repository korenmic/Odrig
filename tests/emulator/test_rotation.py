import json
import unittest

from emulator import binding, host
from odrig import mapping
from tests.core import support as native
from tests.core.test_mini import files_for, projected
from tests.core.test_rotation import rotated, revision
from . import support


class SquareRotation(unittest.TestCase):
    def test_native_output_and_miniature_share_all_four_permutations(self):
        pixels = [[(x * 4, y * 4, (x + y) * 2) for x in range(60)] for y in range(60)]
        with native.installed(files_for(pixels)) as folder:
            source = host.FolderHost(folder)
            self.addCleanup(source.close)
            core = binding.Core(support.LIBRARY, source)
            for tick in range(0, 400, 20):
                core.poll(tick)
            before = 0
            for i, angle in enumerate((90, 180, 270, 0)):
                now = 400 + i * 20
                state = json.loads(core.command(now, f'rotation set {revision(before)} {angle}'.encode()))
                self.assertEqual(state['degrees'], angle)
                core.command(now, b'debug mini on')
                core.poll(now)
                expected = rotated(pixels, angle)
                rgb = core.frame()
                canvas = mapping.loads(files_for()['mapping.json'].encode())
                at = 0
                for leg in canvas.legs:
                    data = bytes(c for p in native.led_pixels(canvas, leg) for c in expected[p // 60][p % 60])
                    self.assertEqual(rgb[at:at + len(data)], data)
                    at += len(data)
                preview = projected(expected)
                self.assertEqual(core.miniature()[1], bytes(preview[3 * (y * 10 + x) + c]
                                 for x in range(10) for y in range(6) for c in range(3)))
                before = angle

    def test_http_and_line_commands_share_saved_orientation_and_source_bytes(self):
        with native.installed(files_for()) as folder:
            original = support.files_of(folder)
            with support.Emulator(folder) as target:
                first = json.loads(target.command('rotation'))
                self.assertEqual(first['degrees'], 0)
                with support.lines(target) as wire:
                    changed = json.loads(wire.ask(f"rotation set {first['revision']} 90"))
                    self.assertEqual(changed['degrees'], 90)
                self.assertEqual(json.loads(target.command('rotation'))['degrees'], 90)
                read = support.run_tool('--http', f'127.0.0.1:{target.port}', 'rotation')
                self.assertEqual(read.status, 0, read.err)
                self.assertEqual(json.loads(read.out)['degrees'], 90)
            self.assertEqual(support.files_of(folder), {**original, 'rotation.txt': b'1 90\n'})
            with support.Emulator(folder) as again:
                self.assertEqual(json.loads(again.command('rotation'))['degrees'], 90)

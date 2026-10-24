import json
import pathlib
import shutil
import tempfile
import unittest
from emulator import binding, host
from tests.core import support as core_support
from . import support


class Capacity(unittest.TestCase):
    def test_absent_known_large_and_unavailable_external_capacity(self):
        with core_support.installed(core_support.example_show()) as folder, tempfile.TemporaryDirectory() as top:
            pathlib.Path(top, 'odrig').mkdir()
            class CapacityHost(host.FolderHost):
                capacity = (31 * 1024**3, 64 * 1024**3)
                def drive_space(self, generation):
                    return self.capacity
            adapter = CapacityHost(folder, drive=host.Drive(top))
            core = binding.Core(support.LIBRARY, adapter)
            try:
                expected = {'present': True, 'free': 31 * 1024**3, 'total': 64 * 1024**3, 'read_only': True}
                self.assertEqual(json.loads(core.command(0, b'space'))['external'], expected)
                for capacity in (None, (100, 99), (0, 2**53)):
                    adapter.capacity = capacity
                    self.assertEqual(json.loads(core.command(0, b'space'))['external'], {'present': True, 'free': None, 'total': None, 'read_only': True})
            finally:
                adapter.release()
            adapter = host.FolderHost(folder)
            core = binding.Core(support.LIBRARY, adapter)
            try:
                self.assertEqual(json.loads(core.command(0, b'space'))['external'], {'present': False, 'free': None, 'total': None, 'read_only': True})
            finally:
                adapter.release()

    def test_folder_capacity_is_filesystem_usage(self):
        with tempfile.TemporaryDirectory() as top:
            pathlib.Path(top, 'odrig').mkdir()
            adapter = host.FolderHost(top, drive=host.Drive(top))
            number = adapter.drive_number()
            free, total = adapter.drive_space(number)
            self.assertGreater(total, 0)
            self.assertLessEqual(free, total)
            self.assertIsNone(adapter.drive_space(number + 1))
            self.assertEqual(total, shutil.disk_usage(top).total)


class ManagementRoutes(unittest.TestCase):
    def test_cli_forwards_inclusion_and_bulk_commands_on_http_tcp_and_serial(self):
        items = [{'id': n, 'file': 'a.odrg'} for n in range(1, 4)]
        files = {'mapping.json': core_support.mapping_texts()['legs-2'], 'show.json': core_support.show_text(items), 'a.odrg': core_support.clip(1, 60, 6)}
        for route in ('http', 'tcp', *(('serial',) if support.HAS_SERIAL else ())):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as work:
                folder = support.installed(pathlib.Path(work, 'show'), files)
                with support.Emulator(folder, tcp_port=0) as emulator:
                    options = ['--http', f'127.0.0.1:{emulator.port}'] if route == 'http' else (['--tcp', emulator.tcp] if route == 'tcp' else ['--port', emulator.serial])
                    result = support.run_tool(*options, 'ignore', '1', '1')
                    self.assertEqual(result.status, 0, result.err)
                    self.assertTrue(json.loads(emulator.command('list'))['items'][0]['ignored'])
                    result = support.run_tool(*options, 'remove', 'many', '1,2')
                    self.assertEqual(result.status, 0, result.err)
                    self.assertEqual([x['id'] for x in json.loads(emulator.command('list'))['items']], [3])

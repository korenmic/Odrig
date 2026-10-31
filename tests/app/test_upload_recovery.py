"""An upload refusal can be recovered by selecting the same file again."""
import pathlib
import json
import tempfile
import unittest

from tests.emulator import support as emulator_support
from . import support
from .test_target import entered
from .test_upload import WITH_A_CANVAS, taken
from .test_catalog import Catalogs
from tests.core import support as core_support


class StorageTarget:
    def __init__(self, mode):
        self.mode = mode
        self.present = mode != 'old-internal'

    def space(self, _):
        return 200, json.dumps({'ok': True, 'free': 8000000, 'total': 10000000, 'animations': 2,
                               'external': {'present': self.present, 'free': 100000000 if self.present else None,
                                            'total': 200000000 if self.present else None, 'read_only': not self.present}})

    def catalog(self, line):
        internal = {'state': 'none', 'uncataloged': 2}
        external = {'state': 'ok', 'generation': 1, 'entries': 0, 'writable': True} if self.present else {'state': 'absent'}
        return Catalogs(internal, external).catalog(line)

    def upload(self, line):
        stage = line.split(b' ')[1]
        if stage == b'begin':
            reply = {'ok': True, 'chunk': 1500}
            if self.mode != 'old-internal':
                reply['replacing'] = False
            return 200, json.dumps(reply)
        if stage == b'expect' and self.mode == 'old-external':
            return 200, '{"ok":false,"error":"bad-argument"}'
        if stage == b'data':
            if self.mode == 'inflight' and not self.present:
                return 200, '{"ok":false,"error":"storage-error"}'
            return taken(line)
        return 200, '{"ok":true}'

    def replies(self):
        return {'status': WITH_A_CANVAS, 'list': support.LISTED, 'space': self.space,
                'catalog': self.catalog, 'upload': self.upload}


class UploadRecovery(unittest.TestCase):
    def run_recovery(self, mode, explicit=False):
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media/'ready.odrg').write_bytes(core_support.clip(7, 60, 6, (20,)*100))
        target = StorageTarget(mode)
        def absent():
            target.present = False
        def present():
            target.present = True
        steps = [absent, present] if mode == 'hotplug' else [absent] if mode in ('preflight', 'inflight') else []
        with support.StandIn(target.replies(), delay=0.02) as stand_in:
            found = support.run('ready-recovery', address=stand_in.address,
                                settings={'rows': 2, 'file': 'ready.odrg', 'mode': mode, 'explicit': explicit},
                                media=media, steps=steps).seen
            lines = [line for _, line in stand_in.lines if line.startswith(b'upload ')]
        return found, lines

    def test_absence_then_redetection_restores_default_and_a_new_form(self):
        found, lines = self.run_recovery('hotplug')
        self.assertEqual(found['default'], 'external')
        self.assertEqual(found['absent'], {'storage': 'internal', 'destination': 'Internal /ready.odrg'})
        self.assertEqual(found['returned'], 'external')
        self.assertEqual(found['nextForm'], 'external')
        self.assertEqual(lines, [])

    def test_explicit_internal_survives_redetection_only_for_this_form(self):
        found, lines = self.run_recovery('hotplug', explicit=True)
        self.assertEqual(found['returned'], 'internal')
        self.assertEqual(found['nextForm'], 'external')
        self.assertEqual(lines, [])

    def test_preflight_absence_changes_visible_destination_without_sending(self):
        found, lines = self.run_recovery('preflight')
        self.assertIn('destination changed to Internal /ready.odrg', found['message'])
        self.assertEqual(found['afterDestination'], 'Internal /ready.odrg')
        self.assertEqual(lines, [])

    def test_older_internal_firmware_is_cancelled_before_data(self):
        found, lines = self.run_recovery('old-internal')
        self.assertIn('No file bytes were sent', found['message'])
        self.assertIn(b'upload cancel', lines)
        self.assertFalse(any(line.startswith(b'upload data ') for line in lines))

    def test_older_external_firmware_is_cancelled_before_data(self):
        found, lines = self.run_recovery('old-external')
        self.assertIn('firmware lacks safe folder uploads', found['message'])
        self.assertIn(b'upload cancel', lines)
        self.assertFalse(any(line.startswith(b'upload data ') for line in lines))

    def test_removal_during_transfer_never_replays_into_internal(self):
        found, lines = self.run_recovery('inflight')
        self.assertEqual(found['frozen'], 'External /ready.odrg')
        begun = [line for line in lines if line.startswith(b'upload begin ')]
        self.assertEqual(len(begun), 1)
        self.assertTrue(begun[0].startswith(b'upload begin external '))
        self.assertNotIn('Uploaded', found['message'])

    def test_the_same_file_can_be_selected_again_after_revalidation(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media/'ready.odrg').write_bytes((folder/'hello.odrg').read_bytes())
        found = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}',
                            settings={'rows': 2, 'file': 'ready.odrg', 'send': False}, media=media).seen
        self.assertTrue(found['pickerReset'], found)

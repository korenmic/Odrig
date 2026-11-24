import json
import pathlib
import tempfile
import unittest

from . import support
from .test_clock_modes import ModeTarget


class UploadModeTarget(ModeTarget):
    def __init__(self, test, present=True):
        self.present = present
        super().__init__(test, 'only')
        if not present:
            self.only_folder = None
            self.only_state = 'no-clocks'
            self.levels[None] = self.levels[None][:2]

    def reply(self, line):
        if line == b'space':
            return self.answer(dict(ok=True, free=10000000, total=20000000,
                                    external=dict(present=True, read_only=False, free=10000000, total=20000000) if self.present else dict(present=False, read_only=True, free=None, total=None)))
        if line == b'catalog':
            return self.answer(dict(ok=True, internal=dict(state='none', uncataloged=0),
                                    external=dict(state='ok', generation=2, entries=1, writable=True) if self.present else dict(state='absent'), rebuild=None))
        status, body = super().reply(line)
        if line == b'status':
            return self.answer({**json.loads(body), 'width': 60, 'height': 60})
        return status, body


class OnlyUploadDestinations(unittest.TestCase):
    def test_missing_external_storage_cannot_fallback_to_internal_root_in_only(self):
        seen = support.run('only-upload-destination').seen
        self.assertEqual(seen['storage'], 'external')
        self.assertEqual(seen['label'], 'External /clocks/ready.odrg')
        self.assertFalse(seen['allowed'])
        self.assertIn('Clocks only', seen['error'])

    def test_internal_root_cannot_be_selected_in_only(self):
        seen = support.run('only-upload-destination', settings=dict(present=True, internal=True)).seen
        self.assertEqual(seen['storage'], 'external')
        self.assertTrue(seen['allowed'])

    def test_direct_job_cannot_bypass_the_only_destination_guard(self):
        seen = support.run('only-upload-job', settings=dict(case='upload-job')).seen
        self.assertEqual(seen, dict(begins=0, ends=0, cancels=0, error='in-use', done=False))

    def test_a_root_upload_started_off_is_cancelled_when_only_is_confirmed_before_its_data(self):
        seen = support.run('only-upload-job', settings=dict(case='upload-race')).seen
        self.assertEqual(seen, dict(begins=1, ends=0, cancels=1, error='in-use', done=False))

    def test_direct_root_preflight_is_refused_in_only(self):
        seen = support.run('only-upload-job', settings=dict(case='upload-snapshot')).seen
        self.assertEqual(seen, dict(error='in-use', mode='only'))

    def test_preflight_reads_current_policy_before_authorizing_a_prepared_root(self):
        seen = support.run('only-upload-job', settings=dict(case='upload-snapshot-race')).seen
        self.assertEqual(seen, dict(error='in-use', mode='only'))

    def test_authoring_keeps_preview_but_disables_its_internal_root_save_in_only(self):
        target = UploadModeTarget(self)
        seen = support.run('only-author', address=target.stand_in.address).seen
        self.assertTrue(seen['preview'])
        self.assertTrue(seen['disabled'])
        self.assertIn('Clocks only', seen['reason'])

    def test_ready_upload_disables_internal_and_submission_when_external_is_missing(self):
        from tests.core.test_mini import files_for
        target = UploadModeTarget(self, present=False)
        with tempfile.TemporaryDirectory() as folder:
            media = pathlib.Path(folder)
            (media / 'ready.odrg').write_bytes(files_for()['picture.odrg'])
            seen = support.run('ready-upload', address=target.stand_in.address,
                               media=media, settings=dict(rows=0, file='ready.odrg', send=False)).seen
        self.assertTrue(seen['internalDisabled'])
        self.assertTrue(seen['externalDisabled'])
        self.assertTrue(seen['uploadDisabled'])
        self.assertEqual(seen['default'], 'external')

    def test_normal_missing_external_fallback_returns_after_only_is_released(self):
        seen = support.run('only-upload-destination', settings=dict(release=True)).seen
        self.assertEqual(seen['storage'], 'internal')
        self.assertTrue(seen['allowed'])

    def test_root_draft_is_not_silently_repointed_when_only_starts(self):
        seen = support.run('only-upload-destination', settings=dict(rootDraft=True, present=True)).seen
        self.assertFalse(seen['allowed'])
        self.assertIn('Clocks only', seen['error'])
        self.assertEqual(seen['label'], 'External /ready.odrg')

    def test_authoring_save_returns_after_confirmed_exit(self):
        target = UploadModeTarget(self)
        seen = support.run('only-author', address=target.stand_in.address,
                           settings=dict(release=True), steps=[lambda: setattr(target, 'mode', 'off')]).seen
        self.assertTrue(seen['disabled'])
        self.assertTrue(seen['released'])

    def test_ready_file_still_uploads_its_original_bytes_into_clocks_on_the_native_player(self):
        from odrig import catalog
        from tests.emulator import support as emulator_support
        from .test_target import entered
        folder = entered(self, emulator_support.example_show())
        card = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        drive = card / 'odrig'
        clocks = drive / 'clocks'
        clocks.mkdir(parents=True)
        data = (folder / 'hello.odrg').read_bytes()
        (clocks / 'old.odrg').write_bytes(data)
        _, refused = catalog.rebuild(catalog.Storage(drive, drive=True),
                                     names=['clocks/old.odrg'], canvas=(60, 6))
        self.assertEqual(refused, [])
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media / 'ready.odrg').write_bytes(data)
        emulator = entered(self, emulator_support.Emulator(folder, '--drive', card))
        self.assertEqual(json.loads(emulator.command('clocks only')), dict(ok=True))
        seen = support.run('ready-upload', address=f'127.0.0.1:{emulator.port}', media=media,
                           settings=dict(rows=1, file='ready.odrg')).seen
        self.assertTrue(seen['internalDisabled'])
        self.assertFalse(seen['uploadDisabled'])
        self.assertEqual(seen['destination'], 'External /clocks/ready.odrg')
        self.assertIn('Uploaded to the card', seen['message'])
        self.assertEqual((clocks / 'ready.odrg').read_bytes(), data)
        self.assertFalse((drive / 'ready.odrg').exists())
        self.assertFalse((folder / 'ready.odrg').exists())
        self.assertEqual(json.loads(emulator.command('status'))['clock_mode'], 'only')

"""A refused folder lookup is verified before the app abandons its browsing path."""
import json
import pathlib
import shutil
import tempfile
import unittest

from odrig import catalog
from tests.emulator import support as emulator_support
from . import support
from .test_catalog import Catalogs
from .test_folders import SPACE, answer, status
from .test_target import entered


class FolderRecovery(unittest.TestCase):
    def recovery(self, *, later=False, renamed=False, removed=False, verification=False, navigation=False, nested=False, catalog_state=None):
        active = False
        failed = False
        folder = 60007
        calls = []

        def reply(line):
            nonlocal failed
            calls.append(line.decode())
            words = line.decode().split()
            if words[0] == 'status':
                return status('all', None)
            if words[0] == 'space':
                return SPACE
            if words[0] == 'catalog':
                if active and catalog_state is not None:
                    return Catalogs(dict(state='none', uncataloged=0), dict(state=catalog_state)).catalog(line)
                return answer(dict(ok=False, error='unknown-command'))
            if words[0] == 'order':
                return answer(dict(ok=False, error='unknown-command'))
            if words[0] != 'list':
                return answer(dict(ok=True))
            level = int(words[2]) if len(words) > 2 and words[1] == 'in' else None
            at = int(words[-1])
            current = 61007 if active and renamed else folder
            if level is None:
                if active and verification:
                    return answer(dict(ok=False, error='storage-error'))
                items = [] if active and (removed or catalog_state is not None) else [dict(id=current, playlist='clocks', files=6, external=True)]
            else:
                requested = 60008 if nested else folder
                if active and level == requested and (removed or renamed or catalog_state is not None or not failed and at == (3 if later else 0)):
                    failed = True
                    return answer(dict(ok=False, error='unknown-id'))
                if level not in (current, 60008):
                    return answer(dict(ok=False, error='unknown-id'))
                path = 'clocks/message' if level == 60008 else 'clocks'
                items = [dict(id=60001 + n + (10 if level == 60008 else 0), file=f'{path}/clock-{n}.odrg',
                              bytes=100, external=True) for n in range(6)]
                if level == current and nested:
                    items.insert(0, dict(id=60008, playlist='clocks/message', files=6, external=True))
            size = 3
            return answer(dict(ok=True, items=items[at:at+size], next=at+size if at+size < len(items) else None))

        def activate():
            nonlocal active
            active = True

        with support.StandIn(reply, delay=0.07) as target:
            found = support.run('folder-recovery', address=target.address,
                                settings=dict(nested=nested, navigation=navigation, verificationFailure=verification or catalog_state is not None),
                                steps=[activate]).seen
        return found, calls

    def test_a_transient_first_page_refusal_keeps_the_folder(self):
        found, _ = self.recovery()
        self.assertEqual(found, dict(path='clocks', folder=60007, ids=list(range(60001, 60007)), visitedRoot=False))

    def test_a_transient_later_page_refusal_restarts_the_listing_without_mixing_pages(self):
        found, _ = self.recovery(later=True)
        self.assertEqual(found, dict(path='clocks', folder=60007, ids=list(range(60001, 60007)), visitedRoot=False))

    def test_an_existing_path_is_resolved_again_when_its_folder_id_changes(self):
        found, _ = self.recovery(renamed=True)
        self.assertEqual(found['path'], 'clocks')
        self.assertEqual(found['folder'], 61007)
        self.assertFalse(found['visitedRoot'])

    def test_a_nested_path_is_verified_through_its_parents(self):
        found, _ = self.recovery(nested=True)
        self.assertEqual(found, dict(path='clocks/message', folder=60008, ids=list(range(60011, 60017)), visitedRoot=False))

    def test_a_failed_verification_does_not_prove_the_folder_is_gone(self):
        found, _ = self.recovery(verification=True)
        self.assertEqual(found['path'], 'clocks')
        self.assertEqual(found['ids'], list(range(60001, 60007)))
        self.assertFalse(found['visitedRoot'])

    def test_a_confirmed_removed_folder_returns_to_root(self):
        found, _ = self.recovery(removed=True)
        self.assertEqual(found['path'], '')
        self.assertEqual(found['ids'], [])

    def test_a_catalog_being_read_or_damaged_does_not_confirm_removal(self):
        for state in ('loading', 'damaged'):
            with self.subTest(state=state):
                found, _ = self.recovery(catalog_state=state)
                self.assertEqual(found['path'], 'clocks')
                self.assertEqual(found['ids'], list(range(60001, 60007)))
                self.assertFalse(found['visitedRoot'])

    def test_a_late_failure_does_not_undo_the_operators_navigation(self):
        found, _ = self.recovery(navigation=True)
        self.assertEqual(found['path'], '')


class NativeClocksBrowsing(unittest.TestCase):
    def test_actual_clock_files_remain_in_their_folder_through_repeated_page_refreshes(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        temporary = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        show = temporary/'show'
        show.mkdir()
        shutil.copyfile(root/'mapping/legs-20.json', show/'mapping.json')
        (show/'show.json').write_text(json.dumps(dict(version=1, brightness=40, items=[])), encoding='utf-8', newline='\n')
        drive = temporary/'card'/'odrig'
        original = root/'collection/card/clocks'
        names = []
        for file in original.rglob('*'):
            if file.suffix not in ('.odrg', '.odrgx'):
                continue
            relative = file.relative_to(original.parent)
            destination = drive/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, destination)
            names.append(relative.as_posix())
        _, refused = catalog.rebuild(catalog.Storage(drive, drive=True), names=names, canvas=(60, 60))
        self.assertEqual(refused, [])
        count = sum('/' not in name.removeprefix('clocks/') for name in names)
        self.assertGreater(count, 100)
        emulator = entered(self, emulator_support.Emulator(show, '--drive', drive.parent, '--drive-read-only', checked=False))
        found = support.run('folder-refresh', address=f'127.0.0.1:{emulator.port}', settings=dict(rows=count)).seen
        self.assertEqual(found, dict(path='clocks', rows=count, uniqueIds=count, visitedRoot=False, refreshes=3))

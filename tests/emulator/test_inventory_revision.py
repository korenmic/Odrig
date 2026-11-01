import json
import pathlib
import tempfile
import unittest

from emulator import binding, host
from odrig import catalog
from tests.core.test_clocks import clock_of
from tests.core.test_mini import files_for
from . import support


class InventoryRevision(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        source = files_for()
        source['another.odrg'] = source['picture.odrg']
        show = json.loads(source['show.json'])
        show['items'].append(dict(id=2, file='another.odrg'))
        source['show.json'] = json.dumps(show)
        self.folder = support.installed(self.root / 'show', source)

    def start(self, *, drive=False, managed=False):
        if drive:
            path = self.root / 'card' / 'odrig' / 'clocks'
            path.mkdir(parents=True)
            (path / 'face.odrgx').write_bytes(clock_of(canvas=(60, 60)))
            if managed:
                _, refused = catalog.rebuild(catalog.Storage(path.parent, drive=True),
                                            names=['clocks/face.odrgx'], canvas=(60, 60))
                self.assertEqual(refused, [])
        files = host.FolderHost(self.folder, drive=host.Drive(self.root / 'card') if drive else None)
        self.files = files
        self.addCleanup(files.release)
        core = binding.Core(support.LIBRARY, files)
        for now in range(0, 3001, 20):
            core.poll(now)
        return core

    def evidence(self, core, now=3000):
        answer = json.loads(core.command(now, b'catalog'))
        self.assertIn('inventory', answer)
        self.assertIsInstance(answer['inventory']['board'], str)
        return answer['inventory']

    def test_unchanged_inventory_has_a_stable_board_and_content_revision(self):
        core = self.start()
        before = self.evidence(core)
        self.assertTrue(before['authoritative'])
        for now in range(3020, 6001, 20):
            core.poll(now)
        for line in (b'off', b'on', b'brightness 20', b'clocks only', b'clocks off'):
            self.assertEqual(json.loads(core.command(6000, line)), dict(ok=True))
        self.assertEqual(before, self.evidence(core, 6000))

    def test_internal_inclusion_and_order_changes_invalidate_only_internal_revision(self):
        core = self.start()
        before = self.evidence(core)
        self.assertEqual(json.loads(core.command(3000, b'ignore 1 1')), dict(ok=True))
        after = self.evidence(core)
        self.assertNotEqual(before['internal'], after['internal'])
        self.assertEqual(before['external'], after['external'])
        order = json.loads(core.command(3000, b'order get'))
        self.assertEqual(json.loads(core.command(3000, f"order move {order['revision']} 2 1".encode())), dict(ok=True))
        moved = self.evidence(core)
        self.assertNotEqual(after['internal'], moved['internal'])
        self.assertEqual(after['external'], moved['external'])

    def test_managed_external_inclusion_changes_its_revision_without_changing_generation(self):
        core = self.start(drive=True, managed=True)
        before = self.evidence(core)
        generation = json.loads(core.command(3000, b'catalog'))['external']['generation']
        folder = next(item['id'] for item in json.loads(core.command(3000, b'list'))['items']
                      if item.get('playlist') == 'clocks')
        self.assertEqual(json.loads(core.command(3000, f'ignore {folder} 1'.encode())), dict(ok=True))
        after = self.evidence(core)
        self.assertTrue(after['authoritative'])
        self.assertNotEqual(before['external'], after['external'])
        self.assertEqual(before['internal'], after['internal'])
        self.assertEqual(before['external_keys'], after['external_keys'])
        self.assertEqual(generation, json.loads(core.command(3000, b'catalog'))['external']['generation'])

    def test_unmanaged_external_inventory_does_not_claim_authoritative_revision(self):
        core = self.start(drive=True)
        self.assertFalse(self.evidence(core)['authoritative'])

    def test_different_cards_with_equal_generation_and_entry_count_have_different_evidence(self):
        first = self.start(drive=True, managed=True)
        before = self.evidence(first)
        card = self.root / 'second-card' / 'odrig' / 'clocks'
        card.mkdir(parents=True)
        (card / 'other.odrgx').write_bytes(clock_of(canvas=(60, 60)))
        _, refused = catalog.rebuild(catalog.Storage(card.parent, drive=True),
                                    names=['clocks/other.odrgx'], canvas=(60, 60))
        self.assertEqual(refused, [])
        files = host.FolderHost(self.folder, drive=host.Drive(card.parent.parent))
        self.addCleanup(files.release)
        second = binding.Core(support.LIBRARY, files)
        for now in range(0, 3001, 20):
            second.poll(now)
        after = self.evidence(second)
        self.assertEqual(before['board'], after['board'])
        self.assertNotEqual(before['external'], after['external'])
        self.assertNotEqual(before['external_keys'], after['external_keys'])

    def test_a_failed_index_read_cannot_confirm_cached_inventory(self):
        core = self.start(drive=True, managed=True)
        self.assertTrue(self.evidence(core)['authoritative'])
        folder = next(item['id'] for item in json.loads(core.command(3000, b'list'))['items']
                      if item.get('playlist') == 'clocks')
        original = self.files.read_at
        self.files.read_at = lambda name, offset, capacity: None if name.startswith('drive/index-') else original(name, offset, capacity)
        failed = json.loads(core.command(3000, f'list in {folder}'.encode()))
        self.assertFalse(failed['ok'])
        self.assertFalse(self.evidence(core)['authoritative'])

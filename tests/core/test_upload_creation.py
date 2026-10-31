"""CRC-bearing internal begin confirms whether the chosen id would replace an item."""
import unittest

from . import support
from .test_drive import SHOW, asked, replies


class CreationConfirmation(unittest.TestCase):
    def test_crc_begin_confirms_a_new_id(self):
        reply = replies(support.start(SHOW, asked(0, 'upload begin 4 new.odrg 100 11111111')))[0]
        self.assertEqual(reply, {'ok': True, 'chunk': 1500, 'replacing': False})

    def test_crc_begin_identifies_an_existing_id_before_data(self):
        reply = replies(support.start(SHOW, asked(0, 'upload begin 1 new.odrg 100 11111111')))[0]
        self.assertEqual(reply, {'ok': True, 'chunk': 1500, 'replacing': True})

    def test_new_crc_upload_cannot_overwrite_an_unreferenced_physical_file(self):
        files = {**SHOW, 'orphan.odrg': b'keep these original bytes'}
        run, left = support.start_and_keep(files, asked(0, 'upload begin 4 orphan.odrg 100 11111111'))
        self.assertEqual(replies(run)[0], {'ok': False, 'error': 'in-use'})
        self.assertEqual(left['orphan.odrg'], files['orphan.odrg'])

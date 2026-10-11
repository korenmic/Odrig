import unittest

from fwtool import partitions

from . import support


class Parse(unittest.TestCase):
    def test_the_table_of_wleds_16_mb_layout_gives_its_six_partitions(self):
        found = partitions.parse(support.partition_table())
        self.assertEqual([(p.name, p.type, p.subtype, p.offset, p.size) for p in found], list(support.LAYOUT))

    def test_a_table_without_its_checksum_entry_is_read_too(self):
        self.assertEqual(len(partitions.parse(support.partition_table(checksum=False))), 6)

    def test_the_layout_gives_the_first_application_and_the_storage(self):
        application, storage = partitions.check(support.partition_table(), 1232640)
        self.assertEqual((application.name, application.offset, application.size), ("app0", 0x10000, 0x300000))
        self.assertEqual((storage.name, storage.offset, storage.size), ("spiffs", 0x610000, 0x9E0000))
        self.assertEqual(storage.size, 10354688)

    def test_an_image_as_large_as_the_partition_fits(self):
        partitions.check(support.partition_table(), 0x300000)


class Mismatch(unittest.TestCase):
    def mismatch(self, table, image_size=1232640):
        return support.reason_of(self, lambda: partitions.check(table, image_size))

    def test_a_table_without_spiffs_is_a_mismatch(self):
        layout = [entry for entry in support.LAYOUT if entry[0] != "spiffs"]
        self.assertEqual(self.mismatch(support.partition_table(layout)), "layout-mismatch")

    def test_an_application_partition_named_spiffs_is_no_storage(self):
        layout = [entry if entry[0] != "spiffs" else ("spiffs", 0, 0x12, 0x610000, 0x9E0000) for entry in support.LAYOUT]
        self.assertEqual(self.mismatch(support.partition_table(layout)), "layout-mismatch")

    def test_a_first_application_elsewhere_is_a_mismatch(self):
        layout = [entry if entry[0] != "app0" else ("app0", 0, 0x10, 0x20000, 0x2F0000) for entry in support.LAYOUT]
        self.assertEqual(self.mismatch(support.partition_table(layout)), "layout-mismatch")

    def test_a_data_partition_at_the_application_address_is_a_mismatch(self):
        layout = [entry if entry[0] != "app0" else ("app0", 1, 0x10, 0x10000, 0x300000) for entry in support.LAYOUT]
        self.assertEqual(self.mismatch(support.partition_table(layout)), "layout-mismatch")

    def test_an_image_larger_than_the_partition_is_a_mismatch(self):
        self.assertEqual(self.mismatch(support.partition_table(), 0x300001), "layout-mismatch")

    def test_a_wrong_magic_is_a_mismatch(self):
        self.assertEqual(self.mismatch(support.partition_table(magic=b"\xaa\x51")), "layout-mismatch")

    def test_an_erased_table_is_a_mismatch(self):
        self.assertEqual(self.mismatch(b"\xff" * support.TABLE_SIZE), "layout-mismatch")

    def test_a_table_that_does_not_match_its_checksum_is_a_mismatch(self):
        table = bytearray(support.partition_table())
        table[12] ^= 1
        self.assertEqual(self.mismatch(bytes(table)), "layout-mismatch")

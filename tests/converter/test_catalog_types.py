"""The type and the loop of each file in a catalog: ODRG files, and ODRGX containers of
frames, of text and of a widget."""

import pathlib
import tempfile
import unittest

from odrig import catalog, errors, odrgx

from . import support
from .test_catalog_format import animation

VECTORS = support.ROOT / "tests" / "vectors"
TEXT = (VECTORS / "texts" / "valid" / "hebrew.marquee.odrgx").read_bytes()
WIDGET = (VECTORS / "widgets" / "valid" / "analog.odrgx").read_bytes()
SMALL = (VECTORS / "widgets" / "valid" / "small.analog.odrgx").read_bytes()


def film(loop=200, width=60, height=60):
    """A container of the frames of `animation(8)`: three frames of 40, 60 and 100 ms."""
    return odrgx.wrap(1, width, height, loop, animation(8, width, height))


def reason_of(test, action):
    with test.assertRaises(errors.Rejection) as caught:
        action()
    return caught.exception.reason


class Entries(unittest.TestCase):
    def test_an_odrg_file_is_of_frames_with_the_sum_of_their_durations(self):
        data = animation(1)
        self.assertEqual(catalog.entry_of("sun.odrg", data), catalog.Entry("sun.odrg", len(data), catalog.crc(data), 60, 60, 200, "frames"))

    def test_a_container_has_its_type_and_the_loop_its_header_gives(self):
        for name, data, kind, loop in (("hebrew.marquee.odrgx", TEXT, "text", 3967), ("analog.odrgx", WIDGET, "widget", 30000), ("film.odrgx", film(), "frames", 200)):
            with self.subTest(kind=kind):
                self.assertEqual(catalog.entry_of(name, data), catalog.Entry(name, len(data), catalog.crc(data), 60, 60, loop, kind))

    def test_another_canvas_is_a_size_mismatch_and_none_is_not_compared(self):
        self.assertEqual(reason_of(self, lambda: catalog.entry_of("small.odrgx", SMALL)), errors.SIZE_MISMATCH)
        self.assertEqual(reason_of(self, lambda: catalog.entry_of("film.odrgx", film(width=30, height=6), canvas=(60, 60))), errors.SIZE_MISMATCH)
        entry = catalog.entry_of("small.odrgx", SMALL, canvas=None)
        self.assertEqual((entry.width, entry.height, entry.type), (21, 13, "widget"))

    def test_a_container_is_refused_with_the_reason_the_library_gives(self):
        cases = {
            VECTORS / "containers" / "invalid" / "truncated.header.odrgx": errors.TRUNCATED,
            VECTORS / "containers" / "invalid" / "unknown-type.odrgx": errors.UNKNOWN_TYPE,
            VECTORS / "containers" / "invalid" / "loop-mismatch.odrgx": errors.LOOP_MISMATCH,
            VECTORS / "texts" / "invalid" / "trailing-bytes.odrgx": errors.PAYLOAD_SIZE,
            VECTORS / "widgets" / "invalid" / "payload-size.short.odrgx": errors.PAYLOAD_SIZE,
            VECTORS / "widgets" / "invalid" / "payload-size.header.odrgx": errors.PAYLOAD_SIZE,
        }
        for path, reason in cases.items():
            with self.subTest(vector=path.name):
                self.assertEqual(reason_of(self, lambda: catalog.entry_of(path.name, path.read_bytes(), canvas=None)), reason)
        self.assertEqual(reason_of(self, lambda: catalog.entry_of("film.odrgx", film(loop=199))), errors.LOOP_MISMATCH)

    def test_the_kind_of_a_file_is_told_by_its_bytes_and_not_by_its_name(self):
        self.assertEqual(catalog.entry_of("film.odrg", film()).type, "frames")
        self.assertEqual(catalog.entry_of("clock.odrg", WIDGET).type, "widget")
        self.assertEqual(catalog.entry_of("sun.odrgx", animation(1)).type, "frames")


class Names(unittest.TestCase):
    def test_a_catalog_holds_names_ending_in_odrgx_too(self):
        for name in ("clock.odrgx", "Clock.ODRGX", "hebrew.marquee.odrgx", "x" * 94 + ".odrgx"):
            self.assertTrue(catalog.name_allowed(name), name)
        for name in ("clock.odrgxx", "clock.odrgx ", ".clock.odrgx", "x" * 95 + ".odrgx", "clock.odr"):
            self.assertFalse(catalog.name_allowed(name), name)

    def test_a_storage_lists_both_in_the_order_of_their_bytes(self):
        files = {"b.odrgx": b"", "a.odrg": b"", "C.ODRGX": b"", ".hidden.odrgx": b"", "notes.txt": b""}
        self.assertEqual(catalog.MemoryStorage(files).names(), ["C.ODRGX", "a.odrg", "b.odrgx"])
        with tempfile.TemporaryDirectory() as folder:
            for name in files:
                pathlib.Path(folder, name).write_bytes(b"")
            self.assertEqual(catalog.Storage(folder).names(), ["C.ODRGX", "a.odrg", "b.odrgx"])


class Catalogs(unittest.TestCase):
    def test_a_rebuild_records_the_type_and_the_loop_of_every_file(self):
        storage = catalog.MemoryStorage({"sun.odrg": animation(1), "hebrew.marquee.odrgx": TEXT, "analog.odrgx": WIDGET, "film.odrgx": film()})
        made, refused = catalog.rebuild(storage)
        self.assertEqual(refused, [])
        self.assertEqual(sorted((entry.name, entry.type, entry.total_ms) for entry in made.entries), [
            ("analog.odrgx", "widget", 30000), ("film.odrgx", "frames", 200), ("hebrew.marquee.odrgx", "text", 3967), ("sun.odrg", "frames", 200),
        ])
        page = storage.read(catalog.page_name(catalog.page_of("hebrew.marquee.odrgx")))
        self.assertIn(f"{catalog.crc(TEXT):08x} {len(TEXT)} 60 60 3967 text hebrew.marquee.odrgx\n".encode("ascii"), page)
        self.assertEqual(catalog.read(storage).entries, made.entries)
        self.assertEqual(catalog.check(storage), [])

    def test_an_addition_of_a_container_records_its_type(self):
        storage = catalog.MemoryStorage({"sun.odrg": animation(1)})
        catalog.rebuild(storage)
        entry = catalog.add(storage, "analog.odrgx", WIDGET)
        self.assertEqual((entry.type, entry.total_ms), ("widget", 30000))
        self.assertEqual(catalog.read(storage).entry("analog.odrgx"), entry)
        self.assertEqual(storage.read("analog.odrgx"), WIDGET)


if __name__ == "__main__":
    unittest.main()

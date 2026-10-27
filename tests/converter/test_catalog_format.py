import json
import pathlib
import random
import unittest

from odrig import catalog, errors, jsonframes, odrg

from . import support

VECTORS = support.ROOT / "tests" / "vectors"
CASES = json.loads((VECTORS / "catalog" / "cases.json").read_text(encoding="ascii"))


def animation(seed, width=60, height=60, durations=(40, 60, 100)):
    """The bytes of a small seeded ODRG file."""
    rng = random.Random(seed)
    palette = [rng.randbytes(3) for _ in range(4)]
    frames = tuple((ms, b"".join(rng.choice(palette) for _ in range(width * height))) for ms in durations)
    return odrg.encode(jsonframes.Animation(width, height, frames))


class TheVectors(unittest.TestCase):
    def test_every_vector_reads_as_its_case_says(self):
        self.assertEqual(len(CASES), 27)
        for name, wanted in sorted(CASES.items()):
            with self.subTest(vector=name):
                found = catalog.read(catalog.Storage(VECTORS / "catalog" / name))
                self.assertEqual(found.state, wanted["state"])
                if "detail" in wanted:
                    self.assertEqual(found.detail, wanted["detail"])
                if wanted["state"] == "ok":
                    self.assertEqual(found.marker.generation, wanted["generation"])
                    self.assertEqual([[entry.name, entry.bytes, entry.crc, entry.width, entry.height, entry.total_ms, entry.type] for entry in found.entries], wanted["entries"])

    def test_every_vector_folder_has_its_case(self):
        folders = {path.name for path in (VECTORS / "catalog").iterdir() if path.is_dir()}
        self.assertEqual(folders, set(CASES))

    def test_the_builder_writes_the_same_bytes_again(self):
        from .build_catalog_vectors import cases

        for name, (files, _) in cases().items():
            folder = VECTORS / "catalog" / name
            self.assertEqual({path.name: path.read_bytes() for path in folder.iterdir()}, files, name)


class TheMarker(unittest.TestCase):
    def test_it_is_409_bytes_of_18_lines_at_every_generation(self):
        for generation in (1, 0x2A, 0xFFFFFFFF):
            text = catalog.Marker(generation, (0,) * 16, (0,) * 16).text()
            self.assertEqual(len(text), 409)
            self.assertEqual(text.count(b"\n"), 18)
            self.assertEqual(catalog.parse_marker(text).generation, generation)

    def test_its_lines_are_as_the_document_gives_them(self):
        text = catalog.Marker(0x2A, (3,) + (0,) * 14 + (1,), (0x1A2B3C4D,) + (0,) * 14 + (0x9F00E1AA,)).text().decode("ascii")
        lines = text.split("\n")
        self.assertEqual(lines[0], "odrig-catalog 1 check 1 generation 0000002a")
        self.assertEqual(lines[1], "page 00 0003 1a2b3c4d")
        self.assertEqual(lines[2], "page 01 0000 00000000")
        self.assertEqual(lines[16], "page 15 0001 9f00e1aa")
        self.assertRegex(lines[17], r"^crc [0-9a-f]{8}$")
        self.assertEqual(int(lines[17][4:], 16), catalog.crc(text[:396].encode("ascii")))

    def test_the_generation_after_the_last_is_1(self):
        self.assertEqual(catalog.next_generation(0xFFFFFFFF), 1)
        self.assertEqual(catalog.next_generation(0), 1)
        self.assertEqual(catalog.next_generation(41), 42)


class Pages(unittest.TestCase):
    def test_the_page_of_a_name_is_the_low_four_bits_of_its_fnv_1a_hash(self):
        # FNV-1a of "" is 811c9dc5, of "a" e40c292c, of "foobar" bf9cf968.
        self.assertEqual((catalog.page_of(""), catalog.page_of("a"), catalog.page_of("foobar")), (5, 12, 8))

    def test_an_entry_is_one_line_in_the_documents_order(self):
        entry = catalog.Entry("Fire Swirl 2.ODRG", 734002, 0xFF, 60, 60, 61000)
        self.assertEqual(entry.line(), b"000000ff 734002 60 60 61000 frames Fire Swirl 2.ODRG\n")

    def test_the_longest_line_is_161_bytes(self):
        entry = catalog.Entry("l" * 95 + ".odrg", 4294967295, 0xFFFFFFFF, 65535, 65535, 18446744073709551615)
        self.assertEqual(len(entry.line()), 161)


class Names(unittest.TestCase):
    def test_the_names_a_catalog_may_hold(self):
        for name in ("a.odrg", "Fire Swirl 2.ODRG", "x" * 95 + ".odrg", "clip-01_b.odrg", "#1 (new).odrg"):
            self.assertTrue(catalog.name_allowed(name), name)
        for name in ("", ".hidden.odrg", " a.odrg", "a.odrg ", "a.odrg.", "x" * 96 + ".odrg", "a\\b.odrg", "a:b.odrg", "a*b.odrg", "a?b.odrg",
                     'a"b.odrg', "a<b.odrg", "a>b.odrg", "a|b.odrg", "a.txt", "caf\u00e9.odrg", "a\tb.odrg", "123"):
            self.assertFalse(catalog.name_allowed(name), name)

    def test_a_name_may_be_a_path_of_at_most_three_folders(self):
        for name in ("night/comet.odrg", "night/deep/x.odrg", "a/b/c/d.odrg", "2026/day.odrg", "a b/c.ODRGX", "x" * 50 + "/" + "y" * 44 + ".odrg"):
            self.assertTrue(catalog.name_allowed(name), name)
        for name in ("/a.odrg", "a/", "a//b.odrg", "a /b.odrg", "a. /b.odrg", ".a/b.odrg", "a/.b.odrg", "../b.odrg", "night/../x.odrg", "a/b/c/d/e.odrg",
                     "x" * 96 + "/a.odrg", "a/123", "a/b.txt", 'a"b/c.odrg', "a\\b/c.odrg", "a/b.odrg "):
            self.assertFalse(catalog.name_allowed(name), name)
        self.assertEqual(catalog.page_of("night/comet.odrg"), catalog.page_of("night/comet.odrg"))
        self.assertNotEqual(catalog.page_of("night/comet.odrg"), catalog.page_of("comet.odrg"))


class TheCommitRecord(unittest.TestCase):
    def test_it_is_read_back_whole(self):
        text = catalog.do_text(0x2B, 0x0008, [("move", "upload.part", "my sun.odrg"), ("remove", "old one.odrg")])
        self.assertEqual(text.split(b"\n")[:4], [b"odrig-catalog-do 1 generation 0000002b", b"pages 0008", b"move upload.part my sun.odrg", b"remove old one.odrg"])
        self.assertEqual(catalog.parse_do(text), (0x2B, 8, [("move", "upload.part", "my sun.odrg"), ("remove", "old one.odrg")]))

    def test_one_that_is_cut_or_changed_is_not_whole(self):
        text = catalog.do_text(1, 1, [])
        for torn in (text[:-1], text[:20], b"", text.replace(b"pages 0001", b"pages 0003")):
            self.assertIsNone(catalog.parse_do(torn), torn)


class Entries(unittest.TestCase):
    def test_an_animation_gives_its_size_crc_canvas_and_length(self):
        data = animation(1)
        entry = catalog.entry_of("one.odrg", data)
        self.assertEqual(entry, catalog.Entry("one.odrg", len(data), catalog.crc(data), 60, 60, 200, "frames"))

    def test_another_canvas_is_a_size_mismatch(self):
        with self.assertRaises(errors.Rejection) as caught:
            catalog.entry_of("small.odrg", animation(2, 4, 3))
        self.assertEqual(caught.exception.reason, errors.SIZE_MISMATCH)
        self.assertEqual(catalog.entry_of("small.odrg", animation(2, 4, 3), canvas=(4, 3)).width, 4)

    def test_every_invalid_vector_is_refused_with_its_reason(self):
        for path in sorted((VECTORS / "invalid").glob("*.odrg")):
            with self.subTest(vector=path.name):
                with self.assertRaises(errors.Rejection) as caught:
                    catalog.entry_of(path.name, path.read_bytes(), canvas=None)
                self.assertEqual(caught.exception.reason, path.name.split(".")[0])


if __name__ == "__main__":
    unittest.main()

"""A drive's catalog of version 2 and its index: the folders' files, the table and the map
that an import writes, and what an upload, a replacement, a removal, a move and a rebuild
make of them, with a cut at every storage call."""

import unittest

from odrig import catalog

from .test_catalog_format import animation

# A card of files in the root and in folders at every depth, `only` holding no file of its
# own. In the listing's order: `A.ODRG`, `b.odrg`, `a b/c.odrg`, `night/comet.odrg`,
# `night/deep/x.odrg`, `only/sub/y.odrg`.
CARD = ["b.odrg", "A.ODRG", "night/comet.odrg", "night/deep/x.odrg", "a b/c.odrg", "only/sub/y.odrg"]


def card(names=CARD):
    return catalog.MemoryStorage({name: animation(seed) for seed, name in enumerate(names)}, drive=True)


def imported(names=CARD):
    storage = card(names)
    made, refused = catalog.rebuild(storage)
    assert refused == [] and made.state == catalog.OK, (refused, made.state, made.detail)
    return storage


def lines(storage, name):
    """The lines of an index file without their padding."""
    data = storage.read(name)
    width = catalog.ID_ROW if name == catalog.IDS else catalog.ROW
    return catalog.unpadded(data, width)


def index_files(storage):
    return {name: data for name, data in storage.files.items() if name.startswith(("index-", "catalog"))}


class Interrupted(catalog.MemoryStorage):
    """A drive whose changing calls are counted, and of which the call `cut_at` is cut: a
    `write` keeps half of its bytes, a `rename` and a `remove` do not happen."""

    def __init__(self, files, cut_at):
        super().__init__(files, drive=True)
        self.calls = 0
        self.cut_at = cut_at

    def _cut(self):
        self.calls += 1
        return self.calls == self.cut_at

    def write(self, name, data):
        if self._cut():
            super().write(name, data[: len(data) // 2])
            raise Cut()
        super().write(name, data)

    def rename(self, old, new):
        if self._cut():
            raise Cut()
        super().rename(old, new)

    def remove(self, name):
        if self._cut():
            raise Cut()
        return super().remove(name)


class Cut(Exception):
    pass


class TheFiles(unittest.TestCase):
    def test_an_import_writes_the_folders_files_the_table_and_the_map_in_the_walks_order(self):
        storage = imported()
        names = ["A.ODRG", "b.odrg", "a b/c.odrg", "night/comet.odrg", "night/deep/x.odrg", "only/sub/y.odrg"]
        self.assertEqual(lines(storage, catalog.FOLDERS), [
            f"0 0 0 6 0 2 3 {catalog.crc(storage.read('index-0.txt')):08x}",
            f"1 60007 1 2 2 1 0 {catalog.crc(storage.read('index-60007.txt')):08x} a b",
            f"2 60008 1 4 3 1 1 {catalog.crc(storage.read('index-60008.txt')):08x} night",
            f"3 60009 2 4 4 1 0 {catalog.crc(storage.read('index-60009.txt')):08x} night/deep",
            f"4 60010 1 6 5 0 1 {catalog.crc(storage.read('index-60010.txt')):08x} only",
            f"5 60011 2 6 5 1 0 {catalog.crc(storage.read('index-60011.txt')):08x} only/sub",
        ])
        entry = catalog.read(storage).entry("A.ODRG")
        self.assertEqual(lines(storage, "index-0.txt"), [
            f"60001 f {entry.crc:08x} {entry.bytes} 60 60 {entry.total_ms} frames A.ODRG",
            f"60002 f {catalog.read(storage).entry('b.odrg').crc:08x} {catalog.read(storage).entry('b.odrg').bytes} 60 60 200 frames b.odrg",
            "60007 d 1 a b", "60008 d 1 night", "60010 d 0 only",
        ])
        self.assertEqual(lines(storage, "index-60010.txt"), ["60011 d 1 only/sub"])
        self.assertEqual(lines(storage, catalog.IDS), [
            "60001 f 0 0", "60002 f 0 1", "60003 f 1 0", "60004 f 2 0", "60005 f 3 0", "60006 f 5 0",
            "60007 d 1 0", "60008 d 2 0", "60009 d 3 0", "60010 d 4 0", "60011 d 5 0",
        ])
        made = catalog.read(storage)
        self.assertEqual([entry.name for entry in made.index.entries()], names)
        self.assertEqual((made.marker.folders[0], made.marker.ids[0]), (6, 11))

    def test_every_line_has_its_files_length_and_the_marker_is_of_version_2(self):
        storage = imported(CARD + [f"{'n' * 30}/{'m' * 30}/{'o' * 30}/{'p' * 2}.odrg"])
        for name, data in index_files(storage).items():
            if name.startswith("index-"):
                width = catalog.ID_ROW if name == catalog.IDS else catalog.ROW
                self.assertEqual(len(data) % width, 0, name)
                self.assertTrue(all(data[at + width - 1 : at + width] == b"\n" for at in range(0, len(data), width)), name)
        marker = storage.read(catalog.MARKER)
        self.assertEqual(len(marker), catalog.DRIVE_MARKER_SIZE)
        self.assertTrue(marker.startswith(b"odrig-catalog 2 check 1 generation 00000001\n"))
        self.assertRegex(marker.decode().split("\n")[17], r"\Afolders 0000000009 [0-9a-f]{8}\Z")
        self.assertRegex(marker.decode().split("\n")[18], r"\Aids 0000000015 [0-9a-f]{8}\Z")

    def test_an_empty_card_has_the_roots_line_alone_and_no_map(self):
        storage = catalog.MemoryStorage({}, drive=True)
        made, refused = catalog.rebuild(storage)
        self.assertEqual((made.state, refused), (catalog.OK, []))
        self.assertEqual(lines(storage, catalog.FOLDERS), ["0 0 0 1 0 0 0 00000000"])
        self.assertEqual((storage.read(catalog.IDS), storage.read("index-0.txt")), (None, None))
        self.assertEqual((made.marker.folders, made.marker.ids), ((1, catalog.crc(storage.read(catalog.FOLDERS))), (0, 0)))

    def test_each_storage_reads_only_its_own_version(self):
        storage = imported()
        inside = catalog.MemoryStorage(dict(storage.files))
        self.assertEqual((catalog.read(inside).state, catalog.read(inside).detail), (catalog.INCOMPATIBLE, "format 2, check 1"))
        flat = catalog.MemoryStorage({"sun.odrg": animation(1)})
        catalog.rebuild(flat)
        drive = catalog.MemoryStorage(dict(flat.files), drive=True)
        self.assertEqual((catalog.read(drive).state, catalog.read(drive).detail), (catalog.INCOMPATIBLE, "format 1, check 1"))

    def test_an_index_that_does_not_agree_is_damaged(self):
        for name, change, detail in [
            (catalog.FOLDERS, lambda data: None, "page"),
            ("index-60008.txt", lambda data: data.replace(b"night/comet", b"night/comex"), "page"),
            (catalog.IDS, lambda data: data[: -catalog.ID_ROW], "page"),
        ]:
            with self.subTest(name=name):
                storage = imported()
                changed = change(storage.read(name))
                if changed is None:
                    storage.remove(name)
                else:
                    storage.write(name, changed)
                made = catalog.read(storage)
                self.assertEqual((made.state, made.detail), (catalog.DAMAGED, detail))

    def test_a_row_that_agrees_with_its_crc_but_not_with_the_pages_is_damaged(self):
        storage = imported()
        rows = storage.read("index-60008.txt").replace(b"night/comet.odrg", b"night/comex.odrg")
        table = storage.read(catalog.FOLDERS).decode()
        old_crc = f"{catalog.crc(storage.read('index-60008.txt')):08x}"
        table = table.replace(old_crc, f"{catalog.crc(rows):08x}").encode()
        storage.write("index-60008.txt", rows)
        storage.write(catalog.FOLDERS, table)
        marker = catalog.parse_marker(storage.read(catalog.MARKER), drive=True)
        storage.write(catalog.MARKER, catalog.Marker(marker.generation, marker.counts, marker.crcs, (marker.folders[0], catalog.crc(table)), marker.ids).text())
        self.assertEqual((catalog.read(storage).state, catalog.read(storage).detail), (catalog.DAMAGED, "line"))

    def test_a_thousand_files_in_fifty_folders_are_indexed_every_one(self):
        names = [f"f{folder:02d}/clip-{number:02d}.odrg" for folder in range(50) for number in range(20)]
        files = {}
        made_once = animation(1)
        for name in names:
            files[name] = made_once
        storage = catalog.MemoryStorage(files, drive=True)
        made, refused = catalog.rebuild(storage)
        self.assertEqual((made.state, refused, len(made.entries)), (catalog.OK, [], 1000))
        self.assertEqual((len(made.index.folders), made.marker.ids[0]), (51, 1050))
        self.assertEqual([folder.path for folder in made.index.folders[1:3]], ["f00", "f01"])
        self.assertEqual([file_id for file_id, _ in made.index.folders[50].rows], list(range(60981, 61001)))
        self.assertEqual(made.index.folders[50].id, 61050)


class TheChanges(unittest.TestCase):
    def test_an_upload_of_a_new_file_goes_last_among_the_roots_files_with_the_lowest_free_id(self):
        storage = imported()
        catalog.remove(storage, "b.odrg")
        catalog.add(storage, "new.odrg", animation(9))
        made = catalog.read(storage)
        self.assertEqual(made.state, catalog.OK)
        self.assertEqual([(file_id, entry.name) for file_id, entry in made.index.folders[0].rows], [(60001, "A.ODRG"), (60002, "new.odrg")])
        catalog.add(storage, "zz.odrg", animation(10))
        made = catalog.read(storage)
        self.assertEqual([(file_id, entry.name) for file_id, entry in made.index.folders[0].rows][-1], (60012, "zz.odrg"))
        self.assertEqual(lines(storage, catalog.FOLDERS)[1].split()[4], "3")
        self.assertEqual(lines(storage, "index-0.txt")[3:], ["60007 d 1 a b", "60008 d 1 night", "60010 d 0 only"])

    def test_a_replacement_keeps_its_id_and_its_place_and_leaves_the_map(self):
        storage = imported()
        ids = storage.read(catalog.IDS)
        entry = catalog.add(storage, "A.ODRG", animation(20))
        made = catalog.read(storage)
        self.assertEqual(made.index.folders[0].rows[0], (60001, entry))
        self.assertEqual(storage.read(catalog.IDS), ids)

    def test_a_drives_file_is_added_to_its_root_only(self):
        storage = imported()
        with self.assertRaises(catalog.errors.Rejection):
            catalog.add(storage, "night/new.odrg", animation(9))

    def test_a_removal_takes_the_folders_left_without_a_file_out_and_their_files(self):
        storage = imported()
        catalog.remove(storage, "only/sub/y.odrg")
        made = catalog.read(storage)
        self.assertEqual(made.state, catalog.OK)
        self.assertEqual([folder.path for folder in made.index.folders], ["", "a b", "night", "night/deep"])
        self.assertEqual([name for name in storage.files if name.startswith("index-")], ["index-0.txt", "index-60007.txt", "index-60008.txt", "index-60009.txt", "index-folders.txt", "index-ids.txt"])
        self.assertEqual(lines(storage, "index-0.txt")[2:], ["60007 d 1 a b", "60008 d 1 night"])
        self.assertNotIn(60006, made.index.ids())
        catalog.remove(storage, "night/comet.odrg")
        made = catalog.read(storage)
        self.assertEqual([folder.path for folder in made.index.folders], ["", "a b", "night", "night/deep"])
        self.assertEqual(lines(storage, "index-0.txt")[3], "60008 d 0 night")
        catalog.remove(storage, "night/deep/x.odrg")
        self.assertEqual([folder.path for folder in catalog.read(storage).index.folders], ["", "a b"])

    def test_a_move_puts_a_file_before_another_or_last_in_its_folder(self):
        storage = imported(["a.odrg", "b.odrg", "c.odrg", "night/x.odrg"])
        catalog.move(storage, "c.odrg", "a.odrg")
        made = catalog.read(storage)
        self.assertEqual([(file_id, entry.name) for file_id, entry in made.index.folders[0].rows], [(60003, "c.odrg"), (60001, "a.odrg"), (60002, "b.odrg")])
        self.assertEqual(lines(storage, catalog.IDS)[:3], ["60001 f 0 1", "60002 f 0 2", "60003 f 0 0"])
        catalog.move(storage, "c.odrg")
        self.assertEqual([entry.name for _, entry in catalog.read(storage).index.folders[0].rows], ["a.odrg", "b.odrg", "c.odrg"])
        generation = catalog.read(storage).marker.generation
        catalog.move(storage, "c.odrg")
        catalog.move(storage, "a.odrg", "a.odrg")
        self.assertEqual(catalog.read(storage).marker.generation, generation)
        with self.assertRaises(catalog.errors.Rejection):
            catalog.move(storage, "a.odrg", "night/x.odrg")

    def test_a_rebuild_keeps_the_rows_order_and_puts_new_files_after_them_by_their_names(self):
        storage = imported(["a.odrg", "b.odrg", "c.odrg", "night/x.odrg", "night/y.odrg", "gone/z.odrg"])
        catalog.move(storage, "c.odrg", "a.odrg")
        catalog.move(storage, "night/y.odrg", "night/x.odrg")
        storage.remove("a.odrg")
        storage.remove("gone/z.odrg")
        storage.write("0.odrg", animation(30))
        storage.write("night/w.odrg", animation(31))
        storage.write("new/v.odrg", animation(32))
        made, refused = catalog.rebuild(storage)
        self.assertEqual((made.state, refused), (catalog.OK, []))
        self.assertEqual([(folder.path, [(file_id, entry.name) for file_id, entry in folder.rows]) for folder in made.index.folders], [
            ("", [(60001, "c.odrg"), (60002, "b.odrg"), (60003, "0.odrg")]),
            ("new", [(60004, "new/v.odrg")]),
            ("night", [(60005, "night/y.odrg"), (60006, "night/x.odrg"), (60007, "night/w.odrg")]),
        ])
        self.assertEqual([folder.id for folder in made.index.folders], [0, 60008, 60009])
        self.assertEqual(lines(storage, "index-60008.txt"), [lines(storage, "index-60008.txt")[0]])
        self.assertEqual(sorted(name for name in storage.files if name.startswith("index-")),
                         ["index-0.txt", "index-60008.txt", "index-60009.txt", "index-folders.txt", "index-ids.txt"])

    def test_a_rebuild_over_an_index_that_does_not_agree_with_its_crcs_puts_every_folder_in_the_order_of_names(self):
        storage = imported(["a.odrg", "b.odrg"])
        catalog.move(storage, "b.odrg", "a.odrg")
        storage.write("index-0.txt", storage.read("index-0.txt")[:-1] + b"!")
        made, _ = catalog.rebuild(storage)
        self.assertEqual([entry.name for _, entry in made.index.folders[0].rows], ["a.odrg", "b.odrg"])

    def test_the_record_names_each_index_file_it_puts_in_place_or_removes(self):
        storage = imported()
        finished = catalog.finish
        records = []

        def keeping(storage):
            record = storage.read(catalog.DO)
            if record is not None:
                records.append(catalog.parse_do(record))
            return finished(storage)

        catalog.finish = keeping
        try:
            catalog.add(storage, "new.odrg", animation(9))
            catalog.remove(storage, "only/sub/y.odrg")
            catalog.move(storage, "new.odrg", "A.ODRG")
        finally:
            catalog.finish = finished
        moves = [action for action in records]
        self.assertEqual(moves[0][2], [("move", "upload.part", "new.odrg"), ("move", "index-0.new", "index-0.txt"),
                                       ("move", "index-folders.new", "index-folders.txt"), ("move", "index-ids.new", "index-ids.txt")])
        self.assertEqual(moves[1][2], [("remove", "index-60010.txt"), ("remove", "index-60011.txt"), ("remove", "only/sub/y.odrg"),
                                       ("move", "index-0.new", "index-0.txt"), ("move", "index-folders.new", "index-folders.txt"),
                                       ("move", "index-ids.new", "index-ids.txt")])
        self.assertEqual(moves[2][1:], (0, [("move", "index-0.new", "index-0.txt"), ("move", "index-folders.new", "index-folders.txt"),
                                             ("move", "index-ids.new", "index-ids.txt")]))

    def test_a_cut_at_any_call_of_a_change_leaves_the_catalog_before_it_or_after_it(self):
        before = imported()
        changes = [
            lambda storage: catalog.add(storage, "new.odrg", animation(9)),
            lambda storage: catalog.remove(storage, "only/sub/y.odrg"),
            lambda storage: catalog.move(storage, "b.odrg", "A.ODRG"),
            lambda storage: catalog.rebuild(storage),
        ]
        for number, change in enumerate(changes):
            after = catalog.MemoryStorage(dict(before.files), drive=True)
            change(after)
            wanted = ({name: data for name, data in index_files(before).items()}, {name: data for name, data in index_files(after).items()})
            cut_at = 1
            while True:
                storage = Interrupted(dict(before.files), cut_at)
                try:
                    change(storage)
                except Cut:
                    pass
                else:
                    break
                again = catalog.MemoryStorage(storage.files, drive=True)
                catalog.recover(again)
                with self.subTest(change=number, cut_at=cut_at):
                    self.assertIn(index_files(again), wanted)
                    self.assertEqual(catalog.read(again).state, catalog.OK)
                cut_at += 1
            self.assertGreater(cut_at, 5)


if __name__ == "__main__":
    unittest.main()

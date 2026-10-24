import pathlib
import tempfile
import unittest

from odrig import catalog, errors

from .test_catalog_format import animation


class Cut(Exception):
    """The power went at a storage call."""


class Recording(catalog.Storage):
    """A folder whose changing calls are written down, `(call, names…)`, and of which the
    call `cut_at` (counted from 1) is cut: a `write` keeps half of its bytes, a `rename`
    and a `remove` do not happen."""

    def __init__(self, folder, cut_at=0):
        super().__init__(folder)
        self.calls = []
        self.cut_at = cut_at

    def _call(self, *call):
        self.calls.append(call)
        return len(self.calls) == self.cut_at

    def write(self, name, data):
        if self._call("write", name):
            super().write(name, data[: len(data) // 2])
            raise Cut()
        super().write(name, data)

    def rename(self, old, new):
        if self._call("rename", old, new):
            raise Cut()
        super().rename(old, new)

    def remove(self, name):
        if self._call("remove", name):
            raise Cut()
        return super().remove(name)


def folder_files(folder):
    return {path.name: path.read_bytes() for path in pathlib.Path(folder).iterdir()}


class Changes(unittest.TestCase):
    def setUp(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        self.folder = pathlib.Path(made.name)

    def storage(self, cut_at=0):
        return Recording(self.folder, cut_at)

    def started(self, names=("sun.odrg", "moon.odrg", "star.odrg")):
        """A card of these animations, imported."""
        for seed, name in enumerate(names):
            (self.folder / name).write_bytes(animation(seed))
        made, refused = catalog.rebuild(self.storage())
        self.assertEqual(refused, [])
        return made

    def test_an_import_writes_every_page_with_entries_and_the_marker(self):
        made = self.started()
        self.assertEqual(made.state, "ok")
        self.assertEqual(made.marker.generation, 1)
        self.assertEqual(sorted(entry.name for entry in made.entries), ["moon.odrg", "star.odrg", "sun.odrg"])
        pages = {catalog.page_name(catalog.page_of(name)) for name in ("sun.odrg", "moon.odrg", "star.odrg")}
        self.assertEqual(set(folder_files(self.folder)), {"sun.odrg", "moon.odrg", "star.odrg", "catalog.txt", *pages})

    def test_an_addition_writes_its_page_the_marker_and_the_record_and_moves_the_part(self):
        self.started()
        storage = self.storage()
        data = animation(7)
        entry = catalog.add(storage, "new one.odrg", data)
        page = catalog.page_of("new one.odrg")
        self.assertEqual(storage.calls, [
            ("write", "upload.part"), ("write", catalog.new_page_name(page)), ("write", "catalog.new"), ("write", "catalog.do"),
            ("rename", "upload.part", "new one.odrg"), ("rename", catalog.new_page_name(page), catalog.page_name(page)),
            ("rename", "catalog.new", "catalog.txt"), ("remove", "catalog.do"),
        ])
        after = catalog.read(storage)
        self.assertEqual(after.marker.generation, 2)
        self.assertEqual(after.entry("new one.odrg"), entry)
        self.assertEqual((self.folder / "new one.odrg").read_bytes(), data)
        self.assertNotIn("upload.part", folder_files(self.folder))

    def test_a_replacement_keeps_the_place_of_its_line(self):
        self.started(("a1.odrg", "b2.odrg", "c3.odrg", "d4.odrg", "e5.odrg", "f6.odrg", "g7.odrg", "h8.odrg", "i9.odrg", "j10.odrg", "k11.odrg", "l12.odrg",
                      "m13.odrg", "n14.odrg", "o15.odrg", "p16.odrg", "q17.odrg", "r18.odrg"))
        before = catalog.read(self.storage())
        shared = [entry.name for entry in before.entries if catalog.page_of(entry.name) == catalog.page_of(before.entries[0].name)]
        self.assertGreater(len(shared), 1)
        catalog.add(self.storage(), shared[0], animation(99))
        after = catalog.read(self.storage())
        self.assertEqual([entry.name for entry in after.entries], [entry.name for entry in before.entries])
        self.assertEqual(after.entry(shared[0]).bytes, len(animation(99)))

    def test_a_removal_removes_the_file_and_an_emptied_page(self):
        self.started(("only.odrg",))
        storage = self.storage()
        catalog.remove(storage, "only.odrg")
        page = catalog.page_of("only.odrg")
        self.assertEqual(storage.calls, [
            ("remove", catalog.new_page_name(page)), ("write", "catalog.new"), ("write", "catalog.do"),
            ("remove", "only.odrg"), ("remove", catalog.page_name(page)), ("rename", "catalog.new", "catalog.txt"), ("remove", "catalog.do"),
        ])
        self.assertEqual(set(folder_files(self.folder)), {"catalog.txt"})
        self.assertEqual(catalog.read(storage).entries, [])

    def test_a_change_of_a_storage_without_a_catalog_is_refused(self):
        (self.folder / "sun.odrg").write_bytes(animation(1))
        with self.assertRaises(catalog.Unusable) as caught:
            catalog.add(self.storage(), "moon.odrg", animation(2))
        self.assertEqual(caught.exception.state, "none")
        self.assertEqual(set(folder_files(self.folder)), {"sun.odrg"})

    def test_a_file_that_does_not_pass_leaves_nothing(self):
        self.started()
        before = folder_files(self.folder)
        with self.assertRaises(errors.Rejection) as caught:
            catalog.add(self.storage(), "bad.odrg", animation(3)[:-5])
        self.assertEqual(caught.exception.reason, errors.TRUNCATED)
        with self.assertRaises(errors.Rejection):
            catalog.add(self.storage(), "bad?.odrg", animation(3))
        self.assertEqual(folder_files(self.folder), before)

    def test_an_import_refuses_what_does_not_pass_and_lists_like_a_drive(self):
        for name, data in {"good.odrg": animation(1), "Bad.ODRG": animation(2)[:-3], "small.odrg": animation(3, 4, 3), ".hidden.odrg": animation(4),
                           "notes.txt": b"notes", "x" * 96 + ".odrg": animation(5)}.items():
            (self.folder / name).write_bytes(data)
        made, refused = catalog.rebuild(self.storage())
        self.assertEqual([entry.name for entry in made.entries], ["good.odrg"])
        self.assertEqual(sorted(refused), sorted([("Bad.ODRG", errors.TRUNCATED), ("small.odrg", errors.SIZE_MISMATCH), ("x" * 96 + ".odrg", errors.FILE_MALFORMED)]))

    def test_a_second_import_steps_the_generation_and_removes_stale_new_pages(self):
        self.started(("one.odrg",))
        stale = catalog.new_page_name((catalog.page_of("one.odrg") + 1) % 16)
        (self.folder / stale).write_bytes(b"left by a change that was not committed\n")
        made, _ = catalog.rebuild(self.storage())
        self.assertEqual(made.marker.generation, 2)
        self.assertNotIn(stale, folder_files(self.folder))

    def test_check_finds_files_that_changed_behind_the_catalog(self):
        self.started()
        (self.folder / "sun.odrg").write_bytes(animation(0) + b"x")
        data = bytearray(animation(1))
        data[-1] ^= 1
        (self.folder / "moon.odrg").write_bytes(bytes(data))
        (self.folder / "star.odrg").unlink()
        self.assertEqual(sorted(catalog.check(self.storage())), [("moon.odrg", "crc"), ("star.odrg", "missing"), ("sun.odrg", "size")])

    def test_recover_removes_what_an_uncommitted_change_left(self):
        self.started()
        for name in ("upload.part", "catalog.new", "catalog-03.new"):
            (self.folder / name).write_bytes(b"left")
        (self.folder / "catalog.do").write_bytes(b"odrig-catalog-do 1 gen")
        self.assertEqual(sorted(catalog.recover(self.storage())), ["catalog-03.new", "catalog.do", "catalog.new", "upload.part"])
        self.assertEqual(catalog.read(self.storage()).state, "ok")


class Interruptions(unittest.TestCase):
    """A change cut at each of its storage calls: after `recover`, the catalog is the one
    before or the one after, and the files agree with it."""

    def run_cut(self, prepare, change):
        whole = None
        cut_at = 1
        outcomes = set()
        while True:
            with tempfile.TemporaryDirectory() as folder:
                prepare(pathlib.Path(folder))
                before = catalog.read(catalog.Storage(folder))
                storage = Recording(folder, cut_at)
                try:
                    change(storage)
                except Cut:
                    pass
                else:
                    whole = cut_at
                catalog.recover(catalog.Storage(folder))
                after = catalog.read(catalog.Storage(folder))
                self.assertEqual(after.state, "ok", cut_at)
                for entry in after.entries:
                    data = pathlib.Path(folder, entry.name).read_bytes()
                    self.assertEqual((len(data), catalog.crc(data)), (entry.bytes, entry.crc), (cut_at, entry.name))
                outcomes.add("before" if after.marker == before.marker else "after")
            if whole is not None:
                return cut_at, outcomes
            cut_at += 1

    def card(self, names):
        def prepare(folder):
            for seed, name in enumerate(names):
                (folder / name).write_bytes(animation(seed))
            catalog.rebuild(catalog.Storage(folder))
        return prepare

    def test_an_addition(self):
        calls, outcomes = self.run_cut(self.card(("sun.odrg", "moon.odrg")), lambda storage: catalog.add(storage, "star.odrg", animation(9)))
        self.assertEqual((calls, outcomes), (9, {"before", "after"}))

    def test_a_replacement(self):
        calls, outcomes = self.run_cut(self.card(("sun.odrg", "moon.odrg")), lambda storage: catalog.add(storage, "sun.odrg", animation(9)))
        self.assertEqual((calls, outcomes), (9, {"before", "after"}))

    def test_a_removal(self):
        calls, outcomes = self.run_cut(self.card(("sun.odrg", "moon.odrg")), lambda storage: catalog.remove(storage, "moon.odrg"))
        self.assertEqual(outcomes, {"before", "after"})
        self.assertGreater(calls, 5)

    def test_an_import(self):
        calls, outcomes = self.run_cut(self.card(("sun.odrg", "moon.odrg")), lambda storage: catalog.rebuild(storage))
        self.assertEqual(outcomes, {"before", "after"})
        self.assertGreater(calls, 5)


if __name__ == "__main__":
    unittest.main()

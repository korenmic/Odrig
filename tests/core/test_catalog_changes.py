"""Changes of the internal storage keep its catalog: what each change writes, a cut and a
failure at each of its storage calls, and the same changes made by the PC library."""

import json
import unittest
import zlib

from odrig import catalog, show

from . import support
from .test_content import animation, cycle, small_show
from .test_incremental import T0, stored, touched, upload, written
from .test_powercut import POWER_CUT, as_bytes, storage_calls

# The canvas of the two-leg mapping of `small_show`.
CANVAS = (60, 6)
ITEMS = [animation(1, "one.odrg"), animation(2, "two.odrg"), cycle(3, [1, 2], 1), animation(4, "four.odrg")]


def cataloged(files, canvas=CANVAS):
    """The files with the catalog the PC library makes of the show's files."""
    files = as_bytes(files)
    storage = catalog.MemoryStorage(files)
    _, refused = catalog.rebuild(storage, names=show.files(show.loads(files["show.json"])), canvas=canvas)
    assert refused == [], refused
    return storage.files


def catalog_files(files):
    return {name: data for name, data in files.items() if name.startswith("catalog")}


def by_the_library(files, change):
    """The files after a change the PC library makes on them."""
    storage = catalog.MemoryStorage(as_bytes(files))
    change(storage)
    return storage.files


def lines(*texts, at=T0):
    return [support.line(at, text) for text in texts]


def commit_point(calls, record="catalog.do"):
    """The number of the storage call that ends the writing of the commit record: the
    change is made once it has returned."""
    opened = calls.index(f"write_open {record} 1")
    return next(at for at in range(opened, len(calls)) if calls[at].startswith("write_close")) + 1


def script_bytes(script):
    return "".join(f"{line}\n" for line in script).encode("ascii")


class Changes(unittest.TestCase):
    def setUp(self):
        self.files = cataloged(small_show(ITEMS, start=1))
        self.clip = support.clip(31, 60, 6, (20, 40, 60))

    def run_changes(self, script):
        run, left = support.start_and_keep(self.files, script, ["--trace-store"])
        self.assertIsNone(run.error)
        for name in ("catalog.new", "catalog.do", "upload.part") + tuple(catalog.new_page_name(page) for page in range(16)):
            self.assertNotIn(name, left)
        return run, left

    def test_an_upload_of_a_new_item_commits_its_entry_with_its_file(self):
        run, left = self.run_changes(upload(9, "new.odrg", self.clip) + lines("catalog"))
        found = catalog.read(catalog.MemoryStorage(left))
        self.assertEqual(found.entry("new.odrg"), catalog.Entry("new.odrg", len(self.clip), zlib.crc32(self.clip), 60, 6, 120))
        self.assertEqual(found.marker.generation, 2)
        reply = json.loads(run.lines[-1][len("reply "):])
        self.assertEqual(reply["internal"], {"state": "ok", "generation": 2, "entries": 4, "uncataloged": 0})
        self.assertEqual(left["new.odrg"], self.clip)
        self.assertEqual(catalog_files(left), catalog_files(by_the_library(self.files, lambda storage: catalog.add(storage, "new.odrg", self.clip, canvas=CANVAS))))
        page = catalog.page_of("new.odrg")
        catalog_calls = [call for call in stored(run) if "catalog" in call or call.startswith("rename upload.part")]
        self.assertEqual(catalog_calls, [
            f"write_open {catalog.new_page_name(page)} 1", "write_open catalog.new 1", "write_open catalog.do 1", "rename upload.part new.odrg 1",
            f"rename {catalog.new_page_name(page)} {catalog.page_name(page)} 1", "rename catalog.new catalog.txt 1", "remove catalog.do 1"])

    def test_a_replacement_under_its_name_is_one_commit_and_keeps_its_line(self):
        before = self.files["show.json"]
        run, left = self.run_changes(upload(2, "two.odrg", self.clip))
        self.assertEqual(left["show.json"], before)
        self.assertEqual(left["two.odrg"], self.clip)
        self.assertEqual(catalog_files(left), catalog_files(by_the_library(self.files, lambda storage: catalog.add(storage, "two.odrg", self.clip, canvas=CANVAS))))
        self.assertNotIn("write_open show.part 1", stored(run))

    def test_a_replacement_under_another_name_takes_the_old_entry_out(self):
        _, left = self.run_changes(upload(4, "newer.odrg", self.clip))
        found = catalog.read(catalog.MemoryStorage(left))
        self.assertIsNone(found.entry("four.odrg"))
        self.assertEqual(found.entry("newer.odrg").bytes, len(self.clip))
        self.assertNotIn("four.odrg", left)

    def test_a_removal_takes_its_entry_out_and_an_emptied_page_goes(self):
        _, left = self.run_changes(lines("remove 4"))
        self.assertNotIn("four.odrg", left)
        expected = by_the_library(self.files, lambda storage: catalog.commit(storage, catalog.read(storage), removed=("four.odrg",)))
        self.assertEqual(catalog_files(left), catalog_files(expected))

    def test_remove_many_takes_out_the_entries_of_the_files_that_go(self):
        files = cataloged(small_show([animation(1, "one.odrg"), animation(2, "two.odrg"), animation(4, "four.odrg"), animation(5, "two.odrg")], start=1))
        run, left = support.start_and_keep(files, lines("remove many 1,2,4"), ["--trace-store"])
        self.assertEqual(run.lines[-1], 'reply {"ok":true}')
        found = catalog.read(catalog.MemoryStorage(left))
        # Animation 5 keeps two.odrg.
        self.assertEqual(sorted(entry.name for entry in found.entries), ["two.odrg"])
        expected = by_the_library(files, lambda storage: catalog.commit(storage, catalog.read(storage), removed=("one.odrg", "four.odrg")))
        self.assertEqual(catalog_files(left), catalog_files(expected))

    def test_a_storage_without_a_catalog_gets_none_from_a_change(self):
        files = small_show(ITEMS, start=1)
        _, left = support.start_and_keep(files, upload(9, "new.odrg", self.clip) + lines("remove 4", "ignore 1 1", at=T0 + 300))
        self.assertEqual(catalog_files(left), {})

    def test_a_damaged_catalog_is_left_as_it_is_by_a_change(self):
        page = next(name for name in self.files if name.startswith("catalog-"))
        files = {**self.files, page: self.files[page][:-1]}
        _, left = support.start_and_keep(files, upload(9, "new.odrg", self.clip) + lines("remove 4", at=T0 + 300))
        self.assertEqual(catalog_files(left), catalog_files(files))


class Cuts(unittest.TestCase):
    """A cut at every storage call of a change, then a start: the catalog before the change or
    after it, and every entry of a file of the show agrees with the file."""

    def cut_everywhere(self, files, script):
        outcomes = set()
        number = 1
        while True:
            with support.installed(files) as folder:
                result = support.host("session", folder, support.CHECK_FIRST, "--cut-at", number, stdin="".join(f"{line}\n" for line in script).encode("ascii"))
                if result.status != POWER_CUT:
                    self.assertEqual(result.status, 0, result.out[-300:])
                    return number, outcomes
                support.session(folder, lines("status"))
                after = support.folder_files(folder)
            found = catalog.read(catalog.MemoryStorage(after))
            self.assertEqual(found.state, "ok", number)
            named = show.files(show.loads(after["show.json"]))
            for entry in found.entries:
                if entry.name in named:
                    self.assertEqual((len(after[entry.name]), zlib.crc32(after[entry.name])), (entry.bytes, entry.crc), (number, entry.name))
            before = catalog.read(catalog.MemoryStorage(as_bytes(files))).marker.generation
            outcomes.add("before" if found.marker.generation == before else "after")
            number += 1

    def test_an_upload_of_a_new_item(self):
        files = cataloged(small_show(ITEMS, start=1))
        calls, outcomes = self.cut_everywhere(files, upload(9, "new.odrg", support.clip(31, 60, 6)))
        self.assertEqual(outcomes, {"before", "after"})
        self.assertGreater(calls, 10)

    def test_a_replacement_under_its_name(self):
        files = cataloged(small_show(ITEMS, start=1))
        _, outcomes = self.cut_everywhere(files, upload(2, "two.odrg", support.clip(31, 60, 6)))
        self.assertEqual(outcomes, {"before", "after"})

    def test_a_removal(self):
        files = cataloged(small_show(ITEMS, start=1))
        _, outcomes = self.cut_everywhere(files, lines("remove 4"))
        self.assertEqual(outcomes, {"before", "after"})


class Failures(unittest.TestCase):
    """A storage call that fails, at every call of a change: the core goes on, and the next
    start finds the catalog after the change when the call came after the end of its commit
    record or the change succeeded, and before it otherwise, every entry of a file of the
    show agreeing with the file."""

    def fail_everywhere(self, files, script):
        calls = storage_calls(files, script)
        point = commit_point(calls)
        before = catalog.read(catalog.MemoryStorage(as_bytes(files))).marker.generation
        for at in range(1, len(calls) + 1):
            what = f"storage call {at}, `{calls[at - 1]}`, fails"
            with support.installed(files) as folder:
                result = support.host("session", folder, support.CHECK_FIRST, "--store-fails-at", at, stdin=script_bytes(script))
                self.assertEqual(result.status, 0, (what, result.out[-300:]))
                support.session(folder, lines("status"))
                after = support.folder_files(folder)
            made = json.loads([line for line in result.out.splitlines() if line.startswith("reply ")][-1][len("reply "):]).get("ok")
            found = catalog.read(catalog.MemoryStorage(after))
            self.assertEqual(found.state, "ok", what)
            self.assertEqual(found.marker.generation, before + 1 if at > point or made else before, what)
            named = show.files(show.loads(after["show.json"]))
            for entry in found.entries:
                if entry.name in named:
                    self.assertIn(entry.name, after, what)
                    self.assertEqual((len(after[entry.name]), zlib.crc32(after[entry.name])), (entry.bytes, entry.crc), (what, entry.name))
            self.assertNotIn("catalog.do", sorted(after), what)

    def test_an_upload_of_a_new_item(self):
        self.fail_everywhere(cataloged(small_show(ITEMS, start=1)), upload(9, "new.odrg", support.clip(31, 60, 6)))

    def test_a_replacement_under_its_name(self):
        self.fail_everywhere(cataloged(small_show(ITEMS, start=1)), upload(2, "two.odrg", support.clip(31, 60, 6)))

    def test_a_removal(self):
        self.fail_everywhere(cataloged(small_show(ITEMS, start=1)), lines("remove 4"))


class LeftRecord(unittest.TestCase):
    """A commit record that a failed call left is finished before the next change writes
    anything, so that a cut in that change cannot finish the old record on the new change's
    files."""

    def test_an_upload_after_a_failed_removal_of_the_record(self):
        files = cataloged(small_show(ITEMS, start=1))
        first, second = support.clip(31, 60, 6), support.clip(32, 60, 6, (20, 40))
        script = upload(9, "new.odrg", first) + upload(10, "other.odrg", second, at=T0 + 400)
        calls = storage_calls(files, script)
        failing = calls.index("remove catalog.do 1") + 1
        traced = support.start(files, script, ["--trace-store", "--store-fails-at", str(failing)])
        later = list(traced.stored) + stored(traced)
        part = [at for at, call in enumerate(later) if call == "write_open upload.part 1"][1]
        self.assertIn("remove catalog.do 1", later[failing:part], "the record is finished before the next upload's part")
        cut_at = next(at for at in range(part, len(later)) if later[at].startswith("write_close")) + 1
        with support.installed(files) as folder:
            result = support.host("session", folder, support.CHECK_FIRST, "--store-fails-at", failing, "--cut-at", cut_at, stdin=script_bytes(script))
            self.assertEqual(result.status, POWER_CUT, result.out[-300:])
            support.session(folder, lines("status"))
            after = support.folder_files(folder)
        found = catalog.read(catalog.MemoryStorage(after))
        self.assertEqual(found.state, "ok")
        self.assertEqual((found.entry("new.odrg").crc, zlib.crc32(after["new.odrg"])), (zlib.crc32(first), zlib.crc32(first)))


class Costs(unittest.TestCase):
    """What a change writes of the catalog does not grow with the library beyond its page."""

    def library(self, count):
        items = [animation(number, f"clip-{number:03d}.odrg") for number in range(1, count + 1)]
        files = {"mapping.json": support.mapping_texts()["legs-2"], "show.json": support.show_text(items, 128, None)}
        files.update({item["file"]: support.clip(item["id"], 60, 6, (20, 20)) for item in items})
        return cataloged(files)

    def test_an_addition_writes_its_page_the_marker_and_the_record_at_every_size(self):
        clip = support.clip(999, 60, 6, (20, 20, 20))
        counts = []
        for count in (16, 64, 128):
            files = self.library(count)
            run, left = support.start_and_keep(files, upload(count + 1, "added.odrg", clip), ["--trace-store"])
            calls = stored(run)
            page = catalog.page_name(catalog.page_of("added.odrg"))
            catalog_written = sum(int(call.split()[1]) for call, before in zip(calls[1:], calls) if call.startswith("write ") and "catalog" in before)
            self.assertEqual(catalog_written, len(left[page]) + len(left["catalog.txt"]) + len(catalog.do_text(2, 1, [("move", "upload.part", "added.odrg")])), count)
            self.assertEqual(touched(calls) - {"added.odrg", "upload.part", "show.part", "show.json", "pending.txt"},
                             {"catalog.txt", "catalog.new", "catalog.do", page, catalog.new_page_name(catalog.page_of("added.odrg"))})
            counts.append(len([call for call in calls if call.split()[0] in ("write_open", "rename", "remove")]))
        self.assertEqual(len(set(counts)), 1, counts)


if __name__ == "__main__":
    unittest.main()

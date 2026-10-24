"""The internal catalog at the start: what the core takes from it, what it reads as
before, and how it finishes a change that a cut interrupted."""

import json
import unittest

from odrig import catalog, show

from . import support
from .test_drive import asked, logged, replies
from .test_playback import T0
from .test_playlist import CANVAS, loop_of, show_of

VECTORS = support.ROOT / "tests" / "vectors" / "catalog"
CASES = json.loads((VECTORS / "cases.json").read_text(encoding="ascii"))

ANIMATIONS = {"one.odrg": loop_of(4, 1), "two.odrg": loop_of(6, 2), "three.odrg": loop_of(8, 3)}
SHOW = show_of([{"id": 1, "file": "one.odrg"}, {"id": 2, "file": "two.odrg"}, {"id": 3, "file": "three.odrg"}], ANIMATIONS, min_seconds=4)


def with_catalog(files, names=None):
    """The files with the catalog the PC library makes of the show's files, or of `names`."""
    storage = catalog.MemoryStorage(files)
    names = names if names is not None else show.files(show.loads(files["show.json"].encode("utf-8") if isinstance(files["show.json"], str) else files["show.json"]))
    made, refused = catalog.rebuild(storage, names=names, canvas=CANVAS)
    assert refused == [], refused
    return storage.files


def catalog_reply(run):
    return [reply for reply in replies(run) if "internal" in reply][0]


def grid(step):
    return T0 + 20 * step


class Vectors(unittest.TestCase):
    """Every vector as the internal storage of a show that names the entries the show's rule
    allows: the core finds what the PC library finds."""

    def files_of(self, name):
        found = {path.name: path.read_bytes() for path in (VECTORS / name).iterdir()}
        named = [entry for entry in ("sunrise.odrg", "moon.odrg", "a.odrg") if entry in str(found)]
        items = [{"id": number, "file": entry} for number, entry in enumerate(named or ["a.odrg"], start=1)]
        files = {"mapping.json": support.one_leg_mapping(60, 60), "show.json": json.dumps({"version": 1, "brightness": 255, "items": items})}
        return {**files, **found}

    def test_every_vector(self):
        for name, case in sorted(CASES.items()):
            for options in ([], ["--no-storage"]):
                with self.subTest(vector=name, options=options):
                    found = catalog_reply(support.start(self.files_of(name), asked(0, "catalog"), options))["internal"]
                    wanted = dict(case)
                    if name == "interrupted" and not options:
                        # A host that can change its storage finishes the change first.
                        wanted = {"state": "ok", "generation": 0x2A, "entries": [None] * 5}
                    self.assertEqual(found["state"], wanted["state"])
                    if "detail" in wanted:
                        self.assertEqual(found["detail"], wanted["detail"])
                    if wanted["state"] == "ok":
                        self.assertEqual((found["generation"], found["entries"]), (wanted["generation"], len(wanted["entries"])))


class TheStart(unittest.TestCase):
    def test_cataloged_files_are_neither_opened_nor_read_and_their_sizes_are_listed_at_once(self):
        script = asked(0, "list", "catalog") + [f"poll {grid(step)}" for step in range(1, 100)]
        run = support.start(with_catalog(SHOW), script, ["--trace-files", "--trace-calls"], check_first=False)
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], [])
        self.assertEqual([item["bytes"] for item in replies(run)[0]["items"]], [len(data) for data in ANIMATIONS.values()])
        self.assertEqual(catalog_reply(run), {"ok": True, "internal": {"state": "ok", "generation": 1, "entries": 3, "uncataloged": 0}, "external": {"state": "absent"}, "rebuild": None})
        # Nothing reads a file but the player, which plays the first animation.
        read = sum(int(line.split()[1]) for line in run.lines if line.startswith("call "))
        self.assertLess(read, len(ANIMATIONS["one.odrg"]) * 4)

    def test_a_file_of_the_show_without_an_entry_is_opened_and_read_as_before(self):
        files = with_catalog(SHOW, names=["one.odrg", "three.odrg"])
        run = support.start(files, asked(0, "list", "catalog"), ["--trace-files"], check_first=False)
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], ["two.odrg"])
        self.assertEqual([item["bytes"] for item in replies(run)[0]["items"]], [len(ANIMATIONS["one.odrg"]), None, len(ANIMATIONS["three.odrg"])])
        self.assertEqual(catalog_reply(run)["internal"]["uncataloged"], 1)
        later = support.start(files, asked(0, "list"))
        self.assertEqual([item["bytes"] for item in replies(later)[0]["items"]], [len(data) for data in ANIMATIONS.values()])

    def test_an_entry_of_another_canvas_makes_its_file_unavailable_without_reading_it(self):
        files = with_catalog(SHOW)
        storage = catalog.MemoryStorage(files)
        wide = catalog.read(storage).entry("two.odrg")
        catalog.commit(storage, catalog.read(storage), added=catalog.Entry(wide.name, wide.bytes, wide.crc, 4, 2, wide.total_ms))
        run = support.start(storage.files, asked(0, "list"), ["--trace-files"], check_first=False)
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], [])
        self.assertEqual(replies(run)[0]["items"][1]["fault"], "size-mismatch")
        self.assertIn("file two.odrg unavailable: size-mismatch", logged(run))

    def test_a_storage_without_a_catalog_is_read_as_before(self):
        run = support.start(SHOW, asked(0, "list", "catalog"), ["--trace-files"], check_first=False)
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], list(ANIMATIONS))
        self.assertEqual(catalog_reply(run)["internal"], {"state": "none", "uncataloged": 3})

    def test_a_damaged_or_incompatible_catalog_is_logged_and_the_files_are_read_as_without_one(self):
        files = with_catalog(SHOW)
        page = next(name for name in files if name.startswith("catalog-"))
        for broken, state, text in (({page: files[page][:-1]}, {"state": "damaged", "detail": "page", "uncataloged": 3}, "catalog internal damaged"),
                                    ({"catalog.txt": files["catalog.txt"].replace(b"check 1", b"check 2")}, {"state": "incompatible", "uncataloged": 3}, "catalog internal incompatible")):
            with self.subTest(text=text):
                run = support.start({**files, **broken}, asked(0, "catalog", "list"), ["--trace-files"], check_first=False)
                self.assertEqual(catalog_reply(run)["internal"], state)
                self.assertIn(text, logged(run))
                self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], list(ANIMATIONS))

    def test_a_file_whose_bytes_changed_behind_the_catalog_is_still_quarantined_by_playback(self):
        files = with_catalog(SHOW)
        files["two.odrg"] = files["two.odrg"][:-4]
        script = asked(0, "play 2") + [f"poll {grid(step)}" for step in range(1, 400)] + asked(8100, "list")
        run = support.start(files, script, check_first=False)
        self.assertEqual(replies(run)[-1]["items"][1].get("fault"), "truncated")


class Interrupted(unittest.TestCase):
    """A change cut after its commit record is finished at the start, as the PC library
    finishes it; one cut before is not."""

    def cut(self, cut_at):
        """The files of a show whose catalog's change, an addition of `four.odrg`, was cut
        at the storage call `cut_at` of the PC library."""
        files = with_catalog(SHOW)
        storage = catalog.MemoryStorage(files)
        calls = []
        original = {"write": storage.write, "rename": storage.rename, "remove": storage.remove}

        class Cut(Exception):
            pass

        def counted(kind):
            def call(*arguments):
                calls.append(kind)
                if len(calls) == cut_at:
                    raise Cut()
                return original[kind](*arguments)
            return call

        for kind in original:
            setattr(storage, kind, counted(kind))
        try:
            catalog.add(storage, "four.odrg", loop_of(2, 4), canvas=CANVAS)
        except Cut:
            pass
        return dict(storage.files)

    def test_at_every_call_after_the_commit_record_the_core_finishes_as_the_pc_library_does(self):
        # The addition's calls: the part, the page, the marker, the record, then four that
        # finish it.
        for cut_at in range(5, 9):
            with self.subTest(cut_at=cut_at):
                files = self.cut(cut_at)
                self.assertIn("catalog.do", files)
                _, kept = support.start_and_keep(files, asked(0, "status"))
                finished = catalog.MemoryStorage(files)
                catalog.finish(finished)
                self.assertEqual({name: data for name, data in kept.items() if name.startswith("catalog") or name == "four.odrg"},
                                 {name: data for name, data in finished.files.items() if name.startswith("catalog") or name == "four.odrg"})
                self.assertEqual(catalog.read(catalog.MemoryStorage(kept)).entry("four.odrg").bytes, len(loop_of(2, 4)))

    def test_before_the_commit_record_is_whole_nothing_is_finished(self):
        for cut_at in range(1, 5):
            with self.subTest(cut_at=cut_at):
                files = self.cut(cut_at)
                run, kept = support.start_and_keep(files, asked(0, "catalog"))
                self.assertEqual(catalog_reply(run)["internal"]["generation"], 1)
                self.assertEqual(kept["catalog.txt"], with_catalog(SHOW)["catalog.txt"])
                self.assertNotIn("four.odrg", kept)


if __name__ == "__main__":
    unittest.main()

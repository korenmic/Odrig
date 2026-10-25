"""`catalog rebuild` and `catalog cancel`: a storage read whole by the check's steps and its
catalog committed at the end, as the PC library makes it; progress, refusals, a cancel and a
cut at every step."""

import json
import unittest

from odrig import catalog, show

from . import support
from .test_catalog_drive import card
from .test_catalog_start import ANIMATIONS, SHOW, with_catalog
from .test_catalog_writes import a_card, folder_of
from .test_drive import asked, replies
from .test_playback import T0
from .test_playlist import CANVAS, loop_of

POWER_CUT = 75


def polls(begin, count):
    return [f"poll {T0 + begin + 20 * step}" for step in range(count)]


def catalog_files(files):
    return {name: data for name, data in files.items() if name.startswith("catalog")}


def catalog_replies(run):
    return [reply for reply in replies(run) if "rebuild" in reply]


class Internal(unittest.TestCase):
    def test_a_storage_without_a_catalog_is_imported_and_the_next_start_reads_no_animation(self):
        script = asked(0, "catalog rebuild internal") + polls(20, 400) + asked(8100, "catalog")
        run, left = support.start_and_keep(SHOW, script)
        self.assertEqual(replies(run)[0], {"ok": True})
        self.assertEqual(catalog_replies(run)[-1]["internal"], {"state": "ok", "generation": 1, "entries": 3, "uncataloged": 0})
        self.assertEqual(catalog_files(left), catalog_files(with_catalog(SHOW)))
        again = support.start(left, asked(0, "list"), ["--trace-files"], check_first=False)
        self.assertEqual([name for name, _ in again.opened if name.endswith(".odrg")], [])

    def test_its_progress_is_reported_and_readiness_is_checking_meanwhile(self):
        files = {**SHOW, **{f"more-{number}.odrg": loop_of(6, number) for number in range(3)}}
        items = json.loads(files["show.json"])["items"] + [{"id": 10 + number, "file": f"more-{number}.odrg"} for number in range(3)]
        files["show.json"] = json.dumps({**json.loads(files["show.json"]), "items": items})
        script = asked(0, "catalog rebuild internal")
        for step in range(60):
            script += asked(20 + 20 * step, "catalog", "status")
        run = support.start(files, script)
        rebuilds = [reply["rebuild"] for reply in catalog_replies(run)]
        running = [found for found in rebuilds if found is not None]
        self.assertGreater(len(running), 2)
        self.assertEqual({found["storage"] for found in running}, {"internal"})
        self.assertEqual([found["read"] + found["to_read"] for found in running], [6] * len(running))
        self.assertEqual([found["read"] for found in running], sorted(found["read"] for found in running))
        self.assertIsNone(rebuilds[-1])
        statuses = [reply for reply in replies(run) if "readiness" in reply]
        self.assertEqual(statuses[0]["readiness"], "checking")
        self.assertEqual(statuses[-1]["readiness"], "ready")

    def test_a_cancel_at_any_step_leaves_the_catalog_as_it_was_and_the_check_takes_up_the_rest(self):
        cancelled = 0
        for steps in (0, 1, 2, 3, 5, 8, 20):
            with self.subTest(steps=steps):
                script = asked(0, "catalog rebuild internal") + polls(20, steps) + asked(20 + 20 * steps, "catalog", "catalog cancel") + polls(40 + 20 * steps, 300)
                script += asked(7000 + 20 * steps, "catalog", "list")
                run, left = support.start_and_keep(SHOW, script, check_first=False)
                # A cancel after the rebuild's end finds the whole catalog, and changes nothing.
                running = catalog_replies(run)[0]["rebuild"] is not None
                cancelled += running
                self.assertEqual(catalog_files(left), {} if running else catalog_files(with_catalog(SHOW)))
                self.assertEqual(catalog_replies(run)[-1]["internal"]["state"], "none" if running else "ok")
                self.assertEqual([item["bytes"] for item in replies(run)[-1]["items"]], [len(data) for data in ANIMATIONS.values()])
        self.assertGreaterEqual(cancelled, 3)

    def test_changes_are_busy_while_it_runs(self):
        lines = ["upload begin 9 new.odrg 100", "upload begin external new.odrg 100", "remove 2", "remove many 2,3", "ignore 1 1", "order move 1 2 1",
                 "mapping set 0 1", "catalog rebuild internal", "catalog rebuild external"]
        run = support.start(SHOW, asked(0, "catalog rebuild internal", *lines))
        self.assertEqual([reply.get("error") for reply in replies(run)[1:]], ["busy"] * len(lines))

    def test_a_host_that_cannot_change_its_storage_cannot_rebuild(self):
        run = support.start(SHOW, asked(0, "catalog rebuild internal", "catalog rebuild external", "catalog rebuild", "catalog cancel"), ["--no-storage"])
        self.assertEqual([reply.get("error") for reply in replies(run)], ["read-only", "read-only", "bad-argument", None])

    def test_a_cut_at_every_storage_call_leaves_no_catalog_or_the_whole_one(self):
        script = asked(0, "catalog rebuild internal") + polls(20, 300)
        number = 1
        outcomes = set()
        whole = catalog_files(with_catalog(SHOW))
        while True:
            with support.installed(SHOW) as folder:
                result = support.host("session", folder, support.CHECK_FIRST, "--cut-at", number, stdin="".join(f"{line}\n" for line in script).encode("ascii"))
                if result.status != POWER_CUT:
                    self.assertEqual(result.status, 0, result.out[-300:])
                    break
                support.session(folder, asked(0, "status"))
                after = catalog_files(support.folder_files(folder))
            found = {name: data for name, data in after.items() if not name.endswith((".new", ".do"))}
            self.assertIn(found, ({}, whole), number)
            outcomes.add("before" if found == {} else "after")
            number += 1
        self.assertEqual(outcomes, {"before", "after"})


    def test_a_failure_at_every_storage_call_leaves_no_catalog_or_the_whole_one(self):
        script = asked(0, "catalog rebuild internal") + polls(20, 300)
        whole = catalog_files(with_catalog(SHOW))
        number = 1
        outcomes = set()
        while True:
            with support.installed(SHOW) as folder:
                result = support.host("session", folder, support.CHECK_FIRST, "--trace-store", "--store-fails-at", number,
                                      stdin="".join(f"{line}\n" for line in script).encode("ascii"))
                self.assertEqual(result.status, 0, (number, result.out[-300:]))
                if len([line for line in result.out.splitlines() if line.startswith("store ")]) < number:
                    break
                support.session(folder, asked(0, "status"))
                after = catalog_files(support.folder_files(folder))
            self.assertNotIn("catalog.do", after, number)
            found = {name: data for name, data in after.items() if not name.endswith(".new")}
            self.assertIn(found, ({}, whole), number)
            outcomes.add("before" if found == {} else "after")
            number += 1
        self.assertEqual(outcomes, {"before", "after"})


class External(unittest.TestCase):
    def test_a_card_without_a_catalog_is_imported_as_the_pc_library_imports_it(self):
        drive = {"sun.odrg": loop_of(2, 5), "Moon Rise.ODRG": loop_of(3, 6), "bad.odrg": loop_of(2, 7)[:-4], "x" * 96 + ".odrg": loop_of(2, 8)}
        with a_card(drive) as top:
            run = support.start(SHOW, asked(0, "catalog rebuild external") + polls(20, 400) + asked(8100, "catalog", "list"), ["--drive", top])
            left = folder_of(top)
        self.assertEqual(catalog_replies(run)[-1]["external"], {"state": "ok", "generation": 1, "entries": 2, "writable": True})
        storage = catalog.MemoryStorage(drive)
        _, refused = catalog.rebuild(storage, canvas=CANVAS)
        self.assertEqual(sorted(name for name, _ in refused), sorted(["bad.odrg", "x" * 96 + ".odrg"]))
        self.assertEqual(catalog_files(left), catalog_files(storage.files))
        listed = {item["file"]: item.get("fault") for item in replies(run)[-1]["items"] if item.get("external")}
        self.assertEqual(listed["bad.odrg"], "truncated")
        self.assertIn("x" * 96 + ".odrg", listed)

    def test_a_file_copied_onto_a_card_with_a_catalog_joins_after_a_rebuild(self):
        drive = {**card({"sun.odrg": loop_of(2, 5), "moon.odrg": loop_of(3, 6)}), "copied.odrg": loop_of(2, 7)}
        script = polls(0, 300) + asked(6100, "list") + asked(6120, "catalog rebuild external") + polls(6140, 400) + asked(14200, "list")
        with a_card(drive) as top:
            run = support.start(SHOW, script, ["--drive", top])
        lists = [sorted(item["file"] for item in reply["items"] if item.get("external")) for reply in replies(run) if "items" in reply]
        self.assertEqual(lists, [["moon.odrg", "sun.odrg"], ["copied.odrg", "moon.odrg", "sun.odrg"]])

    def test_the_next_plug_in_reads_the_catalog(self):
        drive = {"sun.odrg": loop_of(2, 5), "moon.odrg": loop_of(3, 6)}
        with a_card(drive) as top:
            support.start(SHOW, asked(0, "catalog rebuild external") + polls(20, 400), ["--drive", top])
            run = support.start(SHOW, polls(0, 300) + asked(6000, "catalog"), ["--drive", top, "--trace-drive"], check_first=False)
        self.assertFalse(any(line.startswith("drive list") for line in run.lines))
        self.assertEqual(catalog_replies(run)[-1]["external"]["state"], "ok")

    def test_a_drive_that_cannot_be_written_or_none_cannot_be_rebuilt(self):
        with a_card({"sun.odrg": loop_of(2, 5)}) as top:
            run = support.start(SHOW, asked(0, "catalog rebuild external"), ["--drive", top, "--drive-read-only"])
        self.assertEqual(replies(run)[0]["error"], "read-only")
        run = support.start(SHOW, asked(0, "catalog rebuild external"))
        self.assertEqual(replies(run)[0]["error"], "read-only")

    def test_a_failure_at_every_storage_call_leaves_no_catalog_or_the_one_of_the_pc_library(self):
        drive = {"sun.odrg": loop_of(2, 5), "moon.odrg": loop_of(3, 6)}
        storage = catalog.MemoryStorage(dict(drive))
        catalog.rebuild(storage, canvas=CANVAS)
        whole = catalog_files(storage.files)
        script = asked(0, "catalog rebuild external") + polls(20, 300)
        number = 1
        outcomes = set()
        while True:
            with a_card(drive) as top, support.installed(SHOW) as folder:
                result = support.host("session", folder, support.CHECK_FIRST, "--drive", top, "--trace-store", "--store-fails-at", number,
                                      stdin="".join(f"{line}\n" for line in script).encode("ascii"))
                self.assertEqual(result.status, 0, (number, result.out[-300:]))
                if len([line for line in result.out.splitlines() if line.startswith("store ")]) < number:
                    break
                support.session(folder, asked(0, "status") + polls(20, 100), ["--drive", top])
                after = catalog_files(folder_of(top))
            self.assertNotIn("catalog.do", after, number)
            found = {name: data for name, data in after.items() if not name.endswith(".new")}
            self.assertIn(found, ({}, whole), number)
            outcomes.add("before" if found == {} else "after")
            number += 1
        self.assertEqual(outcomes, {"before", "after"})

    def test_pulling_the_card_out_ends_its_rebuild(self):
        drive = {f"clip-{number:02d}.odrg": loop_of(3, number) for number in range(12)}
        with a_card(drive) as top:
            run = support.start(SHOW, asked(0, "catalog rebuild external") + polls(20, 1) + asked(40, "catalog") + ["drive pull"] + asked(60, "catalog")
                                + ["drive plug"] + polls(80, 600) + asked(12200, "catalog"), ["--drive", top])
            left = folder_of(top)
        self.assertEqual(catalog_replies(run)[0]["rebuild"]["storage"], "external")
        self.assertIsNone(catalog_replies(run)[1]["rebuild"])
        self.assertEqual(catalog_replies(run)[2]["external"]["state"], "none")
        # Pages it wrote before the card went may stay; without a record they are never read.
        self.assertEqual([name for name in catalog_files(left) if not name.endswith(".new")], [])


if __name__ == "__main__":
    unittest.main()

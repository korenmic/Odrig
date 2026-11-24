"""`folder remove <id>`: an empty folder of the board's own storage or of the card leaves
its list of folders first and its folder of the storage after it; any other folder is
refused, and only the folder named goes."""

import json
import pathlib
import unittest
import zlib

from odrig import catalog

from . import support
from .test_catalog_drive import card, drive_ids
from .test_catalog_writes import POWER_CUT, a_card, folder_of, upload_external
from .test_drive import SHOW, a_drive, asked, replies, statuses
from .test_folder_make import FILES as CARD_FILES, levels
from .test_internal_folders import FLAT, LONG_ITEMS, LONG_TEXT, foldered, items_of, kept, store_calls
from .test_mini import files_for
from .test_playback import T0
from .test_playlist import loop_of, show_of


def made_card(*paths):
    """The card of CARD_FILES with these folders made by the core, and their ids."""
    with a_card(card(CARD_FILES)) as top:
        run = support.start(SHOW, asked(0, *(f"folder make external {path}" for path in paths)), ["--drive", top])
        answers = replies(run)
        assert all(answer.get("made") for answer in answers), answers
        return folder_of(top), [answer["id"] for answer in answers]


def index_paths(files):
    found = catalog.read(catalog.MemoryStorage(files, drive=True))
    assert found.state == "ok", found
    return [folder.path for folder in found.index.folders]


def on_card(files, script, options=(), folders=()):
    """A session on a card of these files, with these empty folders on it: the run, the card's
    files afterwards and its folders."""
    with a_card(files) as top:
        for path in folders:
            pathlib.Path(top, "odrig", *path.split("/")).mkdir(parents=True, exist_ok=True)
        run = support.start(SHOW, script, ["--drive", top, *options])
        root = pathlib.Path(top, "odrig")
        return run, folder_of(top), sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir())


class TheBoardsStorage(unittest.TestCase):
    def test_an_empty_folder_leaves_its_line_and_its_numbered_folder_and_its_id_is_free_again(self):
        run, left, folders = kept(FLAT, asked(0, "folder make internal shows", "folder make internal art", "folder remove 2", "list",
                                              "folder make internal new", "status"))
        made_shows, made_art, removed, listed, made_new, status = replies(run)
        self.assertEqual((made_shows["id"], made_art["id"]), (2, 3))
        self.assertEqual(removed, {"ok": True})
        self.assertEqual([item["id"] for item in items_of(listed)], [1, 3])
        self.assertEqual(made_new, {"ok": True, "id": 2, "made": True})
        self.assertEqual(left["folders.txt"], b"odrig-folders 1 4\n2 3 0 art\n3 2 0 new\n")
        self.assertEqual(folders, ["2", "3"])
        self.assertTrue(status["ok"])
        self.assertEqual(json.loads(left["show.json"]), json.loads(FLAT["show.json"]))

    def test_a_folder_with_a_file_or_a_sub_folder_is_in_use_and_nothing_changes(self):
        files = foldered()
        run, left, _ = kept(files, asked(0, "folder remove 7", "folder remove 5", "folder remove 6"))
        self.assertEqual(replies(run), [{"ok": False, "error": "in-use"}] * 3)
        self.assertEqual(left["folders.txt"], files["folders.txt"].encode("ascii"))

    def test_a_file_listed_at_the_root_for_its_long_path_keeps_its_folder_from_going(self):
        items = [LONG_ITEMS[0], LONG_ITEMS[2]]
        files = {**show_of(items, {"four.odrg": loop_of(4, 1), items[1]["file"]: loop_of(2, 7)}, min_seconds=4), "folders.txt": LONG_TEXT}
        run, left, _ = kept(files, asked(0, "folder remove 7", "folder remove 6"))
        self.assertEqual(replies(run), [{"ok": False, "error": "in-use"}] * 2)
        self.assertEqual(left["folders.txt"], LONG_TEXT.encode("ascii"))

    def test_only_the_folder_named_goes_and_its_emptied_parent_stays_until_its_own_removal(self):
        run, left, folders = kept(FLAT, asked(0, "folder make internal shows", "folder make internal shows/night", "folder make internal art",
                                              "folder remove 2", "folder remove 3", "list", "folder remove 2", "list"))
        answers = replies(run)
        self.assertEqual(answers[3], {"ok": False, "error": "in-use"})
        self.assertEqual(answers[4], {"ok": True})
        self.assertEqual([item.get("playlist") for item in items_of(answers[5])], [None, "art", "shows"])
        self.assertEqual(answers[6], {"ok": True})
        self.assertEqual([item.get("playlist") for item in items_of(answers[7])], [None, "art"])
        self.assertEqual(left["folders.txt"], b"odrig-folders 1 4\n3 4 0 art\n")
        self.assertEqual(folders, ["3"])

    def test_the_current_playlist_removed_gives_the_root_saved_and_another_stays_current(self):
        with a_drive({}) as top, support.installed(FLAT) as show:
            run = support.session(show, asked(0, "folder make internal shows", "folder make internal art", "play 3", "status", "folder remove 2",
                                              "status") + asked(20, "status"), ["--drive", top])
            kept_art = pathlib.Path(show, "playlist.txt").read_text(encoding="ascii").splitlines()[:2]
            run_gone = support.session(show, asked(0, "folder remove 3", "status") + asked(20, "status"), ["--drive", top])
            root_saved = pathlib.Path(show, "playlist.txt").read_text(encoding="ascii").splitlines()[:2]
        answers = replies(run)
        self.assertEqual(answers[4], {"ok": True})
        self.assertEqual((answers[3]["playing"], answers[3]["playlist"]), (3, "art"))
        self.assertEqual((answers[5]["playing"], answers[5]["playlist"]), (3, "art"))
        self.assertEqual(kept_art, ["odrig-playlist 1", ":art"])
        gone = replies(run_gone)
        self.assertEqual(gone[0], {"ok": True})
        self.assertIsNone(gone[1]["playlist"])
        self.assertEqual(root_saved, ["odrig-playlist 1", ""])

    def test_the_animation_that_plays_goes_on(self):
        script = asked(0, "folder make internal shows", "status") + asked(500, "folder remove 2", "status") + asked(1000, "status")
        run, _, _ = kept(FLAT, script)
        shown = [animation for _, animation in statuses(run)]
        self.assertEqual(set(shown), {1})

    def test_its_refusals_in_their_order(self):
        upload_open = support.line(T0, "upload begin 9 new.odrg 100")
        cases = [
            ("folder remove", "bad-argument"),
            ("folder remove x", "bad-argument"),
            ("folder remove 0", "bad-argument"),
            ("folder remove 2 3", "bad-argument"),
            ("folder remove 4294967296", "bad-argument"),
            ("folder remove 1", "in-use"),
            ("folder remove 99", "unknown-id"),
            ("folder remove 4294967295", "unknown-id"),
        ]
        run, _, _ = kept(FLAT, asked(0, "folder make internal shows", *(line for line, _ in cases)))
        self.assertEqual([answer.get("error") for answer in replies(run)[1:]], [error for _, error in cases])
        run, _, _ = kept(FLAT, asked(0, "folder make internal shows") + [upload_open] + asked(0, "folder remove 2"))
        self.assertEqual(replies(run)[-1], {"ok": False, "error": "busy"})
        broken = {**FLAT, "folders.txt": "odrig-folders 1 2\nbroken\n"}
        run, _, _ = kept(broken, asked(0, "folder remove 2"))
        self.assertEqual(replies(run), [{"ok": False, "error": "storage-error"}])
        run, _, _ = kept({**FLAT, "show.json": "{"}, asked(0, "folder remove 2"))
        self.assertEqual(replies(run), [{"ok": False, "error": "show-invalid"}])

    def test_a_folder_the_storage_cannot_remove_stays_listed_nowhere(self):
        with support.installed({**FLAT, "folders.txt": "odrig-folders 1 2\n1 5 0 shows\n"}) as show:
            pathlib.Path(show, "1").mkdir()
            pathlib.Path(show, "1", "stray.odrg").write_bytes(loop_of(2, 3))
            run = support.session(show, asked(0, "folder remove 5", "list"))
            left = pathlib.Path(show, "folders.txt").read_bytes()
            stays = pathlib.Path(show, "1", "stray.odrg").exists()
        answers = replies(run)
        self.assertEqual(answers[0], {"ok": True})
        self.assertEqual([item["id"] for item in items_of(answers[1])], [1])
        self.assertEqual(left, b"odrig-folders 1 2\n")
        self.assertTrue(stays)

    def test_its_store_calls_are_the_part_its_rename_and_the_folder(self):
        run = support.start({**FLAT, "folders.txt": "odrig-folders 1 2\n1 5 0 shows\n"}, asked(0, "folder remove 5"), ["--trace-store"])
        self.assertEqual(replies(run), [{"ok": True}])
        calls = store_calls(run)
        self.assertEqual(calls[-2:], ["rename folders.part folders.txt 1", "remove 1 0"])

    def test_a_power_cut_at_each_store_call_leaves_the_old_line_or_none(self):
        start = {**FLAT, "folders.txt": "odrig-folders 1 2\n1 5 0 shows\n"}
        outcomes = set()
        for number in range(1, 40):
            with support.installed(start) as show:
                pathlib.Path(show, "1").mkdir()
                result = support.host("session", show, support.CHECK_FIRST, "--cut-at", number,
                                      stdin=(support.line(T0, "folder remove 5") + "\n").encode("ascii"))
                if result.status != POWER_CUT:
                    self.assertEqual(result.status, 0, result.out[-300:])
                    break
                after = support.session(show, asked(0, "list"))
                text = pathlib.Path(show, "folders.txt").read_bytes()
                self.assertIn(text, (b"odrig-folders 1 2\n1 5 0 shows\n", b"odrig-folders 1 2\n"), number)
                self.assertFalse(any("folders unreadable" in line for line in after.lines), number)
                rows = [item.get("playlist") for item in items_of(replies(after)[0])]
                self.assertEqual("shows" in rows, text.endswith(b"shows\n"), number)
                outcomes.add(text)
        else:
            self.fail("storage operation count exceeded the test bound")
        self.assertEqual(len(outcomes), 2)


class TheCard(unittest.TestCase):
    def test_an_empty_folder_leaves_the_index_in_one_commit_and_the_card_and_the_other_ids_stay(self):
        files, (clocks, aaa) = made_card("clocks", "night/aaa")
        before = drive_ids(files)
        run, left, folders = on_card(files, asked(0, f"folder remove {clocks}", "list", f"list in {aaa}"), folders=("clocks", "night/aaa"))
        removed, listed, inside = replies(run)
        self.assertEqual(removed, {"ok": True})
        self.assertNotIn("clocks", [item.get("playlist") for item in items_of(listed)])
        self.assertEqual(inside, {"ok": True, "items": [], "next": None})
        self.assertEqual(index_paths(left), ["", "night", "night/aaa", "night/deep", "space room"])
        self.assertEqual(drive_ids(left), before)
        self.assertNotIn("clocks", folders)
        self.assertIn("night/aaa", folders)
        for path, data in CARD_FILES.items():
            self.assertEqual(left[path], data)
        found = catalog.read(catalog.MemoryStorage(left, drive=True))
        self.assertEqual(found.marker.generation, 4)
        for entry in found.entries:
            self.assertEqual(zlib.crc32(left[entry.name]), entry.crc)

    def test_folders_after_it_keep_their_ids_and_their_levels(self):
        files, (aaa, zzz) = made_card("night/aaa", "night/zzz")
        deep = next(folder.id for folder in catalog.read(catalog.MemoryStorage(files, drive=True)).index.folders if folder.path == "night/deep")
        run, left, _ = on_card(files, asked(0, f"folder remove {aaa}", f"list in {deep}", f"list in {zzz}", "list"), folders=("night/aaa", "night/zzz"))
        removed, deep_level, zzz_level, root = replies(run)
        self.assertEqual(removed, {"ok": True})
        self.assertEqual([item.get("file") for item in deep_level["items"]], ["night/deep/old.odrg"])
        self.assertEqual(zzz_level["items"], [])
        self.assertEqual(index_paths(left), ["", "night", "night/deep", "night/zzz", "space room"])
        rows = {item.get("playlist"): item["id"] for item in root["items"] if "playlist" in item}
        self.assertEqual(rows["night"], next(folder.id for folder in catalog.read(catalog.MemoryStorage(files, drive=True)).index.folders if folder.path == "night"))

    def test_a_folder_with_a_file_or_a_sub_folder_is_in_use(self):
        files = card(CARD_FILES)
        ids = {folder.path: folder.id for folder in catalog.read(catalog.MemoryStorage(files, drive=True)).index.folders}
        run, left, _ = on_card(files, asked(0, f"folder remove {ids['night']}", f"folder remove {ids['night/deep']}", f"folder remove {ids['space room']}"))
        self.assertEqual(replies(run), [{"ok": False, "error": "in-use"}] * 3)
        self.assertEqual(left, files)

    def test_an_animation_of_the_card_is_in_use_and_an_id_nothing_has_is_unknown(self):
        files = card(CARD_FILES)
        animation = drive_ids(files)["root.odrg"]
        run, _, _ = on_card(files, asked(0, f"folder remove {animation}", "folder remove 70000"))
        self.assertEqual(replies(run), [{"ok": False, "error": "in-use"}, {"ok": False, "error": "unknown-id"}])

    def test_a_current_card_playlist_after_it_is_found_again_and_a_removed_one_gives_the_root(self):
        files, (aaa, zzz) = made_card("night/aaa", "night/zzz")
        run, _, _ = on_card(files, asked(0, f"play {zzz}", f"folder remove {aaa}", "status") + asked(20, "status"), folders=("night/aaa", "night/zzz"))
        answers = replies(run)
        self.assertEqual(answers[1], {"ok": True})
        self.assertEqual((answers[2]["playing"], answers[2]["playlist"]), (zzz, "night/zzz"))
        self.assertEqual((answers[3]["playing"], answers[3]["playlist"]), (zzz, "night/zzz"))
        run, _, _ = on_card(files, asked(0, f"play {zzz}", f"folder remove {zzz}", "status") + asked(20, "status"), folders=("night/aaa", "night/zzz"))
        answers = replies(run)
        self.assertEqual(answers[1], {"ok": True})
        self.assertIsNone(answers[3]["playlist"])

    def test_an_empty_clocks_folder_may_be_removed_and_status_reports_a_card_without_it(self):
        files, (clocks,) = made_card("clocks")
        script = asked(0, "clocks only") + asked(100, "status") + asked(200, f"folder remove {clocks}") + asked(400, "status")
        run, left, _ = on_card(files, script, folders=("clocks",))
        answers = replies(run)
        self.assertEqual(answers[2], {"ok": True})
        without, _, _ = on_card(card(CARD_FILES), asked(0, "clocks only") + asked(400, "status"))
        self.assertEqual(answers[3]["clock_only"], replies(without)[1]["clock_only"])
        self.assertNotIn("clocks", index_paths(left))

    def test_a_folder_on_the_card_that_holds_a_file_the_index_does_not_know_stays_listed_nowhere_and_is_made_again(self):
        files, (clocks,) = made_card("clocks")
        with a_card({**files, "clocks/notes.txt": b"notes"}) as top:
            run = support.start(SHOW, asked(0, f"folder remove {clocks}", "list", "folder make external clocks"), ["--drive", top])
            there = pathlib.Path(top, "odrig", "clocks", "notes.txt").exists()
            left = folder_of(top)
        removed, listed, made = replies(run)
        self.assertEqual(removed, {"ok": True})
        self.assertNotIn("clocks", [item.get("playlist") for item in items_of(listed)])
        self.assertTrue(made["made"])
        self.assertTrue(there)
        self.assertIn("clocks", index_paths(left))

    def test_a_read_only_card_a_stick_a_test_that_shows_and_an_open_upload_are_refused(self):
        files, (clocks,) = made_card("clocks")
        run, left, _ = on_card(files, asked(0, f"folder remove {clocks}"), options=("--drive-read-only",), folders=("clocks",))
        self.assertEqual(replies(run), [{"ok": False, "error": "read-only"}])
        self.assertEqual(left, files)
        with a_card(files) as top:
            pathlib.Path(top, "odrig", "clocks").mkdir()
            run = support.start(files_for(), asked(0, "mapping test on", f"folder remove {clocks}", "mapping test off", f"folder remove {clocks}"), ["--drive", top])
        self.assertEqual(replies(run), [{"ok": True}, {"ok": False, "error": "busy"}, {"ok": True}, {"ok": True}])
        run, _, _ = on_card(files, [support.line(T0, "upload begin external x.odrg 100")] + asked(0, f"folder remove {clocks}"), folders=("clocks",))
        self.assertEqual(replies(run)[-1], {"ok": False, "error": "busy"})
        stick = {"night/b.odrg": loop_of(2, 5), "c.odrg": loop_of(3, 6)}
        run, _, _ = on_card(stick, asked(0, "list"))
        night = next(item["id"] for item in items_of(replies(run)[0]) if item.get("playlist") == "night")
        run, left, _ = on_card(stick, asked(0, "list", f"folder remove {night}"))
        self.assertEqual(replies(run)[-1], {"ok": False, "error": "read-only"})
        self.assertEqual(left, stick)

    def test_a_card_folders_id_is_unknown_while_the_card_is_out_and_its_folder_goes_once_it_is_back(self):
        files, (clocks,) = made_card("clocks")
        script = asked(0, "status") + ["drive pull"] + asked(20, f"folder remove {clocks}") + ["drive plug"]
        script += [f"poll {T0 + 40 + 20 * step}" for step in range(300)] + asked(6100, f"folder remove {clocks}")
        run, left, _ = on_card(files, script, folders=("clocks",))
        answers = replies(run)
        self.assertEqual(answers[1], {"ok": False, "error": "unknown-id"})
        self.assertEqual(answers[2], {"ok": True})
        self.assertNotIn("clocks", index_paths(left))

    def test_a_power_cut_at_each_storage_call_leaves_the_old_index_or_the_new_one(self):
        files, (clocks,) = made_card("clocks")
        outcomes = set()
        for number in range(1, 80):
            with a_card(files) as top, support.installed(SHOW) as show:
                pathlib.Path(top, "odrig", "clocks").mkdir()
                result = support.host("session", show, support.CHECK_FIRST, "--drive", top, "--cut-at", number,
                                      stdin=(support.line(T0, f"folder remove {clocks}") + "\n").encode("ascii"))
                if result.status != POWER_CUT:
                    self.assertEqual(result.status, 0, result.out[-300:])
                    break
                support.session(show, asked(0, "status"), ["--drive", top])
                after = folder_of(top)
            found = catalog.read(catalog.MemoryStorage(after, drive=True))
            self.assertEqual(found.state, "ok", number)
            outcomes.add(found.marker.generation)
            for entry in found.entries:
                self.assertEqual(zlib.crc32(after[entry.name]), entry.crc, number)
            self.assertEqual("clocks" in [folder.path for folder in found.index.folders], found.marker.generation == 2, number)
        else:
            self.fail("storage operation count exceeded the test bound")
        self.assertEqual(outcomes, {2, 3})

    def test_an_upload_into_the_parent_after_a_removal_keeps_the_index_sound(self):
        files, (aaa,) = made_card("night/aaa")
        data = loop_of(4, 9)
        run, left, _ = on_card(files, asked(0, f"folder remove {aaa}") + upload_external("night/new.odrg", data, T0 + 100), folders=("night/aaa",))
        self.assertEqual(replies(run)[0], {"ok": True})
        self.assertTrue(replies(run)[-1]["ok"], replies(run)[-1])
        self.assertEqual(left["night/new.odrg"], data)
        self.assertEqual(index_paths(left), ["", "night", "night/deep", "space room"])
        self.assertEqual(levels(left)["night"]["files"], 2)


if __name__ == "__main__":
    unittest.main()

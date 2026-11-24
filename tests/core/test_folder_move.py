"""`move internal <folder id> <path>`: a folder of the board's own storage moved or renamed by
one rewrite of `folders.txt`, its sub-folders with it, every id, number, stored name, setting
and file kept; its refusals in their order; what follows the move."""

import json
import pathlib
import unittest

from . import support
from .test_drive import a_drive, asked, logged, refusal, replies, statuses
from .test_internal_folders import LONG_ITEMS, LONG_TEXT, POWER_CUT, every, foldered, items_of, kept, played, store_calls
from .test_playback import T0
from .test_playlist import loop_of, show_of

# A deeper tree: `art` (1, id 20), `old` (5, id 24, ignored), `shows` (2, id 21),
# `shows/night` (3, id 22), `shows/night/deep` (4, id 23), each holding one file.
DEEP_TEXT = "odrig-folders 1 6\n1 20 0 art\n5 24 1 old\n2 21 0 shows\n3 22 0 shows/night\n4 23 0 shows/night/deep\n"
DEEP_ITEMS = [{"id": 1, "file": "four.odrg"}, {"id": 11, "file": "2/a.odrg"}, {"id": 12, "file": "3/b.odrg"}, {"id": 13, "file": "4/c.odrg"},
              {"id": 14, "file": "1/d.odrg"}]
DEEP_FILES = {"four.odrg": loop_of(4, 1), "2/a.odrg": loop_of(2, 5), "3/b.odrg": loop_of(2, 6), "4/c.odrg": loop_of(2, 7), "1/d.odrg": loop_of(2, 8)}


def deep(text=DEEP_TEXT, items=DEEP_ITEMS, files=DEEP_FILES):
    return {**show_of(items, files, min_seconds=4), "folders.txt": text}


class Moving(unittest.TestCase):
    def test_a_rename_keeps_every_line_and_file_and_takes_its_place_among_its_siblings(self):
        files = deep()
        run, left, folders = kept(files, asked(0, "move internal 21 programs", "list", "list in 21", "list in 23"))
        answer, root, programs, deepest = replies(run)
        self.assertEqual(answer, {"ok": True, "id": 21, "moved": True})
        self.assertEqual(left["folders.txt"].decode("ascii"),
                         "odrig-folders 1 6\n1 20 0 art\n5 24 1 old\n2 21 0 programs\n3 22 0 programs/night\n4 23 0 programs/night/deep\n")
        self.assertEqual([item.get("playlist") for item in items_of(root) if "playlist" in item], ["art", "old", "programs"])
        self.assertEqual([(item["id"], item.get("file"), item.get("stored")) for item in items_of(programs)],
                         [(22, None, None), (11, "programs/a.odrg", "2/a.odrg")])
        self.assertEqual(items_of(programs)[0]["playlist"], "programs/night")
        self.assertEqual([(item["id"], item["file"], item["stored"]) for item in items_of(deepest)], [(13, "programs/night/deep/c.odrg", "4/c.odrg")])
        for name, data in files.items():
            if name != "folders.txt":
                self.assertEqual(left[name], data.encode("ascii") if isinstance(data, str) else data, name)
        self.assertEqual(folders, ["1", "2", "3", "4"])

    def test_a_move_to_another_parent_to_the_root_and_from_the_root_to_depth_three(self):
        cases = {
            "move internal 22 art/night": "odrig-folders 1 6\n1 20 0 art\n3 22 0 art/night\n4 23 0 art/night/deep\n5 24 1 old\n2 21 0 shows\n",
            "move internal 23 deep": "odrig-folders 1 6\n1 20 0 art\n4 23 0 deep\n5 24 1 old\n2 21 0 shows\n3 22 0 shows/night\n",
            "move internal 20 shows/night/art": "odrig-folders 1 6\n5 24 1 old\n2 21 0 shows\n3 22 0 shows/night\n1 20 0 shows/night/art\n4 23 0 shows/night/deep\n",
            "move internal 24 shows/old": "odrig-folders 1 6\n1 20 0 art\n2 21 0 shows\n3 22 0 shows/night\n4 23 0 shows/night/deep\n5 24 1 shows/old\n",
        }
        for line, text in cases.items():
            with self.subTest(line=line):
                run, left, _ = kept(deep(), asked(0, line))
                self.assertTrue(replies(run)[0]["moved"], replies(run))
                self.assertEqual(left["folders.txt"].decode("ascii"), text)

    def test_its_own_path_answers_not_moved_and_writes_nothing(self):
        run = support.start(deep(), asked(0, "move internal 21 shows", "move internal 23 shows/night/deep"), ["--trace-store"])
        self.assertEqual(replies(run), [{"ok": True, "id": 21, "moved": False}, {"ok": True, "id": 23, "moved": False}])
        self.assertEqual(store_calls(run), [])

    def test_a_rename_that_changes_only_the_case_of_its_name_is_taken(self):
        run, left, _ = kept(deep(), asked(0, "move internal 21 Shows", "list in 22"))
        self.assertEqual(replies(run)[0], {"ok": True, "id": 21, "moved": True})
        self.assertIn("2 21 0 Shows\n3 22 0 Shows/night\n", left["folders.txt"].decode("ascii"))
        self.assertEqual(items_of(replies(run)[1])[0]["playlist"], "Shows/night/deep")

    def test_its_refusals_in_their_order(self):
        cases = [
            ("move internal", "bad-argument"),
            ("move internal 21", "bad-argument"),
            ("move internal x shows", "bad-argument"),
            ("move internal 0 shows", "bad-argument"),
            ("move internal 21 a/b/c/d", "bad-argument"),
            ("move internal 21 x.odrg", "bad-argument"),
            ("move internal 21 " + "a" * 94, "bad-argument"),
            ("move internal 21 shows a", "bad-argument"),
            ("move internal 1 programs", "in-use"),
            ("move internal 99 programs", "unknown-id"),
            ("move internal 4294967295 programs", "unknown-id"),
            ("move internal 21 shows/x", "bad-argument"),
            ("move internal 21 shows/night/x", "bad-argument"),
            ("move internal 22 old/a/b", "bad-argument"),
            ("move internal 22 missing/a", "unknown-id"),
            ("move internal 21 shows", None),
            ("move internal 22 art", "in-use"),
            ("move internal 22 ART", "in-use"),
            ("move internal 22 old/shows", None),
        ]
        run, left, _ = kept(deep(), asked(0, *(line for line, _ in cases[:-1])))
        self.assertEqual([answer.get("error") for answer in replies(run)], [error for _, error in cases[:-1]])
        self.assertEqual(left["folders.txt"].decode("ascii"), DEEP_TEXT)
        run, _, _ = kept(deep(), asked(0, cases[-1][0]))
        self.assertEqual(replies(run), [{"ok": True, "id": 22, "moved": True}])

    def test_the_limits_of_its_subtree(self):
        # A new path of 93 bytes for the deepest folder is taken, one of 94 is not.
        name = "p" * (93 - len("/night/deep"))
        run, left, _ = kept(deep(), asked(0, f"move internal 21 {name}x", f"move internal 21 {name}"))
        self.assertEqual(replies(run), [refusal("bad-argument"), {"ok": True, "id": 21, "moved": True}])
        self.assertIn(f"4 23 0 {name}/night/deep\n", left["folders.txt"].decode("ascii"))
        # A file of the subtree whose path would pass 100 bytes keeps its folder from moving.
        long_file = "4/" + "c" * 27 + ".odrg"
        items = [*DEEP_ITEMS[:3], {"id": 13, "file": long_file}, DEEP_ITEMS[4]]
        files = {**{key: value for key, value in DEEP_FILES.items() if key != "4/c.odrg"}, long_file: loop_of(2, 7)}
        short = "q" * 50
        longer = "q" * 70
        run, left, _ = kept(deep(items=items, files=files), asked(0, f"move internal 21 {longer}", f"move internal 21 {short}"))
        self.assertEqual(replies(run), [refusal("bad-argument"), {"ok": True, "id": 21, "moved": True}])

    def test_a_file_listed_at_the_root_for_its_long_path_blocks_no_move(self):
        files = {**show_of(LONG_ITEMS, {"four.odrg": loop_of(4, 1), "3/x.odrg": loop_of(2, 5), LONG_ITEMS[2]["file"]: loop_of(2, 7)}, min_seconds=4),
                 "folders.txt": LONG_TEXT}
        shorter = f"{'a' * 30}/{'b' * 30}/{'c' * 30}"
        run, left, _ = kept(files, asked(0, f"move internal 7 {shorter}", "list in 7"))
        self.assertEqual(replies(run)[0], {"ok": True, "id": 7, "moved": True})
        self.assertEqual([item["file"] for item in items_of(replies(run)[1])], [f"{shorter}/x.odrg"])

    def test_the_other_refusals(self):
        run = support.start({**deep(), "show.json": "{"}, asked(0, "move internal 21 programs"))
        self.assertEqual(replies(run), [refusal("show-invalid")])
        run = support.start(deep(), asked(0, "move internal 21 programs"), ["--only-space"])
        self.assertEqual(replies(run), [refusal("unsupported")])
        upload_open = support.line(T0, "upload begin 9 new.odrg 100")
        run = support.start(deep(), [upload_open] + asked(0, "move internal 21 programs"))
        self.assertEqual(replies(run)[-1], refusal("busy"))
        run = support.start({**deep(), "folders.txt": "odrig-folders 1 2\nbroken\n"}, asked(0, "move internal 21 programs"))
        self.assertEqual(replies(run), [refusal("storage-error")])
        with a_drive({"x.odrg": loop_of(2, 9)}) as top:
            run = support.start(deep(), every(100, 2000, "status") + asked(2000, "list", "move internal 60001 programs"), ["--drive", top])
        self.assertIn(60001, [item["id"] for item in items_of(replies(run)[-2])])
        self.assertEqual(replies(run)[-1], refusal("in-use"))

    def test_a_failed_write_leaves_the_folders_as_they_were(self):
        traced = support.start(deep(), asked(0, "move internal 21 programs"), ["--trace-store"])
        before = len(list(traced.stored))
        calls = store_calls(traced)
        self.assertEqual(calls[-1], "rename folders.part folders.txt 1")
        for number in range(before + 1, before + len(calls) + 1):
            with self.subTest(call=calls[number - before - 1]):
                run, left, _ = kept(deep(), asked(0, "move internal 21 programs"), ["--store-fails-at", str(number)])
                self.assertEqual(replies(run), [refusal("storage-error")])
                self.assertEqual(left["folders.txt"].decode("ascii"), DEEP_TEXT)
                self.assertNotIn("folders.part", left)


class WhatIsKept(unittest.TestCase):
    def test_ids_numbers_stored_names_settings_the_order_and_the_catalog_stay_byte_for_byte(self):
        script = asked(0, "brightness 12 7 save", "repeat 13 3 save", "order get in 22") + asked(100, "move internal 22 art/night", "saved 12", "saved 13",
                                                                                                "order get in 22")
        with support.installed(deep()) as folder:
            support.session(folder, asked(0, "catalog rebuild internal") + every(100, 3000, "catalog"))
            before = support.folder_files(folder)
            run = support.session(folder, script)
            after = support.folder_files(folder)
        answers = replies(run)
        self.assertEqual(answers[3], {"ok": True, "id": 22, "moved": True})
        self.assertEqual((answers[4]["brightness"], answers[5]["repeat"]), (7, 3))
        self.assertEqual((answers[6]["ids"], answers[6]["revision"]), (answers[2]["ids"], answers[2]["revision"]))
        for name, data in after.items():
            if name not in ("folders.txt", "brightness.txt", "repeats.txt", "playlist.txt"):
                self.assertEqual(data, before.get(name), name)
        self.assertEqual(json.loads(after["show.json"]), json.loads(before["show.json"]))


class WhatFollows(unittest.TestCase):
    def test_the_root_walks_the_new_tree(self):
        run = support.start(foldered(), asked(0, "move internal 7 shows/night/art") + every(100, 40000, "status"))
        self.assertEqual(replies(run)[0], {"ok": True, "id": 7, "moved": True})
        self.assertEqual(played(run)[:5], [1, 11, 12, 13, 1])
        run = support.start(foldered(), asked(0, "move internal 6 night") + every(100, 40000, "status"))
        self.assertEqual(played(run)[:5], [1, 13, 12, 11, 1])

    def test_ignore_is_inherited_under_an_ignored_folder_and_lost_out_of_it(self):
        run, _, _ = kept(deep(), asked(0, "move internal 22 old/night", "list in 24", "list in 22", "move internal 22 night", "list in 22"))
        under_old, night_rows, _, night_out = replies(run)[1:]
        self.assertEqual(items_of(under_old)[0]["playlist"], "old/night")
        self.assertTrue(items_of(under_old)[0]["inherited_ignored"])
        self.assertTrue(all(item["inherited_ignored"] for item in items_of(night_rows)))
        self.assertFalse(any(item["inherited_ignored"] for item in items_of(night_out)))

    def test_a_moved_current_playlist_and_one_below_it_follow_in_status_and_in_the_saved_file(self):
        with a_drive({}) as top, support.installed(deep()) as folder:
            run = support.session(folder, asked(0, "play 22", "status", "move internal 22 art/night", "status") + asked(100, "status"), ["--drive", top])
            saved = pathlib.Path(folder, "playlist.txt").read_text(encoding="ascii").splitlines()[:2]
            below = support.session(folder, asked(0, "play 23", "move internal 22 art/evening", "status") + asked(100, "status"), ["--drive", top])
            saved_below = pathlib.Path(folder, "playlist.txt").read_text(encoding="ascii").splitlines()[:2]
        answers = replies(run)
        self.assertEqual((answers[1]["playing"], answers[1]["playlist"]), (22, "shows/night"))
        self.assertEqual(answers[2], {"ok": True, "id": 22, "moved": True})
        self.assertEqual((answers[3]["playing"], answers[3]["playlist"]), (22, "art/night"))
        self.assertEqual((answers[4]["playing"], answers[4]["playlist"]), (22, "art/night"))
        self.assertEqual(saved, ["odrig-playlist 1", ":art/night"])
        later = replies(below)
        self.assertEqual(later[1], {"ok": True, "id": 22, "moved": True})
        self.assertEqual((later[2]["playing"], later[2]["playlist"]), (23, "art/evening/deep"))
        self.assertEqual(later[3]["playlist"], "art/evening/deep")
        self.assertEqual(saved_below, ["odrig-playlist 1", ":art/evening/deep"])

    def test_the_animation_that_plays_goes_on_through_the_move(self):
        script = every(100, 1500, "status") + asked(1500, "move internal 22 art/night") + every(100, 3000, "status")
        run = support.start(deep(), script)
        shown = [animation for _, animation in statuses(run)]
        self.assertEqual(len(set(shown)), 1)

    def test_a_power_cut_at_each_store_call_leaves_the_old_file_or_the_new_one(self):
        script = asked(0, "move internal 22 art/night")
        traced = support.start(deep(), script, ["--trace-store"])
        before = len(list(traced.stored))
        calls = store_calls(traced)
        new = "odrig-folders 1 6\n1 20 0 art\n3 22 0 art/night\n4 23 0 art/night/deep\n5 24 1 old\n2 21 0 shows\n"
        for number in range(before + 1, before + len(calls) + 1):
            with self.subTest(cut=number, call=calls[number - before - 1]), support.installed(deep()) as folder:
                result = support.host("session", folder, support.CHECK_FIRST, "--cut-at", str(number), stdin="".join(f"{line}\n" for line in script).encode("ascii"))
                self.assertEqual(result.status, POWER_CUT, result.out[-300:])
                again = support.session(folder, asked(0, "list"))
                self.assertNotIn("folders unreadable", logged(again))
                text = pathlib.Path(folder, "folders.txt").read_text(encoding="ascii")
                self.assertIn(text, (DEEP_TEXT, new))
                self.assertFalse(pathlib.Path(folder, "folders.part").exists())


if __name__ == "__main__":
    unittest.main()

"""Folders of the board's own storage: `folders.txt`, the numbered folders that hold the
files, `folder make internal`, uploads by a path, the rows of `list`, Ignore, the walk, the
rotation, the pruning of an emptied folder and the start's repair."""

import json
import pathlib
import unittest

from . import support
from .test_drive import DONE, a_drive, asked, logged, refusal, replies, statuses
from .test_playback import T0
from .test_playlist import loop_of, show_of

POWER_CUT = 75
WINDOW = 86_400_000

# A show of one animation at the root, whose turns last four seconds.
FLAT = show_of([{"id": 1, "file": "four.odrg"}], {"four.odrg": loop_of(4, 1)}, min_seconds=4)

# A show whose files are in three folders: `art` (number 2, id 7), `shows` (number 1, id 5)
# and `shows/night` (number 3, id 6), in the tree's order art, shows, shows/night.
FOLDERS_TEXT = "odrig-folders 1 4\n2 7 0 art\n1 5 0 shows\n3 6 0 shows/night\n"
ITEMS = [{"id": 1, "file": "four.odrg"}, {"id": 11, "file": "1/a.odrg"}, {"id": 12, "file": "3/b.odrg"}, {"id": 13, "file": "2/c.odrg"}]
FILES = {"four.odrg": loop_of(4, 1), "1/a.odrg": loop_of(2, 5), "3/b.odrg": loop_of(2, 6), "2/c.odrg": loop_of(2, 7)}


# A folder whose path is 93 bytes, three deep (number 3, id 7): its file `x.odrg` has a path
# of 100 bytes, and a file of a longer name, whose path would pass 100, is no file of it.
LONG_PATH = f"{'a' * 30}/{'b' * 30}/{'c' * 31}"
LONG_TEXT = f"odrig-folders 1 4\n1 5 0 {'a' * 30}\n2 6 0 {'a' * 30}/{'b' * 30}\n3 7 0 {LONG_PATH}\n"
LONG_ORPHAN = f"3/{'y' * 27}.odrg"
LONG_ITEMS = [{"id": 1, "file": "four.odrg"}, {"id": 11, "file": "3/x.odrg"}, {"id": 12, "file": LONG_ORPHAN}]
LONG_FILES = {"four.odrg": loop_of(4, 1), "3/x.odrg": loop_of(2, 5), LONG_ORPHAN: loop_of(2, 7)}


def foldered(text=FOLDERS_TEXT, items=ITEMS, files=FILES):
    return {**show_of(items, files, min_seconds=4), "folders.txt": text}


def kept(files, script, options=(), status=0, check_first=True):
    """A session on these files: the run, the files afterwards, and the folders."""
    with support.installed(files) as folder:
        run = support.session(folder, script, options, status, check_first)
        root = pathlib.Path(folder)
        return run, support.folder_files(folder), sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir())


def upload(at, number, path, data):
    """The lines of an upload of a file to the board's storage, with refreshes for its check."""
    lines = [support.line(at, line) for line in support.upload_lines(number, path, data)]
    lines += [f"poll {at + 20 * step}" for step in range(1, 30)]
    return lines + [support.line(at + 600, support.upload_end(data))]


def items_of(reply):
    return reply["items"]


def show_items(files):
    return json.loads(files["show.json"])["items"]


def store_calls(run):
    return [line[len("store "):] for line in run.lines if line.startswith("store ")]


def every(ms, until, *commands):
    return [line for time in range(0, until, ms) for line in asked(time, *commands)]


def played(run):
    seen = []
    for _, animation in statuses(run):
        if not seen or seen[-1] != animation:
            seen.append(animation)
    return seen


def folder_row(id, path, files=0, ignored=False, inherited=False):
    return {"id": id, "playlist": path, "external": False, "files": files, "ignored": ignored, "inherited_ignored": inherited}


class Making(unittest.TestCase):
    def test_a_folder_is_made_at_the_root_with_the_lowest_free_id_its_line_and_its_numbered_folder(self):
        run, left, folders = kept(FLAT, asked(0, "folder make internal shows", "list"))
        made, listed = replies(run)
        self.assertEqual(made, {"ok": True, "id": 2, "made": True})
        self.assertEqual(left["folders.txt"], b"odrig-folders 1 2\n1 2 0 shows\n")
        self.assertEqual(folders, ["1"])
        self.assertEqual([item["id"] for item in items_of(listed)], [1, 2])
        self.assertEqual(items_of(listed)[1], folder_row(2, "shows"))
        self.assertIsNone(listed["next"])
        self.assertEqual(json.loads(left["show.json"]), json.loads(FLAT["show.json"]))

    def test_folders_stand_in_the_trees_order_and_take_their_numbers_in_turn(self):
        paths = ("shows", "art", "shows/night", "shows/day", "art/old", "art/old/x")
        run, left, folders = kept(FLAT, asked(0, *(f"folder make internal {path}" for path in paths), "list", "list in 3", "list in 2", "list in 6"))
        answers = replies(run)
        self.assertEqual(answers[:6], [{"ok": True, "id": id, "made": True} for id in (2, 3, 4, 5, 6, 7)])
        self.assertEqual(left["folders.txt"].decode("ascii"), "odrig-folders 1 7\n2 3 0 art\n5 6 0 art/old\n6 7 0 art/old/x\n1 2 0 shows\n4 5 0 shows/day\n3 4 0 shows/night\n")
        self.assertEqual(folders, ["1", "2", "3", "4", "5", "6"])
        root, art, shows, old = answers[6:]
        self.assertEqual(items_of(root)[1:], [folder_row(3, "art"), folder_row(2, "shows")])
        self.assertEqual(items_of(art), [folder_row(6, "art/old")])
        self.assertEqual(items_of(shows), [folder_row(5, "shows/day"), folder_row(4, "shows/night")])
        self.assertEqual(items_of(old), [folder_row(7, "art/old/x")])

    def test_the_same_path_again_is_not_made_and_nothing_is_written(self):
        run = support.start(FLAT, asked(0, "folder make internal shows") + asked(20, "status") + asked(40, "folder make internal shows"), ["--trace-store"])
        answers = replies(run)
        self.assertEqual((answers[0], answers[2]), ({"ok": True, "id": 2, "made": True}, {"ok": True, "id": 2, "made": False}))
        calls = store_calls(run)
        self.assertEqual(calls[-1], "rename folders.part folders.txt 1")
        self.assertIn("make_folder 1 1", calls)

    def test_its_refusals_in_their_order(self):
        long_name = "a" * 93
        commands = ("folder make internal", "folder make internal a/b/c/d", f"folder make internal {long_name}x", "folder make internal x.odrg",
                    "folder make internal shows", "folder make internal Shows", "folder make internal missing/child", f"folder make internal {long_name}")
        run = support.start(FLAT, asked(0, *commands))
        self.assertEqual(replies(run), [refusal("bad-argument")] * 4 + [{"ok": True, "id": 2, "made": True}, refusal("in-use"), refusal("unknown-id"),
                                                                         {"ok": True, "id": 3, "made": True}])

    def test_an_open_upload_makes_it_busy(self):
        data = loop_of(2, 5)
        run = support.start(FLAT, asked(0, f"upload begin 9 x.odrg {len(data)}", "folder make internal shows"))
        self.assertEqual(replies(run)[1], refusal("busy"))

    def test_a_33rd_folder_has_no_space(self):
        run, left, folders = kept(FLAT, asked(0, *(f"folder make internal f{number}" for number in range(33))))
        answers = replies(run)
        self.assertTrue(all(answer["ok"] for answer in answers[:32]), answers)
        self.assertEqual(answers[32], refusal("no-space"))
        self.assertEqual(len(left["folders.txt"].decode("ascii").splitlines()), 33)
        self.assertEqual(len(folders), 32)

    def test_a_host_that_cannot_make_folders_answers_unsupported(self):
        for option in ("--no-folders", "--only-space"):
            with self.subTest(option=option):
                run = support.start(FLAT, asked(0, "folder make internal shows"), [option])
                self.assertEqual(replies(run), [refusal("unsupported")])

    def test_an_invalid_show_answers_show_invalid(self):
        broken = {**FLAT, "show.json": "{"}
        run = support.start(broken, asked(0, "folder make internal shows"))
        self.assertEqual(replies(run), [refusal("show-invalid")])


class Uploads(unittest.TestCase):
    def test_a_file_is_uploaded_into_a_folder_by_its_path_under_its_stored_name(self):
        data = loop_of(2, 5)
        script = asked(0, "folder make internal shows") + upload(T0 + 20, 5, "shows/x.odrg", data) + asked(1000, "list", "list in 2", "order get in 2")
        run, left, folders = kept(FLAT, script)
        answers = replies(run)
        self.assertEqual(answers[-4], DONE)
        root, inside, order = answers[-3:]
        self.assertEqual(items_of(root)[1], folder_row(2, "shows", files=1))
        self.assertEqual(items_of(inside), [{"id": 5, "file": "shows/x.odrg", "bytes": len(data), "ignored": False, "external": False, "type": "frames",
                                             "stored": "1/x.odrg", "inherited_ignored": False}])
        self.assertEqual(order["ids"], [5])
        self.assertEqual(left["1/x.odrg"], data)
        self.assertEqual(show_items(left)[-1], {"id": 5, "file": "1/x.odrg"})
        self.assertNotIn("x.odrg", left)

    def test_a_path_is_decoded_once_and_old_clients_send_a_name_as_before(self):
        data = loop_of(2, 5)
        script = asked(0, "folder make internal my%20shows") + upload(T0 + 20, 5, "my%20shows/x.odrg", data) + upload(T0 + 1000, 6, "y.odrg", data)
        run, left, _ = kept(FLAT, script + asked(2000, "list in 2"))
        self.assertEqual(items_of(replies(run)[-1])[0]["file"], "my shows/x.odrg")
        self.assertEqual([item["file"] for item in show_items(left)], ["four.odrg", "1/x.odrg", "y.odrg"])

    def test_a_missing_folder_a_folders_id_and_a_long_path_are_refused(self):
        long_path = "/".join(["a" * 31] * 3) + "/x.odrg"
        commands = ("folder make internal shows", "upload begin 5 nope/x.odrg 10", "upload begin 2 shows/x.odrg 10", f"upload begin 5 {long_path} 10",
                    "upload begin 5 shows/X.odrg 10")
        run = support.start(FLAT, asked(0, *commands))
        self.assertEqual(replies(run)[1:], [refusal("unknown-id"), refusal("in-use"), refusal("bad-argument"), refusal("bad-argument")])

    def test_the_fault_of_an_upload_into_a_folder_names_its_stored_name(self):
        bad = loop_of(2, 5)[:-3]
        run = support.start(FLAT, asked(0, "folder make internal shows") + upload(T0 + 20, 5, "shows/x.odrg", bad) + asked(1000, "fault"))
        fault = replies(run)[-1]["fault"]
        self.assertEqual((fault["work"], fault["file"]), ("upload", "1/x.odrg"))

    def test_the_same_name_in_two_folders_is_two_files(self):
        data = loop_of(2, 5)
        other = loop_of(2, 6)
        script = asked(0, "folder make internal a", "folder make internal b") + upload(T0 + 20, 5, "a/x.odrg", data) + upload(T0 + 1000, 6, "b/x.odrg", other)
        run, left, _ = kept(FLAT, script)
        self.assertEqual((left["1/x.odrg"], left["2/x.odrg"]), (data, other))

    def test_an_upload_of_the_same_id_into_another_folder_moves_the_file_and_prunes_the_old_folder(self):
        data = loop_of(2, 5)
        script = upload(T0, 12, "shows/x.odrg", data) + asked(1000, "list")
        run, left, folders = kept(foldered(), script)
        self.assertNotIn("3/b.odrg", left)
        self.assertEqual(left["1/x.odrg"], data)
        self.assertEqual(left["folders.txt"].decode("ascii"), "odrig-folders 1 4\n2 7 0 art\n1 5 0 shows\n")
        self.assertNotIn("3", folders)


class Listing(unittest.TestCase):
    def test_the_root_lists_its_items_then_the_internal_folders_of_the_first_level(self):
        run = support.start(foldered(), asked(0, "list", "list in 5", "list in 6", "list in 7", "order get", "order get in 5"))
        root, shows, night, art, order, order_shows = replies(run)
        self.assertEqual([item["id"] for item in items_of(root)], [1, 7, 5])
        self.assertEqual(items_of(root)[0]["file"], "four.odrg")
        self.assertNotIn("stored", items_of(root)[0])
        self.assertEqual(items_of(root)[1:], [folder_row(7, "art", files=1), folder_row(5, "shows", files=1)])
        self.assertEqual(items_of(shows)[0], folder_row(6, "shows/night", files=1))
        self.assertEqual([(item["id"], item["file"], item["stored"]) for item in items_of(shows)[1:]], [(11, "shows/a.odrg", "1/a.odrg")])
        self.assertEqual([(item["id"], item["file"], item["stored"]) for item in items_of(night)], [(12, "shows/night/b.odrg", "3/b.odrg")])
        self.assertEqual([(item["id"], item["file"]) for item in items_of(art)], [(13, "art/c.odrg")])
        self.assertEqual((order["ids"], order_shows["ids"]), ([1], [11]))

    def test_a_level_is_paged_at_1024_bytes(self):
        names = [f"{'n' * 25}{number:02d}.odrg" for number in range(12)]
        items = [{"id": 1, "file": "four.odrg"}] + [{"id": 20 + number, "file": f"1/{name}"} for number, name in enumerate(names)]
        files = {"four.odrg": loop_of(4, 1), **{f"1/{name}": loop_of(2, 5) for name in names}}
        long_folder = "s" * 67
        run = support.start(foldered(f"odrig-folders 1 2\n1 5 0 {long_folder}\n", items, files), asked(0, *(f"list in 5 {start}" for start in range(12))))
        answers = replies(run)
        items, position = [], 0
        while position is not None:
            items += items_of(answers[position])
            position = answers[position]["next"]
        self.assertEqual([item["id"] for item in items], [20 + number for number in range(12)])
        self.assertTrue(all(len(line) - len("reply ") + 1 <= 1024 for line in run.lines if line.startswith("reply ")))
        self.assertGreater(len([answer for answer in answers if answer["next"] is not None]), 1)

    def test_status_names_the_logical_path_of_the_file_on_the_leds(self):
        run = support.start(foldered(), asked(0, "play 12") + asked(20, "status"))
        status = replies(run)[1]
        self.assertEqual((status["animation"], status["file"]), (12, "shows/night/b.odrg"))

    def test_status_names_the_logical_path_of_the_file_under_check(self):
        run = support.start(foldered(items=[ITEMS[1], ITEMS[0]]), [support.line(T0, "status")], check_first=False)
        self.assertEqual(replies(run)[0]["checking"], "shows/a.odrg")

    def test_a_file_whose_path_would_pass_100_bytes_is_listed_at_the_root_under_its_stored_name(self):
        run = support.start(foldered(LONG_TEXT, LONG_ITEMS, LONG_FILES), asked(0, "list", "list in 7", "play 12") + asked(20, "status"))
        root, deepest, played_now, status = replies(run)
        self.assertEqual([(item["id"], item.get("file")) for item in items_of(root)], [(1, "four.odrg"), (12, LONG_ORPHAN), (5, None)])
        self.assertNotIn("stored", items_of(root)[1])
        self.assertEqual([(item["id"], item["file"]) for item in items_of(deepest)], [(11, f"{LONG_PATH}/x.odrg")])
        self.assertEqual(len(items_of(deepest)[0]["file"]), 100)
        self.assertEqual(played_now, DONE)
        self.assertEqual((status["animation"], status["file"]), (12, LONG_ORPHAN))

    def test_the_path_under_check_is_cut_to_32_characters_as_the_cards_names_are(self):
        files = {name: LONG_FILES[name] for name in ("four.odrg", "3/x.odrg")}
        run = support.start(foldered(LONG_TEXT, LONG_ITEMS[1:2] + LONG_ITEMS[:1], files), [support.line(T0, "status")], check_first=False)
        self.assertEqual(replies(run)[0]["checking"], f"{LONG_PATH}/x.odrg"[:32])

    def test_the_longest_reply_to_status_fits_1024_bytes(self):
        # A long internal playlist current, its file of a path of 100 bytes on the LEDs and a
        # file under check; then every member at its longest: the host's name at the 160
        # bytes the core cuts it to, both errors, and numbers of the most digits.
        with a_drive({}) as top:
            files = {"four.odrg": LONG_FILES["four.odrg"], "3/x.odrg": LONG_FILES["3/x.odrg"], "3/z.odrg": loop_of(2, 6)}
            run = support.start(foldered(LONG_TEXT, LONG_ITEMS[1:2] + LONG_ITEMS[:1] + [{"id": 13, "file": "3/z.odrg"}], files),
                                asked(0, "play 7") + asked(20, "status"), ["--drive", top], check_first=False)
        printed = [line[len("reply "):] for line in run.lines if line.startswith("reply ")][-1]
        status = json.loads(printed)
        self.assertEqual(json.dumps(status, separators=(",", ":")), printed)
        self.assertEqual((status["playlist"], status["file"]), (LONG_PATH, f"{LONG_PATH}/x.odrg"))
        self.assertLessEqual(len(status["checking"] or ""), 32)
        big = 4294967295
        longest = {"ok": True, "on": False, "brightness": 255, "dimming": {"value": 255, "saved": 255, "error": "settings-unreadable"},
                   "mini": {"supported": False, "on": False, "pending": False, "requested": False, "error": "output-setup-failed", "brightness": 255},
                   "playing": 65535, "animation": 65535, "fps": 9999, "error": None, "width": 255, "height": 255, "timing": True, "readiness": "checking",
                   "checked": 65535, "to_check": 65535, "unavailable": 65535, "checking": "c" * 32, "host": "h" * 160, "seed": big, "repeat": big,
                   "loop": big, "saved": 65535, "file": "f" * 100, "playlist": "p" * 93, "clocks": False, "clock_message": False,
                   "clock_mode": "between", "clock_only": None, "left": 86400}
        self.assertEqual(list(status), list(longest))
        # In Only mode the playlist is `clocks`, and `clock_only` is given.
        only = {**longest, "playlist": "clocks", "clock_only": {"folder": 65535, "state": "missing-folder"}}
        for shape in (longest, only):
            self.assertLessEqual(len(json.dumps(shape, separators=(",", ":"))) + 1, 1024)

    def test_a_folders_id_is_in_use_for_the_commands_of_an_animation(self):
        commands = ("read 5 0", "read 5 0 10", "remove 5", "saved 5", "repeat 5 2 save", "brightness 5 9 save", "upload begin 5 x.odrg 10", "remove many 5")
        run = support.start(foldered(), asked(0, *commands))
        self.assertEqual(replies(run), [refusal("in-use")] * len(commands))


class Ignoring(unittest.TestCase):
    def test_a_folders_ignore_is_kept_in_its_line_and_holds_its_subtree(self):
        script = asked(0, "ignore 5 1", "list", "list in 5", "list in 6") + every(100, 25000, "status")
        run, left, _ = kept(foldered(), script)
        done, root, shows, night = replies(run)[:4]
        self.assertEqual(done, DONE)
        self.assertEqual(left["folders.txt"].decode("ascii"), "odrig-folders 1 4\n2 7 0 art\n1 5 1 shows\n3 6 0 shows/night\n")
        self.assertEqual(items_of(root)[2], folder_row(5, "shows", files=1, ignored=True))
        self.assertEqual(items_of(shows)[0], folder_row(6, "shows/night", files=1, inherited=True))
        self.assertEqual((items_of(shows)[1]["ignored"], items_of(shows)[1]["inherited_ignored"]), (False, True))
        self.assertEqual(items_of(night)[0]["inherited_ignored"], True)
        self.assertEqual(set(played(run)), {1, 13})

    def test_a_folder_taken_in_again_plays_and_ignore_of_its_state_writes_nothing(self):
        held = foldered(FOLDERS_TEXT.replace("1 5 0 shows", "1 5 1 shows"))
        run, left, _ = kept(held, asked(0, "ignore 6 0", "ignore 5 0") + every(100, 25000, "status"))
        self.assertEqual(replies(run)[:2], [DONE, DONE])
        self.assertEqual(left["folders.txt"].decode("ascii"), FOLDERS_TEXT)
        self.assertEqual(sorted(set(played(run))), [1, 11, 12, 13])


class Playing(unittest.TestCase):
    def test_the_root_walks_its_items_then_each_folder_depth_first(self):
        run = support.start(foldered(), every(100, 40000, "status"))
        self.assertEqual(played(run)[:6], [1, 13, 11, 12, 1, 13])

    def test_play_of_a_folder_plays_its_own_files_then_its_sub_folders_and_again(self):
        with a_drive({}) as top:
            run = support.start(foldered(), asked(0, "play 5") + every(100, 20000, "status"), ["--drive", top])
        self.assertEqual(replies(run)[0], DONE)
        self.assertEqual(played(run)[:4], [11, 12, 11, 12])
        status = [reply for reply in replies(run) if "on" in reply][0]
        self.assertEqual((status["playing"], status["playlist"], status["file"]), (5, "shows", "shows/a.odrg"))

    def test_a_folder_is_no_playlist_on_a_host_without_the_saved_playlist(self):
        run = support.start(foldered(), asked(0, "play 5"))
        self.assertEqual(replies(run), [refusal("unsupported")])

    def test_the_chosen_folder_is_saved_and_found_again_after_a_restart(self):
        with a_drive({}) as top, support.installed(foldered()) as folder:
            support.session(folder, asked(0, "play 6") + asked(20), ["--drive", top])
            self.assertEqual(pathlib.Path(folder, "playlist.txt").read_text(encoding="ascii").splitlines()[:2], ["odrig-playlist 1", ":shows/night"])
            again = support.session(folder, asked(20, "status"), ["--drive", top])
        status = replies(again)[0]
        self.assertEqual((status["playing"], status["animation"], status["playlist"]), (6, 12, "shows/night"))

    def test_a_boot_that_cannot_read_the_folders_plays_the_root_and_keeps_the_chosen_folder_for_the_next(self):
        with a_drive({}) as top, support.installed(foldered()) as folder:
            support.session(folder, asked(0, "play 6") + asked(20), ["--drive", top])
            playlist = pathlib.Path(folder, "playlist.txt")
            folders = pathlib.Path(folder, "folders.txt")
            sound = folders.read_bytes()
            folders.write_bytes(sound.replace(b"3 6 0 shows/night", b"3 6 0 night/shows"))
            damaged = support.session(folder, asked(20, "status") + asked(40) + asked(60) + asked(1_000_000), ["--drive", top])
            kept = playlist.read_text(encoding="ascii").splitlines()[:2]
            folders.write_bytes(sound)
            again = support.session(folder, asked(20, "status"), ["--drive", top])
        self.assertIn("folders unreadable", logged(damaged))
        self.assertEqual(replies(damaged)[0]["playing"], "all")
        self.assertEqual(kept, ["odrig-playlist 1", ":shows/night"])
        status = replies(again)[0]
        self.assertEqual((status["playing"], status["animation"], status["playlist"]), (6, 12, "shows/night"))

    def test_the_rotation_goes_root_then_the_internal_folders_by_rank_then_the_root(self):
        times = (WINDOW + 20_000, 2 * WINDOW + 20_000, 3 * WINDOW + 20_000, 4 * WINDOW + 20_000)
        with a_drive({}) as top:
            run = support.start(foldered(), asked(20) + [line for time in times for line in asked(time, "status")], ["--drive", top])
        self.assertEqual([reply["playing"] for reply in replies(run)], [7, 5, 6, "all"])


class Pruning(unittest.TestCase):
    def test_the_removal_of_a_folders_last_file_takes_its_line_and_its_folder(self):
        run, left, folders = kept(foldered(), asked(0, "remove 12", "list in 5"))
        self.assertEqual(replies(run)[0], DONE)
        self.assertEqual(left["folders.txt"].decode("ascii"), "odrig-folders 1 4\n2 7 0 art\n1 5 0 shows\n")
        self.assertEqual(folders, ["1", "2"])
        self.assertEqual([item["id"] for item in items_of(replies(run)[1])], [11])

    def test_an_emptied_parent_goes_with_its_last_sub_folder(self):
        items = [ITEMS[0], ITEMS[2], ITEMS[3]]
        files = {name: data for name, data in FILES.items() if name != "1/a.odrg"}
        run, left, folders = kept(foldered(items=items, files=files), asked(0, "remove many 12,13", "list"))
        self.assertEqual(replies(run)[0], DONE)
        self.assertEqual(left["folders.txt"].decode("ascii"), "odrig-folders 1 4\n")
        self.assertEqual(folders, [])
        self.assertEqual([item["id"] for item in items_of(replies(run)[1])], [1])

    def test_a_folder_made_and_never_filled_stays(self):
        run, left, folders = kept(FLAT, asked(0, "folder make internal a", "folder make internal a/b", "remove 1"))
        self.assertEqual(left["folders.txt"].decode("ascii"), "odrig-folders 1 3\n1 2 0 a\n2 3 0 a/b\n")
        self.assertEqual(folders, ["1", "2"])


class Numbers(unittest.TestCase):
    def test_numbers_go_round_and_pass_over_a_number_a_line_or_a_stored_name_has(self):
        text = "odrig-folders 1 254\n254 5 0 old\n"
        items = [ITEMS[0], {"id": 11, "file": "254/a.odrg"}, {"id": 12, "file": "1/b.odrg"}]
        files = {"four.odrg": loop_of(4, 1), "254/a.odrg": loop_of(2, 5), "1/b.odrg": loop_of(2, 6)}
        run, left, _ = kept(foldered(text, items, files), asked(0, "folder make internal x", "folder make internal y"))
        self.assertEqual(replies(run), [{"ok": True, "id": 2, "made": True}, {"ok": True, "id": 3, "made": True}])
        self.assertEqual(left["folders.txt"].decode("ascii"), "odrig-folders 1 3\n254 5 0 old\n255 2 0 x\n2 3 0 y\n")


class TheStart(unittest.TestCase):
    def test_a_folders_id_that_an_item_has_is_given_a_new_one(self):
        clashing = foldered(FOLDERS_TEXT.replace("2 7 0 art", "2 13 0 art"))
        run, left, _ = kept(clashing, asked(0, "list"))
        self.assertEqual(left["folders.txt"].decode("ascii"), FOLDERS_TEXT.replace("2 7 0 art", "2 2 0 art"))
        self.assertEqual(items_of(replies(run)[0])[1], folder_row(2, "art", files=1))

    def test_a_damaged_file_is_left_as_it_is_its_files_play_at_the_root_and_changes_are_refused(self):
        damaged = foldered(FOLDERS_TEXT.replace("3 6 0 shows/night", "3 6 0 night/shows"))
        run, left, _ = kept(damaged, asked(0, "list", "folder make internal new", "ignore 5 1", "upload begin 20 shows/x.odrg 10"))
        self.assertIn("folders unreadable", logged(run))
        self.assertEqual(left["folders.txt"], damaged["folders.txt"].encode("ascii"))
        root = replies(run)[0]
        self.assertEqual([(item["id"], item.get("file")) for item in items_of(root)], [(1, "four.odrg"), (11, "1/a.odrg"), (12, "3/b.odrg"), (13, "2/c.odrg")])
        self.assertEqual(replies(run)[1:], [refusal("storage-error"), refusal("unknown-id"), refusal("storage-error")])

    def test_a_flat_show_reads_no_folder_and_is_listed_as_before(self):
        run = support.start(FLAT, asked(0, "list", "status"), ["--trace-read-at"])
        self.assertFalse([line for line in run.lines if line.startswith("read_at folders")])
        self.assertEqual([item["id"] for item in items_of(replies(run)[0])], [1])


class StoredNames(unittest.TestCase):
    def test_an_animation_of_a_folder_moves_inside_its_level(self):
        items = ITEMS + [{"id": 14, "file": "1/d.odrg"}]
        files = {**FILES, "1/d.odrg": loop_of(2, 8)}
        first = support.start(foldered(items=items, files=files), asked(0, "order get in 5"))
        revision = replies(first)[0]["revision"]
        run, left, _ = kept(foldered(items=items, files=files), asked(0, f"order move {revision} 14 11", f"order move {revision} 12 11", "order get in 5", "order get"))
        moved, other_level, order, root = replies(run)
        self.assertEqual((moved, other_level), (DONE, refusal("in-use")))
        self.assertEqual((order["ids"], root["ids"]), ([14, 11], [1]))

    def test_a_saved_repeat_and_brightness_of_a_file_in_a_folder_are_kept_by_its_stored_name(self):
        with support.installed(foldered()) as folder:
            support.session(folder, asked(0, "repeat 12 3 save", "brightness 12 40 save"))
            left = support.folder_files(folder)
            again = support.session(folder, asked(0, "saved 12"))
        self.assertIn(b"3 f 3/b.odrg\n", left["repeats.txt"])
        self.assertIn(b"40 f 3/b.odrg\n", left["brightness.txt"])
        self.assertEqual(replies(again)[0], {"ok": True, "brightness": 40, "repeat": 3, "start": False})

    def test_the_internal_catalog_keys_files_by_their_stored_names_as_the_library_does(self):
        from .test_catalog_rebuild import catalog_files
        from .test_catalog_start import with_catalog
        script = asked(0, "catalog rebuild internal") + [f"poll {T0 + 20 + 20 * step}" for step in range(400)] + asked(8100, "catalog", "list in 6")
        run, left = support.start_and_keep(foldered(), script)
        self.assertEqual([reply for reply in replies(run) if "internal" in reply][-1]["internal"]["state"], "ok")
        self.assertEqual(catalog_files(left), catalog_files(with_catalog(foldered())))
        again = support.start(left, asked(0, "list in 6"), ["--trace-files"], check_first=False)
        self.assertEqual([name for name, _ in again.opened if name.endswith(".odrg")], [])
        self.assertEqual(items_of(replies(again)[0])[0]["bytes"], len(FILES["3/b.odrg"]))

    def test_the_root_lists_its_items_then_the_internal_folders_then_the_cards(self):
        with a_drive({"night/x.odrg": loop_of(2, 9), "y.odrg": loop_of(2, 10)}) as top:
            run = support.start(foldered(), asked(0, "list"), ["--drive", top])
        listed = items_of(replies(run)[0])
        self.assertEqual([(item.get("playlist") or item.get("file"), item["external"]) for item in listed],
                         [("four.odrg", False), ("art", False), ("shows", False), ("night", True), ("y.odrg", True)])


class PowerCuts(unittest.TestCase):
    def cut_everywhere(self, files, script):
        """Cuts the power at every storage call of the script and starts again on what is
        left: the show is valid, no part is left, and `folders.txt` is sound or absent."""
        traced = support.start(files, script, ["--trace-store"])
        calls = list(traced.stored) + store_calls(traced)
        self.assertTrue(calls)
        for number in range(1, len(calls) + 1):
            with self.subTest(cut=number, call=calls[number - 1]), support.installed(files) as folder:
                result = support.host("session", folder, support.CHECK_FIRST, "--cut-at", str(number), stdin="".join(f"{line}\n" for line in script).encode("ascii"))
                self.assertEqual(result.status, POWER_CUT, result.out[-300:])
                again = support.session(folder, asked(0, "list"))
                self.assertIsNone(again.error)
                self.assertNotIn("folders unreadable", logged(again))
                left = support.folder_files(folder)
                self.assertNotIn("folders.part", left)
                self.assertNotIn("upload.part", left)
                self.assertTrue(replies(again)[0]["ok"])
                show = json.loads(left["show.json"])
                for item in show["items"]:
                    if "file" in item:
                        self.assertIn(item["file"], left)

    def test_a_cut_while_a_folder_is_made(self):
        self.cut_everywhere(FLAT, asked(0, "folder make internal shows", "folder make internal shows/night"))

    def test_a_cut_while_a_file_is_uploaded_into_a_folder(self):
        self.cut_everywhere(foldered(), upload(T0, 20, "shows/night/x.odrg", loop_of(2, 9)))

    def test_a_cut_while_a_folder_is_pruned(self):
        self.cut_everywhere(foldered(), asked(0, "remove 12"))

    def test_a_cut_while_a_folder_is_ignored(self):
        self.cut_everywhere(foldered(), asked(0, "ignore 6 1"))


if __name__ == "__main__":
    unittest.main()

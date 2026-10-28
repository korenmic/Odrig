"""The tree of a card's folders: its order on a legacy and on a cataloged card, the folders'
ids after the files', the folder items of `list`, the paths in the saved order and in the
catalog, and the limits of the table."""

import json
import unittest

from odrig import catalog

from . import support
from .test_catalog_drive import card, polls
from .test_catalog_writes import a_card, folder_of, upload_external
from .test_drive import DONE, SHOW, a_drive, asked, logged, refusal, replies, statuses, with_drive
from .test_order import ordered
from .test_playback import T0
from .test_playlist import CANVAS, loop_of, show_of

# A card of nested folders. Listed depth first: `A.ODRG`, `b.odrg`, `a b/c.odrg`,
# `night/comet.odrg`, `night/deep/x.odrg`, `night/deep/deeper/y.odrg`; its folders in the
# tree's order: `a b`, `night`, `night/deep`, `night/deep/deeper`.
NESTED = {"b.odrg": loop_of(2, 5), "A.ODRG": loop_of(3, 6), "night/comet.odrg": loop_of(2, 7), "night/deep/x.odrg": loop_of(2, 8), "a b/c.odrg": loop_of(2, 9),
          "night/deep/deeper/y.odrg": loop_of(2, 10)}
TREE = ["a b", "night", "night/deep", "night/deep/deeper"]


def folders(reply):
    """The id and the path of each folder item of a reply of `list`."""
    return [(item["id"], item["playlist"]) for item in reply["items"] if "playlist" in item]


def files(reply):
    return [(item["id"], item["file"]) for item in reply["items"] if "file" in item]


def on_cataloged_card(card_files, script, options=()):
    """A session with a cataloged card plugged in at the start, read at refreshes before the
    script's first command."""
    with a_drive(card_files) as top:
        return support.start(SHOW, polls(0, 400) + script, ["--drive", top, *options], check_first=False)


def listing(time, level=""):
    """A refresh and `list` from every position of 0 to 79 on, or `list in <id>` of a level,
    so that the replies hold the chain of pages of the level from the first on: `paged`
    follows it."""
    return asked(time, *(f"list {level}{start}" for start in range(80)))


# The levels of NESTED: the root's, with the show's item, and each folder's.
LEVELS = ("list", "list in 60007", "list in 60008", "list in 60009", "list in 60010")


def whole(answers):
    """The items of the replies of every level, the root's first."""
    return [item for reply in answers for item in reply["items"]]


def every_level(card_files):
    """The items of every level of a cataloged card, found level by level: the root's, then
    those of the folders each level names."""
    found = []
    pending = ["list"]
    while pending:
        answers = replies(on_cataloged_card(card_files, asked(8100, *pending)))
        pending = [f"list in {item['id']}" for reply in answers for item in reply["items"] if "playlist" in item]
        found += whole(answers)
    return found


def paged(answers):
    """The items of every page of `list`, from the replies of `listing`."""
    items = []
    position = 0
    while position is not None:
        items += answers[position]["items"]
        position = answers[position]["next"]
    return items


class TheTree(unittest.TestCase):
    def test_list_gives_the_shows_items_and_the_roots_level_its_folders_with_ids_after_the_files(self):
        reply = replies(with_drive(SHOW, NESTED, asked(0, "list")))[0]
        self.assertEqual([item["id"] for item in reply["items"]], [1, 60007, 60008, 60001, 60002])
        self.assertEqual(folders(reply), [(60007, "a b"), (60008, "night")])
        self.assertEqual(files(reply), [(1, "four.odrg"), (60001, "A.ODRG"), (60002, "b.odrg")])
        self.assertEqual(reply["items"][1], {"id": 60007, "playlist": "a b", "external": True, "files": 1})

    def test_list_in_gives_a_folders_level_its_sub_folders_then_its_own_files(self):
        answers = replies(with_drive(SHOW, NESTED, asked(0, *LEVELS[1:])))
        self.assertEqual([[(item["id"], item.get("playlist", item.get("file")), item.get("files")) for item in reply["items"]] for reply in answers], [
            [(60003, "a b/c.odrg", None)],
            [(60009, "night/deep", 1), (60004, "night/comet.odrg", None)],
            [(60010, "night/deep/deeper", 1), (60005, "night/deep/x.odrg", None)],
            [(60006, "night/deep/deeper/y.odrg", None)],
        ])
        self.assertEqual({reply["next"] for reply in answers}, {None})

    def test_a_cataloged_card_lists_the_same_levels_whatever_the_order_of_its_pages(self):
        items = whole(replies(on_cataloged_card(card(NESTED), asked(8100, *LEVELS))))
        self.assertEqual([(item["id"], item["playlist"]) for item in items if "playlist" in item], list(zip(range(60007, 60011), TREE)))
        self.assertEqual(sorted(item["file"] for item in items if "file" in item), sorted(["four.odrg", *NESTED]))
        self.assertEqual(sorted(item["id"] for item in items if "file" in item), [1, *range(60001, 60007)])

    def test_the_positions_of_a_level_count_its_folders_and_its_files(self):
        run = with_drive(SHOW, NESTED, asked(0, "list 1", "list 3", "list 5", "list in 60008 1", "list in 60008 2", "list in 60008 4294967295"))
        first, third, beyond, night, after, far = replies(run)
        self.assertEqual([item["id"] for item in first["items"]], [60007, 60008, 60001, 60002])
        self.assertEqual([item["id"] for item in third["items"]], [60001, 60002])
        self.assertEqual(beyond, {"ok": True, "items": [], "next": None})
        self.assertEqual([item["id"] for item in night["items"]], [60004])
        self.assertEqual((after, far), ({"ok": True, "items": [], "next": None}, {"ok": True, "items": [], "next": None}))

    def test_list_in_of_an_id_that_is_no_folder_is_unknown_and_its_words_are_in_their_form(self):
        known = ("list in 1", "list in 60001", "list in 99999", "list in 4294967295")
        bad = ("list in", "list in x", "list in 0", "list in 4294967296", "list 1 2", "list in 60008 1 2", "list 4294967296", "list into 60008")
        run = with_drive(SHOW, NESTED, asked(0, *known, *bad))
        self.assertEqual(replies(run), [refusal("unknown-id")] * len(known) + [refusal("bad-argument")] * len(bad))

    def test_a_page_holds_folder_items_of_the_longest_paths(self):
        # Ten files whose paths are 100 bytes, in three folders each, thirty folders in all.
        drive = {}
        for number in range(10):
            drive[f"{number:02d}{'a' * 28}/{'b' * 30}/{'c' * 31}/x.odrg"] = loop_of(2, number)
        run = with_drive(SHOW, drive, listing(0) + listing(0, "in 60012 ") + listing(0, "in 60013 "))
        answers = replies(run)
        lines = [line[len("reply "):] for line in run.lines if line.startswith("reply ")]
        self.assertTrue(all(len(line.encode()) + 1 <= 1024 for line in lines))
        root = paged(answers[:80])
        self.assertEqual(len(root), 1 + 10)
        self.assertEqual([item["id"] for item in root], [1, *range(60011, 60041, 3)])
        self.assertEqual([(item["playlist"], item["files"]) for item in root[1:3]], [(f"00{'a' * 28}", 0), (f"01{'a' * 28}", 0)])
        self.assertEqual([(item["id"], item["playlist"], item["files"]) for item in paged(answers[80:160])], [(60013, f"00{'a' * 28}/{'b' * 30}/{'c' * 31}", 1)])
        self.assertEqual([(item["id"], item["file"]) for item in paged(answers[160:])], [(60001, f"00{'a' * 28}/{'b' * 30}/{'c' * 31}/x.odrg")])

    def test_a_33rd_sub_folder_of_an_index_is_a_playlist_as_the_others(self):
        names = [f"f{number:02d}/x.odrg" for number in range(33)]
        run = on_cataloged_card(card({name: loop_of(2, number) for number, name in enumerate(names)}), listing(8100) + asked(8200, "list in 60066"))
        items = paged(replies(run)[:-1])
        self.assertEqual([(item["id"], item["playlist"], item["files"]) for item in items if "playlist" in item],
                         [(60034 + number, f"f{number:02d}", 1) for number in range(33)])
        self.assertEqual([(item["id"], item["file"]) for item in replies(run)[-1]["items"]], [(60033, "f32/x.odrg")])
        self.assertFalse([line for line in logged(run) if "too-many-folders" in line])

    def test_a_folder_without_a_file_is_no_folder_of_the_tree(self):
        with a_drive(NESTED) as top:
            support.pathlib.Path(top, "odrig", "empty", "deeper").mkdir(parents=True)
            run = support.start(SHOW, asked(0, *LEVELS), ["--drive", top])
        self.assertEqual(folders({"items": whole(replies(run))}), list(zip(range(60007, 60011), TREE)))


class WhatPlaysAndTheOrderOfALevel(unittest.TestCase):
    def test_status_names_the_file_on_the_leds_and_the_current_folders_path(self):
        script = asked(0, "status", "play 60008") + asked(20, "status", "play 60002") + asked(40, "status", "play all") + asked(60, "status")
        run = with_drive(SHOW, NESTED, script)
        named = [(reply["playing"], reply["animation"], reply["file"], reply["playlist"]) for reply in replies(run) if "on" in reply]
        self.assertEqual(named, [("all", 1, "four.odrg", None), (60008, 60004, "night/comet.odrg", "night"), (60008, 60002, "b.odrg", "night"),
                                 ("all", 1, "four.odrg", None)])
        nothing = replies(support.start(show_of([], {}), asked(0, "status")))[0]
        self.assertEqual((nothing["file"], nothing["playlist"]), (None, None))
        self.assertEqual(list(nothing)[-5:], ["file", "playlist", "clocks", "clock_message", "left"])

    def test_order_get_gives_the_root_level_and_order_get_in_a_folders(self):
        lines = ("order get", "order get in 60007", "order get in 60008", "order get in 60010", "order get in 60008 1", "order get in 1", "order get in 60001",
                 "order get in", "order get in 60008 x", "order get in 60008 1 2")
        answers = replies(with_drive(SHOW, NESTED, asked(0, *lines)))
        self.assertEqual([(reply["ids"], reply["next"]) for reply in answers[:5]], [([1, 60001, 60002], None), ([60003], None), ([60004], None), ([60006], None), ([], None)])
        self.assertEqual(answers[5:], [refusal("unknown-id")] * 2 + [refusal("bad-argument")] * 3)
        self.assertEqual(len({reply["revision"] for reply in answers[:4]}), 4)

    def test_a_move_is_compared_with_the_revision_of_the_level_of_its_animation(self):
        with a_drive(NESTED) as top:
            first = support.start(SHOW, asked(0, "order get", "order get in 60009"), ["--drive", top])
            root, deep = (reply["revision"] for reply in replies(first))
            run = support.start(SHOW, asked(0, f"order move {deep} 1 end", f"order move {root} 1 end"), ["--drive", top])
        self.assertEqual(replies(run), [refusal("order-conflict"), DONE])


class ThePathsInTheSavedOrderAndTheCatalog(unittest.TestCase):
    def test_a_file_of_a_drive_without_a_catalog_is_not_moved(self):
        with a_drive(NESTED) as top:
            first = support.start(SHOW, asked(0, "order get", "order get in 60008"), ["--drive", top])
            root, night = (reply["revision"] for reply in replies(first))
            self.assertEqual([reply["ids"] for reply in replies(first)], [[1, 60001, 60002], [60004]])
            run, kept = support.start_and_keep(SHOW, asked(0, f"order move {night} 60004 end", f"order move {root} 1 end", "order get"), ["--drive", top])
        self.assertEqual(replies(run)[:2], [refusal("read-only"), DONE])
        self.assertEqual(replies(run)[2]["ids"], [1, 60001, 60002])
        self.assertNotIn("order.txt", kept)

    def test_remove_of_a_file_in_a_folder_removes_that_file_and_an_emptied_folder_leaves_the_tree(self):
        card_files = card(NESTED)
        ids = {item["file"]: item["id"] for item in every_level(card_files) if "file" in item}
        with a_card(card_files) as top:
            script = polls(0, 400) + asked(8100, f"remove {ids['night/comet.odrg']}", *LEVELS, f"remove {ids['a b/c.odrg']}", "list", "list in 60007")
            run = support.start(SHOW, script, ["--drive", top], check_first=False)
            left = folder_of(top)
        answers = replies(run)
        done, after_first, done_again, after_second, gone = answers[0], answers[1:6], answers[6], answers[7], answers[8]
        self.assertEqual((done, done_again), ({"ok": True}, {"ok": True}))
        self.assertEqual(folders({"items": whole(after_first)}), list(zip(range(60007, 60011), TREE)))
        self.assertNotIn("night/comet.odrg", [name for _, name in files({"items": whole(after_first)})])
        self.assertEqual((folders(after_second), gone), ([(60008, "night")], refusal("unknown-id")))
        self.assertNotIn("night/comet.odrg", left)
        self.assertNotIn("a b/c.odrg", left)
        self.assertEqual(sorted(name for name in left if name.lower().endswith(".odrg")), ["A.ODRG", "b.odrg", "night/deep/deeper/y.odrg", "night/deep/x.odrg"])
        found = catalog.read(catalog.MemoryStorage(left, drive=True))
        self.assertEqual(sorted(entry.name for entry in found.entries), ["A.ODRG", "b.odrg", "night/deep/deeper/y.odrg", "night/deep/x.odrg"])

    def test_upload_begin_external_takes_a_bare_file_name(self):
        run = on_cataloged_card(card(NESTED), asked(8100, "upload begin external night/new.odrg 100", "upload begin external new.odrg 100", "upload cancel"))
        self.assertEqual((replies(run)[0], replies(run)[1]["ok"]), (refusal("bad-argument"), True))


def every(ms, until, *commands):
    """A refresh and these commands every `ms` until a time after power-on."""
    return [line for time in range(0, until, ms) for line in asked(time, *commands)]


def played(run):
    """The animations `status` named, each run of the same one once."""
    seen = []
    for _, animation in statuses(run):
        if not seen or seen[-1] != animation:
            seen.append(animation)
    return seen


class PlayOfAFolder(unittest.TestCase):
    def test_play_of_a_folder_plays_its_first_animation_and_goes_on_within_the_folder(self):
        run = with_drive(SHOW, NESTED, asked(0, "play 60008") + every(100, 40000, "status"))
        self.assertEqual(replies(run)[0], DONE)
        self.assertEqual(played(run)[:5], [60004, 60005, 60006, 60004, 60005])
        self.assertEqual({playing for playing, _ in statuses(run)}, {60008})

    def test_play_all_plays_the_root_and_a_folder_plays_again_from_its_first(self):
        script = asked(0, "play 60007") + asked(20, "status") + asked(40, "play all") + asked(60, "status") + asked(80, "play 60008") + asked(100, "status")
        script += asked(120, "play 60008") + asked(140, "status")
        run = with_drive(SHOW, NESTED, script)
        self.assertEqual([reply for reply in replies(run) if "on" not in reply], [DONE] * 4)
        self.assertEqual(played(run), [60003, 1, 60004])
        self.assertEqual(len(statuses(run)), 4)

    def test_a_folder_with_nothing_to_play_plays_the_root_in_its_place(self):
        drive = {**NESTED, "solo/bad.odrg": b"not an animation"}
        run = with_drive(SHOW, drive, asked(0, "list", "play 60012") + asked(20, "status", "list in 60012"))
        reply, done = replies(run)[:2]
        self.assertEqual(folders(reply)[-1], (60012, "solo"))
        self.assertEqual([item.get("fault") for item in replies(run)[-1]["items"] if item.get("file") == "solo/bad.odrg"], ["bad-magic"])
        # The folder is current and named, and the root's first animation plays in its place.
        self.assertEqual((done, statuses(run)), (DONE, [(60012, 1)]))

    def test_a_folders_id_is_unknown_while_the_card_is_out(self):
        run = with_drive(SHOW, NESTED, asked(0, "list") + ["drive pull"] + asked(40, "play 60008", "list"))
        self.assertEqual(replies(run)[1], refusal("unknown-id"))
        self.assertEqual(folders(replies(run)[2]), [])

    def test_a_folders_id_is_in_use_for_the_commands_of_an_animation(self):
        with a_drive(NESTED) as top:
            revision = replies(support.start(SHOW, asked(0, "order get"), ["--drive", top]))[0]["revision"]
            commands = ("remove many 60008", "ignore 60008 1", "read 60008 0", "upload begin 60008 x.odrg 10", f"order move {revision} 60008 60001",
                        f"order move {revision} 60001 60008", "remove 60008")
            run = support.start(SHOW, asked(0, *commands), ["--drive", top])
        self.assertEqual(replies(run), [refusal("in-use")] * len(commands))
        on_card = on_cataloged_card(card(NESTED), asked(8100, "remove 60008", "list"))
        self.assertEqual(replies(on_card)[0], refusal("in-use"))
        self.assertEqual(folders(replies(on_card)[1]), [(60007, "a b"), (60008, "night")])


class TheExhaustingOrder(unittest.TestCase):
    def test_a_folder_with_one_animation_plays_it_again_and_again(self):
        run = with_drive(SHOW, {"b.odrg": loop_of(2, 5), "night/comet.odrg": loop_of(2, 7)}, asked(0, "play 60003") + every(100, 15000, "status"))
        self.assertEqual(replies(run)[0], DONE)
        self.assertEqual(set(animation for _, animation in statuses(run)), {60002})

    def test_the_root_plays_the_shows_animations_then_the_drives_walk_whatever_the_saved_order_says(self):
        # The saved order names `night/comet.odrg` and `b.odrg`, lines that are passed over:
        # the root plays the show's animation, then the root's files, then each folder's in
        # the tree's order, and again.
        installed = ordered(SHOW, "x night/comet.odrg", "x b.odrg")
        with a_drive(NESTED) as top:
            run = support.start(installed, every(100, 45000, "status"), ["--drive", top])
        self.assertEqual(played(run)[:9], [1, 60001, 60002, 60003, 60004, 60005, 60006, 1, 60001])

    def test_a_folder_exhausts_its_own_animations_then_its_nested_folders_then_again(self):
        run = with_drive(SHOW, NESTED, asked(0, "play 60008") + every(100, 20000, "status"))
        self.assertEqual(played(run)[:5], [60004, 60005, 60006, 60004, 60005])

    def test_a_folders_files_play_in_the_walk_whatever_the_saved_order_says(self):
        drive = {**NESTED, "night/zeta.odrg": loop_of(2, 11)}
        installed = ordered(SHOW, "x night/zeta.odrg")
        with a_drive(drive) as top:
            run = support.start(installed, asked(0, "list", "list in 60009", "play 60009") + every(100, 25000, "status"), ["--drive", top])
        reply = replies(run)[0]
        self.assertEqual(folders(reply)[1], (60009, "night"))
        self.assertEqual([id for id, name in files(replies(run)[1]) if name in ("night/comet.odrg", "night/zeta.odrg")], [60004, 60005])
        self.assertEqual(played(run)[:5], [60004, 60005, 60006, 60007, 60004])

    def test_a_jump_inside_the_current_playlist_goes_on_from_the_jumped_animation(self):
        script = asked(0, "play 60008") + asked(20, "status") + asked(100, "play 60006") + [line for time in range(200, 15000, 100) for line in asked(time, "status")]
        run = with_drive(SHOW, NESTED, script)
        self.assertEqual(played(run)[:5], [60004, 60006, 60004, 60005, 60006])

    def test_a_jump_outside_plays_its_turn_and_the_cut_turn_again_from_its_first_frame(self):
        times = range(1100, 20000, 100)
        script = asked(0, "play 60008") + asked(20, "status") + asked(1000, "play 1") + [line for time in times for line in asked(time, "status")]
        run = with_drive(SHOW, NESTED, script)
        self.assertEqual(played(run)[:5], [60004, 1, 60004, 60005, 60006])
        # The jumped turn begins at the refresh after the jump, at 1,100 ms, and lasts its
        # 4,000 ms; the cut turn begins again when it ends.
        self.assertEqual([time for time, (_, animation) in zip(times, statuses(run)[1:]) if animation == 1][-1], 5000)
        self.assertEqual(statuses(run)[1:][times.index(5100)], (60008, 60004))

    def test_the_root_plays_in_the_folders_place_while_the_card_is_out_and_the_folder_takes_over_at_the_turns_end(self):
        # The card out at 40 ms: the show's own animation plays its turn of 4,000 ms from
        # there. The card back at 60 ms is listed and read during that turn, and the folder
        # takes over when the turn ends.
        script = asked(0, "play 60008") + ["drive pull"] + asked(40, "status") + ["drive plug"] + polls(60, 100)
        script += [line for time in range(2100, 9000, 100) for line in asked(time, "status")]
        run = with_drive(SHOW, NESTED, script)
        self.assertEqual(replies(run)[0], DONE)
        self.assertEqual(statuses(run)[0], ("all", 1))
        animations = [animation for _, animation in statuses(run)[1:]]
        self.assertEqual((animations[:20], animations[20]), ([1] * 20, 60004))
        self.assertEqual(statuses(run)[-1], (60008, 60005))

    def test_status_names_the_current_folder_while_the_card_is_in(self):
        script = asked(0, "play 60008") + asked(20, "status") + ["drive pull"] + asked(40, "status") + ["drive plug"] + polls(60, 300) + asked(6100, "status")
        run = with_drive(SHOW, NESTED, script)
        self.assertEqual(statuses(run), [(60008, 60004), ("all", 1), (60008, 60004)])


WINDOW = 86_400_000
# The test card with a turn of 5,000 ms in `night`, so that a turn of its playlist is in
# progress when a window ends: `night` is `night/comet.odrg`, 5,000 ms, then
# `night/deep/x.odrg` and `night/deep/deeper/y.odrg`, 4,000 ms each, 13,000 ms a round.
WINDOWED = {**NESTED, "night/comet.odrg": loop_of(5, 7)}


def status_lines(run):
    return [reply for reply in replies(run) if "on" in reply]


def left_of(run):
    return [(reply["playing"], reply["animation"], reply["left"]) for reply in status_lines(run)]


class TheWindow(unittest.TestCase):
    def test_left_counts_the_seconds_down_and_is_0_from_the_windows_end_to_the_turns_end(self):
        # The turn of the chosen playlist's first animation begins at the refresh after the
        # choice, at 20 ms; the window began at the choice, at 0.
        times = (0, 1000, 60_000, WINDOW - 100, WINDOW + 100, WINDOW + 2_900, WINDOW + 3_100)
        run = with_drive(SHOW, WINDOWED, asked(0, "play 60008") + asked(20) + [line for time in times for line in asked(time, "status")])
        self.assertEqual(replies(run)[0], DONE)
        # The round of `night` begins at 86,398,020; the turn of `night/comet.odrg` runs to
        # 86,403,020, past the window's end, and `night/deep` is current from there.
        self.assertEqual(left_of(run), [(60008, 60004, 86399), (60008, 60004, 86399), (60008, 60005, 86340), (60008, 60004, 0), (60008, 60004, 0), (60008, 60004, 0),
                                        (60009, 60005, 86399)])

    def test_the_rotation_goes_through_the_tree_and_to_the_root_after_the_last(self):
        # `night/deep` from 86,403,020 for a window, its round 8,000 ms; `night/deep/deeper`
        # from 172,803,020, its turn 4,000 ms; the root from 259,203,020, whose round of
        # 31,000 ms is in its first turn, the show's own, when the window ends at
        # 345,603,020: the root plays to 345,604,020, then `a b`; then `night` again.
        times = (WINDOW + 3_100, 2 * WINDOW + 3_100, 3 * WINDOW + 3_100, 4 * WINDOW + 3_100, 4 * WINDOW + 4_100, 5 * WINDOW + 3_100, 5 * WINDOW + 4_100)
        run = with_drive(SHOW, WINDOWED, asked(0, "play 60008") + asked(20) + [line for time in times for line in asked(time, "status")])
        self.assertEqual(left_of(run), [(60009, 60005, 86399), (60010, 60006, 86399), ("all", 1, 86399), ("all", 1, 0), (60007, 60003, 86399), (60007, 60003, 0),
                                        (60008, 60004, 86399)])

    def test_a_gap_of_many_windows_is_taken_at_one_refresh(self):
        run = with_drive(SHOW, WINDOWED, asked(0, "play 60008") + asked(20) + asked(5 * WINDOW + 4_100, "status") + asked(5 * WINDOW + 9_100, "status"))
        self.assertEqual(left_of(run), [(60008, 60004, 86399), (60008, 60005, 86394)])

    def test_a_window_that_ends_during_a_cycle_changes_the_current_playlist_and_not_what_plays(self):
        cycled = show_of([{"id": 1, "file": "four.odrg"}, {"id": 3, "cycle": [1], "seconds": 2}], {"four.odrg": loop_of(4, 1)}, min_seconds=4)
        with a_drive(WINDOWED) as top:
            script = asked(0, "play 60008") + asked(1000, "play 3") + asked(WINDOW + 100, "status") + asked(WINDOW + 200, "play 60005") + asked(WINDOW + 300, "status")
            run = support.start(cycled, script, ["--drive", top])
        self.assertEqual(left_of(run), [(3, 1, 86400), (60009, 60005, 86399)])

    def test_a_window_that_ends_under_a_mapping_test_is_taken_when_the_test_ends(self):
        demo = support.demo_show()
        drive = {"night/comet.odrg": support.clip(7, 60, 60, (1000,) * 5)}
        with a_drive(drive) as top:
            first = support.start(demo, asked(0, "list"), ["--drive", top])
            night = folders(replies(first)[0])[0][0]
            script = asked(0, f"play {night}") + asked(1000, "mapping test on") + asked(WINDOW + 100, "status") + asked(WINDOW + 200, "mapping test off", "status")
            run = support.start(demo, script, ["--drive", top])
        self.assertEqual([reply for reply in replies(run) if "on" not in reply], [DONE] * 3)
        self.assertEqual([(playing, left) for playing, _, left in left_of(run)], [(None, 0), ("all", 86400)])
        self.assertNotEqual(status_lines(run)[1]["animation"], None)

    def test_the_root_alone_is_not_changed_by_the_window(self):
        # The flat card's round is 14,000 ms: the turn of `A.ODRG`, 6,000 ms, runs from
        # 86,398,000 across the window's end, and the root is current again from its end.
        script = asked(0) + asked(WINDOW - 100, "status") + asked(WINDOW + 100, "status") + asked(WINDOW + 4_100, "status")
        run = with_drive(SHOW, {"b.odrg": loop_of(2, 5), "A.ODRG": loop_of(3, 6)}, script)
        self.assertEqual(left_of(run), [("all", 60001, 0), ("all", 60001, 0), ("all", 60002, 86399)])
        # Without a card the turns of 4,000 ms end at the window's end exactly.
        without = support.start(SHOW, script)
        self.assertEqual(left_of(without), [("all", 1, 0), ("all", 1, 86399), ("all", 1, 86395)])


def store_calls(run):
    """The storage calls of a session after its start, as `--trace-store` prints them."""
    return [line[len("store "):] for line in run.lines if line.startswith("store ")]


def playlist_writes(run):
    """The storage calls of the saved playlist's file, in order: the part opened and renamed."""
    return [call for call in store_calls(run) if "playlist" in call]


WRITE = ["write_open playlist.part 1", "rename playlist.part playlist.txt 1"]


class TheSavedFile(unittest.TestCase):
    def test_a_choice_writes_the_file_at_once_and_every_15_minutes_while_a_folder_is_current(self):
        with a_drive(NESTED) as top:
            run, kept = support.start_and_keep(SHOW, asked(0, "play 60008") + asked(20) + asked(899_000) + asked(900_000) + asked(1_800_000) + asked(1_900_000),
                                               ["--drive", top, "--trace-store"])
        self.assertEqual(kept["playlist.txt"], b"odrig-playlist 1\nnight\n1800000\n")
        self.assertNotIn("playlist.part", kept)
        self.assertEqual(playlist_writes(run), WRITE * 3)

    def test_the_root_chosen_is_saved_too_and_a_flat_card_or_none_writes_nothing(self):
        with a_drive(NESTED) as top:
            run, kept = support.start_and_keep(SHOW, asked(0, "play 60008") + asked(20, "play all") + asked(40), ["--drive", top, "--trace-store"])
        self.assertEqual(kept["playlist.txt"], b"odrig-playlist 1\n\n0\n")
        self.assertEqual(playlist_writes(run), WRITE * 2)
        flat = with_drive(SHOW, {"b.odrg": loop_of(2, 5)}, asked(0, "play all") + asked(2_000_000, "play 60001", "play all"), options=["--trace-store"])
        none = support.start(SHOW, asked(0, "play all") + asked(2_000_000, "play all"), ["--trace-store"])
        self.assertEqual((playlist_writes(flat), playlist_writes(none)), ([], []))

    def test_a_write_waits_while_an_upload_receives_its_bytes(self):
        data = loop_of(2, 9)
        script = asked(0, *support.upload_lines(5, "new.odrg", data)[:1]) + asked(20, "play 60008") + asked(40) + asked(60, "upload cancel") + asked(80)
        with a_drive(NESTED) as top:
            run = support.start(SHOW, script, ["--drive", top, "--trace-store"])
        calls = store_calls(run)
        self.assertEqual(playlist_writes(run), WRITE)
        self.assertLess(calls.index("remove upload.part 1"), calls.index("write_open playlist.part 1"))

    def test_a_restart_plays_the_saved_folder_with_the_saved_time(self):
        with a_drive(NESTED) as top:
            _, kept = support.start_and_keep(SHOW, asked(0, "play 60008") + asked(20) + asked(1_000_000), ["--drive", top])
            self.assertEqual(kept["playlist.txt"], b"odrig-playlist 1\nnight\n1000000\n")
            # At power-on the card is not read: the root plays in the folder's place, and the
            # folder, current again, takes over at the end of the turn in progress.
            second = support.start(kept, asked(0, "status") + polls(20, 300) + asked(6100, "status") + asked(10_100, "status"), ["--drive", top], check_first=False)
        self.assertEqual(left_of(second), [("all", 1, 85400), (60008, 60004, 85393), (60008, 60005, 85389)])

    def test_the_card_out_and_in_keeps_the_choice_and_the_window(self):
        script = asked(0, "play 60008") + asked(20) + ["drive pull"] + asked(40, "status") + ["drive plug"] + polls(60, 100) + asked(6100, "status")
        run = with_drive(SHOW, NESTED, script)
        self.assertEqual(left_of(run), [("all", 1, 86399), (60008, 60004, 86393)])

    def test_a_card_without_the_saved_folder_makes_the_root_current_and_saves_it(self):
        kept = {**SHOW, "playlist.txt": b"odrig-playlist 1\nnight\n5400000\n"}
        with a_drive({"b.odrg": loop_of(2, 5), "day/sun.odrg": loop_of(2, 6)}) as top:
            run, left = support.start_and_keep(kept, asked(0, "status") + polls(20, 300) + asked(6100, "status"), ["--drive", top, "--trace-store"], check_first=False)
        first, second = left_of(run)
        self.assertEqual(first, ("all", 1, 81000))
        # The root is current from the refresh at which the card was read, with a fresh window,
        # and the playlist goes on: the card's file after the show's.
        self.assertEqual(second[:2], ("all", 60001))
        self.assertGreater(second[2], 86390)
        self.assertRegex(left["playlist.txt"].decode(), r"^odrig-playlist 1\n\n[0-9]+\n$")
        self.assertEqual(playlist_writes(run), WRITE)

    def test_the_removal_of_the_current_folders_last_file_makes_the_root_current_and_saves_it(self):
        card_files = card({**NESTED, "solo/only.odrg": loop_of(2, 11)})
        items = every_level(card_files)
        ids = {item["file"]: item["id"] for item in items if "file" in item}
        solo = [item["id"] for item in items if item.get("playlist") == "solo"][0]
        with a_card(card_files) as top:
            script = polls(0, 400) + asked(8100, f"play {solo}", "status") + asked(8120, f"remove {ids['solo/only.odrg']}", "status", "list") + asked(8140)
            run, left = support.start_and_keep(SHOW, script, ["--drive", top, "--trace-store"], check_first=False)
        before, after = status_lines(run)
        self.assertEqual((before["playing"], before["animation"]), (solo, ids["solo/only.odrg"]))
        self.assertEqual((after["playing"], after["left"]), ("all", 86400))
        self.assertNotIn("solo", [path for _, path in folders(replies(run)[-1])])
        # Written at the refresh after the removal, 20 ms into the fresh window.
        self.assertEqual(left["playlist.txt"], b"odrig-playlist 1\n\n20\n")

    def test_a_power_cut_during_the_write_leaves_the_old_choice_or_the_new_one(self):
        for at in range(1, 4):
            with self.subTest(at=at):
                with a_drive(NESTED) as top:
                    _, kept = support.start_and_keep(SHOW, asked(0, "play 60008") + asked(20), ["--drive", top])
                    options = ["--drive", top, "--cut-at", str(at), "--cut-keeps", "0"]
                    _, cut = support.start_and_keep(kept, asked(0, "play 60007") + asked(20), options, status=75)
                    again, left = support.start_and_keep(cut, asked(0, "status") + polls(20, 300) + asked(6100, "status"), ["--drive", top], check_first=False)
                self.assertNotIn("playlist.part", left)
                self.assertIn(left["playlist.txt"], (b"odrig-playlist 1\nnight\n0\n", b"odrig-playlist 1\na b\n0\n"))
                self.assertIn(left_of(again)[-1][0], (60007, 60008))

    def test_the_start_of_a_show_without_a_drive_makes_no_call_for_the_file(self):
        run = support.start(SHOW, asked(0, "status"), ["--trace-store", "--trace-read-at"])
        self.assertFalse(any("playlist" in line for line in run.lines if not line.startswith("reply ")))


if __name__ == "__main__":
    unittest.main()

"""The tree of a card's folders: its order on a legacy and on a cataloged card, the folders'
ids after the files', the folder items of `list`, the paths in the saved order and in the
catalog, and the limits of the table."""

import json
import unittest

from odrig import catalog

from . import support
from .test_catalog_drive import card, polls
from .test_catalog_writes import a_card, folder_of
from .test_drive import DONE, SHOW, a_drive, asked, logged, refusal, replies, statuses, with_drive
from .test_order import HEADER, ordered
from .test_playback import T0
from .test_playlist import CANVAS, loop_of

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


def listing(time):
    """A refresh and `list` from every position of 0 to 79 on, so that the replies hold the
    chain of pages of `list` from the first on: `paged` follows it."""
    return asked(time, *(f"list {start}" for start in range(80)))


def paged(answers):
    """The items of every page of `list`, from the replies of `listing`."""
    items = []
    position = 0
    while position is not None:
        items += answers[position]["items"]
        position = answers[position]["next"]
    return items


class TheTree(unittest.TestCase):
    def test_a_legacy_card_lists_its_folders_after_the_shows_items_with_ids_after_the_files(self):
        reply = replies(with_drive(SHOW, NESTED, asked(0, "list")))[0]
        self.assertEqual([item["id"] for item in reply["items"]], [1, 60007, 60008, 60009, 60010, 60001, 60002, 60003, 60004, 60005, 60006])
        self.assertEqual(folders(reply), list(zip(range(60007, 60011), TREE)))
        self.assertEqual(files(reply), [(1, "four.odrg"), (60001, "A.ODRG"), (60002, "b.odrg"), (60003, "a b/c.odrg"), (60004, "night/comet.odrg"),
                                        (60005, "night/deep/x.odrg"), (60006, "night/deep/deeper/y.odrg")])
        self.assertEqual(reply["items"][1], {"id": 60007, "playlist": "a b", "external": True})

    def test_a_cataloged_card_lists_the_same_tree_whatever_the_order_of_its_pages(self):
        reply = replies(on_cataloged_card(card(NESTED), asked(8100, "list")))[0]
        self.assertEqual(folders(reply), list(zip(range(60007, 60011), TREE)))
        self.assertEqual(sorted(name for _, name in files(reply)), sorted(["four.odrg", *NESTED]))
        self.assertEqual([item["id"] for item in reply["items"]][:5], [1, 60007, 60008, 60009, 60010])
        self.assertEqual(sorted(id for id, _ in files(reply)), [1, *range(60001, 60007)])

    def test_the_positions_of_list_count_the_folders(self):
        run = with_drive(SHOW, NESTED, asked(0, "list 1", "list 3", "list 5", "list 11"))
        first, third, fifth, beyond = replies(run)
        self.assertEqual([item["id"] for item in first["items"]], [60007, 60008, 60009, 60010, 60001, 60002, 60003, 60004, 60005, 60006])
        self.assertEqual([item["id"] for item in third["items"]], [60009, 60010, 60001, 60002, 60003, 60004, 60005, 60006])
        self.assertEqual(files(fifth), files(first))
        self.assertEqual(beyond, {"ok": True, "items": [], "next": None})

    def test_a_page_holds_folder_items_of_the_longest_paths(self):
        # Ten files whose paths are 100 bytes, in three folders each, thirty folders in all.
        drive = {}
        for number in range(10):
            drive[f"{number:02d}{'a' * 28}/{'b' * 30}/{'c' * 31}/x.odrg"] = loop_of(2, number)
        run = with_drive(SHOW, drive, listing(0))
        answers = replies(run)
        lines = [line[len("reply "):] for line in run.lines if line.startswith("reply ")]
        self.assertTrue(all(len(line.encode()) + 1 <= 1024 for line in lines))
        self.assertGreater(answers[0]["next"], 1)
        whole = paged(answers)
        self.assertEqual(len([item for item in whole if "playlist" in item]), 30)
        self.assertEqual(len(whole), 1 + 30 + 10)
        self.assertEqual([item["playlist"] for item in whole[1:4]], [f"00{'a' * 28}", f"00{'a' * 28}/{'b' * 30}", f"00{'a' * 28}/{'b' * 30}/{'c' * 31}"])
        self.assertEqual([item["id"] for item in whole], [1, *range(60011, 60041), *range(60001, 60011)])

    def test_a_33rd_sub_folder_named_by_a_catalog_is_left_out_with_too_many_folders(self):
        names = [f"f{number:02d}/x.odrg" for number in range(33)]
        storage = catalog.MemoryStorage({name: loop_of(2, number) for number, name in enumerate(names)})
        made, refused = catalog.rebuild(storage, names=names, canvas=CANVAS)
        self.assertEqual((refused, made.marker.counts and sum(made.marker.counts)), ([], 33))
        run = on_cataloged_card(storage.files, listing(8100))
        items = paged(replies(run))
        self.assertEqual(len([item for item in items if "playlist" in item]), 32)
        left_out = [item for item in items if item.get("fault") == "too-many-folders"]
        self.assertEqual(len(left_out), 1)
        self.assertEqual([line for line in logged(run) if "too-many-folders" in line], [f"drive file {left_out[0]['file']} left out: too-many-folders"])
        self.assertEqual(len([item for item in items if "file" in item and "fault" not in item]), 1 + 32)

    def test_a_folder_without_a_file_is_no_folder_of_the_tree(self):
        with a_drive(NESTED) as top:
            support.pathlib.Path(top, "odrig", "empty", "deeper").mkdir(parents=True)
            run = support.start(SHOW, asked(0, "list"), ["--drive", top])
        self.assertEqual(folders(replies(run)[0]), list(zip(range(60007, 60011), TREE)))


class ThePathsInTheSavedOrderAndTheCatalog(unittest.TestCase):
    def test_order_move_of_a_file_in_a_folder_writes_its_path(self):
        with a_drive(NESTED) as top:
            first = support.start(SHOW, asked(0, "order get"), ["--drive", top])
            revision = replies(first)[0]["revision"]
            self.assertEqual(replies(first)[0]["ids"], [1, 60001, 60002, 60003, 60004, 60005, 60006])
            run, kept = support.start_and_keep(SHOW, asked(0, f"order move {revision} 60004 60001", "order get"), ["--drive", top])
        self.assertEqual(replies(run), [{"ok": True}, {"ok": True, "ids": [1, 60004, 60001, 60002, 60003, 60005, 60006], "next": None, "revision": replies(run)[1]["revision"]}])
        self.assertEqual(kept["order.txt"], (HEADER + "i 1\nx night/comet.odrg\nx A.ODRG\nx b.odrg\nx a b/c.odrg\nx night/deep/x.odrg\nx night/deep/deeper/y.odrg\n").encode())

    def test_remove_of_a_file_in_a_folder_removes_that_file_and_an_emptied_folder_leaves_the_tree(self):
        card_files = card(NESTED)
        ids = {name: id for id, name in files(replies(on_cataloged_card(card_files, asked(8100, "list")))[0])}
        with a_card(card_files) as top:
            script = polls(0, 400) + asked(8100, f"remove {ids['night/comet.odrg']}", "list", f"remove {ids['a b/c.odrg']}", "list")
            run = support.start(SHOW, script, ["--drive", top], check_first=False)
            left = folder_of(top)
        done, after_first, done_again, after_second = replies(run)
        self.assertEqual((done, done_again), ({"ok": True}, {"ok": True}))
        self.assertEqual(folders(after_first), list(zip(range(60007, 60011), TREE)))
        self.assertNotIn("night/comet.odrg", [name for _, name in files(after_first)])
        self.assertEqual(folders(after_second), [(60008, "night"), (60009, "night/deep"), (60010, "night/deep/deeper")])
        self.assertNotIn("night/comet.odrg", left)
        self.assertNotIn("a b/c.odrg", left)
        self.assertEqual(sorted(name for name in left if name.lower().endswith(".odrg")), ["A.ODRG", "b.odrg", "night/deep/deeper/y.odrg", "night/deep/x.odrg"])
        found = catalog.read(catalog.MemoryStorage(left))
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
        run = with_drive(SHOW, drive, asked(0, "list", "play 60012") + asked(20, "status"))
        reply, done = replies(run)[:2]
        self.assertEqual(folders(reply)[-1], (60012, "solo"))
        self.assertEqual([item.get("fault") for item in reply["items"] if item.get("file") == "solo/bad.odrg"], ["bad-magic"])
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
        self.assertEqual(folders(replies(on_card)[1]), list(zip(range(60007, 60011), TREE)))


class TheExhaustingOrder(unittest.TestCase):
    def test_a_folder_with_one_animation_plays_it_again_and_again(self):
        run = with_drive(SHOW, {"b.odrg": loop_of(2, 5), "night/comet.odrg": loop_of(2, 7)}, asked(0, "play 60003") + every(100, 15000, "status"))
        self.assertEqual(replies(run)[0], DONE)
        self.assertEqual(set(animation for _, animation in statuses(run)), {60002})

    def test_the_root_plays_its_own_animations_in_the_saved_order_then_each_folder_once_then_again(self):
        # The saved order puts `night/comet.odrg` first and `b.odrg` second. The root begins
        # with the show's first animation at power-on, as always, goes on with its own
        # animations by their keys, then each folder's once in the tree's order, and comes
        # back to its own, `b.odrg` first by the saved order; `night/comet.odrg` plays in
        # its folder's turn, not first.
        installed = ordered(SHOW, "x night/comet.odrg", "x b.odrg")
        with a_drive(NESTED) as top:
            run = support.start(installed, every(100, 45000, "status"), ["--drive", top])
        self.assertEqual(played(run)[:9], [1, 60001, 60003, 60004, 60005, 60006, 60002, 1, 60001])

    def test_a_folder_exhausts_its_own_animations_then_its_nested_folders_then_again(self):
        run = with_drive(SHOW, NESTED, asked(0, "play 60008") + every(100, 20000, "status"))
        self.assertEqual(played(run)[:5], [60004, 60005, 60006, 60004, 60005])

    def test_the_order_within_a_folder_follows_the_saved_order(self):
        drive = {**NESTED, "night/zeta.odrg": loop_of(2, 11)}
        installed = ordered(SHOW, "x night/zeta.odrg")
        with a_drive(drive) as top:
            run = support.start(installed, asked(0, "list", "play 60009") + every(100, 25000, "status"), ["--drive", top])
        reply = replies(run)[0]
        self.assertEqual(folders(reply)[1], (60009, "night"))
        self.assertEqual([id for id, name in files(reply) if name in ("night/comet.odrg", "night/zeta.odrg")], [60004, 60005])
        self.assertEqual(played(run)[:5], [60005, 60004, 60006, 60007, 60005])

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


if __name__ == "__main__":
    unittest.main()

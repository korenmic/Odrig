import json
import unittest

from . import support
from .test_drive import a_drive, asked, refusal, replies
from .test_playback import T0
from .test_playlist import loop_of, show_of

HEADER = "odrig-order 1\n"


def animations(count, start=None, ignored=(), first_id=1):
    """A show of animations with ids from `first_id` on, each with a loop and a turn of four
    seconds, the one file of each its own."""
    items = []
    files = {}
    for number in range(first_id, first_id + count):
        item = {"id": number, "file": f"a{number}.odrg"}
        if number in ignored:
            item["ignored"] = True
        items.append(item)
        files[item["file"]] = loop_of(4, number)
    return show_of(items, files, start, min_seconds=4)


def ordered(files, *entries, header=HEADER):
    """The files with an `order.txt` of these entry lines."""
    return {**files, "order.txt": header + "".join(f"{entry}\n" for entry in entries)}


def turns(run):
    """The animation each `status` of a session names."""
    return [reply["animation"] for reply in replies(run) if "on" in reply]


def every_turn(count, begin=100):
    """A refresh at `begin`, where the turn that plays then begins when it was just played,
    and `status` in the middle of each of so many turns of four seconds after it."""
    script = asked(begin)
    for turn in range(count):
        script += asked(begin + 2000 + 4000 * turn, "status")
    return script


def ticks(begin, count):
    """A refresh at each grid time from `begin` on, so many."""
    return [f"poll {T0 + begin + 20 * step}" for step in range(count)]


def order_ids(run):
    """The ids of every reply of `order get` of a session, joined, and their revisions."""
    ids = []
    revisions = set()
    for reply in replies(run):
        if "ids" in reply:
            ids += reply["ids"]
            revisions.add(reply["revision"])
    return ids, revisions


class ThePlaylistInTheSavedOrder(unittest.TestCase):
    def test_without_an_order_file_the_playlist_goes_in_the_order_of_the_show(self):
        run = support.start(animations(3), every_turn(4))
        self.assertEqual(turns(run), [1, 2, 3, 1])

    def test_the_order_file_orders_the_playlist_and_its_wrapping(self):
        run = support.start(ordered(animations(3), "i 3", "i 1", "i 2"), every_turn(5))
        self.assertEqual(turns(run), [3, 1, 2, 3, 1])

    def test_animations_the_file_does_not_name_come_after_those_it_names(self):
        run = support.start(ordered(animations(4), "i 3"), every_turn(5))
        self.assertEqual(turns(run), [3, 1, 2, 4, 3])

    def test_play_all_begins_with_the_first_of_the_order_and_play_goes_on_after_the_one_played(self):
        files = ordered(animations(3), "i 2", "i 3", "i 1")
        script = asked(0) + asked(10, "play all") + asked(20) + asked(2020, "status") + asked(4120, "status")
        script += asked(4200, "play 3") + asked(4220) + asked(4300, "status") + asked(8320, "status")
        run = support.start(files, script)
        self.assertEqual(turns(run), [2, 3, 3, 1])

    def test_the_start_of_the_show_begins_the_playlist_which_then_follows_the_order(self):
        run = support.start(ordered(animations(3, start=1), "i 2", "i 3", "i 1"), every_turn(4))
        self.assertEqual(turns(run), [1, 2, 3, 1])

    def test_an_ignored_animation_keeps_its_place_and_is_skipped(self):
        files = ordered(animations(3, ignored=(1,)), "i 1", "i 3", "i 2")
        run = support.start(files, every_turn(3) + asked(12200, "order get"))
        self.assertEqual(turns(run), [3, 2, 3])
        self.assertEqual(order_ids(run)[0], [1, 3, 2])

    def test_a_file_without_the_header_names_nothing(self):
        for header in ("", "odrig-order 2\n", "odrig-order 1 \n", "\n"):
            with self.subTest(header=header):
                run = support.start(ordered(animations(3), "i 3", "i 2", header=header), every_turn(3))
                self.assertEqual(turns(run), [1, 2, 3])

    def test_malformed_lines_take_no_place_and_the_first_entry_of_an_id_counts(self):
        files = ordered(animations(4), "i 03", "i x", "y 1", "x", "i 70000", "i 4", "i 2", "i 4", "i 0", "i 3", "i 99999")
        run = support.start(files, asked(100, "order get"))
        self.assertEqual(order_ids(run)[0], [4, 2, 3, 1])

    def test_a_line_without_its_line_feed_at_the_end_is_no_entry(self):
        files = {**animations(3), "order.txt": HEADER + "i 3\ni 2"}
        run = support.start(files, asked(100, "order get"))
        self.assertEqual(order_ids(run)[0], [3, 1, 2])

    def test_the_order_is_the_same_after_a_restart(self):
        files = ordered(animations(3), "i 2", "i 3")
        first = support.start(files, asked(100, "order get"))
        again = support.start(files, asked(100, "order get"))
        self.assertEqual(order_ids(first), order_ids(again))
        self.assertEqual(order_ids(first)[0], [2, 3, 1])


class CardEntries(unittest.TestCase):
    SHOW = animations(2)
    DRIVE = {"b.odrg": loop_of(4, 5), "A.ODRG": loop_of(4, 6), "c d.odrg": loop_of(4, 7)}

    def run_with_drive(self, files, script, options=()):
        with a_drive(self.DRIVE) as top:
            return support.start(files, script, ["--drive", top, *options])

    def test_card_animations_are_named_by_their_file_names_in_one_mixed_order(self):
        files = ordered(self.SHOW, "x b.odrg", "i 2", "x c d.odrg", "i 1", "x A.ODRG")
        run = self.run_with_drive(files, asked(0, "list", "order get"))
        ids = {item["file"]: item["id"] for item in replies(run)[0]["items"]}
        self.assertEqual(order_ids(run)[0], [ids["b.odrg"], 2, ids["c d.odrg"], 1, ids["A.ODRG"]])

    def test_the_playlist_plays_card_and_internal_animations_in_the_saved_order(self):
        files = ordered(self.SHOW, "x b.odrg", "i 2", "x A.ODRG", "i 1")
        run = self.run_with_drive(files, asked(0, "list", "play all") + every_turn(6))
        ids = {item["file"]: item["id"] for item in replies(run)[0]["items"]}
        self.assertEqual(turns(run)[:5], [ids["b.odrg"], 2, ids["A.ODRG"], 1, ids["c d.odrg"]])

    def test_a_card_entry_whose_file_is_absent_keeps_its_place_and_is_skipped(self):
        files = ordered(self.SHOW, "x gone.odrg", "i 2", "x b.odrg", "i 1")
        run = self.run_with_drive(files, asked(0, "list", "order get"))
        ids = {item["file"]: item["id"] for item in replies(run)[0]["items"]}
        self.assertEqual(order_ids(run)[0], [2, ids["b.odrg"], 1, ids["A.ODRG"], ids["c d.odrg"]])

    def test_a_card_pulled_out_and_plugged_in_again_takes_its_places_again(self):
        files = ordered(self.SHOW, "x c d.odrg", "i 2", "x b.odrg", "i 1")
        script = asked(0, "list", "order get") + ["drive pull"] + asked(20, "order get") + ["drive plug"] + ticks(40, 120)
        script += asked(2440, "list", "order get")
        run = self.run_with_drive(files, script)
        lists = [reply for reply in replies(run) if "items" in reply]
        orders = [reply["ids"] for reply in replies(run) if "ids" in reply]
        before = {item["file"]: item["id"] for item in lists[0]["items"]}
        self.assertEqual(orders[0], [before["c d.odrg"], 2, before["b.odrg"], 1, before["A.ODRG"]])
        self.assertEqual(orders[1], [2, 1])
        after = {item["file"]: item["id"] for item in lists[1]["items"]}
        self.assertEqual(orders[2], [after["c d.odrg"], 2, after["b.odrg"], 1, after["A.ODRG"]])

    def test_the_playlist_goes_on_after_a_card_animation_that_left_in_the_saved_order(self):
        files = ordered(self.SHOW, "i 1", "x b.odrg", "i 2", "x A.ODRG")
        script = asked(0, "list", "play all") + asked(120) + asked(4220, "status") + ["drive pull"] + asked(4240, "status")
        run = self.run_with_drive(files, script)
        ids = {item["file"]: item["id"] for item in replies(run)[0]["items"]}
        self.assertEqual(turns(run), [ids["b.odrg"], 2])

    def test_every_animation_item_of_list_says_whether_it_is_external(self):
        files = ordered(dict(self.SHOW, **{"show.json": json.dumps({**json.loads(self.SHOW["show.json"]), "items": json.loads(self.SHOW["show.json"])["items"] + [{"id": 9, "cycle": [1, 2], "seconds": 3}]})}), "i 2")
        run = self.run_with_drive(files, asked(0, "list"))
        items = replies(run)[0]["items"]
        self.assertEqual([(item["id"], item.get("external")) for item in items if "cycle" not in item], [(1, False), (2, False), (60001, True), (60002, True), (60003, True)])
        self.assertEqual([item for item in items if "cycle" in item], [{"id": 9, "cycle": [1, 2], "seconds": 3}])
        self.assertEqual(list(items[0]), ["id", "file", "bytes", "ignored", "external", "type"])
        self.assertEqual(list(items[3]), ["id", "file", "bytes", "external", "type"])


class OrderGet(unittest.TestCase):
    def test_its_parts_hold_every_listed_animation_once_with_one_revision(self):
        items = [{"id": number, "file": "a.odrg"} for number in range(1, 301)]
        files = show_of(items, {"a.odrg": loop_of(4, 1)}, min_seconds=4)
        files["order.txt"] = HEADER + "".join(f"i {number}\n" for number in range(300, 150, -1))
        script = asked(0, "order get")
        run = support.start(files, script)
        first = replies(run)[0]
        self.assertIsNotNone(first["next"])
        parts = [first]
        while parts[-1]["next"] is not None:
            run = support.start(files, asked(0, f"order get {parts[-1]['next']}"))
            parts.append(replies(run)[0])
        ids = [number for part in parts for number in part["ids"]]
        self.assertEqual(ids, list(range(300, 150, -1)) + list(range(1, 151)))
        self.assertEqual(len({part["revision"] for part in parts}), 1)
        self.assertTrue(all(len(json.dumps(part, separators=(",", ":"))) < 1024 for part in parts))

    def test_a_position_at_or_after_the_end_gives_no_ids(self):
        run = support.start(animations(2), asked(0, "order get 2", "order get 65535"))
        self.assertEqual([(reply["ids"], reply["next"]) for reply in replies(run)], [([], None), ([], None)])

    def test_the_revision_follows_the_order_and_the_listed_animations(self):
        plain = animations(3)
        revisions = {}
        for name, files in {"plain": plain, "same": dict(plain), "ordered": ordered(plain, "i 2"), "fewer": animations(2)}.items():
            revisions[name] = order_ids(support.start(files, asked(0, "order get")))[1].pop()
        self.assertEqual(revisions["plain"], revisions["same"])
        self.assertEqual(len({revisions["plain"], revisions["ordered"], revisions["fewer"]}), 3)

    def test_it_is_refused_as_list_is(self):
        # While the player reads the installed animations after a start, both answer.
        run = support.start(animations(2), asked(0, "list", "order get", "order get x", "order get 65536", "order get 1 2", "order", "order put"), check_first=False)
        listed, order = replies(run)[:2]
        self.assertIn(None, [item["bytes"] for item in listed["items"]])
        self.assertEqual((order["ids"], order["next"]), ([1, 2], None))
        self.assertEqual(replies(run)[2:], [refusal("bad-argument")] * 5)
        broken = {**animations(2), "show.json": "{"}
        run = support.start(broken, asked(0, "order get"))
        self.assertEqual(replies(run), [refusal("show-invalid")])


class NewUploadsAndRemovals(unittest.TestCase):
    def test_an_upload_that_reuses_an_id_an_old_entry_names_takes_its_place_now_and_after_a_restart(self):
        files = ordered(animations(2), "i 9", "i 2", "i 1")
        data = loop_of(4, 9)
        script = asked(0, "order get", *support.upload_lines(9, "nine.odrg", data))
        script += [f"poll {T0 + 20 * step}" for step in range(1, 12)] + [support.line(T0 + 300, support.upload_end(data)), support.line(T0 + 301, "order get")]
        run, kept = support.start_and_keep(files, script)
        orders = [reply["ids"] for reply in replies(run) if "ids" in reply]
        self.assertEqual(orders, [[2, 1], [9, 2, 1]])
        again = support.start(kept, asked(0, "order get"))
        self.assertEqual(order_ids(again)[0], [9, 2, 1])

    def test_a_new_upload_is_last_and_a_removal_keeps_the_order_of_the_others(self):
        files = ordered(animations(3), "i 3", "i 1")
        data = loop_of(4, 8)
        script = asked(0, *support.upload_lines(8, "eight.odrg", data))
        script += [f"poll {T0 + 20 * step}" for step in range(1, 12)] + [support.line(T0 + 300, support.upload_end(data)), support.line(T0 + 301, "order get")]
        script += [support.line(T0 + 302, "remove 1"), support.line(T0 + 303, "order get")]
        run = support.start(files, script)
        orders = [reply["ids"] for reply in replies(run) if "ids" in reply]
        self.assertEqual(orders, [[3, 1, 2, 8], [3, 2, 8]])

    def test_an_order_part_left_by_an_interrupted_move_is_removed_at_the_start(self):
        files = {**ordered(animations(2), "i 2"), "order.part": HEADER + "i 1\n"}
        run, kept = support.start_and_keep(files, asked(0, "order get"))
        self.assertNotIn("order.part", kept)
        self.assertEqual(kept["order.txt"], files["order.txt"].encode())
        self.assertEqual(order_ids(run)[0], [2, 1])

    def test_a_folder_without_an_order_part_gets_no_storage_call_more(self):
        run = support.start(animations(2), options=["--trace-store"])
        self.assertFalse(any("order" in call for call in run.stored))



def revision(files, options=()):
    """The revision `order get` reports for these files."""
    return order_ids(support.start(files, asked(0, "order get"), options))[1].pop()


def moved(files, *moves, options=()):
    """A session that moves, each move `(id, before)` with the revision of the moment, and
    its run and the files it leaves. Each move asks for the revision first."""
    kept = dict(files)
    runs = []
    for what, before in moves:
        current = revision(kept, options)
        run, kept = support.start_and_keep(kept, asked(0, f"order move {current} {what} {before}", "order get"), options)
        runs.append(run)
    return runs, kept


class OrderMove(unittest.TestCase):
    def test_it_moves_an_animation_before_another_and_saves_the_whole_order(self):
        runs, kept = moved(animations(3), (3, 1))
        self.assertEqual(replies(runs[0])[0], {"ok": True})
        self.assertEqual(order_ids(runs[0])[0], [3, 1, 2])
        self.assertEqual(kept["order.txt"], (HEADER + "i 3\ni 1\ni 2\n").encode())
        self.assertNotIn("order.part", kept)
        again = support.start(kept, every_turn(3))
        self.assertEqual(turns(again), [3, 1, 2])

    def test_it_moves_an_animation_to_the_end(self):
        runs, kept = moved(ordered(animations(3), "i 2", "i 1"), (2, "end"))
        self.assertEqual(order_ids(runs[0])[0], [1, 3, 2])
        self.assertEqual(kept["order.txt"], (HEADER + "i 1\ni 3\ni 2\n").encode())

    def test_moves_of_external_animations_keep_absent_entries_in_their_places(self):
        drive = {"b.odrg": loop_of(4, 5), "A.ODRG": loop_of(4, 6), "c d.odrg": loop_of(4, 7)}
        files = ordered(animations(2), "x gone.odrg", "i 2", "x b.odrg", "i 1")
        with a_drive(drive) as top:
            options = ["--drive", top]
            first = support.start(files, asked(0, "list"), options)
            ids = {item["file"]: item["id"] for item in replies(first)[0]["items"]}
            runs, kept = moved(files, (ids["A.ODRG"], 2), (1, ids["b.odrg"]), options=options)
            self.assertEqual(order_ids(runs[0])[0], [ids["A.ODRG"], 2, ids["b.odrg"], 1, ids["c d.odrg"]])
            self.assertEqual(order_ids(runs[1])[0], [ids["A.ODRG"], 2, 1, ids["b.odrg"], ids["c d.odrg"]])
        self.assertEqual(kept["order.txt"], (HEADER + "x gone.odrg\nx A.ODRG\ni 2\ni 1\nx b.odrg\nx c d.odrg\n").encode())
        # Without the card its entries keep their places, and a move keeps them.
        runs, kept = moved(kept, (1, 2))
        self.assertEqual(order_ids(runs[0])[0], [1, 2])
        self.assertEqual(kept["order.txt"], (HEADER + "x gone.odrg\nx A.ODRG\ni 1\ni 2\nx b.odrg\nx c d.odrg\n").encode())

    def test_entries_of_ids_no_item_has_are_dropped_when_the_file_is_written(self):
        runs, kept = moved(ordered(animations(2), "i 7", "i 2", "i 1"), (1, 2))
        self.assertEqual(kept["order.txt"], (HEADER + "i 1\ni 2\n").encode())

    def test_a_move_that_changes_nothing_writes_nothing(self):
        files = ordered(animations(3), "i 2", "i 3", "i 1")
        current = revision(files)
        for line in (f"order move {current} 2 3", f"order move {current} 1 end", f"order move {current} 3 3"):
            with self.subTest(line=line):
                run, kept = support.start_and_keep(files, asked(0, line), ["--trace-store"])
                self.assertEqual(replies(run), [{"ok": True}])
                self.assertFalse(any(text.startswith("store ") for text in run.lines))
                self.assertEqual(kept, {name: content.encode() if isinstance(content, str) else content for name, content in files.items()})

    def test_every_refusal_comes_in_the_order_of_the_table(self):
        show = json.loads(animations(3)["show.json"])
        show["items"].append({"id": 9, "cycle": [1, 2], "seconds": 3})
        files = {**animations(3), "show.json": json.dumps(show)}
        current = revision(files)
        lines = {
            "order move": "bad-argument",
            f"order move {current} 1": "bad-argument",
            f"order move x 1 2": "bad-argument",
            f"order move {current} 0 2": "bad-argument",
            f"order move {current} 70000 2": "bad-argument",
            f"order move {current} 1 x": "bad-argument",
            f"order move {current} 1 0": "bad-argument",
            f"order move 4294967296 1 2": "bad-argument",
            f"order move {current} 1 2 3": "bad-argument",
            f"order move {current} 8 2": "unknown-id",
            f"order move {current} 1 8": "unknown-id",
            f"order move {current} 9 8": "unknown-id",
            f"order move {current + 1 if current < 4294967295 else 0} 9 2": "in-use",
            f"order move {current} 1 9": "in-use",
            f"order move {current + 1 if current < 4294967295 else 0} 1 2": "order-conflict",
        }
        run, kept = support.start_and_keep(files, asked(0, *lines))
        self.assertEqual(replies(run), [refusal(code) for code in lines.values()])
        self.assertNotIn("order.txt", kept)

    def test_it_is_busy_after_a_start_and_while_an_upload_is_open_and_invalid_with_an_invalid_show(self):
        files = animations(2)
        current = revision(files)
        run = support.start(files, asked(0, f"order move {current} 2 1"), check_first=False)
        self.assertEqual(replies(run), [refusal("busy")])
        data = loop_of(4, 9)
        run = support.start(files, asked(0, support.upload_lines(9, "nine.odrg", data)[0], f"order move {current} 2 1"))
        self.assertEqual(replies(run)[1], refusal("busy"))
        run = support.start({**files, "show.json": "{"}, asked(0, f"order move {current} 2 1"))
        self.assertEqual(replies(run), [refusal("show-invalid")])

    def test_a_host_whose_storage_cannot_be_changed_cannot_save_an_order(self):
        files = animations(2)
        current = revision(files, ["--only-space"])
        run = support.start(files, asked(0, f"order move {current} 2 1"), ["--only-space"])
        self.assertEqual(replies(run), [refusal("storage-error")])

    def test_a_stale_revision_changes_nothing(self):
        files = animations(2)
        stale = revision(files)
        data = loop_of(4, 9)
        script = asked(0, *support.upload_lines(9, "nine.odrg", data)) + [f"poll {T0 + 20 * step}" for step in range(1, 12)]
        script += [support.line(T0 + 300, support.upload_end(data)), support.line(T0 + 301, f"order move {stale} 2 1"), support.line(T0 + 302, "order get")]
        run, kept = support.start_and_keep(files, script)
        self.assertIn(refusal("order-conflict"), replies(run))
        self.assertEqual(order_ids(run)[0], [1, 2, 9])
        self.assertNotIn("order.txt", kept)

    def test_the_turn_in_progress_power_and_brightness_stay_and_the_next_turn_follows_the_new_order(self):
        files = animations(3)
        current = revision(files)
        script = every_turn(0) + asked(2100, "off", "brightness 40", "status", f"order move {current} 3 2", "status")
        script += asked(4200, "status") + asked(8200, "status")
        run = support.start(files, script)
        states = [(reply["animation"], reply["on"], reply["brightness"]) for reply in replies(run) if "on" in reply]
        self.assertEqual(states, [(1, False, 40), (1, False, 40), (3, False, 40), (2, False, 40)])

    def test_a_power_cut_at_any_call_of_a_move_leaves_the_old_order_or_the_new_one(self):
        files = ordered(animations(3), "i 2")
        current = revision(files)
        command = asked(0, f"order move {current} 3 2")
        observed, whole = support.start_and_keep(files, command, ["--trace-store"])
        first = len(observed.stored) + 1
        calls = sum(line.startswith("store ") for line in observed.lines)
        self.assertEqual(calls, 4)
        # The rename is the last call: a cut at any of them leaves the old order.
        for at in range(first, first + calls):
            for keeps in (0, 1):
                with self.subTest(at=at, keeps=keeps):
                    _, left = support.start_and_keep(files, command, ["--cut-at", str(at), "--cut-keeps", str(keeps)], status=75)
                    recovered, settled = support.start_and_keep(left, asked(0, "order get"))
                    self.assertEqual(order_ids(recovered)[0], [2, 1, 3])
                    self.assertNotIn("order.part", settled)
                    self.assertEqual(settled["order.txt"], files["order.txt"].encode())
        recovered = support.start(whole, asked(0, "order get"))
        self.assertEqual(order_ids(recovered)[0], [3, 2, 1])

    def test_a_failed_call_before_the_rename_changes_nothing_and_says_storage_error(self):
        files = ordered(animations(3), "i 2")
        current = revision(files)
        command = asked(0, f"order move {current} 3 2", "order get")
        observed = support.start(files, command, ["--trace-store"])
        first = len(observed.stored) + 1
        calls = sum(line.startswith("store ") for line in observed.lines)
        for at in range(first, first + calls):
            with self.subTest(at=at):
                run, kept = support.start_and_keep(files, command, ["--store-fails-at", str(at)])
                answer = replies(run)[0]
                if answer == {"ok": True}:
                    self.assertEqual(order_ids(run)[0], [3, 2, 1])
                    continue
                self.assertEqual(answer, refusal("storage-error"))
                self.assertEqual(order_ids(run)[0], [2, 1, 3])
                self.assertEqual(kept["order.txt"], files["order.txt"].encode())
                self.assertNotIn("order.part", kept)

    def test_it_works_while_a_test_of_the_mapping_shows(self):
        files = support.demo_show()
        current = revision(files)
        run = support.start(files, asked(0, "mapping test on", f"order move {current} 2 1", "order get", "mapping get"))
        self.assertEqual(replies(run)[1], {"ok": True})
        self.assertEqual(replies(run)[2]["ids"], [2, 1])
        self.assertTrue(replies(run)[3]["test"])


class UnavailableAnimations(unittest.TestCase):
    """An animation that `list` gives with a fault has its place in the saved order as any
    other: `order get` holds it where it stands, and it can be moved."""

    def test_an_installed_animation_with_a_fault_is_in_the_order_and_can_be_moved(self):
        files = ordered({**animations(3), "a2.odrg": b"nothing"}, "i 2", "i 3", "i 1")
        run = support.start(files, asked(0, "list", "order get"))
        self.assertEqual([item["id"] for item in replies(run)[0]["items"] if "fault" in item], [2])
        self.assertEqual(order_ids(run)[0], [2, 3, 1])
        runs, kept = moved(files, (2, "end"))
        self.assertEqual(replies(runs[0])[0], {"ok": True})
        self.assertEqual(order_ids(runs[0])[0], [3, 1, 2])
        self.assertEqual(kept["order.txt"], (HEADER + "i 3\ni 1\ni 2\n").encode())

    def test_a_file_of_the_card_left_out_for_a_fault_is_in_the_order_and_can_be_moved(self):
        drive = {"b.odrg": loop_of(4, 5), "zz.odrg": loop_of(4, 6)[:-3]}
        files = ordered(animations(2), "x zz.odrg", "i 2", "x b.odrg", "i 1")
        with a_drive(drive) as top:
            options = ["--drive", top]
            run = support.start(files, asked(0, "list", "order get"), options)
            listed = replies(run)[0]["items"]
            ids = {item["file"]: item["id"] for item in listed}
            self.assertEqual([item["file"] for item in listed if "fault" in item], ["zz.odrg"])
            self.assertEqual(order_ids(run)[0], [ids["zz.odrg"], 2, ids["b.odrg"], 1])
            runs, kept = moved(files, (ids["zz.odrg"], "end"), options=options)
            self.assertEqual(replies(runs[0])[0], {"ok": True})
            self.assertEqual(order_ids(runs[0])[0], [2, ids["b.odrg"], 1, ids["zz.odrg"]])
        self.assertEqual(kept["order.txt"], (HEADER + "i 2\nx b.odrg\ni 1\nx zz.odrg\n").encode())


if __name__ == "__main__":
    unittest.main()

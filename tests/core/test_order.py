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
        self.assertEqual(list(items[0]), ["id", "file", "bytes", "ignored", "external"])
        self.assertEqual(list(items[3]), ["id", "file", "bytes", "external"])


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
        run = support.start(animations(2), asked(0, "order get", "order get x", "order get 65536", "order get 1 2", "order", "order put"), check_first=False)
        self.assertEqual(replies(run), [refusal("busy")] + [refusal("bad-argument")] * 5)
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


if __name__ == "__main__":
    unittest.main()

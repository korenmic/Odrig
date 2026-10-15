import json
import re
import unittest

from odrig import errors, show

from . import support

EXAMPLE_SHOW = support.ROOT / "shows" / "example" / "show.json"


def source(version=1, brightness=128, items=None, start=..., **more):
    """The bytes of a show file; `...` leaves a member out."""
    if items is None:
        items = [{"id": 1, "file": "a.odrg"}]
    top = {"version": version, "brightness": brightness, "items": items, "start": start, **more}
    return json.dumps({name: value for name, value in top.items() if value is not ...}).encode()


def reason_of(data):
    try:
        show.loads(data)
    except errors.Rejection as rejection:
        return rejection.reason
    return None


class Accepted(unittest.TestCase):
    def test_the_example_of_the_show_document(self):
        text = (support.ROOT / "docs" / "show.md").read_text(encoding="utf-8")
        example = re.search(r"```json\n(.*?)```", text, re.DOTALL).group(1).encode()
        result = show.loads(example)
        self.assertEqual(result.brightness, 128)
        self.assertEqual(result.start, 3)
        self.assertEqual(
            result.items,
            (
                show.Item(1, "hello.odrg", None, None),
                show.Item(2, "dvd.odrg", None, None),
                show.Item(3, None, (1, 2), 15),
            ),
        )

    def test_a_show_without_start(self):
        self.assertIsNone(show.loads(source()).start)

    def test_an_animation_with_a_repeat_count_and_a_longest_duration(self):
        items = [{"id": 1, "file": "a.odrg", "repeat": 3, "max_seconds": 120}, {"id": 2, "file": "b.odrg", "max_seconds": 1},
                 {"id": 3, "file": "c.odrg", "repeat": 65535}, {"id": 4, "file": "d.odrg"}, {"id": 5, "cycle": [1, 4], "seconds": 9}]
        result = show.loads(source(items=items, start=5))
        self.assertEqual([(item.repeat, item.max_seconds) for item in result.items], [(3, 120), (None, 1), (65535, None), (None, None), (None, None)])
        self.assertEqual(result.items[0], show.Item(1, "a.odrg", None, None, 3, 120))
        self.assertEqual(result.items[3], show.Item(4, "d.odrg", None, None))
        for repeat, longest in ((1, 1), (65535, 65535)):
            read = show.loads(source(items=[{"id": 1, "file": "a.odrg", "repeat": repeat, "max_seconds": longest}])).items[0]
            self.assertEqual((read.repeat, read.max_seconds), (repeat, longest))

    def test_the_shortest_time_of_an_animation_is_30_seconds_unless_the_show_says_another(self):
        self.assertEqual(show.loads(source()).min_seconds, 30)
        for seconds in (1, 30, 45, 65535):
            self.assertEqual(show.loads(source(min_seconds=seconds)).min_seconds, seconds)

    def test_a_show_without_items(self):
        result = show.loads(source(items=[]))
        self.assertEqual((result.brightness, result.items, result.start), (128, (), None))
        self.assertEqual(show.files(result), [])
        self.assertEqual(show.loads(b'{"version":1,"brightness":0,"items":[]}\n').items, ())
        with self.assertRaises(errors.Rejection) as caught:
            show.loads(source(items=[], start=1))
        self.assertEqual(caught.exception.reason, "undefined-id")

    def test_the_show_file_as_the_player_writes_it_after_a_change(self):
        text = (support.ROOT / "docs" / "show.md").read_text(encoding="utf-8")
        section = text.split("\n## show.json after a change\n")[1].split("\n## ")[0]
        example = re.search(r"```json\n(.*?)```", section, re.DOTALL).group(1)
        # One line without spaces and a line feed, the members in the order of the table.
        self.assertEqual(example.count("\n"), 1)
        self.assertTrue(example.endswith("}\n"))
        self.assertNotIn(" ", example)
        self.assertEqual(example, json.dumps(json.loads(example), separators=(",", ":")) + "\n")
        self.assertEqual(list(json.loads(example)), ["version", "brightness", "min_seconds", "items", "start"])
        self.assertEqual(list(json.loads(example)["items"][0]), ["id", "file", "repeat", "max_seconds"])
        result = show.loads(example.encode())
        self.assertEqual((result.brightness, result.start, result.min_seconds), (128, 4, 45))
        self.assertEqual(result.items, (show.Item(1, "hello.odrg", None, None, 3, 120), show.Item(2, "dvd.odrg", None, None), show.Item(4, None, (2, 1), 15)))
        for written in (
            b'{"version":1,"brightness":0,"items":[]}\n',
            b'{"version":1,"brightness":0,"min_seconds":1,"items":[{"id":1,"file":"a.odrg","max_seconds":65535}]}\n',
            b'{"version":1,"brightness":0,"items":[{"id":1,"file":"a.odrg","repeat":65535}]}\n',
            b'{"version":1,"brightness":255,"items":[{"id":65535,"file":".odrg"}]}\n',
            b'{"version":1,"brightness":7,"items":[{"id":2,"file":"a.odrg"},{"id":1,"cycle":[2,2,2],"seconds":65535}],"start":1}\n',
        ):
            read = show.loads(written)
            self.assertEqual(len(read.items), written.count(b'"id"'))
            self.assertEqual(read.start, 1 if b"start" in written else None)

    def test_the_limits(self):
        items = [
            {"id": 1, "file": ".odrg"},
            {"id": 65535, "file": "a-b_c.9" + "x" * 20 + ".odrg"},
            {"id": 7, "cycle": [1, 65535, 1], "seconds": 1},
            {"id": 8, "cycle": [1], "seconds": 65535},
        ]
        for brightness in (0, 255):
            result = show.loads(source(brightness=brightness, items=items, start=8))
            self.assertEqual(result.brightness, brightness)
        self.assertEqual(len(result.items[1].file), 32)

    def test_files_are_listed_once_in_the_order_of_first_use(self):
        items = [
            {"id": 1, "file": "b.odrg"},
            {"id": 2, "file": "a.odrg"},
            {"id": 3, "cycle": [2, 1], "seconds": 5},
            {"id": 4, "file": "b.odrg"},
        ]
        self.assertEqual(show.files(show.loads(source(items=items))), ["b.odrg", "a.odrg"])


class Malformed(unittest.TestCase):
    def check(self, data, inner=None):
        with self.assertRaises(errors.Rejection) as caught:
            show.loads(data)
        self.assertEqual(caught.exception.reason, "show-malformed", data)
        if inner is not None:
            self.assertIn(inner, caught.exception.detail)

    def test_not_strict_json(self):
        self.check(b"", "bad-json")
        self.check(b"\xef\xbb\xbf" + source(), "bad-json")
        self.check(source() + b"{}", "bad-json")
        self.check(b"[]", "bad-json")
        self.check(b'{"version": 1, "brightness": 1, "brightness": 1, "items": [{"id": 1, "file": "a.odrg"}]}', "bad-json")

    def test_members_other_than_the_listed_ones(self):
        self.check(source(fps=50), "unknown-member")
        self.check(source(version=...), "missing-member")
        self.check(source(brightness=...), "missing-member")
        self.check(source(items=...), "missing-member")

    def test_a_version_other_than_1(self):
        self.check(source(version=2), "bad-version")
        self.check(source(version=2, fps=50), "bad-version")
        self.check(source(version="1"), "bad-type")

    def test_brightness_outside_0_to_255(self):
        self.check(source(brightness=-1), "out-of-range")
        self.check(source(brightness=256), "out-of-range")
        self.check(source(brightness="128"), "bad-type")
        self.check(source().replace(b"128", b"128.0"), "bad-type")

    def test_items_that_are_no_list_of_items(self):
        self.check(source(items={}), "bad-type")
        self.check(source(items=[1]), "bad-type")
        self.check(source(items="[]"), "bad-type")

    def test_an_item_that_is_neither_kind(self):
        self.check(source(items=[{"id": 1}]), "missing-member")
        self.check(source(items=[{"id": 1, "file": "a.odrg", "cycle": [1], "seconds": 5}]), "unknown-member")
        self.check(source(items=[{"id": 1, "file": "a.odrg", "seconds": 5}]), "unknown-member")
        self.check(source(items=[{"id": 1, "file": "a.odrg", "name": "A"}]), "unknown-member")
        self.check(source(items=[{"id": 1, "cycle": [1]}]), "missing-member")
        self.check(source(items=[{"id": 1, "seconds": 5}]), "missing-member")
        self.check(source(items=[{"file": "a.odrg"}]), "missing-member")
        self.check(source(items=[{"cycle": [1], "seconds": 5}]), "missing-member")

    def test_a_repeat_count_or_a_longest_duration_that_is_no_whole_number_from_1_to_65535(self):
        for member in ("repeat", "max_seconds"):
            with self.subTest(member=member):
                for value in (0, -1, 65536):
                    self.check(source(items=[{"id": 1, "file": "a.odrg", member: value}]), "out-of-range")
                for value in ("3", None, True, [3], {"n": 3}):
                    self.check(source(items=[{"id": 1, "file": "a.odrg", member: value}]), "bad-type")
                self.check(source(items=[{"id": 1, "file": "a.odrg", member: 3}]).replace(b": 3}", b": 3.0}"), "bad-type")
                self.check(source(items=[{"id": 1, "file": "a.odrg", member: 3}]).replace(b": 3}", b": 3e0}"), "bad-type")

    def test_a_cycle_has_neither_of_the_two(self):
        for member in ("repeat", "max_seconds"):
            self.check(source(items=[{"id": 1, "file": "a.odrg"}, {"id": 2, "cycle": [1], "seconds": 5, member: 2}]), "unknown-member")

    def test_a_shortest_time_that_is_no_whole_number_from_1_to_65535(self):
        for value in (0, -30, 65536):
            self.check(source(min_seconds=value), "out-of-range")
        for value in ("30", None, False, [30]):
            self.check(source(min_seconds=value), "bad-type")
        self.check(source(min_seconds=30).replace(b'"min_seconds": 30', b'"min_seconds": 30.0'), "bad-type")

    def test_the_two_are_no_members_of_the_show_and_the_shortest_time_none_of_an_item(self):
        self.check(source(repeat=2), "unknown-member")
        self.check(source(max_seconds=2), "unknown-member")
        self.check(source(items=[{"id": 1, "file": "a.odrg", "min_seconds": 30}]), "unknown-member")

    def test_an_id_outside_1_to_65535(self):
        self.check(source(items=[{"id": 0, "file": "a.odrg"}]), "out-of-range")
        self.check(source(items=[{"id": 65536, "file": "a.odrg"}]), "out-of-range")
        self.check(source(items=[{"id": "1", "file": "a.odrg"}]), "bad-type")
        self.check(source(items=[{"id": True, "file": "a.odrg"}]), "bad-type")

    def test_a_file_name_outside_the_naming_rule(self):
        for name in ("a.gif", "a", "A.odrg", "a b.odrg", "sub/a.odrg", "a.odrg ", "a.ODRG", "x" * 28 + ".odrg", "", "é.odrg", "a.odrg\n"):
            with self.subTest(name=name):
                self.check(source(items=[{"id": 1, "file": name}]), "file of item 1")
        self.check(source(items=[{"id": 1, "file": 7}]), "bad-type")

    def test_seconds_outside_1_to_65535(self):
        first = {"id": 1, "file": "a.odrg"}
        self.check(source(items=[first, {"id": 2, "cycle": [1], "seconds": 0}]), "out-of-range")
        self.check(source(items=[first, {"id": 2, "cycle": [1], "seconds": 65536}]), "out-of-range")
        self.check(source(items=[first, {"id": 2, "cycle": [1], "seconds": "15"}]), "bad-type")

    def test_a_cycle_that_is_not_a_list_of_one_or_more_integers(self):
        first = {"id": 1, "file": "a.odrg"}
        self.check(source(items=[first, {"id": 2, "cycle": [], "seconds": 5}]), "cycle of item 2 is empty")
        self.check(source(items=[first, {"id": 2, "cycle": 1, "seconds": 5}]), "bad-type")
        self.check(source(items=[first, {"id": 2, "cycle": ["1"], "seconds": 5}]), "bad-type")
        self.check(source(items=[first, {"id": 2, "cycle": [1, True], "seconds": 5}]), "bad-type")

    def test_a_start_that_is_not_an_integer(self):
        self.check(source(start="1"), "bad-type")
        self.check(source(start=None), "bad-type")
        self.check(source(start=[1]), "bad-type")


class Ids(unittest.TestCase):
    A = {"id": 1, "file": "a.odrg"}
    B = {"id": 2, "file": "b.odrg"}

    def test_duplicate_id(self):
        self.assertEqual(reason_of(source(items=[self.A, {"id": 1, "file": "b.odrg"}])), "duplicate-id")
        self.assertEqual(reason_of(source(items=[self.A, {"id": 1, "cycle": [1], "seconds": 5}])), "duplicate-id")

    def test_undefined_id_in_a_cycle(self):
        self.assertEqual(reason_of(source(items=[self.A, {"id": 2, "cycle": [1, 3], "seconds": 5}])), "undefined-id")
        self.assertEqual(reason_of(source(items=[self.A, {"id": 2, "cycle": [0], "seconds": 5}])), "undefined-id")
        self.assertEqual(reason_of(source(items=[self.A, {"id": 2, "cycle": [70000], "seconds": 5}])), "undefined-id")

    def test_undefined_id_in_start(self):
        self.assertEqual(reason_of(source(items=[self.A], start=2)), "undefined-id")
        self.assertEqual(reason_of(source(items=[self.A], start=0)), "undefined-id")
        self.assertIsNone(reason_of(source(items=[self.A], start=1)))

    def test_nested_cycle(self):
        cycle = {"id": 3, "cycle": [1, 2], "seconds": 5}
        self.assertEqual(reason_of(source(items=[self.A, self.B, cycle, {"id": 4, "cycle": [1, 3], "seconds": 5}])), "nested-cycle")
        self.assertEqual(reason_of(source(items=[self.A, {"id": 2, "cycle": [2], "seconds": 5}])), "nested-cycle")

    def test_a_cycle_may_name_an_item_that_comes_later_and_one_item_twice(self):
        items = [{"id": 3, "cycle": [2, 1, 2], "seconds": 5}, self.A, self.B]
        self.assertIsNone(reason_of(source(items=items, start=3)))

    def test_the_format_is_judged_before_the_ids(self):
        items = [self.A, {"id": 1, "file": "b.gif"}]
        self.assertEqual(reason_of(source(items=items)), "show-malformed")

    def test_a_duplicate_id_is_reported_before_an_undefined_one(self):
        items = [{"id": 5, "cycle": [9], "seconds": 5}, self.A, {"id": 1, "file": "b.odrg"}]
        self.assertEqual(reason_of(source(items=items, start=8)), "duplicate-id")

    def test_an_undefined_id_is_reported_before_a_nested_cycle(self):
        first = {"id": 3, "cycle": [4], "seconds": 5}
        second = {"id": 4, "cycle": [1, 9], "seconds": 5}
        self.assertEqual(reason_of(source(items=[self.A, first, second])), "undefined-id")
        self.assertEqual(reason_of(source(items=[self.A, first, {"id": 4, "cycle": [1], "seconds": 5}], start=9)), "undefined-id")
        self.assertEqual(reason_of(source(items=[self.A, first, {"id": 4, "cycle": [1], "seconds": 5}])), "nested-cycle")


class ExampleShow(unittest.TestCase):
    def test_the_tracked_example_show(self):
        result = show.read(EXAMPLE_SHOW)
        self.assertEqual(result.brightness, 128)
        self.assertEqual(result.start, 3)
        self.assertEqual(
            result.items,
            (
                show.Item(1, "hello.odrg", None, None),
                show.Item(2, "dvd.odrg", None, None),
                show.Item(3, None, (1, 2), 15),
            ),
        )
        self.assertNotIn(b"\r", EXAMPLE_SHOW.read_bytes())

    def test_a_missing_show_file_is_show_missing(self):
        with self.assertRaises(errors.Rejection) as caught:
            show.read(support.ROOT / "shows" / "example" / "absent.json")
        self.assertEqual(caught.exception.reason, "show-missing")


if __name__ == "__main__":
    unittest.main()

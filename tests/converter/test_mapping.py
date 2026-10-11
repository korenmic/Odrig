import json
import tempfile
import unittest
from pathlib import Path

from odrig import errors, mapping

from . import support


def leg(number=1, pin=1, first_led="right", rows=(1,), **more):
    """One entry of `legs`; `...` leaves a member out."""
    if isinstance(rows, (tuple, range)):
        rows = list(rows)
    entry = {"leg": number, "pin": pin, "first_led": first_led, "rows": rows, **more}
    return {name: value for name, value in entry.items() if value is not ...}


def source(version=1, width=60, legs=None, **more):
    """The bytes of a mapping file; `...` leaves a member out."""
    if legs is None:
        legs = [leg(1, 1, rows=(6, 5, 4)), leg(2, 2, rows=(3, 2, 1))]
    top = {"version": version, "width": width, "legs": legs, **more}
    return json.dumps({name: value for name, value in top.items() if value is not ...}).encode()


class TrackedFiles(unittest.TestCase):
    def test_the_two_leg_mapping_is_60_by_6_with_two_legs(self):
        result = mapping.read(support.ROOT / "mapping" / "legs-2.json")
        self.assertEqual((result.width, result.height), (60, 6))
        self.assertEqual(
            result.legs,
            (mapping.Leg(1, 1, "right", (6, 5, 4)), mapping.Leg(2, 2, "right", (3, 2, 1))),
        )

    def test_the_ten_leg_mapping_is_60_by_30_with_ten_legs(self):
        result = mapping.read(support.ROOT / "mapping" / "legs-10.json")
        self.assertEqual((result.width, result.height), (60, 30))
        self.assertEqual(len(result.legs), 10)
        self.assertEqual([entry.leg for entry in result.legs], list(range(1, 11)))
        self.assertEqual([entry.pin for entry in result.legs], list(range(1, 11)))
        self.assertEqual(result.legs[0].rows, (30, 29, 28))
        self.assertEqual(result.legs[9].rows, (3, 2, 1))
        self.assertEqual({entry.first_led for entry in result.legs}, {"right"})


class Accepted(unittest.TestCase):
    def test_the_height_is_the_total_number_of_rows(self):
        self.assertEqual(mapping.loads(source()).height, 6)
        self.assertEqual(mapping.loads(source(legs=[leg(rows=(1,))])).height, 1)

    def test_legs_may_have_different_numbers_of_rows_and_start_on_the_left(self):
        legs = [leg(7, 0, "left", rows=(1, 2)), leg(3, 255, "right", rows=(6, 5, 4, 3))]
        result = mapping.loads(source(width=5, legs=legs))
        self.assertEqual((result.width, result.height), (5, 6))
        self.assertEqual(result.legs, (mapping.Leg(7, 0, "left", (1, 2)), mapping.Leg(3, 255, "right", (6, 5, 4, 3))))

    def test_the_limits_of_leg_and_pin(self):
        legs = [leg(1, 0, rows=(1,)), leg(255, 255, rows=(2,))]
        self.assertEqual(mapping.loads(source(legs=legs)).height, 2)

    def test_the_largest_canvas(self):
        self.assertEqual(mapping.loads(source(width=65534, legs=[leg(rows=(1,))])).width, 65534)
        self.assertEqual(mapping.loads(source(width=32767, legs=[leg(rows=(1, 2))])).height, 2)
        self.assertEqual(mapping.loads(source(width=1, legs=[leg(rows=range(1, 65535))])).height, 65534)


class Rejected(unittest.TestCase):
    def check(self, data, inner=None):
        with self.assertRaises(errors.Rejection) as caught:
            mapping.loads(data)
        self.assertEqual(caught.exception.reason, "mapping-malformed")
        if inner is not None:
            self.assertIn(inner, caught.exception.detail)

    def test_not_strict_json(self):
        self.check(b"", "bad-json")
        self.check(b"\xef\xbb\xbf" + source(), "bad-json")
        self.check(source() + b"]", "bad-json")
        self.check(b"[]", "bad-json")
        self.check(b'{"version": 1, "width": 60, "width": 60, "legs": []}', "bad-json")
        self.check(source().replace(b'"pin": 2', b'"pin": 2, "pin": 3'), "bad-json")

    def test_a_missing_member(self):
        self.check(source(version=...), "missing-member")
        self.check(source(width=...), "missing-member")
        self.check(source(legs=...), "missing-member")
        for name in ("number", "pin", "first_led", "rows"):
            with self.subTest(name=name):
                self.check(source(legs=[leg(**{name: ...})]), "missing-member")

    def test_an_unknown_member(self):
        self.check(source(height=6), "unknown-member")
        self.check(source(legs=[leg(name="top")]), "unknown-member")

    def test_version_2(self):
        self.check(source(version=2), "bad-version")
        self.check(source(version=2, extra=1), "bad-version")
        self.check(source(version="1"), "bad-type")
        self.check(source().replace(b'"version": 1', b'"version": 1.0'), "bad-type")

    def test_width_0_and_other_widths_out_of_range(self):
        self.check(source(width=0), "out-of-range")
        self.check(source(width=-60), "out-of-range")
        self.check(source(width=65536), "out-of-range")
        self.check(source(width="60"), "bad-type")
        self.check(source(width=True), "bad-type")
        self.check(source().replace(b'"width": 60', b'"width": 60.0'), "bad-type")

    def test_no_legs(self):
        self.check(source(legs=[]), "legs is empty")
        self.check(source(legs={}), "bad-type")
        self.check(source(legs=[7]), "bad-type")

    def test_a_leg_number_out_of_range_or_of_another_type(self):
        self.check(source(legs=[leg(0)]), "out-of-range")
        self.check(source(legs=[leg(256)]), "out-of-range")
        self.check(source(legs=[leg("1")]), "bad-type")

    def test_a_repeated_leg_number(self):
        self.check(source(legs=[leg(1, 1, rows=(1,)), leg(1, 2, rows=(2,))]), "two legs have the number 1")

    def test_a_pin_out_of_range_or_of_another_type(self):
        self.check(source(legs=[leg(pin=-1)]), "out-of-range")
        self.check(source(legs=[leg(pin=256)]), "out-of-range")
        self.check(source(legs=[leg(pin=None)]), "bad-type")

    def test_a_repeated_pin(self):
        self.check(source(legs=[leg(1, 4, rows=(1,)), leg(2, 4, rows=(2,))]), "two legs have the pin 4")

    def test_a_first_led_of_another_word(self):
        self.check(source(legs=[leg(first_led="top")]), "first_led")
        self.check(source(legs=[leg(first_led="Left")]), "first_led")
        self.check(source(legs=[leg(first_led="")]), "first_led")
        self.check(source(legs=[leg(first_led=1)]), "first_led")

    def test_an_empty_rows(self):
        self.check(source(legs=[leg(rows=())]), "rows of leg 1 is empty")
        self.check(source(legs=[leg(1, 1, rows=(1,)), leg(2, 2, rows=())]), "rows of leg 2 is empty")

    def test_rows_that_are_not_an_array_of_integers(self):
        self.check(source(legs=[leg(rows=1)]), "bad-type")
        self.check(source(legs=[leg(rows="1")]), "bad-type")
        self.check(source(legs=[leg(rows={"1": 1})]), "bad-type")
        self.check(source(legs=[leg(rows=("1",))]), "bad-type")
        self.check(source(legs=[leg(rows=(True,))]), "bad-type")
        self.check(source(legs=[leg(rows=(1,))]).replace(b"[1]", b"[1.0]"), "bad-type")

    def test_a_row_listed_twice(self):
        self.check(source(legs=[leg(rows=(1, 1))]), "row 1 is listed twice")
        self.check(source(legs=[leg(1, 1, rows=(2, 1)), leg(2, 2, rows=(3, 2))]), "row 2 is listed twice")

    def test_a_row_missing(self):
        # Three rows in all, so every y from 1 to 3 is needed; 2 is absent.
        self.check(source(legs=[leg(1, 1, rows=(1, 3)), leg(2, 2, rows=(4,))]))
        self.check(source(legs=[leg(rows=(2,))]))

    def test_a_row_above_the_height_or_below_1(self):
        self.check(source(legs=[leg(rows=(1, 2, 4))]), "row 4")
        self.check(source(legs=[leg(rows=(0, 1, 2))]), "row 0")
        self.check(source(legs=[leg(rows=(-1,))]), "row -1")

    def test_a_canvas_above_65534_pixels(self):
        self.check(source(width=65535, legs=[leg(rows=(1,))]), "above 65534")
        self.check(source(width=32768, legs=[leg(rows=(1, 2))]), "above 65534")
        self.check(source(width=256, legs=[leg(rows=range(1, 257))]), "above 65534")


class Files(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def test_a_missing_file_is_mapping_missing(self):
        path = self.folder / "absent.json"
        with self.assertRaises(errors.Rejection) as caught:
            mapping.read(path)
        self.assertEqual(caught.exception.reason, "mapping-missing")
        self.assertIn(str(path), caught.exception.detail)

    def test_a_malformed_file_is_named_with_the_broken_rule(self):
        path = self.folder / "mapping.json"
        path.write_bytes(source(width=0))
        with self.assertRaises(errors.Rejection) as caught:
            mapping.read(path)
        self.assertEqual(caught.exception.reason, "mapping-malformed")
        self.assertIn(str(path), caught.exception.detail)
        self.assertIn("out-of-range", caught.exception.detail)
        self.assertIn("width", caught.exception.detail)

    def test_a_file_is_read(self):
        path = self.folder / "mapping.json"
        path.write_bytes(source())
        self.assertEqual(mapping.read(path), mapping.loads(source()))


if __name__ == "__main__":
    unittest.main()

import json
import re
import tempfile
import unittest
from pathlib import Path

from odrig import errors, mapping

from . import support


def leg(number=1, pin=1, first_led="right", rows=(1,), **more):
    """One entry of `legs` of a row-leg file; `...` leaves a member out."""
    if isinstance(rows, (tuple, range)):
        rows = list(rows)
    entry = {"leg": number, "pin": pin, "first_led": first_led, "rows": rows, **more}
    return {name: value for name, value in entry.items() if value is not ...}


def source(version=1, width=60, legs=None, **more):
    """The bytes of a row-leg file; `...` leaves a member out."""
    if legs is None:
        legs = [leg(1, 1, rows=(6, 5, 4)), leg(2, 2, rows=(3, 2, 1))]
    top = {"version": version, "width": width, "legs": legs, **more}
    return json.dumps({name: value for name, value in top.items() if value is not ...}).encode()


def column_leg(number=1, pin=1, first_led="bottom", columns=(1,), **more):
    """One entry of `legs` of a column-leg file; `...` leaves a member out."""
    if isinstance(columns, (tuple, range)):
        columns = list(columns)
    entry = {"leg": number, "pin": pin, "first_led": first_led, "columns": columns, **more}
    return {name: value for name, value in entry.items() if value is not ...}


def column_source(version=1, height=60, legs=None, **more):
    """The bytes of a column-leg file; `...` leaves a member out."""
    if legs is None:
        legs = [column_leg(1, 1, columns=(1, 2, 3)), column_leg(2, 2, columns=(4, 5, 6))]
    top = {"version": version, "height": height, "legs": legs, **more}
    return json.dumps({name: value for name, value in top.items() if value is not ...}).encode()


def detail_of(data):
    """The detail with which the reader refuses a file as `mapping-malformed`."""
    try:
        mapping.loads(data)
    except errors.Rejection as rejection:
        if rejection.reason != "mapping-malformed":
            raise AssertionError(f"refused as {rejection.reason}, not as mapping-malformed: {data[:200]!r}") from None
        return rejection.detail
    raise AssertionError(f"accepted: {data[:200]!r}")


class TrackedFiles(unittest.TestCase):
    def test_the_two_leg_mapping_is_60_by_6_with_two_legs(self):
        result = mapping.read(support.ROOT / "mapping" / "legs-2.json")
        self.assertEqual((result.width, result.height), (60, 6))
        self.assertEqual(
            result.legs,
            (mapping.Leg(1, 1, "right", (6, 5, 4)), mapping.Leg(2, 2, "right", (3, 2, 1))),
        )

    def test_the_two_leg_mapping_is_of_the_kind_rows_with_180_leds_on_every_leg(self):
        result = mapping.read(support.ROOT / "mapping" / "legs-2.json")
        self.assertEqual(result.kind, mapping.ROWS)
        self.assertEqual(result.strip_length, 60)
        self.assertEqual({result.led_count(entry) for entry in result.legs}, {180})

    def test_the_two_leg_mapping_has_these_bytes_which_are_the_row_leg_file_of_the_mapping_document(self):
        lines = [
            "{",
            '  "version": 1,',
            '  "width": 60,',
            '  "legs": [',
            '    {"leg": 1, "pin": 1, "first_led": "right", "rows": [6, 5, 4]},',
            '    {"leg": 2, "pin": 2, "first_led": "right", "rows": [3, 2, 1]}',
            "  ]",
            "}",
        ]
        held = (support.ROOT / "mapping" / "legs-2.json").read_bytes()
        self.assertEqual(held, ("\n".join(lines) + "\n").encode("ascii"))
        text = (support.ROOT / "docs" / "mapping.md").read_text(encoding="utf-8")
        shown = re.findall(r"```json\n(.*?)```", text.split("\n## Mapping file\n")[1].split("\n### Rules\n")[0], re.DOTALL)
        self.assertEqual(shown[0].encode("ascii"), held)


class TargetFile(unittest.TestCase):
    PINS = (*range(1, 19), 21, 47)

    def setUp(self):
        self.path = support.ROOT / "mapping" / "legs-20.json"
        self.canvas = mapping.read(self.path)

    def test_it_is_a_column_leg_file_of_60_by_60_with_twenty_legs_of_180_leds(self):
        self.assertEqual(self.canvas.kind, mapping.COLUMNS)
        self.assertEqual((self.canvas.width, self.canvas.height), (60, 60))
        self.assertEqual(self.canvas.strip_length, 60)
        self.assertEqual(len(self.canvas.legs), 20)
        self.assertEqual([self.canvas.led_count(entry) for entry in self.canvas.legs], [180] * 20)

    def test_leg_n_has_the_columns_3n_minus_2_to_3n_from_the_bottom_on_the_pins_1_to_18_21_and_47(self):
        self.assertEqual(len(self.PINS), 20)
        self.assertEqual(self.canvas.legs, tuple(mapping.Leg(n, pin, "bottom", (3 * n - 2, 3 * n - 1, 3 * n)) for n, pin in enumerate(self.PINS, start=1)))
        self.assertEqual([entry.leg for entry in self.canvas.legs], list(range(1, 21)))
        self.assertEqual([entry.pin for entry in self.canvas.legs], [*range(1, 19), 21, 47])

    def test_its_corners_are_where_the_requirement_puts_them(self):
        first, last = self.canvas.legs[0], self.canvas.legs[19]
        self.assertEqual([mapping.position(self.canvas, first, n) for n in (1, 60, 61, 120, 121)], [(1, 1), (1, 60), (2, 60), (2, 1), (3, 1)])
        self.assertEqual(mapping.position(self.canvas, last, 180), (60, 60))
        file = json.loads(self.path.read_bytes())
        self.assertEqual([place_by_the_rule(file, file["legs"][0], n) for n in (1, 60, 61, 120, 121)], [(1, 1), (1, 60), (2, 60), (2, 1), (3, 1)])
        self.assertEqual(place_by_the_rule(file, file["legs"][19], 180), (60, 60))

    def test_its_members_are_written_as_the_mapping_document_writes_a_column_leg_file(self):
        lines = ["{", '  "version": 1,', '  "height": 60,', '  "legs": [']
        for n, pin in enumerate(self.PINS, start=1):
            end = "," if n < 20 else ""
            lines.append(f'    {{"leg": {n}, "pin": {pin}, "first_led": "bottom", "columns": [{3 * n - 2}, {3 * n - 1}, {3 * n}]}}{end}')
        lines += ["  ]", "}"]
        self.assertEqual(self.path.read_bytes(), ("\n".join(lines) + "\n").encode("ascii"))


class Accepted(unittest.TestCase):
    def test_the_height_is_the_total_number_of_rows(self):
        self.assertEqual(mapping.loads(source()).height, 6)
        self.assertEqual(mapping.loads(source(legs=[leg(rows=(1,))])).height, 1)

    def test_legs_may_have_different_numbers_of_rows_and_start_on_the_left(self):
        legs = [leg(7, 0, "left", rows=(1, 2)), leg(3, 255, "right", rows=(6, 5, 4, 3))]
        result = mapping.loads(source(width=5, legs=legs))
        self.assertEqual((result.width, result.height), (5, 6))
        self.assertEqual(result.legs, (mapping.Leg(7, 0, "left", (1, 2)), mapping.Leg(3, 255, "right", (6, 5, 4, 3))))

    def test_ten_legs_of_three_rows_of_60_from_the_top_row_down_are_60_by_30(self):
        legs = [leg(n, n, rows=(33 - 3 * n, 32 - 3 * n, 31 - 3 * n)) for n in range(1, 11)]
        result = mapping.loads(source(legs=legs))
        self.assertEqual((result.kind, result.width, result.height), (mapping.ROWS, 60, 30))
        self.assertEqual([entry.leg for entry in result.legs], list(range(1, 11)))
        self.assertEqual([entry.pin for entry in result.legs], list(range(1, 11)))
        self.assertEqual(result.legs[0].strips, (30, 29, 28))
        self.assertEqual(result.legs[9].strips, (3, 2, 1))
        self.assertEqual({entry.first_led for entry in result.legs}, {"right"})
        self.assertEqual({result.led_count(entry) for entry in result.legs}, {180})

    def test_the_limits_of_leg_and_pin(self):
        legs = [leg(1, 0, rows=(1,)), leg(255, 255, rows=(2,))]
        self.assertEqual(mapping.loads(source(legs=legs)).height, 2)

    def test_the_largest_canvas(self):
        self.assertEqual(mapping.loads(source(width=65534, legs=[leg(rows=(1,))])).width, 65534)
        self.assertEqual(mapping.loads(source(width=32767, legs=[leg(rows=(1, 2))])).height, 2)
        self.assertEqual(mapping.loads(source(width=1, legs=[leg(rows=range(1, 65535))])).height, 65534)

    def test_a_row_leg_file_gives_its_kind_its_strip_length_and_the_leds_of_each_leg(self):
        legs = [leg(7, 0, "left", rows=(1, 2)), leg(3, 255, "right", rows=(6, 5, 4, 3))]
        result = mapping.loads(source(width=5, legs=legs))
        self.assertEqual(result.kind, "rows")
        self.assertEqual(result.kind, mapping.ROWS)
        self.assertEqual(result.strip_length, 5)
        self.assertEqual([result.led_count(entry) for entry in result.legs], [10, 20])


class AcceptedColumns(unittest.TestCase):
    def test_the_height_is_the_member_and_the_width_is_the_total_number_of_columns(self):
        result = mapping.loads(column_source())
        self.assertEqual((result.width, result.height), (6, 60))
        result = mapping.loads(column_source(height=9, legs=[column_leg(columns=(1,))]))
        self.assertEqual((result.width, result.height), (1, 9))
        result = mapping.loads(column_source(height=2, legs=[column_leg(columns=(4, 1, 3, 2, 5))]))
        self.assertEqual((result.width, result.height), (5, 2))

    def test_the_reader_gives_the_kind_the_canvas_and_every_leg_in_file_order(self):
        legs = [column_leg(7, 0, "top", columns=(1, 2)), column_leg(3, 255, "bottom", columns=(6, 5, 4, 3))]
        result = mapping.loads(column_source(height=5, legs=legs))
        self.assertEqual(result.kind, "columns")
        self.assertEqual(result.kind, mapping.COLUMNS)
        self.assertEqual((result.width, result.height), (6, 5))
        self.assertEqual(result.legs, (mapping.Leg(7, 0, "top", (1, 2)), mapping.Leg(3, 255, "bottom", (6, 5, 4, 3))))
        self.assertEqual([(entry.leg, entry.pin, entry.first_led, entry.strips) for entry in result.legs],
                         [(7, 0, "top", (1, 2)), (3, 255, "bottom", (6, 5, 4, 3))])
        self.assertEqual(result.strip_length, 5)
        self.assertEqual([result.led_count(entry) for entry in result.legs], [10, 20])

    def test_the_two_examples_of_the_mapping_document_are_read_and_the_second_is_6_by_60(self):
        text = (support.ROOT / "docs" / "mapping.md").read_text(encoding="utf-8")
        section = text.split("\n## Mapping file\n")[1].split("\n### Rules\n")[0]
        row_legs, column_legs = re.findall(r"```json\n(.*?)```", section, re.DOTALL)
        self.assertEqual(json.loads(row_legs), json.loads(source()))
        self.assertEqual(json.loads(column_legs), json.loads(column_source()))
        self.assertEqual(mapping.loads(row_legs.encode()), mapping.loads(source()))
        result = mapping.loads(column_legs.encode())
        self.assertEqual((result.kind, result.width, result.height), (mapping.COLUMNS, 6, 60))
        self.assertEqual(result.legs, (mapping.Leg(1, 1, "bottom", (1, 2, 3)), mapping.Leg(2, 2, "bottom", (4, 5, 6))))
        self.assertEqual([result.led_count(entry) for entry in result.legs], [180, 180])

    def test_the_limits_of_leg_and_pin(self):
        legs = [column_leg(1, 0, columns=(1,)), column_leg(255, 255, columns=(2,))]
        self.assertEqual(mapping.loads(column_source(legs=legs)).width, 2)

    def test_255_legs(self):
        legs = [column_leg(255 - n, n, "top" if n % 2 else "bottom", columns=(n + 1,)) for n in range(255)]
        result = mapping.loads(column_source(height=2, legs=legs))
        self.assertEqual((result.width, result.height), (255, 2))
        self.assertEqual(len(result.legs), 255)
        self.assertEqual([entry.leg for entry in result.legs], list(range(255, 0, -1)))
        self.assertEqual([entry.pin for entry in result.legs], list(range(255)))
        self.assertEqual({result.led_count(entry) for entry in result.legs}, {2})

    def test_a_canvas_of_65534_pixels(self):
        result = mapping.loads(column_source(height=65534, legs=[column_leg(columns=(1,))]))
        self.assertEqual((result.width, result.height), (1, 65534))
        result = mapping.loads(column_source(height=32767, legs=[column_leg(columns=(1, 2))]))
        self.assertEqual((result.width, result.height), (2, 32767))
        result = mapping.loads(column_source(height=1, legs=[column_leg(columns=range(1, 65535))]))
        self.assertEqual((result.width, result.height), (65534, 1))

    def test_the_members_may_come_in_any_order_with_columns_before_first_led(self):
        text = b'{"legs": [{"columns": [2, 1], "pin": 3, "leg": 9, "first_led": "top"}], "height": 3, "version": 1}'
        result = mapping.loads(text)
        self.assertEqual(result.kind, mapping.COLUMNS)
        self.assertEqual((result.width, result.height), (2, 3))
        self.assertEqual(result.legs, (mapping.Leg(9, 3, "top", (2, 1)),))


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
        self.check(source(legs=...), "missing-member")
        for name in ("number", "pin", "first_led", "rows"):
            with self.subTest(name=name):
                self.check(source(legs=[leg(**{name: ...})]), "missing-member")

    def test_an_unknown_member(self):
        self.check(source(depth=6), "unknown-member")
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


class RejectedColumns(unittest.TestCase):
    """Every rule of docs/mapping.md broken in a column-leg file, with the detail the reader
    gives."""

    def refused(self, data, detail):
        self.assertEqual(detail_of(data), detail)

    def test_rule_1_not_strict_json(self):
        self.assertTrue(detail_of(b"").startswith("bad-json: "))
        self.assertTrue(detail_of(column_source() + b"]").startswith("bad-json: "))
        self.refused(b"\xef\xbb\xbf" + column_source(), "bad-json: starts with a byte-order mark")
        self.refused(b'{"version": 1, "height": 60, "height": 60, "legs": []}', 'bad-json: member "height" appears twice in one object')
        self.refused(column_source().replace(b'"pin": 2', b'"pin": 2, "pin": 3'), 'bad-json: member "pin" appears twice in one object')
        self.refused(column_source().replace(b'"height": 60', b'"height": 60.0'), "bad-type: height is not an integer")
        self.refused(column_source().replace(b'"height": 60', b'"height": 6e1'), "bad-type: height is not an integer")
        self.refused(column_source(legs=[column_leg(columns=(1,))]).replace(b"[1]", b"[1.0]"), "bad-type: a column of leg 1 is not an integer")

    def test_rule_2_the_top_level_and_the_version(self):
        self.refused(b"[]", "bad-json: the top level is not an object")
        self.refused(b"60", "bad-json: the top level is not an object")
        self.refused(column_source(version=...), 'missing-member: the file has no member "version"')
        self.refused(column_source(version=2), "bad-version: version is 2, not 1")
        self.refused(column_source(version=0), "bad-version: version is 0, not 1")
        self.refused(column_source(version="1"), "bad-type: version is not an integer")
        self.refused(column_source().replace(b'"version": 1', b'"version": 1.0'), "bad-type: version is not an integer")

    def test_rule_3_legs_is_an_array_of_one_or_more_objects(self):
        self.refused(column_source(legs={}), "bad-type: legs is not an array")
        self.refused(column_source(legs=[]), "legs is empty")
        self.refused(column_source(legs=[7]), "bad-type: entry 1 of legs is not an object")
        self.refused(column_source(legs=[column_leg(), [1]]), "bad-type: entry 2 of legs is not an object")

    def test_rule_3_a_leg_number_from_1_to_255_that_no_other_leg_has(self):
        self.refused(column_source(legs=[column_leg(0)]), "out-of-range: leg of entry 1 of legs is below 1")
        self.refused(column_source(legs=[column_leg(256)]), "out-of-range: leg of entry 1 of legs is above 255")
        self.refused(column_source(legs=[column_leg("1")]), "bad-type: leg of entry 1 of legs is not an integer")
        self.refused(column_source(legs=[column_leg(1, 1, columns=(1,)), column_leg(1, 2, columns=(2,))]), "two legs have the number 1")
        legs = [column_leg(1 + n % 255, n % 256, columns=(n + 1,)) for n in range(256)]
        self.refused(column_source(height=1, legs=legs), "two legs have the number 1")

    def test_rule_3_a_pin_from_0_to_255_that_no_other_leg_has(self):
        self.refused(column_source(legs=[column_leg(pin=-1)]), "out-of-range: pin of leg 1 is below 0")
        self.refused(column_source(legs=[column_leg(pin=256)]), "out-of-range: pin of leg 1 is above 255")
        self.refused(column_source(legs=[column_leg(pin=None)]), "bad-type: pin of leg 1 is not an integer")
        self.refused(column_source(legs=[column_leg(pin=True)]), "bad-type: pin of leg 1 is not an integer")
        self.refused(column_source(legs=[column_leg(1, 4, columns=(1,)), column_leg(2, 4, columns=(2,))]), "two legs have the pin 4")

    def test_rule_4_a_canvas_above_65534_pixels(self):
        self.refused(column_source(height=65535, legs=[column_leg(columns=(1,))]), "the canvas of 1 x 65535 has 65535 pixels, above 65534")
        self.refused(column_source(height=32768, legs=[column_leg(columns=(1, 2))]), "the canvas of 2 x 32768 has 65536 pixels, above 65534")
        self.refused(column_source(height=256, legs=[column_leg(columns=range(1, 257))]), "the canvas of 256 x 256 has 65536 pixels, above 65534")
        self.refused(source(width=32768, legs=[leg(rows=(1, 2))]), "the canvas of 32768 x 2 has 65536 pixels, above 65534")

    def test_rule_5_the_members_of_the_top_level(self):
        self.refused(column_source(legs=...), 'missing-member: the file has no member "legs"')
        self.refused(column_source(name="west"), 'unknown-member: the file has the unknown member "name"')
        self.refused(column_source(columns=[1]), 'unknown-member: the file has the unknown member "columns"')

    def test_rule_5_a_height_from_1_to_65535(self):
        self.refused(column_source(height=0), "out-of-range: height is below 1")
        self.refused(column_source(height=-60), "out-of-range: height is below 1")
        self.refused(column_source(height=65536), "out-of-range: height is above 65535")
        self.refused(column_source(height="60"), "bad-type: height is not an integer")
        self.refused(column_source(height=True), "bad-type: height is not an integer")
        self.refused(column_source(height=None), "bad-type: height is not an integer")

    def test_rule_6_the_members_of_a_leg(self):
        for name, member in (("number", "leg"), ("pin", "pin"), ("first_led", "first_led"), ("columns", "columns")):
            with self.subTest(member=member):
                self.refused(column_source(legs=[column_leg(**{name: ...})]), f'missing-member: entry 1 of legs has no member "{member}"')
        self.refused(column_source(legs=[column_leg(name="east")]), 'unknown-member: entry 1 of legs has the unknown member "name"')
        legs = [column_leg(1, 1, columns=(1,)), column_leg(2, 2, columns=(2,), height=60)]
        self.refused(column_source(legs=legs), 'unknown-member: entry 2 of legs has the unknown member "height"')

    def test_rule_6_a_first_led_of_bottom_or_top(self):
        for word in ("up", "Bottom", "TOP", "", " top", 1, None, ["top"]):
            with self.subTest(first_led=word):
                self.refused(column_source(legs=[column_leg(first_led=word)]), 'first_led of leg 1 is not "bottom" or "top"')
        legs = [column_leg(4, 1, "top", columns=(1,)), column_leg(9, 2, "down", columns=(2,))]
        self.refused(column_source(legs=legs), 'first_led of leg 9 is not "bottom" or "top"')

    def test_rule_7_columns_is_an_array_of_one_or_more_integers(self):
        self.refused(column_source(legs=[column_leg(columns=())]), "columns of leg 1 is empty")
        self.refused(column_source(legs=[column_leg(1, 1, columns=(1,)), column_leg(2, 2, columns=())]), "columns of leg 2 is empty")
        self.refused(column_source(legs=[column_leg(columns=1)]), "bad-type: columns of leg 1 is not an array")
        self.refused(column_source(legs=[column_leg(columns="1")]), "bad-type: columns of leg 1 is not an array")
        self.refused(column_source(legs=[column_leg(columns={"1": 1})]), "bad-type: columns of leg 1 is not an array")
        self.refused(column_source(legs=[column_leg(columns=("1",))]), "bad-type: a column of leg 1 is not an integer")
        self.refused(column_source(legs=[column_leg(columns=(True,))]), "bad-type: a column of leg 1 is not an integer")
        self.refused(column_source(legs=[column_leg(columns=(1, [2]))]), "bad-type: a column of leg 1 is not an integer")

    def test_rule_8_every_column_from_1_to_the_total_exactly_once(self):
        self.refused(column_source(legs=[column_leg(columns=(1, 1))]), "column 1 is listed twice")
        self.refused(column_source(legs=[column_leg(1, 1, columns=(2, 1)), column_leg(2, 2, columns=(3, 2))]), "column 2 is listed twice")
        # Three columns in all, so every x from 1 to 3 is needed; 2 is absent.
        self.refused(column_source(legs=[column_leg(1, 1, columns=(1, 3)), column_leg(2, 2, columns=(4,))]),
                     "column 4 of leg 2 is not from 1 to 3, the number of columns")
        self.refused(column_source(legs=[column_leg(columns=(2,))]), "column 2 of leg 1 is not from 1 to 1, the number of columns")
        self.refused(column_source(legs=[column_leg(columns=(1, 2, 4))]), "column 4 of leg 1 is not from 1 to 3, the number of columns")
        self.refused(column_source(legs=[column_leg(columns=(0, 1, 2))]), "column 0 of leg 1 is not from 1 to 3, the number of columns")
        self.refused(column_source(legs=[column_leg(columns=(-1,))]), "column -1 of leg 1 is not from 1 to 1, the number of columns")

    def test_the_details_of_a_row_leg_file_are_these_with_the_words_of_rows(self):
        self.refused(source(width=0), "out-of-range: width is below 1")
        self.refused(source(width=65536), "out-of-range: width is above 65535")
        self.refused(source(width="60"), "bad-type: width is not an integer")
        self.refused(source(legs=[leg(rows=...)]), 'missing-member: entry 1 of legs has no member "rows"')
        self.refused(source(legs=[leg(first_led="up")]), 'first_led of leg 1 is not "left" or "right"')
        self.refused(source(legs=[leg(rows=())]), "rows of leg 1 is empty")
        self.refused(source(legs=[leg(rows=1)]), "bad-type: rows of leg 1 is not an array")
        self.refused(source(legs=[leg(rows=("1",))]), "bad-type: a row of leg 1 is not an integer")
        self.refused(source(legs=[leg(rows=(1, 1))]), "row 1 is listed twice")
        self.refused(source(legs=[leg(rows=(1, 2, 4))]), "row 4 of leg 1 is not from 1 to 3, the number of rows")


class Kinds(unittest.TestCase):
    """A file is of one kind: what tells the kind, and members and values of the other kind."""

    def refused(self, data, detail):
        self.assertEqual(detail_of(data), detail)

    def test_both_width_and_height(self):
        self.refused(source(height=6), 'the file has both "width" and "height"')
        self.refused(column_source(width=6), 'the file has both "width" and "height"')
        self.refused(b'{"version": 1, "height": 60, "width": 60, "legs": [{"leg": 1, "pin": 1, "first_led": "bottom", "columns": [1]}]}',
                     'the file has both "width" and "height"')
        self.refused(source(height=None), 'the file has both "width" and "height"')

    def test_neither_width_nor_height(self):
        self.refused(source(width=...), 'the file has neither "width" nor "height"')
        self.refused(column_source(height=...), 'the file has neither "width" nor "height"')
        self.refused(b'{"version": 1}', 'the file has neither "width" nor "height"')
        self.refused(column_source(height=..., Height=60), 'the file has neither "width" nor "height"')

    def test_rows_in_a_column_leg_file(self):
        self.refused(column_source(legs=[column_leg(columns=..., rows=[1])]), 'missing-member: entry 1 of legs has no member "columns"')
        self.refused(column_source(legs=[leg(1, 1, "bottom", rows=(1,))]), 'missing-member: entry 1 of legs has no member "columns"')
        legs = [column_leg(1, 1, columns=(1,)), leg(2, 2, rows=(2,))]
        self.refused(column_source(legs=legs), 'missing-member: entry 2 of legs has no member "columns"')

    def test_columns_in_a_row_leg_file(self):
        self.refused(source(legs=[leg(rows=..., columns=[1])]), 'missing-member: entry 1 of legs has no member "rows"')
        self.refused(source(legs=[column_leg(1, 1, "left", columns=(1,))]), 'missing-member: entry 1 of legs has no member "rows"')
        legs = [leg(1, 1, rows=(1,)), column_leg(2, 2, columns=(2,))]
        self.refused(source(legs=legs), 'missing-member: entry 2 of legs has no member "rows"')

    def test_a_leg_with_both_rows_and_columns(self):
        self.refused(column_source(legs=[column_leg(rows=[1])]), 'unknown-member: entry 1 of legs has the unknown member "rows"')
        self.refused(source(legs=[leg(columns=[1])]), 'unknown-member: entry 1 of legs has the unknown member "columns"')

    def test_a_leg_with_neither_rows_nor_columns(self):
        self.refused(column_source(legs=[column_leg(columns=...)]), 'missing-member: entry 1 of legs has no member "columns"')
        self.refused(source(legs=[leg(rows=...)]), 'missing-member: entry 1 of legs has no member "rows"')

    def test_left_or_right_in_a_column_leg_file(self):
        self.refused(column_source(legs=[column_leg(first_led="left")]), 'first_led of leg 1 is not "bottom" or "top"')
        self.refused(column_source(legs=[column_leg(first_led="right")]), 'first_led of leg 1 is not "bottom" or "top"')

    def test_bottom_or_top_in_a_row_leg_file(self):
        self.refused(source(legs=[leg(first_led="bottom")]), 'first_led of leg 1 is not "left" or "right"')
        self.refused(source(legs=[leg(first_led="top")]), 'first_led of leg 1 is not "left" or "right"')


class Order(unittest.TestCase):
    """Files that break two rules: the check that comes first gives the detail."""

    def refused(self, data, detail):
        self.assertEqual(detail_of(data), detail)

    def test_the_version_is_judged_before_the_kind(self):
        self.refused(column_source(version=2, width=60), "bad-version: version is 2, not 1")
        self.refused(column_source(version=..., width=60), 'missing-member: the file has no member "version"')
        self.refused(column_source(version="1", height=...), "bad-type: version is not an integer")

    def test_the_kind_is_judged_before_the_members_of_the_top_level(self):
        self.refused(column_source(width=60, legs=..., name="west"), 'the file has both "width" and "height"')
        self.refused(column_source(width=0, height=0), 'the file has both "width" and "height"')
        self.refused(column_source(height=..., legs=..., name="west"), 'the file has neither "width" nor "height"')

    def test_a_missing_member_is_reported_before_an_unknown_one(self):
        self.refused(column_source(legs=..., name="west"), 'missing-member: the file has no member "legs"')
        legs = [column_leg(columns=..., rows=[1], name="east")]
        self.refused(column_source(legs=legs), 'missing-member: entry 1 of legs has no member "columns"')

    def test_the_members_are_judged_before_the_strip_length_and_that_before_the_legs(self):
        self.refused(column_source(height=0, name="west"), 'unknown-member: the file has the unknown member "name"')
        self.refused(column_source(height=0, legs=[]), "out-of-range: height is below 1")
        self.refused(column_source(height="60", legs={}), "bad-type: height is not an integer")

    def test_inside_a_leg_the_checks_run_in_the_order_of_the_document(self):
        self.refused(column_source(legs=[column_leg(0, pin=...)]), 'missing-member: entry 1 of legs has no member "pin"')
        self.refused(column_source(legs=[column_leg(0, 256, "left", columns=())]), "out-of-range: leg of entry 1 of legs is below 1")
        legs = [column_leg(1, 1, columns=(1,)), column_leg(1, 256, "left", columns=())]
        self.refused(column_source(legs=legs), "two legs have the number 1")
        legs = [column_leg(1, 1, columns=(1,)), column_leg(2, 256, "left", columns=())]
        self.refused(column_source(legs=legs), "out-of-range: pin of leg 2 is above 255")
        legs = [column_leg(1, 4, columns=(1,)), column_leg(2, 4, "left", columns=())]
        self.refused(column_source(legs=legs), "two legs have the pin 4")
        legs = [column_leg(1, 4, columns=(1,)), column_leg(2, 5, "left", columns=())]
        self.refused(column_source(legs=legs), 'first_led of leg 2 is not "bottom" or "top"')
        legs = [column_leg(1, 4, columns=(1,)), column_leg(2, 5, "top", columns=7)]
        self.refused(column_source(legs=legs), "bad-type: columns of leg 2 is not an array")

    def test_the_legs_are_judged_in_file_order(self):
        legs = [column_leg(1, 1, columns="x"), 7]
        self.refused(column_source(legs=legs), "bad-type: columns of leg 1 is not an array")
        legs = [column_leg(8, 1, "left", columns=(1,)), column_leg(9, 2, "right", columns=(2,))]
        self.refused(column_source(legs=legs), 'first_led of leg 8 is not "bottom" or "top"')

    def test_every_leg_is_judged_before_the_place_of_any_column(self):
        legs = [column_leg(1, 1, columns=(9,)), column_leg(2, "x", columns=(1,))]
        self.refused(column_source(legs=legs), "bad-type: pin of leg 2 is not an integer")
        legs = [column_leg(1, 1, columns=(1, 1)), column_leg(2, 2, columns=())]
        self.refused(column_source(legs=legs), "columns of leg 2 is empty")

    def test_the_columns_are_judged_in_file_order_each_for_its_range_and_then_for_a_repeat(self):
        self.refused(column_source(legs=[column_leg(columns=(1, 1, 9))]), "column 1 is listed twice")
        self.refused(column_source(legs=[column_leg(columns=(9, 1, 1))]), "column 9 of leg 1 is not from 1 to 3, the number of columns")
        legs = [column_leg(1, 1, columns=(2, 2)), column_leg(2, 2, columns=(0,))]
        self.refused(column_source(legs=legs), "column 2 is listed twice")

    def test_the_columns_are_judged_before_the_size_of_the_canvas(self):
        self.refused(column_source(height=65535, legs=[column_leg(columns=(2,))]), "column 2 of leg 1 is not from 1 to 1, the number of columns")
        self.refused(column_source(height=65535, legs=[column_leg(columns=(1,))]), "the canvas of 1 x 65535 has 65535 pixels, above 65534")


def place_by_the_rule(file, entry, n):
    """Where LED `n` of a leg is: the rule of docs/mapping.md, "Where each LED is", written
    out here on the members of the file as JSON gives them."""
    if "width" in file:
        w = file["width"]
        r = (n - 1) // w
        i = (n - 1) % w
        y = entry["rows"][r]
        starts_on_the_first_led_side = r % 2 == 0
        starts_right = (entry["first_led"] == "right") == starts_on_the_first_led_side
        x = w - i if starts_right else 1 + i
    else:
        h = file["height"]
        s = (n - 1) // h
        i = (n - 1) % h
        x = entry["columns"][s]
        starts_at_the_first_led_end = s % 2 == 0
        starts_at_the_bottom = (entry["first_led"] == "bottom") == starts_at_the_first_led_end
        y = 1 + i if starts_at_the_bottom else h - i
    return x, y


ROW_LEG_FILES = {
    "legs-2": (support.ROOT / "mapping" / "legs-2.json").read_bytes(),
    "one leg that starts on the left": source(width=7, legs=[leg(1, 1, "left", rows=(3, 2, 1))]),
    "two and four rows": source(width=5, legs=[leg(1, 4, "right", rows=(6, 5)), leg(2, 5, "left", rows=(1, 2, 3, 4))]),
    "rows apart": source(width=4, legs=[leg(1, 1, "right", rows=(2, 4)), leg(2, 2, "left", rows=(1, 5, 3))]),
    "one LED": source(width=1, legs=[leg(1, 1, "left", rows=(1,))]),
}

COLUMN_LEG_FILES = {
    "legs-20": (support.ROOT / "mapping" / "legs-20.json").read_bytes(),
    "two legs of three columns of 60": column_source(),
    "one leg that starts at the top": column_source(height=7, legs=[column_leg(1, 1, "top", columns=(1, 2, 3))]),
    "two and four columns": column_source(height=5, legs=[column_leg(1, 4, "bottom", columns=(1, 2)), column_leg(2, 5, "top", columns=(6, 5, 4, 3))]),
    "columns apart": column_source(height=4, legs=[column_leg(1, 1, "bottom", columns=(2, 4)), column_leg(2, 2, "top", columns=(1, 5, 3))]),
    "one LED": column_source(height=1, legs=[column_leg(1, 1, "top", columns=(1,))]),
}


class Positions(unittest.TestCase):
    def every_led(self, files, strips_name, length_name):
        for name, data in files.items():
            with self.subTest(file=name):
                file = json.loads(data)
                canvas = mapping.loads(data)
                self.assertEqual(len(canvas.legs), len(file["legs"]))
                seen = []
                for entry, listed in zip(file["legs"], canvas.legs):
                    count = file[length_name] * len(entry[strips_name])
                    self.assertEqual(canvas.led_count(listed), count)
                    for n in range(1, count + 1):
                        place = mapping.position(canvas, listed, n)
                        if place != place_by_the_rule(file, entry, n):
                            self.fail(f"LED {n} of leg {listed.leg} is put at {place}, and the rule puts it at {place_by_the_rule(file, entry, n)}")
                        seen.append(place)
                # Every pixel of the canvas is the place of exactly one LED.
                everywhere = {(x, y) for x in range(1, canvas.width + 1) for y in range(1, canvas.height + 1)}
                self.assertEqual(len(seen), canvas.width * canvas.height)
                self.assertEqual(set(seen), everywhere)

    def test_every_led_of_a_row_leg_file_is_where_the_rule_puts_it(self):
        self.every_led(ROW_LEG_FILES, "rows", "width")

    def test_every_led_of_a_column_leg_file_is_where_the_rule_puts_it(self):
        self.every_led(COLUMN_LEG_FILES, "columns", "height")

    def test_the_ends_of_the_rows_of_the_two_leg_mapping(self):
        canvas = mapping.loads(ROW_LEG_FILES["legs-2"])
        first, second = canvas.legs
        self.assertEqual([mapping.position(canvas, first, n) for n in (1, 60, 61, 120, 121, 180)],
                         [(60, 6), (1, 6), (1, 5), (60, 5), (60, 4), (1, 4)])
        self.assertEqual([mapping.position(canvas, second, n) for n in (1, 60, 61, 120, 121, 180)],
                         [(60, 3), (1, 3), (1, 2), (60, 2), (60, 1), (1, 1)])

    def test_the_ends_of_the_columns_of_legs_that_start_at_the_bottom(self):
        canvas = mapping.loads(COLUMN_LEG_FILES["two legs of three columns of 60"])
        first, second = canvas.legs
        self.assertEqual([mapping.position(canvas, first, n) for n in (1, 60, 61, 120, 121, 180)],
                         [(1, 1), (1, 60), (2, 60), (2, 1), (3, 1), (3, 60)])
        self.assertEqual([mapping.position(canvas, second, n) for n in (1, 60, 61, 120, 121, 180)],
                         [(4, 1), (4, 60), (5, 60), (5, 1), (6, 1), (6, 60)])

    def test_the_ends_of_the_columns_of_a_leg_that_starts_at_the_top(self):
        canvas = mapping.loads(COLUMN_LEG_FILES["one leg that starts at the top"])
        self.assertEqual([mapping.position(canvas, canvas.legs[0], n) for n in (1, 2, 7, 8, 14, 15, 21)],
                         [(1, 7), (1, 6), (1, 1), (2, 1), (2, 7), (3, 7), (3, 1)])

    def test_a_number_that_no_led_of_the_leg_has_is_refused(self):
        for files in (ROW_LEG_FILES, COLUMN_LEG_FILES):
            for name, data in files.items():
                canvas = mapping.loads(data)
                for listed in canvas.legs:
                    for n in (0, -1, canvas.led_count(listed) + 1):
                        with self.subTest(file=name, leg=listed.leg, n=n), self.assertRaises(ValueError):
                            mapping.position(canvas, listed, n)


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

    def test_a_malformed_column_leg_file_is_named_with_the_broken_rule(self):
        path = self.folder / "mapping.json"
        path.write_bytes(column_source(legs=[column_leg(first_led="left")]))
        with self.assertRaises(errors.Rejection) as caught:
            mapping.read(path)
        self.assertEqual(caught.exception.reason, "mapping-malformed")
        self.assertEqual(caught.exception.detail, f'{path}: first_led of leg 1 is not "bottom" or "top"')

    def test_a_file_is_read(self):
        path = self.folder / "mapping.json"
        path.write_bytes(source())
        self.assertEqual(mapping.read(path), mapping.loads(source()))

    def test_a_column_leg_file_is_read(self):
        path = self.folder / "mapping.json"
        path.write_bytes(column_source())
        self.assertEqual(mapping.read(path), mapping.loads(column_source()))
        self.assertEqual(mapping.read(path).kind, mapping.COLUMNS)
        self.assertNotEqual(mapping.read(path), mapping.loads(source()))


if __name__ == "__main__":
    unittest.main()

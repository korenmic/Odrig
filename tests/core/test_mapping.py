import json
import unittest

from odrig import errors, mapping

from . import support

MAPPING_REASONS = ("mapping-missing", "mapping-malformed")


def one_leg(**changes):
    """A mapping of one leg on a canvas of 60 x 2, with members of the leg changed."""
    leg = {"leg": 1, "pin": 1, "first_led": "right", "rows": [2, 1]}
    leg.update(changes)
    return {"version": 1, "width": 60, "legs": [leg]}


def two_legs(first, second):
    """A mapping of two legs of one row each, with members of each leg changed."""
    legs = [{"leg": 1, "pin": 1, "first_led": "right", "rows": [2]}, {"leg": 2, "pin": 2, "first_led": "right", "rows": [1]}]
    legs[0].update(first)
    legs[1].update(second)
    return {"version": 1, "width": 60, "legs": legs}


def without(value, member):
    return {name: entry for name, entry in value.items() if name != member}


# One mapping for each rule of docs/mapping.md, broken.
BROKEN = {
    "not an object": [1, 60, []],
    "version is missing": without(one_leg(), "version"),
    "width is missing": without(one_leg(), "width"),
    "legs is missing": without(one_leg(), "legs"),
    "a member too many": {**one_leg(), "height": 2},
    "version 2": {**one_leg(), "version": 2},
    "version 0": {**one_leg(), "version": 0},
    "version as text": {**one_leg(), "version": "1"},
    "width 0": {**one_leg(), "width": 0},
    "width 65536": {**one_leg(), "width": 65536},
    "width as text": {**one_leg(), "width": "60"},
    "width null": {**one_leg(), "width": None},
    "legs is an object": {**one_leg(), "legs": {}},
    "legs is empty": {**one_leg(), "legs": []},
    "a leg that is a number": {**one_leg(), "legs": [1]},
    "a leg that is an array": {**one_leg(), "legs": [[]]},
    "a leg without leg": {**one_leg(), "legs": [without(one_leg()["legs"][0], "leg")]},
    "a leg without pin": {**one_leg(), "legs": [without(one_leg()["legs"][0], "pin")]},
    "a leg without first_led": {**one_leg(), "legs": [without(one_leg()["legs"][0], "first_led")]},
    "a leg without rows": {**one_leg(), "legs": [without(one_leg()["legs"][0], "rows")]},
    "a leg with a member too many": one_leg(colour="red"),
    "leg 0": one_leg(leg=0),
    "leg 256": one_leg(leg=256),
    "leg as text": one_leg(leg="1"),
    "two legs with one number": two_legs({}, {"leg": 1}),
    "pin 256": one_leg(pin=256),
    "pin as text": one_leg(pin="1"),
    "pin true": one_leg(pin=True),
    "two legs with one pin": two_legs({}, {"pin": 1}),
    "first_led up": one_leg(first_led="up"),
    "first_led in capitals": one_leg(first_led="RIGHT"),
    "first_led as a number": one_leg(first_led=1),
    "rows is empty": one_leg(rows=[]),
    "rows is a number": one_leg(rows=2),
    "a row as text": one_leg(rows=[2, "1"]),
    "a row that is an array": one_leg(rows=[2, [1]]),
    "row 0": one_leg(rows=[1, 0]),
    "a row above the height": one_leg(rows=[1, 3]),
    "a row twice in one leg": one_leg(rows=[1, 1]),
    "a row twice in two legs": two_legs({"rows": [1]}, {"rows": [1]}),
    "a row left out": two_legs({"rows": [3]}, {"rows": [1]}),
    "a canvas above 65,534 pixels": {"version": 1, "width": 32768, "legs": [{"leg": 1, "pin": 1, "first_led": "left", "rows": [1, 2]}]},
    "a width of 65,535": {"version": 1, "width": 65535, "legs": [{"leg": 1, "pin": 1, "first_led": "left", "rows": [1]}]},
    "256 legs": {"version": 1, "width": 1, "legs": [{"leg": 1 + n % 255, "pin": n % 256, "first_led": "left", "rows": [n + 1]} for n in range(256)]},
}

# Mappings at the edges of the rules.
ALLOWED = {
    "leg 255 and pin 0": one_leg(leg=255, pin=0),
    "pin 255": one_leg(pin=255),
    "a canvas of 65,534 pixels": {"version": 1, "width": 32767, "legs": [{"leg": 1, "pin": 1, "first_led": "left", "rows": [1, 2]}]},
    "a width of 65,534": {"version": 1, "width": 65534, "legs": [{"leg": 1, "pin": 1, "first_led": "right", "rows": [1]}]},
    "255 legs": {"version": 1, "width": 2, "legs": [{"leg": 255 - n, "pin": n, "first_led": "left", "rows": [n + 1]} for n in range(255)]},
    "rows before the side": {"legs": [{"rows": [2, 1], "pin": 3, "leg": 9, "first_led": "left"}], "width": 3, "version": 1},
}


def leg_list(text):
    """The leg list the converter's reader gives: `(leg, pin, LED count)` in file order."""
    canvas = mapping.loads(text.encode("utf-8"))
    return tuple((leg.leg, leg.pin, canvas.width * len(leg.rows)) for leg in canvas.legs)


class LegList(unittest.TestCase):
    def test_every_mapping_gives_its_legs_in_the_order_of_the_file(self):
        texts = support.mapping_texts()
        self.assertGreaterEqual(len(texts), 6)
        runs = support.start_each([{"mapping.json": text} for text in texts.values()])
        for (name, text), run in zip(texts.items(), runs):
            with self.subTest(mapping=name):
                listed = json.loads(text)["legs"]
                width = json.loads(text)["width"]
                self.assertEqual(run.core, "ok")
                self.assertNotIn(run.error, MAPPING_REASONS)
                self.assertEqual(run.legs, tuple((leg["leg"], leg["pin"], width * len(leg["rows"])) for leg in listed))
                self.assertEqual(run.legs, leg_list(text))

    def test_the_two_tracked_mappings_have_legs_of_180_leds_on_the_pins_of_their_numbers(self):
        for name, count in (("legs-2", 2), ("legs-10", 10)):
            run = support.start({"mapping.json": support.mapping_texts()[name]})
            self.assertEqual(run.legs, tuple((number, number, 180) for number in range(1, count + 1)))

    def test_mappings_at_the_edges_of_the_rules_are_accepted(self):
        runs = support.start_each([{"mapping.json": json.dumps(value)} for value in ALLOWED.values()])
        for (name, value), run in zip(ALLOWED.items(), runs):
            with self.subTest(mapping=name):
                self.assertNotIn(run.error, MAPPING_REASONS)
                self.assertEqual(run.legs, leg_list(json.dumps(value)))


class RefusedMappings(unittest.TestCase):
    def test_a_missing_file_gives_mapping_missing_and_no_legs(self):
        run = support.start({}, ["error"])
        self.assertEqual(run.core, "ok")
        self.assertEqual(run.error, "mapping-missing")
        self.assertEqual(run.legs, ())
        self.assertEqual(run.logs, ("mapping-missing",))
        self.assertEqual(run.lines, ["error mapping-missing"])

    def test_a_file_under_another_name_is_not_the_mapping(self):
        run = support.start({"legs-2.json": support.mapping_texts()["legs-2"]})
        self.assertEqual(run.error, "mapping-missing")

    def test_each_broken_rule_gives_mapping_malformed_and_no_legs(self):
        self.assertGreaterEqual(len(BROKEN), 40)
        runs = support.start_each([{"mapping.json": json.dumps(value)} for value in BROKEN.values()], ["error"])
        for (name, value), run in zip(BROKEN.items(), runs):
            with self.subTest(rule=name):
                with self.assertRaises(errors.Rejection) as refused:
                    mapping.loads(json.dumps(value).encode("utf-8"))
                self.assertEqual(refused.exception.reason, "mapping-malformed")
                self.assertEqual(run.core, "ok")
                self.assertEqual(run.error, "mapping-malformed")
                self.assertEqual(run.legs, ())
                self.assertEqual(run.lines, ["error mapping-malformed"])

    def test_a_refused_mapping_asks_for_no_more_memory_than_its_checks_need(self):
        missing = support.start({})
        self.assertEqual(missing.memory[1], 1)
        cut = support.start({"mapping.json": support.mapping_texts()["legs-10"][:-3]})
        self.assertEqual(cut.error, "mapping-malformed")
        self.assertEqual(cut.memory, missing.memory)


if __name__ == "__main__":
    unittest.main()

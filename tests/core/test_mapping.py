import json
import unittest

from odrig import errors, jsonframes, mapping, odrg

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
    "a row leg with starts": {"version": 1, "width": 5, "legs": [{"leg": 1, "pin": 1, "first_led": "left", "rows": [1, 2, 3], "starts": ["left", "left", "right"]}]},
}


def row_leg(leg=1, pin=1, first_led="right", rows=(1,), **more):
    """One entry of `legs` of a row-leg file; `...` leaves a member out."""
    entry = {"leg": leg, "pin": pin, "first_led": first_led, "rows": rows, **more}
    return {name: value for name, value in entry.items() if value is not ...}


def row_file(width=60, legs=None, version=1, **more):
    """A row-leg file, of two legs of three rows unless it is given legs; `...` leaves a
    member out."""
    if legs is None:
        legs = [row_leg(1, 1, rows=(6, 5, 4)), row_leg(2, 2, rows=(3, 2, 1))]
    top = {"version": version, "width": width, "legs": legs, **more}
    return {name: value for name, value in top.items() if value is not ...}


def column_leg(leg=1, pin=1, first_led="bottom", columns=(1,), **more):
    """One entry of `legs` of a column-leg file; `...` leaves a member out."""
    entry = {"leg": leg, "pin": pin, "first_led": first_led, "columns": columns, **more}
    return {name: value for name, value in entry.items() if value is not ...}


def column_file(height=60, legs=None, version=1, **more):
    """A column-leg file, of two legs of three columns unless it is given legs; `...` leaves
    a member out."""
    if legs is None:
        legs = [column_leg(1, 1, columns=(1, 2, 3)), column_leg(2, 2, columns=(4, 5, 6))]
    top = {"version": version, "height": height, "legs": legs, **more}
    return {name: value for name, value in top.items() if value is not ...}


# One column-leg mapping for each rule of docs/mapping.md, broken.
BROKEN_COLUMNS = {
    "version is missing": column_file(version=...),
    "version 2": column_file(version=2),
    "version 0": column_file(version=0),
    "version as text": column_file(version="1"),
    "legs is an object": column_file(legs={}),
    "legs is empty": column_file(legs=[]),
    "a leg that is a number": column_file(legs=[7]),
    "a second leg that is an array": column_file(legs=[column_leg(), [1]]),
    "leg 0": column_file(legs=[column_leg(0)]),
    "leg 256": column_file(legs=[column_leg(256)]),
    "leg as text": column_file(legs=[column_leg("1")]),
    "two legs with one number": column_file(legs=[column_leg(1, 1, columns=(1,)), column_leg(1, 2, columns=(2,))]),
    "256 legs": column_file(height=1, legs=[column_leg(1 + n % 255, n % 256, columns=(n + 1,)) for n in range(256)]),
    "pin -1": column_file(legs=[column_leg(pin=-1)]),
    "pin 256": column_file(legs=[column_leg(pin=256)]),
    "pin null": column_file(legs=[column_leg(pin=None)]),
    "pin true": column_file(legs=[column_leg(pin=True)]),
    "two legs with one pin": column_file(legs=[column_leg(1, 4, columns=(1,)), column_leg(2, 4, columns=(2,))]),
    "a canvas of 1 x 65,535": column_file(height=65535, legs=[column_leg(columns=(1,))]),
    "a canvas of 2 x 32,768": column_file(height=32768, legs=[column_leg(columns=(1, 2))]),
    "a canvas of 256 x 256": column_file(height=256, legs=[column_leg(columns=list(range(1, 257)))]),
    "legs is missing": column_file(legs=...),
    "a member too many": column_file(name="west"),
    "columns at the top level": column_file(columns=[1]),
    "height 0": column_file(height=0),
    "height -60": column_file(height=-60),
    "height 65536": column_file(height=65536),
    "height as text": column_file(height="60"),
    "height true": column_file(height=True),
    "height null": column_file(height=None),
    "a leg without leg": column_file(legs=[column_leg(leg=...)]),
    "a leg without pin": column_file(legs=[column_leg(pin=...)]),
    "a leg without first_led": column_file(legs=[column_leg(first_led=...)]),
    "a leg without columns": column_file(legs=[column_leg(columns=...)]),
    "a leg with a member too many": column_file(legs=[column_leg(name="east")]),
    "a leg with a height": column_file(legs=[column_leg(1, 1, columns=(1,)), column_leg(2, 2, columns=(2,), height=60)]),
    "first_led up": column_file(legs=[column_leg(first_led="up")]),
    "first_led with a capital": column_file(legs=[column_leg(first_led="Bottom")]),
    "first_led in capitals": column_file(legs=[column_leg(first_led="TOP")]),
    "first_led empty": column_file(legs=[column_leg(first_led="")]),
    "first_led after a space": column_file(legs=[column_leg(first_led=" top")]),
    "first_led as a number": column_file(legs=[column_leg(first_led=1)]),
    "first_led null": column_file(legs=[column_leg(first_led=None)]),
    "first_led in an array": column_file(legs=[column_leg(first_led=["top"])]),
    "first_led down in a second leg": column_file(legs=[column_leg(4, 1, "top", columns=(1,)), column_leg(9, 2, "down", columns=(2,))]),
    "columns is empty": column_file(legs=[column_leg(columns=())]),
    "columns of a second leg is empty": column_file(legs=[column_leg(1, 1, columns=(1,)), column_leg(2, 2, columns=())]),
    "columns is a number": column_file(legs=[column_leg(columns=1)]),
    "columns is text": column_file(legs=[column_leg(columns="1")]),
    "columns is an object": column_file(legs=[column_leg(columns={"1": 1})]),
    "a column as text": column_file(legs=[column_leg(columns=("1",))]),
    "a column that is true": column_file(legs=[column_leg(columns=(True,))]),
    "a column that is an array": column_file(legs=[column_leg(columns=(1, [2]))]),
    "a column twice in one leg": column_file(legs=[column_leg(columns=(1, 1))]),
    "a column twice in two legs": column_file(legs=[column_leg(1, 1, columns=(2, 1)), column_leg(2, 2, columns=(3, 2))]),
    "a column left out": column_file(legs=[column_leg(1, 1, columns=(1, 3)), column_leg(2, 2, columns=(4,))]),
    "column 2 of one": column_file(legs=[column_leg(columns=(2,))]),
    "a column above the width": column_file(legs=[column_leg(columns=(1, 2, 4))]),
    "column 0": column_file(legs=[column_leg(columns=(0, 1, 2))]),
    "column -1": column_file(legs=[column_leg(columns=(-1,))]),
    "starts empty": column_file(legs=[column_leg(columns=(1,), starts=[])]),
    "starts shorter than the columns": column_file(legs=[column_leg(columns=(1, 2, 3), starts=["bottom", "top"])]),
    "starts longer than the columns": column_file(legs=[column_leg(columns=(1, 2), starts=["bottom", "top", "bottom"])]),
    "starts whose first is not first_led": column_file(legs=[column_leg(first_led="bottom", columns=(1, 2), starts=["top", "bottom"])]),
    "starts as a word": column_file(legs=[column_leg(columns=(1,), starts="bottom")]),
    "starts with a number": column_file(legs=[column_leg(columns=(1, 2), starts=["bottom", 1])]),
    "starts with up": column_file(legs=[column_leg(columns=(1, 2), starts=["bottom", "up"])]),
    "starts in capitals": column_file(legs=[column_leg(columns=(1, 2), starts=["bottom", "TOP"])]),
}

# Files that are of no kind, of both, or that hold a member or a word of the other kind.
# Each would be valid if the kind were not judged.
MIXED_KINDS = {
    "a column-leg file with a width too": column_file(width=6),
    "a row-leg file with a height too": row_file(height=6),
    "height, then width": {"version": 1, "height": 60, "width": 60, "legs": [column_leg()]},
    "a row-leg file with a height of null": row_file(height=None),
    "a row-leg file without width": row_file(width=...),
    "a column-leg file without height": column_file(height=...),
    "version alone": {"version": 1},
    "Height with a capital": column_file(height=..., Height=60),
    "rows in a leg of a column-leg file": column_file(legs=[column_leg(columns=..., rows=[1])]),
    "a row leg in a column-leg file": column_file(legs=[row_leg(1, 1, rows=(1,))]),
    "a row leg after a column leg": column_file(legs=[column_leg(1, 1, columns=(1,)), row_leg(2, 2, rows=(2,))]),
    "a row leg before a column leg": column_file(legs=[row_leg(1, 1, rows=(1,)), column_leg(2, 2, columns=(2,))]),
    "columns in a leg of a row-leg file": row_file(legs=[row_leg(rows=..., columns=[1])]),
    "a column leg in a row-leg file": row_file(legs=[column_leg(1, 1, columns=(1,))]),
    "a column leg after a row leg": row_file(legs=[row_leg(1, 1, rows=(1,)), column_leg(2, 2, columns=(2,))]),
    "a column leg before a row leg": row_file(legs=[column_leg(1, 1, columns=(1,)), row_leg(2, 2, rows=(2,))]),
    "rows and columns in a leg of a column-leg file": column_file(legs=[column_leg(rows=[1])]),
    "rows and columns in a leg of a row-leg file": row_file(legs=[row_leg(columns=[1])]),
    "neither rows nor columns in a leg of a row-leg file": row_file(legs=[row_leg(rows=...)]),
    "left in a column-leg file": column_file(legs=[column_leg(first_led="left")]),
    "right in a column-leg file": column_file(legs=[column_leg(first_led="right")]),
    "bottom in a row-leg file": row_file(legs=[row_leg(first_led="bottom")]),
    "top in a row-leg file": row_file(legs=[row_leg(first_led="top")]),
    "right in the second leg of a column-leg file": column_file(legs=[column_leg(1, 1, columns=(1,)), column_leg(2, 2, "right", columns=(2,))]),
    "top in the second leg of a row-leg file": row_file(legs=[row_leg(1, 1, rows=(1,)), row_leg(2, 2, "top", rows=(2,))]),
    "starts of rows in a column-leg file": column_file(legs=[column_leg(columns=(1, 2), starts=["left", "right"])]),
    "starts of columns in a row-leg file": row_file(legs=[row_leg(first_led="left", rows=(1, 2), starts=["left", "top"])]),
    "starts of both kinds": column_file(legs=[column_leg(columns=(1, 2), starts=["bottom", "right"])]),
}

# Column-leg files that break two rules.
BROKEN_TWICE = {
    "version 2 and a width too": column_file(version=2, width=60),
    "no version and a width too": column_file(version=..., width=60),
    "version as text and no height": column_file(version="1", height=...),
    "a width too, no legs and a member too many": column_file(width=60, legs=..., name="west"),
    "a width and a height of 0": column_file(width=0, height=0),
    "no height, no legs and a member too many": column_file(height=..., legs=..., name="west"),
    "no legs and a member too many": column_file(legs=..., name="west"),
    "a leg with rows for columns and a member too many": column_file(legs=[column_leg(columns=..., rows=[1], name="east")]),
    "height 0 and a member too many": column_file(height=0, name="west"),
    "height 0 and legs empty": column_file(height=0, legs=[]),
    "height as text and legs an object": column_file(height="60", legs={}),
    "leg 0 without pin": column_file(legs=[column_leg(0, pin=...)]),
    "leg 0, pin 256, left and no column": column_file(legs=[column_leg(0, 256, "left", columns=())]),
    "a leg number twice, pin 256, left and no column": column_file(legs=[column_leg(1, 1, columns=(1,)), column_leg(1, 256, "left", columns=())]),
    "pin 256, left and no column": column_file(legs=[column_leg(1, 1, columns=(1,)), column_leg(2, 256, "left", columns=())]),
    "a pin twice, left and no column": column_file(legs=[column_leg(1, 4, columns=(1,)), column_leg(2, 4, "left", columns=())]),
    "left and no column": column_file(legs=[column_leg(1, 4, columns=(1,)), column_leg(2, 5, "left", columns=())]),
    "columns a number in a second leg": column_file(legs=[column_leg(1, 4, columns=(1,)), column_leg(2, 5, "top", columns=7)]),
    "columns as text and a leg that is a number": column_file(legs=[column_leg(1, 1, columns="x"), 7]),
    "left and right": column_file(legs=[column_leg(8, 1, "left", columns=(1,)), column_leg(9, 2, "right", columns=(2,))]),
    "column 9 and a pin as text": column_file(legs=[column_leg(1, 1, columns=(9,)), column_leg(2, "x", columns=(1,))]),
    "a column twice and columns empty": column_file(legs=[column_leg(1, 1, columns=(1, 1)), column_leg(2, 2, columns=())]),
    "a column twice and column 9": column_file(legs=[column_leg(columns=(1, 1, 9))]),
    "column 9 and a column twice": column_file(legs=[column_leg(columns=(9, 1, 1))]),
    "a column twice and column 0": column_file(legs=[column_leg(1, 1, columns=(2, 2)), column_leg(2, 2, columns=(0,))]),
    "column 2 of one and a canvas above 65,534 pixels": column_file(height=65535, legs=[column_leg(columns=(2,))]),
}

# Column-leg mappings at the edges of the rules.
ALLOWED_COLUMNS = {
    "two legs of three columns of 60": column_file(),
    "one column of 9": column_file(height=9, legs=[column_leg(columns=(1,))]),
    "five columns that are not in order": column_file(height=2, legs=[column_leg(columns=(4, 1, 3, 2, 5))]),
    "legs of two and of four columns": column_file(height=5, legs=[column_leg(7, 0, "top", columns=(1, 2)), column_leg(3, 255, "bottom", columns=(6, 5, 4, 3))]),
    "leg 1 on pin 0 and leg 255 on pin 255": column_file(legs=[column_leg(1, 0, columns=(1,)), column_leg(255, 255, columns=(2,))]),
    "255 legs": column_file(height=2, legs=[column_leg(255 - n, n, "top" if n % 2 else "bottom", columns=(n + 1,)) for n in range(255)]),
    "a canvas of 1 x 65,534": column_file(height=65534, legs=[column_leg(columns=(1,))]),
    "a canvas of 2 x 32,767": column_file(height=32767, legs=[column_leg(columns=(1, 2))]),
    "a canvas of 65,534 x 1": column_file(height=1, legs=[column_leg(columns=list(range(1, 65535)))]),
    "columns before the end": {"legs": [{"columns": [2, 1], "pin": 3, "leg": 9, "first_led": "top"}], "height": 3, "version": 1},
    "a leg with starts": column_file(height=4, legs=[column_leg(columns=(1, 3, 2), starts=["bottom", "bottom", "top"])]),
    "starts that alternate": column_file(height=4, legs=[column_leg(first_led="top", columns=(1, 2, 3), starts=["top", "bottom", "top"])]),
    "starts before columns and first_led": {"legs": [{"starts": ["top", "top"], "columns": [2, 1], "pin": 3, "leg": 9, "first_led": "top"}], "height": 3, "version": 1},
    "a leg with starts and one without": column_file(height=2, legs=[column_leg(1, 1, columns=(1, 2), starts=["bottom", "bottom"]), column_leg(2, 2, "top", columns=(3, 4))]),
}

# What the core lists for each made-up column-leg mapping: `(leg, pin, LED count)`.
LEGS_OF_THE_COLUMN_MAPPINGS = {
    "crossed-columns": ((1, 5, 12), (2, 6, 8)),
    "top-start": ((1, 4, 21),),
    "two-and-four-columns": ((3, 9, 10), (1, 0, 20)),
    "columns-apart": ((7, 12, 8), (2, 3, 12)),
    "one-led-column": ((255, 255, 1),),
}


def leg_list(text):
    """The leg list the converter's reader gives: `(leg, pin, LED count)` in file order."""
    canvas = mapping.loads(text.encode("utf-8"))
    return tuple((leg.leg, leg.pin, canvas.strip_length * len(leg.strips)) for leg in canvas.legs)


class LegList(unittest.TestCase):
    def test_every_mapping_gives_its_legs_in_the_order_of_the_file(self):
        texts = support.mapping_texts()
        self.assertLessEqual({"legs-2", "legs-20", *support.MADE_UP_MAPPINGS, *support.MADE_UP_COLUMN_MAPPINGS}, set(texts))
        self.assertGreaterEqual(len(texts), 10)
        runs = support.start_each([{"mapping.json": text} for text in texts.values()])
        kinds = set()
        for (name, text), run in zip(texts.items(), runs):
            with self.subTest(mapping=name):
                file = json.loads(text)
                listed = file["legs"]
                # A leg has the strip length times the number of its strips: the width
                # times its rows in a row-leg file, the height times its columns in a
                # column-leg file.
                length, strips = ("width", "rows") if "width" in file else ("height", "columns")
                kinds.add(strips)
                self.assertEqual(run.core, "ok")
                self.assertNotIn(run.error, MAPPING_REASONS)
                self.assertEqual(run.legs, tuple((leg["leg"], leg["pin"], file[length] * len(leg[strips])) for leg in listed))
                self.assertEqual(run.legs, leg_list(text))
        self.assertEqual(kinds, {"rows", "columns"})

    def test_the_row_leg_mappings_of_two_and_of_ten_legs_have_legs_of_180_leds_on_the_pins_of_their_numbers(self):
        for name, count in (("legs-2", 2), ("ten-row-legs", 10)):
            run = support.start({"mapping.json": support.mapping_texts()[name]})
            self.assertEqual(run.legs, tuple((number, number, 180) for number in range(1, count + 1)))

    def test_the_target_file_has_twenty_legs_of_180_leds_on_the_pins_1_to_18_21_and_47(self):
        run = support.start({"mapping.json": support.mapping_texts()["legs-20"]})
        self.assertEqual(run.core, "ok")
        self.assertEqual(run.error, "show-missing")
        pins = (*range(1, 19), 21, 47)
        self.assertEqual(len(pins), 20)
        self.assertEqual(run.legs, tuple((number, pin, 180) for number, pin in enumerate(pins, start=1)))

    def target_with(self, clip):
        """A session on the target file with a show of one clip, asked for its reason and
        for one refresh."""
        files = {
            "mapping.json": support.mapping_texts()["legs-20"],
            "show.json": support.show_text([{"id": 1, "file": "clip.odrg"}], 255, 1),
            "clip.odrg": clip,
        }
        return support.start(files, ["error", "poll 0"])

    def test_the_canvas_of_the_target_file_is_60_by_60(self):
        for width, height in ((60, 30), (30, 60), (60, 61), (180, 20), (20, 180)):
            run = self.target_with(support.clip("another size", width, height, (20,)))
            self.assertIsNone(run.error, (width, height))
            self.assertEqual(run.logs, ("file clip.odrg unavailable: size-mismatch",), (width, height))
        run = self.target_with(support.clip("the size", 60, 60, (20,)))
        self.assertIsNone(run.error)
        self.assertEqual(run.lines[:2], ["error none", "refresh 0"])
        self.assertEqual(len(run.lines), 22)

    def test_the_corners_of_the_target_file_are_where_its_requirement_puts_them(self):
        # Pixel (x, y) has the colour (x, y, 200), so an LED tells which pixel it shows.
        picture = b"".join(bytes((x, y, 200)) for y in range(1, 61) for x in range(1, 61))
        run = self.target_with(odrg.encode(jsonframes.Animation(60, 60, ((20, picture),))))
        self.assertEqual(run.lines[:2], ["error none", "refresh 0"])
        legs = {}
        for line in run.lines[2:]:
            word, leg, data = line.split(" ")
            self.assertEqual(word, "data")
            leds = bytes.fromhex(data)
            self.assertEqual(len(leds), 540)
            legs[int(leg)] = [tuple(leds[at:at + 2]) for at in range(0, 540, 3)]
        self.assertEqual(sorted(legs), list(range(1, 21)))
        self.assertEqual([legs[1][n - 1] for n in (1, 60, 61, 120, 121)], [(1, 1), (1, 60), (2, 60), (2, 1), (3, 1)])
        self.assertEqual(legs[20][180 - 1], (60, 60))
        for number, leds in legs.items():
            first = 3 * number - 2
            self.assertEqual([leds[n - 1] for n in (1, 60, 61, 120, 121, 180)],
                             [(first, 1), (first, 60), (first + 1, 60), (first + 1, 1), (first + 2, 1), (first + 2, 60)], number)

    def test_mappings_at_the_edges_of_the_rules_are_accepted(self):
        runs = support.start_each([{"mapping.json": json.dumps(value)} for value in ALLOWED.values()])
        for (name, value), run in zip(ALLOWED.items(), runs):
            with self.subTest(mapping=name):
                self.assertNotIn(run.error, MAPPING_REASONS)
                self.assertEqual(run.legs, leg_list(json.dumps(value)))

    def test_the_made_up_column_leg_mappings_have_these_legs(self):
        texts = support.column_mapping_texts()
        self.assertEqual(sorted(texts), sorted(LEGS_OF_THE_COLUMN_MAPPINGS))
        runs = support.start_each([{"mapping.json": text} for text in texts.values()])
        for name, run in zip(texts, runs):
            with self.subTest(mapping=name):
                self.assertEqual(run.core, "ok")
                self.assertEqual(run.error, "show-missing")
                self.assertEqual(run.legs, LEGS_OF_THE_COLUMN_MAPPINGS[name])

    def test_column_leg_mappings_at_the_edges_of_the_rules_are_accepted(self):
        runs = support.start_each([{"mapping.json": json.dumps(value)} for value in ALLOWED_COLUMNS.values()])
        for (name, value), run in zip(ALLOWED_COLUMNS.items(), runs):
            with self.subTest(mapping=name):
                self.assertEqual(run.core, "ok")
                self.assertNotIn(run.error, MAPPING_REASONS)
                self.assertEqual(run.legs, tuple((leg["leg"], leg["pin"], value["height"] * len(leg["columns"])) for leg in value["legs"]))
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

    def assert_each_refused(self, files):
        """Every one of these files is refused by the converter's reader and by the core,
        which gives the reason name alone and lists no leg."""
        runs = support.start_each([{"mapping.json": json.dumps(value)} for value in files.values()], ["error"])
        for (name, value), run in zip(files.items(), runs):
            with self.subTest(file=name):
                with self.assertRaises(errors.Rejection) as refused:
                    mapping.loads(json.dumps(value).encode("utf-8"))
                self.assertEqual(refused.exception.reason, "mapping-malformed")
                self.assertEqual(run.core, "ok")
                self.assertEqual(run.error, "mapping-malformed")
                self.assertEqual(run.legs, ())
                self.assertEqual(run.logs, ("mapping-malformed",))
                self.assertEqual(run.lines, ["error mapping-malformed"])

    def test_each_rule_broken_in_a_column_leg_file_gives_mapping_malformed_and_no_legs(self):
        self.assertGreaterEqual(len(BROKEN_COLUMNS), 50)
        self.assert_each_refused(BROKEN_COLUMNS)

    def test_a_file_of_no_kind_of_both_or_with_a_part_of_the_other_kind_is_refused(self):
        self.assertGreaterEqual(len(MIXED_KINDS), 20)
        self.assert_each_refused(MIXED_KINDS)

    def test_a_column_leg_file_that_breaks_two_rules_is_refused(self):
        self.assertGreaterEqual(len(BROKEN_TWICE), 20)
        self.assert_each_refused(BROKEN_TWICE)

    def test_a_refused_mapping_asks_for_no_more_memory_than_its_checks_need(self):
        missing = support.start({})
        # The core object, and the line and the reply of the byte entry.
        self.assertEqual(missing.memory[1], 3)
        cut = support.start({"mapping.json": support.mapping_texts()["legs-20"][:-3]})
        self.assertEqual(cut.error, "mapping-malformed")
        self.assertEqual(cut.memory, missing.memory)


class Starts(unittest.TestCase):
    """A leg whose `starts` names the end each strip starts at, as a snake that is chained
    around a dead output is."""

    def leds(self, listed, width, height):
        """The canvas pixel each LED of the one leg of a file shows: pixel (x, y) has the
        colour (x, y, 200)."""
        picture = b"".join(bytes((x, y, 200)) for y in range(1, height + 1) for x in range(1, width + 1))
        files = {
            "mapping.json": json.dumps(listed),
            "show.json": support.show_text([{"id": 1, "file": "clip.odrg"}], 255, 1),
            "clip.odrg": odrg.encode(jsonframes.Animation(width, height, ((20, picture),))),
        }
        run = support.start(files, ["error", "poll 0"])
        self.assertEqual(run.lines[:2], ["error none", "refresh 0"])
        word, leg, data = run.lines[2].split(" ")
        self.assertEqual((word, leg), ("data", "1"))
        leds = bytes.fromhex(data)
        return [tuple(leds[at:at + 2]) for at in range(0, len(leds), 3)]

    def test_each_column_starts_at_the_end_its_word_names(self):
        listed = {"version": 1, "height": 3, "legs": [{"leg": 1, "pin": 1, "first_led": "bottom", "columns": [1, 3, 2], "starts": ["bottom", "bottom", "top"]}]}
        self.assertEqual(self.leds(listed, 3, 3), [(1, 1), (1, 2), (1, 3), (3, 1), (3, 2), (3, 3), (2, 3), (2, 2), (2, 1)])

    def test_each_row_starts_at_the_side_its_word_names(self):
        listed = {"version": 1, "width": 3, "legs": [{"leg": 1, "pin": 1, "first_led": "left", "rows": [1, 2, 3], "starts": ["left", "left", "right"]}]}
        self.assertEqual(self.leds(listed, 3, 3), [(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2), (3, 3), (2, 3), (1, 3)])

    def test_starts_that_alternate_place_the_leds_as_a_leg_without_them(self):
        plain = {"version": 1, "height": 3, "legs": [{"leg": 1, "pin": 1, "first_led": "top", "columns": [2, 1, 3]}]}
        listed = {"version": 1, "height": 3, "legs": [{**plain["legs"][0], "starts": ["top", "bottom", "top"]}]}
        self.assertEqual(self.leds(listed, 3, 3), self.leds(plain, 3, 3))

    def test_a_member_given_twice_is_refused(self):
        text = '{"version": 1, "height": 60, "legs": [{"leg": 1, "pin": 1, "first_led": "bottom", "columns": [1], "starts": ["bottom"], "starts": ["bottom"]}]}'
        run = support.start({"mapping.json": text}, ["error"])
        self.assertEqual(run.error, "mapping-malformed")
        with self.assertRaises(errors.Rejection) as refused:
            mapping.loads(text.encode("utf-8"))
        self.assertEqual(refused.exception.reason, "mapping-malformed")

    def test_a_file_without_starts_asks_for_no_block_more_and_one_with_them_for_one(self):
        plain = support.start({"mapping.json": json.dumps(column_file())})
        crossed = support.start({"mapping.json": json.dumps(column_file(legs=[column_leg(1, 1, columns=(1, 3, 2), starts=["bottom", "bottom", "top"]), column_leg(2, 2, columns=(4, 5, 6))]))})
        self.assertEqual(crossed.memory[1], plain.memory[1] + 1)


class ChangedBetweenTheReadings(unittest.TestCase):
    """The core reads the mapping file twice. The test host gives the second reading
    another file, and stops the run when the core writes outside a block of its memory."""

    def read_twice(self, first, second):
        files = {"mapping.json": json.dumps(first), "second.json": json.dumps(second)}
        run = support.start(files, ["error", "poll 0"], ["--swap-after", "mapping.json", "1", "second.json", "--trace-files"])
        self.assertEqual([opened for opened in run.opened if not opened[0].startswith("catalog")][:2], [("mapping.json", 1), ("mapping.json", 1)])
        self.assertEqual(run.core, "ok")
        return run

    def assert_refused(self, first, second):
        run = self.read_twice(first, second)
        self.assertEqual(run.error, "mapping-malformed")
        self.assertEqual(run.legs, ())
        self.assertEqual(run.lines, ["error mapping-malformed", "idle 0"])

    def test_starts_that_appear_only_at_the_second_reading_are_refused(self):
        first = column_file(height=4, legs=[column_leg(1, 1, columns=(1, 2, 3))])
        second = column_file(height=4, legs=[column_leg(1, 1, columns=(1, 3, 2), starts=["bottom", "bottom", "top"])])
        self.assert_refused(first, second)

    def test_starts_of_more_columns_at_the_second_reading_are_refused(self):
        first = column_file(height=4, legs=[column_leg(1, 1, columns=(1, 2), starts=["bottom", "top"])])
        second = column_file(height=4, legs=[column_leg(1, 1, columns=(1, 2, 3), starts=["bottom", "top", "bottom"])])
        self.assert_refused(first, second)
        second = column_file(height=4, legs=[column_leg(1, 1, starts=["bottom", "top", "bottom"], columns=(1, 2, 3))])
        self.assert_refused(first, second)

    def test_a_file_of_the_other_kind_at_the_second_reading_is_refused(self):
        rows = row_file(width=3, legs=[row_leg(1, 1, "left", rows=(1, 2))])
        columns = column_file(height=3, legs=[column_leg(1, 1, "bottom", columns=(1, 2))])
        self.assert_refused(rows, columns)
        self.assert_refused(columns, rows)
        # The same canvas of 2 x 2, and of 1 x 1, held as rows and as columns.
        self.assert_refused(row_file(width=2, legs=[row_leg(rows=(1, 2))]), column_file(height=2, legs=[column_leg(columns=(1, 2))]))
        self.assert_refused(column_file(height=2, legs=[column_leg(columns=(1, 2))]), row_file(width=2, legs=[row_leg(rows=(1, 2))]))
        self.assert_refused(column_file(height=1, legs=[column_leg()]), row_file(width=1, legs=[row_leg()]))
        self.assert_refused(row_file(width=1, legs=[row_leg()]), column_file(height=1, legs=[column_leg()]))

    def test_a_column_leg_file_of_another_size_at_the_second_reading_is_refused(self):
        first = column_file(height=4, legs=[column_leg(1, 1, columns=(1, 2)), column_leg(2, 2, "top", columns=(3,))])
        others = {
            "a longer strip": column_file(height=5, legs=[column_leg(1, 1, columns=(1, 2)), column_leg(2, 2, "top", columns=(3,))]),
            "a shorter strip": column_file(height=3, legs=[column_leg(1, 1, columns=(1, 2)), column_leg(2, 2, "top", columns=(3,))]),
            "a column more in the first leg": column_file(height=4, legs=[column_leg(1, 1, columns=(1, 2, 4)), column_leg(2, 2, "top", columns=(3,))]),
            "a column more in the last leg": column_file(height=4, legs=[column_leg(1, 1, columns=(1, 2)), column_leg(2, 2, "top", columns=(3, 4))]),
            "a column less": column_file(height=4, legs=[column_leg(1, 1, columns=(1,)), column_leg(2, 2, "top", columns=(2,))]),
            "a leg more": column_file(height=4, legs=[column_leg(1, 1, columns=(1,)), column_leg(2, 2, columns=(2,)), column_leg(3, 3, columns=(3,))]),
            "a leg less": column_file(height=4, legs=[column_leg(1, 1, columns=(1, 2, 3))]),
            "a leg more and its columns": column_file(height=4, legs=[column_leg(1, 1, columns=(1, 2)), column_leg(2, 2, columns=(3,)), column_leg(3, 3, columns=(4, 5))]),
            "the height after legs with a column more": {"version": 1, "legs": [column_leg(1, 1, columns=(1, 2, 3, 4))], "height": 4},
            "65,534 columns of one LED": column_file(height=1, legs=[column_leg(columns=list(range(1, 65535)))]),
            "one column of 65,534": column_file(height=65534, legs=[column_leg()]),
            "255 legs": column_file(height=4, legs=[column_leg(n, n, columns=(n,)) for n in range(1, 256)]),
            "a file that is refused": column_file(height=4, legs=[column_leg(1, 1, columns=(1, 2)), column_leg(2, 1, "top", columns=(3,))]),
        }
        for name, second in others.items():
            with self.subTest(second=name):
                self.assert_refused(first, second)
                if name != "a file that is refused":
                    self.assert_refused(second, first)

    def test_a_column_leg_file_of_the_same_size_at_the_second_reading_gives_its_own_legs(self):
        first = column_file(height=4, legs=[column_leg(1, 1, columns=(1, 2)), column_leg(2, 2, "top", columns=(3,))])
        second = column_file(height=4, legs=[column_leg(8, 5, "top", columns=(3,)), column_leg(9, 6, columns=(2, 1))])
        run = self.read_twice(first, second)
        self.assertEqual(run.error, "show-missing")
        self.assertEqual(run.legs, ((8, 5, 4), (9, 6, 8)))
        self.assertEqual(run.lines, ["error show-missing", "refresh 0", "data 8 " + "00" * 12, "data 9 " + "00" * 24])


if __name__ == "__main__":
    unittest.main()

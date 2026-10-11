import json
import math
import pathlib
import re
import subprocess
import tempfile
import unittest

from odrig import mapping
from tests.core import support as core_support

from . import support

JSC = pathlib.Path("/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc")
WEB = support.ROOT / "emulator" / "web"
SCRIPTS = (WEB / "board.js", WEB / "layout.js", support.ROOT / "tests" / "emulator" / "js" / "dump_layout.js")

# The colours of the first twelve legs of a file.
COLOURS = "#ff6b6b #ffa94d #ffd43b #a9e34b #51cf66 #38d9a9 #3bc9db #4dabf7 #748ffc #b197fc #f783ac #ced4da".split()


def dump(text, **questions):
    """What the page's layout script computes for a mapping file, run in the JavaScript
    shell of macOS without a browser."""
    if not JSC.exists():
        raise AssertionError(f"the JavaScript shell of macOS is not at {JSC}")
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder, "mapping.json")
        path.write_text(text, encoding="utf-8")
        done = subprocess.run([str(JSC), *map(str, SCRIPTS), "--", str(path), json.dumps(questions)], capture_output=True, text=True)
    if done.returncode != 0 or done.stderr:
        raise AssertionError(f"jsc ended with status {done.returncode}:\n{done.stdout[-600:]}\n{done.stderr[-600:]}")
    return json.loads(done.stdout)


def rule(canvas):
    """For each leg of a mapping, the canvas position of LED 1, 2, ... by the rule of
    docs/mapping.md, as the core's suite states it in Python."""
    places = []
    for leg in canvas.legs:
        places.append([[place % canvas.width + 1, place // canvas.width + 1] for place in core_support.led_pixels(canvas, leg)])
    return places


def inside(part, area):
    return area["x"] <= part["x"] and area["y"] <= part["y"] and part["x"] + part["width"] <= area["x"] + area["width"] and part["y"] + part["height"] <= area["y"] + area["height"]


def apart(first, second):
    return (first["x"] + first["width"] <= second["x"] or second["x"] + second["width"] <= first["x"]
            or first["y"] + first["height"] <= second["y"] or second["y"] + second["height"] <= first["y"])


class Positions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = core_support.mapping_texts()
        cls.dumps = {name: dump(text) for name, text in cls.texts.items()}
        cls.canvases = {name: mapping.loads(text.encode("utf-8")) for name, text in cls.texts.items()}

    def test_the_mappings_are_the_tracked_ones_and_made_up_ones(self):
        self.assertLessEqual({"legs-2", "legs-10", "left-start", "two-and-four-rows", "another-order", "one-led"}, set(self.texts))
        apart_rows = [leg.strips for leg in self.canvases["another-order"].legs]
        self.assertEqual(apart_rows, [(2, 4), (1, 5, 3)])

    def test_the_mappings_are_of_both_kinds_with_the_target_file_and_made_up_column_leg_files(self):
        columns = {name for name, canvas in self.canvases.items() if canvas.kind == mapping.COLUMNS}
        self.assertEqual(columns, {"legs-20", "top-start", "two-and-four-columns", "columns-apart", "one-led-column"})
        self.assertGreaterEqual(len(self.canvases) - len(columns), 5)
        self.assertEqual([leg.strips for leg in self.canvases["columns-apart"].legs], [(2, 4), (1, 5, 3)])
        self.assertEqual([(leg.first_led, len(leg.strips)) for leg in self.canvases["two-and-four-columns"].legs], [("bottom", 2), ("top", 4)])
        self.assertEqual((self.canvases["top-start"].legs[0].first_led, self.canvases["top-start"].height), ("top", 7))
        self.assertEqual((self.canvases["one-led-column"].width, self.canvases["one-led-column"].height), (1, 1))

    def test_read_gives_the_kind_the_width_the_height_and_the_legs_of_the_file(self):
        for name, canvas in self.canvases.items():
            with self.subTest(name):
                read = self.dumps[name]["mapping"]
                self.assertEqual(sorted(read), ["height", "kind", "legs", "width"])
                self.assertEqual(read["kind"], "columns" if "height" in json.loads(self.texts[name]) else "rows")
                self.assertEqual(read["kind"], canvas.kind)
                self.assertEqual((read["width"], read["height"]), (canvas.width, canvas.height))
                strip_length = canvas.width if read["kind"] == "rows" else canvas.height
                self.assertEqual([(leg["leg"], leg["pin"], leg["first_led"], tuple(leg["strips"]), leg["count"]) for leg in read["legs"]],
                                 [(leg.leg, leg.pin, leg.first_led, tuple(leg.strips), strip_length * len(leg.strips)) for leg in canvas.legs])
                for leg in read["legs"]:
                    self.assertEqual(sorted(leg), ["count", "first_led", "leg", "pin", "strips"])

    def test_position_of_every_led_is_the_rule_of_the_mapping_document(self):
        for name, canvas in self.canvases.items():
            expected = rule(canvas)
            got = self.dumps[name]["positions"]
            self.assertEqual(len(got), len(expected), name)
            for leg, places, wanted in zip(canvas.legs, got, expected):
                self.assertEqual(len(places), len(wanted), name)
                for n, (place, right) in enumerate(zip(places, wanted), start=1):
                    if place != right:
                        self.fail(f"{name}: LED {n} of leg {leg.leg} is put at {tuple(place)}, and the rule puts it at {tuple(right)}")

    def test_find_is_the_inverse_of_position(self):
        for name, canvas in self.canvases.items():
            with self.subTest(name):
                found = self.dumps[name]["found"]
                seen = set()
                for index, places in enumerate(rule(canvas)):
                    for n, (x, y) in enumerate(places, start=1):
                        self.assertEqual(found[y - 1][x - 1], {"leg": index, "led": n}, (x, y))
                        seen.add((x, y))
                self.assertEqual(len(seen), canvas.width * canvas.height)
                self.assertTrue(all(cell is not None for row in found for cell in row))

    def test_a_place_outside_the_canvas_and_an_led_that_is_not_there_are_null(self):
        asked = dump(self.texts["legs-2"], points=[[0, 1], [61, 1], [1, 0], [1, 7], [1.5, 2], [1, 1]], leds=[[3, 1], [1, 0], [1, 181], [1, 1.5], [2, 180], [1, 1]])["asked"]
        self.assertEqual(asked["points"], [None, None, None, None, None, {"leg": 1, "led": 180}])
        self.assertEqual(asked["leds"], [None, None, None, None, [1, 1], [60, 6]])

    def of_kind(self, kind):
        """The mappings of one kind, by name."""
        found = {name: canvas for name, canvas in self.canvases.items() if canvas.kind == kind}
        self.assertGreaterEqual(len(found), 5)
        return found

    def test_strips_gives_each_row_its_y_its_side_and_its_end_numbers(self):
        for name, canvas in self.of_kind(mapping.ROWS).items():
            with self.subTest(name):
                places = rule(canvas)
                for index, (leg, rows) in enumerate(zip(canvas.legs, self.dumps[name]["strips"])):
                    self.assertEqual([row["y"] for row in rows], list(leg.strips))
                    for r, row in enumerate(rows):
                        self.assertEqual(sorted(row), ["first", "last", "start", "y"])
                        self.assertEqual((row["first"], row["last"]), (r * canvas.width + 1, (r + 1) * canvas.width))
                        first_x = places[index][row["first"] - 1][0]
                        self.assertEqual(row["start"], "right" if first_x == canvas.width else "left")
                        if canvas.width > 1:
                            self.assertEqual(places[index][row["last"] - 1][0], 1 if row["start"] == "right" else canvas.width)

    def test_strips_gives_each_column_its_x_its_end_and_its_end_numbers(self):
        for name, canvas in self.of_kind(mapping.COLUMNS).items():
            with self.subTest(name):
                places = rule(canvas)
                for index, (leg, columns) in enumerate(zip(canvas.legs, self.dumps[name]["strips"])):
                    self.assertEqual([column["x"] for column in columns], list(leg.strips))
                    for s, column in enumerate(columns):
                        self.assertEqual(sorted(column), ["first", "last", "start", "x"])
                        self.assertEqual((column["first"], column["last"]), (s * canvas.height + 1, (s + 1) * canvas.height))
                        self.assertEqual({tuple(place)[0] for place in places[index][column["first"] - 1:column["last"]]}, {column["x"]})
                        first_y = places[index][column["first"] - 1][1]
                        last_y = places[index][column["last"] - 1][1]
                        if canvas.height > 1:
                            self.assertEqual(column["start"], "bottom" if first_y == 1 else "top")
                            self.assertEqual((first_y, last_y), (1, canvas.height) if column["start"] == "bottom" else (canvas.height, 1))
                    # The columns of a leg start at the two ends in turn, the first at the first LED's.
                    self.assertEqual([column["start"] for column in columns],
                                     [leg.first_led if s % 2 == 0 else {"bottom": "top", "top": "bottom"}[leg.first_led] for s in range(len(columns))])

    def test_strips_gives_the_end_numbers_of_the_columns_of_the_target_file(self):
        strips = self.dumps["legs-20"]["strips"]
        self.assertEqual(len(strips), 20)
        for index, columns in enumerate(strips):
            self.assertEqual(columns, [
                {"x": 3 * index + 1, "start": "bottom", "first": 1, "last": 60},
                {"x": 3 * index + 2, "start": "top", "first": 61, "last": 120},
                {"x": 3 * index + 3, "start": "bottom", "first": 121, "last": 180},
            ])

    def test_strips_gives_the_end_numbers_of_the_drawings_in_the_mapping_document(self):
        text = (support.ROOT / "docs" / "mapping.md").read_text(encoding="utf-8")
        sections = {"legs-2": text.split("## Today's build")[1].split("\n## ")[0], "legs-10": text.split("## Target build")[1].split("\n## ")[0]}
        for name, section in sections.items():
            drawn = re.findall(r"(?m)^y=([0-9]+) +\| +([0-9]+) (<-+|-+>) +([0-9]+) \|(?: +leg ([0-9]+), pin ([0-9]+))?$", section)
            canvas = self.canvases[name]
            self.assertEqual(len(drawn), canvas.height, name)
            by_y = {}
            for index, rows in enumerate(self.dumps[name]["strips"]):
                for row in rows:
                    by_y[row["y"]] = (index, row)
            for y, at_left, arrow, at_right, leg, pin in drawn:
                index, row = by_y[int(y)]
                self.assertEqual(row["start"], "right" if arrow.startswith("<") else "left", (name, y))
                at_x1, at_xw = (row["last"], row["first"]) if row["start"] == "right" else (row["first"], row["last"])
                self.assertEqual((at_x1, at_xw), (int(at_left), int(at_right)), (name, y))
                if leg:
                    self.assertEqual((canvas.legs[index].leg, canvas.legs[index].pin), (int(leg), int(pin)))

    def test_strips_gives_the_end_numbers_of_the_tables_in_the_mapping_document(self):
        text = (support.ROOT / "docs" / "mapping.md").read_text(encoding="utf-8")
        rows_of_tables = re.findall(r"(?m)^\| ([0-9]+) \| ([0-9]+) \| ([0-9, ]+) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \|$", text)
        self.assertEqual(len(rows_of_tables), 12)
        for name, table in (("legs-2", rows_of_tables[:2]), ("legs-10", rows_of_tables[2:])):
            canvas = self.canvases[name]
            self.assertEqual(len(table), len(canvas.legs))
            for (leg, pin, ys, *numbers), listed, rows, places in zip(table, canvas.legs, self.dumps[name]["strips"], self.dumps[name]["positions"]):
                self.assertEqual((int(leg), int(pin), [int(y) for y in ys.split(",")]), (listed.leg, listed.pin, list(listed.strips)))
                ends = [number for row in rows for number in (row["first"], row["last"])]
                self.assertEqual(ends, [1, 60, 61, 120, 121, 180])
                pairs = list(zip(map(int, numbers[0::2]), map(int, numbers[1::2])))
                self.assertEqual([tuple(places[number - 1]) for number in ends], pairs)

    def test_path_passes_through_every_led_in_chain_order(self):
        for name, canvas in self.of_kind(mapping.ROWS).items():
            with self.subTest(name):
                for leg, corners, places in zip(canvas.legs, self.dumps[name]["paths"], rule(canvas)):
                    self.assertEqual(len(corners), 2 * len(leg.strips))
                    walked = []
                    for start, end in zip(corners[0::2], corners[1::2]):
                        self.assertEqual(start[1], end[1])
                        step = 1 if end[0] >= start[0] else -1
                        walked += [[x, start[1]] for x in range(start[0], end[0] + step, step)]
                    self.assertEqual(walked, places)

    def test_the_path_of_a_column_leg_passes_through_every_led_in_chain_order(self):
        for name, canvas in self.of_kind(mapping.COLUMNS).items():
            with self.subTest(name):
                for leg, corners, places in zip(canvas.legs, self.dumps[name]["paths"], rule(canvas)):
                    self.assertEqual(len(corners), 2 * len(leg.strips))
                    walked = []
                    for start, end in zip(corners[0::2], corners[1::2]):
                        self.assertEqual(start[0], end[0])
                        self.assertEqual({start[1], end[1]}, {1, canvas.height})
                        step = 1 if end[1] >= start[1] else -1
                        walked += [[start[0], y] for y in range(start[1], end[1] + step, step)]
                    self.assertEqual(walked, places)
        self.assertEqual(self.dumps["legs-20"]["paths"][0], [[1, 1], [1, 60], [2, 60], [2, 1], [3, 1], [3, 60]])
        self.assertEqual(self.dumps["legs-20"]["paths"][19], [[58, 1], [58, 60], [59, 60], [59, 1], [60, 1], [60, 60]])
        self.assertEqual(self.dumps["top-start"]["paths"][0], [[1, 7], [1, 1], [2, 1], [2, 7], [3, 7], [3, 1]])
        self.assertEqual(self.dumps["columns-apart"]["paths"], [[[2, 1], [2, 4], [4, 4], [4, 1]], [[1, 4], [1, 1], [5, 1], [5, 4], [3, 4], [3, 1]]])

    def test_runs_joins_the_neighbouring_rows_of_a_leg(self):
        self.assertEqual(self.dumps["legs-2"]["runs"], [[{"top": 6, "bottom": 4}], [{"top": 3, "bottom": 1}]])
        self.assertEqual(self.dumps["another-order"]["runs"], [[{"top": 4, "bottom": 4}, {"top": 2, "bottom": 2}], [{"top": 5, "bottom": 5}, {"top": 3, "bottom": 3}, {"top": 1, "bottom": 1}]])
        self.assertEqual(self.dumps["two-and-four-rows"]["runs"], [[{"top": 6, "bottom": 5}], [{"top": 4, "bottom": 1}]])

    def test_runs_joins_the_neighbouring_columns_of_a_leg_from_the_left(self):
        self.assertEqual(self.dumps["legs-20"]["runs"], [[{"left": 3 * index + 1, "right": 3 * index + 3}] for index in range(20)])
        self.assertEqual(self.dumps["columns-apart"]["runs"], [[{"left": 2, "right": 2}, {"left": 4, "right": 4}], [{"left": 1, "right": 1}, {"left": 3, "right": 3}, {"left": 5, "right": 5}]])
        self.assertEqual(self.dumps["two-and-four-columns"]["runs"], [[{"left": 1, "right": 2}], [{"left": 3, "right": 6}]])
        self.assertEqual(self.dumps["top-start"]["runs"], [[{"left": 1, "right": 3}]])
        self.assertEqual(self.dumps["one-led-column"]["runs"], [[{"left": 1, "right": 1}]])
        swapped = dump(json.dumps({"version": 1, "height": 2, "legs": [
            {"leg": 1, "pin": 1, "first_led": "bottom", "columns": [6, 2, 1, 5]}, {"leg": 2, "pin": 2, "first_led": "top", "columns": [4, 3, 7]}]}))
        self.assertEqual(swapped["runs"], [[{"left": 1, "right": 2}, {"left": 5, "right": 6}], [{"left": 3, "right": 4}, {"left": 7, "right": 7}]])

    def test_a_place_outside_the_canvas_of_a_column_leg_file_and_an_led_that_is_not_there_are_null(self):
        asked = dump(self.texts["legs-20"], points=[[0, 1], [61, 1], [1, 0], [1, 61], [2, 1.5], [1.5, 2], [1, 1], [2, 1], [60, 60]],
                     leds=[[19, 1], [1, 0], [1, 181], [1, 1.5], [47, 180], [21, 61], [1, 1]])["asked"]
        self.assertEqual(asked["points"], [None, None, None, None, None, None, {"leg": 0, "led": 1}, {"leg": 0, "led": 120}, {"leg": 19, "led": 180}])
        self.assertEqual(asked["leds"], [None, None, None, None, [60, 60], [56, 60], [1, 1]])

    def test_the_corners_of_the_target_file_are_where_its_requirement_puts_them(self):
        asked = dump(self.texts["legs-20"], leds=[[1, 1], [1, 60], [1, 61], [1, 120], [1, 121], [47, 180]])["asked"]
        self.assertEqual(asked["leds"], [[1, 1], [1, 60], [2, 60], [2, 1], [3, 1], [60, 60]])

    def test_position_in_a_column_leg_file_takes_the_pin_not_the_place_of_the_leg_in_the_file(self):
        swapped = json.loads(self.texts["columns-apart"])
        swapped["legs"].reverse()
        got = dump(json.dumps(swapped), leds=[[12, 1], [3, 1], [12, 8], [3, 12]])
        self.assertEqual(got["asked"]["leds"], [[2, 1], [1, 4], [4, 1], [3, 1]])
        self.assertEqual([leg["pin"] for leg in got["mapping"]["legs"]], [3, 12])

    def test_position_takes_the_pin_not_the_place_of_the_leg_in_the_file(self):
        swapped = json.loads(self.texts["legs-2"])
        swapped["legs"].reverse()
        got = dump(json.dumps(swapped), leds=[[1, 1], [2, 1], [1, 180], [2, 180]])
        self.assertEqual(got["asked"]["leds"], [[60, 6], [60, 3], [1, 4], [1, 1]])
        self.assertEqual([leg["pin"] for leg in got["mapping"]["legs"]], [2, 1])


class ColoursAndCurve(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dump = dump(core_support.mapping_texts()["legs-10"])

    def test_ten_legs_have_ten_different_colours(self):
        colours = self.dump["colours"]
        self.assertEqual(len(colours), 10)
        self.assertEqual(len(set(colours)), 10)
        self.assertEqual(colours, COLOURS[:10])

    def test_there_are_twenty_colours_and_a_leg_beyond_the_twentieth_takes_them_again_from_the_start(self):
        many = self.dump["manyColours"]
        self.assertEqual(len(many), 45)
        twenty = many[:20]
        self.assertEqual(len(set(twenty)), 20)
        self.assertEqual(many, [twenty[index % 20] for index in range(45)])
        for colour in twenty:
            self.assertRegex(colour, r"\A#[0-9a-f]{6}\Z")

    def test_the_colours_of_the_first_twelve_legs_are_the_twelve_of_the_list(self):
        self.assertEqual(self.dump["manyColours"][:12], COLOURS)
        self.assertEqual(len(set(COLOURS)), 12)

    def test_the_twenty_legs_of_the_target_file_have_twenty_different_colours(self):
        colours = dump(core_support.mapping_texts()["legs-20"])["colours"]
        self.assertEqual(len(colours), 20)
        self.assertEqual(len(set(colours)), 20)
        self.assertEqual(colours[:12], COLOURS)
        self.assertEqual(colours, self.dump["manyColours"][:20])

    def test_the_display_curve_is_fixed_starts_at_0_ends_at_255_and_never_falls(self):
        curve = self.dump["shown"]
        self.assertEqual(len(curve), 256)
        self.assertEqual((curve[0], curve[255]), (0, 255))
        self.assertTrue(all(later >= earlier for earlier, later in zip(curve, curve[1:])))
        self.assertEqual(curve, [math.floor(255 * (value / 255) ** (1 / 2.2) + 0.5) for value in range(256)])
        self.assertGreater(curve[128], 128)
        self.assertGreater(curve[1], 0)


class Fit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        texts = core_support.mapping_texts()
        cls.areas = [[1280, 800], [1280, 546], [756, 500], [300, 200], [3000, 2000], [1920, 1000]]
        cls.ten = dump(texts["legs-10"], areas=cls.areas)
        cls.two = dump(texts["legs-2"], areas=cls.areas)

    def parts(self, f):
        return [f["bracket"], f["yLabel"], f["numberLeft"], f["canvas"], f["numberRight"], f["header"], *f["gutters"]]

    def test_the_ten_leg_mapping_at_1280_x_800_has_a_cell_of_17_pixels(self):
        f = self.ten["fits"][0]
        self.assertEqual(f["cell"], 17)
        self.assertEqual((f["canvas"]["width"], f["canvas"]["height"]), (60 * 17, 30 * 17))
        self.assertEqual((f["width"], f["height"]), (1280, 800))

    def test_every_part_is_inside_the_area_and_apart_from_the_others(self):
        for dumped in (self.ten, self.two):
            for area, f in zip(self.areas, dumped["fits"]):
                if area == [300, 200]:
                    continue
                with self.subTest(area=area):
                    whole = {"x": 0, "y": 0, "width": area[0], "height": area[1]}
                    parts = self.parts(f)
                    for part in parts:
                        self.assertTrue(inside(part, whole), part)
                        self.assertTrue(inside(part, f["content"]), part)
                    for index, first in enumerate(parts):
                        for second in parts[index + 1:]:
                            self.assertTrue(apart(first, second), (first, second))
                    self.assertEqual(f["canvas"]["width"], 60 * f["cell"])

    def test_the_cell_is_the_largest_that_fits_between_4_and_28_pixels(self):
        cells = dict(zip(map(tuple, self.areas), (f["cell"] for f in self.ten["fits"])))
        self.assertEqual(cells[(1280, 546)], 17)
        self.assertEqual(cells[(3000, 2000)], 28)
        self.assertEqual(cells[(300, 200)], 4)
        self.assertGreaterEqual(cells[(756, 500)], 9)
        self.assertGreater(cells[(1920, 1000)], cells[(1280, 800)])
        two = dict(zip(map(tuple, self.areas), (f["cell"] for f in self.two["fits"])))
        self.assertEqual(two[(1280, 800)], 17)
        self.assertEqual(two[(3000, 2000)], 28)

    def test_a_drawing_that_cannot_fit_is_larger_than_the_area_and_keeps_its_parts_apart(self):
        f = self.ten["fits"][self.areas.index([300, 200])]
        self.assertEqual(f["cell"], 4)
        self.assertGreater(f["width"], 300)
        self.assertEqual(f["canvas"]["width"], 240)
        parts = self.parts(f)
        for index, first in enumerate(parts):
            for second in parts[index + 1:]:
                self.assertTrue(apart(first, second), (first, second))

    def test_1_1_is_at_the_bottom_left_x_grows_to_the_right_and_y_upward(self):
        for f, (bottom_left, bottom_right, top_left, top_right), cells in zip(self.ten["fits"], self.ten["centres"], self.ten["cells"]):
            cell, canvas = f["cell"], f["canvas"]
            self.assertEqual(bottom_left, [canvas["x"] + 0.5 * cell, canvas["y"] + (30 - 1 + 0.5) * cell])
            self.assertEqual(top_right, [canvas["x"] + (60 - 0.5) * cell, canvas["y"] + 0.5 * cell])
            self.assertLess(bottom_left[0], bottom_right[0])
            self.assertGreater(bottom_left[1], top_left[1])
            self.assertEqual(cells, [[1, 1], [60, 1], [1, 30], [60, 30], None, None])


def column_text(height, legs):
    """A column-leg mapping file with these legs, each given as (leg, pin, first_led, columns)."""
    return json.dumps({"version": 1, "height": height, "legs": [dict(zip(("leg", "pin", "first_led", "columns"), leg)) for leg in legs]})


class UprightLeds(unittest.TestCase):
    """The LEDs view of a column-leg file: the canvas, the marks of the rows beside it, the
    header with the marks of the columns, the leg band with its words, and the two bands of
    LED numbers."""

    PARTS = ("header", "legBand", "legWords", "yLabel", "canvas")
    NUMBER_BANDS = ("numberTop", "numberBottom")

    @classmethod
    def setUpClass(cls):
        texts = core_support.mapping_texts()
        cls.areas = [[1280, 546], [500, 546], [1280, 800], [756, 546], [1280, 620], [1280, 648], [1920, 1000], [300, 200], [3000, 2000]]
        cls.names = ["legs-20", *core_support.column_mapping_texts()]
        cls.dumps = {name: dump(texts[name], areas=cls.areas) for name in cls.names}

    def each(self):
        for name, dumped in self.dumps.items():
            for index, area in enumerate(self.areas):
                yield name, tuple(area), dumped, index

    def parts(self, f):
        """The parts of a fit: every one it must name, and the number bands it has."""
        missing = sorted({"view", "feed", "cell", "width", "height", "content", "gutters", *self.PARTS, *self.NUMBER_BANDS} - set(f))
        self.assertEqual(missing, [], "the fit lacks parts of the LEDs view of a column-leg file")
        self.assertEqual(len(f["gutters"]), 2)
        return [*f["gutters"], *(f[name] for name in self.PARTS), *(f[name] for name in self.NUMBER_BANDS if f[name] is not None)]

    def target(self, area):
        return self.dumps["legs-20"]["fits"][self.areas.index(list(area))]

    def test_the_mappings_are_the_target_file_and_the_four_made_up_column_leg_files(self):
        self.assertEqual(self.names, ["legs-20", "top-start", "two-and-four-columns", "columns-apart", "one-led-column"])
        self.assertEqual({name: dumped["mapping"]["kind"] for name, dumped in self.dumps.items()}, dict.fromkeys(self.names, "columns"))
        self.assertEqual({name: (dumped["mapping"]["width"], dumped["mapping"]["height"]) for name, dumped in self.dumps.items()},
                         {"legs-20": (60, 60), "top-start": (3, 7), "two-and-four-columns": (6, 5), "columns-apart": (5, 4), "one-led-column": (1, 1)})

    def test_the_target_file_is_whole_in_an_area_of_1280_x_546_with_cells_of_7_or_more(self):
        f = self.target((1280, 546))
        self.assertEqual((f["width"], f["height"]), (1280, 546), "the drawing is larger than the area, so the stage would scroll")
        self.assertGreaterEqual(f["cell"], 7)
        self.assertEqual((f["canvas"]["width"], f["canvas"]["height"]), (60 * f["cell"], 60 * f["cell"]))
        whole = {"x": 0, "y": 0, "width": 1280, "height": 546}
        for part in self.parts(f):
            self.assertTrue(inside(part, whole), part)
        self.assertEqual(f["cell"], 8)
        self.assertEqual((f["canvas"]["width"], f["canvas"]["height"]), (480, 480))

    def test_the_target_file_is_whole_in_an_area_of_500_x_546_with_cells_of_7_or_more(self):
        f = self.target((500, 546))
        self.assertEqual((f["width"], f["height"]), (500, 546), "the drawing is larger than the area, so the stage would scroll")
        self.assertGreaterEqual(f["cell"], 7)
        self.assertEqual((f["canvas"]["width"], f["canvas"]["height"]), (60 * f["cell"], 60 * f["cell"]))
        whole = {"x": 0, "y": 0, "width": 500, "height": 546}
        for part in self.parts(f):
            self.assertTrue(inside(part, whole), part)
        # What stands beside the canvas takes 80 pixels of the width at most.
        self.assertLessEqual(f["content"]["width"] - f["canvas"]["width"], 80)

    def test_every_part_is_inside_the_drawing_and_apart_from_the_others(self):
        for name, area, dumped, index in self.each():
            with self.subTest(name=name, area=area):
                f = dumped["fits"][index]
                self.assertEqual(f["view"], "leds")
                self.assertTrue(4 <= f["cell"] <= 28)
                self.assertEqual((f["canvas"]["width"], f["canvas"]["height"]), (dumped["mapping"]["width"] * f["cell"], dumped["mapping"]["height"] * f["cell"]))
                self.assertEqual((f["width"], f["height"]), (max(area[0], f["content"]["width"]), max(area[1], f["content"]["height"])))
                whole = {"x": 0, "y": 0, "width": f["width"], "height": f["height"]}
                parts = self.parts(f)
                for part in parts:
                    self.assertTrue(inside(part, whole), part)
                    self.assertTrue(inside(part, f["content"]), part)
                    self.assertGreater(part["width"], 0)
                    self.assertGreater(part["height"], 0)
                for at, first in enumerate(parts):
                    for second in parts[at + 1:]:
                        self.assertTrue(apart(first, second), (first, second))

    def test_a_drawing_that_fits_its_area_is_in_the_middle_of_it(self):
        for name, area, dumped, index in self.each():
            f = dumped["fits"][index]
            content = f["content"]
            if content["width"] <= area[0]:
                self.assertEqual(content["x"], (area[0] - content["width"]) // 2, (name, area))
            else:
                self.assertEqual(content["x"], 0, (name, area))
            if content["height"] <= area[1]:
                self.assertEqual(content["y"], (area[1] - content["height"]) // 2, (name, area))
            else:
                self.assertEqual(content["y"], 0, (name, area))

    def test_the_cell_is_the_largest_that_fits_between_4_and_28_pixels(self):
        cells = {tuple(area): self.target(area)["cell"] for area in self.areas}
        self.assertEqual(cells, {(1280, 546): 8, (500, 546): 7, (1280, 800): 11, (756, 546): 8, (1280, 620): 8, (1280, 648): 9, (1920, 1000): 14, (300, 200): 4, (3000, 2000): 28})
        for name, area, dumped, index in self.each():
            f = dumped["fits"][index]
            width, height = dumped["mapping"]["width"], dumped["mapping"]["height"]
            if f["cell"] == 28:
                continue
            # One pixel more for every cell would not fit. Where the drawing has no number
            # bands the cells stay below 9, where it would have them.
            too_large = f["content"]["width"] + width > area[0] or f["content"]["height"] + height > area[1]
            self.assertTrue(too_large or (f["cell"] == 8 and f["numberTop"] is None), (name, area, f["cell"]))
        # A drawing that cannot fit keeps cells of 4 pixels and is higher than its area.
        small = self.target((300, 200))
        self.assertEqual((small["cell"], small["width"], small["height"]), (4, 300, 300))

    def test_the_number_bands_are_drawn_where_the_cells_are_9_pixels_or_more(self):
        numbered = set()
        for name, area, dumped, index in self.each():
            with self.subTest(name=name, area=area):
                f = dumped["fits"][index]
                canvas = f["canvas"]
                for band in self.NUMBER_BANDS:
                    self.assertEqual(f[band] is not None, f["cell"] >= 9, band)
                numbered.add(f["cell"] >= 9)
                if f["cell"] >= 9:
                    top, bottom = f["numberTop"], f["numberBottom"]
                    self.assertEqual((top["x"], top["width"], top["y"] + top["height"]), (canvas["x"], canvas["width"], canvas["y"]))
                    self.assertEqual((bottom["x"], bottom["width"], bottom["y"]), (canvas["x"], canvas["width"], canvas["y"] + canvas["height"]))
                    self.assertEqual(top["height"], bottom["height"])
                    self.assertGreaterEqual(top["height"], 24)
        self.assertEqual(numbered, {True, False})
        self.assertIsNone(self.target((1280, 546))["numberTop"])
        self.assertIsNone(self.target((1280, 620))["numberTop"])
        self.assertIsNotNone(self.target((1280, 648))["numberTop"])
        self.assertIsNotNone(self.target((1280, 800))["numberBottom"])

    def test_the_leg_band_is_on_the_side_of_the_canvas_away_from_the_feed_edge(self):
        feeds = {name: dumped["side"] for name, dumped in self.dumps.items()}
        self.assertEqual(feeds, {"legs-20": "bottom", "top-start": "top", "two-and-four-columns": "bottom", "columns-apart": "bottom", "one-led-column": "top"})
        for name, area, dumped, index in self.each():
            with self.subTest(name=name, area=area):
                f = dumped["fits"][index]
                self.parts(f)
                canvas, band, header, words, marks = f["canvas"], f["legBand"], f["header"], f["legWords"], f["yLabel"]
                self.assertEqual(f["feed"], feeds[name])
                top = f["numberTop"] or canvas
                bottom = f["numberBottom"] or canvas
                if f["feed"] == "bottom":
                    # From the top: the marks of the columns, the leg band, and the canvas with its numbers.
                    self.assertLessEqual(header["y"] + header["height"], band["y"])
                    self.assertEqual(band["y"] + band["height"], top["y"])
                else:
                    self.assertEqual(bottom["y"] + bottom["height"], band["y"])
                    self.assertLessEqual(band["y"] + band["height"], header["y"])
                for across in (band, header):
                    self.assertEqual((across["x"], across["width"]), (canvas["x"], canvas["width"]))
                # The words leg and pin stand at the left end of the band, and the marks of
                # the rows at the left of the canvas.
                self.assertEqual((words["y"], words["height"]), (band["y"], band["height"]))
                self.assertEqual(words["x"] + words["width"], band["x"])
                self.assertEqual((marks["y"], marks["height"]), (canvas["y"], canvas["height"]))
                self.assertEqual(marks["x"] + marks["width"], canvas["x"])
                self.assertGreaterEqual(band["height"], 30)
                self.assertGreaterEqual(marks["width"], 28)

    def test_every_run_of_columns_of_a_leg_has_its_span_of_the_leg_band(self):
        for name, area, dumped, index in self.each():
            with self.subTest(name=name, area=area):
                f, spans = dumped["fits"][index], dumped["spans"][index]
                expected = [(leg, run["left"], run["right"]) for leg, runs in enumerate(dumped["runs"]) for run in runs]
                self.assertEqual([(span["leg"], span["left"], span["right"]) for span in spans], expected)
                for span in spans:
                    self.assertEqual(span["x"], f["canvas"]["x"] + (span["left"] - 1) * f["cell"])
                    self.assertEqual(span["width"], (span["right"] - span["left"] + 1) * f["cell"])
                    self.assertTrue(f["legBand"]["x"] <= span["x"] and span["x"] + span["width"] <= f["legBand"]["x"] + f["legBand"]["width"])
                ordered = sorted(spans, key=lambda span: span["x"])
                self.assertEqual(ordered[0]["x"], f["canvas"]["x"])
                for first, second in zip(ordered, ordered[1:]):
                    self.assertEqual(first["x"] + first["width"], second["x"])
                self.assertEqual(sum(span["width"] for span in spans), f["canvas"]["width"])
        target = self.dumps["legs-20"]["spans"][0]
        self.assertEqual([(span["leg"], span["width"]) for span in target], [(index, 24) for index in range(20)])
        apart_spans = self.dumps["columns-apart"]["spans"][0]
        self.assertEqual([(span["leg"], span["left"]) for span in apart_spans], [(0, 2), (0, 4), (1, 1), (1, 3), (1, 5)])
        self.assertEqual({span["width"] for span in apart_spans}, {28})

    def test_1_1_is_at_the_bottom_left_x_grows_to_the_right_and_y_upward(self):
        for name, area, dumped, index in self.each():
            with self.subTest(name=name, area=area):
                f = dumped["fits"][index]
                width, height = dumped["mapping"]["width"], dumped["mapping"]["height"]
                bottom_left, bottom_right, top_left, top_right = dumped["centres"][index]
                cell, canvas = f["cell"], f["canvas"]
                self.assertEqual(bottom_left, [canvas["x"] + 0.5 * cell, canvas["y"] + (height - 1 + 0.5) * cell])
                self.assertEqual(top_right, [canvas["x"] + (width - 0.5) * cell, canvas["y"] + 0.5 * cell])
                self.assertEqual(dumped["cells"][index], [[1, 1], [width, 1], [1, height], [width, height], None, None])
                if width > 1:
                    self.assertLess(bottom_left[0], bottom_right[0])
                if height > 1:
                    self.assertGreater(bottom_left[1], top_left[1])

    def test_the_marks_are_the_first_every_tenth_and_the_last(self):
        counts = [60, 1, 2, 7, 10, 11, 12, 13, 30, 32, 33, 100]
        marks = dict(zip(counts, dump(core_support.mapping_texts()["legs-20"], counts=counts)["marks"]))
        self.assertEqual(marks[60], [1, 10, 20, 30, 40, 50, 60])
        self.assertEqual(marks[100], [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        self.assertEqual(marks[30], [1, 10, 20, 30])
        self.assertEqual((marks[1], marks[2], marks[7], marks[10]), ([1], [1, 2], [1, 7], [1, 10]))
        # A tenth nearer than three to the last would stand on it, and is left out.
        self.assertEqual((marks[11], marks[12], marks[13]), ([1, 11], [1, 12], [1, 10, 13]))
        self.assertEqual((marks[32], marks[33]), ([1, 10, 20, 32], [1, 10, 20, 30, 33]))

    def test_side_is_the_edge_where_most_legs_have_their_first_led_and_the_bottom_when_equal(self):
        cases = {
            "bottom": [(1, 1, "bottom", [1]), (2, 2, "bottom", [2])],
            "top": [(1, 1, "top", [1]), (2, 2, "top", [2])],
            "bottom ": [(1, 1, "top", [1]), (2, 2, "bottom", [2])],
            "top ": [(1, 1, "top", [1]), (2, 2, "bottom", [2]), (3, 3, "top", [3])],
            "bottom  ": [(1, 1, "bottom", [1]), (2, 2, "bottom", [2]), (3, 3, "top", [3])],
        }
        for expected, legs in cases.items():
            self.assertEqual(dump(column_text(4, legs))["side"], expected.strip(), legs)

    def test_with_one_leg_of_the_target_file_started_at_the_top_the_feed_edge_and_the_parts_stay(self):
        listed = json.loads(core_support.mapping_texts()["legs-20"])
        listed["legs"][6]["first_led"] = "top"
        flipped = dump(json.dumps(listed), areas=self.areas)
        self.assertEqual(flipped["side"], "bottom")
        self.assertEqual(flipped["fits"], self.dumps["legs-20"]["fits"])
        self.assertEqual(flipped["spans"], self.dumps["legs-20"]["spans"])
        self.assertEqual(flipped["strips"][6], [{"x": 19, "start": "top", "first": 1, "last": 60}, {"x": 20, "start": "bottom", "first": 61, "last": 120}, {"x": 21, "start": "top", "first": 121, "last": 180}])
        self.assertEqual(flipped["strips"][:6] + flipped["strips"][7:], self.dumps["legs-20"]["strips"][:6] + self.dumps["legs-20"]["strips"][7:])


class EveryMapping(unittest.TestCase):
    def test_every_mapping_of_both_kinds_is_fitted_with_and_without_a_board_in_a_wide_and_a_narrow_area(self):
        areas = [[1280, 546], [756, 546], [500, 546]]
        texts = core_support.mapping_texts()
        self.assertGreaterEqual(len(texts), 11)
        for name, text in texts.items():
            with self.subTest(name):
                dumped = dump(text, areas=areas)
                width, height = dumped["mapping"]["width"], dumped["mapping"]["height"]
                self.assertEqual((len(dumped["fits"]), len(dumped["mapped"])), (3, 3))
                for f in dumped["fits"] + [mapped["fit"] for mapped in dumped["mapped"]]:
                    self.assertTrue(4 <= f["cell"] <= 28)
                    self.assertEqual((f["canvas"]["width"], f["canvas"]["height"]), (width * f["cell"], height * f["cell"]))
                    self.assertTrue(inside(f["canvas"], {"x": 0, "y": 0, "width": f["width"], "height": f["height"]}))
                for mapped in dumped["mapped"]:
                    self.assertEqual(len(mapped["chains"]), len(dumped["mapping"]["legs"]))
                    self.assertEqual(len(mapped["firsts"]), len(dumped["mapping"]["legs"]))


# What the layout gives the bench file in each drawing area: for the LEDs view the cell and
# the canvas (x, y, width, height), and for the mapping view the arrangement, the cell, the
# place of the canvas (x, y) and the board (x, y, pitch).
BENCH = {
    (1280, 800): ((17, 192, 355, 1020, 102), ("beside", 13, 127, 366, 1005, 186, 17)),
    (1280, 546): ((17, 192, 228, 1020, 102), ("beside", 13, 127, 239, 1005, 59, 17)),
    (1100, 600): ((14, 192, 264, 840, 84), ("beside", 10, 127, 275, 825, 86, 17)),
    (900, 465): ((12, 133, 201, 720, 72), ("below", 11, 148, 18, 610, 110, 16)),
    (756, 500): ((10, 121, 225, 600, 60), ("below", 9, 136, 18, 478, 98, 16)),
    (756, 400): ((10, 121, 175, 600, 60), ("below", 9, 136, 18, 478, 98, 16)),
    (300, 200): ((4, 120, 93, 240, 24), ("beside", 4, 124, 141, 462, 26, 10)),
    (1920, 1000): ((28, 182, 422, 1680, 168), ("beside", 22, 180, 439, 1608, 246, 20)),
    (3000, 2000): ((28, 722, 922, 1680, 168), ("beside", 28, 540, 921, 2328, 746, 20)),
}


class BenchFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dump = dump(core_support.mapping_texts()["legs-2"], areas=[list(area) for area in BENCH])

    def test_the_leds_view_has_its_cell_and_its_canvas_where_they_are(self):
        for (area, (leds, _)), f in zip(BENCH.items(), self.dump["fits"]):
            canvas = f["canvas"]
            self.assertEqual((f["cell"], canvas["x"], canvas["y"], canvas["width"], canvas["height"]), leds, area)
            self.assertEqual(sorted(f), sorted(["view", "cell", "roomy", "width", "height", "content", "gutters", "header", "bracket", "yLabel", "numberLeft", "numberRight", "canvas"]))

    def test_the_mapping_view_has_its_cell_its_canvas_and_its_board_where_they_are(self):
        for (area, (_, mapping_view)), mapped in zip(BENCH.items(), self.dump["mapped"]):
            f = mapped["fit"]
            canvas, board = f["canvas"], f["board"]
            self.assertEqual((f["arrangement"], f["cell"], canvas["x"], canvas["y"], board["x"], board["y"], board["pitch"]), mapping_view, area)


def mapping_text(width, legs):
    """A mapping file with these legs, each given as (leg, pin, first_led, rows)."""
    return json.dumps({"version": 1, "width": width, "legs": [dict(zip(("leg", "pin", "first_led", "rows"), leg)) for leg in legs]})


def segments(points):
    """The straight pieces of a line through corner points: each level or upright."""
    pieces = []
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x1 != x2 and y1 != y2:
            raise AssertionError(f"a piece of a line is neither level nor upright: {(x1, y1)} to {(x2, y2)}")
        pieces.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
    return pieces


def meetings(first, second):
    """`(crossings, overlaps)` of two lines given as corner points: the places where a
    level piece of one crosses an upright piece of the other, and the pieces of the two
    that lie on each other."""
    crossings = overlaps = 0
    for ax1, ay1, ax2, ay2 in segments(first):
        for bx1, by1, bx2, by2 in segments(second):
            a_level, b_level = ay1 == ay2, by1 == by2
            if a_level != b_level:
                crossings += ax1 <= bx2 and bx1 <= ax2 and ay1 <= by2 and by1 <= ay2
            elif a_level:
                overlaps += ay1 == by1 and ax1 < bx2 and bx1 < ax2
            else:
                overlaps += ax1 == bx1 and ay1 < by2 and by1 < ay2
    return crossings, overlaps


def through(rect, points, margin=0):
    """Whether a line through corner points passes through the inside of a rectangle."""
    for x1, y1, x2, y2 in segments(points):
        if x1 < rect["x"] + rect["width"] - margin and rect["x"] + margin < x2 + (x1 == x2) and y1 < rect["y"] + rect["height"] - margin and rect["y"] + margin < y2 + (y1 == y2):
            return True
    return False


class Board(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = core_support.mapping_texts()
        cls.ten = dump(cls.texts["legs-10"], pins=list(range(0, 12)) + [48, 99, 255], areas=[[1280, 800]])

    def test_side_is_where_most_legs_have_their_first_led_and_right_when_equal(self):
        cases = {
            "right": [(1, 1, "right", [2]), (2, 2, "right", [1])],
            "left": [(1, 1, "left", [2]), (2, 2, "left", [1])],
            "right ": [(1, 1, "left", [2]), (2, 2, "right", [1])],
            "left ": [(1, 1, "left", [3]), (2, 2, "right", [2]), (3, 3, "left", [1])],
            "right  ": [(1, 1, "right", [3]), (2, 2, "right", [2]), (3, 3, "left", [1])],
        }
        for expected, legs in cases.items():
            self.assertEqual(dump(mapping_text(4, legs))["side"], expected.strip(), legs)
        self.assertEqual(self.ten["side"], "right")
        self.assertEqual(dump(self.texts["left-start"])["side"], "left")

    def test_place_finds_the_pad_of_a_gpio_in_the_two_rows_of_the_board(self):
        places = dict(zip(list(range(0, 12)) + [48, 99, 255], self.ten["places"]))
        self.assertEqual(places[1], {"row": "right", "index": 3})
        self.assertEqual(places[2], {"row": "right", "index": 4})
        self.assertEqual(places[3], {"row": "left", "index": 12})
        self.assertEqual([places[pin] for pin in (4, 5, 6, 7)], [{"row": "left", "index": index} for index in (3, 4, 5, 6)])
        self.assertEqual([places[pin] for pin in (8, 9, 10, 11)], [{"row": "left", "index": index} for index in (11, 14, 15, 16)])
        self.assertEqual(places[0], {"row": "right", "index": 13})
        self.assertEqual(places[48], {"row": "right", "index": 15})
        self.assertIsNone(places[99])
        self.assertIsNone(places[255])
        board = self.ten["board"]
        for pin, found in places.items():
            if found:
                self.assertEqual(board[found["row"]][found["index"]], str(pin))

    def test_tracks_gives_every_leg_its_own_track_ordered_by_the_first_row(self):
        self.assertEqual(self.ten["tracks"], list(range(10)))
        another = dump(self.texts["another-order"])
        self.assertEqual(another["tracks"], [0, 1])
        shuffled = dump(mapping_text(3, [(1, 1, "right", [2, 1]), (2, 2, "right", [6]), (3, 3, "left", [3, 5]), (4, 4, "left", [4])]))
        self.assertEqual(shuffled["tracks"], [3, 0, 2, 1])
        self.assertEqual(sorted(shuffled["tracks"]), [0, 1, 2, 3])

    def test_the_ten_leg_mapping_at_1280_x_800_has_a_cell_of_12_pixels_beside_the_board(self):
        f = self.ten["mapped"][0]["fit"]
        self.assertEqual((f["view"], f["arrangement"], f["boardSide"]), ("mapping", "beside", "right"))
        self.assertEqual(f["cell"], 12)
        self.assertEqual((f["canvas"]["width"], f["canvas"]["height"]), (720, 360))
        self.assertEqual(f["channel"]["width"], 100)
        self.assertEqual(f["board"]["pitch"], 16)
        self.assertEqual((f["board"]["width"], f["board"]["height"]), (184, 420))
        self.assertEqual((f["width"], f["height"]), (1280, 800))

    def test_the_canvas_the_gutters_the_channel_and_the_board_are_inside_the_area_and_apart(self):
        f = self.ten["mapped"][0]["fit"]
        whole = {"x": 0, "y": 0, "width": 1280, "height": 800}
        parts = [f["gutters"][0], f["bracket"], f["yLabel"], f["numberLeft"], f["canvas"], f["numberRight"], f["channel"], f["nearLabel"], f["board"], f["farZone"], f["gutters"][1]]
        for part in parts:
            self.assertTrue(inside(part, whole), part)
        for index, first in enumerate(parts):
            for second in parts[index + 1:]:
                self.assertTrue(apart(first, second), (first, second))
        self.assertEqual([part["x"] for part in parts], sorted(part["x"] for part in parts))
        self.assertTrue(apart(f["header"], f["canvas"]))


class Lines(unittest.TestCase):
    """The lines from the pads of the board to the first LEDs, for the board beside the
    canvas and for the board below it."""

    @classmethod
    def setUpClass(cls):
        texts = core_support.mapping_texts()
        cls.areas = [[1280, 800], [1280, 546], [1100, 600], [900, 465], [756, 400], [1920, 1000]]
        cls.mappings = {
            "legs-10": texts["legs-10"],
            "legs-2": texts["legs-2"],
            "board on the left": mapping_text(40, [(1, 4, "left", [12, 11, 10, 9]), (2, 38, "left", [8, 7, 6, 5]), (3, 21, "right", [4, 3]), (4, 14, "left", [2, 1])]),
            "pins the board lacks, rows apart": mapping_text(30, [(7, 99, "right", [10, 8, 6]), (2, 13, "left", [9, 7]), (5, 47, "right", [5, 4, 3, 2, 1]), (9, 200, "left", [11])]),
            "another-order": texts["another-order"],
            "one-led": texts["one-led"],
        }
        cls.dumps = {name: dump(text, areas=cls.areas) for name, text in cls.mappings.items()}

    def each(self):
        for name, dumped in self.dumps.items():
            for area, mapped in zip(self.areas, dumped["mapped"]):
                yield name, tuple(area), dumped, mapped

    def test_a_wide_area_has_the_board_beside_the_canvas_and_a_narrow_one_below_it(self):
        arrangements = {area: mapped["fit"]["arrangement"] for name, area, _, mapped in self.each() if name == "legs-10"}
        self.assertEqual(arrangements, {(1280, 800): "beside", (1280, 546): "beside", (1100, 600): "beside", (900, 465): "below", (756, 400): "below", (1920, 1000): "beside"})
        cells = {area: mapped["fit"]["cell"] for name, area, _, mapped in self.each() if name == "legs-10"}
        self.assertEqual((cells[(1280, 800)], cells[(1280, 546)]), (12, 12))
        self.assertGreaterEqual(cells[(900, 465)], 9)
        self.assertGreaterEqual(cells[(1100, 600)], 9)
        self.assertGreaterEqual(cells[(1920, 1000)], 20)
        below = next(mapped["fit"] for name, area, _, mapped in self.each() if name == "legs-10" and area == (900, 465))
        self.assertGreaterEqual(below["board"]["y"], below["canvas"]["y"] + below["canvas"]["height"] + below["band"]["height"])
        self.assertEqual(below["width"], 900)
        self.assertGreater(below["height"], 465)

    def test_every_part_is_inside_the_drawing_and_the_board_is_apart_from_the_canvas(self):
        for name, area, _, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                whole = {"x": 0, "y": 0, "width": f["width"], "height": f["height"]}
                for part in (f["canvas"], f["board"], f["bracket"], f["yLabel"], f["numberLeft"], f["numberRight"], f["channel"], f["header"], *f["gutters"]):
                    self.assertTrue(inside(part, whole), part)
                self.assertTrue(apart(f["board"], f["canvas"]))
                self.assertTrue(apart(f["board"], f["channel"]))
                self.assertTrue(apart(f["canvas"], f["channel"]))
                self.assertGreaterEqual(f["board"]["pitch"], 10)
                self.assertLessEqual(f["board"]["pitch"], 20)
                self.assertTrue(4 <= f["cell"] <= 28)

    def test_every_line_runs_from_the_pad_of_its_pin_to_the_first_led_of_its_chain(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f, legs = mapped["fit"], dumped["mapping"]["legs"]
                self.assertEqual([wire["leg"] for wire in mapped["wires"]], list(range(len(legs))))
                for wire, leg, first in zip(mapped["wires"], legs, mapped["firsts"]):
                    start, end = wire["points"][0], wire["points"][-1]
                    self.assertEqual(start, [wire["pad"]["x"], wire["pad"]["y"]])
                    self.assertEqual(end[1], first[1])
                    self.assertLessEqual(abs(end[0] - first[0]), f["cell"] / 2 + 2)
                    self.assertFalse(f["canvas"]["x"] < end[0] < f["canvas"]["x"] + f["canvas"]["width"])
                    place = next((row, index) for row in ("left", "right") for index, label in enumerate(dumped["board"][row]) if label == str(leg["pin"])) if wire["kind"] != "off" else None
                    if place is None:
                        self.assertEqual((wire["pad"]["row"], wire["pad"]["index"]), (None, None))
                        self.assertGreater(wire["pad"]["y"], f["board"]["y"] + f["board"]["height"])
                    else:
                        self.assertEqual((wire["pad"]["row"], wire["pad"]["index"]), place)
                        self.assertTrue(f["board"]["x"] < wire["pad"]["x"] < f["board"]["x"] + f["board"]["width"])
                        self.assertTrue(f["board"]["y"] < wire["pad"]["y"] < f["board"]["y"] + f["board"]["height"])
                    segments(wire["points"])

    def test_the_pads_of_one_row_are_one_pitch_apart_from_the_antenna_end_to_the_usb_end(self):
        mapped = self.dumps["legs-10"]["mapped"][0]
        f = mapped["fit"]
        pads = {(wire["pad"]["row"], wire["pad"]["index"]): (wire["pad"]["x"], wire["pad"]["y"]) for wire in mapped["wires"]}
        self.assertEqual(pads[("left", 4)][1] - pads[("left", 3)][1], f["board"]["pitch"])
        self.assertEqual(pads[("left", 15)][1] - pads[("left", 3)][1], 12 * f["board"]["pitch"])
        self.assertEqual(pads[("right", 3)][1], pads[("left", 3)][1])
        self.assertLess(pads[("left", 3)][0], pads[("right", 3)][0])
        self.assertEqual({x for (row, _), (x, _) in pads.items() if row == "left"}, {pads[("left", 3)][0]})

    def test_no_line_passes_through_the_board_and_no_two_lines_lie_on_each_other(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                for wire in mapped["wires"]:
                    self.assertFalse(through(f["board"], wire["points"], margin=f["board"]["pitch"] * 0.75), f"the line of leg index {wire['leg']} passes through the board")
                for index, first in enumerate(mapped["wires"]):
                    for second in mapped["wires"][index + 1:]:
                        self.assertEqual(meetings(first["points"], second["points"])[1], 0, (first["leg"], second["leg"]))

    def test_the_lines_of_the_tracked_mappings_cross_only_where_the_pins_are_out_of_order(self):
        for area, mapped in zip(self.areas, self.dumps["legs-10"]["mapped"]):
            wires = mapped["wires"]
            crossings = sum(meetings(first["points"], second["points"])[0] for index, first in enumerate(wires) for second in wires[index + 1:])
            self.assertEqual(crossings, 6, f"{area}: the lines of the ten-leg mapping cross {crossings} times")
        for area, mapped in zip(self.areas, self.dumps["legs-2"]["mapped"]):
            wires = mapped["wires"]
            self.assertEqual(sum(meetings(first["points"], second["points"])[0] for index, first in enumerate(wires) for second in wires[index + 1:]), 1, area)

    def test_a_first_led_on_the_side_away_from_the_board_is_reached_through_the_gap_above_its_row(self):
        dumped = self.dumps["board on the left"]
        mapped = dumped["mapped"][0]
        f = mapped["fit"]
        self.assertEqual(f["boardSide"], "left")
        self.assertLess(f["board"]["x"], f["canvas"]["x"])
        wire, first = mapped["wires"][2], mapped["firsts"][2]
        self.assertEqual(dumped["mapping"]["legs"][2]["first_led"], "right")
        gap = first[1] - f["cell"] / 2
        level = [piece for piece in segments(wire["points"]) if piece[1] == piece[3] == gap]
        self.assertEqual(len(level), 1)
        self.assertLessEqual(level[0][0], f["canvas"]["x"])
        self.assertGreaterEqual(level[0][2], f["canvas"]["x"] + f["canvas"]["width"])
        self.assertGreater(wire["points"][-1][0], f["canvas"]["x"] + f["canvas"]["width"])
        other = mapped["wires"][0]
        self.assertLess(other["points"][-1][0], f["canvas"]["x"])

    def test_the_chain_of_a_leg_passes_through_the_corners_of_its_path_and_turns_outside_the_canvas(self):
        for name, area, dumped, mapped in self.each():
            f = mapped["fit"]
            width, height = dumped["mapping"]["width"], dumped["mapping"]["height"]
            for corners, chain in zip(dumped["paths"], mapped["chains"]):
                centres = [[f["canvas"]["x"] + (x - 0.5) * f["cell"], f["canvas"]["y"] + (height - y + 0.5) * f["cell"]] for x, y in corners]
                inside_canvas = [point for point in chain["points"] if f["canvas"]["x"] < point[0] < f["canvas"]["x"] + f["canvas"]["width"]]
                self.assertEqual(inside_canvas, centres, (name, area))
                self.assertEqual(len(chain["points"]), len(corners) + 2 * (len(corners) // 2 - 1))
                self.assertEqual(len(chain["turns"]), len(corners) // 2 - 1)
                segments(chain["points"])
                for turn, start in zip(chain["turns"], centres[2::2]):
                    self.assertEqual(turn["y"], start[1])
                    self.assertEqual(turn["direction"], 1 if turn["x"] < f["canvas"]["x"] + f["canvas"]["width"] / 2 else -1)
                    if width > 1:
                        self.assertFalse(f["canvas"]["x"] <= turn["x"] <= f["canvas"]["x"] + f["canvas"]["width"])

    def test_the_path_of_a_leg_whose_rows_are_not_neighbours_joins_them_in_chain_order(self):
        dumped = self.dumps["pins the board lacks, rows apart"]
        self.assertEqual(dumped["mapping"]["legs"][0]["strips"], [10, 8, 6])
        self.assertEqual(dumped["paths"][0], [[30, 10], [1, 10], [1, 8], [30, 8], [30, 6], [1, 6]])
        chain = dumped["mapped"][0]["chains"][0]
        f = dumped["mapped"][0]["fit"]
        ys = [point[1] for point in chain["points"]]
        self.assertEqual(sorted(set(ys)), [f["canvas"]["y"] + (11 - y + 0.5) * f["cell"] for y in (10, 8, 6)])
        self.assertEqual(dumped["runs"][0], [{"top": 10, "bottom": 10}, {"top": 8, "bottom": 8}, {"top": 6, "bottom": 6}])


class WithoutABrowser(unittest.TestCase):
    def test_the_layout_script_runs_in_the_javascript_shell(self):
        done = subprocess.run([str(JSC), str(WEB / "layout.js"), "-e", "print(typeof OdrigLayout.position, typeof window, typeof document)"], capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout.strip(), done.stderr), (0, "function undefined undefined", ""))

    def test_the_position_rule_is_written_in_the_layout_script_only(self):
        users = sorted(path.name for path in WEB.iterdir() if path.suffix in (".js", ".html") and "first_led" in path.read_text(encoding="utf-8"))
        self.assertEqual(users, ["layout.js"])
        view = (WEB / "view.js").read_text(encoding="utf-8")
        self.assertIn("OdrigLayout.position(m, leg[1], n)", view)

    def test_the_view_takes_the_spans_the_marks_and_the_strips_of_column_legs_from_the_layout_script(self):
        view = (WEB / "view.js").read_text(encoding="utf-8")
        for taken in ("OdrigLayout.legSpans(m, f)", "OdrigLayout.marks(m.height)", "OdrigLayout.marks(m.width)", "OdrigLayout.strips(m, i)", "f.numberTop && f.numberBottom"):
            self.assertIn(taken, view)


if __name__ == "__main__":
    unittest.main()

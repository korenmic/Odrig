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

WEB = support.ROOT / "emulator" / "web"
SCRIPTS = (WEB / "board.js", WEB / "layout.js", support.ROOT / "tests" / "emulator" / "js" / "dump_layout.js")
VIEW_SCRIPTS = (support.ROOT / "tests" / "emulator" / "js" / "dump_view.js", "--", WEB / "board.js", WEB / "layout.js", WEB / "view.js")

# The colours of the first twelve legs of a file.
COLOURS = "#ff6b6b #ffa94d #ffd43b #a9e34b #51cf66 #38d9a9 #3bc9db #4dabf7 #748ffc #b197fc #f783ac #ced4da".split()


def dump(text, **questions):
    """What the page's layout script computes for a mapping file, run in the JavaScript
    shell without a browser."""
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder, "mapping.json")
        path.write_text(text, encoding="utf-8")
        done = subprocess.run([*support.js_shell(), *map(str, SCRIPTS), "--", str(path), json.dumps(questions)], capture_output=True, text=True)
    if done.returncode != 0 or done.stderr:
        raise AssertionError(f"the JavaScript shell ended with status {done.returncode}:\n{done.stdout[-600:]}\n{done.stderr[-600:]}")
    return json.loads(done.stdout)


def drawn(text, areas, pointed=0):
    """What the page's view script draws for a mapping file in its mapping view, for each
    drawing area, run in the JavaScript shell with a stand-in for the document.
    `pointed` is the index of the leg that is pointed at once the drawing is made."""
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder, "mapping.json")
        path.write_text(text, encoding="utf-8")
        done = subprocess.run([*support.js_shell(), *map(str, VIEW_SCRIPTS), str(path), json.dumps(areas), str(pointed)], capture_output=True, text=True)
    if done.returncode != 0 or done.stderr:
        raise AssertionError(f"the JavaScript shell ended with status {done.returncode}:\n{done.stdout[-600:]}\n{done.stderr[-600:]}")
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
        self.assertLessEqual({"legs-2", "ten-row-legs", "left-start", "two-and-four-rows", "another-order", "one-led"}, set(self.texts))
        apart_rows = [leg.strips for leg in self.canvases["another-order"].legs]
        self.assertEqual(apart_rows, [(2, 4), (1, 5, 3)])

    def test_the_mappings_are_of_both_kinds_with_the_target_file_and_made_up_column_leg_files(self):
        columns = {name for name, canvas in self.canvases.items() if canvas.kind == mapping.COLUMNS}
        self.assertEqual(columns, {"legs-20", "top-start", "two-and-four-columns", "columns-apart", "one-led-column", "crossed-columns"})
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
                self.assertEqual([(leg["leg"], leg["pin"], leg["first_led"], tuple(leg["strips"]), leg["count"], tuple(leg.get("starts", ()))) for leg in read["legs"]],
                                 [(leg.leg, leg.pin, leg.first_led, tuple(leg.strips), strip_length * len(leg.strips), leg.starts or ()) for leg in canvas.legs])
                for leg, listed in zip(read["legs"], canvas.legs):
                    self.assertEqual(sorted(leg), sorted(["count", "first_led", "leg", "pin", "strips"] + (["starts"] if listed.starts else [])))

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
                    # The columns of a leg start at the two ends in turn, the first at the first LED's,
                    # or each at the end its `starts` names.
                    self.assertEqual([column["start"] for column in columns],
                                     list(leg.starts) if leg.starts else
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

    def sections_of_the_mapping_document(self):
        """The section of the bench build and the section of the target build, by the name
        of the mapping file each one draws."""
        text = (support.ROOT / "docs" / "mapping.md").read_text(encoding="utf-8")
        sections = {"legs-2": text.split("## Today's build")[1].split("\n## ")[0], "legs-20": text.split("## Target build")[1].split("\n## ")[0]}
        self.assertEqual((self.canvases["legs-2"].kind, self.canvases["legs-20"].kind), (mapping.ROWS, mapping.COLUMNS))
        for name, section in sections.items():
            self.assertIn(f"(../mapping/{name}.json)", section)
        return sections

    def test_strips_gives_the_end_numbers_of_the_drawings_in_the_mapping_document(self):
        for name, section in self.sections_of_the_mapping_document().items():
            canvas = self.canvases[name]
            # A line of a drawing is one strip: a row, with the LED numbers at x = 1 and at
            # x = W, or a column lying down, with the LED numbers at y = 1 and at y = H.
            across, low_end, count = ("y", "left", canvas.height) if canvas.kind == mapping.ROWS else ("x", "bottom", canvas.width)
            drawn = re.findall(r"(?m)^" + across + r"=([0-9]+) +\| +([0-9]+) (<-+|-+>) +([0-9]+) \|(?: +leg ([0-9]+), pin ([0-9]+))?$", section)
            self.assertEqual(len(drawn), count, name)
            self.assertEqual(len(re.findall(r"(?m)^[xy]=[0-9]+ +\|", section)), count, name)
            by_place = {}
            for index, strips in enumerate(self.dumps[name]["strips"]):
                for place, strip in enumerate(strips):
                    by_place[strip[across]] = (index, place, strip)
            self.assertEqual([int(place) for place, *_ in drawn], sorted(by_place, reverse=canvas.kind == mapping.ROWS), name)
            for place, at_the_low_end, arrow, at_the_far_end, leg, pin in drawn:
                index, place_in_the_leg, strip = by_place[int(place)]
                self.assertEqual(strip["start"] == low_end, arrow.endswith(">"), (name, place))
                wanted = (strip["first"], strip["last"]) if strip["start"] == low_end else (strip["last"], strip["first"])
                self.assertEqual(wanted, (int(at_the_low_end), int(at_the_far_end)), (name, place))
                # The leg and the pin stand beside the first strip of a leg and nowhere else.
                self.assertEqual(bool(leg), place_in_the_leg == 0, (name, place))
                if leg:
                    self.assertEqual((canvas.legs[index].leg, canvas.legs[index].pin), (int(leg), int(pin)))

    def test_strips_gives_the_end_numbers_of_the_tables_in_the_mapping_document(self):
        for name, section in self.sections_of_the_mapping_document().items():
            canvas = self.canvases[name]
            self.assertIn("| Rows (y) |" if canvas.kind == mapping.ROWS else "| Columns (x) |", section)
            table = re.findall(r"(?m)^\| ([0-9]+) \| ([0-9]+) \| ([0-9, ]+) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \|$", section)
            self.assertEqual(len(table), len(canvas.legs), name)
            for (leg, pin, listed_strips, *numbers), listed, strips, places in zip(table, canvas.legs, self.dumps[name]["strips"], self.dumps[name]["positions"]):
                self.assertEqual((int(leg), int(pin), [int(strip) for strip in listed_strips.split(",")]), (listed.leg, listed.pin, list(listed.strips)))
                ends = [number for strip in strips for number in (strip["first"], strip["last"])]
                self.assertEqual(ends, [1, 60, 61, 120, 121, 180])
                pairs = list(zip(map(int, numbers[0::2]), map(int, numbers[1::2])))
                self.assertEqual([tuple(places[number - 1]) for number in ends], pairs, (name, leg))

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

    def test_a_first_led_at_the_top_reverses_every_column_of_that_leg_of_the_target_file_and_moves_no_other_led(self):
        listed = json.loads(self.texts["legs-20"])
        self.assertEqual((listed["legs"][6]["leg"], listed["legs"][6]["first_led"], listed["legs"][6]["columns"]), (7, "bottom", [19, 20, 21]))
        listed["legs"][6]["first_led"] = "top"
        moved = dump(json.dumps(listed))["positions"]
        plain = self.dumps["legs-20"]["positions"]
        self.assertEqual(len(moved), 20)
        for index, (now, before) in enumerate(zip(moved, plain)):
            if index != 6:
                self.assertEqual(now, before, f"an LED of leg {index + 1} moved")
                continue
            self.assertEqual(len(now), 180)
            for column in range(3):
                self.assertEqual(now[60 * column:60 * column + 60], before[60 * column:60 * column + 60][::-1], f"column {column} of leg 7")
            # A column of 60 has no LED in its middle, so every LED of the leg moved.
            self.assertTrue(all(place != old for place, old in zip(now, before)))

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
        cls.dump = dump(core_support.mapping_texts()["ten-row-legs"])

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
        cls.ten = dump(texts["ten-row-legs"], areas=cls.areas)
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

    def test_the_mappings_are_the_target_file_and_the_five_made_up_column_leg_files(self):
        self.assertEqual(self.names, ["legs-20", "top-start", "two-and-four-columns", "columns-apart", "one-led-column", "crossed-columns"])
        self.assertEqual({name: dumped["mapping"]["kind"] for name, dumped in self.dumps.items()}, dict.fromkeys(self.names, "columns"))
        self.assertEqual({name: (dumped["mapping"]["width"], dumped["mapping"]["height"]) for name, dumped in self.dumps.items()},
                         {"legs-20": (60, 60), "top-start": (3, 7), "two-and-four-columns": (6, 5), "columns-apart": (5, 4), "one-led-column": (1, 1),
                          "crossed-columns": (5, 4)})

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
        self.assertEqual(feeds, {"legs-20": "bottom", "top-start": "top", "two-and-four-columns": "bottom", "columns-apart": "bottom", "one-led-column": "top",
                                 "crossed-columns": "bottom"})
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
        cls.ten = dump(cls.texts["ten-row-legs"], pins=list(range(0, 12)) + [48, 99, 255], areas=[[1280, 800]])

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
            "ten-row-legs": texts["ten-row-legs"],
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
        arrangements = {area: mapped["fit"]["arrangement"] for name, area, _, mapped in self.each() if name == "ten-row-legs"}
        self.assertEqual(arrangements, {(1280, 800): "beside", (1280, 546): "beside", (1100, 600): "beside", (900, 465): "below", (756, 400): "below", (1920, 1000): "beside"})
        cells = {area: mapped["fit"]["cell"] for name, area, _, mapped in self.each() if name == "ten-row-legs"}
        self.assertEqual((cells[(1280, 800)], cells[(1280, 546)]), (12, 12))
        self.assertGreaterEqual(cells[(900, 465)], 9)
        self.assertGreaterEqual(cells[(1100, 600)], 9)
        self.assertGreaterEqual(cells[(1920, 1000)], 20)
        below = next(mapped["fit"] for name, area, _, mapped in self.each() if name == "ten-row-legs" and area == (900, 465))
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
        mapped = self.dumps["ten-row-legs"]["mapped"][0]
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

    def test_the_lines_of_the_ten_leg_and_the_two_leg_mapping_cross_only_where_the_pins_are_out_of_order(self):
        for area, mapped in zip(self.areas, self.dumps["ten-row-legs"]["mapped"]):
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


def upright_mappings():
    """The column-leg mappings the mapping view is drawn for, by name: the target file, the
    made-up ones of every suite, and files for what those leave out."""
    texts = core_support.mapping_texts()
    target = json.loads(texts["legs-20"])

    def started(listed, first_leds):
        return json.dumps({**listed, "legs": [{**leg, "first_led": first_leds.get(leg["leg"], leg["first_led"])} for leg in listed["legs"]]})

    # Pins the board lacks, pads in both rows, columns that are not neighbours and not in
    # order, and two legs that start at the top.
    odd = json.loads(column_text(8, [
        (1, 99, "bottom", [1, 2, 3, 4]), (2, 1, "bottom", [8, 7, 6, 5]), (3, 21, "top", [9, 10, 11, 12]), (4, 200, "bottom", [13, 15, 14, 16]),
        (5, 14, "bottom", [17, 18, 19, 20]), (6, 48, "bottom", [24, 23, 22, 21]), (7, 4, "top", [25, 26, 27, 28]), (8, 0, "bottom", [29, 31, 30, 32]),
        (9, 2, "bottom", [33, 34, 35, 36]), (10, 47, "bottom", [37, 38, 39, 40]), (11, 3, "bottom", [41, 42, 43, 44]), (12, 46, "bottom", [45, 46, 47, 48])]))
    # Sixteen legs, every one on a pad of the right row of the board, in no order.
    right_row = [21, 1, 40, 0, 2, 47, 42, 35, 48, 19, 41, 36, 20, 45, 39, 38]
    mappings = {name: texts[name] for name in ["legs-20", *core_support.column_mapping_texts()]}
    mappings["a leg of the target from the top"] = started(target, {7: "top"})
    mappings["the target from the top"] = started(target, dict.fromkeys(range(1, 21), "top"))
    mappings["pins the board lacks, columns apart"] = json.dumps(odd)
    mappings["the same, turned over"] = started(odd, {leg["leg"]: {"bottom": "top", "top": "bottom"}[leg["first_led"]] for leg in odd["legs"]})
    mappings["the right row"] = column_text(6, [(index + 1, pin, "bottom", [3 * index + 1, 3 * index + 2, 3 * index + 3]) for index, pin in enumerate(right_row)])
    return mappings


class UprightCase(unittest.TestCase):
    """What the tests of the mapping view of a column-leg file share: the mappings, the
    drawing areas, and what the layout script gives for each."""

    AREAS = [[1280, 546], [1920, 1000], [1100, 600], [756, 546], [600, 546]]
    # The files as wide as the target: 48 columns or more.
    LARGE = ("legs-20", "a leg of the target from the top", "the target from the top", "pins the board lacks, columns apart", "the same, turned over", "the right row")
    dumps = None

    @classmethod
    def setUpClass(cls):
        if UprightCase.dumps is None:
            UprightCase.dumps = {name: dump(text, areas=cls.AREAS) for name, text in upright_mappings().items()}

    def each(self):
        for name, dumped in self.dumps.items():
            for area, mapped in zip(self.AREAS, dumped["mapped"]):
                yield name, tuple(area), dumped, mapped

    def target(self, area):
        return self.dumps["legs-20"]["mapped"][self.AREAS.index(list(area))]

    @staticmethod
    def down(f):
        """1 where the level channel lies below the canvas, -1 where it lies above it."""
        return 1 if f["feed"] == "bottom" else -1

    @classmethod
    def to_channel(cls, f):
        """1 where the level channel lies below the board, -1 where it lies above it."""
        return cls.down(f) if f["arrangement"] == "wide" else -cls.down(f)

    @staticmethod
    def on_level_track(f, wire):
        """The piece of a line that lies on its level track, as (y, the x where the line
        comes to the track, the x where it leaves it for its first LED)."""
        level, points = f["level"], wire["points"]
        found = [index for index, (first, second) in enumerate(zip(points, points[1:]))
                 if first[1] == second[1] and level["y"] < first[1] < level["y"] + level["height"]]
        if len(found) != 1:
            raise AssertionError(f"the line of leg index {wire['leg']} has {len(found)} pieces in the level channel")
        return points[found[0]][1], points[found[0]][0], points[found[0] + 1][0]

    @classmethod
    def nearness(cls, f, wire):
        """A number that is larger for the pad nearer to the level channel."""
        return cls.to_channel(f) * wire["pad"]["y"]


class UprightMapping(UprightCase):
    """The mapping view of a column-leg file: the arrangement, the cells and the parts."""

    PARTS = ("header", "legBand", "legWords", "yLabel", "numberTop", "numberBottom", "canvas", "level", "upright", "nearLabel", "board", "farZone")

    def test_the_mappings_are_the_target_file_made_up_ones_and_ones_for_what_those_leave_out(self):
        self.assertEqual(list(self.dumps), ["legs-20", "top-start", "two-and-four-columns", "columns-apart", "one-led-column", "crossed-columns", "a leg of the target from the top",
                                            "the target from the top", "pins the board lacks, columns apart", "the same, turned over", "the right row"])
        self.assertEqual({dumped["mapping"]["kind"] for dumped in self.dumps.values()}, {"columns"})
        self.assertEqual({name: dumped["side"] for name, dumped in self.dumps.items()}, {
            "legs-20": "bottom", "top-start": "top", "two-and-four-columns": "bottom", "columns-apart": "bottom", "one-led-column": "top", "crossed-columns": "bottom",
            "a leg of the target from the top": "bottom", "the target from the top": "top", "pins the board lacks, columns apart": "bottom",
            "the same, turned over": "top", "the right row": "bottom"})
        board = self.dumps["legs-20"]["board"]
        kinds = {}
        for name, dumped in self.dumps.items():
            pins = [str(leg["pin"]) for leg in dumped["mapping"]["legs"]]
            kinds[name] = (sum(pin in board["left"] for pin in pins), sum(pin in board["right"] for pin in pins), sum(pin not in board["left"] + board["right"] for pin in pins))
        self.assertEqual(kinds["legs-20"], (16, 4, 0))
        self.assertEqual(kinds["pins the board lacks, columns apart"], (4, 6, 2))
        self.assertEqual(kinds["the right row"], (0, 16, 0))
        self.assertEqual(kinds["one-led-column"], (0, 0, 1))
        for name in self.LARGE:
            self.assertGreaterEqual(self.dumps[name]["mapping"]["width"], 48)

    def test_the_target_file_has_the_board_beside_the_canvas_in_a_wide_area_and_below_it_in_a_narrow_one(self):
        fits = {tuple(area): self.target(area)["fit"] for area in self.AREAS}
        self.assertEqual({area: f["arrangement"] for area, f in fits.items()},
                         {(1280, 546): "wide", (1920, 1000): "wide", (1100, 600): "wide", (756, 546): "narrow", (600, 546): "narrow"})
        self.assertEqual({area: f["cell"] for area, f in fits.items()}, {(1280, 546): 9, (1920, 1000): 12, (1100, 600): 9, (756, 546): 9, (600, 546): 7})
        for area, f in fits.items():
            self.assertEqual(f["view"], "mapping")
            self.assertEqual(f["width"], area[0], "the drawing is wider than its area, so the stage would scroll sideways")
            self.assertLessEqual(f["content"]["width"], area[0])
            canvas, board = f["canvas"], f["board"]
            if f["arrangement"] == "wide":
                self.assertGreaterEqual(board["x"], canvas["x"] + canvas["width"])
                self.assertLess(board["y"], canvas["y"] + canvas["height"])
                self.assertGreater(board["y"] + board["height"], canvas["y"])
            else:
                self.assertGreaterEqual(board["y"], canvas["y"] + canvas["height"])
                self.assertLess(board["x"], canvas["x"] + canvas["width"])
        for area in ((1280, 546), (756, 546)):
            self.assertGreaterEqual(fits[area]["cell"], 9)
        # With cells of 9 pixels the drawing is higher than an area 546 high, and the
        # stage scrolls up and down. An area of 1920 x 1000 holds the whole drawing.
        self.assertGreater(fits[(1280, 546)]["height"], 546)
        self.assertGreater(fits[(756, 546)]["height"], 546)
        self.assertEqual((fits[(1920, 1000)]["width"], fits[(1920, 1000)]["height"]), (1920, 1000))

    def test_the_board_stands_beside_the_canvas_where_cells_of_9_pixels_fit_the_width_with_it(self):
        edge = dump(upright_mappings()["legs-20"], areas=[[960, 546], [959, 546], [968, 2000]])["mapped"]
        self.assertEqual([(mapped["fit"]["arrangement"], mapped["fit"]["cell"]) for mapped in edge], [("wide", 9), ("narrow", 9), ("wide", 9)])
        self.assertEqual(edge[0]["fit"]["content"]["width"], 960)
        self.assertEqual(edge[0]["fit"]["board"]["pitch"], 10)
        for name, area, dumped, mapped in self.each():
            f = mapped["fit"]
            self.assertIn(f["arrangement"], ("wide", "narrow"))
            if f["arrangement"] == "wide":
                self.assertGreaterEqual(f["cell"], 9, (name, area))
        arrangements = {name: [mapped["fit"]["arrangement"] for mapped in dumped["mapped"]] for name, dumped in self.dumps.items()}
        for name, found in arrangements.items():
            # The small files have room for the board beside the canvas in every area.
            self.assertEqual(found, ["wide", "wide", "wide", "narrow", "narrow"] if name in self.LARGE else ["wide"] * 5, name)

    def test_the_cell_is_the_largest_that_fits_both_ways_or_the_largest_up_to_9_that_fits_the_width(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                width, height = dumped["mapping"]["width"], dumped["mapping"]["height"]
                self.assertTrue(4 <= f["cell"] <= 28)
                self.assertEqual((f["canvas"]["width"], f["canvas"]["height"]), (width * f["cell"], height * f["cell"]))
                self.assertEqual((f["width"], f["height"]), (max(area[0], f["content"]["width"]), max(area[1], f["content"]["height"])))
                # No drawing is wider than its area, and one that is higher has cells of 9 at most.
                self.assertLessEqual(f["content"]["width"], area[0])
                if f["content"]["height"] > area[1]:
                    self.assertLessEqual(f["cell"], 9)
                if f["cell"] < 9:
                    self.assertEqual(f["arrangement"], "narrow")
                    self.assertGreater(f["content"]["width"] + width, area[0], "cells one pixel larger would fit the width")
        cells = {name: [mapped["fit"]["cell"] for mapped in dumped["mapped"]] for name, dumped in self.dumps.items()}
        self.assertEqual(cells["a leg of the target from the top"], cells["legs-20"])
        self.assertEqual(cells["the target from the top"], cells["legs-20"])
        self.assertEqual(cells["top-start"], [28] * 5)
        self.assertEqual(cells["pins the board lacks, columns apart"][3:], [9, 9])
        # Where both arrangements are too wide for the area, the cells are 4 pixels and the
        # drawing is wider than the area.
        small = dump(upright_mappings()["legs-20"], areas=[[300, 546]])["mapped"][0]["fit"]
        self.assertEqual((small["arrangement"], small["cell"]), ("narrow", 4))
        self.assertGreater(small["width"], 300)

    def test_every_part_is_inside_the_drawing_and_the_board_is_apart_from_the_canvas_and_both_channels(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                missing = sorted({"view", "arrangement", "feed", "cell", "width", "height", "content", "gutters", "reaches", *self.PARTS} - set(f))
                self.assertEqual(missing, [], "the fit lacks parts of the mapping view of a column-leg file")
                whole = {"x": 0, "y": 0, "width": f["width"], "height": f["height"]}
                for part in (*f["gutters"], *(f[part] for part in self.PARTS)):
                    self.assertTrue(inside(part, whole), part)
                    self.assertTrue(inside(part, f["content"]), part)
                    self.assertGreater(part["width"], 0)
                    self.assertGreater(part["height"], 0)
                for part in ("canvas", "level", "upright", "nearLabel", "farZone", "numberTop", "numberBottom", "legBand", "header", "yLabel"):
                    self.assertTrue(apart(f["board"], f[part]), f"the board is not apart from {part}")
                for part in ("level", "upright", "nearLabel", "farZone", "numberTop", "numberBottom", "legBand", "yLabel"):
                    self.assertTrue(apart(f["canvas"], f[part]), f"the canvas is not apart from {part}")
                self.assertTrue(apart(f["level"], f["upright"]))
                for band in ("numberTop", "numberBottom", "legBand", "header"):
                    self.assertTrue(apart(f["level"], f[band]), band)
                self.assertGreaterEqual(f["board"]["pitch"], 10)
                self.assertLessEqual(f["board"]["pitch"], 20)
                self.assertEqual((f["board"]["width"], f["board"]["height"]), (math.floor(11.5 * f["board"]["pitch"] + 0.5), math.floor(26.25 * f["board"]["pitch"] + 0.5)))

    def test_the_number_bands_are_always_drawn_and_hold_the_numbers_clear_of_the_turns(self):
        for name, area, dumped, mapped in self.each():
            f = mapped["fit"]
            canvas, top, bottom = f["canvas"], f["numberTop"], f["numberBottom"]
            self.assertEqual((top["x"], top["width"], top["y"] + top["height"]), (canvas["x"], canvas["width"], canvas["y"]), (name, area))
            self.assertEqual((bottom["x"], bottom["width"], bottom["y"]), (canvas["x"], canvas["width"], canvas["y"] + canvas["height"]), (name, area))
            self.assertEqual(top["height"], bottom["height"])
            self.assertGreaterEqual(top["height"], 28)
        # Also where the cells are under 9 pixels, at which the LEDs view leaves them out.
        small = dump(upright_mappings()["legs-20"], areas=[[600, 546]])
        self.assertEqual((small["mapped"][0]["fit"]["cell"], small["fits"][0]["cell"]), (7, 8))
        self.assertIsNotNone(small["mapped"][0]["fit"]["numberTop"])
        self.assertIsNone(small["fits"][0]["numberTop"])

    def test_a_track_takes_7_pixels_and_a_channel_5_more_at_each_side(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f, wires = mapped["fit"], mapped["wires"]
                legs = len(dumped["mapping"]["legs"])
                self.assertEqual(f["level"]["height"], 7 * legs + 10)
                tracks = [reach["upright"] for reach in f["reaches"] if "upright" in reach]
                self.assertEqual(sorted(tracks), list(range(len(tracks))))
                self.assertEqual(f["upright"]["width"], 7 * len(tracks) + 10)
                self.assertEqual(sorted(reach["level"] for reach in f["reaches"]), list(range(legs)))
                # Every leg has a level track of its own, 7 pixels from the next, the first
                # 5 pixels and half a track inside the channel.
                levels = sorted(self.on_level_track(f, wire)[0] for wire in wires)
                self.assertEqual(levels, [f["level"]["y"] + 5 + 3.5 + 7 * track for track in range(legs)])
                uprights = sorted({wire["points"][index][0] for wire, reach in zip(wires, f["reaches"]) if "upright" in reach
                                   for index in range(len(wire["points"])) if f["upright"]["x"] < wire["points"][index][0] < f["upright"]["x"] + f["upright"]["width"]})
                self.assertEqual(uprights, [f["upright"]["x"] + 5 + 3.5 + 7 * track for track in range(len(tracks))])
        for area in self.AREAS:
            f = self.target(area)["fit"]
            self.assertEqual((f["level"]["height"], f["upright"]["width"]), (150, 136), area)
            self.assertEqual(sum("upright" in reach for reach in f["reaches"]), 18)

    def test_the_wide_arrangement_has_the_level_channel_along_the_feed_edge_and_on_under_the_board(self):
        seen = set()
        for name, area, dumped, mapped in self.each():
            f = mapped["fit"]
            if f["arrangement"] != "wide":
                continue
            seen.add(f["feed"])
            with self.subTest(name=name, area=area):
                canvas, level, upright, board, far = f["canvas"], f["level"], f["upright"], f["board"], f["farZone"]
                # From left to right: the marks of the rows, the canvas, the upright channel,
                # the names of the legs, the board and the far zone.
                across = [f["yLabel"], canvas, upright, f["nearLabel"], board, far]
                for first, second in zip(across, across[1:]):
                    self.assertEqual(first["x"] + first["width"], second["x"])
                self.assertEqual((level["x"], level["x"] + level["width"]), (canvas["x"], far["x"] + far["width"]))
                feed_band = f["numberBottom"] if f["feed"] == "bottom" else f["numberTop"]
                if f["feed"] == "bottom":
                    self.assertEqual(level["y"], feed_band["y"] + feed_band["height"])
                    self.assertLessEqual(board["y"] + board["height"], level["y"])
                    self.assertLessEqual(far["y"] + far["height"], level["y"])
                    self.assertEqual(upright["y"] + upright["height"], level["y"])
                else:
                    self.assertEqual(level["y"] + level["height"], feed_band["y"])
                    self.assertGreaterEqual(board["y"], level["y"] + level["height"])
                    self.assertGreaterEqual(far["y"], level["y"] + level["height"])
                    self.assertEqual(upright["y"], level["y"] + level["height"])
                self.assertLessEqual(upright["y"], min(board["y"], canvas["y"]))
                self.assertGreaterEqual(upright["y"] + upright["height"], max(board["y"] + board["height"], canvas["y"] + canvas["height"]))
        self.assertEqual(seen, {"bottom", "top"})

    def test_the_narrow_arrangement_has_the_level_channel_between_the_canvas_and_the_board(self):
        seen = set()
        for name, area, dumped, mapped in self.each():
            f = mapped["fit"]
            if f["arrangement"] != "narrow":
                continue
            seen.add(f["feed"])
            with self.subTest(name=name, area=area):
                canvas, level, upright, board, far = f["canvas"], f["level"], f["upright"], f["board"], f["farZone"]
                # The board stands at the left, the upright channel at its left, and the
                # canvas begins to the right of the upright channel.
                across = [upright, f["nearLabel"], board, far]
                for first, second in zip(across, across[1:]):
                    self.assertEqual(first["x"] + first["width"], second["x"])
                self.assertEqual(canvas["x"], upright["x"] + upright["width"])
                self.assertEqual(f["yLabel"]["x"] + f["yLabel"]["width"], canvas["x"])
                self.assertGreaterEqual(f["yLabel"]["x"], f["content"]["x"] + f["gutters"][0]["width"])
                self.assertEqual(level["x"], upright["x"])
                self.assertGreaterEqual(level["x"] + level["width"], max(canvas["x"] + canvas["width"], far["x"] + far["width"]))
                if f["feed"] == "bottom":
                    below = f["numberBottom"]
                    self.assertEqual(level["y"], below["y"] + below["height"])
                    self.assertGreater(board["y"], level["y"] + level["height"])
                    self.assertEqual(upright["y"], level["y"] + level["height"])
                    self.assertGreaterEqual(upright["y"] + upright["height"], board["y"] + board["height"])
                else:
                    above = f["numberTop"]
                    self.assertEqual(level["y"] + level["height"], above["y"])
                    self.assertLess(board["y"] + board["height"], level["y"])
                    self.assertEqual(upright["y"] + upright["height"], level["y"])
                    self.assertLessEqual(upright["y"], board["y"])
                # Every first LED is to the right of every upright track.
                tracks = [point[0] for wire in mapped["wires"] for point in wire["points"] if point[0] < upright["x"] + upright["width"]]
                for wire in mapped["wires"]:
                    self.assertGreater(self.on_level_track(f, wire)[2], max(tracks, default=0))
                    self.assertGreaterEqual(wire["points"][-1][0], canvas["x"])
        self.assertEqual(seen, {"bottom", "top"})

    def test_the_leg_band_and_the_header_are_on_the_side_of_the_canvas_away_from_the_feed_edge(self):
        for name, area, dumped, mapped in self.each():
            f = mapped["fit"]
            canvas, band, header, words = f["canvas"], f["legBand"], f["header"], f["legWords"]
            self.assertEqual(f["feed"], dumped["side"])
            if f["feed"] == "bottom":
                self.assertLessEqual(header["y"] + header["height"], band["y"])
                self.assertEqual(band["y"] + band["height"], f["numberTop"]["y"])
            else:
                self.assertEqual(f["numberBottom"]["y"] + f["numberBottom"]["height"], band["y"])
                self.assertLessEqual(band["y"] + band["height"], header["y"])
            for across in (band, header):
                self.assertEqual((across["x"], across["width"]), (canvas["x"], canvas["width"]))
            self.assertEqual((words["y"], words["height"], words["x"] + words["width"]), (band["y"], band["height"], band["x"]))
            self.assertEqual((f["yLabel"]["y"], f["yLabel"]["height"]), (canvas["y"], canvas["height"]))

    def test_a_file_whose_legs_all_start_at_the_top_is_drawn_turned_over_all_but_the_board(self):
        upright = self.dumps["legs-20"]["mapped"]
        turned = self.dumps["the target from the top"]["mapped"]
        swapped = {"numberTop": "numberBottom", "numberBottom": "numberTop"}
        for area, first, second in zip(self.AREAS, upright, turned):
            with self.subTest(area=area):
                f, g = first["fit"], second["fit"]
                self.assertEqual((f["feed"], g["feed"]), ("bottom", "top"))
                self.assertEqual((g["arrangement"], g["cell"], g["content"], g["board"]["pitch"]), (f["arrangement"], f["cell"], f["content"], f["board"]["pitch"]))
                content = f["content"]
                for part in ("header", "legBand", "legWords", "yLabel", "numberTop", "numberBottom", "canvas", "level", "upright", "farZone"):
                    theirs = g[swapped.get(part, part)]
                    self.assertEqual((theirs["x"], theirs["width"], theirs["height"]), (f[part]["x"], f[part]["width"], f[part]["height"]), part)
                    self.assertEqual(theirs["y"] - content["y"], content["y"] + content["height"] - f[part]["y"] - f[part]["height"], part)
                canvas, level, board = g["canvas"], g["level"], g["board"]
                # The level channel lies above the canvas and the leg band below it.
                self.assertLess(level["y"], canvas["y"])
                self.assertGreater(g["legBand"]["y"], canvas["y"])
                if g["arrangement"] == "narrow":
                    self.assertLess(board["y"] + board["height"], level["y"])
                # The board is the board, with its antenna end up: the pad of a pin is as
                # far below the top of the board as in every drawing.
                for wire, other in zip(second["wires"], first["wires"]):
                    self.assertEqual((wire["pad"]["row"], wire["pad"]["index"]), (other["pad"]["row"], other["pad"]["index"]))
                    self.assertEqual(wire["pad"]["y"] - board["y"], other["pad"]["y"] - f["board"]["y"])
                    self.assertEqual(wire["pad"]["y"] - board["y"], (2.75 + wire["pad"]["index"] + 0.5) * board["pitch"])
                    self.assertEqual(wire["pad"]["x"] - board["x"], other["pad"]["x"] - f["board"]["x"])
                for wire, centre in zip(second["wires"], second["firsts"]):
                    self.assertEqual(wire["points"][-1], [centre[0], canvas["y"] - 2])
        for name in ("top-start", "one-led-column", "the same, turned over"):
            for mapped in self.dumps[name]["mapped"]:
                f = mapped["fit"]
                self.assertEqual(f["feed"], "top")
                self.assertLess(f["level"]["y"], f["canvas"]["y"])
                self.assertGreater(f["legBand"]["y"], f["canvas"]["y"])


class UprightLines(UprightCase):
    """The lines from the pads of the board to the first LEDs of a column-leg file, and
    the chains of its legs."""

    def crossings(self, wires):
        """For each pair of lines that cross, by the indexes of their legs, how often."""
        found = {}
        for index, first in enumerate(wires):
            for second in wires[index + 1:]:
                count = meetings(first["points"], second["points"])[0]
                if count:
                    found[(first["leg"], second["leg"])] = count
        return found

    def test_every_line_runs_from_the_pad_of_its_pin_to_the_first_led_of_its_chain(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f, legs, board = mapped["fit"], dumped["mapping"]["legs"], dumped["board"]
                canvas = f["canvas"]
                self.assertEqual([wire["leg"] for wire in mapped["wires"]], list(range(len(legs))))
                for wire, leg, first in zip(mapped["wires"], legs, mapped["firsts"]):
                    points = wire["points"]
                    self.assertEqual(points[0], [wire["pad"]["x"], wire["pad"]["y"]])
                    # The line ends at the first LED, outside the canvas, with an upright piece.
                    self.assertEqual(points[-1][0], first[0])
                    self.assertEqual(points[-2][0], first[0])
                    self.assertLessEqual(abs(points[-1][1] - first[1]), f["cell"] / 2 + 2)
                    self.assertFalse(canvas["y"] <= points[-1][1] <= canvas["y"] + canvas["height"])
                    # Level and upright pieces, none without a length.
                    segments(points)
                    for before, after in zip(points, points[1:]):
                        self.assertNotEqual(before, after)
                    place = next(((row, index) for row in ("left", "right") for index, label in enumerate(board[row]) if label == str(leg["pin"])), None)
                    if place is None:
                        self.assertEqual((wire["kind"], wire["pad"]["row"], wire["pad"]["index"]), ("off", None, None))
                    else:
                        self.assertEqual((wire["pad"]["row"], wire["pad"]["index"]), place)
                        self.assertEqual(wire["kind"], "near" if place[0] == "left" else "far")
                        inset = 0.5625 * f["board"]["pitch"]
                        self.assertEqual(wire["pad"]["x"], f["board"]["x"] + inset if place[0] == "left" else f["board"]["x"] + f["board"]["width"] - inset)
                        self.assertEqual(wire["pad"]["y"], f["board"]["y"] + (2.75 + place[1] + 0.5) * f["board"]["pitch"])

    def test_a_line_runs_level_to_its_upright_track_along_it_to_its_level_track_and_along_that_to_its_first_led(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                upright, far, board = f["upright"], f["farZone"], f["board"]
                for wire, reach in zip(mapped["wires"], f["reaches"]):
                    points = wire["points"]
                    level_y, comes, leaves = self.on_level_track(f, wire)
                    self.assertEqual(reach["kind"], wire["kind"])
                    if wire["kind"] == "far":
                        # First level to its loop in the far zone, at the right of the board.
                        self.assertEqual(points[1][1], points[0][1])
                        self.assertTrue(far["x"] < points[1][0] < far["x"] + far["width"])
                        self.assertIn(reach["way"], ("short", "long"))
                    # It comes to its level track along an upright piece: along its upright
                    # track at the left of the board, or on the short way along its loop.
                    self.assertEqual(points[points.index([comes, level_y]) - 1][0], comes)
                    if wire["kind"] != "far" or reach["way"] == "long":
                        self.assertTrue(upright["x"] < comes < upright["x"] + upright["width"])
                        self.assertLess(comes, board["x"])
                    else:
                        self.assertEqual(comes, points[1][0])
                        self.assertGreater(comes, board["x"] + board["width"])
                    if wire["kind"] != "far":
                        self.assertEqual(points[1], [comes, points[0][1]])
                        self.assertEqual(points[2], [comes, level_y])
                    # From the level track upright to the canvas.
                    after = points[points.index([leaves, level_y]) + 1]
                    self.assertEqual(after[0], leaves)
                    self.assertTrue(f["canvas"]["x"] <= leaves <= f["canvas"]["x"] + f["canvas"]["width"])

    def test_the_leg_whose_first_led_is_farthest_from_where_the_lines_come_in_takes_the_level_track_farthest_from_the_canvas(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                edge = f["level"]["y"] if f["feed"] == "bottom" else f["level"]["y"] + f["level"]["height"]
                tracks = [self.on_level_track(f, wire) for wire in mapped["wires"]]
                # From the left: farther from the canvas where the lines come from the
                # left, as below the canvas, and nearer to it where they come from the right.
                depths = [abs(level_y - edge) for level_y, comes, leaves in sorted(tracks, key=lambda track: track[2])]
                self.assertEqual(depths, sorted(depths, reverse=f["arrangement"] == "wide"))
                self.assertEqual(len(set(depths)), len(depths))
                self.assertEqual([round((abs(level_y - edge) - 8.5) / 7) for level_y, comes, leaves in tracks], [reach["level"] for reach in f["reaches"]])
                firsts = sorted(range(len(tracks)), key=lambda index: dumped["mapping"]["legs"][index]["strips"][0])
                self.assertEqual(sorted(range(len(tracks)), key=lambda index: tracks[index][2]), firsts)

    def test_the_pad_nearest_the_level_channel_takes_the_upright_track_nearest_the_board(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                beside = [(self.nearness(f, wire), self.on_level_track(f, wire)[1]) for wire in mapped["wires"] if wire["kind"] != "far"]
                ordered = [track for nearness, track in sorted(beside, reverse=True)]
                self.assertEqual(ordered, sorted(ordered, reverse=True))
                self.assertEqual(len(set(ordered)), len(ordered))
                if beside:
                    self.assertEqual(max(ordered), f["upright"]["x"] + f["upright"]["width"] - 8.5)

    def test_a_pin_the_board_lacks_has_a_pad_beyond_the_end_of_the_board_that_faces_the_level_channel(self):
        seen = 0
        for name, area, dumped, mapped in self.each():
            f = mapped["fit"]
            board = f["board"]
            way = self.to_channel(f)
            off = [wire for wire in mapped["wires"] if wire["kind"] == "off"]
            on = [wire for wire in mapped["wires"] if wire["kind"] == "near"]
            seen += len(off)
            for wire in off:
                with self.subTest(name=name, area=area, leg=wire["leg"]):
                    self.assertEqual(f["reaches"][wire["leg"]]["at"], None)
                    # In the line of the left row of pads, between the board and the level channel.
                    self.assertEqual(wire["pad"]["x"], board["x"] + 0.5625 * board["pitch"])
                    if way > 0:
                        self.assertTrue(board["y"] + board["height"] < wire["pad"]["y"] < f["level"]["y"])
                    else:
                        self.assertTrue(f["level"]["y"] + f["level"]["height"] < wire["pad"]["y"] < board["y"])
                    # It is treated as the pad nearest the level channel.
                    for other in on:
                        self.assertGreater(self.on_level_track(f, wire)[1], self.on_level_track(f, other)[1])
            pads = sorted(wire["pad"]["y"] for wire in off)
            for first, second in zip(pads, pads[1:]):
                self.assertGreaterEqual(second - first, 14)
            # Of two such pads the one whose level track is farther from the canvas stands
            # nearer to the level channel, so their lines do not cross.
            edge = f["level"]["y"] if f["feed"] == "bottom" else f["level"]["y"] + f["level"]["height"]
            depths = [abs(self.on_level_track(f, wire)[0] - edge) for wire in sorted(off, key=lambda wire: self.nearness(f, wire))]
            self.assertEqual(depths, sorted(depths), (name, area))
            for at, first in enumerate(off):
                for second in off[at + 1:]:
                    self.assertEqual(meetings(first["points"], second["points"]), (0, 0), (name, area))
        self.assertGreaterEqual(seen, 5 * 5)
        kinds = [wire["kind"] for wire in self.dumps["pins the board lacks, columns apart"]["mapped"][0]["wires"]]
        self.assertEqual(kinds, ["off", "far", "far", "off", "near", "far", "near", "far", "far", "far", "near", "near"])
        self.assertEqual(self.dumps["one-led-column"]["mapped"][0]["wires"][0]["kind"], "off")

    def test_a_leg_of_the_right_row_takes_the_short_way_when_its_level_track_is_in_the_far_half_of_the_level_channel(self):
        ways = {area: {leg: reach.get("way") for leg, reach in enumerate(self.target(area)["fit"]["reaches"], start=1) if reach["kind"] == "far"} for area in map(tuple, self.AREAS)}
        wide = {1: "short", 2: "short", 19: "long", 20: "long"}
        narrow = {1: "long", 2: "long", 19: "short", 20: "short"}
        self.assertEqual(ways, {(1280, 546): wide, (1920, 1000): wide, (1100, 600): wide, (756, 546): narrow, (600, 546): narrow})
        both = set()
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                board, level = f["board"], f["level"]
                legs = len(f["reaches"])
                way = self.to_channel(f)
                for wire, reach in zip(mapped["wires"], f["reaches"]):
                    if reach["kind"] != "far":
                        self.assertNotIn("way", reach)
                        continue
                    points = wire["points"]
                    level_y, comes, leaves = self.on_level_track(f, wire)
                    far_half = 2 * reach["level"] + 1 >= legs
                    both.add(reach["way"])
                    if reach["way"] == "short":
                        self.assertTrue(far_half)
                        # Level to the loop, along it to the level track: round the end
                        # of the board that faces the level channel.
                        self.assertEqual(points[2], [points[1][0], level_y])
                        self.assertEqual(len(points), 5 if points[-2][1] == level_y else 7)
                    else:
                        if f["arrangement"] == "wide":
                            self.assertFalse(far_half)
                        # Round the other end of the board, back across beyond it, and
                        # along the left side of the board on an upright track.
                        beyond = points[2][1]
                        self.assertEqual(points[2][0], points[1][0])
                        self.assertEqual(points[3], [comes, beyond])
                        self.assertEqual(points[4], [comes, level_y])
                        if way > 0:
                            self.assertLess(beyond, board["y"])
                        else:
                            self.assertGreater(beyond, board["y"] + board["height"])
                        self.assertFalse(level["y"] <= beyond <= level["y"] + level["height"])
                        # On a track beyond every upright track of the pads at the left.
                        for other in mapped["wires"]:
                            if other["kind"] != "far":
                                self.assertLess(comes, self.on_level_track(f, other)[1])
                    if f["arrangement"] == "narrow" and reach["way"] == "long" and far_half:
                        # Its first LED is not to the right of every loop.
                        loops = [other["points"][1][0] for other in mapped["wires"] if other["kind"] == "far"]
                        self.assertLess(leaves, max(loops) + 7)
                    if reach["way"] == "short":
                        loops = [other["points"][1][0] for other in mapped["wires"] if other["kind"] == "far"]
                        if f["arrangement"] == "narrow":
                            self.assertGreaterEqual(leaves, max(loops) + 7)
        self.assertEqual(both, {"short", "long"})

    def test_the_loops_of_each_way_nest(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                far = [(wire, reach) for wire, reach in zip(mapped["wires"], f["reaches"]) if reach["kind"] == "far"]
                loops = [wire["points"][1][0] for wire, reach in far]
                self.assertEqual(len(set(loops)), len(loops))
                for first, second in zip(sorted(loops), sorted(loops)[1:]):
                    self.assertGreaterEqual(second - first, 7)
                # On the short way the pad farthest from the level channel takes the outer loop.
                shorts = sorted(((self.nearness(f, wire), wire["points"][1][0]) for wire, reach in far if reach["way"] == "short"), reverse=True)
                self.assertEqual([loop for nearness, loop in shorts], sorted(loop for nearness, loop in shorts))
                # On the long way the pad nearest the level channel takes the outer loop,
                # which passes farthest beyond the end of the board and takes the upright
                # track farthest from the board.
                longs = sorted((self.nearness(f, wire), wire["points"][1][0], abs(wire["points"][2][1] - f["board"]["y"] - f["board"]["height"] / 2), self.on_level_track(f, wire)[1])
                               for wire, reach in far if reach["way"] == "long")
                self.assertEqual([loop for nearness, loop, beyond, track in longs], sorted(loop for nearness, loop, beyond, track in longs))
                self.assertEqual([beyond for nearness, loop, beyond, track in longs], sorted(beyond for nearness, loop, beyond, track in longs))
                self.assertEqual([track for nearness, loop, beyond, track in longs], sorted((track for nearness, loop, beyond, track in longs), reverse=True))

    def test_no_two_lines_lie_on_each_other_and_none_passes_through_the_board_or_over_an_led(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                canvas, cell = f["canvas"], f["cell"]
                for wire in mapped["wires"]:
                    self.assertFalse(through(f["board"], wire["points"], margin=f["board"]["pitch"] * 0.75), f"the line of leg index {wire['leg']} passes through the board")
                    for start, end in zip(wire["points"], wire["points"][1:]):
                        if through(canvas, [start, end]):
                            # Inside the canvas a line runs upright between two columns,
                            # or along the left edge, clear of every LED.
                            self.assertEqual(start[0], end[0], f"the line of leg index {wire['leg']} crosses the canvas")
                            self.assertEqual((start[0] - canvas["x"]) % cell, 0, f"the line of leg index {wire['leg']} passes over LEDs")
                for index, first in enumerate(mapped["wires"]):
                    for second in mapped["wires"][index + 1:]:
                        self.assertEqual(meetings(first["points"], second["points"])[1], 0, f"the lines of leg indexes {first['leg']} and {second['leg']} lie on each other")

    def test_no_two_lines_cross_twice(self):
        crossed = 0
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                found = self.crossings(mapped["wires"])
                twice = {pair: count for pair, count in found.items() if count > 1}
                self.assertEqual(twice, {}, "lines that cross more than once, by the indexes of their legs")
                crossed += len(found)
        self.assertGreater(crossed, 1000)

    def test_the_lines_of_the_target_file_cross_88_times_in_both_arrangements(self):
        for area in map(tuple, self.AREAS):
            mapped = self.target(area)
            found = self.crossings(mapped["wires"])
            self.assertEqual(sum(found.values()), 88, f"{area}, {mapped['fit']['arrangement']}: the lines of the target file cross {sum(found.values())} times")
            self.assertEqual(set(found.values()), {1})
        self.assertEqual({self.target(area)["fit"]["arrangement"] for area in self.AREAS}, {"wide", "narrow"})

    def test_the_lines_of_the_target_file_cross_where_the_pads_of_the_board_are_out_of_the_order_of_the_legs(self):
        board = self.dumps["legs-20"]["board"]
        legs = self.dumps["legs-20"]["mapping"]["legs"]
        pin_of = {leg["leg"]: str(leg["pin"]) for leg in legs}
        # Going down the left row of pads, and the right one, the legs by their numbers.
        left = [leg for label in board["left"] for leg, pin in pin_of.items() if pin == label]
        right = [leg for label in board["right"] for leg, pin in pin_of.items() if pin == label]
        self.assertEqual(left, [4, 5, 6, 7, 15, 16, 17, 18, 8, 3, 9, 10, 11, 12, 13, 14])
        self.assertEqual(right, [1, 2, 20, 19])
        # Two lines of the left row cross when the upper pad has the lower leg number.
        out_of_order = {(min(upper, lower), max(upper, lower)) for at, upper in enumerate(left) for lower in left[at + 1:] if upper < lower}
        self.assertEqual(len(out_of_order), 83)
        for area in map(tuple, self.AREAS):
            mapped = self.target(area)
            found = {(first + 1, second + 1) for first, second in self.crossings(mapped["wires"])}
            self.assertEqual({pair for pair in found if pair[0] in left and pair[1] in left}, out_of_order, area)
            # A line of the short way and one of the long way cross once in the far zone,
            # and so do the lines of legs 19 and 20.
            self.assertEqual(found - out_of_order, {(1, 19), (1, 20), (2, 19), (2, 20), (19, 20)}, area)

    def test_the_chain_of_a_leg_passes_through_the_corners_of_its_path_and_turns_outside_the_top_and_the_bottom_edge(self):
        for name, area, dumped, mapped in self.each():
            with self.subTest(name=name, area=area):
                f = mapped["fit"]
                canvas, cell = f["canvas"], f["cell"]
                top, bottom = canvas["y"], canvas["y"] + canvas["height"]
                height = dumped["mapping"]["height"]
                for corners, chain, columns in zip(dumped["paths"], mapped["chains"], dumped["strips"]):
                    centres = [[canvas["x"] + (x - 0.5) * cell, canvas["y"] + (height - y + 0.5) * cell] for x, y in corners]
                    inside_canvas = [point for point in chain["points"] if top < point[1] < bottom]
                    self.assertEqual(inside_canvas, centres)
                    self.assertEqual(sorted(chain), ["points", "turns"])
                    self.assertEqual(len(chain["points"]), len(corners) + 2 * (len(columns) - 1))
                    self.assertEqual(len(chain["turns"]), len(columns) - 1)
                    segments(chain["points"])
                    outside = [point for point in chain["points"] if not top < point[1] < bottom]
                    for column, turn, start, first, second in zip(columns[1:], chain["turns"], centres[2::2], outside[0::2], outside[1::2]):
                        # The chain leaves the column before at the end where this one
                        # starts, 6 pixels outside the canvas, and comes back in there.
                        edge, way = (top, 1) if column["start"] == "top" else (bottom, -1)
                        self.assertEqual(first[1], edge - 6 * way)
                        self.assertEqual(second, [start[0], edge - 6 * way])
                        self.assertEqual(turn, {"x": start[0], "y": edge - way, "direction": way})
                        self.assertNotEqual(first[0], second[0])
        chain = self.target((1280, 546))["chains"][0]
        f = self.target((1280, 546))["fit"]
        x, top, bottom = f["canvas"]["x"], f["canvas"]["y"], f["canvas"]["y"] + 540
        self.assertEqual(chain["points"], [[x + 4.5, bottom - 4.5], [x + 4.5, top + 4.5], [x + 4.5, top - 6], [x + 13.5, top - 6], [x + 13.5, top + 4.5], [x + 13.5, bottom - 4.5],
                                           [x + 13.5, bottom + 6], [x + 22.5, bottom + 6], [x + 22.5, bottom - 4.5], [x + 22.5, top + 4.5]])
        self.assertEqual(chain["turns"], [{"x": x + 13.5, "y": top - 1, "direction": 1}, {"x": x + 22.5, "y": bottom + 1, "direction": -1}])

    def test_a_first_led_at_the_feed_edge_is_reached_straight_from_the_level_track(self):
        for name, area, dumped, mapped in self.each():
            f = mapped["fit"]
            canvas = f["canvas"]
            down = self.down(f)
            feed_edge = canvas["y"] + canvas["height"] if down > 0 else canvas["y"]
            for wire, leg, columns, centre in zip(mapped["wires"], dumped["mapping"]["legs"], dumped["strips"], mapped["firsts"]):
                if columns[0]["start"] != f["feed"] and dumped["mapping"]["height"] > 1:
                    continue
                level_y, comes, leaves = self.on_level_track(f, wire)
                self.assertEqual(wire["points"][-2:], [[centre[0], level_y], [centre[0], feed_edge + 2 * down]], (name, area, leg["leg"]))
                self.assertEqual(leaves, canvas["x"] + (columns[0]["x"] - 0.5) * f["cell"])

    def test_a_leg_that_starts_at_the_far_edge_is_reached_through_the_gap_at_the_left_of_its_first_column(self):
        cases = {"a leg of the target from the top": [(6, 19)], "two-and-four-columns": [(1, 6)], "columns-apart": [(1, 1)], "pins the board lacks, columns apart": [(2, 9), (6, 25)],
                 "the same, turned over": [(2, 9), (6, 25)]}
        for name, legs in cases.items():
            dumped = self.dumps[name]
            away = [index for index, columns in enumerate(dumped["strips"]) if columns[0]["start"] != dumped["side"]]
            self.assertEqual(away, [index for index, column in legs], name)
            for area, mapped in zip(self.AREAS, dumped["mapped"]):
                f = mapped["fit"]
                canvas, cell = f["canvas"], f["cell"]
                down = self.down(f)
                far_edge = canvas["y"] if down > 0 else canvas["y"] + canvas["height"]
                for index, column in legs:
                    with self.subTest(name=name, area=area, leg=index):
                        wire, centre = mapped["wires"][index], mapped["firsts"][index]
                        self.assertEqual(dumped["mapping"]["legs"][index]["strips"][0], column)
                        level_y, comes, leaves = self.on_level_track(f, wire)
                        gap = canvas["x"] + (column - 1) * cell
                        self.assertEqual(leaves, gap)
                        self.assertEqual(centre[0], gap + cell / 2)
                        # Along the gap from the level track past the far edge, and into
                        # the LED from outside the canvas.
                        self.assertEqual(wire["points"][-4:], [[gap, level_y], [gap, far_edge - 6 * down], [centre[0], far_edge - 6 * down], [centre[0], far_edge - 2 * down]])
                        self.assertLessEqual(abs(wire["points"][-1][1] - centre[1]), cell / 2 + 2)
                        # The legs beside it are reached at the feed edge.
                        for other, columns in zip(mapped["wires"], dumped["strips"]):
                            if columns[0]["start"] == dumped["side"]:
                                self.assertEqual(abs(other["points"][-1][1] - far_edge), canvas["height"] + 2)

    def test_tracks_gives_the_legs_of_a_column_leg_file_their_places_from_the_left(self):
        self.assertEqual(self.dumps["legs-20"]["tracks"], list(range(20)))
        self.assertEqual(self.dumps["columns-apart"]["tracks"], [1, 0])
        self.assertEqual(self.dumps["two-and-four-columns"]["tracks"], [0, 1])
        self.assertEqual(self.dumps["pins the board lacks, columns apart"]["tracks"], list(range(12)))
        shuffled = dump(column_text(3, [(1, 1, "bottom", [5, 6]), (2, 2, "top", [1]), (3, 3, "bottom", [4, 2]), (4, 4, "top", [3])]))
        self.assertEqual(shuffled["tracks"], [3, 0, 2, 1])


def numbers_of(d):
    """The numbers in the path data of an SVG path, in order."""
    return [float(number) for number in re.findall(r"-?[0-9]+(?:\.[0-9]+)?", d)]


class UprightView(UprightCase):
    """What the view script draws in the mapping view of a column-leg file: run without a
    browser, with a stand-in for the document that keeps the elements."""

    VIEW_AREAS = [[1280, 546], [756, 546]]
    drawings = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if UprightView.drawings is None:
            UprightView.drawings = {name: drawn(text, cls.VIEW_AREAS) for name, text in upright_mappings().items()}

    def every(self):
        for name, found in self.drawings.items():
            dumped = self.dumps[name]
            for area, drawing in zip(self.VIEW_AREAS, found):
                yield name, tuple(area), dumped, dumped["mapped"][self.AREAS.index(area)], drawing

    @staticmethod
    def of(elements, kind, leg=None):
        """The elements of one class, all of them or those of one leg."""
        return [element for element in elements if element["attributes"].get("class") == kind and (leg is None or element["leg"] == leg)]

    @staticmethod
    def upright_text(element):
        """Where a number written upright stands: (left, top, right, bottom). It is read
        from bottom to top, so its line of writing is its right edge."""
        attributes = element["attributes"]
        x, y = re.fullmatch(r"translate\(([0-9.]+) ([0-9.]+)\) rotate\(-90\)", attributes["transform"]).groups()
        size = float(attributes["font-size"])
        length = float(attributes["textLength"]) if "textLength" in attributes else len(element["text"]) * 0.6 * size
        top = {"start": float(y) - length, "middle": float(y) - length / 2, "end": float(y)}[attributes["text-anchor"]]
        return float(x) - 0.72 * size, top, float(x), top + length

    def at_point(self, numbers, point):
        """Says that two numbers of path data, which are written with two decimals, are a point."""
        self.assertEqual(len(numbers), 2)
        for number, wanted in zip(numbers, point):
            self.assertAlmostEqual(number, wanted, delta=0.006)

    def test_the_drawing_is_the_canvas_of_dots_between_two_layers_for_the_fit_of_the_layout_script(self):
        for name, area, dumped, mapped, drawing in self.every():
            with self.subTest(name=name, area=area):
                f = drawing["fit"]
                self.assertEqual(f, mapped["fit"])
                self.assertEqual((drawing["view"], drawing["layers"]), ("mapping", ["svg", "canvas", "svg"]))
                self.assertEqual(drawing["size"], [f"{f['width']}px", f"{f['height']}px"])
                # The LEDs of the mapping view are the live ones: every LED is drawn.
                self.assertEqual(drawing["dots"], dumped["mapping"]["width"] * dumped["mapping"]["height"])
                self.assertEqual(drawing["at"], {**dumped["found"][0][0], "x": 1, "y": 1})
                self.assertEqual(len(self.of(drawing["elements"], "board")), 1)
                self.assertEqual(len(self.of(drawing["elements"], "wires close")), 1)
                self.assertEqual(self.of(drawing["elements"], "wires"), [])

    def test_every_leg_has_its_pad_its_line_its_chain_its_frame_its_numbers_and_its_labels_in_its_colour(self):
        for name, area, dumped, mapped, drawing in self.every():
            f, elements = drawing["fit"], drawing["elements"]
            canvas, cell = f["canvas"], f["cell"]
            height = dumped["mapping"]["height"]
            arrows = 3 if height >= 12 else (1 if height >= 3 else 0)
            for index, (leg, colour, columns, runs, wire) in enumerate(zip(dumped["mapping"]["legs"], dumped["colours"], dumped["strips"], dumped["runs"], mapped["wires"])):
                with self.subTest(name=name, area=area, leg=leg["leg"]):
                    def one(kind):
                        found = self.of(elements, kind, index)
                        self.assertEqual(len(found), 1, kind)
                        return found[0]["attributes"]

                    # The line, from the pad to the first LED, with an arrow head at its end.
                    line = one("wire")
                    self.assertEqual(line["stroke"], colour)
                    self.at_point(numbers_of(line["d"])[:2], wire["points"][0])
                    self.at_point(numbers_of(line["d"])[-2:], wire["points"][-1])
                    self.assertEqual(one("reach-line")["d"], line["d"])
                    heads = self.of(elements, "head", index)
                    self.assertEqual(len(heads), len(columns))
                    self.assertEqual({head["attributes"]["fill"] for head in heads}, {colour})
                    self.at_point(numbers_of(heads[-1]["attributes"]["d"])[:2], wire["points"][-1])
                    # The path of the chain, its small arrows, and the bar at its end.
                    self.assertEqual(one("chain")["stroke"], colour)
                    self.at_point(numbers_of(one("chain")["d"])[:2], mapped["chains"][index]["points"][0])
                    self.assertEqual(len(self.of(elements, "chevron", index)), arrows * len(columns))
                    self.assertEqual(one("wire ending")["stroke"], colour)
                    # A frame round each run of columns, a band behind it and a veil on it.
                    frames = self.of(elements, "outline", index)
                    self.assertEqual([(float(frame["attributes"]["x"]), float(frame["attributes"]["width"])) for frame in frames],
                                     [(canvas["x"] + (run["left"] - 1) * cell + 1, (run["right"] - run["left"] + 1) * cell - 2) for run in runs])
                    for frame in frames:
                        self.assertEqual((float(frame["attributes"]["y"]), float(frame["attributes"]["height"]), frame["attributes"]["stroke"]), (canvas["y"] - 1.5, canvas["height"] + 3, colour))
                        self.assertGreater(float(frame["attributes"]["rx"]), 0)
                    for kind in ("veil", "tint"):
                        self.assertEqual([(float(part["attributes"]["x"]), float(part["attributes"]["y"]), float(part["attributes"]["width"]), float(part["attributes"]["height"])) for part in self.of(elements, kind, index)],
                                         [(canvas["x"] + (run["left"] - 1) * cell, canvas["y"], (run["right"] - run["left"] + 1) * cell, canvas["height"]) for run in runs])
                    # The numbers at the two ends of every column: the 1 of the first LED
                    # in the tag, the others in the two bands.
                    numbers = [element for element in self.of(elements, "t-n", index)]
                    tagged = [element for element in numbers if "data-leg" in element["attributes"]]
                    self.assertEqual([element["text"] for element in tagged], ["1"])
                    self.assertEqual(one("tag")["stroke"], colour)
                    ends = sorted(str(number) for column in columns for number in (column["first"], column["last"]))
                    ends.remove("1")
                    self.assertEqual(sorted(element["text"] for element in numbers if "data-leg" not in element["attributes"]), ends)
                    self.assertEqual({element["attributes"]["fill"] for element in numbers}, {colour})
                    # The pad, the name of the leg beside it, and the leg band.
                    self.assertEqual(len(self.of(elements, "pin taken", index)), 1)
                    self.assertEqual([circle["attributes"]["fill"] for circle in self.of(elements, "pad", index)], [colour])
                    pad = self.of(elements, "pad", index)[0]["attributes"]
                    at = (0, 0) if wire["kind"] == "off" else (f["board"]["x"], f["board"]["y"])
                    self.assertAlmostEqual(float(pad["cx"]) + at[0], wire["pad"]["x"], places=2)
                    self.assertAlmostEqual(float(pad["cy"]) + at[1], wire["pad"]["y"], places=2)
                    label = self.of(elements, "t-leg t-wire", index)
                    self.assertEqual([(element["text"], element["attributes"]["fill"]) for element in label], [(f"leg {leg['leg']}", colour)])
                    self.assertEqual([element["text"] for element in self.of(elements, "t-leg", index)], [str(leg["leg"])] * len(runs))
                    self.assertEqual([element["text"] for element in self.of(elements, "t-pin", index)], [str(leg["pin"])] * len(runs))
                    # A pin the board lacks has a pad of its own with the name of the pin.
                    named = self.of(elements, "t-pad", index)
                    self.assertEqual([element["text"] for element in named], [f"GPIO {leg['pin']}" if wire["kind"] == "off" else str(leg["pin"])])
                    if wire["kind"] == "off":
                        # The name of the pin at the right of the pad, the name of the leg at its left.
                        self.assertEqual(named[0]["attributes"]["text-anchor"], "start")
                        self.assertGreater(float(named[0]["attributes"]["x"]), wire["pad"]["x"] + wire["pad"]["radius"])
                        self.assertEqual(label[0]["attributes"]["text-anchor"], "end")
                        self.assertLess(float(label[0]["attributes"]["x"]), wire["pad"]["x"] - wire["pad"]["radius"])
            lacking = sum(wire["kind"] == "off" for wire in mapped["wires"])
            self.assertEqual(len(self.of(elements, "pad")), 44 + lacking)
            self.assertEqual(len(self.of(elements, "pin")), 44 + lacking - len(mapped["wires"]))
            self.assertEqual(len(self.of(elements, "wire")), len(mapped["wires"]))
        gpio = [element["text"] for element in self.drawings["pins the board lacks, columns apart"][0]["elements"] if element["text"].startswith("GPIO")]
        self.assertEqual(sorted(gpio), ["GPIO 200", "GPIO 99"])

    def test_the_arrow_heads_of_a_chain_point_into_the_canvas_where_it_comes_back_in(self):
        for name, area, dumped, mapped, drawing in self.every():
            f = drawing["fit"]
            top, bottom = f["canvas"]["y"], f["canvas"]["y"] + f["canvas"]["height"]
            for index, chain in enumerate(mapped["chains"]):
                heads = self.of(drawing["elements"], "head", index)[:-1]
                self.assertEqual(len(heads), len(chain["turns"]))
                for head, turn in zip(heads, chain["turns"]):
                    tip_x, tip_y, back_x, back_y = numbers_of(head["attributes"]["d"])[:4]
                    # The tip is on the edge of the canvas, and the head lies outside it.
                    self.at_point([tip_x, tip_y], (turn["x"], top if turn["direction"] > 0 else bottom))
                    self.assertEqual((back_y < tip_y), turn["direction"] > 0)

    def test_the_tag_with_the_number_1_sits_on_the_last_piece_of_the_line(self):
        for name, area, dumped, mapped, drawing in self.every():
            f, elements = drawing["fit"], drawing["elements"]
            canvas = f["canvas"]
            for index, (wire, columns, centre) in enumerate(zip(mapped["wires"], dumped["strips"], mapped["firsts"])):
                with self.subTest(name=name, area=area, leg=index):
                    tag = self.of(elements, "tag", index)[0]["attributes"]
                    left, top, width, tall = (float(tag[key]) for key in ("x", "y", "width", "height"))
                    text = [element for element in self.of(elements, "t-n", index) if "data-leg" in element["attributes"]][0]
                    box = self.upright_text(text)
                    # In the middle of the column of the first LED, in the band at its end.
                    self.assertAlmostEqual(left + width / 2, centre[0], places=1)
                    band = f["numberBottom"] if columns[0]["start"] == "bottom" else f["numberTop"]
                    self.assertTrue(band["y"] <= top and top + tall <= band["y"] + band["height"], (top, tall, band))
                    self.assertTrue(left - 0.5 <= box[0] and box[2] <= left + width + 0.5 and top <= box[1] and box[3] <= top + tall, (box, tag))
                    end = wire["points"][-1]
                    self.assertEqual(end[0], centre[0])
                    edge = min((canvas["y"], canvas["y"] + canvas["height"]), key=lambda y: abs(y - end[1]))
                    if columns[0]["start"] == f["feed"] or dumped["mapping"]["height"] == 1:
                        # The last piece of the line passes under the whole tag.
                        before = wire["points"][-2]
                        self.assertEqual(before[0], end[0])
                        self.assertTrue(min(before[1], end[1]) < top and top + tall < max(before[1], end[1]))
                    else:
                        # Beyond the turn by which the line comes into the LED.
                        self.assertGreater(min(abs(top - edge), abs(top + tall - edge)), 6)
                    # Clear of the arrow head at the canvas.
                    self.assertGreater(min(abs(top - edge), abs(top + tall - edge)), 9)

    def test_the_led_numbers_stand_upright_in_the_two_bands_none_over_another_and_clear_of_the_turns(self):
        for name, area, dumped, mapped, drawing in self.every():
            with self.subTest(name=name, area=area):
                f, elements = drawing["fit"], drawing["elements"]
                canvas, cell = f["canvas"], f["cell"]
                self.assertGreaterEqual(cell, 9)
                boxes = []
                for element in self.of(elements, "t-n"):
                    left, top, right, bottom = self.upright_text(element)
                    self.assertLessEqual(right - left, cell)
                    if "data-leg" not in element["attributes"]:
                        boxes.append((left, top, right, bottom))
                    # In one of the two bands, 11 pixels or more from the canvas: a turn
                    # of a chain is 6 pixels outside it.
                    if bottom <= canvas["y"]:
                        self.assertGreaterEqual(top, f["numberTop"]["y"] - 0.5)
                        self.assertLessEqual(bottom, canvas["y"] - 11)
                    else:
                        self.assertGreaterEqual(top, canvas["y"] + canvas["height"] + 11)
                        self.assertLessEqual(bottom, f["numberBottom"]["y"] + f["numberBottom"]["height"] + 0.5)
                    self.assertTrue(canvas["x"] <= left and right <= canvas["x"] + canvas["width"])
                for tag in self.of(elements, "tag"):
                    left, top, width, tall = (float(tag["attributes"][key]) for key in ("x", "y", "width", "height"))
                    boxes.append((left, top, left + width, top + tall))
                self.assertEqual(len(boxes), 2 * dumped["mapping"]["width"])
                boxes.sort()
                for at, first in enumerate(boxes):
                    for second in boxes[at + 1:]:
                        if second[0] >= first[2]:
                            break
                        self.assertTrue(second[1] >= first[3] or first[1] >= second[3], f"two numbers stand on each other: {first} and {second}")

    def test_pointing_at_a_leg_highlights_it_in_every_place_and_fades_the_others(self):
        for name, area, dumped, mapped, drawing in self.every():
            with self.subTest(name=name, area=area):
                for element in drawing["elements"]:
                    words = element["attributes"].get("class", "").split()
                    self.assertFalse({"hot", "dim"} & set(words))
                self.assertEqual(drawing["host"], "pointing")
                places = set()
                parts = [element for element in drawing["pointing"] if "data-leg" in element["attributes"]]
                self.assertEqual(len(parts), len([element for element in drawing["elements"] if "data-leg" in element["attributes"]]))
                for element in parts:
                    words = element["attributes"]["class"].split()
                    if element["leg"] == 0:
                        self.assertIn("hot", words)
                        self.assertNotIn("dim", words)
                        places.add(" ".join(word for word in words if word != "hot"))
                    else:
                        self.assertIn("dim", words)
                        self.assertNotIn("hot", words)
                # Its label, its pad, its line, its columns, its chain, its numbers and its tag.
                wanted = {"of-leg", "pin taken", "wire", "reach-line", "head", "t-leg t-wire", "tint", "outline", "veil", "chain", "wire ending", "tag", "t-n"}
                self.assertLessEqual(wanted, places)
                if dumped["mapping"]["height"] >= 3:
                    self.assertIn("chevron", places)

    def test_a_row_leg_file_is_drawn_with_its_rows_and_its_one_channel(self):
        drawing = drawn(core_support.mapping_texts()["ten-row-legs"], [[1280, 800]])[0]
        elements = drawing["elements"]
        self.assertEqual((drawing["view"], drawing["fit"]["arrangement"], drawing["dots"]), ("mapping", "beside", 1800))
        counts = {kind: len(self.of(elements, kind)) for kind in ("wires", "wires close", "wire", "reach-line", "tag", "outline", "veil", "chain", "head", "chevron", "wire ending", "pin taken", "t-leg t-wire")}
        self.assertEqual(counts, {"wires": 1, "wires close": 0, "wire": 10, "reach-line": 10, "tag": 10, "outline": 10, "veil": 10, "chain": 10, "head": 30, "chevron": 90,
                                  "wire ending": 10, "pin taken": 10, "t-leg t-wire": 10})
        # The numbers stand level, at the two ends of every row, and the y of every row beside it.
        numbers = self.of(elements, "t-n")
        self.assertEqual(len(numbers), 60)
        self.assertFalse(any("transform" in number["attributes"] for number in numbers))
        self.assertEqual([element["text"] for element in self.of(elements, "t-y") if element["text"].startswith("y=")], [f"y={y}" for y in range(30, 0, -1)])


class WithoutABrowser(unittest.TestCase):
    def test_the_layout_script_runs_in_the_javascript_shell(self):
        done = subprocess.run([*support.js_shell(), str(WEB / "layout.js"), "-e", "print(typeof OdrigLayout.position, typeof window, typeof document)"], capture_output=True, text=True)
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

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

    def test_read_gives_the_width_the_height_and_the_legs_of_the_file(self):
        for name, canvas in self.canvases.items():
            with self.subTest(name):
                read = self.dumps[name]["mapping"]
                self.assertEqual((read["width"], read["height"]), (canvas.width, canvas.height))
                self.assertEqual([(leg["leg"], leg["pin"], leg["first_led"], tuple(leg["rows"]), leg["count"]) for leg in read["legs"]],
                                 [(leg.leg, leg.pin, leg.first_led, tuple(leg.strips), canvas.width * len(leg.strips)) for leg in canvas.legs])

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

    def test_rows_gives_each_row_its_y_its_side_and_its_end_numbers(self):
        for name, canvas in self.canvases.items():
            with self.subTest(name):
                places = rule(canvas)
                for index, (leg, rows) in enumerate(zip(canvas.legs, self.dumps[name]["rows"])):
                    self.assertEqual([row["y"] for row in rows], list(leg.strips))
                    for r, row in enumerate(rows):
                        self.assertEqual((row["first"], row["last"]), (r * canvas.width + 1, (r + 1) * canvas.width))
                        first_x = places[index][row["first"] - 1][0]
                        self.assertEqual(row["start"], "right" if first_x == canvas.width else "left")
                        if canvas.width > 1:
                            self.assertEqual(places[index][row["last"] - 1][0], 1 if row["start"] == "right" else canvas.width)

    def test_rows_gives_the_end_numbers_of_the_drawings_in_the_mapping_document(self):
        text = (support.ROOT / "docs" / "mapping.md").read_text(encoding="utf-8")
        sections = {"legs-2": text.split("## Today's build")[1].split("\n## ")[0], "legs-10": text.split("## Target build")[1].split("\n## ")[0]}
        for name, section in sections.items():
            drawn = re.findall(r"(?m)^y=([0-9]+) +\| +([0-9]+) (<-+|-+>) +([0-9]+) \|(?: +leg ([0-9]+), pin ([0-9]+))?$", section)
            canvas = self.canvases[name]
            self.assertEqual(len(drawn), canvas.height, name)
            by_y = {}
            for index, rows in enumerate(self.dumps[name]["rows"]):
                for row in rows:
                    by_y[row["y"]] = (index, row)
            for y, at_left, arrow, at_right, leg, pin in drawn:
                index, row = by_y[int(y)]
                self.assertEqual(row["start"], "right" if arrow.startswith("<") else "left", (name, y))
                at_x1, at_xw = (row["last"], row["first"]) if row["start"] == "right" else (row["first"], row["last"])
                self.assertEqual((at_x1, at_xw), (int(at_left), int(at_right)), (name, y))
                if leg:
                    self.assertEqual((canvas.legs[index].leg, canvas.legs[index].pin), (int(leg), int(pin)))

    def test_rows_gives_the_end_numbers_of_the_tables_in_the_mapping_document(self):
        text = (support.ROOT / "docs" / "mapping.md").read_text(encoding="utf-8")
        rows_of_tables = re.findall(r"(?m)^\| ([0-9]+) \| ([0-9]+) \| ([0-9, ]+) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \| \(([0-9]+),([0-9]+)\) \|$", text)
        self.assertEqual(len(rows_of_tables), 12)
        for name, table in (("legs-2", rows_of_tables[:2]), ("legs-10", rows_of_tables[2:])):
            canvas = self.canvases[name]
            self.assertEqual(len(table), len(canvas.legs))
            for (leg, pin, ys, *numbers), listed, rows, places in zip(table, canvas.legs, self.dumps[name]["rows"], self.dumps[name]["positions"]):
                self.assertEqual((int(leg), int(pin), [int(y) for y in ys.split(",")]), (listed.leg, listed.pin, list(listed.strips)))
                ends = [number for row in rows for number in (row["first"], row["last"])]
                self.assertEqual(ends, [1, 60, 61, 120, 121, 180])
                pairs = list(zip(map(int, numbers[0::2]), map(int, numbers[1::2])))
                self.assertEqual([tuple(places[number - 1]) for number in ends], pairs)

    def test_path_passes_through_every_led_in_chain_order(self):
        for name, canvas in self.canvases.items():
            with self.subTest(name):
                for leg, corners, places in zip(canvas.legs, self.dumps[name]["paths"], rule(canvas)):
                    self.assertEqual(len(corners), 2 * len(leg.strips))
                    walked = []
                    for start, end in zip(corners[0::2], corners[1::2]):
                        self.assertEqual(start[1], end[1])
                        step = 1 if end[0] >= start[0] else -1
                        walked += [[x, start[1]] for x in range(start[0], end[0] + step, step)]
                    self.assertEqual(walked, places)

    def test_runs_joins_the_neighbouring_rows_of_a_leg(self):
        self.assertEqual(self.dumps["legs-2"]["runs"], [[{"top": 6, "bottom": 4}], [{"top": 3, "bottom": 1}]])
        self.assertEqual(self.dumps["another-order"]["runs"], [[{"top": 4, "bottom": 4}, {"top": 2, "bottom": 2}], [{"top": 5, "bottom": 5}, {"top": 3, "bottom": 3}, {"top": 1, "bottom": 1}]])
        self.assertEqual(self.dumps["two-and-four-rows"]["runs"], [[{"top": 6, "bottom": 5}], [{"top": 4, "bottom": 1}]])

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

    def test_the_colour_of_a_leg_is_entry_i_mod_12_of_the_list(self):
        self.assertEqual(self.dump["manyColours"], [COLOURS[index % 12] for index in range(30)])
        for colour in COLOURS:
            self.assertRegex(colour, r"\A#[0-9a-f]{6}\Z")

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
        self.assertEqual(dumped["mapping"]["legs"][0]["rows"], [10, 8, 6])
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


if __name__ == "__main__":
    unittest.main()

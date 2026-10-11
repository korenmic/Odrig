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
SCRIPTS = (WEB / "layout.js", support.ROOT / "tests" / "emulator" / "js" / "dump_layout.js")

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
        places.append([[place % canvas.width + 1, place // canvas.width + 1] for place in core_support.led_pixels(canvas.width, leg)])
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
        apart_rows = [leg.rows for leg in self.canvases["another-order"].legs]
        self.assertEqual(apart_rows, [(2, 4), (1, 5, 3)])

    def test_read_gives_the_width_the_height_and_the_legs_of_the_file(self):
        for name, canvas in self.canvases.items():
            with self.subTest(name):
                read = self.dumps[name]["mapping"]
                self.assertEqual((read["width"], read["height"]), (canvas.width, canvas.height))
                self.assertEqual([(leg["leg"], leg["pin"], leg["first_led"], tuple(leg["rows"]), leg["count"]) for leg in read["legs"]],
                                 [(leg.leg, leg.pin, leg.first_led, tuple(leg.rows), canvas.width * len(leg.rows)) for leg in canvas.legs])

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
                    self.assertEqual([row["y"] for row in rows], list(leg.rows))
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
                self.assertEqual((int(leg), int(pin), [int(y) for y in ys.split(",")]), (listed.leg, listed.pin, list(listed.rows)))
                ends = [number for row in rows for number in (row["first"], row["last"])]
                self.assertEqual(ends, [1, 60, 61, 120, 121, 180])
                pairs = list(zip(map(int, numbers[0::2]), map(int, numbers[1::2])))
                self.assertEqual([tuple(places[number - 1]) for number in ends], pairs)

    def test_path_passes_through_every_led_in_chain_order(self):
        for name, canvas in self.canvases.items():
            with self.subTest(name):
                for leg, corners, places in zip(canvas.legs, self.dumps[name]["paths"], rule(canvas)):
                    self.assertEqual(len(corners), 2 * len(leg.rows))
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

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
from .test_layout import JSC, WEB, dump, numbers_of, rule

SCRIPT = support.ROOT / "tests" / "emulator" / "js" / "dump_painted.js"

# What only the mapping view draws: the board, the lines, the chains, and the frame, the
# veil and the tag of a leg.
OF_THE_MAPPING_VIEW = ("board", "wires", "wires close", "wire", "reach-line", "chain", "chevron", "head", "wire ending", "outline", "veil", "tag", "pin", "pin taken", "pad", "t-pad", "t-leg t-wire")


def painted(text, areas, refreshes=(), board=False):
    """What the page's view script draws for a mapping file, and what it paints on its
    canvas when the drawing is made and for each refresh, for each drawing area: run in the
    JavaScript shell of macOS with a stand-in for the document. With `board` the drawing
    is the mapping view, without it the LEDs view."""
    if not JSC.exists():
        raise AssertionError(f"the JavaScript shell of macOS is not at {JSC}")
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder, "mapping.json")
        path.write_text(text, encoding="utf-8")
        asked = pathlib.Path(folder, "questions.json")
        asked.write_text(json.dumps({"areas": areas, "board": board, "refreshes": [list(refresh) for refresh in refreshes]}), encoding="utf-8")
        done = subprocess.run([str(JSC), str(SCRIPT), "--", str(WEB / "board.js"), str(WEB / "layout.js"), str(WEB / "view.js"), str(path), str(asked)], capture_output=True, text=True)
    if done.returncode != 0 or done.stderr:
        raise AssertionError(f"jsc ended with status {done.returncode}:\n{done.stdout[-600:]}\n{done.stderr[-600:]}")
    return json.loads(done.stdout)


def shown(value):
    """The display curve of the page, as docs/emulator.md gives it."""
    return math.floor(255 * (value / 255) ** (1 / 2.2) + 0.5)


def of(elements, kind, leg=None):
    """The elements of one class, all of them or those of one leg."""
    return [element for element in elements if element["attributes"].get("class") == kind and (leg is None or element["leg"] == leg)]


def own_colours(count):
    """A refresh in which every LED is lit in a colour no other LED has, also once the
    display curve has been applied: the curve gives every value up to 60 a value of its
    own."""
    return bytes(value for k in range(count) for value in (1 + k % 60, 1 + k // 60 % 60, 1 + k // 3600))


def some_dark(refresh):
    """The same refresh with every third LED dark and the LED after each of them lit as
    little as an LED can be."""
    changed = bytearray(refresh)
    for k in range(0, len(refresh) // 3, 3):
        changed[3 * k:3 * k + 3] = bytes(3)
        if 3 * k + 6 <= len(refresh):
            changed[3 * k + 3:3 * k + 6] = bytes((0, 0, 1))
    return bytes(changed)


class Painted(unittest.TestCase):
    """What the view script paints on its canvas of dots, in the LEDs view and in the
    mapping view, for every mapping of the suites."""

    AREA = [1280, 546]

    @classmethod
    def setUpClass(cls):
        cls.texts = core_support.mapping_texts()
        cls.canvases = {name: mapping.loads(text.encode("utf-8")) for name, text in cls.texts.items()}
        cls.refreshes = {}
        cls.drawings = {}
        for name, canvas in cls.canvases.items():
            first = own_colours(canvas.width * canvas.height)
            cls.refreshes[name] = (first, some_dark(first))
            for board in (False, True):
                cls.drawings[name, board] = painted(cls.texts[name], [cls.AREA], cls.refreshes[name], board)[0]

    def each(self):
        for (name, board), drawing in self.drawings.items():
            yield name, "mapping" if board else "leds", self.canvases[name], drawing

    def centres(self, canvas, drawing):
        """For each LED of a refresh, in the order of its bytes, the centre of the cell of
        its canvas position in the pixels of the canvas of dots: the legs in the order of
        the mapping file, each with its LEDs by the rule of docs/mapping.md."""
        cell = drawing["fit"]["cell"]
        return [((x - 0.5) * cell, (canvas.height - y + 0.5) * cell) for places in rule(canvas) for x, y in places]

    def by_centre(self, dots):
        """The dots of one painting by their centres; no place is painted twice."""
        found = {(x, y): (radius, fill, stroke, width, cleared) for x, y, radius, fill, stroke, width, cleared in dots}
        self.assertEqual(len(found), len(dots))
        return found

    def test_the_mappings_are_of_both_kinds_and_both_views_are_drawn(self):
        self.assertLessEqual({"legs-2", "legs-20", *core_support.MADE_UP_MAPPINGS, *core_support.MADE_UP_COLUMN_MAPPINGS}, set(self.texts))
        self.assertEqual({canvas.kind for canvas in self.canvases.values()}, {mapping.ROWS, mapping.COLUMNS})
        self.assertEqual({(name, view): drawing["view"] for name, view, _, drawing in self.each()}, {(name, view): view for name, view, _, _ in self.each()})
        self.assertEqual(len(self.drawings), 2 * len(self.texts))
        for name, view, _, drawing in self.each():
            self.assertEqual(drawing["layers"], ["svg", "canvas", "svg"], (name, view))

    def test_the_canvas_of_dots_lies_on_the_canvas_of_the_fit(self):
        for name, view, canvas, drawing in self.each():
            with self.subTest(name=name, view=view):
                f = drawing["fit"]
                self.assertEqual((f["canvas"]["width"], f["canvas"]["height"]), (canvas.width * f["cell"], canvas.height * f["cell"]))
                self.assertEqual(drawing["canvas"]["style"], {"left": f"{f['canvas']['x']}px", "top": f"{f['canvas']['y']}px", "width": f"{f['canvas']['width']}px", "height": f"{f['canvas']['height']}px"})
                self.assertEqual((drawing["canvas"]["width"], drawing["canvas"]["height"]), (f["canvas"]["width"], f["canvas"]["height"]))
                self.assertEqual(drawing["canvas"]["scale"], [[1, 0, 0, 1, 0, 0]])

    def test_every_led_of_a_refresh_is_painted_in_the_cell_of_its_canvas_position_in_the_colour_of_its_own_bytes(self):
        for name, view, canvas, drawing in self.each():
            with self.subTest(name=name, view=view):
                cell = drawing["fit"]["cell"]
                refresh = self.refreshes[name][0]
                centres = self.centres(canvas, drawing)
                self.assertEqual(len(centres), len(refresh) // 3)
                self.assertEqual(len(set(centres)), canvas.width * canvas.height)
                wanted = {centre: f"rgb({shown(refresh[3 * k])},{shown(refresh[3 * k + 1])},{shown(refresh[3 * k + 2])})" for k, centre in enumerate(centres)}
                self.assertEqual(len(set(wanted.values())), len(wanted), "two LEDs of the refresh would be shown in one colour")
                dots = self.by_centre(drawing["painted"][0])
                self.assertEqual(len(dots), len(centres))
                for centre, colour in wanted.items():
                    radius, fill, stroke, _, cleared = dots[centre]
                    if fill != colour:
                        self.fail(f"the LED at {centre} of the canvas of dots is painted {fill}, and its own bytes give {colour}")
                    self.assertIsNone(stroke)
                    # A dot stays inside the cell of its LED, and the cell is cleared for it.
                    self.assertTrue(0 < radius < cell / 2, radius)
                    self.assertEqual(cleared, [centre[0] - cell / 2, centre[1] - cell / 2, cell, cell])
                # (1,1) is the bottom-left cell: LED 180 of leg 2 of the bench file, LED 1
                # of leg 1 of the target file.
                self.assertIn((cell / 2, (canvas.height - 0.5) * cell), dots)

    def test_the_first_led_of_the_target_file_is_painted_at_the_bottom_left_and_its_last_at_the_top_right(self):
        for board in (False, True):
            drawing = self.drawings["legs-20", board]
            cell = drawing["fit"]["cell"]
            centres = self.centres(self.canvases["legs-20"], drawing)
            self.assertEqual(len(centres), 3600)
            self.assertEqual(centres[0], (cell / 2, 59.5 * cell))
            self.assertEqual(centres[59], (cell / 2, cell / 2))
            self.assertEqual(centres[60], (1.5 * cell, cell / 2))
            self.assertEqual(centres[3599], (59.5 * cell, cell / 2))
            order = [(x, y) for x, y, *_ in drawing["painted"][0]]
            self.assertEqual(sorted(order), sorted(centres))

    def test_a_dark_led_is_a_ring_and_an_led_with_any_light_is_a_filled_dot(self):
        stage = re.search(r"(?m)^  --stage: (#[0-9a-f]{6});$", (WEB / "style.css").read_text(encoding="utf-8")).group(1)
        for name, view, canvas, drawing in self.each():
            with self.subTest(name=name, view=view):
                cell = drawing["fit"]["cell"]
                first, second = self.refreshes[name]
                centres = self.centres(canvas, drawing)
                # What each cell shows in the end is what was painted there last.
                last = {}
                for dots in (drawing["made"], *drawing["painted"]):
                    last.update(self.by_centre(dots))
                self.assertEqual(sorted(last), sorted(centres))
                kinds = set()
                for k, centre in enumerate(centres):
                    red, green, blue = second[3 * k:3 * k + 3]
                    radius, fill, stroke, width, _ = last[centre]
                    if red or green or blue:
                        self.assertEqual((fill, stroke), (f"rgb({shown(red)},{shown(green)},{shown(blue)})", None), centre)
                        self.assertNotEqual(fill, "rgb(0,0,0)")
                    else:
                        self.assertEqual((fill, width), (None, 1), centre)
                        self.assertRegex(stroke, r"\A#[0-9a-f]{6}\Z")
                        self.assertTrue(0 < radius < cell / 2, radius)
                        # The ring is lighter than the stage it is drawn on.
                        self.assertTrue(all(int(stroke[at:at + 2], 16) > int(stage[at:at + 2], 16) for at in (1, 3, 5)), (stroke, stage))
                    kinds.add((red, green, blue) == (0, 0, 0))
                self.assertEqual(kinds, {True, False} if len(centres) > 1 else {True})

    def test_a_drawing_that_has_shown_no_refresh_has_every_led_as_a_dark_ring(self):
        for name, view, canvas, drawing in self.each():
            with self.subTest(name=name, view=view):
                made = self.by_centre(drawing["made"])
                self.assertEqual(sorted(made), sorted(self.centres(canvas, drawing)))
                self.assertEqual({(fill, width) for _, fill, _, width, _ in made.values()}, {(None, 1)})
                self.assertEqual(len({stroke for _, _, stroke, _, _ in made.values()}), 1)


class UprightLedsView(unittest.TestCase):
    """What the view script draws round the canvas in the LEDs view of a column-leg file."""

    AREAS = [[1280, 546], [1280, 800]]

    @classmethod
    def setUpClass(cls):
        texts = core_support.mapping_texts()
        cls.names = ["legs-20", *core_support.column_mapping_texts()]
        sizes = {name: mapping.loads(texts[name].encode("utf-8")) for name in cls.names}
        cls.dumps = {name: dump(texts[name], areas=cls.AREAS, counts=[sizes[name].height, sizes[name].width]) for name in cls.names}
        cls.drawings = {name: painted(texts[name], cls.AREAS) for name in cls.names}

    def each(self):
        for name in self.names:
            for index, area in enumerate(self.AREAS):
                yield name, tuple(area), self.dumps[name], index, self.drawings[name][index]

    def test_the_drawing_is_the_one_of_the_fit_and_has_no_board_no_line_and_no_chain(self):
        for name, area, dumped, index, drawing in self.each():
            with self.subTest(name=name, area=area):
                f = drawing["fit"]
                self.assertEqual(f, dumped["fits"][index])
                self.assertEqual((drawing["view"], drawing["layers"]), ("leds", ["svg", "canvas", "svg"]))
                self.assertEqual(drawing["size"], [f"{f['width']}px", f"{f['height']}px"])
                self.assertEqual(len(drawing["made"]), dumped["mapping"]["width"] * dumped["mapping"]["height"])
                for kind in OF_THE_MAPPING_VIEW:
                    self.assertEqual(of(drawing["elements"], kind), [], kind)

    def test_every_run_of_columns_of_a_leg_has_a_band_behind_it_and_a_bracket_with_the_number_and_the_pin_in_the_colour_of_the_leg(self):
        for name, area, dumped, index, drawing in self.each():
            f, elements = drawing["fit"], drawing["elements"]
            canvas, cell, band = f["canvas"], f["cell"], f["legBand"]
            for at, (leg, colour, runs) in enumerate(zip(dumped["mapping"]["legs"], dumped["colours"], dumped["runs"])):
                with self.subTest(name=name, area=area, leg=leg["leg"]):
                    spans = [(canvas["x"] + (run["left"] - 1) * cell, (run["right"] - run["left"] + 1) * cell) for run in runs]
                    bands = [part["attributes"] for part in of(elements, "tint", at)]
                    self.assertEqual([(float(part["x"]), float(part["y"]), float(part["width"]), float(part["height"]), part["fill"]) for part in bands],
                                     [(x, canvas["y"], width, canvas["height"], colour) for x, width in spans])
                    brackets = [part["attributes"] for part in of(elements, "bracket", at)]
                    self.assertEqual([part["stroke"] for part in brackets], [colour] * len(runs))
                    for bracket, (x, width) in zip(brackets, spans):
                        self.assertRegex(bracket["d"], r"\AM[0-9.]+ [0-9.]+v-?[0-9.]+H[0-9.]+v-?[0-9.]+\Z")
                        left, hook, rise, right, fall = numbers_of(bracket["d"])
                        # It spans the columns of the run, in the leg band, with its two
                        # ends towards the canvas.
                        self.assertEqual((left, right), (x + 2, x + width - 2))
                        self.assertEqual(rise, -fall)
                        spine = hook + rise
                        self.assertTrue(band["y"] <= min(hook, spine) and max(hook, spine) <= band["y"] + band["height"])
                        middle = canvas["y"] + canvas["height"] / 2
                        self.assertLess(abs(hook - middle), abs(spine - middle))
                    for kind, text in (("t-leg", str(leg["leg"])), ("t-pin", str(leg["pin"]))):
                        labels = of(elements, kind, at)
                        self.assertEqual([label["text"] for label in labels], [text] * len(runs))
                        for label, (x, width) in zip(labels, spans):
                            self.assertEqual((float(label["attributes"]["x"]), label["attributes"]["text-anchor"], label["attributes"]["fill"]), (x + width / 2, "middle", colour))
                            self.assertTrue(band["y"] <= float(label["attributes"]["y"]) <= band["y"] + band["height"])
        self.assertEqual(len(of(self.drawings["legs-20"][0]["elements"], "bracket")), 20)
        self.assertEqual(len(of(self.drawings["columns-apart"][0]["elements"], "bracket")), 5)

    def marks(self, drawing, anchor):
        """The texts that mark rows, which end at the left of the canvas, or columns, which
        stand in the middle of their column: (text, x, y) each."""
        marks = [element for kind in ("t-y", "t-x") for element in of(drawing["elements"], kind)
                 if element["attributes"]["text-anchor"] == anchor and element["text"] not in ("leg", "pin")]
        return [(element["text"], float(element["attributes"]["x"]), float(element["attributes"]["y"])) for element in marks]

    def test_the_first_every_tenth_and_the_last_row_and_column_are_marked_beside_the_canvas(self):
        for name, area, dumped, index, drawing in self.each():
            with self.subTest(name=name, area=area):
                f = drawing["fit"]
                canvas, cell = f["canvas"], f["cell"]
                width, height = dumped["mapping"]["width"], dumped["mapping"]["height"]
                wanted_rows, wanted_columns = dumped["marks"]
                rows = sorted(self.marks(drawing, "end"), key=lambda mark: -mark[2])
                self.assertEqual([text for text, _, _ in rows], [f"y={y}" if y in (1, height) else str(y) for y in wanted_rows])
                for (_, x, y), row in zip(rows, wanted_rows):
                    # At the left of the canvas, at the height of its row.
                    self.assertLess(x, canvas["x"])
                    self.assertLess(abs(y - (canvas["y"] + (height - row + 0.5) * cell)), 5)
                columns = sorted(self.marks(drawing, "middle"), key=lambda mark: mark[1])
                self.assertEqual([text for text, _, _ in columns], [f"x={x}" if x in (1, width) else str(x) for x in wanted_columns])
                for (_, x, y), column in zip(columns, wanted_columns):
                    # Over or under the canvas, in the header, in the middle of its column.
                    self.assertEqual(x, canvas["x"] + (column - 0.5) * cell)
                    self.assertTrue(f["header"]["y"] <= y <= f["header"]["y"] + f["header"]["height"])
        target = self.drawings["legs-20"][0]
        self.assertEqual([text for text, _, _ in sorted(self.marks(target, "end"), key=lambda mark: -mark[2])], ["y=1", "10", "20", "30", "40", "50", "y=60"])
        self.assertEqual([text for text, _, _ in sorted(self.marks(target, "middle"), key=lambda mark: mark[1])], ["x=1", "10", "20", "30", "40", "50", "x=60"])

    def test_where_the_cells_are_9_pixels_or_more_the_numbers_of_the_leds_at_the_two_ends_of_every_column_stand_there(self):
        numbered = set()
        for name, area, dumped, index, drawing in self.each():
            with self.subTest(name=name, area=area):
                f = drawing["fit"]
                canvas, cell = f["canvas"], f["cell"]
                width, height = dumped["mapping"]["width"], dumped["mapping"]["height"]
                numbers = of(drawing["elements"], "t-n")
                numbered.add(cell >= 9)
                if cell < 9:
                    self.assertEqual(numbers, [])
                    continue
                self.assertEqual(len(numbers), 2 * width)
                above, below = {}, {}
                for number in numbers:
                    x, y = (float(value) for value in re.fullmatch(r"translate\(([0-9.]+) ([0-9.]+)\) rotate\(-90\)", number["attributes"]["transform"]).groups())
                    column = int((x - canvas["x"]) // cell) + 1
                    self.assertTrue(1 <= column <= width)
                    # In the half of its column's cell that its line of writing ends.
                    self.assertTrue(0 <= x - (canvas["x"] + (column - 0.5) * cell) < cell / 2)
                    side = above if y <= canvas["y"] else below
                    self.assertTrue(y <= canvas["y"] or y >= canvas["y"] + canvas["height"])
                    self.assertNotIn(column, side)
                    side[column] = (int(number["text"]), number["attributes"]["fill"], number["leg"])
                self.assertEqual((sorted(above), sorted(below)), (list(range(1, width + 1)),) * 2)
                for column in range(1, width + 1):
                    for side, y in ((above, height), (below, 1)):
                        there = dumped["found"][y - 1][column - 1]
                        self.assertEqual(side[column], (there["led"], dumped["colours"][there["leg"]], there["leg"]), (column, y))
        self.assertEqual(numbered, {True, False})
        self.assertEqual((self.drawings["legs-20"][0]["fit"]["cell"], self.drawings["legs-20"][1]["fit"]["cell"]), (8, 11))
        # The numbers of leg 1 of the target file: 1, 120 and 121 below, 60, 61 and 180 above.
        first = [int(number["text"]) for number in of(self.drawings["legs-20"][1]["elements"], "t-n", 0)]
        self.assertEqual(sorted(first), [1, 60, 61, 120, 121, 180])


class BoardInTheMappingView(unittest.TestCase):
    """The board as the view script draws it in the mapping view of the target file, beside
    the canvas and below it."""

    AREAS = [[1280, 546], [756, 546]]

    @classmethod
    def setUpClass(cls):
        text = core_support.mapping_texts()["legs-20"]
        cls.board = dump(text)["board"]
        cls.drawings = painted(text, cls.AREAS, board=True)

    def test_the_antenna_is_at_the_top_the_two_usb_sockets_are_at_the_bottom_and_the_labels_of_the_two_rows_are_in_the_order_of_the_board(self):
        self.assertEqual([drawing["fit"]["arrangement"] for drawing in self.drawings], ["wide", "narrow"])
        self.assertEqual((len(self.board["left"]), len(self.board["right"])), (22, 22))
        for area, drawing in zip(self.AREAS, self.drawings):
            with self.subTest(area=area):
                f, elements = drawing["fit"], drawing["elements"]
                self.assertEqual((drawing["view"], len(of(elements, "board"))), ("mapping", 1))
                pads = [(float(pad["attributes"]["cx"]), float(pad["attributes"]["cy"])) for pad in of(elements, "pad")]
                self.assertEqual(len(pads), 44)
                left, right = min(x for x, _ in pads), max(x for x, _ in pads)
                self.assertLess(left, right)
                rows = {"left": sorted(y for x, y in pads if x == left), "right": sorted(y for x, y in pads if x == right)}
                self.assertEqual(rows["left"], rows["right"])
                self.assertEqual(len(rows["left"]), 22)
                # The labels of a row, read from the antenna to the sockets, each beside its pad.
                for row, anchor in (("left", "start"), ("right", "end")):
                    labels = sorted((float(label["attributes"]["y"]), label["text"]) for label in of(elements, "t-pad") if label["attributes"]["text-anchor"] == anchor)
                    self.assertEqual([text for _, text in labels], self.board[row], row)
                    for (y, _), pad in zip(labels, rows[row]):
                        self.assertLess(abs(y - pad), f["board"]["pitch"] / 2)
                # The antenna is above the first pads, and the sockets reach the lower edge
                # of the board, below the last ones.
                antenna = of(elements, "antenna")
                self.assertEqual(len(antenna), 1)
                heights = [numbers_of(antenna[0]["attributes"]["d"])[1], *(float(y) for y in re.findall(r"V([0-9.]+)", antenna[0]["attributes"]["d"]))]
                self.assertGreater(len(heights), 5)
                self.assertLess(max(heights), rows["left"][0])
                sockets = [socket["attributes"] for socket in of(elements, "socket")]
                self.assertEqual(len(sockets), 2)
                for socket in sockets:
                    self.assertGreater(float(socket["y"]), max(heights))
                    self.assertGreaterEqual(float(socket["y"]) + float(socket["height"]), f["board"]["height"])
                    self.assertGreater(float(socket["y"]) + float(socket["height"]), rows["left"][-1])
                    self.assertTrue(left < float(socket["x"]) and float(socket["x"]) + float(socket["width"]) < right)
                self.assertEqual([label["text"] for label in of(elements, "t-usb")], ["USB", "USB"])
                self.assertEqual(" ".join(label["text"] for kind in ("t-chip", "t-chip small") for label in of(elements, kind)), self.board["name"])


class BenchLedsView(unittest.TestCase):
    """What the view script draws round the canvas in the LEDs view of the bench file."""

    @classmethod
    def setUpClass(cls):
        text = core_support.mapping_texts()["legs-2"]
        cls.dumped = dump(text, areas=[[1280, 546]])
        cls.drawing = painted(text, [[1280, 546]])[0]

    def test_it_has_no_board_no_line_and_no_chain(self):
        self.assertEqual((self.drawing["view"], self.drawing["fit"]), ("leds", self.dumped["fits"][0]))
        for kind in OF_THE_MAPPING_VIEW:
            self.assertEqual(of(self.drawing["elements"], kind), [], kind)

    def test_each_leg_has_a_band_behind_its_rows_and_a_bracket_with_its_number_and_its_pin_in_its_colour(self):
        f, elements = self.drawing["fit"], self.drawing["elements"]
        canvas, cell = f["canvas"], f["cell"]
        for at, (leg, colour, runs) in enumerate(zip(self.dumped["mapping"]["legs"], self.dumped["colours"], self.dumped["runs"])):
            self.assertEqual(len(runs), 1)
            top, tall = canvas["y"] + (6 - runs[0]["top"]) * cell, (runs[0]["top"] - runs[0]["bottom"] + 1) * cell
            bands = [part["attributes"] for part in of(elements, "tint", at)]
            self.assertEqual([(float(part["x"]), float(part["y"]), float(part["width"]), float(part["height"]), part["fill"]) for part in bands], [(canvas["x"], top, canvas["width"], tall, colour)])
            bracket = of(elements, "bracket", at)
            self.assertEqual([part["attributes"]["stroke"] for part in bracket], [colour])
            x, start, _, end, _ = numbers_of(bracket[0]["attributes"]["d"])
            self.assertEqual((start, end), (top + 2, top + tall - 2))
            self.assertTrue(f["bracket"]["x"] <= x <= f["bracket"]["x"] + f["bracket"]["width"])
            self.assertEqual([(label["text"], label["attributes"]["fill"]) for label in of(elements, "t-leg", at)], [(f"leg {leg['leg']}", colour)])
            self.assertEqual([(label["text"], label["attributes"]["fill"]) for label in of(elements, "t-pin", at)], [(f"pin {leg['pin']}", colour)])

    def test_every_row_has_its_y_and_the_numbers_of_the_leds_at_its_two_ends(self):
        f, elements = self.drawing["fit"], self.drawing["elements"]
        canvas, cell = f["canvas"], f["cell"]
        named = [(element["text"], float(element["attributes"]["y"])) for element in of(elements, "t-y") if element["text"].startswith("y=")]
        self.assertEqual([text for text, _ in sorted(named, key=lambda mark: mark[1])], [f"y={y}" for y in range(6, 0, -1)])
        numbers = of(elements, "t-n")
        self.assertEqual(len(numbers), 12)
        ends = {}
        for number in numbers:
            x, y = float(number["attributes"]["x"]), float(number["attributes"]["y"])
            row = 6 - int((y - canvas["y"]) // cell)
            at_the_left = x < canvas["x"]
            self.assertTrue(at_the_left or x > canvas["x"] + canvas["width"])
            self.assertEqual(number["attributes"]["text-anchor"], "end" if at_the_left else "start")
            ends[row, at_the_left] = (int(number["text"]), number["attributes"]["fill"])
        self.assertEqual(len(ends), 12)
        for (row, at_the_left), shown_there in ends.items():
            there = self.dumped["found"][row - 1][0 if at_the_left else 59]
            self.assertEqual(shown_there, (there["led"], self.dumped["colours"][there["leg"]]), (row, at_the_left))
        self.assertEqual([ends[row, True][0] for row in range(6, 0, -1)], [60, 61, 180, 60, 61, 180])
        self.assertEqual([ends[row, False][0] for row in range(6, 0, -1)], [1, 120, 121, 1, 120, 121])


if __name__ == "__main__":
    unittest.main()

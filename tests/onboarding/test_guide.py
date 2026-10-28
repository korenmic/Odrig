import pathlib
import re
import tempfile
import unittest

from odrig import jsonframes, mapping
from odrig.generators import dense, dvd_bounce, hello_world

from . import support

PAGE = "agent/animation-guide.md"

HEADINGS = (
    "Two ways to make an animation",
    "A generator",
    "An import",
    "Check a source",
    "Pack it into a show",
    "Look at it in the emulator",
    "Check it without a screen",
    "Where things go",
    "How large sources get",
    "Dense animations on the board",
)

EXAMPLE = "odrig/generators/dot.py"

# The rows of the table of sizes that a program can work out again: the two tracked sources,
# and what three generators write for the canvas of the target.
TRACKED = ("`animations/dvd.json`", "`animations/hello.json`")
GENERATED = {
    "DVD bounce, as the demo show has it": lambda width, height: dvd_bounce.frames(width, height),
    "Hello world, as the demo show has it": lambda width, height: hello_world.frames(width, height),
    "The clip of the generator `dense`, every place changing at every refresh": lambda width, height: dense.frames(width, height, 10),
}
MEASURED = 3


def flat(text):
    return " ".join(text.split())


def summary(animation, size):
    """A row of the table for an animation: its canvas, its length, its frames and its bytes."""
    seconds = sum(ms for ms, _ in animation.frames) / 1000
    return (f"{animation.width} x {animation.height}", f"{seconds:.1f} s", str(len(animation.frames)), f"{size:,}")


class Guide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = support.read(PAGE)

    def part(self, heading):
        return support.section(self.text, heading)

    def test_it_is_one_of_the_pages_and_has_its_sections(self):
        self.assertIn(PAGE, support.PAGES)
        self.assertEqual(tuple(re.findall(r"(?m)^## (.+)$", self.text)), HEADINGS)

    def test_the_example_generator_writes_a_source_for_the_canvas_of_each_tracked_mapping_file(self):
        examples = [block for block in support.blocks(self.text) if block.mark == "python"]
        self.assertEqual([block.heading for block in examples], ["A generator"])
        self.assertIn(f"`{EXAMPLE}`", self.part("A generator"))
        self.assertIn("write proof-of-concept animations: test content, not examples of finished work", flat(self.part("A generator")))
        self.assertIn("are test content", flat(self.part("Where things go")))
        self.assertFalse((support.ROOT / EXAMPLE).exists())
        module = {"__name__": "odrig.generators.dot", "__package__": "odrig.generators"}
        exec(compile(examples[0].body, EXAMPLE, "exec"), module)
        files = sorted((support.ROOT / "mapping").glob("*.json"))
        self.assertEqual([path.name for path in files], ["legs-2.json", "legs-20.json"])
        for path in files:
            with self.subTest(mapping=path.name), tempfile.TemporaryDirectory() as folder:
                canvas = mapping.read(path)
                out = pathlib.Path(folder) / "dot.json"
                self.assertEqual(module["main"]([str(out), "--mapping", str(path)]), 0)
                animation = jsonframes.read(out)
                self.assertEqual((animation.width, animation.height), (canvas.width, canvas.height))
                self.assertEqual(len(animation.frames), canvas.width)
                for x, (ms, picture) in enumerate(animation.frames, 1):
                    lit = [place for place in range(canvas.width * canvas.height) if any(picture[3 * place:3 * place + 3])]
                    self.assertEqual((ms, lit), (100, [x - 1]))

    def test_it_gives_the_three_fits_and_how_to_take_a_part_of_a_file(self):
        imported = flat(self.part("An import"))
        for phrase in ("`fill`, the default", "`fit`", "`stretch`", "`--start`", "`--duration`", "`.mp4`, `.mov` or `.gif`", "`build/try/clip.gif`"):
            self.assertIn(phrase, imported)

    def test_it_imports_checks_and_packs_with_the_converter_and_generates_with_python(self):
        commands = dict((heading, command) for heading, command in support.page_commands(self.text) if not command.startswith(("mkdir", "printf")))
        for heading, subcommand in (("An import", "import"), ("Check a source", "check"), ("Pack it into a show", "pack")):
            with self.subTest(heading=heading):
                self.assertTrue(commands[heading].startswith(f"{support.NODE} {support.CONVERTER} {subcommand} "), commands[heading])
        self.assertTrue(commands["A generator"].startswith(".venv/bin/python -m odrig.generators."), commands["A generator"])

    def test_it_says_which_tool_imports(self):
        imported = flat(self.part("An import"))
        self.assertIn("Import with this tool: it is the only one that imports.", imported)
        self.assertNotIn("crash", imported)
        self.assertNotIn("reference", imported)

    def test_it_says_what_to_look_for_and_that_the_emulator_does_not_show_the_boards_rate(self):
        looked = self.part("Look at it in the emulator")
        self.assertEqual(len(re.findall(r"(?m)^- \*\*", looked)), 5)
        for phrase in ("right way up", "covers the canvas", "The colours", "The join", "`core` and `page`", "plays everything at 50 refreshes a second", "The board does not"):
            self.assertIn(phrase, flat(looked))

    def test_it_says_where_things_go_and_what_is_committed(self):
        table = self.part("Where things go")
        rows = re.findall(r"(?m)^\| (.+?) \| (.+?) \| (Yes|No)\b.*\|$", table)
        self.assertEqual(len(rows), 8)
        committed = {where: answer for _, where, answer in rows}
        self.assertEqual([answer for where, answer in committed.items() if where.startswith("`thumbnails/")], ["Yes"])
        self.assertEqual([answer for where, answer in committed.items() if where.startswith("`collection/")], ["Yes"])
        self.assertEqual(committed["`animations/NAME.json`"], "Yes")
        self.assertEqual(committed["`shows/NAME/show.json`"], "Yes")
        self.assertEqual(committed["`mapping/`"], "Yes")
        self.assertEqual([answer for where, answer in committed.items() if where.startswith("`build/`")], ["No", "No"])
        self.assertIn("at most 27 characters", flat(table))
        self.assertIn("1 to 32 characters", support.read("docs/show.md"))

    def test_the_sizes_it_gives_are_those_of_the_files_and_of_the_generators(self):
        sizes = self.part("How large sources get")
        rows = {name: tuple(cells) for name, *cells in re.findall(r"(?m)^\| (.+?) \| ([0-9]+ x [0-9]+) \| ([0-9.]+ s) \| ([0-9,]+) \| ([0-9,]+) \|$", sizes)}
        self.assertEqual(len(rows), len(TRACKED) + len(GENERATED) + MEASURED)
        for name in TRACKED:
            with self.subTest(source=name):
                path = support.ROOT / name.strip("`")
                self.assertEqual(rows[name], summary(jsonframes.read(path), path.stat().st_size))
        target = mapping.read(support.ROOT / "mapping" / "legs-20.json")
        for name, frames in GENERATED.items():
            with self.subTest(source=name):
                animation = jsonframes.Animation(target.width, target.height, tuple(frames(target.width, target.height)))
                self.assertEqual(rows[name], summary(animation, len(jsonframes.dumps(animation))))

    def test_it_gives_the_limit_of_a_hosting_service_and_the_owners_ruling(self):
        sizes = flat(self.part("How large sources get"))
        for phrase in ("refuse a single file above 100 MB and warn above 50 MB", "Keep every source at 50 MB or less", "the JSON source is what is committed for every animation", "1,210 bytes"):
            self.assertIn(phrase, sizes)
        self.assertIn("The JSON source is committed for every animation", flat(support.read("docs/decisions.md")))
        self.assertIn("| 1,210 |", support.read("docs/emulator.md"))

    def test_the_rates_of_a_dense_animation_are_those_the_firmware_document_records(self):
        dense_part = flat(self.part("Dense animations on the board"))
        for phrase in ("45 to 47 refreshes a second uncompressed, 36 to 42 compressed", "5 percent larger", "`--uncompressed`", "a little over a minute"):
            self.assertIn(phrase, dense_part)
        firmware = flat(support.read("docs/firmware.md"))
        self.assertIn("45 to 47 against 36 to 42, and the uncompressed file is 5 percent larger", firmware)
        self.assertIn("65 to 74 seconds of it compressed and 61 to 70 seconds uncompressed", flat(support.read("docs/format.md")))


if __name__ == "__main__":
    unittest.main()

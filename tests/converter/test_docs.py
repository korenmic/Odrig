import re
import subprocess
import unittest

from odrig import errors, jsonframes, mapping, odrg
from odrig.generators import dense

from . import support

DOCS = support.ROOT / "docs"


def reasons_in_code():
    return {value for name, value in vars(errors).items() if name.isupper() and isinstance(value, str)}


class ReasonsDocument(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (DOCS / "reasons.md").read_text(encoding="utf-8")
        # The last section lists what the core reports; the tool has only the reasons before it.
        of_the_tool = cls.text.split("\n## The core\n")[0]
        rows = re.findall(r"(?m)^\| ((?:`[a-z0-9-]+`(?:, )?)+) \| (.+) \|$", of_the_tool)
        cls.listed = {}
        for names, condition in rows:
            for name in re.findall(r"`([a-z0-9-]+)`", names):
                cls.listed.setdefault(name, []).append(condition)

    def test_every_reason_of_the_tool_is_listed_with_a_condition(self):
        for reason in sorted(reasons_in_code()):
            with self.subTest(reason=reason):
                self.assertIn(reason, self.listed)
                self.assertTrue(all(condition.strip() for condition in self.listed[reason]))

    def test_every_listed_reason_is_a_reason_of_the_tool(self):
        self.assertEqual(sorted(self.listed), sorted(reasons_in_code()))

    def test_the_tool_has_the_reasons_of_every_kind_of_file(self):
        for reason in ("not-found", "bad-json", "truncated", "mapping-malformed", "show-malformed", "bad-range", "canvas-too-small"):
            self.assertIn(reason, reasons_in_code())

    def test_the_error_line_is_described(self):
        self.assertIn("error: <reason>: <detail>", self.text)

    def test_a_mapping_file_of_either_kind_has_two_reasons_and_no_other(self):
        section = self.text.split("\n## Mapping files\n")[1].split("\n## ")[0]
        self.assertEqual(re.findall(r"(?m)^\| `([a-z0-9-]+)` \| ", section), ["mapping-missing", "mapping-malformed"])
        self.assertEqual(sorted(reason for reason in reasons_in_code() if "mapping" in reason), ["mapping-malformed", "mapping-missing"])
        self.assertEqual((errors.MAPPING_MISSING, errors.MAPPING_MALFORMED), ("mapping-missing", "mapping-malformed"))
        said = " ".join(section.split())
        self.assertIn("The two reasons hold for both kinds of mapping file, the row-leg file and the column-leg file.", said)
        # No reason is named after a part of a mapping file or after one of its kinds.
        for word in ("row", "rows", "column", "columns", "leg", "legs", "strip", "kind", "pin"):
            self.assertEqual([reason for reason in reasons_in_code() if word in reason.split("-")], [], word)


class ConverterDocument(unittest.TestCase):
    """The page of the converter people use, the JavaScript tool: its commands are that
    tool's, and what belongs to the Python tool is on the page of the reference."""

    TOOL = "node converter/odrig.js"
    SUBCOMMANDS = ("import", "encode", "decode", "check", "pack")

    @classmethod
    def setUpClass(cls):
        cls.text = (DOCS / "converter.md").read_text(encoding="utf-8")

    def test_it_names_every_subcommand_with_a_section_and_an_example(self):
        for subcommand in self.SUBCOMMANDS:
            with self.subTest(subcommand=subcommand):
                self.assertIn(f"\n## {subcommand}\n", self.text)
                section = self.text.split(f"\n## {subcommand}\n")[1].split("\n## ")[0]
                self.assertGreaterEqual(section.count(f"{self.TOOL} {subcommand} "), 2)

    def test_no_command_of_it_starts_the_python_tool(self):
        self.assertNotIn("python -m odrig", self.text)
        self.assertNotIn("python3 -m venv", self.text)

    def test_it_gives_the_setup_and_the_test_command_of_the_javascript_tool(self):
        self.assertIn("\nnpm ci --prefix converter\n", self.text)
        self.assertIn("\nnpm test --prefix converter\n", self.text)

    def test_it_describes_the_three_fits(self):
        section = self.text.split("\n## import\n")[1].split("\n## ")[0]
        for fit in ("fill", "fit", "stretch"):
            self.assertIn(f"| `{fit}` |", section)

    def test_it_packs_the_example_show_into_build_example_show(self):
        command = (
            f"{self.TOOL} pack --show shows/example/show.json --mapping mapping/legs-2.json \\\n"
            "    --sources animations --out build/example-show"
        )
        self.assertIn(command, self.text)

    def test_it_points_to_the_page_of_the_python_library(self):
        self.assertIn("(python-library.md)", self.text)


class LibraryDocument(unittest.TestCase):
    """The page of the Python package: a library for the tests and the tools, which holds the
    generators and converts nothing."""

    @classmethod
    def setUpClass(cls):
        cls.text = (DOCS / "python-library.md").read_text(encoding="utf-8")

    def test_it_says_that_the_package_is_a_library_and_points_to_the_converter(self):
        opening = " ".join(self.text.split("\n## ")[0].split())
        self.assertIn("a library for the tests and the tools", opening)
        self.assertIn("It converts nothing", opening)
        self.assertIn("[converter.md](converter.md)", opening)

    def test_it_gives_the_test_command(self):
        self.assertIn("python -m unittest discover -s tests/converter -t .", self.text)

    def test_it_describes_the_setup_with_a_virtual_environment_in_the_repository(self):
        self.assertIn("python3 -m venv .venv", self.text)

    def test_it_describes_the_generators(self):
        for name in ("hello_world", "dvd_bounce", "dense"):
            self.assertIn(f"python -m odrig.generators.{name} ", self.text)

    def test_it_names_the_program_that_writes_the_mapping_document(self):
        self.assertIn("`python -m odrig.mapdoc`", self.text)

    def test_it_describes_the_layout_of_the_test_vectors_and_how_to_build_them(self):
        for phrase in ("tests/vectors/valid/", "tests/vectors/invalid/", "NAME.json", "REASON.CASE.odrg", "python -m tests.converter.build_vectors"):
            self.assertIn(phrase, self.text)

    def test_it_lists_every_vector_that_is_tracked(self):
        vectors = support.ROOT / "tests" / "vectors"
        for path in (vectors / "valid").glob("*.odrg"):
            self.assertIn(f"`{path.name[:-5]}`", self.text, path.name)
        section = self.text.split("`tests/vectors/invalid/` holds")[1].split("\n## ")[0]
        for path in (vectors / "invalid").iterdir():
            parts = path.name.split(".")
            self.assertIn(f"`{parts[0]}`", section, path.name)
            if len(parts) == 3:
                self.assertIn(f"`{parts[1]}`", section, path.name)

    def test_it_describes_the_use_from_python(self):
        section = self.text.split("\n## From Python\n")[1].split("\n## ")[0]
        for call in ("odrig.odrg.decode(data)", "odrig.odrg.encode(animation, compressed=True)", "odrig.mapping.read(path)", "odrig.show.read(path)"):
            self.assertIn(f"`{call}`", section)


class Readme(unittest.TestCase):
    def test_it_points_to_the_converter_document_and_to_the_document_of_the_library(self):
        text = (support.ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("(docs/converter.md)", text)
        self.assertIn("(docs/python-library.md)", text)


class TheTenLegFile(unittest.TestCase):
    """No tracked file names the mapping file of ten row legs or its demo show, apart from
    the records of what was done: the seeds, the specs, the drifts and the change log of
    the decisions."""

    NAMES = tuple(f"{stem}-10".encode("ascii") for stem in ("legs", "demo"))
    RECORDS = ("project-seeds/", "docs/specs/", "docs/drifts.md")
    DECISIONS = "docs/decisions.md"
    CHANGE_LOG = b"\n## Change log\n"

    def test_no_tracked_file_names_them_outside_the_records(self):
        listed = subprocess.run(["git", "ls-files", "-z"], cwd=support.ROOT, capture_output=True, check=True).stdout
        tracked = sorted(name for name in listed.decode("utf-8").split("\0") if name)
        self.assertIn(self.DECISIONS, tracked)
        self.assertIn(self.CHANGE_LOG, (support.ROOT / self.DECISIONS).read_bytes())
        naming = []
        for name in tracked:
            if name.startswith(self.RECORDS):
                continue
            path = support.ROOT / name
            content = path.read_bytes() if path.is_file() else b""
            if name == self.DECISIONS:
                content = content.split(self.CHANGE_LOG)[0]
            if any(gone in name.encode("utf-8") or gone in content for gone in self.NAMES):
                naming.append(name)
        self.assertEqual(len(naming), 0, "tracked files that name the ten-leg mapping or its demo show: " + ", ".join(naming))


class OneConverter(unittest.TestCase):
    """No page calls anything a reference converter, apart from the records of what was
    done: the seeds, the specs, the drifts and the change log of the decisions."""

    RECORDS = TheTenLegFile.RECORDS
    DECISIONS = TheTenLegFile.DECISIONS
    CHANGE_LOG = "\n## Change log\n"

    def test_no_page_names_a_reference_converter(self):
        listed = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=support.ROOT, capture_output=True, check=True).stdout
        pages = sorted(name for name in listed.decode("utf-8").split("\0") if name and not name.startswith(self.RECORDS))
        self.assertIn("docs/python-library.md", pages)
        naming = []
        for name in pages:
            text = (support.ROOT / name).read_text(encoding="utf-8")
            if name == self.DECISIONS:
                text = text.split(self.CHANGE_LOG)[0]
            if re.search(r"reference converter|reference-converter\.md", " ".join(text.split()), re.IGNORECASE):
                naming.append(name)
        self.assertEqual(naming, [])
        self.assertFalse((DOCS / "reference-converter.md").exists())


def paragraph(text, start):
    """The paragraph of a text that begins with these words, with its line breaks as spaces."""
    return " ".join((start + text.split("\n" + start)[1].split("\n\n")[0]).split())


class MeasuredSizes(unittest.TestCase):
    """The row of the dense clip at 60 x 60 in the table of measured sizes of the format
    document, and what that document and the decisions say fits into the board's storage."""

    STARTS = "**What fits.**"

    @classmethod
    def setUpClass(cls):
        cls.section = (DOCS / "format.md").read_text(encoding="utf-8").split("\n## Measured sizes\n")[1]
        cls.rows = re.findall(r"(?m)^\| (.+?) \| ([0-9]+) x ([0-9]+) \| ([0-9,]+) \| ([0-9,]+) \| ([0-9,]+) \|$", cls.section)
        cls.frames, cls.plain, cls.compressed = (int(number.replace(",", "")) for number in cls.rows[-1][3:])
        cls.fits = paragraph(cls.section, cls.STARTS)

    def test_the_last_row_is_the_dense_clip_at_60_by_60_with_the_sizes_the_converter_gives(self):
        self.assertEqual(self.rows[-1][:3], ("Dense full-colour, 10 s", "60", "60"))
        canvas = mapping.read(support.ROOT / "mapping" / "legs-20.json")
        self.assertEqual((canvas.width, canvas.height), (60, 60))
        animation = jsonframes.Animation(canvas.width, canvas.height, tuple(dense.frames(canvas.width, canvas.height, 10)))
        self.assertEqual(self.frames, len(odrg.decode(odrg.encode(animation, compressed=False)).records))
        self.assertEqual(self.plain, len(odrg.encode(animation, compressed=False)))
        # A compressed size depends on the version of zlib.
        compressed = len(odrg.encode(animation, compressed=True))
        self.assertLessEqual(abs(compressed - self.compressed) * 100, 2 * self.compressed, compressed)

    def test_the_document_says_which_rows_the_prototype_measured_and_which_the_converter(self):
        self.assertEqual(sum(row[:3] == ("Dense full-colour, 10 s", "60", "60") for row in self.rows), 1)
        text = " ".join(self.section.split())
        self.assertIn("prototype of the frame coder", text)
        self.assertIn("The last row was measured with the converter of this repository", text)
        self.assertIn("`mapping/legs-20.json`", text)
        self.assertIn("zlib 1.2.12", text)

    def test_it_points_to_the_measurements_on_the_board(self):
        self.assertNotIn("not yet been run", " ".join(self.section.split()))
        self.assertRegex(self.section, r"\[firmware\.md\]\(firmware\.md\),\s+\"Measurements\s+on\s+the\s+board\"")

    def test_what_fits_follows_from_the_sizes_of_the_row_and_the_two_sizes_of_storage(self):
        firmware = (DOCS / "firmware.md").read_text(encoding="utf-8")
        partition, played = 0x9E0000, 9001905
        self.assertIn("| Storage (`spiffs`) | `0x610000` | `0x9E0000` |", firmware)
        self.assertIn(f"| {played:,} bytes |", firmware)
        self.assertIn(f"{partition:,} bytes", self.fits)
        self.assertIn(f"{played:,} bytes", self.fits)
        # A picture that nothing predicts is a stored frame record, one for each 20 ms.
        stored = 5 + 3 * 60 * 60
        self.assertIn(f"{stored:,} bytes for each 20 ms", self.fits)
        for what, ten_seconds in (("compressed", self.compressed), ("uncompressed", self.plain), ("stored frame by frame", 500 * stored)):
            least, most = played * 10 // ten_seconds, partition * 10 // ten_seconds
            self.assertIn(f"{least} to {most} seconds", self.fits, what)
            self.assertRegex(self.fits, rf"{least} to {most} seconds [^.;,]*{what}", what)

    def test_the_decisions_state_what_fits_in_the_same_words(self):
        decisions = (DOCS / "decisions.md").read_text(encoding="utf-8")
        measured = decisions.split("\n### Measurements behind the choice\n")[1].split("\n## ")[0]
        self.assertEqual(paragraph(measured, "- " + self.STARTS)[2:], self.fits)
        self.assertNotIn("noisy", measured)


class TheTarget(unittest.TestCase):
    """No document presents a canvas of 60 x 30, ten legs or 1,800 LEDs as what is built.

    A document may still hold what was measured on ten row legs. Such a record says so
    itself: it stands in a section that has the words of MARK, at or before the paragraph
    that names what was measured. A section is the text from one heading to the next, and
    a paragraph ends at an empty line. The seeds, the specs, the drifts and the change log
    of the decisions keep what they recorded."""

    MARK = "before the target became twenty upright legs"
    GIVEN_UP = re.compile(r"60 ?x ?30|\b(?:ten|10)[- ]legs?\b|\b(?:ten|10) outputs\b|1,800 (?:LEDs|mA)|\blegs [23] to 10\b|\bpins [123] to 10\b|\b30 rows\b", re.IGNORECASE)
    RECORDS = ("project-seeds/", "docs/specs/", "docs/drifts.md")
    DECISIONS = "docs/decisions.md"
    CHANGE_LOG = "\n## Change log\n"

    @classmethod
    def documents(cls):
        listed = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=support.ROOT, capture_output=True, check=True).stdout
        for name in sorted(name for name in listed.decode("utf-8").split("\0") if name and not name.startswith(cls.RECORDS)):
            text = (support.ROOT / name).read_text(encoding="utf-8")
            yield name, text.split(cls.CHANGE_LOG)[0] if name == cls.DECISIONS else text

    @classmethod
    def unmarked(cls, text):
        """The lines of a text that name what was given up outside a record."""
        found = {}
        for section in re.split(r"(?m)^(?=#+ )", text):
            for mention in cls.GIVEN_UP.finditer(section):
                end = section.find("\n\n", mention.end())
                if cls.MARK not in " ".join(section[:end if end >= 0 else len(section)].split()):
                    found[section[section.rfind("\n", 0, mention.start()) + 1:].split("\n")[0].strip()] = True
        return list(found)

    def test_the_rule_tells_a_record_from_a_statement(self):
        record = f"## Measured\n\nTaken {self.MARK}, on ten row legs.\n\n| Dense 60 x 30 clip, 1,800 LEDs |\n\nTen outputs work.\n"
        self.assertEqual(self.unmarked(record), [])
        self.assertEqual(self.unmarked(record + "\n## The page\n\nAll ten legs are drawn.\n"), ["All ten legs are drawn."])
        self.assertEqual(self.unmarked(f"## Measured\n\nA 60 x 30 canvas.\n\nTaken {self.MARK}.\n"), ["A 60 x 30 canvas."])
        self.assertEqual(self.unmarked(f"## Tried\n\n- It held the rate on a 60 x 30 matrix,\n  the target's size {self.MARK}.\n"), [])
        for statement in ("the 60x30 canvas", "the ten-leg mapping", "10 legs", "on ten outputs", "placing 1,800 LEDs", "1,800 mA at rest", "Legs 3 to 10", "pins 1 to 10", "all 30 rows"):
            self.assertEqual(self.unmarked(f"## Now\n\nIt has {statement}.\n"), [f"It has {statement}."], statement)
        for statement in ("ten row legs of three rows of 60", "ten seconds", "60 x 60", "twenty legs", "pins 1 to 18", "a 60 x 6 canvas"):
            self.assertEqual(self.unmarked(f"## Now\n\nIt has {statement}.\n"), [], statement)

    def test_no_document_names_what_was_given_up_outside_a_record(self):
        documents = dict(self.documents())
        self.assertLessEqual({"README.md", "docs/emulator.md", "docs/firmware.md", "docs/format.md", "docs/mapping.md", self.DECISIONS}, set(documents))
        self.assertIn(self.CHANGE_LOG, (support.ROOT / self.DECISIONS).read_text(encoding="utf-8"))
        found = [f"{name}: {line[:90]}" for name, text in documents.items() for line in self.unmarked(text)]
        self.assertEqual(len(found), 0, "documents that name a 60 x 30 canvas, ten legs or 1,800 LEDs outside a record:\n" + "\n".join(found))

    def test_the_documents_that_name_the_target_name_60_by_60_on_twenty_legs(self):
        documents = dict(self.documents())
        canvas = " ".join(documents[self.DECISIONS].split("\n## Canvas and coordinates\n")[1].split("\n## ")[0].split())
        for phrase in ("Target: a 60 x 60 canvas, 3,600 LEDs, on twenty legs", "row legs", "column legs", "`mapping/legs-20.json`", "`mapping/legs-2.json`"):
            self.assertIn(phrase, canvas)
        self.assertIn("\n## Target build: 20 legs, 60 x 60\n", documents["docs/mapping.md"])
        self.assertIn("snake of rows or of columns", " ".join(documents["README.md"].split()))
        self.assertIn("twenty upright legs, 60 x 60", " ".join(documents["README.md"].split()))


def said(text):
    """A text with every run of white space as one space."""
    return " ".join(text.split())


class BothKindsOfLeg(unittest.TestCase):
    """What the documents say of the two kinds of mapping file and of the two builds."""

    @classmethod
    def setUpClass(cls):
        cls.mapping = (DOCS / "mapping.md").read_text(encoding="utf-8")
        cls.decisions = (DOCS / "decisions.md").read_text(encoding="utf-8")

    def part(self, heading):
        """The text of the mapping document under one heading, up to the next heading."""
        return re.split(r"(?m)^#+ ", self.mapping.split(f"\n{heading}\n")[1])[0]

    def test_the_mapping_document_has_its_sections_in_this_order(self):
        headings = re.findall(r"(?m)^(#+ .+)$", self.mapping)
        wanted = ["## Mapping file", "### Rules", "### Where each LED is", "## Today's build: 2 legs, 60 x 6", "## Target build: 20 legs, 60 x 60", "## What is confirmed"]
        self.assertEqual([heading for heading in headings if heading in wanted], wanted)

    def test_the_mapping_document_gives_the_members_of_both_kinds_of_file(self):
        described = self.part("## Mapping file")
        rows = {name: (of_rows, of_columns) for name, of_rows, of_columns in re.findall(r"(?m)^\| `([a-z_]+)` \| (.+) \| (.+) \|$", described)}
        self.assertEqual(sorted(rows), ["columns", "first_led", "height", "leg", "legs", "pin", "rows", "version", "width"])
        self.assertEqual((rows["width"][1], rows["height"][0], rows["rows"][1], rows["columns"][0]), ("Absent.",) * 4)
        self.assertIn('`"left"` or `"right"`', rows["first_led"][0])
        self.assertIn('`"bottom"` or `"top"`', rows["first_led"][1])
        for phrase in ("All legs of one file are of one kind.", "a file with `width` and without `height` is a row-leg file", "a file with `height` and without `width` is a column-leg file",
                       "| Canvas width W | `width` | the number of columns of all legs |", "| Canvas height H | the number of rows of all legs | `height` |"):
            self.assertIn(phrase, said(described))

    def test_the_mapping_document_numbers_eight_rules_and_the_reader_has_a_test_for_each(self):
        rules = self.part("### Rules")
        self.assertEqual(re.findall(r"(?m)^([0-9]+)\. ", rules), [str(number) for number in range(1, 9)])
        for phrase in ("`version` is 1", "from 1 to 255", "from 0 to 255", "W * H is at most 65,534", "an integer from 1 to 65,535", "an array of one or more integers",
                       "every y from 1 to H in a row-leg file, every x from 1 to W in a column-leg file", "a file with both `width` and `height`, or with neither",
                       "`mapping-malformed`", "`mapping-missing`", "The two reasons are the same for both kinds."):
            self.assertIn(phrase, said(rules))
        from .test_mapping import RejectedColumns

        tested = {int(name.split("_")[2]) for name in dir(RejectedColumns) if name.startswith("test_rule_")}
        self.assertEqual(tested, set(range(1, 9)))

    def test_the_mapping_document_says_where_each_led_is_for_both_kinds(self):
        rule = said(self.part("### Where each LED is"))
        for phrase in ("A row leg whose `rows` has R entries has W * R LEDs.", "r = (n - 1) div W", "i = (n - 1) mod W", "y = `rows[r]`",
                       "x = W - i when the row starts on the right, and x = 1 + i when it starts on the left",
                       "A column leg whose `columns` has C entries has H * C LEDs.", "s = (n - 1) div H", "i = (n - 1) mod H", "x = `columns[s]`",
                       "The column starts at the `first_led` end when s is even and at the opposite end when s is odd.",
                       "y = 1 + i when the column starts at the bottom, and y = H - i when it starts at the top"):
            self.assertIn(phrase, rule)

    def test_the_mapping_document_has_both_builds_with_their_files_and_what_is_confirmed(self):
        self.assertIn("File: [`mapping/legs-2.json`](../mapping/legs-2.json).", self.part("## Today's build: 2 legs, 60 x 6"))
        self.assertIn("File: [`mapping/legs-20.json`](../mapping/legs-20.json).", self.part("## Target build: 20 legs, 60 x 60"))
        confirmed = said(self.part("## What is confirmed"))
        for phrase in ("Legs 1 and 2 of today's build are confirmed on the hardware", "The legs of the target build are not wired",
                       "twenty working outputs on pins 1 to 18, 21 and 47", "have not been seen", "It has not been compared with the installation."):
            self.assertIn(phrase, confirmed)

    def test_the_decisions_state_what_was_measured_for_twenty_outputs_and_have_the_target_in_their_change_log(self):
        questions = said(self.decisions.split("\n## Open questions\n")[1].split("\n## ")[0])
        asked = questions.split("- Whether one board can drive twenty LED outputs.")[1].split(" - ")[0]
        for phrase in ("Measured on the board", "twenty working outputs", "four through WLED's RMT driver and sixteen through its parallel driver", "on pins 1 to 18, 21 and 47"):
            self.assertIn(phrase, asked)
        entries = [said(entry) for entry in re.split(r"(?m)^- (?=[0-9]{4}-[0-9]{2}-[0-9]{2}: )", self.decisions.split("\n## Change log\n")[1])[1:]]
        self.assertEqual(entries, sorted(entries, key=lambda entry: entry[:10]))
        named = [entry for entry in entries if "the target of twenty upright legs, 60 x 60" in entry]
        self.assertEqual(len(named), 1)
        for phrase in ("column legs beside row legs", "`mapping/legs-20.json`", "`shows/demo-20`", "twenty working outputs"):
            self.assertIn(phrase, named[0])

    def test_the_converter_document_describes_both_kinds_and_names_the_target(self):
        text = said((DOCS / "converter.md").read_text(encoding="utf-8"))
        for phrase in ("with a row-leg file it is as wide as the mapping's `width` and as high as the number of rows the mapping lists",
                       "with a column-leg file it is as wide as the number of columns the mapping lists and as high as the mapping's `height`",
                       "The show for the target build of twenty legs, 60 x 60, is the demo show `shows/demo-20/show.json`"):
            self.assertIn(phrase, text)

    def test_the_document_of_the_library_has_the_generators_for_both_kinds_and_for_the_target(self):
        generators = said((DOCS / "python-library.md").read_text(encoding="utf-8").split("\n## Generators\n")[1].split("\n## ")[0])
        for phrase in ("from a mapping file of either kind, a row-leg file or a column-leg file", "--mapping mapping/legs-20.json"):
            self.assertIn(phrase, generators)


if __name__ == "__main__":
    unittest.main()

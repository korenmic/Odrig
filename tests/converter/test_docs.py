import re
import subprocess
import unittest

from odrig import cli, errors, jsonframes, mapping, odrg
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


class ConverterDocument(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (DOCS / "converter.md").read_text(encoding="utf-8")

    def test_it_names_every_subcommand_with_a_section_and_an_example(self):
        for subcommand in cli.SUBCOMMANDS:
            with self.subTest(subcommand=subcommand.name):
                self.assertIn(f"\n## {subcommand.name}\n", self.text)
                section = self.text.split(f"\n## {subcommand.name}\n")[1].split("\n## ")[0]
                self.assertGreaterEqual(section.count(f"python -m odrig {subcommand.name} "), 2)

    def test_it_gives_the_test_command(self):
        self.assertIn("python -m unittest discover -s tests/converter -t .", self.text)

    def test_it_describes_the_setup_with_a_virtual_environment_in_the_repository(self):
        self.assertIn("python3 -m venv .venv", self.text)
        self.assertIn(".venv/bin/python -m pip install -r requirements.txt", self.text)

    def test_it_names_the_versions_that_the_requirements_file_pins(self):
        pinned = dict(
            re.findall(r"(?m)^([a-z]+)==([0-9.]+)(?:;.*)?$", (support.ROOT / "requirements.txt").read_text())
        )
        self.assertEqual(sorted(pinned), ["av", "numpy", "pillow"])
        for version in pinned.values():
            self.assertIn(version, self.text)

    def test_it_describes_the_three_fits(self):
        section = self.text.split("\n## import\n")[1].split("\n## ")[0]
        for fit in ("fill", "fit", "stretch"):
            self.assertIn(f"| `{fit}` |", section)

    def test_it_describes_the_generators(self):
        for name in ("hello_world", "dvd_bounce", "dense"):
            self.assertIn(f"python -m odrig.generators.{name} ", self.text)

    def test_it_packs_the_example_show_into_build_example_show(self):
        command = (
            "python -m odrig pack --show shows/example/show.json --mapping mapping/legs-2.json \\\n"
            "    --sources animations --out build/example-show"
        )
        self.assertIn(command, self.text)

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


class Readme(unittest.TestCase):
    def test_it_points_to_the_converter_document(self):
        text = (support.ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("(docs/converter.md)", text)


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


if __name__ == "__main__":
    unittest.main()

import re
import unittest

from odrig import cli, errors

from . import support

DOCS = support.ROOT / "docs"


def reasons_in_code():
    return {value for name, value in vars(errors).items() if name.isupper() and isinstance(value, str)}


class ReasonsDocument(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (DOCS / "reasons.md").read_text(encoding="utf-8")
        rows = re.findall(r"(?m)^\| ((?:`[a-z0-9-]+`(?:, )?)+) \| (.+) \|$", cls.text)
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


if __name__ == "__main__":
    unittest.main()

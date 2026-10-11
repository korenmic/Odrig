import re
import subprocess
import unittest

from . import support

SOURCES = support.CORE / "src"
INCLUDE = support.CORE / "include"
ALLOWED_SYMBOLS = support.ROOT / "tests" / "core" / "allowed_symbols.txt"

# The only headers of the system a source of the core may include.
SYSTEM_HEADERS = ("stdint.h", "stddef.h", "string.h")

INCLUDE_LINE = re.compile(r'(?m)^[ \t]*#[ \t]*include[ \t]*([<"])([^>"]+)[>"]')
FLOATING_POINT = re.compile(r"\b(?:float|double)\b")


def core_sources():
    """Every source file and header of the core."""
    return sorted([*SOURCES.glob("*.cpp"), *SOURCES.glob("*.h"), *INCLUDE.glob("*.h")])


def without_comments_and_strings(text):
    """The code of a C++ source: comments, string literals and character literals removed."""
    pattern = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.S)
    return pattern.sub(lambda match: " " if match.group().startswith("/") else '""', text)


def foreign_headers(text, own):
    """The headers a source includes that are neither allowed system headers nor the core's own."""
    found = []
    for bracket, name in INCLUDE_LINE.findall(text):
        allowed = name in SYSTEM_HEADERS if bracket == "<" else name in own
        if not allowed:
            found.append(name)
    return found


def nm(*options):
    done = subprocess.run(
        ["nm", *options, str(support.built(support.LIBRARY))], capture_output=True, text=True, check=True
    )
    return done.stdout


def symbols():
    """`(undefined, defined)`: the names the library refers to and the names it defines."""
    undefined = set()
    defined = set()
    for line in nm("-m").splitlines():
        match = re.match(r"^\s*[0-9a-f]*\s*\((.+?)\)\s+(?:\[.*?\]\s+)?(?:non-)?(?:weak )?(?:private )?external\s+(\S+)", line)
        if not match:
            continue
        section, name = match.groups()
        (undefined if section == "undefined" else defined).add(name)
    return undefined, defined


def allowed_symbols():
    lines = ALLOWED_SYMBOLS.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


class Library(unittest.TestCase):
    def test_it_refers_only_to_names_of_the_allowed_list(self):
        undefined, defined = symbols()
        self.assertIn("__ZN5odrig11reason_nameENS_6ReasonE", defined)
        outside = sorted(undefined - defined - allowed_symbols())
        self.assertEqual(outside, [], f"names outside {ALLOWED_SYMBOLS.name}: {', '.join(outside)}")

    def test_the_allowed_list_holds_no_allocation_input_output_or_clock(self):
        allowed = allowed_symbols()
        self.assertTrue(allowed)
        for name in allowed:
            self.assertRegex(name, r"^_(mem(cpy|move|set|cmp)|bzero|__stack_chk_(fail|guard))$")

    def test_it_has_no_symbol_in_a_writable_data_section(self):
        listing = nm("-m")
        self.assertIn("(__TEXT,__text)", listing)
        for line in listing.splitlines():
            section = re.search(r"\((__[A-Z_]+,__[a-z_0-9]+|common)\)", line)
            if not section:
                continue
            name = section.group(1)
            writable = name == "common" or (name.startswith("__DATA,") and name != "__DATA,__const")
            self.assertFalse(writable, line.strip())

    def test_the_library_holds_every_source(self):
        members = subprocess.run(
            ["ar", "t", str(support.built(support.LIBRARY))], capture_output=True, text=True, check=True
        ).stdout.split()
        objects = sorted(name for name in members if name.endswith(".o"))
        self.assertEqual(objects, sorted(path.stem + ".o" for path in SOURCES.glob("*.cpp")))


class Sources(unittest.TestCase):
    def test_there_are_sources_to_check(self):
        names = {path.name for path in core_sources()}
        self.assertIn("reasons.cpp", names)
        self.assertIn("reasons.h", names)

    def test_they_include_only_three_system_headers_and_their_own(self):
        own = {path.name for path in core_sources()}
        for path in core_sources():
            text = path.read_text(encoding="utf-8")
            self.assertEqual(foreign_headers(text, own), [], path.name)

    def test_they_use_no_floating_point_type(self):
        for path in core_sources():
            code = without_comments_and_strings(path.read_text(encoding="utf-8"))
            self.assertIsNone(FLOATING_POINT.search(code), path.name)

    def test_they_have_no_function_local_static_and_no_exceptions(self):
        for path in core_sources():
            code = without_comments_and_strings(path.read_text(encoding="utf-8"))
            for word in ("throw", "try", "catch", "typeid", "dynamic_cast", "new", "delete", "virtual", "thread_local"):
                self.assertIsNone(re.search(rf"\b{word}\b", code), f"{path.name} uses {word}")
            for line in code.splitlines():
                if re.match(r"^\s+static\b", line):
                    self.fail(f"{path.name} has a static inside a block: {line.strip()}")

    def test_the_checks_find_what_they_look_for(self):
        own = {"reasons.h"}
        text = '#include <stdint.h>\n#include "reasons.h"\n  # include <vector>\n#include "other.h"\n'
        self.assertEqual(foreign_headers(text, own), ["vector", "other.h"])
        code = without_comments_and_strings('int a; // a double\nconst char *b = "float"; /* float */ double c;')
        self.assertEqual(FLOATING_POINT.findall(code), ["double"])


class ReasonNames(unittest.TestCase):
    def test_every_name_the_core_can_report_is_in_the_reasons_document(self):
        names = support.host_lines("reasons")
        self.assertGreater(len(names), 20)
        self.assertEqual(len(names), len(set(names)))
        text = (support.ROOT / "docs" / "reasons.md").read_text(encoding="utf-8")
        listed = set(re.findall(r"`([a-z0-9-]+)`", text))
        for name in names:
            with self.subTest(name=name):
                self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
                self.assertIn(name, listed)

    def test_the_core_has_the_reason_of_every_invalid_vector(self):
        names = set(support.host_lines("reasons"))
        vectors = sorted((support.ROOT / "tests" / "vectors" / "invalid").iterdir())
        self.assertGreater(len(vectors), 20)
        for path in vectors:
            self.assertIn(path.name.split(".")[0], names, path.name)


if __name__ == "__main__":
    unittest.main()

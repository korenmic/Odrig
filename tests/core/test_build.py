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
        expected = ("core.cpp", "core_state.h", "reasons.cpp", "reasons.h", "arena.h", "file_source.cpp", "inflate.cpp", "odrg_decoder.cpp",
                    "json_reader.cpp", "mapping.cpp", "show.cpp", "player.cpp", "commands.cpp", "odrig_core.h")
        for name in expected:
            self.assertIn(name, names)

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

    def test_they_are_valid_in_every_standard_from_cpp11_on(self):
        sources = sorted(SOURCES.glob("*.cpp"))
        self.assertGreaterEqual(len(sources), 10)
        for standard in ("c++11", "c++14", "c++17", "c++20", "c++2b"):
            done = subprocess.run(
                ["c++", f"-std={standard}", "-Wall", "-Wextra", "-Wpedantic", "-Wshadow", "-Werror", "-fno-exceptions", "-fno-rtti", f"-I{INCLUDE}", "-fsyntax-only", *map(str, sources)],
                capture_output=True,
                text=True,
            )
            self.assertEqual((done.returncode, done.stderr), (0, ""), standard)

    def test_the_checks_find_what_they_look_for(self):
        own = {"reasons.h"}
        text = '#include <stdint.h>\n#include "reasons.h"\n  # include <vector>\n#include "other.h"\n'
        self.assertEqual(foreign_headers(text, own), ["vector", "other.h"])
        code = without_comments_and_strings('int a; // a double\nconst char *b = "float"; /* float */ double c;')
        self.assertEqual(FLOATING_POINT.findall(code), ["double"])


# A host written against the interface, valid as C and as C++.
USE_OF_THE_INTERFACE = """
#include "odrig_core.h"
#include "odrig_core.h"

static void *give(void *ctx, size_t bytes) { (void)ctx; (void)bytes; return 0; }
static int open_file(void *ctx, const char *name) { (void)ctx; (void)name; return 0; }
static int32_t read_file(void *ctx, uint8_t *buffer, size_t capacity) { (void)ctx; (void)buffer; (void)capacity; return 0; }
static void close_file(void *ctx) { (void)ctx; }
static void log_line(void *ctx, const char *text) { (void)ctx; (void)text; }
static void on_reply(void *ctx, const char *line, size_t line_length, const char *reply, size_t reply_length) {
    (void)ctx; (void)line; (void)line_length; (void)reply; (void)reply_length;
}

int main(void) {
    odrig_host host = {0, give, open_file, read_file, close_file, log_line};
    odrig_leg leg;
    char line[ODRIG_LINE_MAX + 1] = "status";
    char reply[ODRIG_REPLY_MAX];
    const uint8_t bytes[1] = {10};
    odrig_reply_fn answered = on_reply;
    odrig_core *core = odrig_core_begin(&host);
    uint64_t now = 0;
    uint32_t legs = odrig_core_leg_count(core);
    int produced = odrig_core_poll(core, now);
    int found = odrig_core_leg(core, 0, &leg);
    size_t length = odrig_core_command(core, now, line, 6, reply, sizeof reply);
    const char *error = odrig_core_error(core);
    const uint8_t *rgb = leg.rgb;
    uint16_t number = leg.leg, pin = leg.pin;
    uint32_t count = leg.led_count;
    odrig_core_feed(core, now, bytes, 1, answered, 0);
    return (int)(legs + count + length) + produced + found + number + pin + (error != 0) + (rgb != 0)CHANGE;
}
"""


class HostInterface(unittest.TestCase):
    HEADER = INCLUDE / "odrig_core.h"

    def compiles(self, compiler, language, standard, source):
        done = subprocess.run(
            [compiler, "-x", language, f"-std={standard}", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-fsyntax-only", f"-I{INCLUDE}", "-"],
            input=source,
            capture_output=True,
            text=True,
        )
        return done.returncode == 0, done.stderr

    def test_it_is_the_only_header_a_host_includes(self):
        self.assertEqual([path.name for path in INCLUDE.iterdir()], ["odrig_core.h"])

    def test_it_compiles_as_c_and_as_cpp(self):
        source = USE_OF_THE_INTERFACE.replace("CHANGE", "")
        for compiler, language, standard in (("cc", "c", "c99"), ("cc", "c", "c17"), ("c++", "c++", "c++11"), ("c++", "c++", "c++17")):
            with self.subTest(standard=standard):
                compiled, complaint = self.compiles(compiler, language, standard, source)
                self.assertTrue(compiled, complaint)

    def test_the_compilation_refuses_a_wrong_use(self):
        source = USE_OF_THE_INTERFACE.replace("CHANGE", " + odrig_core_poll(core)")
        for compiler, language, standard in (("cc", "c", "c99"), ("c++", "c++", "c++11")):
            with self.subTest(standard=standard):
                compiled, complaint = self.compiles(compiler, language, standard, source)
                self.assertFalse(compiled)
                self.assertIn("odrig_core_poll", complaint)

    def test_it_needs_only_stdint_and_stddef(self):
        text = self.HEADER.read_text(encoding="utf-8")
        self.assertEqual(sorted(INCLUDE_LINE.findall(text)), [("<", "stddef.h"), ("<", "stdint.h")])

    def test_it_declares_the_seven_functions_of_the_core(self):
        text = self.HEADER.read_text(encoding="utf-8")
        declared = re.findall(r"\b(odrig_core_[a-z_]+)\(", without_comments_and_strings(text))
        self.assertEqual(
            sorted(declared),
            [
                "odrig_core_begin",
                "odrig_core_command",
                "odrig_core_error",
                "odrig_core_feed",
                "odrig_core_leg",
                "odrig_core_leg_count",
                "odrig_core_poll",
            ],
        )


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

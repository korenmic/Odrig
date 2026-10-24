import re
import subprocess
import sys
import unittest

from . import support

SOURCES = support.CORE / "src"
INCLUDE = support.CORE / "include"
ALLOWED_SYMBOLS = support.ROOT / "tests" / "core" / "allowed_symbols.txt"

# The only headers of the system a source of the core may include.
SYSTEM_HEADERS = ("stdint.h", "stddef.h", "string.h")

INCLUDE_LINE = re.compile(r'(?m)^[ \t]*#[ \t]*include[ \t]*([<"])([^>"]+)[>"]')
FLOATING_POINT = re.compile(r"\b(?:float|double)\b")

# An array declared inside a block: its element type, whether it holds pointers, its name
# and its number of elements as the source writes it.
ARRAY_IN_A_BLOCK = re.compile(r"(?m)^[ \t]+(?:const[ \t]+)?([A-Za-z_]\w*)[ \t]+(\*?)[ \t]*([A-Za-z_]\w*)\[([^\]\n]+)\];")
CONSTANT = re.compile(r"(?m)^const[ \t]+\w+[ \t]+(k\w+)[ \t]*=[ \t]*([^;\n]+);")
ELEMENT_BYTES = {"char": 1, "uint8_t": 1, "int8_t": 1, "uint16_t": 2, "int16_t": 2, "uint32_t": 4, "int32_t": 4, "uint64_t": 8, "int64_t": 8}
# The structures of the core that a function holds an array of, by their size: a stroke of
# a clock's dial is five 16-bit numbers.
ELEMENT_BYTES["Stroke"] = 10
NO_TYPES = ("return", "else", "case", "goto", "delete", "throw", "sizeof")
# The most bytes an array inside a function of the core may have.
LARGEST_LOCAL_ARRAY = 256


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


# The object files of macOS are listed with their sections, by `nm -m`, and every name of
# C has an underscore in front. For the object files of Windows `nm` gives one letter for
# the kind of a name, and the name as it is in C: there the underscore is put in front
# here, so that a name reads the same on both systems.
MACH_O = sys.platform != "win32"
def number(text, constants):
    """The value of a number of elements: digits, constants of the same source, and the
    signs of a sum or a product."""
    if not re.fullmatch(r"[\w \t+*()-]+", text):
        raise ValueError(f"not a plain number of elements: {text}")
    return int(eval(text, {"__builtins__": {}}, dict(constants)))


def constants_of(code, known=()):
    """The constants a source defines as plain numbers, by name, beside the ones known."""
    constants = dict(known)
    for name, value in CONSTANT.findall(code):
        try:
            constants[name] = number(value, constants)
        except (ValueError, NameError, SyntaxError):
            pass
    return constants


def arrays_in_blocks(code, known=()):
    """`(name, bytes)` of every array a source declares inside a block. `known` holds the
    constants of the headers it includes."""
    constants = constants_of(code, known)
    found = []
    for element, pointer, name, count in ARRAY_IN_A_BLOCK.findall(code):
        if element in NO_TYPES:
            continue
        found.append((name, number(count, constants) * (8 if pointer else ELEMENT_BYTES[element])))
    return found


def nm(*options):
    done = subprocess.run(
        [support.gnu("nm"), *options, str(support.built(support.LIBRARY))], capture_output=True, text=True, check=True
    )
    return done.stdout


def lettered():
    """`(letter, name)` for every name `nm` lists with a letter for its kind."""
    return [(match.group(1), "_" + match.group(2)) for match in re.finditer(r"(?m)^[0-9a-f]*\s+([A-Za-z]) (\S+)$", nm())]


def symbols():
    """`(undefined, defined)`: the names the library refers to and the names it defines."""
    undefined = set()
    defined = set()
    if not MACH_O:
        for letter, name in lettered():
            (undefined if letter == "U" else defined).add(name)
        return undefined, defined
    for line in nm("-m").splitlines():
        match = re.match(r"^\s*[0-9a-f]*\s*\((.+?)\)\s+(?:\[.*?\]\s+)?(?:non-)?(?:weak )?(?:private )?external\s+(\S+)", line)
        if not match:
            continue
        section, name = match.groups()
        (undefined if section == "undefined" else defined).add(name)
    return undefined, defined


def writable():
    """The names the library keeps in a section a program can write to. A name that begins
    with a dot is that of a section, which every object file has, also when it is empty."""
    if not MACH_O:
        return sorted(name[1:] for letter, name in lettered() if letter in "DdBbCcGgSs" and not name.startswith("_."))
    found = []
    for line in nm("-m").splitlines():
        section = re.search(r"\((__[A-Z_]+,__[a-z_0-9]+|common)\)", line)
        if not section:
            continue
        name = section.group(1)
        if name == "common" or (name.startswith("__DATA,") and name != "__DATA,__const"):
            found.append(line.strip())
    return found


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
            self.assertRegex(name, r"^_(mem(cpy|move|set|cmp)|strlen|bzero|__stack_chk_(fail|guard))$")

    def test_it_has_no_symbol_in_a_writable_data_section(self):
        self.assertIn("(__TEXT,__text)" if MACH_O else " T ", nm("-m") if MACH_O else nm())
        self.assertEqual(writable(), [])

    def test_the_library_holds_every_source(self):
        members = subprocess.run(
            [support.gnu("ar"), "t", str(support.built(support.LIBRARY))], capture_output=True, text=True, check=True
        ).stdout.split()
        objects = sorted(name for name in members if name.endswith(".o"))
        self.assertEqual(objects, sorted(path.stem + ".o" for path in SOURCES.glob("*.cpp")))


class Sources(unittest.TestCase):
    def test_there_are_sources_to_check(self):
        names = {path.name for path in core_sources()}
        expected = ("core.cpp", "core_state.h", "reasons.cpp", "reasons.h", "arena.h", "file_source.cpp", "inflate.cpp", "odrg_decoder.cpp",
                    "json_reader.cpp", "mapping.cpp", "show.cpp", "player.cpp", "commands.cpp", "content.cpp", "content.h", "storage.h", "odrig_core.h")
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

    def test_no_function_has_an_array_above_256_bytes(self):
        found = []
        shared = {}
        for path in sorted(SOURCES.glob("*.h")):
            shared = constants_of(without_comments_and_strings(path.read_text(encoding="utf-8")), shared)
        self.assertEqual((shared["kIdTextSize"], shared["kFileBufferSize"]), (12, 512))
        for path in sorted(SOURCES.glob("*.cpp")):
            code = without_comments_and_strings(path.read_text(encoding="utf-8"))
            for name, size in arrays_in_blocks(code, shared):
                found.append((path.name, name, size))
                self.assertLessEqual(size, LARGEST_LOCAL_ARRAY, f"{path.name}: {name} has {size} bytes")
        # The check reads the arrays the sources have: names of files and ids, the tables
        # of a Huffman code, the start of a file and of a frame record.
        self.assertGreaterEqual(len(found), 15)
        self.assertLessEqual({("show.cpp", "file", 33), ("odrg_decoder.cpp", "header", 16), ("inflate.cpp", "offset", 32), ("commands.cpp", "text", 40), ("clock.cpp", "made", 140)}, set(found))
        # The compiler holds every function to a frame of 512 bytes, and the core object to
        # 4,096 bytes.
        makefile = (support.CORE / "Makefile").read_text(encoding="utf-8")
        self.assertIn("-Wframe-larger-than=512", makefile)
        self.assertIn("-Werror", makefile)
        self.assertIn("static_assert(sizeof(odrig_core) <= 4096,", (SOURCES / "core_state.h").read_text(encoding="utf-8"))

    def test_they_are_valid_in_every_standard_from_cpp11_on(self):
        sources = sorted(SOURCES.glob("*.cpp"))
        self.assertGreaterEqual(len(sources), 10)
        for standard in ("c++11", "c++14", "c++17", "c++20", "c++2b"):
            done = subprocess.run(
                [support.gnu("cxx"), f"-std={standard}", "-Wall", "-Wextra", "-Wpedantic", "-Wshadow", "-Werror", "-fno-exceptions", "-fno-rtti", f"-I{INCLUDE}", "-fsyntax-only", *map(str, sources)],
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
        code = "const uint32_t kSize = 100;\nconst uint32_t kMore = kSize + 29;\nvoid f() {\n    uint8_t small[kSize];\n    uint16_t large[kMore];\n    const char *words[4];\n" \
               "    return small[0];\n        char one[257];\n}\nuint8_t outside[1000];\n"
        self.assertEqual(arrays_in_blocks(code), [("small", 100), ("large", 258), ("words", 32), ("one", 257)])
        with self.assertRaises(KeyError):
            arrays_in_blocks("void f() {\n    Thing things[4];\n}\n")


# A host written against the interface, valid as C and as C++.
USE_OF_THE_INTERFACE = """
#include "odrig_core.h"
#include "odrig_core.h"

static void *give(void *ctx, size_t bytes) { (void)ctx; (void)bytes; return 0; }
static int open_file(void *ctx, const char *name) { (void)ctx; (void)name; return 0; }
static int32_t read_file(void *ctx, uint8_t *buffer, size_t capacity) { (void)ctx; (void)buffer; (void)capacity; return 0; }
static void close_file(void *ctx) { (void)ctx; }
static void log_line(void *ctx, const char *text) { (void)ctx; (void)text; }
static int begin_file(void *ctx, const char *name) { (void)ctx; (void)name; return -1; }
static int add_bytes(void *ctx, const uint8_t *bytes, size_t length) { (void)ctx; (void)bytes; (void)length; return -1; }
static int end_file(void *ctx) { (void)ctx; return -1; }
static int rename_file(void *ctx, const char *from, const char *to) { (void)ctx; (void)from; (void)to; return -1; }
static int remove_file(void *ctx, const char *name) { (void)ctx; (void)name; return -1; }
static int tell_space(void *ctx, uint32_t *free_bytes, uint32_t *total_bytes) { (void)ctx; *free_bytes = 1; *total_bytes = 2; return 1; }
static int32_t read_part(void *ctx, const char *name, uint32_t offset, uint8_t *buffer, size_t capacity) {
    (void)ctx; (void)name; (void)offset; (void)buffer; (void)capacity; return -1;
}
static uint32_t drive_number(void *ctx) { (void)ctx; return 0; }
static int drive_name(void *ctx, uint32_t drive, uint32_t place, char *buffer, size_t capacity) {
    (void)ctx; (void)drive; (void)place; (void)buffer; (void)capacity; return 0;
}
static void on_reply(void *ctx, const char *line, size_t line_length, const char *reply, size_t reply_length) {
    (void)ctx; (void)line; (void)line_length; (void)reply; (void)reply_length;
}

int main(void) {
    odrig_host host = {0, give, open_file, read_file, close_file, log_line,
                       begin_file, add_bytes, end_file, rename_file, remove_file, tell_space, read_part,
                       drive_number, drive_name, 0};
    odrig_host plain = {0, give, open_file, read_file, close_file, log_line, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    odrig_leg leg;
    char line[ODRIG_LINE_MAX + 1] = "status";
    char reply[ODRIG_REPLY_MAX];
    const uint8_t bytes[1] = {10};
    odrig_reply_fn answered = on_reply;
    odrig_core *core = odrig_core_begin(plain.write_open == 0 ? &host : &plain);
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
            [support.gnu({"cc": "cc", "c++": "cxx"}[compiler]), "-x", language, f"-std={standard}", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-fsyntax-only", f"-I{INCLUDE}", "-"],
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

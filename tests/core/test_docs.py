import re
import unittest

from . import support

DOCS = support.ROOT / "docs"
HEADER = support.CORE / "include" / "odrig_core.h"
HOST = support.ROOT / "tests" / "core" / "host" / "host.cpp"


def without_comments(text):
    return re.sub(r"/\*.*?\*/", " ", text, flags=re.S)


def named_in_code(text):
    """Everything a document writes as code in its sentences and tables: the words inside
    its backticks."""
    without_blocks = re.sub(r"(?s)```.*?```", " ", text)
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", " ".join(re.findall(r"`([^`\n]+)`", without_blocks))))


class CoreDocument(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (DOCS / "core.md").read_text(encoding="utf-8")
        cls.named = named_in_code(cls.text)
        cls.header = without_comments(HEADER.read_text(encoding="utf-8"))

    def test_it_names_every_function_of_the_header(self):
        functions = set(re.findall(r"\b(odrig_core_[a-z_]+)\(", self.header))
        self.assertEqual(len(functions), 7)
        for function in sorted(functions):
            self.assertTrue(function in self.named, function)
            self.assertTrue(f"{function}(" in self.text, function)

    def test_it_names_every_member_of_the_two_structs(self):
        structs = dict(re.findall(r"typedef struct (odrig_[a-z]+) \{(.*?)\}", self.header, flags=re.S))
        self.assertEqual(sorted(structs), ["odrig_host", "odrig_leg"])
        members = {}
        for struct, body in structs.items():
            members[struct] = re.findall(r"(?:\(\*|[ *])([a-z_]+)\)?(?:\([^;]*\))?;", body)
        self.assertEqual(members["odrig_host"], ["ctx", "alloc", "open", "read", "close", "log", "write_open", "write", "write_close", "rename", "remove", "space", "read_at"])
        self.assertEqual(members["odrig_leg"], ["leg", "pin", "led_count", "rgb"])
        for struct, names in members.items():
            self.assertTrue(struct in self.named, struct)
            for name in names:
                self.assertRegex(self.text, rf"(?m)^\| `{name}` \|", f"{struct}.{name}")

    def test_it_gives_the_led_count_of_a_leg_for_both_kinds_of_leg(self):
        row = re.search(r"(?m)^\| `led_count` \| (.+) \|$", self.text).group(1)
        self.assertIn("the strip length of the mapping file times the leg's number of strips", row)
        for kind in ("rows of the canvas in a row-leg file", "columns in a column-leg file"):
            self.assertIn(kind, row)
        self.assertIn("(mapping.md)", row)

    def test_it_names_the_types_and_the_limits_of_the_header(self):
        types = set(re.findall(r"\b(odrig_[a-z_]+)\b", self.header)) - set(re.findall(r"\b(odrig_core_[a-z_]+)\(", self.header))
        self.assertEqual(types, {"odrig_core", "odrig_host", "odrig_leg", "odrig_reply_fn"})
        limits = dict(re.findall(r"#define (ODRIG_[A-Z_]+)\s+([0-9]+)", self.header))
        self.assertEqual(limits, {"ODRIG_LINE_MAX": "2048", "ODRIG_REPLY_MAX": "1024"})
        for name in sorted(types | set(limits)):
            self.assertTrue(name in self.named, name)
        for name, value in limits.items():
            self.assertRegex(self.text, rf"`{name}` is {value}\b")

    def test_it_gives_the_three_commands_and_what_each_needs(self):
        rows = dict(re.findall(r"(?m)^\| `(make -C core[a-z ]*)` \| .+ \|(.*)\|$", self.text))
        self.assertEqual(sorted(rows), ["make -C core", "make -C core bench", "make -C core clean", "make -C core test"])
        self.assertIn("command-line developer tools", rows["make -C core"])
        self.assertIn("Python 3.10", rows["make -C core test"])
        self.assertIn("PYTHON=", self.text)

    def test_the_commands_it_gives_are_targets_of_the_makefile(self):
        makefile = (support.CORE / "Makefile").read_text(encoding="utf-8")
        for target in ("all", "test", "bench", "clean"):
            self.assertRegex(makefile, rf"(?m)^{target}:")
        phony = re.search(r"(?m)^\.PHONY: (.+)$", makefile).group(1).split()
        self.assertLessEqual({"all", "test", "bench", "clean"}, set(phony))
        test_rule = re.search(r"(?m)^test:.*\n((?:\t.*\n)+)", makefile).group(0)
        self.assertNotIn("bench", test_rule)
        self.assertIn("unittest discover -s tests/core -t .", test_rule)

    def test_it_covers_time_led_data_startup_and_memory(self):
        for heading in ("The host interface", "Rules of use", "Time, the grid and refreshes", "LED data", "Command lines", "Startup", "Memory", "Benchmark", "The test host"):
            self.assertRegex(self.text, rf"(?m)^##+ {heading}$")
        for phrase in ("power-on moment", "every 20 ms", "`(v * brightness + 127) / 255`", "chain order", "131,072", "only inside `odrig_core_begin`"):
            self.assertTrue(phrase in self.text, phrase)

    def test_its_memory_table_adds_up_to_what_the_suite_measures(self):
        table = self.text.split("\n## Memory\n")[1].split("\n## ")[0]
        rows = re.findall(r"(?m)^\| ([^|*]+) \| [^|]+ \| ([0-9,]+) \|$", table)
        self.assertEqual(len(rows), 13)
        total = int(re.search(r"\*\*Total\*\* \| \| \*\*([0-9,]+)\*\*", table).group(1).replace(",", ""))
        self.assertEqual(sum(int(number.replace(",", "")) for _, number in rows), total)
        from .test_memory import hundred_items

        asked, blocks = support.start(hundred_items()).memory
        self.assertEqual((asked, blocks), (total, 13))
        example, _ = support.start(support.example_show()).memory
        self.assertIn(f"{example:,} bytes", table)

    def test_it_names_every_invocation_option_and_input_line_of_the_test_host(self):
        source = HOST.read_text(encoding="utf-8")
        usage = source.split("int usage() {")[1].split("return kUsage;")[0]
        options = set(re.findall(r"--[a-z-]+", usage))
        self.assertGreaterEqual(len(options), 16)
        for option in sorted(options):
            self.assertRegex(self.text, rf"`[^`\n]*{option}\b", option)
        for invocation in ("reasons", "inflate", "decode", "session", "guard"):
            self.assertTrue(f"odrig_host {invocation}" in usage, invocation)
            self.assertTrue(f"`odrig_host {invocation}" in self.text, invocation)
        for line in set(re.findall(r'word == "([a-z]+)"', source)) | {"error"}:
            self.assertRegex(self.text, rf"(?m)^\| `{line}[ `]", line)
        for status in re.findall(r"const int k[A-Za-z]+ = ([0-9]+);", source):
            self.assertRegex(self.text, rf"(?m)^\| {status} \|", status)
        self.assertRegex(self.text, r"(?m)^\| 70 \| `allocation after startup` \|")


class ReasonsDocument(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = (DOCS / "reasons.md").read_text(encoding="utf-8")
        cls.section = text.split("\n## The core\n")[1]

    def test_it_lists_the_texts_of_an_invalid_show_in_the_order_of_the_checks(self):
        texts = re.findall(r"(?m)^\| `([a-z-]+(?: <[a-z]+>)*)` \| .+ \|$", self.section.split("\n| Text | Condition |\n")[1])
        self.assertEqual(
            texts,
            [
                "mapping-missing",
                "mapping-malformed",
                "show-missing",
                "show-malformed",
                "duplicate-id <id>",
                "undefined-id <id>",
                "nested-cycle <id>",
                "file-missing <name>",
                "file-malformed <name> <reason>",
                "size-mismatch <name>",
                "read-error <name>",
                "out-of-memory",
            ],
        )

    def test_every_text_begins_with_a_name_the_core_can_report(self):
        names = set(support.host_lines("reasons"))
        texts = re.findall(r"(?m)^\| `([a-z-]+)(?: <[a-z]+>)*` \|", self.section)
        self.assertGreaterEqual(len(texts), 14)
        for text in texts:
            self.assertIn(text, names)


class Readme(unittest.TestCase):
    def test_it_points_to_the_core_document(self):
        text = (support.ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("(docs/core.md)", text)


if __name__ == "__main__":
    unittest.main()

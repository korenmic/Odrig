import ast
import re
import sys
import unittest

from . import support

PACKAGE = support.ROOT / "odrig"

# What stays of the package: a library that reads and writes the project's files for the
# tests and the tools, and the generators. Converting and packing are the converter's.
LIBRARY = {
    "__init__.py", "errors.py", "files.py", "strictjson.py", "jsonframes.py", "odrg.py", "mapping.py", "show.py", "mapdoc.py",
    "generators/__init__.py", "generators/dense.py", "generators/dvd_bounce.py", "generators/hello_world.py", "generators/lines_test.py", "generators/rainbow.py",
}
# The tools, which run no converter logic, and what of the library they may read with.
TOOLS = ("emulator", "odrigctl", "preview", "firmware/fwtool")
READING = {"odrig", "odrig.errors", "odrig.files", "odrig.strictjson", "odrig.mapping", "odrig.show", "odrig.odrg"}

# Modules that open a network connection or a serial port.
FORBIDDEN_MODULES = (
    "socket",
    "ssl",
    "http",
    "urllib.request",
    "serial",
    "socketserver",
    "ftplib",
    "smtplib",
    "xmlrpc",
    "asyncio",
    "requests",
)

# Names through which a program asks which operating system it runs on.
SYSTEM_ATTRIBUTES = (("sys", "platform"), ("os", "name"), ("os", "uname"), ("sys", "getwindowsversion"))


def modules():
    """`(path, syntax tree)` for every module of the package."""
    paths = sorted(PACKAGE.rglob("*.py"))
    return [(path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))) for path in paths]


def imported(tree):
    """The dotted names of everything a module imports."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def is_or_is_inside(name, module):
    return name == module or name.startswith(module + ".")


def tool_modules():
    """`(path, text, syntax tree)` for every module of the tools."""
    paths = sorted(path for folder in TOOLS for path in (support.ROOT / folder).rglob("*.py"))
    return [(path, path.read_text(encoding="utf-8")) for path in paths]


class WhoConverts(unittest.TestCase):
    def test_the_package_is_the_library_and_the_generators(self):
        names = {path.relative_to(PACKAGE).as_posix() for path, _ in modules()}
        self.assertEqual(names, LIBRARY)

    def test_the_library_needs_only_the_standard_library(self):
        for path, tree in modules():
            for name in imported(tree):
                top = name.split(".")[0]
                self.assertTrue(top in sys.stdlib_module_names or top == "odrig", f"{path.name} imports {name}")

    def test_the_tools_read_with_the_library_and_convert_nothing(self):
        for path, text in tool_modules():
            for name in imported(ast.parse(text, filename=str(path))):
                if is_or_is_inside(name, "odrig"):
                    self.assertIn(name, READING, f"{path.relative_to(support.ROOT)} imports {name}")
            self.assertNotRegex(text, r"\bodrg\.encode\(|\bjsonframes\b", path.relative_to(support.ROOT))

    def test_only_the_preview_starts_the_converter_and_only_to_check_and_pack(self):
        starting = {path.relative_to(support.ROOT).as_posix() for path, text in tool_modules() if "odrig.js" in text}
        self.assertEqual(starting, {"preview/__init__.py"})
        preview = (support.ROOT / "preview" / "__init__.py").read_text(encoding="utf-8")
        self.assertEqual(sorted(set(re.findall(r'converter\(node, "([a-z]+)"', preview))), ["check", "pack"])


class Scope(unittest.TestCase):

    def test_no_module_imports_a_network_or_serial_module(self):
        for path, tree in modules():
            for name in imported(tree):
                for module in FORBIDDEN_MODULES:
                    self.assertFalse(is_or_is_inside(name, module), f"{path.name} imports {name}")

    def test_no_module_asks_which_operating_system_it_runs_on(self):
        for path, tree in modules():
            for name in imported(tree):
                self.assertFalse(is_or_is_inside(name, "platform"), f"{path.name} imports {name}")
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    self.assertNotIn((node.value.id, node.attr), SYSTEM_ATTRIBUTES, f"{path.name}, line {node.lineno}")

    def test_the_checks_find_what_they_look_for(self):
        tree = ast.parse("import os, urllib.request\nfrom http import client\nif os.name == 'nt':\n    pass\n")
        names = imported(tree)
        self.assertTrue(any(is_or_is_inside(name, "urllib.request") for name in names))
        self.assertTrue(any(is_or_is_inside(name, "http") for name in names))
        self.assertFalse(any(is_or_is_inside(name, "socket") for name in names))
        found = [
            (node.value.id, node.attr)
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
        ]
        self.assertIn(("os", "name"), found)

    def test_every_source_file_is_written_in_the_grammar_of_python_3_10(self):
        sources = sorted(PACKAGE.rglob("*.py")) + sorted((support.ROOT / "tests").rglob("*.py"))
        self.assertGreater(len(sources), 20)
        for path in sources:
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 10))

    def test_reasons_are_written_out_in_the_errors_module_only(self):
        from odrig import errors

        reasons = {value for name, value in vars(errors).items() if name.isupper()}
        for path, tree in modules():
            if path.name == "errors.py":
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    self.assertNotIn(node.value, reasons, f"{path.name}, line {node.lineno}")


if __name__ == "__main__":
    unittest.main()

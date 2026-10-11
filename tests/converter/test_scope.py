import ast
import unittest

from . import support

PACKAGE = support.ROOT / "odrig"

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


class Scope(unittest.TestCase):
    def test_the_package_has_the_modules_this_test_reads(self):
        names = {str(path.relative_to(PACKAGE)) for path, _ in modules()}
        for expected in ("cli.py", "odrg.py", "media.py", "pack.py", "generators/dense.py"):
            self.assertIn(expected, names)

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

    def test_only_the_media_module_imports_a_third_party_library(self):
        third_party = ("numpy", "PIL", "av")
        for path, tree in modules():
            uses = {name for name in imported(tree) for library in third_party if is_or_is_inside(name, library)}
            if path.name == "media.py":
                self.assertTrue(uses)
            else:
                self.assertEqual(uses, set(), path.name)

    def test_a_media_file_is_only_ever_a_file_on_this_computer(self):
        from odrig import errors, mapping, media

        canvas = mapping.read(support.ROOT / "mapping" / "legs-2.json")
        with self.assertRaises(errors.Rejection) as caught:
            media.import_media("http://localhost:9/clip.mp4", canvas)
        self.assertEqual(caught.exception.reason, "not-found")


if __name__ == "__main__":
    unittest.main()

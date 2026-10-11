import ast
import sys
import unittest

from . import support

EMULATOR = support.ROOT / "emulator"


def modules(package):
    """`(path, syntax tree)` for every module of a package."""
    paths = sorted(package.rglob("*.py"))
    return [(path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))) for path in paths]


def imported(tree):
    """The top-level names of everything a module imports from outside its own package."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


class Scope(unittest.TestCase):
    def test_the_package_has_the_modules_this_test_reads(self):
        names = {path.name for path, _ in modules(EMULATOR)}
        for expected in ("__init__.py", "binding.py", "failure.py", "host.py"):
            self.assertIn(expected, names)

    def test_every_module_imports_only_the_standard_library_and_its_own_package(self):
        for path, tree in modules(EMULATOR):
            for name in sorted(imported(tree)):
                self.assertTrue(name in sys.stdlib_module_names or name == EMULATOR.name, f"{path.name} imports {name}")

    def test_no_module_imports_the_converter(self):
        for path, tree in modules(EMULATOR):
            self.assertNotIn("odrig", imported(tree), path.name)

    def test_only_the_binding_imports_ctypes(self):
        users = [path.name for path, tree in modules(EMULATOR) if "ctypes" in imported(tree)]
        self.assertEqual(users, ["binding.py"])

    def test_the_checks_find_what_they_look_for(self):
        tree = ast.parse("import os, ctypes.util\nfrom odrig import odrg\nfrom . import failure\nfrom .host import FolderHost\nimport numpy\n")
        self.assertEqual(imported(tree), {"os", "ctypes", "odrig", "numpy"})
        self.assertNotIn("numpy", sys.stdlib_module_names)
        self.assertNotIn("odrig", sys.stdlib_module_names)
        self.assertIn("ctypes", sys.stdlib_module_names)

    def test_every_module_is_written_in_the_grammar_of_python_3_10(self):
        for path, _ in modules(EMULATOR):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()

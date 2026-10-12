import ast
import re
import subprocess
import sys
import unittest

from . import support

EMULATOR = support.ROOT / "emulator"
TOOL = support.ROOT / "odrigctl"
PACKAGES = (EMULATOR, TOOL)

# The proof-of-concept scripts that speak WLED's own protocol. They stay untracked.
PROOF_OF_CONCEPT_TOOLS = ("wled.py", "wled_send.py", "wled_deploy.py")


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


def texts(tree):
    """Every text a module writes out as a constant."""
    return [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]


class Scope(unittest.TestCase):
    def test_the_packages_have_the_modules_this_test_reads(self):
        names = {path.name for path, _ in modules(EMULATOR)}
        for expected in ("__init__.py", "__main__.py", "app.py", "binding.py", "engine.py", "failure.py", "host.py", "httpd.py", "hub.py", "lineport.py", "recfile.py", "record.py", "serialport.py"):
            self.assertIn(expected, names)
        self.assertEqual(sorted(path.name for path, _ in modules(TOOL)), ["__init__.py", "__main__.py", "cli.py", "client.py", "winserial.py"])

    def test_every_module_imports_only_the_standard_library_and_its_own_package(self):
        for package in PACKAGES:
            for path, tree in modules(package):
                for name in sorted(imported(tree)):
                    self.assertTrue(name in sys.stdlib_module_names or name == package.name, f"{package.name}/{path.name} imports {name}")

    def test_no_module_imports_the_converter_or_the_other_package(self):
        for package in PACKAGES:
            others = {"odrig", "emulator", "odrigctl", "tests", "tools"} - {package.name}
            for path, tree in modules(package):
                self.assertEqual(imported(tree) & others, set(), f"{package.name}/{path.name}")

    def test_only_the_binding_and_the_serial_port_of_windows_import_ctypes(self):
        users = [f"{package.name}/{path.name}" for package in PACKAGES for path, tree in modules(package) if "ctypes" in imported(tree)]
        self.assertEqual(users, ["emulator/binding.py", "odrigctl/winserial.py"])

    def test_the_emulator_holds_no_decoder_no_show_reader_and_no_command_names(self):
        for path, tree in modules(EMULATOR):
            self.assertNotIn("zlib", imported(tree), path.name)
            for text in texts(tree):
                self.assertNotIn(text, ("ODRG", "show.json", "play", "brightness", "on", "off"), f"{path.name} writes out {text!r}")
        users = sorted(path.name for path, tree in modules(EMULATOR) if "json" in imported(tree))
        self.assertEqual(users, ["hub.py"])

    def test_the_only_address_a_source_names_is_127_0_0_1(self):
        addresses = []
        for package in PACKAGES:
            for path, tree in modules(package):
                for text in texts(tree):
                    if re.fullmatch(r"[0-9]+(\.[0-9]+){3}|localhost|::1?|\[::1?\]", text.strip()):
                        addresses.append((f"{package.name}/{path.name}", text))
        self.assertEqual(addresses, [("emulator/httpd.py", "127.0.0.1")])
        server = (EMULATOR / "httpd.py").read_text(encoding="utf-8")
        self.assertIn("super().__init__((ADDRESS, port), Handler)", server)
        line_port = (EMULATOR / "lineport.py").read_text(encoding="utf-8")
        self.assertIn("super().__init__((httpd.ADDRESS, port), Connection)", line_port)
        for path, tree in modules(EMULATOR):
            if path.name not in ("httpd.py", "lineport.py"):
                self.assertEqual(imported(tree) & {"socket", "socketserver", "http", "asyncio"}, set(), path.name)

    def test_the_tool_has_no_word_for_the_emulator_or_the_board(self):
        for path in sorted(TOOL.rglob("*.py")):
            words = set(re.findall(r"[a-z]+", path.read_text(encoding="utf-8").lower()))
            self.assertEqual(words & {"emulator", "emulated", "board", "pty", "ttys", "wled"}, set(), path.name)

    def test_none_of_the_proof_of_concept_tools_is_tracked(self):
        listed = subprocess.run(["git", "ls-files", "tools"], cwd=support.ROOT, capture_output=True, text=True, check=True).stdout.split()
        for name in PROOF_OF_CONCEPT_TOOLS:
            self.assertNotIn(f"tools/{name}", listed)
        tracked = subprocess.run(["git", "ls-files", "odrigctl"], cwd=support.ROOT, capture_output=True, text=True, check=True).stdout.split()
        if tracked:
            self.assertEqual(sorted(tracked), ["odrigctl/__init__.py", "odrigctl/__main__.py", "odrigctl/cli.py", "odrigctl/client.py", "odrigctl/winserial.py"])

    def test_no_commit_of_this_seed_changes_a_source_or_the_header_of_the_core(self):
        changed = subprocess.run(
            ["git", "log", "--grep=^Seed 03", "--format=", "--name-only", "--", "core/src", "core/include"],
            cwd=support.ROOT, capture_output=True, text=True, check=True,
        ).stdout.split()
        self.assertEqual(changed, [])
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "core/src", "core/include"], cwd=support.ROOT, capture_output=True, text=True, check=True).stdout
        self.assertEqual(dirty, "")

    def test_the_checks_find_what_they_look_for(self):
        tree = ast.parse("import os, ctypes.util\nfrom odrig import odrg\nfrom . import failure\nfrom .host import FolderHost\nimport numpy\nADDRESS = '0.0.0.0'\n")
        self.assertEqual(imported(tree), {"os", "ctypes", "odrig", "numpy"})
        self.assertNotIn("numpy", sys.stdlib_module_names)
        self.assertNotIn("odrig", sys.stdlib_module_names)
        self.assertIn("ctypes", sys.stdlib_module_names)
        self.assertEqual(texts(tree), ["0.0.0.0"])

    def test_every_module_is_written_in_the_grammar_of_python_3_10(self):
        for package in PACKAGES:
            for path, _ in modules(package):
                with self.subTest(path=f"{package.name}/{path.name}"):
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()

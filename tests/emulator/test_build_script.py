import contextlib
import ctypes
import importlib.util
import io
import json
import os
import pathlib
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from emulator import binding

from . import BUILD_SCRIPT, LIBRARY, ROOT

MAKEFILE = ROOT / "core" / "Makefile"
SEVEN = ["odrig_core_begin", "odrig_core_poll", "odrig_core_leg_count", "odrig_core_leg", "odrig_core_command", "odrig_core_feed", "odrig_core_error"]

# A library of Windows itself: its kernel, or one of the sets its C run-time is reached by.
OF_WINDOWS = re.compile(r"\A(kernel32|ntdll|ucrtbase|msvcrt|api-ms-win-[a-z0-9-]+)\.dll\Z")


def loaded():
    """The build script as a module."""
    spec = importlib.util.spec_from_file_location("odrig_core_build", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = loaded()


def on_the_path(*programs):
    """Stands in for the search of the path: finds these names and no other."""
    return lambda name: f"/usr/bin/{name}" if name in programs else None


def no_microsoft(environ):
    return None


def makefile_flags():
    """The flags the makefile compiles a source of the core with, its variables put in."""
    text = MAKEFILE.read_text(encoding="utf-8")
    variables = dict(re.findall(r"(?m)^([A-Z_]+) = (.+)$", text))
    return re.sub(r"\$\(([A-Z_]+)\)", lambda match: variables[match.group(1)], variables["CORE_FLAGS"]).split()


def tables(path):
    """`(imported libraries, exported names)` of a DLL, read from its file."""
    data = pathlib.Path(path).read_bytes()
    header = struct.unpack_from("<I", data, 0x3C)[0]
    if data[header:header + 4] != b"PE\0\0":
        raise AssertionError(f"{path} is no DLL")
    count, optional_size = struct.unpack_from("<H", data, header + 6)[0], struct.unpack_from("<H", data, header + 20)[0]
    optional = header + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    directories = optional + (112 if magic == 0x20B else 96)
    sections = [struct.unpack_from("<8sIIII", data, optional + optional_size + 40 * index) for index in range(count)]

    def place(address):
        for _, size, start, raw_size, raw in sections:
            if start <= address < start + max(size, raw_size):
                return raw + address - start
        raise AssertionError(f"{path}: nothing holds the address {address:#x}")

    def text(address):
        start = place(address)
        return data[start:data.index(b"\0", start)].decode("ascii")

    export_table, _, import_table, _ = struct.unpack_from("<IIII", data, directories)
    exported = []
    if export_table:
        names, name_table = struct.unpack_from("<I", data, place(export_table) + 24)[0], struct.unpack_from("<I", data, place(export_table) + 32)[0]
        exported = [text(struct.unpack_from("<I", data, place(name_table) + 4 * index)[0]) for index in range(names)]
    imported = []
    entry = place(import_table) if import_table else None
    while entry is not None:
        name = struct.unpack_from("<I", data, entry + 12)[0]
        if not name:
            break
        imported.append(text(name))
        entry += 20
    return imported, exported


class FindingTheCompiler(unittest.TestCase):
    def folder(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        return made.name

    def setUp(self):
        self.tools = pathlib.Path(self.folder(), "tools")

    def unpack(self, *parts):
        file = self.tools.joinpath(*parts)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"")
        return file

    def find(self, named=None, environ=None, programs=("g++", "clang++", "c++"), environment=no_microsoft):
        return build.find(named, environ or {}, on_the_path(*programs), self.tools, environment)

    def test_the_named_compiler_comes_first(self):
        self.unpack("gcc", "bin", "g++.exe")
        found = self.find("clang++", {"CXX": "g++-13"})
        self.assertEqual((found.kind, found.cxx), ("gnu", "clang++"))

    def test_then_the_one_the_variable_names(self):
        self.unpack("gcc", "bin", "g++.exe")
        self.assertEqual(self.find(environ={"CXX": "g++-13"}).cxx, "g++-13")

    def test_then_one_unpacked_under_tools(self):
        unpacked = self.unpack("winlibs", "mingw64", "bin", "g++.exe")
        self.assertEqual(self.find().cxx, str(unpacked))

    def test_a_compiler_deeper_than_three_folders_under_tools_is_not_looked_for(self):
        self.unpack("a", "b", "c", "bin", "g++.exe")
        self.assertEqual(self.find().cxx, "/usr/bin/g++")

    def test_under_tools_a_folder_named_bin_is_what_holds_the_compiler(self):
        self.unpack("gcc", "share", "g++.exe")
        self.unpack("gcc", "bin", "gcc.exe")
        self.assertEqual(self.find().cxx, "/usr/bin/g++")

    def test_then_the_path_with_gcc_before_clang_before_the_systems_own(self):
        self.assertEqual(self.find().cxx, "/usr/bin/g++")
        self.assertEqual(self.find(programs=("clang++", "c++")).cxx, "/usr/bin/clang++")
        self.assertEqual(self.find(programs=("c++",)).cxx, "/usr/bin/c++")

    def test_then_microsofts(self):
        folder = pathlib.Path(self.folder())
        for name in ("cl.exe", "lib.exe", "link.exe"):
            (folder / name).write_bytes(b"")
        environment = {"PATH": str(folder), "INCLUDE": "x"}
        with mock.patch.object(build.shutil, "which", lambda name, path=None: str(folder / f"{name}.exe") if path == str(folder) else None):
            found = self.find(programs=(), environment=lambda environ: environment)
        self.assertEqual((found.kind, found.cxx, found.ar, found.nm), ("msvc", str(folder / "cl.exe"), str(folder / "lib.exe"), str(folder / "link.exe")))
        self.assertIs(found.env, environment)

    def test_without_any_it_is_no_compiler_and_the_detail_says_what_to_install(self):
        with self.assertRaises(build.Failure) as caught:
            self.find(programs=())
        self.assertEqual(caught.exception.reason, "no-compiler")
        for word in ("tools/", "WinLibs", "Microsoft's C++ build tools", "--cxx"):
            self.assertIn(word, caught.exception.detail)

    def test_microsofts_compiler_that_is_named_and_not_there_is_no_compiler(self):
        with self.assertRaises(build.Failure) as caught:
            self.find("cl", programs=())
        self.assertEqual(caught.exception.reason, "no-compiler")

    def test_a_compiler_named_cl_is_microsofts_and_every_other_is_gnu_style(self):
        for program, kind in (("cl", "msvc"), ("CL.EXE", "msvc"), (r"C:\x\bin\cl.exe", "msvc"), ("clang-cl", "msvc"), ("g++", "gnu"), ("clang++", "gnu"), ("c++", "gnu"), ("x86_64-w64-mingw32-g++.exe", "gnu"), ("/opt/llvm/bin/clang++", "gnu")):
            self.assertEqual(build.kind_of(program), kind, program)

    def test_the_c_compiler_has_the_name_that_goes_with_the_cpp_compiler(self):
        for cxx, cc in (("g++", "gcc"), ("clang++", "clang"), ("c++", "cc"), ("g++-13", "gcc-13"), ("x86_64-w64-mingw32-g++.exe", "x86_64-w64-mingw32-gcc.exe")):
            self.assertEqual(build.c_compiler(cxx), cc)
        self.assertEqual(pathlib.PurePath(build.c_compiler(str(pathlib.PurePath("tools", "bin", "g++.exe")))), pathlib.PurePath("tools", "bin", "gcc.exe"))

    def test_the_other_programs_are_taken_from_the_folder_of_the_compiler(self):
        cxx = self.unpack("llvm", "bin", "clang++.exe")
        lister = self.unpack("llvm", "bin", "llvm-nm.exe")
        found = self.find()
        self.assertEqual((found.cxx, found.nm), (str(cxx), str(lister)))
        self.assertEqual(found.ar, "ar")
        self.assertEqual(build.beside(str(cxx), ("ar", "llvm-ar"), on_the_path("llvm-ar")), "/usr/bin/llvm-ar")
        self.assertEqual(build.beside(str(cxx), ("ar", "llvm-ar"), on_the_path()), "ar")


class Commands(unittest.TestCase):
    GNU = build.Toolchain("gnu", "g++", "gcc", "ar", "nm", None)
    MICROSOFT = build.Toolchain("msvc", "cl", "cl", "lib", "link", None)

    def test_a_gnu_style_compiler_gets_the_flags_of_the_makefile(self):
        command, made = build.compile_command(self.GNU, "core.cpp")
        self.assertEqual(command, ["g++", *makefile_flags(), "-c", "src/core.cpp", "-o", "build/core/core.o"])
        self.assertEqual(made, "build/core/core.o")
        self.assertIn("-Werror", command)
        self.assertIn("-fno-exceptions", command)

    def test_microsofts_compiler_gets_warnings_as_errors_and_neither_exceptions_nor_type_information(self):
        command, made = build.compile_command(self.MICROSOFT, "core.cpp")
        self.assertEqual(command[0], "cl")
        for flag in ("/W4", "/WX", "/EHs-c-", "/GR-", "/MT", "/O2", "/Iinclude"):
            self.assertIn(flag, command)
        self.assertEqual((command[-3:], made), (["/c", "src/core.cpp", "/Fobuild/core/core.obj"], "build/core/core.obj"))

    def test_every_source_of_the_core_is_found_and_none_is_listed(self):
        self.assertEqual(build.sources(), sorted(path.name for path in (ROOT / "core" / "src").glob("*.cpp")))
        self.assertGreaterEqual(len(build.sources()), 10)
        text = BUILD_SCRIPT.read_text(encoding="utf-8")
        for name in build.sources():
            self.assertNotIn(name, text)

    def test_the_exports_are_the_functions_the_header_declares(self):
        self.assertEqual(build.exports(), SEVEN)
        self.assertEqual(sorted(build.exports()), sorted(binding.FUNCTIONS))

    def test_the_shared_library_has_the_name_of_the_system(self):
        self.assertEqual([build.shared_name(platform) for platform in ("darwin", "win32", "linux")], ["libodrig_core.dylib", "odrig_core.dll", "libodrig_core.so"])
        for platform in ("darwin", "win32", "linux"):
            self.assertEqual(build.shared_name(platform), binding.library_of(platform)[0])
        self.assertRegex(MAKEFILE.read_text(encoding="utf-8"), r"(?m)^SHARED = \$\(BUILD\)/libodrig_core\.dylib$")

    def test_on_windows_a_gnu_style_link_carries_the_run_time_and_names_the_exports(self):
        command, made, definitions = build.shared_command(self.GNU, ["build/core/a.o"], "win32")
        self.assertEqual(command, ["g++", "-shared", "-static", "-o", "build/odrig_core.dll", "build/core/a.o", "build/core/odrig_core.def"])
        self.assertEqual(made, "build/odrig_core.dll")
        self.assertEqual(definitions, "EXPORTS\n" + "".join(f"    {name}\n" for name in SEVEN))

    def test_on_macos_the_link_is_the_one_of_the_makefile(self):
        command, made, definitions = build.shared_command(self.GNU, ["build/core/a.o"], "darwin")
        self.assertEqual((command, made, definitions), (["g++", "-dynamiclib", "-o", "build/libodrig_core.dylib", "build/core/a.o"], "build/libodrig_core.dylib", None))
        self.assertIn("$(CXX) -dynamiclib -o $@ $(OBJECTS)", MAKEFILE.read_text(encoding="utf-8"))

    def test_elsewhere_the_code_is_made_position_independent(self):
        self.assertEqual(build.position_independent(self.GNU, "linux"), ("-fPIC",))
        for platform in ("win32", "darwin"):
            self.assertEqual(build.position_independent(self.GNU, platform), ())
        self.assertEqual(build.position_independent(self.MICROSOFT, "win32"), ())
        self.assertEqual(build.shared_command(self.GNU, ["a.o"], "linux")[0], ["g++", "-shared", "-o", "build/libodrig_core.so", "a.o"])

    def test_microsofts_link_names_every_export(self):
        command, made, definitions = build.shared_command(self.MICROSOFT, ["build/core/a.obj"], "win32")
        self.assertEqual(command[:4], ["link", "/nologo", "/DLL", "/OUT:build/odrig_core.dll"])
        self.assertEqual([word for word in command if word.startswith("/EXPORT:")], [f"/EXPORT:{name}" for name in SEVEN])
        self.assertEqual((made, definitions), ("build/odrig_core.dll", None))

    def test_the_static_library_of_each_kind(self):
        self.assertEqual(build.static_command(self.GNU, ["a.o", "b.o"]), (["ar", "rcs", "build/libodrig_core.a", "a.o", "b.o"], "build/libodrig_core.a"))
        self.assertEqual(build.static_command(self.MICROSOFT, ["a.obj"]), (["lib", "/nologo", "/OUT:build/odrig_core.lib", "a.obj"], "build/odrig_core.lib"))


def run_main(*argv):
    """Runs one command line of the build script in this interpreter."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = build.main(list(argv))
        except SystemExit as stopped:
            status = stopped.code
    return status, out.getvalue(), err.getvalue()


class OnlyWhatChanged(unittest.TestCase):
    def test_a_file_is_made_again_when_it_is_missing_or_older_than_what_it_is_made_from(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        folder = pathlib.Path(made.name)
        for age, name in enumerate(("old.cpp", "made.o", "new.h")):
            (folder / name).write_bytes(b"")
            os.utime(folder / name, ns=(10**18 + age * 10**9, 10**18 + age * 10**9))
        with mock.patch.object(build, "CORE", folder):
            self.assertFalse(build.stale("made.o", ["old.cpp"]))
            self.assertFalse(build.stale("made.o", []))
            self.assertTrue(build.stale("made.o", ["old.cpp", "new.h"]))
            self.assertTrue(build.stale("missing.o", ["old.cpp"]))

    def test_an_object_depends_on_its_source_every_header_the_script_and_the_toolchain(self):
        needed = build.needed_by("core.cpp")
        self.assertEqual(needed[0], "src/core.cpp")
        for name in ("include/odrig_core.h", "src/core_state.h", "src/reasons.h", "build.py", "build/toolchain.json"):
            self.assertIn(name, needed)
        self.assertNotIn("src/player.cpp", needed)

    @unittest.skipIf(sys.platform == "darwin", "make builds the library on macOS")
    def test_building_again_with_nothing_changed_runs_no_step(self):
        self.assertEqual(run_main("shared"), (0, "", ""))

    @unittest.skipIf(sys.platform == "darwin", "make builds the library on macOS")
    def test_a_library_that_a_program_has_loaded_is_no_obstacle_when_nothing_changed(self):
        binding.load(LIBRARY)
        self.assertEqual(run_main("shared")[0], 0)

    @unittest.skipUnless(sys.platform == "win32", "only Windows keeps a loaded library from being written")
    def test_a_loaded_library_that_has_to_be_built_again_is_refused_with_what_to_do(self):
        binding.load(LIBRARY)
        with self.assertRaises(build.Failure) as caught:
            build.writable(f"build/{LIBRARY.name}")
        self.assertEqual(caught.exception.reason, "build-failed")
        self.assertIn(f"core/build/{LIBRARY.name}", caught.exception.detail)
        self.assertIn("stop the emulator", caught.exception.detail)

    def test_a_library_that_is_not_there_yet_may_be_built_and_the_check_makes_no_file(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        with mock.patch.object(build, "CORE", pathlib.Path(made.name)):
            build.writable("build/odrig_core.dll")
            build.writable("odrig_core.dll")
        self.assertEqual(list(pathlib.Path(made.name).iterdir()), [])

    def test_the_toolchain_is_written_down_again_only_when_it_is_another(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        folder = pathlib.Path(made.name)
        first = build.Toolchain("gnu", "g++", "gcc", "ar", "nm", None)
        with mock.patch.object(build, "BUILD", folder):
            build.record(first)
            os.utime(folder / "toolchain.json", ns=(10**18, 10**18))
            build.record(first)
            self.assertEqual((folder / "toolchain.json").stat().st_mtime_ns, 10**18)
            build.record(build.Toolchain("gnu", "clang++", "clang", "ar", "nm", None))
            self.assertNotEqual((folder / "toolchain.json").stat().st_mtime_ns, 10**18)
            self.assertEqual(json.loads((folder / "toolchain.json").read_text(encoding="utf-8"))["cxx"], "clang++")


class TheCommandLine(unittest.TestCase):
    def run_main(self, *argv):
        return run_main(*argv)

    def test_without_a_compiler_it_ends_with_1_and_one_line(self):
        with mock.patch.object(build, "find", side_effect=build.Failure("no-compiler", build.INSTALL)):
            status, out, err = self.run_main("shared")
        self.assertEqual((status, out, err), (1, "", f"error: no-compiler: {build.INSTALL}\n"))

    def test_a_step_that_fails_ends_it_with_1(self):
        script = "import sys; sys.exit(3)"
        with self.assertRaises(build.Failure) as caught, contextlib.redirect_stdout(io.StringIO()):
            build.started([sys.executable, "-c", script])
        self.assertEqual((caught.exception.reason, caught.exception.detail), ("build-failed", f"{build.stem(sys.executable)} ended with status 3"))
        with mock.patch.object(build, "find", return_value=None), mock.patch.object(build, "build_static", side_effect=caught.exception):
            status, _, err = self.run_main()
        self.assertEqual((status, err), (1, f"error: build-failed: {build.stem(sys.executable)} ended with status 3\n"))

    def test_a_program_that_is_not_there_ends_it_with_1(self):
        with self.assertRaises(build.Failure) as caught, contextlib.redirect_stdout(io.StringIO()):
            build.started([str(ROOT / "core" / "build" / "no-such-compiler")])
        self.assertEqual(caught.exception.reason, "build-failed")

    def test_a_word_it_does_not_know_is_not_understood(self):
        self.assertEqual(self.run_main("bake")[0], 2)

    def test_clean_removes_the_build_folder_and_needs_no_compiler(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        folder = pathlib.Path(made.name, "build")
        (folder / "core").mkdir(parents=True)
        (folder / "core" / "a.o").write_bytes(b"")
        with mock.patch.object(build, "BUILD", folder), mock.patch.object(build, "find", side_effect=AssertionError("looked for a compiler")):
            self.assertEqual(self.run_main("clean"), (0, "", ""))
            self.assertFalse(folder.exists())
            self.assertEqual(self.run_main("clean")[0], 0)

    def test_it_imports_only_the_standard_library(self):
        import ast

        tree = ast.parse(BUILD_SCRIPT.read_text(encoding="utf-8"), feature_version=(3, 10))
        names = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        names |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertEqual(names - set(sys.stdlib_module_names), set())


class TheLibraryOfTheSystem(unittest.TestCase):
    def test_the_binding_has_the_library_of_the_system_it_runs_on(self):
        self.assertEqual((binding.LIBRARY_NAME, binding.BUILD_COMMAND), binding.library_of(sys.platform))
        self.assertEqual(LIBRARY.name, binding.LIBRARY_NAME)

    def test_each_system_has_its_library_and_its_build_command(self):
        self.assertEqual(binding.library_of("darwin"), ("libodrig_core.dylib", "make -C core shared"))
        self.assertEqual(binding.library_of("win32"), ("odrig_core.dll", "python core/build.py shared"))
        self.assertEqual(binding.library_of("linux"), ("libodrig_core.so", "python core/build.py shared"))

    def test_a_missing_library_names_the_build_command_of_the_system(self):
        from emulator import failure

        with self.assertRaises(failure.Failure) as caught:
            binding.load(ROOT / "core" / "build" / "no-such-library")
        self.assertEqual(caught.exception.reason, "core-not-built")
        self.assertIn(f"`{binding.BUILD_COMMAND}`", caught.exception.detail)

    @unittest.skipUnless(sys.platform == "win32", "the shared library is a DLL on Windows only")
    def test_the_dll_exports_the_seven_functions_and_needs_only_libraries_of_windows(self):
        imported, exported = tables(LIBRARY)
        self.assertEqual(sorted(exported), sorted(SEVEN))
        self.assertTrue(imported)
        for name in imported:
            self.assertRegex(name.lower(), OF_WINDOWS)
        library = ctypes.CDLL(str(LIBRARY))
        for name in SEVEN:
            self.assertTrue(hasattr(library, name), name)

    @unittest.skipIf(sys.platform == "darwin", "make builds the library on macOS and writes no such file")
    def test_the_build_script_writes_down_the_toolchain_it_used(self):
        written = json.loads((ROOT / "core" / "build" / "toolchain.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(written), ["ar", "cc", "cxx", "kind", "nm"])
        self.assertIn(written["kind"], ("gnu", "msvc"))
        self.assertEqual(written["kind"], build.kind_of(written["cxx"]))


class TheRepository(unittest.TestCase):
    def git(self, *words):
        return subprocess.run(["git", *words], cwd=ROOT, capture_output=True, text=True)

    def test_the_folder_tools_is_ignored_and_holds_nothing_tracked(self):
        self.assertEqual(self.git("check-ignore", "-q", "tools/gcc/bin/g++.exe").returncode, 0)
        self.assertEqual(self.git("ls-files", "tools").stdout, "")

    def test_no_line_ending_of_a_tracked_file_is_converted(self):
        self.assertEqual((ROOT / ".gitattributes").read_bytes().split(b"\n")[0], b"* -text")
        listed = self.git("check-attr", "text", "--", "README.md", "emulator/app.py", "emulator/web/app.js", "core/src/core.cpp", "core/build.py", "animations/hello.json").stdout
        self.assertEqual(re.findall(r"(?m): text: (.+)$", listed), ["unset"] * 6)

    def test_no_tracked_text_file_holds_a_carriage_return(self):
        listed = subprocess.run(["git", "ls-files", "-z", "--", "*.py", "*.md", "*.js", "*.html", "*.css", "*.cpp", "*.h", "*.json", "*.txt"], cwd=ROOT, capture_output=True, check=True).stdout
        names = [name for name in listed.decode("utf-8").split("\0") if name]
        self.assertGreater(len(names), 200)
        with_one = [name for name in names if (ROOT / name).is_file() and b"\r" in (ROOT / name).read_bytes()]
        self.assertEqual(with_one, [])


if __name__ == "__main__":
    unittest.main()

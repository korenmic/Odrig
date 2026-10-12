"""Builds the core without GNU Make.

    python core/build.py           builds the static library in build/
    python core/build.py shared    builds the shared library the emulator loads
    python core/build.py clean     removes build/

It works with GCC or Clang, started as g++ or clang++, and with Microsoft's compiler cl.
Sources are found, never listed. Only the standard library of Python is used.

Exit status 0 means the work was done, 1 that it could not be done, with one line
`error: <reason>: <detail>` on standard error, and 2 that the command line was not
understood.
"""

import argparse
import collections
import concurrent.futures
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

CORE = pathlib.Path(__file__).resolve().parent
ROOT = CORE.parent
BUILD = CORE / "build"
TOOLS = ROOT / "tools"
HEADER = CORE / "include" / "odrig_core.h"
RECORD = "toolchain.json"

NO_COMPILER = "no-compiler"
BUILD_FAILED = "build-failed"

# The names a GNU-style compiler is looked for by: on the path, and under the folder tools/.
ON_THE_PATH = ("g++", "clang++", "c++")
IN_TOOLS = ("g++", "clang++")
TOOLS_DEPTH = 3
# The C compiler that goes with each, and the other programs of a GNU-style toolchain.
C_COMPILERS = (("clang++", "clang"), ("g++", "gcc"), ("c++", "cc"))
ARCHIVERS = ("ar", "llvm-ar")
LISTERS = ("nm", "llvm-nm")
MICROSOFT = ("cl", "clang-cl")
MICROSOFT_TOOLS = "Microsoft.VisualStudio.Component.VC.Tools.x86.x64"

WARNINGS = ("-Wall", "-Wextra", "-Wpedantic", "-Wshadow", "-Werror")
GNU_FLAGS = ("-std=c++11", "-O2", *WARNINGS, "-Wframe-larger-than=512", "-fno-exceptions", "-fno-rtti", "-Iinclude")
MICROSOFT_FLAGS = ("/nologo", "/std:c++14", "/O2", "/W4", "/WX", "/EHs-c-", "/GR-", "/MT", "/Iinclude")

INSTALL = (
    "no C++ compiler was found; unpack a GCC for Windows, such as the WinLibs build of MinGW-w64, "
    "into the folder tools/ of the repository, or install Microsoft's C++ build tools, or name a compiler with --cxx"
)

Toolchain = collections.namedtuple("Toolchain", "kind cxx cc ar nm env")
Toolchain.__doc__ = """A compiler and what goes with it.

`kind` is `gnu` or `msvc`. `env` is the environment its programs run in, or `None` for the
one of this process. With Microsoft's compiler `ar` is its librarian and `nm` its linker.
"""


class Failure(Exception):
    """The build cannot be done. It is printed as `error: <reason>: <detail>`."""

    def __init__(self, reason, detail):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail

    def line(self):
        return f"error: {self.reason}: {self.detail}"


def stem(program):
    """The name of a program without its folder and without `.exe`, in lower case."""
    name = pathlib.PurePath(str(program)).name.lower()
    return name[:-4] if name.endswith(".exe") else name


def kind_of(program):
    return "msvc" if stem(program) in MICROSOFT else "gnu"


def shared_name(platform=sys.platform):
    """The file name of the shared library on a system."""
    if platform == "win32":
        return "odrig_core.dll"
    if platform == "darwin":
        return "libodrig_core.dylib"
    return "libodrig_core.so"


def exports(header=HEADER):
    """The functions the header declares, in the order it declares them."""
    text = re.sub(r"/\*.*?\*/|//[^\n]*", " ", header.read_text(encoding="utf-8"), flags=re.S)
    return re.findall(r"\b(odrig_core_[a-z_]+)\(", text)


def in_tools(tools=TOOLS):
    """The GNU-style compilers unpacked under a folder: `g++` or `clang++` in a folder
    `bin` at most three folders down, in the order of their paths."""
    found = []
    for depth in range(TOOLS_DEPTH):
        for folder in sorted(tools.glob("/".join(["*"] * depth + ["bin"]))):
            for name in IN_TOOLS:
                for file in (folder / name, folder / f"{name}.exe"):
                    if file.is_file():
                        found.append(file)
    return found


def beside(cxx, names, which):
    """The first program of these names in the folder of a compiler, then on the path. When
    there is none, the first name, so that the step that needs it says so."""
    folder = pathlib.Path(cxx).parent
    if str(folder) not in ("", "."):
        for name in names:
            for file in (folder / name, folder / f"{name}.exe"):
                if file.is_file():
                    return str(file)
    for name in names:
        found = which(name)
        if found:
            return found
    return names[0]


def c_compiler(cxx):
    """The name of the C compiler that goes with a GNU-style C++ compiler: the same file
    name with `g++` as `gcc`, `clang++` as `clang` and `c++` as `cc`."""
    path = pathlib.PurePath(str(cxx))
    for ending, other in C_COMPILERS:
        place = path.name.lower().rfind(ending)
        if place >= 0:
            return str(path.with_name(path.name[:place] + other + path.name[place + len(ending):]))
    return str(path)


def gnu(cxx, which):
    cxx = str(cxx)
    return Toolchain("gnu", cxx, c_compiler(cxx), beside(cxx, ARCHIVERS, which), beside(cxx, LISTERS, which), None)


def microsoft_environment(environ=os.environ, run=subprocess.run):
    """The environment Microsoft's own script sets for its 64-bit compiler, or `None` when
    `vswhere` finds no installation that has the compiler."""
    base = environ.get("ProgramFiles(x86)") or environ.get("ProgramFiles")
    if not base:
        return None
    finder = pathlib.Path(base, "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if not finder.is_file():
        return None
    found = run([str(finder), "-latest", "-products", "*", "-requires", MICROSOFT_TOOLS, "-property", "installationPath"], capture_output=True, text=True)
    places = found.stdout.split("\n") if found.returncode == 0 else []
    if not places or not places[0].strip():
        return None
    script = pathlib.Path(places[0].strip(), "VC", "Auxiliary", "Build", "vcvars64.bat")
    if not script.is_file():
        return None
    shown = run(f'"{script}" >nul 2>&1 && set', shell=True, capture_output=True, text=True)
    if shown.returncode != 0:
        return None
    made = dict(line.split("=", 1) for line in shown.stdout.splitlines() if "=" in line and not line.startswith("="))
    return made if shutil.which(MICROSOFT[0], path=made.get("PATH", made.get("Path", ""))) else None


def microsoft(program, environ, which, environment):
    """Microsoft's toolchain with the compiler of this name, or `None` when there is none.

    The compiler needs the variables its own script sets. A developer prompt has them, and
    then the path has the compiler; otherwise the script's environment is taken."""
    cxx = which(program)
    given = None
    if not cxx or "INCLUDE" not in environ:
        given = environment(environ)
        if given is not None:
            cxx = cxx or shutil.which(program, path=given.get("PATH", given.get("Path", "")))
    if not cxx:
        return None

    def found(name):
        return which(name) if given is None else shutil.which(name, path=given.get("PATH", given.get("Path", "")))

    return Toolchain("msvc", str(cxx), str(cxx), found("lib") or "lib", found("link") or "link", given)


def find(named=None, environ=os.environ, which=shutil.which, tools=TOOLS, environment=microsoft_environment):
    """The toolchain to build with: the compiler that is named, the one the variable `CXX`
    names, one unpacked under `tools/`, one on the path, and then Microsoft's."""
    named = named or environ.get("CXX")
    if named:
        if kind_of(named) == "gnu":
            return gnu(named, which)
        made = microsoft(named, environ, which, environment)
        if made is None:
            raise Failure(NO_COMPILER, f"{named}: Microsoft's compiler is not on the path and no installation of it was found")
        return made
    unpacked = in_tools(tools)
    if unpacked:
        return gnu(unpacked[0], which)
    for name in ON_THE_PATH:
        found = which(name)
        if found:
            return gnu(found, which)
    made = microsoft(MICROSOFT[0], environ, which, environment)
    if made is None:
        raise Failure(NO_COMPILER, INSTALL)
    return made


def started(command, env=None):
    """Runs one step from the folder of the core, as `make -C core` does, and shows it."""
    print(" ".join(str(word) for word in command), flush=True)
    try:
        done = subprocess.run([str(word) for word in command], cwd=CORE, env=env)
    except OSError as error:
        raise Failure(BUILD_FAILED, f"{command[0]}: {error.strerror or type(error).__name__}") from None
    if done.returncode != 0:
        raise Failure(BUILD_FAILED, f"{stem(command[0])} ended with status {done.returncode}")


def all_started(commands, env=None):
    """Runs steps that do not depend on each other, several at a time."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
        for step in [pool.submit(started, command, env) for command in commands]:
            step.result()


def sources():
    return sorted(path.name for path in (CORE / "src").glob("*.cpp"))


def compile_command(toolchain, source, flags=()):
    """`(command, object)` for one source of the core, with paths as seen from `core/`."""
    name = source[: -len(".cpp")]
    if toolchain.kind == "msvc":
        made = f"build/core/{name}.obj"
        return [toolchain.cxx, *MICROSOFT_FLAGS, *flags, "/c", f"src/{source}", f"/Fo{made}"], made
    made = f"build/core/{name}.o"
    return [toolchain.cxx, *GNU_FLAGS, *flags, "-c", f"src/{source}", "-o", made], made


def position_independent(toolchain, platform=sys.platform):
    """The flag a GNU-style compiler needs for code that goes into a shared library, where
    the system does not make all code so."""
    return () if toolchain.kind == "msvc" or platform in ("win32", "darwin") else ("-fPIC",)


def compiled(toolchain):
    """Compiles every source of the core and gives the objects."""
    (BUILD / "core").mkdir(parents=True, exist_ok=True)
    (BUILD / RECORD).write_text(json.dumps({"kind": toolchain.kind, "cxx": toolchain.cxx, "cc": toolchain.cc, "ar": toolchain.ar, "nm": toolchain.nm}, indent=2) + "\n", encoding="utf-8", newline="\n")
    steps = [compile_command(toolchain, source, position_independent(toolchain)) for source in sources()]
    all_started([command for command, _ in steps], toolchain.env)
    return [made for _, made in steps]


def static_command(toolchain, objects):
    """`(command, library)` for the static library."""
    if toolchain.kind == "msvc":
        return [toolchain.ar, "/nologo", "/OUT:build/odrig_core.lib", *objects], "build/odrig_core.lib"
    return [toolchain.ar, "rcs", "build/libodrig_core.a", *objects], "build/libodrig_core.a"


def shared_command(toolchain, objects, platform=sys.platform):
    """`(command, library, definitions)` for the shared library. `definitions` is the text
    of the file that names the exports, or `None` where the link needs no such file."""
    made = f"build/{shared_name(platform)}"
    if toolchain.kind == "msvc":
        named = [f"/EXPORT:{name}" for name in exports()]
        return [toolchain.nm, "/nologo", "/DLL", f"/OUT:{made}", "/IMPLIB:build/core/odrig_core_dll.lib", *objects, *named], made, None
    if platform == "win32":
        definitions = "EXPORTS\n" + "".join(f"    {name}\n" for name in exports())
        return [toolchain.cxx, "-shared", "-static", "-o", made, *objects, "build/core/odrig_core.def"], made, definitions
    if platform == "darwin":
        return [toolchain.cxx, "-dynamiclib", "-o", made, *objects], made, None
    return [toolchain.cxx, "-shared", "-o", made, *objects], made, None


def build_static(toolchain):
    objects = compiled(toolchain)
    command, made = static_command(toolchain, objects)
    (CORE / made).unlink(missing_ok=True)
    started(command, toolchain.env)
    return made


def build_shared(toolchain):
    objects = compiled(toolchain)
    command, made, definitions = shared_command(toolchain, objects)
    if definitions is not None:
        (BUILD / "core" / "odrig_core.def").write_text(definitions, encoding="ascii", newline="\n")
    started(command, toolchain.env)
    return made


def clean():
    shutil.rmtree(BUILD, ignore_errors=True)


TARGETS = {"shared": build_shared}


def parser():
    made = argparse.ArgumentParser(
        prog="python core/build.py",
        description="Builds the core without GNU Make: the static library, or what the word names.",
    )
    made.add_argument("target", metavar="TARGET", nargs="?", choices=sorted([*TARGETS, "clean"]), help="shared: the shared library the emulator loads; clean: removes core/build/")
    made.add_argument("--cxx", metavar="PROGRAM", help="the C++ compiler: g++, clang++ or cl, by name or by path")
    return made


def main(argv=None):
    arguments = parser().parse_args(argv)
    try:
        if arguments.target == "clean":
            clean()
            return 0
        toolchain = find(arguments.cxx)
        TARGETS.get(arguments.target, build_static)(toolchain)
    except Failure as failed:
        print(failed.line(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

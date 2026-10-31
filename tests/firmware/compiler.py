"""Compile host fixtures with the compiler and runtime checks the core supports."""
import pathlib
import subprocess
import sys
from unittest import mock

from core import build as core_build


def compiled(sources, output, includes=(), language="c++"):
    output = pathlib.Path(output)
    if sys.platform == "win32" and output.suffix != ".exe":
        output = output.with_name(output.name + ".exe")
    output.parent.mkdir(parents=True, exist_ok=True)
    toolchain = core_build.find()
    with mock.patch.object(core_build, "CORE", output.parent), mock.patch.object(core_build, "BUILD", output.parent / "build"):
        description, checks = core_build.checks(toolchain)
    if toolchain.kind == "msvc":
        standard = ["/std:c++17", "/EHsc"] if language == "c++" else ["/std:c11", "/TC"]
        flags = ["/nologo", *standard, "/Od", "/W4", "/WX", "/MT", "/D_CRT_SECURE_NO_WARNINGS", *checks]
        command = [toolchain.cxx, *flags, *[f"/I{folder}" for folder in includes], *map(str, sources), f"/Fe{output}"]
    else:
        flags = ["-std=c++11" if language == "c++" else "-std=c99", "-Wall", "-Wextra", "-Werror", "-g", *checks]
        if sys.platform == "win32":
            flags.append("-static")
        language_flags = [] if language == "c++" else ["-x", "c"]
        command = [toolchain.cxx, *language_flags, *flags, *[f"-I{folder}" for folder in includes], *map(str, sources), "-o", str(output)]
    result = subprocess.run(command, cwd=output.parent, env=toolchain.env, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise AssertionError(f"the firmware host fixture does not compile ({description}):\n{result.stderr}")
    return output

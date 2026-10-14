"""Helpers shared by the tests of the pages: which files they are and how a page is read."""

import collections
import contextlib
import functools
import importlib.util
import io
import json
import pathlib
import re
import shlex
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "firmware"

if str(FIRMWARE) not in sys.path:
    sys.path.insert(0, str(FIRMWARE))

# The pages a newcomer reads first, by their paths in the repository.
PAGES = ("AGENTS.md", "CLAUDE.md", "agent/README.md", "agent/vocabulary.md", "agent/working-rules.md", "agent/getting-started.md", "agent/animation-guide.md")

ENTRY = "AGENTS.md"
ENTRY_LINES = 150
PAGE_LINES = 200

# What a page may name although no clone holds it: what is made on the computer.
MADE_ON_THE_COMPUTER = ("build/", "core/build/", ".venv/", ".codex/", "converter/node_modules/")
# Where what is fetched or tried on a computer goes. Git ignores both.
FETCHED_OR_TRIED = ("tools/", "scratch/")
# Folders that exist untracked on the first computer only, and that nobody changes.
FIRST_COMPUTER_ONLY = ("esp32-backup/", "firmware/wled-16.0.1/")
# The files of an installed file set that no tracked file is named after.
INSTALLED_NAMES = ("mapping.json",)
# What a page gives as something for the reader to make.
TO_BE_MADE = ("odrig/generators/dot.py",)
# A seed that the pages name and that a branch holds once it is up to date with `master`.
SEEDS_ON_MASTER = ("project-seeds/11-p0-emulator-and-tools-on-windows/",)
# How a page names a branch of the remote.
REMOTE_BRANCHES = "origin/"

PYTHONS = (".venv/bin/python", "python", "python3")
# The Python of the environment as Windows writes it. A command that starts it is checked
# as one that starts Python.
WINDOWS_PYTHON = ".venv\\Scripts\\python"
BUILD_SCRIPT = "core/build.py"
# The program that runs the converter and the file it is given, and the program that
# installs the converter's packages and runs its suite, with the two ways it is run.
NODE = "node"
CONVERTER = "converter/odrig.js"
NPM = "npm"
NPM_COMMANDS = (["ci", "--prefix", "converter"], ["test", "--prefix", "converter"])
# Programs of the system a page may use in a command, which have nothing to check.
PLAIN_PROGRAMS = ("mkdir", "printf", "rm", "cd", "curl")
GIT_SUBCOMMANDS = ("clone", "add", "commit", "show", "status", "branch", "switch", "merge", "fetch", "push", "log", "diff", "worktree")

Block = collections.namedtuple("Block", "heading mark body")

_FENCE = re.compile(r"(?ms)^```([a-z]*)\n(.*?)^```$")
_FILE_NAME = re.compile(r"[A-Za-z0-9_.-]+\.(?:md|json|py|txt|ini|cpp|h|js|html|css|patch)")
_PATH = re.compile(r"[A-Za-z0-9_.<>*-]*(?:/[A-Za-z0-9_.<>*-]*)+")


def read(page):
    return (ROOT / page).read_text(encoding="utf-8")


def prose(text):
    """A page without its fenced blocks."""
    return _FENCE.sub("", text)


def headings(text):
    """Every heading of a page, of any level, in order."""
    return re.findall(r"(?m)^#+ (.+)$", prose(text))


def anchor(heading):
    """The name by which a link reaches a heading."""
    kept = re.sub(r"[^a-z0-9 _-]", "", heading.lower())
    return kept.replace(" ", "-")


def section(text, heading):
    """The text under a heading of the second level, to the next one."""
    return text.split(f"\n## {heading}\n")[1].split("\n## ")[0]


def blocks(text):
    """The fenced blocks of a page, each with the second-level heading it stands under."""
    found = []
    for match in _FENCE.finditer(text):
        above = re.findall(r"(?m)^## (.+)$", prose(text[:match.start()]))
        found.append(Block(above[-1] if above else None, match.group(1), match.group(2)))
    return found


def commands(body):
    """The commands of a block: one to a line, a line that ends in a backslash going on."""
    joined = re.sub(r"\\\n\s*", "", body)
    return [line.strip() for line in joined.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def page_commands(text):
    """`(heading, command)` for every command of the `sh` blocks of a page."""
    return [(block.heading, command) for block in blocks(text) if block.mark == "sh" for command in commands(block.body)]


def spans(text):
    """The code spans in the prose of a page."""
    return re.findall(r"`([^`\n]+)`", prose(text))


def links(text):
    """The target of every link in the prose of a page."""
    return re.findall(r"\]\(([^)\s]+)\)", prose(text))


def tracked(*patterns):
    """The paths git tracks, all of them or those under the given paths."""
    listed = subprocess.run(["git", "ls-files", "-z", "--", *patterns], cwd=ROOT, capture_output=True, check=True).stdout
    return sorted(name for name in listed.decode("utf-8").split("\0") if name)


@functools.lru_cache(maxsize=None)
def present():
    """The files of the repository that git tracks or would track: none that it ignores."""
    listed = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, check=True).stdout
    return frozenset(name for name in listed.decode("utf-8").split("\0") if name and (ROOT / name).exists())


def governing():
    """The documents that define the project: the README and the documents that are no page."""
    return ["README.md"] + sorted(f"docs/{path.name}" for path in (ROOT / "docs").glob("*.md") if f"docs/{path.name}" not in PAGES)


def is_path(word):
    """Whether a word of a page reads as a path or a file of the repository."""
    if ":" in word or word.startswith(("<", "-", "(", "/")):
        return False
    return bool(_FILE_NAME.fullmatch(word) or _PATH.fullmatch(word))


def looked_for(word):
    """Whether a path must exist in a clone: not one that is made on the computer."""
    apart = MADE_ON_THE_COMPUTER + FETCHED_OR_TRIED + FIRST_COMPUTER_ONLY + (REMOTE_BRANCHES,)
    return not word.startswith(apart) and word not in INSTALLED_NAMES + TO_BE_MADE + SEEDS_ON_MASTER


def on_master(word):
    """Whether `master`, here or on the remote, holds a folder."""
    for branch in ("master", "origin/master"):
        listed = subprocess.run(["git", "ls-tree", "-d", "--name-only", branch, "--", word.rstrip("/")], cwd=ROOT, capture_output=True)
        if listed.returncode == 0 and listed.stdout.strip():
            return True
    return False


def exists(word):
    """Whether a clone holds what a path names: a file, or a folder with a file in it. A bare
    file name is one any folder holds, and a word in capitals, or one in angle brackets,
    stands for any name."""
    plain = word.rstrip("/")
    if plain in present() or any(name.startswith(plain + "/") for name in present()):
        return True
    names = present() if "/" in word else {name.rsplit("/", 1)[-1] for name in present()}
    if plain in names:
        return True
    pattern = re.sub(r"<[^>]*>|[A-Z]{2,}", "*", plain)
    if pattern == plain:
        return False
    shape = re.compile("[^/]+".join(re.escape(part) for part in pattern.split("*")) + r"(?:/.*)?")
    return any(shape.fullmatch(name) for name in names)


def understood(parse, arguments):
    """What a command-line parser says against the arguments: nothing when it takes them."""
    said = io.StringIO()
    with contextlib.redirect_stderr(said), contextlib.redirect_stdout(io.StringIO()):
        try:
            parse(arguments)
        except SystemExit as stopped:
            return said.getvalue().strip() or f"it stopped with status {stopped.code}"
    return None


@functools.lru_cache(maxsize=None)
def build_script():
    """The build script of the core as a module."""
    spec = importlib.util.spec_from_file_location("odrig_core_build", ROOT / BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _python(words):
    """What is wrong with a command that starts Python: a module, the firmware tool, or
    the build script of the core."""
    from emulator import app
    from fwtool import cli as firmware
    from odrig import cli as converter
    from odrigctl import cli as tool

    if words == ["--version"]:
        return None
    if words[:1] == ["firmware/fw.py"]:
        return understood(firmware.parser().parse_args, words[1:])
    if words[:1] == [BUILD_SCRIPT]:
        return understood(build_script().parser().parse_args, words[1:])
    if words[:1] != ["-m"] or len(words) < 2:
        return "it starts neither a module nor the firmware tool"
    module, rest = words[1], words[2:]
    if module == "odrig":
        return understood(converter.build_parser().parse_args, rest) if rest else None
    if module == "emulator":
        return understood(app.parse, rest) if rest else None
    if module == "odrigctl":
        if not rest:
            return None
        made = tool.parser()
        return understood(lambda given: tool.command_line(made, made.parse_args(given)), rest)
    if module == "preview":
        import preview
        return understood(preview.parser().parse_args, rest) if rest else None
    if module == "unittest":
        if rest[:2] != ["discover", "-s"] or rest[3:] != ["-t", "."]:
            return "a suite is selected by discovery: -m unittest discover -s FOLDER -t ."
        return None if any((ROOT / rest[2]).glob("test_*.py")) else f"{rest[2]} holds no test"
    if module == "venv":
        return None if rest == [".venv"] else "the environment is .venv"
    if module == "pip":
        return None if rest == ["install", "-r", "requirements.txt"] else "pip installs the libraries of requirements.txt"
    if (ROOT / (module.replace(".", "/") + ".py")).is_file():
        return None
    return f"there is no module {module}"


# What Node.js is given to put a command line before the converter: the tool's check of the
# version of Node.js, then its parser. It prints what the tool says against the command
# line, or nothing.
_ASK_THE_CONVERTER = """
const [version, parser, ...given] = process.argv.slice(1);
const old = (await import(version)).refusal(process.versions.node);
if (old !== null) {
  console.log(old);
} else {
  try {
    (await import(parser)).parse(given);
  } catch (error) {
    if (error.name !== "UsageError") {
      throw error;
    }
    console.log(error.message);
  }
}
"""


@functools.lru_cache(maxsize=None)
def _converter(arguments):
    """What the converter says against the arguments of a command line: nothing when it
    takes them. Its parser is asked, and nothing of the command is run."""
    node = shutil.which(NODE)
    if node is None:
        return f'Node.js 20 or later is needed as `{NODE}` to put this command before the converter: see docs/converter.md, "Setup"'
    modules = [(ROOT / "converter" / "cli" / name).as_uri() for name in ("version.js", "arguments.js")]
    asked = subprocess.run([node, "--input-type=module", "--eval", _ASK_THE_CONVERTER, "--", *modules, *arguments], cwd=ROOT, capture_output=True, text=True)
    if asked.returncode != 0:
        return f"the parser of the converter could not be asked: {asked.stderr.strip()}"
    return asked.stdout.strip() or None


def _node(words):
    """What is wrong with a command that starts Node.js: it starts the converter."""
    if words == ["--version"]:
        return None
    if words[:1] != [CONVERTER]:
        return f"{NODE} starts the converter: {NODE} {CONVERTER}"
    return _converter(tuple(words[1:])) if words[1:] else None


def _npm(words):
    """What is wrong with a command of npm: it installs the packages of the converter, or
    runs the converter's suite."""
    if words not in NPM_COMMANDS:
        return "npm is run as " + " or as ".join(f"{NPM} {' '.join(command)}" for command in NPM_COMMANDS)
    if not (ROOT / "converter" / "package-lock.json").is_file():
        return "converter/ has no package-lock.json"
    package = json.loads((ROOT / "converter" / "package.json").read_text(encoding="utf-8"))
    if words[0] == "test" and "test" not in package.get("scripts", {}):
        return "converter/package.json has no script test"
    return None


def _make(words):
    makefile = (ROOT / "core" / "Makefile").read_text(encoding="utf-8")
    targets = re.search(r"(?m)^\.PHONY: (.+)$", makefile).group(1).split()
    if words[:2] != ["-C", "core"]:
        return "make is run as make -C core"
    for word in words[2:]:
        if "=" not in word and word not in targets:
            return f"the makefile has no target {word}"
    return None


def refusal(command):
    """What is wrong with a command a page gives, or nothing: the tool it names is asked."""
    words = shlex.split(command.replace(WINDOWS_PYTHON, "python").split(" > ")[0])
    program, rest = words[0], words[1:]
    if program in PYTHONS:
        return _python(rest)
    if program == NODE:
        return _node(rest)
    if program == NPM:
        return _npm(rest)
    if program == "make":
        return _make(rest)
    if program == "git":
        return None if rest and rest[0] in GIT_SUBCOMMANDS else "a git command this test does not know"
    if program in PLAIN_PROGRAMS:
        return None
    return f"{program} is a program this test does not know"


def is_command(span):
    """Whether a code span of the prose is a command: it starts one of the checked programs."""
    words = span.split()
    return len(words) > 1 and words[0] in PYTHONS + (WINDOWS_PYTHON, NODE, NPM, "make", "git")

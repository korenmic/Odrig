"""WLED's source: fetched at the pinned tag into the shared toolchains, copied into the
checkout's work folder, checked, and patched there."""

import pathlib
import contextlib
import shutil
import subprocess
import sys
import tempfile

from . import Failure, env, paths, process

TEMPLATE = paths.FIRMWARE / "platformio_override.ini.in"
OVERRIDE_NAME = "platformio_override.ini"
PLACEHOLDER = "@REPO@"

URL = "https://github.com/wled/WLED.git"
TAG = "v16.0.1"
COMMIT = "29b389df1c1aaec6ff53aea742d17063b985906c"


def _git(folder, *arguments):
    return process.run(["git", "-C", str(folder), *arguments], capture_output=True, text=True, env=env.child())


@contextlib.contextmanager
def staging(folder):
    """A uniquely owned sibling, never a preexisting contributor's partial copy."""
    parent = pathlib.Path(folder).resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    partial = pathlib.Path(tempfile.mkdtemp(prefix='.odrig-wled-', dir=parent))
    partial.rmdir()
    try:
        yield partial
    finally:
        if partial.exists():
            if partial.resolve().parent != parent or not partial.name.startswith('.odrig-wled-'):
                raise Failure('setup-failed', 'refusing cleanup outside the owned source staging folder')
            shutil.rmtree(partial)


def fetch(folder=paths.WLED_SOURCE, url=URL, tag=TAG):
    """Clones WLED at the tag into the folder, unless the folder is there already."""
    folder = paths.output(folder)
    if folder.exists():
        return False
    with staging(folder) as partial:
        done = process.run(["git", "clone", "--config", "core.autocrlf=false", "--depth", "1", "--branch", tag, url, str(partial)], capture_output=True, text=True, env=env.child())
        if done.returncode != 0:
            raise Failure("setup-failed", f"git clone of {url} at {tag} failed: {done.stderr.strip()[-300:]}")
        partial.rename(folder)
    return True


def copy_command(source, folder, platform=sys.platform):
    """The command that copies a folder whole, sharing the blocks of its files where the file
    system can: a clone on macOS, a reflink on Linux. None where there is no such command."""
    if platform == "darwin":
        return ["cp", "-c", "-R", str(source), str(folder)]
    if platform.startswith("linux"):
        return ["cp", "--reflink=auto", "-R", str(source), str(folder)]
    return None


def copy(source=paths.WLED_SOURCE, folder=paths.WLED):
    """Gives the checkout its own copy of WLED's source, with its git folder and whatever the
    source holds besides, unless the copy is there already or is the source itself."""
    folder = paths.output(folder)
    if folder.exists() or pathlib.Path(source).resolve() == folder.resolve():
        return False
    with staging(folder) as partial:
        command = copy_command(source, partial)
        if command is None:
            shutil.copytree(source, partial, symlinks=True)
        else:
            done = process.run(command, capture_output=True, text=True)
            if done.returncode != 0:
                raise Failure("setup-failed", f"copying {source} into {partial} failed: {done.stderr.strip()[-300:]}")
        partial.rename(folder)
    return True


def check(folder=paths.WLED, commit=COMMIT):
    """Refuses a folder that is not a checkout of its own at the pinned commit."""
    top = _git(folder, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or pathlib.Path(top.stdout.strip()).resolve() != pathlib.Path(folder).resolve():
        raise Failure("wled-mismatch", f"{folder} is not a git checkout of its own")
    head = _git(folder, "rev-parse", "HEAD").stdout.strip()
    if head != commit:
        raise Failure("wled-mismatch", f"{folder} is at commit {head or 'none'}, not at {commit}")


def patch_files(folder=paths.PATCHES):
    """The patch files of a folder, in the order of their names."""
    return sorted(pathlib.Path(folder).glob("*.patch"), key=lambda path: path.name)


def restore_and_patch(folder=paths.WLED, patches=paths.PATCHES, commit=COMMIT):
    """Brings the tracked files back to the pinned commit and applies every patch file.
    Without a folder of patches the files stay WLED's own."""
    check(folder, commit)
    for arguments in (("checkout", "--", "."), ("clean", "-fdq")):
        done = _git(folder, *arguments)
        if done.returncode != 0:
            raise Failure("wled-mismatch", f"git {arguments[0]} in {folder} failed: {done.stderr.strip()[-300:]}")
    applied = []
    for patch in patch_files(patches) if patches is not None else []:
        done = _git(folder, "apply", "--whitespace=nowarn", str(patch.resolve()))
        if done.returncode != 0:
            raise Failure("patch-failed", f"{patch.name} does not apply: {done.stderr.strip()[-300:]}")
        applied.append(patch.name)
    return applied


def override_text(root=paths.ROOT, template=TEMPLATE):
    """The override file: the template with the repository's path in place of @REPO@."""
    root = str(pathlib.Path(root).resolve())
    if any(character.isspace() for character in root):
        raise Failure("build-failed", f"the repository's path, {root!r}, has a space in it, which the library entries of the build cannot carry")
    return pathlib.Path(template).read_text().replace(PLACEHOLDER, root)


def write_override(folder=paths.WLED, root=paths.ROOT, template=TEMPLATE):
    """Writes the override file into WLED's folder, unless it is there with this content."""
    path = paths.output(pathlib.Path(folder) / OVERRIDE_NAME)
    text = override_text(root, template)
    if not path.is_file() or path.read_text() != text:
        path.write_text(text)
    return path

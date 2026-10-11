"""WLED's source in the work folder: fetched at the pinned tag, checked, and patched."""

import pathlib
import subprocess

from . import Failure, env, paths

TEMPLATE = paths.FIRMWARE / "platformio_override.ini.in"
OVERRIDE_NAME = "platformio_override.ini"
PLACEHOLDER = "@REPO@"

URL = "https://github.com/wled/WLED.git"
TAG = "v16.0.1"
COMMIT = "29b389df1c1aaec6ff53aea742d17063b985906c"


def _git(folder, *arguments):
    return subprocess.run(["git", "-C", str(folder), *arguments], capture_output=True, text=True, env=env.child())


def fetch(folder=paths.WLED, url=URL, tag=TAG):
    """Clones WLED at the tag into the folder, unless the folder is there already."""
    folder = paths.output(folder)
    if folder.exists():
        return False
    folder.parent.mkdir(parents=True, exist_ok=True)
    done = subprocess.run(["git", "clone", "--depth", "1", "--branch", tag, url, str(folder)], capture_output=True, text=True, env=env.child())
    if done.returncode != 0:
        raise Failure("setup-failed", f"git clone of {url} at {tag} failed: {done.stderr.strip()[-300:]}")
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

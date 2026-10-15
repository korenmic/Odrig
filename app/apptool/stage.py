"""The folder handed to Capacitor: the web code as it is, the converter's library beside
it, and a note of what it was built from."""

import json
import shutil
import subprocess

from . import Failure, paths

NOTE = "build.json"


def _git(*arguments):
    done = subprocess.run(["git", *arguments], cwd=paths.ROOT, capture_output=True, text=True)
    if done.returncode != 0:
        raise Failure("build-failed", f"git {' '.join(arguments)}: {done.stderr.strip()}")
    return done.stdout


def note():
    """The commit the web code is built from, and whether the folder of the app holds a
    change that is not committed."""
    return {"commit": _git("rev-parse", "HEAD").strip(), "changed": _git("status", "--porcelain", "--", "app") != ""}


def staged(folder=paths.STAGED, source=paths.WWW, made_from=None, library=paths.CONVERTER_LIB):
    """Makes the folder anew: every file of the web code, every script of the converter's
    library under `converter/`, and the note."""
    shutil.rmtree(folder, ignore_errors=True)
    shutil.copytree(source, folder)
    beside = folder / paths.LIBRARY_FOLDER
    beside.mkdir()
    for script in sorted(library.glob("*.js")):
        shutil.copyfile(script, beside / script.name)
    (folder / NOTE).write_text(json.dumps(note() if made_from is None else made_from) + "\n", encoding="utf-8")
    return folder

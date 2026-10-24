"""Shows one finished animation in the emulator: `python -m preview FILE`.

The converter packs a show without items, the emulator starts on it, and the file is
uploaded into it as the show's only item, the way an animation reaches the board. Every
judgement of the file is the core's or the converter's: this program only carries it."""

import argparse
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import webbrowser

from emulator import app
from odrigctl import client, content

ROOT = app.ROOT
CONVERTER = ROOT / "converter" / "odrig.js"
EMPTY_SHOW = ROOT / "shows" / "preview" / "show.json"
MAPPING = ROOT / "mapping" / "legs-20.json"
WORK = ROOT / "build" / "preview"
PAGE_PORT = app.PORT
NAME = "preview.odrg"
TIMEOUT_SECONDS = 10.0
STOP_SECONDS = 10
WINDOWS = sys.platform == "win32"
# The emulator is a group of its own, so that an interrupt reaches it however the preview
# is stopped.
OWN_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
STOP = getattr(signal, "CTRL_BREAK_EVENT", signal.SIGINT)
WAIT_STEP_SECONDS = 0.2


class Refused(Exception):
    """What ends the preview with status 1: one line that says why."""


def parser():
    made = argparse.ArgumentParser(prog="python -m preview", description="Shows one finished animation in the emulator, until Ctrl-C.")
    made.add_argument("file", metavar="FILE", help="the .odrg file to show")
    made.add_argument("--mapping", metavar="FILE", default=str(MAPPING), help="the mapping file of the canvas (default: mapping/legs-20.json)")
    made.add_argument("--no-browser", action="store_true", help="print the address of the page and open no browser")
    made.add_argument("--core", metavar="PATH", default=str(app.LIBRARY), help=f"the core's shared library (default: core/build/{app.binding.LIBRARY_NAME})")
    return made


def canvas_of_mapping(text):
    """The width and the height of the canvas of a mapping file: a file of rows has its
    width and as many rows as its legs name, a file of columns its height and as many
    columns as its legs name."""
    mapping = json.loads(text)
    if "width" in mapping:
        return mapping["width"], sum(len(leg["rows"]) for leg in mapping["legs"])
    return sum(len(leg["columns"]) for leg in mapping["legs"]), mapping["height"]


def converter(node, *arguments):
    """Runs the converter as a program. Gives its exit status and what it printed."""
    done = subprocess.run([node, str(CONVERTER), *map(str, arguments)], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def checked(node, file):
    """The canvas of the file as the converter reads it, or the converter's refusal."""
    status, out, err = converter(node, "check", file, "--format", "odrg")
    if status != 0:
        # The converter's line is `error: <reason>: <detail>`.
        said = err.strip().splitlines()[-1] if err.strip() else f"error: the converter ended with status {status}"
        raise Refused(f"{file} is refused: {said.removeprefix('error: ').split(':', 1)[0]}")
    width, height = re.search(r"^canvas: (\d+)x(\d+)$", out, re.M).groups()
    return int(width), int(height)


def packed(node, mapping, work):
    """The folder of a show without items, as the converter packs it."""
    sources = work / "sources"
    sources.mkdir()
    status, _, err = converter(node, "pack", "--show", EMPTY_SHOW, "--mapping", mapping, "--sources", sources, "--out", work / "show")
    if status != 0:
        raise Refused(f"the converter could not pack the show: {err.strip()}")
    return work / "show"


def started(folder, work, core, port):
    """The emulator on a folder, as a child, and the address of its page. None when the
    port of the page is taken."""
    command = [sys.executable, "-m", "emulator", str(folder), "--port", str(port), "--core", str(core)]
    command += ["--tcp-port", "0"] if WINDOWS else ["--serial-link", str(work / "serial")]
    child = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=OWN_GROUP,
                             start_new_session=not WINDOWS)
    for line in child.stdout:
        if line.startswith("page: "):
            return child, line[len("page: "):].strip()
    err = child.stderr.read()
    child.wait()
    if "address-in-use" in err:
        return None, None
    raise Refused(f"the emulator did not start: {err.strip()}")


def stopped(child):
    """Ends the emulator: an interrupt to its group, and a kill when that is not enough."""
    if child.poll() is None:
        try:
            if WINDOWS:
                child.send_signal(STOP)
            else:
                os.killpg(child.pid, STOP)
        except OSError:
            pass
        try:
            child.wait(timeout=STOP_SECONDS)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
    for stream in (child.stdout, child.stderr):
        stream.close()


def uploaded(address, data, file, canvas, mapping):
    """Uploads the file as the show's only item. A reply that is no success is refused."""
    with client.Session(http=address, timeout=TIMEOUT_SECONDS) as session:
        reply = content.upload(session, 1, NAME, data)
    if content.is_ok(reply):
        return
    answer = json.loads(reply)
    if answer.get("reason") == "size-mismatch":
        width, height = canvas_of_mapping(pathlib.Path(mapping).read_text(encoding="utf-8"))
        raise Refused(f"{file} is {canvas[0]} x {canvas[1]}, and the mapping {mapping} is {width} x {height}")
    raise Refused(f"{file} is refused: {answer.get('reason') or answer.get('error')}")


def run(arguments):
    file = pathlib.Path(arguments.file)
    if not file.is_file():
        raise Refused(f"{arguments.file}: there is no file there")
    mapping = pathlib.Path(arguments.mapping)
    if not mapping.is_file():
        raise Refused(f"{arguments.mapping}: there is no mapping file there")
    if not pathlib.Path(arguments.core).is_file():
        raise Refused(f"the core's library is not built: {arguments.core}; run `make -C core shared`, as \"Set up\" in agent/getting-started.md has it")
    node = shutil.which("node")
    if node is None:
        raise Refused("Node.js is not there; see \"What you need\" in agent/getting-started.md")
    canvas = checked(node, file)
    data = file.read_bytes()
    work = WORK / str(os.getpid())
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    child = None
    try:
        folder = packed(node, mapping, work)
        child, page = started(folder, work, arguments.core, PAGE_PORT)
        if child is None:
            child, page = started(folder, work, arguments.core, 0)
            print(f"preview: port {PAGE_PORT} is taken; the page is on {page.rstrip('/').rsplit(':', 1)[1]}", file=sys.stderr)
        uploaded(page.removeprefix("http://").rstrip("/"), data, file, canvas, mapping)
        print(f"page: {page}", flush=True)
        if not arguments.no_browser and not webbrowser.open(page):
            print("preview: no browser could be opened; open the address above", file=sys.stderr)
        try:
            return waited(child)
        except KeyboardInterrupt:
            return 0
    finally:
        if child is not None:
            stopped(child)
        shutil.rmtree(work, ignore_errors=True)


def waited(child):
    """The exit status of the emulator, once it ends. The wait comes back now and then, so
    that Ctrl+Break, which Windows does not let interrupt a wait without a limit, is taken."""
    while True:
        try:
            return child.wait(timeout=WAIT_STEP_SECONDS)
        except subprocess.TimeoutExpired:
            pass


def interrupted(*_):
    """A termination, and Ctrl+Break on Windows, end the preview as Ctrl-C does."""
    raise KeyboardInterrupt


def main(argv=None):
    arguments = parser().parse_args(argv)
    signal.signal(signal.SIGTERM, interrupted)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, interrupted)
    try:
        return run(arguments)
    except Refused as refused:
        print(f"preview: {refused}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


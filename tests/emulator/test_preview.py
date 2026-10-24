import ast
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest

import preview
from odrigctl import client
from tests.core import support as core_support

from . import support

TWO_LEGS = support.ROOT / "mapping" / "legs-2.json"
WAIT_SECONDS = 30


class Preview:
    """`python -m preview` as a child process, with the repository on the module path
    wherever it is run from."""

    def __init__(self, *arguments, cwd=support.ROOT, path=None):
        environment = dict(os.environ, PYTHONPATH=str(support.ROOT))
        if path is not None:
            environment["PATH"] = path
        self.process = subprocess.Popen([sys.executable, "-m", "preview", *map(str, arguments), "--no-browser"], cwd=cwd, env=environment,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)

    def page(self):
        """The address of the page, once the preview printed it."""
        line = self.process.stdout.readline()
        if not line.startswith("page: "):
            self.process.kill()
            raise AssertionError(f"the preview printed {line!r} and {self.process.stderr.read()!r}")
        return line[len("page: "):].strip()

    def interrupt(self):
        """Ctrl-C. Gives the exit status and what the preview wrote to standard error."""
        os.killpg(self.process.pid, signal.SIGINT)
        return self.ended()

    def ended(self):
        try:
            self.process.wait(timeout=WAIT_SECONDS)
        except subprocess.TimeoutExpired:
            self.process.kill()
            raise
        err = self.process.stderr.read()
        self.process.stdout.close()
        self.process.stderr.close()
        return self.process.returncode, err


def answer(page, line):
    address = page.removeprefix("http://").rstrip("/")
    with client.Session(http=address, timeout=5) as session:
        return json.loads(session.exchange(f"{line}\n".encode("ascii")))


def listening(page):
    port = int(page.rstrip("/").rsplit(":", 1)[1])
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", port)) == 0


def previews_left():
    folder = support.ROOT / "build" / "preview"
    return sorted(path.name for path in folder.iterdir()) if folder.is_dir() else []


class OneAnimation(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.before = previews_left()

    def assert_nothing_left(self, page=None):
        if page is not None:
            self.assertFalse(listening(page), "the emulator still listens")
        self.assertEqual(previews_left(), self.before)

    def test_a_file_plays_alone_until_the_preview_is_interrupted(self):
        data = core_support.example_show()["hello.odrg"]
        file = self.work / "My Hello world.odrg"
        file.write_bytes(data)
        started = Preview(file, "--mapping", TWO_LEGS)
        page = started.page()
        self.assertRegex(page, r"\Ahttp://127\.0\.0\.1:[0-9]+/\Z")
        listed = answer(page, "list")
        self.assertEqual(listed["items"], [{"id": 1, "file": "preview.odrg", "bytes": len(data), "ignored": False}])
        time.sleep(1.2)
        status = answer(page, "status")
        self.assertEqual((status["on"], status["brightness"], status["playing"], status["animation"], status["error"]), (True, 255, "all", 1, None))
        self.assertGreaterEqual(status["fps"], 45)
        shown = [path for path in (support.ROOT / "build" / "preview").glob("*/show/preview.odrg")]
        self.assertEqual([path.read_bytes() for path in shown], [data])
        self.assertEqual(started.interrupt(), (0, ""))
        self.assert_nothing_left(page)
        self.assertEqual(file.read_bytes(), data)

    def test_a_relative_path_and_the_installations_canvas_by_default(self):
        data = core_support.clip(3, 60, 60, (40,) * 5)
        (self.work / "clip.odrg").write_bytes(data)
        started = Preview("clip.odrg", cwd=self.work)
        page = started.page()
        self.assertEqual(answer(page, "list")["items"], [{"id": 1, "file": "preview.odrg", "bytes": len(data), "ignored": False}])
        self.assertEqual(answer(page, "status")["error"], None)
        self.assertEqual(started.process.send_signal(signal.SIGTERM), None)
        self.assertEqual(started.ended(), (0, ""))
        self.assert_nothing_left(page)

    def test_a_path_with_nothing_there_and_a_folder_are_refused_before_anything_starts(self):
        for path in (self.work / "absent.odrg", self.work):
            with self.subTest(path=path.name):
                began = time.monotonic()
                status, err = Preview(path).ended()
                self.assertEqual((status, err), (1, f"preview: {path}: there is no file there\n"))
                self.assertLess(time.monotonic() - began, 5)
                self.assert_nothing_left()

    def test_a_file_that_is_no_odrg_file_is_refused_with_its_reason(self):
        file = self.work / "noise.odrg"
        file.write_bytes(bytes(range(256)))
        self.assertEqual(Preview(file).ended(), (1, f"preview: {file} is refused: bad-magic\n"))
        cut = self.work / "cut.odrg"
        cut.write_bytes(core_support.example_show()["hello.odrg"][:-3])
        status, err = Preview(cut, "--mapping", TWO_LEGS).ended()
        self.assertEqual((status, err.count("\n")), (1, 1))
        self.assertRegex(err, r"\Apreview: .*cut\.odrg is refused: [a-z-]+\n\Z")
        self.assert_nothing_left()

    def test_a_file_of_another_canvas_names_both_canvases(self):
        file = self.work / "tall.odrg"
        file.write_bytes(core_support.clip(4, 60, 60, (40,) * 3))
        status, err = Preview(file, "--mapping", TWO_LEGS).ended()
        self.assertEqual((status, err), (1, f"preview: {file} is 60 x 60, and the mapping {TWO_LEGS} is 60 x 6\n"))
        self.assert_nothing_left()

    def test_a_page_port_that_is_taken_gives_a_free_one(self):
        file = self.work / "hello.odrg"
        file.write_bytes(core_support.example_show()["hello.odrg"])
        with socket.socket() as taken:
            try:
                taken.bind(("127.0.0.1", preview.PAGE_PORT))
            except OSError:
                pass
            taken.listen()
            started = Preview(file, "--mapping", TWO_LEGS)
            page = started.page()
            port = int(page.rstrip("/").rsplit(":", 1)[1])
            self.assertNotEqual(port, preview.PAGE_PORT)
            self.assertEqual(answer(page, "status")["error"], None)
            status, err = started.interrupt()
        self.assertEqual((status, err), (0, f"preview: port {preview.PAGE_PORT} is taken; the page is on {port}\n"))
        self.assert_nothing_left(page)

    def test_without_the_core_or_node_it_names_the_step_and_starts_nothing(self):
        file = self.work / "hello.odrg"
        file.write_bytes(core_support.example_show()["hello.odrg"])
        absent = self.work / "no-core.dylib"
        status, err = Preview(file, "--core", absent).ended()
        self.assertEqual((status, err), (1, f"preview: the core's library is not built: {absent}; run `make -C core shared`, as \"Set up\" in agent/getting-started.md has it\n"))
        status, err = Preview(file, path=str(pathlib.Path(sys.executable).parent)).ended()
        self.assertEqual((status, err), (1, "preview: Node.js is not there; see \"What you need\" in agent/getting-started.md\n"))
        self.assert_nothing_left()


class Scope(unittest.TestCase):
    def test_the_preview_imports_no_converter_and_writes_no_file_of_a_show(self):
        text = (support.ROOT / "preview" / "__init__.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imported |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module and node.level == 0}
        self.assertEqual(imported - set(sys.stdlib_module_names), {"emulator", "odrigctl"})
        self.assertEqual(sorted(path.name for path in (support.ROOT / "preview").glob("*.py")), ["__init__.py", "__main__.py"])
        for written in ("write_text(", "write_bytes(", '"w"', "'w'", '"wb"', "'wb'"):
            self.assertNotIn(written, text)
        # The converter runs as a program, its path given to Node.js.
        self.assertIn('CONVERTER = ROOT / "converter" / "odrig.js"', text)
        self.assertEqual(text.count("subprocess.run(["), 1)

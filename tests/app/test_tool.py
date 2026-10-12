import http.client
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import unittest

from . import support

from apptool import cli, webserver  # noqa: E402

TOOL = [sys.executable, str(support.APP / "app.py")]


def get(port, path, method="GET"):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request(method, path)
        answer = connection.getresponse()
        return answer.status, dict(answer.getheaders()), answer.read()
    finally:
        connection.close()


class Serve(unittest.TestCase):
    def setUp(self):
        self.server = webserver.Server(0)
        self.addCleanup(self.server.stop)
        self.server.start()

    def test_every_file_of_the_web_code_is_given_with_its_type_and_is_not_to_be_kept(self):
        types = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
        found = sorted(path for path in support.WWW.rglob("*") if path.is_file())
        self.assertGreater(len(found), 5)
        for path in found:
            with self.subTest(path=path.name):
                status, headers, body = get(self.server.port, "/" + path.relative_to(support.WWW).as_posix())
                self.assertEqual((status, body), (200, path.read_bytes()))
                self.assertEqual((headers["Content-Type"], headers["Cache-Control"]), (types[path.suffix], "no-store"))

    def test_the_address_alone_gives_the_page(self):
        status, headers, body = get(self.server.port, "/")
        self.assertEqual((status, headers["Content-Type"], body), (200, "text/html; charset=utf-8", (support.WWW / "index.html").read_bytes()))
        self.assertEqual(get(self.server.port, "/?x=1")[2], body)
        self.assertEqual(get(self.server.port, "/index.html?x=1")[2], body)

    def test_nothing_else_is_given(self):
        for path in ("/nothing.js", "/screens", "/screens/", "/index.html/", "/../app.py", "/screens/../../app.py", "/%2e%2e/app.py", "/..%2fapp.py", "/.gitignore",
                     "//index.html/..", "/odrig", "/app.py", "/toolchain.json", "/t/driver.html", "/result", "/INDEX.HTML"):
            with self.subTest(path=path):
                status, headers, body = get(self.server.port, path)
                self.assertEqual((status, body), (404, b""))
        self.assertEqual(get(self.server.port, "/index.html", "POST")[0], 501)

    def test_a_file_of_another_kind_in_the_folder_is_not_given(self):
        with tempfile.TemporaryDirectory() as work:
            folder = pathlib.Path(work)
            (folder / "index.html").write_text("page")
            (folder / "notes.txt").write_text("notes")
            (folder / "key.pem").write_text("key")
            (folder / ".hidden.js").write_text("hidden")
            other = webserver.Server(0, folder=folder)
            self.addCleanup(other.stop)
            other.start()
            self.assertEqual(get(other.port, "/")[2], b"page")
            for path in ("/notes.txt", "/key.pem", "/.hidden.js"):
                self.assertEqual(get(other.port, path)[0], 404, path)

    def test_it_listens_on_127_0_0_1(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertEqual(self.server.url, f"http://127.0.0.1:{self.server.port}/")
        self.assertEqual(webserver.PORT, 8610)


class TheCommand(unittest.TestCase):
    def test_serve_prints_its_address_serves_and_ends_with_status_0_at_a_signal(self):
        process = subprocess.Popen([*TOOL, "serve", "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            line = process.stdout.readline()
            self.assertRegex(line, r"\Aapp: http://127\.0\.0\.1:[0-9]+/\n\Z")
            port = int(line.rstrip("/\n").rsplit(":", 1)[1])
            self.assertEqual(get(port, "/")[0], 200)
            process.send_signal(signal.SIGINT)
            out, err = process.communicate(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        self.assertEqual((process.returncode, out, err), (0, "", ""))

    def test_a_port_that_is_taken_is_address_in_use(self):
        taken = webserver.Server(0)
        self.addCleanup(taken.stop)
        done = subprocess.run([*TOOL, "serve", "--port", str(taken.port)], capture_output=True, text=True, timeout=20)
        self.assertEqual((done.returncode, done.stdout), (1, ""))
        self.assertRegex(done.stderr, rf"\Aerror: address-in-use: 127\.0\.0\.1:{taken.port}: .+\n\Z")

    def test_a_command_line_that_is_not_understood_is_status_2(self):
        for arguments in ([], ["dance"], ["serve", "--port"], ["serve", "--port", "70000"], ["serve", "--port", "-1"], ["serve", "--lan"], ["serve", "extra"]):
            with self.subTest(arguments=arguments):
                done = subprocess.run([*TOOL, *arguments], capture_output=True, text=True, timeout=20)
                self.assertEqual((done.returncode, done.stdout), (2, ""))
                self.assertIn("usage:", done.stderr)

    def test_the_tool_needs_nothing_but_the_standard_library(self):
        allowed = set(sys.stdlib_module_names) | {"apptool"}
        for path in sorted((support.APP / "apptool").glob("*.py")) + [support.APP / "app.py"]:
            for line in path.read_text(encoding="utf-8").splitlines():
                words = line.split()
                if words[:1] == ["import"]:
                    self.assertIn(words[1].split(".")[0], allowed, f"{path.name}: {line}")
                elif words[:1] == ["from"] and not words[1].startswith("."):
                    self.assertIn(words[1].split(".")[0], allowed, f"{path.name}: {line}")
        self.assertEqual(cli.parser().prog, "python3 app/app.py")
        self.assertEqual(os.listdir(support.APP / "apptool").count("__init__.py"), 1)


if __name__ == "__main__":
    unittest.main()

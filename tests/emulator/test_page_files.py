import pathlib
import re
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser

from emulator import httpd

from . import support
from .test_layout import JSC

WEB = support.ROOT / "emulator" / "web"
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".json": "application/json"}


class Loaded(HTMLParser):
    """Collects what a page loads: its scripts, its style sheets and every other address."""

    def __init__(self):
        super().__init__()
        self.scripts = []
        self.styles = []
        self.others = []
        self.inline_scripts = 0

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "script":
            if "src" in attributes:
                self.scripts.append(attributes["src"])
            else:
                self.inline_scripts += 1
        elif tag == "link" and attributes.get("rel") == "stylesheet":
            self.styles.append(attributes["href"])
        else:
            self.others += [value for name, value in attributes.items() if name in ("src", "href", "action", "data")]


def page_files():
    return sorted(path for path in WEB.iterdir() if path.is_file())


class Served(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = support.entered(cls, support.example_show())
        cls.emulator = support.entered(cls, support.Emulator(cls.folder))

    def test_every_file_of_the_folder_is_served_with_its_content_type(self):
        files = page_files()
        self.assertEqual({path.name for path in files}, {"index.html", "style.css", "board.js", "layout.js", "view.js", "app.js"})
        for path in files:
            with self.subTest(path.name):
                self.assertIn(path.suffix, CONTENT_TYPES)
                answer = self.emulator.request("GET", "/" + path.name)
                self.assertEqual(answer.status, 200)
                self.assertEqual(answer.headers["content-type"], CONTENT_TYPES[path.suffix])
                self.assertEqual(answer.headers["cache-control"], "no-store")
                self.assertEqual(answer.body, path.read_bytes())
                self.assertEqual(self.emulator.request("GET", f"/{path.name}?v=2").body, path.read_bytes())

    def test_the_page_address_gives_the_index(self):
        answer = self.emulator.request("GET", "/")
        self.assertEqual((answer.status, answer.headers["content-type"]), (200, "text/html; charset=utf-8"))
        self.assertEqual(answer.body, (WEB / "index.html").read_bytes())
        self.assertEqual(self.emulator.request("GET", "/?mapping").body, answer.body)

    def test_no_other_file_is_served(self):
        for path in ("/app.py", "/web/index.html", "/emulator/web/index.html", "/../app.py", "/%2e%2e/app.py", "/..%2fapp.py", "/index.htm", "/index.html/", "/style", "/layout.js.map",
                     "/favicon.ico", "/show/app.js", "/mapping.json", "/show.json", "/hello.odrg", "/.", "/web", "/INDEX.HTML"):
            self.assertEqual(self.emulator.request("GET", path).status, 404, path)
        for method in ("POST", "PUT", "DELETE", "HEAD"):
            self.assertEqual(self.emulator.request(method, "/index.html", body=None if method == "HEAD" else b"x").status, 404, method)

    def test_the_table_of_files_is_made_from_the_folder_and_holds_only_the_known_kinds(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ("index.html", "a.js", "b.css", "c.json", "notes.txt", "d.py", "e"):
                pathlib.Path(folder, name).write_bytes(b"x")
            pathlib.Path(folder, "sub").mkdir()
            pathlib.Path(folder, "sub", "f.js").write_bytes(b"x")
            pathlib.Path(folder, "g.js").mkdir()
            table = httpd.page_files(folder)
        self.assertEqual(sorted(table), ["/", "/a.js", "/b.css", "/c.json", "/index.html"])
        self.assertEqual(table["/"], table["/index.html"])
        self.assertEqual({path: kind for path, (_, kind) in table.items()},
                         {"/": "text/html; charset=utf-8", "/index.html": "text/html; charset=utf-8", "/a.js": "text/javascript", "/b.css": "text/css", "/c.json": "application/json"})
        served = httpd.page_files()
        self.assertEqual(sorted(served), sorted(["/"] + ["/" + path.name for path in page_files()]))


class Files(unittest.TestCase):
    def test_no_page_file_names_another_host(self):
        for path in page_files():
            text = path.read_text(encoding="utf-8")
            named = re.search(r"\b(?:https?|wss?|ftp):|//", text)
            self.assertIsNone(named, f"{path.name} holds {named.group() if named else ''!r}")

    def test_the_index_loads_every_script_and_style_of_the_folder_and_nothing_else(self):
        loaded = Loaded()
        loaded.feed((WEB / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(sorted(loaded.scripts), sorted(path.name for path in page_files() if path.suffix == ".js"))
        self.assertEqual(sorted(loaded.styles), sorted(path.name for path in page_files() if path.suffix == ".css"))
        self.assertEqual(loaded.inline_scripts, 0)
        self.assertEqual(loaded.others, ["data:,"])
        self.assertLess(loaded.scripts.index("board.js"), loaded.scripts.index("layout.js"))
        self.assertLess(loaded.scripts.index("layout.js"), loaded.scripts.index("view.js"))
        self.assertLess(loaded.scripts.index("view.js"), loaded.scripts.index("app.js"))

    def test_the_scripts_and_styles_fetch_only_the_events_and_the_mapping_file(self):
        asked = {}
        for path in page_files():
            text = path.read_text(encoding="utf-8")
            found = re.findall(r"(?:fetch|EventSource|import|url)\(\s*[\"']?([^\"')]+)", text)
            asked[path.name] = [address for address in found if not address.startswith("#")]
        self.assertEqual({name: found for name, found in asked.items() if found}, {"app.js": ["show/mapping.json", "events"]})

    def test_the_page_sends_no_command(self):
        for path in page_files():
            if path.suffix != ".js":
                continue
            text = path.read_text(encoding="utf-8")
            for forbidden in ("POST", "XMLHttpRequest", "sendBeacon", "WebSocket", "odrig\"", "/odrig", "<form", "method:"):
                self.assertNotIn(forbidden, text, f"{path.name} holds {forbidden!r}")
        index = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<form", index)
        self.assertNotIn("<input", index)

    def syntax(self, path):
        """What the JavaScript shell of macOS, which has the engine of Safari, makes of the
        syntax of a script: its exit status and what it prints."""
        done = subprocess.run([str(JSC), "-e", "checkSyntax(arguments[0])", "--", str(path)], capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr

    def test_every_script_is_valid_for_the_javascript_engine_of_safari(self):
        scripts = [path for path in page_files() if path.suffix == ".js"]
        self.assertEqual(len(scripts), 4)
        for path in scripts:
            self.assertEqual(self.syntax(path), (0, ""), path.name)
        with tempfile.TemporaryDirectory() as folder:
            broken = pathlib.Path(folder, "broken.js")
            broken.write_text("var layout = ;\n", encoding="utf-8")
            status, printed = self.syntax(broken)
            self.assertNotEqual(status, 0)
            self.assertIn("SyntaxError", printed)

    def test_the_scripts_and_the_style_sheet_are_plain_ascii(self):
        for path in page_files():
            if path.suffix in (".js", ".css"):
                self.assertTrue(path.read_bytes().isascii(), path.name)

    def test_the_led_values_pass_through_the_display_curve_and_nothing_else(self):
        view = (WEB / "view.js").read_text(encoding="utf-8")
        self.assertIn("CURVE.push(OdrigLayout.shown(value))", view)
        self.assertEqual(re.findall(r'"rgb\(" \+ (.+?) \+ "\)"', view), ['CURVE[red] + "," + CURVE[green] + "," + CURVE[blue]'])
        self.assertEqual(len(re.findall(r"fillStyle\s*=", view)), 1)


if __name__ == "__main__":
    unittest.main()

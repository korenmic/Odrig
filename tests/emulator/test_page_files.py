import pathlib
import re
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser

from emulator import httpd

from . import support

WEB = support.ROOT / "emulator" / "web"
APP = support.ROOT / "app" / "www"
LIBRARY = support.ROOT / "converter" / "lib"
THUMBNAILS = support.ROOT / "thumbnails"
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


def app_files():
    """The files of the operators' app that have a content type, in its folder and in
    the folders below it."""
    return sorted(path for path in APP.rglob("*") if path.is_file() and path.suffix in CONTENT_TYPES)


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


class TheApp(unittest.TestCase):
    """The page's controller view shows the operators' app: the emulator serves the files
    of `app/www/` under `/app/`."""

    @classmethod
    def setUpClass(cls):
        cls.folder = support.entered(cls, support.example_show())
        cls.emulator = support.entered(cls, support.Emulator(cls.folder, checked=False))

    def test_every_file_of_the_apps_web_code_is_served_under_app_as_it_is(self):
        files = app_files()
        for expected in ("index.html", "style.css", "main.js", "client.js", "target.js", "screens/show.js", "screens/target.js"):
            self.assertIn(APP / expected, files)
        for path in files:
            asked = "/app/" + path.relative_to(APP).as_posix()
            with self.subTest(asked):
                answer = self.emulator.request("GET", asked)
                self.assertEqual(answer.status, 200)
                self.assertEqual(answer.headers["content-type"], CONTENT_TYPES[path.suffix])
                self.assertEqual(answer.headers["cache-control"], "no-store")
                self.assertEqual(answer.body, path.read_bytes())

    def test_the_converters_library_is_served_under_app_converter_as_it_is(self):
        scripts = sorted(LIBRARY.glob("*.js"))
        self.assertIn(LIBRARY / "index.js", scripts)
        for path in scripts:
            with self.subTest(path.name):
                answer = self.emulator.request("GET", "/app/converter/" + path.name)
                self.assertEqual((answer.status, answer.headers["content-type"], answer.body), (200, "text/javascript", path.read_bytes()))
        for path in ("/app/converter", "/app/converter/", "/app/converter/nothing.js", "/app/converter/../main.js", "/converter/index.js", "/app/lib/index.js"):
            self.assertEqual(self.emulator.request("GET", path).status, 404, path)

    def test_the_address_app_gives_the_apps_index(self):
        answer = self.emulator.request("GET", "/app/")
        self.assertEqual((answer.status, answer.headers["content-type"]), (200, "text/html; charset=utf-8"))
        self.assertEqual(answer.body, (APP / "index.html").read_bytes())
        self.assertNotEqual(answer.body, self.emulator.request("GET", "/").body)

    def test_nothing_else_of_the_repository_is_served(self):
        for path in ("/app", "/app/app.py", "/app/package.json", "/app/capacitor.config.json", "/app/www/index.html", "/app/apptool/cli.py", "/app/android/build.gradle", "/app/screens",
                     "/app/screens/", "/app/../app.py", "/app/../emulator/httpd.py", "/app/%2e%2e/app.py", "/app/..%2fapp.py", "/app/screens/../../app.py", "/app/MAIN.JS", "/app/main.js/",
                     "/www/index.html", "/emulator/httpd.py", "/core/src/core.cpp", "/docs/emulator.md", "/AGENTS.md"):
            self.assertEqual(self.emulator.request("GET", path).status, 404, path)
        for method in ("POST", "PUT", "DELETE", "HEAD"):
            self.assertEqual(self.emulator.request(method, "/app/main.js", body=None if method == "HEAD" else b"x").status, 404, method)

    def test_the_table_is_made_by_walking_the_folder_and_holds_only_the_known_kinds(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ("index.html", "a.js", "notes.txt", "sub/b.js", "sub/deep/c.css", "sub/d.py", "sub/e"):
                place = pathlib.Path(folder, name)
                place.parent.mkdir(parents=True, exist_ok=True)
                place.write_bytes(b"x")
            library = pathlib.Path(folder, "library")
            library.mkdir()
            for name in ("index.js", "notes.txt"):
                pathlib.Path(library, name).write_bytes(b"y")
            previews = pathlib.Path(folder, "previews")
            (previews / "deep").mkdir(parents=True)
            for name in ("catalog.js", "0a0b0c0d-12.gif", "notes.txt", "deep/0a0b0c0d-13.gif"):
                pathlib.Path(previews, name).write_bytes(b"z")
            table = httpd.app_files(folder, library, previews)
            self.assertEqual(sorted(table), ["/app/", "/app/a.js", "/app/converter/index.js", "/app/index.html", "/app/library/index.js", "/app/previews/catalog.js", "/app/sub/b.js", "/app/sub/deep/c.css",
                                             "/app/thumbnails/0a0b0c0d-12.gif", "/app/thumbnails/catalog.js"])
            self.assertEqual(table["/app/thumbnails/0a0b0c0d-12.gif"], (str(pathlib.Path(previews, "0a0b0c0d-12.gif")), "image/gif"))
            self.assertEqual(table["/app/thumbnails/catalog.js"][1], "text/javascript")
            self.assertEqual(table["/app/"], table["/app/index.html"])
            self.assertEqual(table["/app/sub/deep/c.css"], (str(pathlib.Path(folder, "sub", "deep", "c.css")), "text/css"))
            self.assertEqual(httpd.app_files(pathlib.Path(folder, "absent"), pathlib.Path(folder, "absent"), pathlib.Path(folder, "absent")), {})
        served = httpd.app_files()
        self.assertEqual(sorted(served), sorted(["/app/"] + ["/app/" + path.relative_to(APP).as_posix() for path in app_files()] + ["/app/converter/" + path.name for path in LIBRARY.glob("*.js")] +
                                                ["/app/thumbnails/" + path.name for path in THUMBNAILS.iterdir() if path.suffix in (".js", ".gif")]))

    def test_the_default_preview_catalog_is_served_beside_the_app_and_nothing_below_it(self):
        gifs = sorted(THUMBNAILS.glob("*.gif"))
        self.assertTrue(gifs)
        for path in (THUMBNAILS / "catalog.js", gifs[0], gifs[-1]):
            answer = self.emulator.request("GET", "/app/thumbnails/" + path.name)
            self.assertEqual(answer.status, 200, path.name)
            self.assertEqual(answer.body, path.read_bytes())
            self.assertEqual(answer.headers["content-type"], "image/gif" if path.suffix == ".gif" else "text/javascript")
        for path in ("/app/thumbnails/", "/app/thumbnails/none.gif", "/app/thumbnails/../main.js", "/thumbnails/catalog.js", "/app/thumbnails/%2e%2e/main.js"):
            self.assertEqual(self.emulator.request("GET", path).status, 404, path)


class TheControllerView(unittest.TestCase):
    def test_the_page_has_a_third_tab_and_a_pane_that_holds_no_frame(self):
        index = (WEB / "index.html").read_text(encoding="utf-8")
        tabs = re.findall(r'<button type="button" class="tab" id="tab-([a-z]+)" aria-pressed="(true|false)">([A-Za-z]+)</button>', index)
        self.assertEqual(tabs, [("leds", "true", "LEDs"), ("mapping", "false", "Mapping"), ("controller", "false", "Controller")])
        self.assertEqual(index.count('<aside class="controller" id="controller" hidden></aside>'), 1)
        self.assertNotIn("<iframe", index)

    def test_the_script_keeps_this_emulators_address_where_the_app_looks_for_its_target(self):
        app = (WEB / "app.js").read_text(encoding="utf-8")
        key = re.search(r'^const KEY = "([^"]+)";$', (APP / "target.js").read_text(encoding="utf-8"), re.M).group(1)
        self.assertEqual(app.count(f'var APP_ADDRESS = "{key}";'), 1)
        self.assertEqual(app.count("localStorage.setItem(APP_ADDRESS, location.host);"), 1)

    def test_the_frame_is_made_for_the_view_and_removed_when_the_view_is_left(self):
        app = (WEB / "app.js").read_text(encoding="utf-8")
        made = app[app.index("function controller(wanted) {"):app.index("function show(name) {")]
        steps = [made.index(step) for step in ("pane.hidden = !wanted;", 'pane.textContent = "";', "localStorage.setItem(APP_ADDRESS, location.host);",
                                               'var frame = document.createElement("iframe");', 'frame.src = "app/";', "pane.appendChild(frame);")]
        self.assertEqual(steps, sorted(steps))
        shown = app[app.index("function show(name) {"):app.index("var link = byId(")]
        self.assertEqual(shown.count('controller(name === "controller");'), 1)
        self.assertEqual(app.count('createElement("iframe")'), 1)

    def test_the_address_of_the_page_names_the_view(self):
        app = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertEqual(app.count('var VIEWS = ["leds", "mapping", "controller"];'), 1)
        self.assertEqual(app.count('window.addEventListener("hashchange", function () { show(named()); });'), 1)


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

    def test_the_scripts_and_styles_fetch_only_the_seek_the_events_and_the_mapping_file(self):
        asked = {}
        for path in page_files():
            text = path.read_text(encoding="utf-8")
            found = re.findall(r"(?:fetch|EventSource|import|url)\(\s*[\"']?([^\"')]+)", text)
            asked[path.name] = [address for address in found if not address.startswith("#")]
        self.assertEqual({name: found for name, found in asked.items() if found}, {"app.js": ["seek", "show/mapping.json", "events"]})

    def test_the_page_sends_no_command_and_its_one_request_is_the_seek(self):
        for path in page_files():
            if path.suffix != ".js":
                continue
            text = path.read_text(encoding="utf-8")
            for forbidden in ("XMLHttpRequest", "sendBeacon", "WebSocket", "odrig\"", "/odrig", "<form"):
                self.assertNotIn(forbidden, text, f"{path.name} holds {forbidden!r}")
            self.assertEqual(text.count("method:"), 1 if path.name == "app.js" else 0, path.name)
            self.assertEqual(text.count('fetch("seek", {method: "POST", body: JSON.stringify({ms: '), 1 if path.name == "app.js" else 0, path.name)
        index = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<form", index)
        self.assertNotIn("<input", index)

    def test_the_seek_bar_stands_between_the_drawing_and_the_note(self):
        index = (WEB / "index.html").read_text(encoding="utf-8")
        for part in ('id="drawing"', 'id="seek"', 'id="seek-name"', 'id="seek-bar"', 'role="slider"', 'id="seek-fill"', 'id="seek-knob"', 'id="seek-time"', 'id="seek-note"', 'id="note"'):
            self.assertIn(part, index)
        self.assertLess(index.index('id="drawing"'), index.index('id="seek"'))
        self.assertLess(index.index('id="seek"'), index.index('id="note"'))
        app = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn('source.addEventListener("position", onPosition);', app)

    def syntax(self, path):
        """What the JavaScript shell makes of the syntax of a script: its exit status and
        what it prints. The shell of macOS has the engine of Safari, and Node.js that of
        Chrome and Edge."""
        done = subprocess.run([*support.js_shell(), "-e", "checkSyntax(arguments[0])", "--", str(path)], capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr

    def test_every_script_is_valid_for_the_javascript_engine_of_the_shell(self):
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

    def test_the_drawing_is_made_again_for_the_room_its_host_has_whenever_that_room_changes(self):
        app = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn("new ResizeObserver(resized).observe(host);", app)
        self.assertIn('window.addEventListener("resize", resized);', app)
        resized = app[app.index("function resized() {"):app.index("if (window.ResizeObserver) {")]
        self.assertEqual(resized.count("build();"), 1)
        build = app[app.index("function build() {"):app.index("function shortPath(")]
        steps = [build.index(step) for step in ("var f = OdrigLayout.fit(mapping, host.clientWidth, host.clientHeight, board);", "drawing = OdrigView.build(host, mapping, hello.legs, f, board);", "drawing.paint(newest);")]
        self.assertEqual(steps, sorted(steps))

    def test_the_header_reads_playlist_where_the_status_says_all(self):
        app = (WEB / "app.js").read_text(encoding="utf-8")
        status = app[app.index("function onStatus(event) {"):app.index("function cell(")]
        self.assertEqual(status.count('byId("playing").textContent = status.playing === null ? "nothing" : status.playing === "all" ? "playlist" : String(status.playing);'), 1)
        self.assertEqual(status.count('byId("animation").textContent = status.animation === null ? "none" : String(status.animation);'), 1)

    def test_the_readout_names_the_leg_and_the_pin_and_for_an_led_its_number_and_its_canvas_coordinates(self):
        app = (WEB / "app.js").read_text(encoding="utf-8")
        pointer = app[app.index("function onPointer(event) {"):app.index("function show(name) {")]
        for step in ('readout.textContent = "leg " + pointed.leg + ", pin " + pointed.pin;',
                     "var found = drawing.at(event.clientX - box.left, event.clientY - box.top);",
                     'readout.textContent = "leg " + leg.leg + ", pin " + leg.pin + ", LED " + found.led + " (" + found.x + "," + found.y + ")";'):
            self.assertEqual(pointer.count(step), 1, step)
        self.assertEqual(pointer.count("drawing.focus("), 3)
        self.assertIn('host.addEventListener("pointermove", onPointer);', app)


if __name__ == "__main__":
    unittest.main()

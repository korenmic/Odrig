import hashlib
import re
import unittest

from . import support

CONVERTER_LIBRARY = support.ROOT / "converter" / "lib"
# The lines the app may send: the words of a command, with its number left open.
LINES = {"status", "list", "list <n>", "play <n>", "play all", "on", "off", "brightness <n>"}


def files():
    return sorted(path for path in support.WWW.rglob("*") if path.is_file())


def scripts():
    return {path.relative_to(support.WWW).as_posix(): path.read_text(encoding="utf-8") for path in files() if path.suffix == ".js"}


class TheWebCode(unittest.TestCase):
    def test_it_is_pages_styles_and_scripts_that_a_browser_runs_as_they_are(self):
        self.assertTrue(files())
        self.assertEqual({path.suffix for path in files()}, {".html", ".css", ".js"})
        for path in files():
            self.assertTrue(path.read_bytes().isascii(), path.name)
        for name in ("package.json", "node_modules", "lib", "dist"):
            self.assertFalse((support.WWW / name).exists(), name)

    def test_a_script_imports_only_files_of_the_web_code(self):
        for name, text in scripts().items():
            for imported in re.findall(r"""(?:from|import)\s*\(?\s*["']([^"']+)["']""", text):
                with self.subTest(script=name, imported=imported):
                    self.assertRegex(imported, r"\A\.\.?/")
                    found = (support.WWW / name).parent.joinpath(imported).resolve()
                    self.assertTrue(found.is_file() and support.WWW in found.parents, imported)

    def test_only_the_file_of_the_target_knows_how_a_line_travels(self):
        for name, text in scripts().items():
            with self.subTest(script=name):
                words = set(re.findall(r"[A-Za-z_]+", text))
                self.assertEqual(bool(words & {"fetch", "Capacitor", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon"}), name == "target.js")
                self.assertEqual("/odrig" in text, name == "target.js")
        self.assertEqual(scripts()["target.js"].count("/odrig"), 1)

    def test_the_only_address_in_the_code_is_the_boards(self):
        named = {}
        for path in files():
            found = set(re.findall(r"\b[0-9]{1,3}(?:\.[0-9]{1,3}){3}\b", path.read_text(encoding="utf-8")))
            if found:
                named[path.relative_to(support.WWW).as_posix()] = found
        # The message for a text that is no address shows two addresses as examples.
        self.assertEqual(named, {"target.js": {"4.3.2.1"}, "messages.js": {"4.3.2.1", "192.168.1.23"}})
        for path in files():
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"https?://[A-Za-z0-9]", path.name)

    def test_the_lines_the_app_sends_are_commands_of_its_list(self):
        commands = scripts()["commands.js"]
        sent = re.findall(r"carriedOut\(([^()]*(?:\([^()]*\))?[^()]*)\)", commands.split("async function carriedOut")[1].split("\n}\n", 1)[1])
        self.assertTrue(sent)
        lines = {re.sub(r"\$\{[^}]*\}", "<n>", text.strip().strip("`\"'")) for text in sent}
        self.assertLessEqual(lines, LINES)
        self.assertIn("status", lines)
        for name, text in scripts().items():
            if name not in ("commands.js", "target.js"):
                self.assertNotRegex(text, r"\bsend\(", name)
                self.assertNotIn("carriedOut", text)

    def test_the_page_loads_nothing_from_outside_the_package(self):
        page = (support.WWW / "index.html").read_text(encoding="utf-8")
        loaded = re.findall(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", page)
        self.assertEqual(sorted(loaded), ["main.js", "style.css"])
        self.assertEqual(re.findall(r"<script[^>]*>", page), ['<script type="module" src="main.js">'])
        style = (support.WWW / "style.css").read_text(encoding="utf-8")
        self.assertNotRegex(style, r"url\(|@import|@font-face")

    def test_nothing_of_the_converter_is_in_the_app(self):
        library = {hashlib.sha256(path.read_bytes()).hexdigest() for path in CONVERTER_LIBRARY.glob("*.js")}
        self.assertGreater(len(library), 5)
        for path in sorted((support.ROOT / "app").rglob("*")):
            if path.is_file() and "node_modules" not in path.parts:
                self.assertNotIn(hashlib.sha256(path.read_bytes()).hexdigest(), library, path)
        for name, text in scripts().items():
            self.assertNotRegex(text, r"\bconverter\b|odrg\.encode|importFrames", name)


if __name__ == "__main__":
    unittest.main()

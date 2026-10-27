"""Checks of a built APK.

They need `build/app/odrig-debug.apk` and the SDK of the work folder, both of which
`python3 app/app.py build` makes, and no phone.
"""

import json
import pathlib
import re
import subprocess
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
WWW = ROOT / "app" / "www"
LIBRARY = ROOT / "converter" / "lib"
THUMBNAILS = ROOT / "thumbnails"
WORK = ROOT / "build" / "app"
APK = WORK / "odrig-debug.apk"
IDENTIFIER = "app.odrig.operators"
PUBLIC = "assets/public/"
# What Capacitor puts beside the web code, and the note of the build.
ADDED = {"cordova.js", "cordova_plugins.js", "build.json"}


def build_tool(name):
    """A program of the SDK's build tools, of the version `app/toolchain.json` names."""
    listed = json.loads((ROOT / "app" / "toolchain.json").read_text(encoding="utf-8"))
    version = next(package.split(";")[1] for package in listed["sdk-packages"] if package.startswith("build-tools;"))
    return WORK / "android-sdk" / "build-tools" / version / name


class TheApk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not APK.is_file() or not build_tool("aapt2").is_file():
            raise AssertionError(f"there is no {APK.relative_to(ROOT)} with its SDK; `python3 app/app.py build` makes both")
        cls.packed = zipfile.ZipFile(APK)
        cls.addClassCleanup(cls.packed.close)
        cls.names = cls.packed.namelist()

    def dumped(self, *what):
        done = subprocess.run([str(build_tool("aapt2")), "dump", *what, str(APK)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def test_it_is_the_app_odrig_for_android_7_and_later(self):
        badging = self.dumped("badging")
        self.assertRegex(badging, rf"(?m)^package: name='{re.escape(IDENTIFIER)}' ")
        self.assertRegex(badging, r"(?m)^application-label:'odrig'$")
        self.assertRegex(badging, r"(?m)^(minS|s)dkVersion:'24'$")
        self.assertRegex(badging, r"(?m)^targetSdkVersion:'36'$")
        self.assertRegex(badging, rf"(?m)^launchable-activity: name='{re.escape(IDENTIFIER)}\.MainActivity'")

    def test_it_asks_for_the_three_permissions_of_the_network_and_no_other(self):
        used = set(re.findall(r"(?m)^uses-permission: name='([^']+)'", self.dumped("permissions")))
        # An AndroidX library declares one for the app itself, which asks nothing of the phone.
        own = f"{IDENTIFIER}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION"
        self.assertEqual(used, {"android.permission.INTERNET", "android.permission.ACCESS_NETWORK_STATE", "android.permission.CHANGE_NETWORK_STATE", own})

    def test_plain_http_is_allowed(self):
        manifest = self.dumped("xmltree", "--file", "AndroidManifest.xml")
        self.assertRegex(manifest, r"networkSecurityConfig\(0x[0-9a-f]+\)=@0x[0-9a-f]+")
        config = self.dumped("xmltree", "--file", "res/xml/network_security_config.xml")
        self.assertRegex(config, r"E: base-config \(line=\d+\)\s+A: cleartextTrafficPermitted=true")
        self.assertNotIn("domain-config", config)

    def test_the_web_code_the_converters_library_and_the_previews_are_in_it_byte_for_byte_and_nothing_else(self):
        source = {path.relative_to(WWW).as_posix(): path.read_bytes() for path in WWW.rglob("*") if path.is_file()}
        source |= {f"converter/{path.name}": path.read_bytes() for path in LIBRARY.glob("*.js")}
        source |= {f"thumbnails/{path.name}": path.read_bytes() for path in THUMBNAILS.iterdir() if path.suffix in (".js", ".gif")}
        packed = {name[len(PUBLIC):]: self.packed.read(name) for name in self.names if name.startswith(PUBLIC) and not name.endswith("/")}
        self.assertEqual(set(packed) - ADDED, set(source))
        for name, data in source.items():
            self.assertEqual(packed[name], data, f"{name} in the APK is not the one of app/www, converter/lib or thumbnails: build again")
        self.assertLessEqual(ADDED, set(packed))
        self.assertEqual((packed["cordova.js"], packed["cordova_plugins.js"]), (b"", b""))

    def test_the_note_names_the_commit_it_was_built_from(self):
        note = json.loads(self.packed.read(PUBLIC + "build.json"))
        self.assertEqual(sorted(note), ["changed", "commit"])
        self.assertRegex(note["commit"], r"\A[0-9a-f]{40}\Z")
        self.assertIsInstance(note["changed"], bool)
        known = subprocess.run(["git", "cat-file", "-e", note["commit"] + "^{commit}"], cwd=ROOT, capture_output=True)
        self.assertEqual(known.returncode, 0, "the commit of the note is not in this repository")

    def test_capacitor_is_told_the_identifier_and_the_page_for_an_old_web_view(self):
        config = json.loads(self.packed.read("assets/capacitor.config.json"))
        self.assertEqual((config["appId"], config["appName"], config["android"]["minWebViewVersion"], config["server"]["errorPath"]), (IDENTIFIER, "odrig", 80, "old.html"))
        self.assertNotIn("allowMixedContent", json.dumps(config))
        self.assertEqual(json.loads(self.packed.read("assets/capacitor.plugins.json")), [])

    def test_capacitor_gives_the_page_the_room_of_the_bars_with_light_icons(self):
        config = json.loads(self.packed.read("assets/capacitor.config.json"))
        self.assertEqual(config["plugins"]["SystemBars"], {"insetsHandling": "css", "style": "DARK", "initialViewportFitValueHint": "cover"})
        self.assertEqual(config["android"]["backgroundColor"], "#000000")

    def test_the_sender_and_the_activity_are_in_it(self):
        code = b"".join(self.packed.read(name) for name in self.names if re.fullmatch(r"classes[0-9]*\.dex", name))
        for name in ("MainActivity", "TargetPlugin"):
            self.assertIn(f"L{IDENTIFIER.replace('.', '/')}/{name};".encode(), code, name)


if __name__ == "__main__":
    unittest.main()

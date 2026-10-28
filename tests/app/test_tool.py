import hashlib
import http.client
import http.server
import io
import json
import os
import pathlib
import re
import shlex
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
import unittest.mock
import zipfile

from tests.emulator import support as emulator_support

from . import support

from apptool import Failure, build, cli, device, env, paths, stage, toolchain, webserver  # noqa: E402

TOOL = [sys.executable, str(support.APP / "app.py")]
# A program in a group of its own, and Ctrl-C to it: on Windows that is Ctrl+Break.
OWN_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
INTERRUPT = getattr(signal, "CTRL_BREAK_EVENT", signal.SIGINT)


def stand_in(path, code):
    """A stand-in for the program at `path` that runs the Python `code` with the arguments it
    is given. It is `path` itself where the system starts a script by its `#!` line, and
    `path` with `.cmd` added on Windows. Gives the path to start."""
    script = path.with_name(path.name + ".py")
    script.write_text(code, encoding="utf-8")
    if sys.platform == "win32":
        program = path.with_name(path.name + ".cmd")
        program.write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
        return program
    path.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(script))} "$@"\n', encoding="utf-8")
    path.chmod(0o755)
    return path


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

    def test_the_converters_library_is_given_beside_the_web_code_as_it_is(self):
        library = sorted(path for path in support.CONVERTER_LIBRARY.iterdir() if path.is_file())
        self.assertIn(support.CONVERTER_LIBRARY / "index.js", library)
        for path in library:
            with self.subTest(path=path.name):
                status, headers, body = get(self.server.port, "/converter/" + path.name)
                self.assertEqual((status, body), (200, path.read_bytes()))
                self.assertEqual((headers["Content-Type"], headers["Cache-Control"]), ("text/javascript; charset=utf-8", "no-store"))
        for path in ("/converter", "/converter/", "/converter/nothing.js", "/converter/../index.html", "/converter/lib/index.js", "/lib/index.js", "/converter/index.html"):
            with self.subTest(path=path):
                self.assertEqual(get(self.server.port, path)[0], 404)

    def test_the_default_preview_catalog_is_given_beside_the_web_code_and_nothing_below_it(self):
        kept = sorted(path for path in support.THUMBNAILS.iterdir() if path.is_file())
        self.assertIn(support.THUMBNAILS / "catalog.js", kept)
        for path in kept:
            with self.subTest(path=path.name):
                status, headers, body = get(self.server.port, "/thumbnails/" + path.name)
                self.assertEqual((status, body), (200, path.read_bytes()))
                wanted = "image/gif" if path.suffix == ".gif" else "text/javascript; charset=utf-8"
                self.assertEqual((headers["Content-Type"], headers["Cache-Control"]), (wanted, "no-store"))
        for path in ("/thumbnails", "/thumbnails/", "/thumbnails/none.gif", "/thumbnails/../index.html", "/thumbnails/x/catalog.js", "/catalog.js", "/thumbnails/index.html"):
            with self.subTest(path=path):
                self.assertEqual(get(self.server.port, path)[0], 404)

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


class ManyAtOnce(unittest.TestCase):
    def test_connections_that_come_together_wait_to_be_taken_and_none_is_refused(self):
        server = webserver.Server(0)
        self.addCleanup(server.server_close)
        self.assertEqual(emulator_support.connected_at_once(server.port), emulator_support.AT_ONCE)


class TheCommand(unittest.TestCase):
    def test_serve_prints_its_address_serves_and_ends_with_status_0_at_a_signal(self):
        process = subprocess.Popen([*TOOL, "serve", "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=OWN_GROUP)
        try:
            line = process.stdout.readline()
            self.assertRegex(line, r"\Aapp: http://127\.0\.0\.1:[0-9]+/\n\Z")
            port = int(line.rstrip("/\n").rsplit(":", 1)[1])
            self.assertEqual(get(port, "/")[0], 200)
            process.send_signal(INTERRUPT)
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
        for arguments in ([], ["dance"], ["serve", "--port"], ["serve", "--port", "70000"], ["serve", "--port", "-1"], ["serve", "--lan"], ["serve", "extra"],
                          ["setup", "now"], ["build", "--release"], ["install", "phone"], ["test"]):
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


def packed_jdk():
    """The bytes of an archive laid out as a JDK for macOS is: a home with `bin/java`."""
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:gz") as packed:
        java = tarfile.TarInfo("jdk-0/Contents/Home/bin/java")
        script = b"#!/bin/sh\necho 'openjdk version 0' 1>&2\n"
        java.size, java.mode = len(script), 0o755
        packed.addfile(java, io.BytesIO(script))
    return data.getvalue()


def packed_tools():
    """The bytes of an archive laid out as the command-line tools are."""
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as packed:
        for name, mode in (("cmdline-tools/bin/sdkmanager", 0o755), ("cmdline-tools/lib/tools.jar", 0o644), ("cmdline-tools/NOTICE.txt", 0o644)):
            member = zipfile.ZipInfo(name)
            member.external_attr = (stat.S_IFREG | mode) << 16
            packed.writestr(member, b"#!/bin/sh\nexit 0\n")
    return data.getvalue()


class Archives(unittest.TestCase):
    """The downloads, against a server of the test: nothing here asks another computer."""

    def setUp(self):
        self.work = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.downloads = self.work / "downloads"
        self.served = {"/jdk.tar.gz": packed_jdk(), "/tools.zip": packed_tools()}
        served, asked = self.served, []
        self.asked = asked

        class Files(http.server.BaseHTTPRequestHandler):
            def log_message(self, *arguments):
                pass

            def do_GET(self):
                asked.append(self.path)
                body = served.get(self.path)
                self.send_response(404 if body is None else 200)
                self.send_header("Content-Length", str(len(body or b"")))
                self.end_headers()
                self.wfile.write(body or b"")

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Files)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(), server.server_close()))
        self.at = f"http://127.0.0.1:{server.server_address[1]}"

    def archive(self, path, **other):
        data = self.served[path]
        return {"url": self.at + path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), **other}

    def refused(self, reason, call, *arguments, **settings):
        with self.assertRaises(Failure) as failure:
            call(*arguments, **settings)
        self.assertEqual(failure.exception.reason, reason, failure.exception.detail)
        return failure.exception.detail

    def test_an_archive_with_its_size_and_its_sha256_is_kept_and_fetched_once(self):
        kept = toolchain.fetched(self.archive("/jdk.tar.gz"), self.downloads)
        self.assertEqual((kept, kept.read_bytes()), (self.downloads / "jdk.tar.gz", self.served["/jdk.tar.gz"]))
        self.assertEqual(toolchain.fetched(self.archive("/jdk.tar.gz"), self.downloads), kept)
        self.assertEqual(self.asked, ["/jdk.tar.gz"])
        self.assertEqual(sorted(path.name for path in self.downloads.iterdir()), ["jdk.tar.gz"])

    def test_an_archive_with_another_sha256_or_another_size_is_refused_and_removed_and_nothing_is_unpacked(self):
        jdk = self.work / "jdk"
        for what, other in (("sha256", {"sha256": "0" * 64}), ("size", {"bytes": len(self.served["/jdk.tar.gz"]) + 1})):
            with self.subTest(what):
                detail = self.refused("checksum-mismatch", lambda: toolchain.unpacked_jdk(toolchain.fetched(self.archive("/jdk.tar.gz", **other), self.downloads), jdk))
                self.assertIn("jdk.tar.gz has", detail)
                self.assertEqual(list(self.downloads.iterdir()), [])
                self.assertFalse(jdk.exists(), "the archive was unpacked")

    def test_a_file_that_lies_in_the_folder_of_downloads_is_checked_too(self):
        self.downloads.mkdir()
        (self.downloads / "jdk.tar.gz").write_bytes(b"something else")
        self.refused("checksum-mismatch", toolchain.fetched, self.archive("/jdk.tar.gz"), self.downloads)
        self.assertEqual((list(self.downloads.iterdir()), self.asked), ([], []))

    def test_an_archive_that_cannot_be_fetched_is_download_failed_and_leaves_nothing(self):
        self.refused("download-failed", toolchain.fetched, {"url": self.at + "/absent.zip", "bytes": 1, "sha256": "0" * 64}, self.downloads)
        nowhere = {"url": f"http://127.0.0.1:{support.free_port()}/jdk.tar.gz", "bytes": 1, "sha256": "0" * 64}
        self.refused("download-failed", toolchain.fetched, nowhere, self.downloads)
        self.assertEqual(list(self.downloads.iterdir()), [])

    def test_the_jdk_is_unpacked_and_its_home_is_the_folder_with_bin_java(self):
        home = toolchain.unpacked_jdk(toolchain.fetched(self.archive("/jdk.tar.gz"), self.downloads), self.work / "jdk")
        self.assertEqual(home, self.work / "jdk" / "jdk-0" / "Contents" / "Home")
        self.assertTrue(os.access(home / "bin" / "java", os.X_OK))
        self.assertEqual(toolchain.java_home(self.work / "jdk"), home)
        self.assertIsNone(toolchain.java_home(self.work / "no-jdk"))

    def test_the_command_line_tools_are_unpacked_as_latest_with_their_executable_bits(self):
        sdk = self.work / "sdk"
        latest = toolchain.unpacked_tools(toolchain.fetched(self.archive("/tools.zip"), self.downloads), sdk)
        self.assertEqual(latest, sdk / "cmdline-tools" / "latest")
        if os.name == "posix":
            self.assertTrue(os.access(latest / "bin" / "sdkmanager", os.X_OK))
            self.assertFalse(os.access(latest / "lib" / "tools.jar", os.X_OK))
        else:
            # Windows keeps no executable bits.
            self.assertTrue((latest / "bin" / "sdkmanager").is_file())
            self.assertTrue((latest / "lib" / "tools.jar").is_file())
        self.assertEqual(sorted(path.name for path in sdk.iterdir()), ["cmdline-tools"])
        self.assertEqual(sorted(path.name for path in (sdk / "cmdline-tools").iterdir()), ["latest"])


class TheToolchain(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))

    def refused(self, reason, call, *arguments, **settings):
        with self.assertRaises(Failure) as failure:
            call(*arguments, **settings)
        self.assertEqual(failure.exception.reason, reason, failure.exception.detail)
        return failure.exception.detail

    def test_every_download_is_named_by_one_exact_version_with_its_size_and_sha256(self):
        listed = toolchain.read()
        self.assertEqual(sorted(listed), ["command-line-tools", "jdk", "licence", "sdk-packages"])
        for name in ("jdk", "command-line-tools"):
            self.assertRegex(listed[name]["version"], r"\A[0-9][0-9.+]*\Z")
            archive = listed[name]["darwin-arm64"]
            self.assertEqual(sorted(archive), ["bytes", "sha256", "url"])
            self.assertRegex(archive["url"], r"\Ahttps://[a-z0-9.-]+/")
            self.assertRegex(archive["sha256"], r"\A[0-9a-f]{64}\Z")
            self.assertGreater(archive["bytes"], 100_000_000)
            self.assertIn(listed[name]["version"].split("+")[0], archive["url"])
        self.assertEqual(listed["sdk-packages"], ["platform-tools", "platforms;android-36", "build-tools;35.0.0"])
        self.assertEqual(listed["licence"], "android-sdk-license")

    def test_the_packages_of_npm_are_three_at_one_exact_version_with_a_lock_file(self):
        package = json.loads(paths.PACKAGE.read_text(encoding="utf-8"))
        named = {**package["dependencies"], **package["devDependencies"]}
        self.assertEqual(sorted(named), ["@capacitor/android", "@capacitor/cli", "@capacitor/core"])
        self.assertEqual(len(set(named.values())), 1)
        for version in named.values():
            self.assertRegex(version, r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
        self.assertIs(package["private"], True)
        lock = json.loads(paths.LOCK.read_text(encoding="utf-8"))
        for name, version in named.items():
            self.assertEqual(lock["packages"][f"node_modules/{name}"]["version"], version)

    def test_a_system_the_file_does_not_name_is_unsupported(self):
        listed = toolchain.read()
        self.assertEqual(toolchain.archive_of(listed, "jdk", "darwin-arm64"), listed["jdk"]["darwin-arm64"])
        detail = self.refused("unsupported-platform", toolchain.archive_of, listed, "jdk", "plan9-mips")
        self.assertIn("toolchain.json has no jdk for plan9-mips", detail)
        self.assertRegex(toolchain.system(), r"\A[a-z0-9]+-[a-z0-9_]+\Z")

    def test_the_environment_of_a_child_keeps_everything_in_the_shared_toolchains(self):
        home = self.work / "jdk" / "Home"
        made = env.child(home, caller={"PATH": os.pathsep.join(("/usr/bin", "/bin")), "HOME": "/Users/somebody", "ANDROID_SDK_ROOT": "/elsewhere", "KEPT": "1"})
        work = str(paths.SHARED)
        self.assertEqual(paths.WORK, support.ROOT / "build" / "app")
        self.assertEqual(paths.SHARED, paths.tools_folder() / "app")
        for name in ("ANDROID_HOME", "ANDROID_USER_HOME", "GRADLE_USER_HOME", "npm_config_cache"):
            self.assertTrue(made[name].startswith(work + os.sep), name)
        self.assertEqual(len({made[name] for name in ("ANDROID_HOME", "ANDROID_USER_HOME", "GRADLE_USER_HOME", "npm_config_cache")}), 4)
        self.assertEqual((made["JAVA_HOME"], made["PATH"]), (str(home), os.pathsep.join((os.path.join(str(home), "bin"), "/usr/bin", "/bin"))))
        self.assertEqual((made["npm_config_update_notifier"], made["HOME"], made["KEPT"]), ("false", "/Users/somebody", "1"))
        self.assertNotIn("ANDROID_SDK_ROOT", made)
        # Capacitor's command line gets the toolchains' own folder as the user's.
        self.assertEqual(env.child(home, home=True, caller={"HOME": "/Users/somebody"})["HOME"], str(paths.SHARED / "home"))
        self.assertNotIn("JAVA_HOME", env.child(caller={"PATH": "/usr/bin"}))

    def test_gradle_leaves_nothing_running_and_keeps_its_settings_in_the_work_folder(self):
        command = build.gradle_command()
        self.assertEqual(command[0], str(support.APP / "android" / "gradlew"))
        self.assertEqual(command[1:3], ["--no-daemon", f"-Duser.home={support.ROOT / 'build' / 'app' / 'home'}"])
        self.assertEqual(command[3:], ["-p", str(support.APP / "android"), "assembleDebug"])

    def test_the_android_project_is_the_templates_with_the_checksum_of_gradle(self):
        android = support.APP / "android"
        wrapper = (android / "gradle" / "wrapper" / "gradle-wrapper.properties").read_text(encoding="utf-8")
        self.assertRegex(wrapper, r"(?m)^distributionUrl=https\\://services\.gradle\.org/distributions/gradle-[0-9.]+-all\.zip$")
        self.assertRegex(wrapper, r"(?m)^distributionSha256Sum=[0-9a-f]{64}$")
        versions = (android / "variables.gradle").read_text(encoding="utf-8")
        for expected in ("minSdkVersion = 24", "compileSdkVersion = 36", "targetSdkVersion = 36"):
            self.assertIn(expected, versions)
        tracked = subprocess.run(["git", "ls-files", "app/android"], cwd=support.ROOT, capture_output=True, text=True).stdout.split()
        self.assertIn("app/android/gradlew", tracked)
        self.assertEqual([path for path in tracked if "/build/" in path or "assets/public" in path or path.endswith(("local.properties", ".apk"))], [])
        ignored = subprocess.run(["git", "check-ignore", "app/node_modules/x", "app/android/app/build/x", "app/android/app/src/main/assets/public/index.html", "app/android/local.properties", "build/app/x"],
                                 cwd=support.ROOT, capture_output=True, text=True).stdout.split()
        self.assertEqual(len(ignored), 5)

    def manager(self, code):
        """An SDK folder with a stand-in for `sdkmanager` that runs Python `code`, in which
        `sdk` is the folder that `--sdk_root` names and `os` and `sys` are imported."""
        sdk = self.work / "sdk"
        folder = sdk / "cmdline-tools" / "latest" / "bin"
        folder.mkdir(parents=True, exist_ok=True)
        return sdk, stand_in(folder / "sdkmanager", 'import os\nimport sys\nsdk = sys.argv[1].removeprefix("--sdk_root=")\n' + code)

    LISTED = {"sdk-packages": ["platform-tools", "platforms;android-36", "build-tools;35.0.0"], "licence": "android-sdk-license"}
    INSTALLS = 'for folder in ("platform-tools", "platforms/android-36", "build-tools/35.0.0", "licenses"):\n    os.makedirs(os.path.join(sdk, folder), exist_ok=True)\n'

    @staticmethod
    def writes(name, text):
        """Python that writes `text` into the file `name` of the SDK folder."""
        return f'with open(os.path.join(sdk, *{tuple(name.split("/"))!r}), "w") as file:\n    file.write({text})\n'

    def test_the_sdk_tool_is_given_one_yes_and_the_packages_and_the_one_licence_must_be_there(self):
        code = (self.writes("asked.txt", '" ".join(sys.argv[2:]) + "\\n"')
                + 'answer = sys.stdin.readline().rstrip("\\r\\n")\nmore = sys.stdin.readline().rstrip("\\r\\n")\n'
                + self.writes("answered.txt", 'f"{answer}|{more}\\n"') + self.INSTALLS + self.writes("licenses/android-sdk-license", '"accepted\\n"'))
        sdk, program = self.manager(code)
        toolchain.sdk_packages(self.LISTED, self.work / "jdk", sdk, program)
        self.assertEqual((sdk / "asked.txt").read_text(), "platform-tools platforms;android-36 build-tools;35.0.0\n")
        self.assertEqual((sdk / "answered.txt").read_text(), "y|\n")
        # With the packages there, the tool is not started again.
        (sdk / "asked.txt").unlink()
        toolchain.sdk_packages(self.LISTED, self.work / "jdk", sdk, program)
        self.assertFalse((sdk / "asked.txt").exists())

    def test_another_licence_or_a_missing_package_is_licence_refused(self):
        both = self.INSTALLS + self.writes("licenses/android-sdk-license", '"a\\n"') + self.writes("licenses/android-sdk-preview-license", '"b\\n"')
        sdk, program = self.manager(both)
        detail = self.refused("licence-refused", toolchain.sdk_packages, self.LISTED, self.work / "jdk", sdk, program)
        self.assertIn("android-sdk-preview-license", detail)
        (sdk / "licenses" / "android-sdk-preview-license").unlink()
        toolchain.sdk_packages(self.LISTED, self.work / "jdk", sdk, program)
        (sdk / "build-tools" / "35.0.0").rmdir()
        sdk, program = self.manager("")
        self.assertIn("build-tools;35.0.0", self.refused("licence-refused", toolchain.sdk_packages, self.LISTED, self.work / "jdk", sdk, program))
        sdk, program = self.manager('sys.stderr.write("no network\\n")\nsys.exit(7)\n')
        self.assertIn("status 7: no network", self.refused("setup-failed", toolchain.sdk_packages, self.LISTED, self.work / "jdk", sdk, program))

    def test_a_node_that_is_missing_or_too_old_is_node_missing(self):
        programs = self.work / "bin"
        programs.mkdir()
        with unittest.mock.patch.dict(os.environ, {"PATH": str(programs)}):
            self.assertIn("node is not on the path", self.refused("node-missing", toolchain.node_version))
            stand_in(programs / "node", 'print("v18.20.4")\n')
            self.assertIn("node is v18.20.4", self.refused("node-missing", toolchain.node_version))
            stand_in(programs / "node", 'print("v22.0.0")\n')
            self.assertEqual(toolchain.node_version(), 22)


class TheStagedFolder(unittest.TestCase):
    def test_it_holds_the_web_code_as_it_is_and_a_note_of_what_it_was_built_from(self):
        work = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        folder = work / "www"
        folder.mkdir()
        (folder / "left-over.js").write_text("old")
        made = stage.staged(folder)
        source = {path.relative_to(support.WWW).as_posix(): path.read_bytes() for path in support.WWW.rglob("*") if path.is_file()}
        staged = {path.relative_to(made).as_posix(): path.read_bytes() for path in made.rglob("*") if path.is_file()}
        note = json.loads(staged.pop("build.json"))
        library = {f"converter/{path.name}": path.read_bytes() for path in support.CONVERTER_LIBRARY.glob("*.js")}
        previews = {f"thumbnails/{path.name}": path.read_bytes() for path in support.THUMBNAILS.iterdir() if path.suffix in (".js", ".gif")}
        self.assertGreater(len(library), 5)
        self.assertIn("thumbnails/catalog.js", previews)
        self.assertEqual(staged, source | library | previews)
        self.assertFalse(set(source) & (set(library) | set(previews)))
        self.assertEqual(sorted(note), ["changed", "commit"])
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=support.ROOT, capture_output=True, text=True).stdout.strip()
        self.assertEqual((note["commit"], type(note["changed"])), (head, bool))
        self.assertNotIn("build.json", source)
        self.assertEqual(paths.STAGED, support.ROOT / "build" / "app" / "www")

    def test_capacitor_is_given_that_folder_and_the_page_for_an_old_web_view(self):
        config = json.loads((support.APP / "capacitor.config.json").read_text(encoding="utf-8"))
        self.assertEqual(config, {"appId": "app.odrig.operators", "appName": "odrig", "webDir": "../build/app/www",
                                  "android": {"minWebViewVersion": 80, "backgroundColor": "#000000"}, "server": {"errorPath": "old.html"},
                                  "plugins": {"SystemBars": {"insetsHandling": "css", "style": "DARK", "initialViewportFitValueHint": "cover"}}})
        self.assertEqual((support.APP / config["webDir"]).resolve(), paths.STAGED)
        old = (support.WWW / "old.html").read_text(encoding="utf-8")
        self.assertNotRegex(old, r"<script|src=|href=")
        self.assertIn('update "Android System WebView"', old)


class ThePhone(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.apk = self.work / "odrig-debug.apk"
        self.apk.write_bytes(b"apk")

    def adb(self, listed):
        """A stand-in for `adb`: `adb devices` prints `listed`, in which `\\n` and `\\t` stand for
        a new line and a tab, and any other command is written down in `ran.txt`."""
        shown = listed.replace("\\n", "\n").replace("\\t", "\t")
        ran = self.work / "ran.txt"
        return stand_in(self.work / "adb", f'import sys\nif sys.argv[1:] == ["devices"]:\n    sys.stdout.write({shown!r})\n'
                                           f'else:\n    with open({str(ran)!r}, "w") as file:\n        file.write(" ".join(sys.argv[1:]) + "\\n")\n')

    def test_the_devices_that_are_ready(self):
        self.assertEqual(device.devices("List of devices attached\nR58M123\tdevice\nemulator-5554\toffline\nABC\tunauthorized\n\n"), ["R58M123"])
        self.assertEqual(device.devices("List of devices attached\n\n"), [])

    def test_it_installs_on_the_one_phone_and_refuses_none_and_two(self):
        out = io.StringIO()
        with unittest.mock.patch.object(paths, "ROOT", self.work):
            self.assertEqual(device.install(out, self.adb("List of devices attached\\nR58M123\\tdevice\\n"), self.apk), 0)
            self.assertEqual((self.work / "ran.txt").read_text(), f"-s R58M123 install -r {self.apk}\n")
            self.assertEqual(out.getvalue(), "installed: odrig-debug.apk on R58M123\n")
            for listed in ("List of devices attached\\n", "List of devices attached\\nA\\tdevice\\nB\\tdevice\\n", "List of devices attached\\nA\\tunauthorized\\n"):
                with self.assertRaises(Failure) as failure:
                    device.install(out, self.adb(listed), self.apk)
                self.assertEqual(failure.exception.reason, "no-device")
            with self.assertRaises(Failure) as failure:
                device.install(out, self.adb(""), self.work / "absent.apk")
            self.assertEqual(failure.exception.reason, "build-failed")


if __name__ == "__main__":
    unittest.main()

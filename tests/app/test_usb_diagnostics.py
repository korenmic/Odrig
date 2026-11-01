import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from . import support

ROOT = pathlib.Path(__file__).resolve().parents[2]


class UsbCaptureModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        locations = [pathlib.Path(os.environ["JAVA_HOME"]) / "bin"] if os.environ.get("JAVA_HOME") else []
        if os.name == "nt":
            locations.append(pathlib.Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Android/Android Studio/jbr/bin")
        javac = shutil.which("javac") or next((str(p / "javac.exe") for p in locations if (p / "javac.exe").is_file()), None)
        if not javac:
            raise unittest.SkipTest("JDK needed for the production USB capture model")
        cls.java = str(pathlib.Path(javac).with_name("java.exe" if os.name == "nt" else "java"))
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        sources = [ROOT / "app/android/app/src/main/java/app/odrig/operators/UsbCapture.java", *sorted((ROOT / "tests/app/usb").glob("*.java"))]
        cls.run_tool([javac, "-Xlint:all", "-Werror", "-encoding", "UTF-8", "-d", cls.work.name, *map(str, sources)])

    @staticmethod
    def run_tool(command):
        result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", timeout=30,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        return result.stdout

    def check_model(self, scenario):
        self.assertIn("PASS " + scenario, self.run_tool([self.java, "-cp", self.work.name, "UsbCaptureCheck", scenario]))

    def test_late_permission_does_not_open_usb(self): self.check_model("cancel")
    def test_cancelled_open_closes_without_reading_or_damaging_new_session(self): self.check_model("staleOpen")
    def test_only_one_capture_can_be_active(self): self.check_model("overlap")
    def test_permission_denial_allows_retry_and_ignores_old_failures(self): self.check_model("denied")
    def test_capture_sends_no_commands_and_closes_on_unplug(self): self.check_model("passive")
    def test_explicit_report_request_writes_only_existing_read_commands(self): self.check_model("readReports")
    def test_fragmented_utf8_and_untrusted_text_survive_stop_and_export(self): self.check_model("utf8")
    def test_capture_limit_stops_io_and_preserves_full_bounded_export(self): self.check_model("limit")
    def test_background_cancellation_discards_a_late_read(self): self.check_model("stopRead")


class UsbDiagnosticsView(unittest.TestCase):
    def test_browser_explains_android_requirement_without_opening_usb(self):
        found = support.run("usb-diagnostics", settings={"native": False})
        self.assertEqual(found.seen, {"availability": "USB log capture is available in the Android app.", "hidden": True})

    def test_native_view_captures_read_reports_shares_and_cancels_pending_permission(self):
        found = support.run("usb-diagnostics", settings={"native": True})
        self.assertEqual(found.seen["open"], {"device": "test-usb", "port": 0})
        self.assertTrue(found.seen["selectedVisible"])
        self.assertTrue(found.seen["selectionKept"])
        self.assertTrue(found.seen["textSafe"])
        self.assertEqual(found.seen["reports"], 1)
        self.assertEqual(found.seen["shares"], 1)
        self.assertTrue(found.seen["stoppedOnLeave"])
        self.assertTrue(found.seen["denialVisible"])
        self.assertTrue(found.seen["noDevicesDisabled"])
        self.assertTrue(found.seen["unpluggedLogKept"])

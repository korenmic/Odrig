import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from . import support
from .test_build_script import build

USERMOD = support.ROOT / "firmware" / "usermod"
STUB = pathlib.Path(__file__).with_name("mini_output")


class OutputTransitions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        folder = pathlib.Path(cls.temporary.name)
        cls.program = folder / ("outputs.exe" if sys.platform == "win32" else "outputs")
        cls.toolchain = build.find()
        with mock.patch.multiple(build, CORE=folder, BUILD=folder / "build"):
            _, checks = build.checks(cls.toolchain)
        sources = [str(STUB / "outputs.cpp"), str(USERMOD / "odrig_leds.cpp")]
        if cls.toolchain.kind == "msvc":
            command = [cls.toolchain.cxx, *build.MICROSOFT_HOST_FLAGS, *checks,
                       f"/I{STUB}", f"/I{USERMOD}", *sources, f"/Fe{cls.program}"]
        else:
            command = [cls.toolchain.cxx, "-std=c++11", *build.WARNINGS, *checks,
                       *build.GNU_DEBUG, f"-I{STUB}", f"-I{USERMOD}", *sources,
                       "-o", str(cls.program), *(["-static"] if sys.platform == "win32" else [])]
        done = subprocess.run(command, cwd=folder, env=cls.toolchain.env,
                              capture_output=True, timeout=120)
        if done.returncode:
            raise AssertionError(done.stderr.decode("utf-8", "replace")[-4000:])

    def run_case(self, case):
        done = subprocess.run([str(self.program), case], env=self.toolchain.env,
                              capture_output=True, timeout=10)
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", "replace"))
        self.assertIn(b'"ok":true', done.stdout)

    def test_clear_drain_setup_and_restore_use_actual_active_led_counts(self):
        self.run_case("switch")

    def test_transfers_are_rechecked_before_setup_and_acknowledgement(self):
        self.run_case("wait")

    def test_failed_output_setup_stays_dark_and_can_be_retried(self):
        self.run_case("failure")

    def test_output_summary_follows_the_selected_hardware(self):
        self.run_case("summary")

    def test_failed_restoration_can_retry_miniature_then_normal_outputs(self):
        self.run_case("restore-failure")

    def test_normal_pin_permutations_do_not_change_the_miniature_gpio(self):
        self.run_case("mapping")


class FirmwareIntegration(unittest.TestCase):
    def test_setup_operations_and_transfer_waits_do_not_own_the_core_lock(self):
        source = (USERMOD / "odrig_usermod.cpp").read_text(encoding="utf-8")
        service = source.split("bool serviceMini(", 1)[1].split("#ifdef ODRIG_PROBE", 1)[0]
        scopes = []
        checked = 0
        for token in re.finditer(r"\{|\}|Locked held;", service):
            if token.group() == "{":
                scopes.append([token.end(), False])
            elif token.group() == "Locked held;":
                scopes[-1][1] = True
            elif scopes:
                start, locked = scopes.pop()
                if locked:
                    checked += 1
                    self.assertNotRegex(service[start:token.start()],
                                        r"miniOutput\.step|OdrigLeds::(?:hold|dark|apply)|canAllShow")
        self.assertEqual(checked, 3)
        self.assertIn("miniOutput.step(driver)", service)
        self.assertIn("odrig_core_mini_complete", service)

    def test_refresh_publication_and_switch_capture_share_the_lock(self):
        source = (USERMOD / "odrig_usermod.cpp").read_text(encoding="utf-8")
        due = source.split("bool refreshDue()", 1)[1].split("const char TASK_NAME", 1)[0]
        self.assertIn("Locked held;", due)
        self.assertIn("if (outputChanging) return false;", due)
        self.assertIn("if (due) refreshReady = true;", due)
        requester = source.split("void requestRefreshes(", 1)[1].split("struct MiniDriver", 1)[0]
        self.assertNotIn("refreshReady = true", requester)
        self.assertIn("refreshReady || updating || outputChanging", requester)

    def test_commands_are_serviced_before_a_pending_transition(self):
        source = (USERMOD / "odrig_usermod.cpp").read_text(encoding="utf-8")
        loop = source.split("void loop() override", 1)[1].split("void addToJsonInfo", 1)[0]
        switch = loop.index("serviceMini(refreshFilled)")
        self.assertLess(loop.index("OdrigSerial::poll"), switch)
        self.assertLess(loop.index("OdrigUart::poll"), switch)
        self.assertIn("OdrigLeds::keepLive();", loop)
        self.assertIn("enableMiniSupport();", source)
        self.assertNotRegex(source, r"mini[^\n]*(?:serializeConfig|saveSettings|writeConfig)")


if __name__ == "__main__":
    unittest.main()

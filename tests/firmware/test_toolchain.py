import re
import unittest
from unittest import mock

from fwtool import paths, toolchain, wled

from . import support

PINNED = ("esptool", "littlefs-python", "nodejs-wheel")


class Requirements(unittest.TestCase):
    def test_the_tools_own_packages_are_pinned_at_exact_versions(self):
        lines = [line.strip() for line in paths.REQUIREMENTS.read_text().splitlines() if line.strip() and not line.startswith("#")]
        self.assertEqual(sorted(line.split("==")[0] for line in lines), sorted(PINNED))
        for line in lines:
            self.assertRegex(line, r"^[a-z-]+==\d+(\.\d+)+$")

    def test_wleds_own_pinned_platformio_is_installed_before_them(self):
        self.assertEqual(toolchain.requirement_files(), [paths.WLED_SOURCE / "requirements.txt", paths.REQUIREMENTS])
        pinned = (paths.WLED_SOURCE / "requirements.txt").read_text()
        self.assertRegex(pinned, r"(?m)^platformio==6\.1\.17$")
        for line in pinned.splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                self.assertRegex(line, r"^[A-Za-z0-9._-]+==[^\s]+$")


class Setup(unittest.TestCase):
    def test_nothing_is_fetched_or_installed_when_the_work_folder_has_it_all(self):
        def started(what, command):
            raise AssertionError(f"started: {what}")
        with mock.patch.object(toolchain, "_run", started), mock.patch.object(wled.subprocess, "run", wraps=wled.subprocess.run) as git:
            self.assertEqual(toolchain.python_environment(), [])
        commands = [call.args[0][:4] for call in git.call_args_list]
        self.assertNotIn("clone", [word for command in commands for word in command])

    def test_a_python_older_than_3_10_is_refused(self):
        self.assertEqual(toolchain.MINIMUM_PYTHON, (3, 10))
        with mock.patch.object(toolchain.sys, "version_info", (3, 9, 6)), mock.patch.object(toolchain.sys, "version", "3.9.6 (default)"):
            self.assertEqual(support.reason_of(self, toolchain.python_environment), "setup-failed")

    def test_the_packages_are_installed_again_when_a_requirement_file_changed(self):
        ran = []
        stamp = mock.Mock()
        stamp.exists.return_value = True
        stamp.read_text.return_value = "the checksum of other requirement files\n"
        with mock.patch.object(toolchain, "_run", lambda what, command: ran.append(what) or ""), mock.patch.object(toolchain, "STAMP", stamp):
            done = toolchain.python_environment()
        self.assertEqual(done, ["installed the Python packages"])
        self.assertEqual(ran, ["pip install -r requirements.txt", "pip install -r requirements.txt"])
        stamp.write_text.assert_called_once_with(toolchain._wanted() + "\n")

    def test_every_tool_is_taken_from_the_work_folder(self):
        asked = []
        with mock.patch.object(toolchain, "_run", lambda what, command: asked.append(str(command[0])) or "version 1\n"):
            found = toolchain.versions()
        self.assertEqual(sorted(found), ["esptool", "node", "npm", "platformio", "python"])
        for program in asked:
            self.assertTrue(program.startswith(str(paths.VENV / "bin") + "/"), program)

import configparser
import os
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from fwtool import build, env, paths, toolchain, wled

from . import ROOT, support

PLATFORM = "https://github.com/pioarduino/platform-espressif32/releases/download/55.03.312-1/platform-espressif32.zip"
DOCUMENT = ROOT / "docs" / "firmware.md"
BOARD_SUPPORT = ROOT / "tests" / "board" / "support.py"


def environments():
    """The sections of the override file, read without interpolation."""
    parsed = configparser.ConfigParser(interpolation=None, strict=True)
    parsed.read_string(wled.override_text())
    return parsed


class TheFolder(unittest.TestCase):
    def test_the_newer_software_has_a_folder_of_its_own_inside_the_work_folder(self):
        self.assertEqual(paths.NEWER, paths.WORK / "newer")
        for folder in (paths.NEWER_VENV, paths.NEWER_PYTHON, paths.NEWER_PIO_CORE, paths.NEWER_PIO_CACHE):
            self.assertTrue(folder.is_absolute(), folder)
            self.assertIn(paths.NEWER, folder.parents, folder)
        self.assertEqual(paths.NEWER_PYTHON, paths.NEWER_VENV / "bin" / "python")
        self.assertEqual(paths.NEWER_REQUIREMENTS, paths.FIRMWARE / "requirements-newer.txt")

    def test_no_folder_of_the_build_known_good_lies_in_it(self):
        for folder in (paths.VENV, paths.PIO_CORE, paths.PIO_CACHE, paths.WLED, paths.OUT, paths.STORAGE):
            self.assertNotIn(paths.NEWER, folder.parents, folder)
            self.assertNotEqual(folder, paths.NEWER)


class TheEnvironment(unittest.TestCase):
    def test_platformio_gets_the_folders_of_the_newer_software(self):
        made = env.child({"PATH": "/usr/bin"}, newer=True)
        self.assertEqual(made["PLATFORMIO_CORE_DIR"], str(paths.NEWER_PIO_CORE))
        self.assertEqual(made["PLATFORMIO_BUILD_CACHE_DIR"], str(paths.NEWER_PIO_CACHE))

    def test_pips_and_npms_caches_are_shared(self):
        newer, known = env.child({"PATH": "/usr/bin"}, newer=True), env.child({"PATH": "/usr/bin"})
        for name in ("PIP_CACHE_DIR", "npm_config_cache"):
            self.assertEqual(newer[name], known[name], name)
        for name, value in env.SWITCHES.items():
            self.assertEqual(newer[name], value, name)

    def test_the_programs_of_the_newer_software_come_first_and_those_of_the_build_known_good_are_left_out(self):
        newer = env.child({"PATH": f"{paths.VENV / 'bin'}{os.pathsep}/usr/bin"}, newer=True)
        self.assertEqual(newer["PATH"].split(os.pathsep), [str(paths.NEWER_VENV / "bin"), "/usr/bin"])
        known = env.child(newer)
        self.assertEqual(known["PATH"].split(os.pathsep), [str(paths.VENV / "bin"), "/usr/bin"])
        self.assertEqual(known["PLATFORMIO_CORE_DIR"], str(paths.PIO_CORE))
        self.assertEqual(env.child(newer, newer=True)["PATH"], newer["PATH"])


class ThePackages(unittest.TestCase):
    def pinned(self, path):
        lines = [line.split("#")[0].strip() for line in pathlib.Path(path).read_text().splitlines()]
        return dict(line.split("==") for line in lines if line)

    def test_every_package_of_the_newer_software_is_pinned_at_an_exact_version(self):
        for line in paths.NEWER_REQUIREMENTS.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                self.assertRegex(line, r"^[a-z][a-z0-9-]*==\d+(\.\d+)+$")
        pinned = self.pinned(paths.NEWER_REQUIREMENTS)
        self.assertEqual(pinned["platformio"], "6.2.0")
        self.assertEqual((pinned["nodejs-wheel"], pinned["nodejs-wheel-binaries"]), ("20.18.0", "20.18.0"))

    def test_the_packages_wled_pins_too_have_its_versions_but_platformio(self):
        wleds = self.pinned(paths.WLED / "requirements.txt")
        newer = self.pinned(paths.NEWER_REQUIREMENTS)
        for name, version in wleds.items():
            if name != "platformio":
                self.assertEqual(newer.get(name), version, name)


class SettingUp(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name)
        self.venv = self.folder / "venv"
        self.ran = []
        for name, value in (("NEWER", self.folder), ("NEWER_VENV", self.venv), ("NEWER_PYTHON", self.venv / "bin" / "python")):
            patcher = mock.patch.object(toolchain.paths, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(toolchain, "NEWER_STAMP", self.venv / "odrig-requirements.sha256")
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_(self, what, command, newer=False):
        self.ran.append((what, [str(part) for part in command], newer))
        if command[1:3] == ["-m", "venv"]:
            (self.venv / "bin").mkdir(parents=True)
            (self.venv / "bin" / "python").touch()
        return ""

    def test_a_missing_environment_is_made_and_the_packages_installed_into_it(self):
        with mock.patch.object(toolchain, "_run", self.run_):
            done = toolchain.newer_environment()
        self.assertEqual(done, ["created the newer software's Python environment", "installed the newer software's Python packages"])
        self.assertEqual(self.ran[0][1][1:], ["-m", "venv", str(self.venv)])
        self.assertEqual(self.ran[1][1][:3], [str(self.venv / "bin" / "python"), "-m", "pip"])
        self.assertEqual(self.ran[1][1][-2:], ["-r", str(paths.NEWER_REQUIREMENTS)])
        self.assertTrue(self.ran[1][2], "pip did not run with the newer software's environment")

    def test_nothing_is_run_when_the_environment_has_its_packages(self):
        with mock.patch.object(toolchain, "_run", self.run_):
            toolchain.newer_environment()
            self.ran.clear()
            self.assertEqual(toolchain.newer_environment(), [])
        self.assertEqual(self.ran, [])

    def test_the_packages_are_installed_again_when_the_requirement_file_changed(self):
        with mock.patch.object(toolchain, "_run", self.run_):
            toolchain.newer_environment()
            toolchain.NEWER_STAMP.write_text("the checksum of another file\n")
            self.ran.clear()
            self.assertEqual(toolchain.newer_environment(), ["installed the newer software's Python packages"])
        self.assertEqual([what for what, _, _ in self.ran], ["pip install -r requirements-newer.txt"])


class Building(unittest.TestCase):
    def build(self, *arguments, status=0):
        ran = []
        def run(command, **named):
            ran.append((command, named))
            return mock.Mock(returncode=status)
        with mock.patch.object(build.toolchain, "python_environment"), mock.patch.object(build.toolchain, "newer_environment") as newer, \
                mock.patch.object(build.wled, "restore_and_patch") as patched, mock.patch.object(build.wled, "write_override") as overridden, \
                mock.patch.object(build.subprocess, "run", run), mock.patch.object(build, "keep", return_value=1500000) as kept, \
                mock.patch.object(build, "sha256", return_value="48e51d84"):
            result = support.run_main("build", *arguments)
        return result, ran, newer, patched, overridden, kept

    def test_trial_runs_the_newer_softwares_platformio_on_the_trial_environment(self):
        for arguments, environment, image in ((["--trial"], "odrig_trial", "odrig-trial.bin"), (["--trial", "--probe"], "odrig_trial_probe", "odrig-trial-probe.bin")):
            result, ran, newer, patched, overridden, kept = self.build(*arguments)
            self.assertEqual(result.status, 0, result.err)
            self.assertEqual(ran[0][0], [str(paths.NEWER_PYTHON), "-m", "platformio", "run", "-d", str(paths.WLED), "-e", environment])
            self.assertEqual(ran[0][1]["env"]["PLATFORMIO_CORE_DIR"], str(paths.NEWER_PIO_CORE))
            self.assertEqual(ran[0][1]["env"]["PATH"].split(os.pathsep)[0], str(paths.NEWER_VENV / "bin"))
            newer.assert_called_once_with()
            self.assertEqual(patched.call_args.kwargs, {"patches": paths.PATCHES})
            overridden.assert_called_once_with()
            self.assertEqual(kept.call_args.args, (paths.WLED / ".pio" / "build" / environment / "firmware.bin", paths.OUT / image))
            self.assertIn(f"{image}: 1500000 bytes", result.out)

    def test_the_build_known_good_does_not_touch_the_newer_software(self):
        for arguments in ([], ["--probe"], ["--stock"]):
            result, ran, newer, _, _, _ = self.build(*arguments)
            self.assertEqual(result.status, 0, result.err)
            self.assertEqual(ran[0][0][0], str(paths.PYTHON))
            self.assertEqual(ran[0][1]["env"]["PLATFORMIO_CORE_DIR"], str(paths.PIO_CORE))
            newer.assert_not_called()

    def test_trial_does_not_go_with_stock_or_standalone(self):
        for arguments in (["--trial", "--stock"], ["--trial", "--standalone"], ["--trial", "--probe", "--standalone"]):
            result = support.run_main("build", *arguments)
            self.assertEqual(result.status, 2, arguments)
            self.assertIn("--trial does not go with", result.err)

    def test_a_failed_trial_build_is_build_failed(self):
        result, _, _, _, _, _ = self.build("--trial", status=1)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: build-failed: .*odrig_trial\n$")


class TheImages(unittest.TestCase):
    def test_the_trials_images_have_names_of_their_own(self):
        self.assertEqual(build.KINDS["trial"], ("odrig_trial", "odrig-trial.bin"))
        self.assertEqual(build.KINDS["trial-probe"], ("odrig_trial_probe", "odrig-trial-probe.bin"))
        images = [kind.image for kind in build.KINDS.values()]
        self.assertEqual(len(images), len(set(images)))
        self.assertEqual(build.ON_NEWER, ("trial", "trial-probe"))

    def test_the_trial_takes_the_place_of_the_firmware_and_of_the_probe_build(self):
        self.assertEqual(build.TRIAL_OF, {"firmware": "trial", "probe": "trial-probe"})


class TheOverride(unittest.TestCase):
    def test_the_trial_environment_extends_the_firmware_on_the_pinned_platform(self):
        found = environments()
        trial = found["env:odrig_trial"]
        self.assertEqual(trial["extends"], "env:odrig")
        self.assertEqual(trial["platform"], PLATFORM)
        self.assertEqual(trial["platform_packages"], "")
        probe = found["env:odrig_trial_probe"]
        self.assertEqual(probe["extends"], "env:odrig_trial")
        self.assertEqual(probe["build_flags"].split("\n"), ["${env:odrig_trial.build_flags}", "-D ODRIG_PROBE"])

    def test_the_firmware_and_its_probe_build_keep_wleds_platform(self):
        found = environments()
        for name in ("env:odrig", "env:odrig_probe"):
            for setting in ("platform", "platform_packages"):
                self.assertNotIn(setting, found[name], f"{name} {setting}")


class WhatTheTrialLeavesOut(unittest.TestCase):
    def test_the_trial_leaves_out_what_does_not_build_on_the_newer_software(self):
        trial = environments()["env:odrig_trial"]
        self.assertEqual(trial["lib_ignore"].split("\n"), ["esp_dmx", "IRremoteESP8266", "NeoESP32RmtHI"])
        self.assertEqual(trial["build_unflags"].split("\n"), ["${env:odrig.build_unflags}", "-D WLED_ENABLE_DMX_INPUT"])
        flags = trial["build_flags"].split("\n")
        self.assertEqual(flags[:4], ["${env:odrig.build_flags}", "-D WLED_DISABLE_INFRARED", "-D WLED_USE_SHARED_RMT", "-D ESP32_ARDUINO_NO_RGB_BUILTIN"])
        self.assertEqual(flags[4:], [f"-include {ROOT}/firmware/newer/odrig_newer.h"])

    def test_the_firmware_known_good_leaves_nothing_out(self):
        found = environments()
        for name in ("env:odrig", "env:odrig_probe"):
            for setting in ("lib_ignore",):
                self.assertNotIn(setting, found[name], f"{name} {setting}")
            self.assertNotIn("odrig_newer.h", found[name].get("build_flags", ""))

    def test_the_header_of_the_newer_software_gives_back_the_old_name(self):
        text = (ROOT / "firmware" / "newer" / "odrig_newer.h").read_text(encoding="utf-8")
        self.assertIn("#define gpio_hal_iomux_func_sel(pin_reg, func) PIN_FUNC_SELECT(pin_reg, func)", text)

    def test_every_change_of_the_patch_is_held_by_the_version_of_esp_idf(self):
        text = (ROOT / "firmware" / "patches" / "020-newer-software.patch").read_text(encoding="utf-8")
        files = re.findall(r"(?m)^\+\+\+ b/(\S+)$", text)
        self.assertTrue(files)
        for chunk in re.split(r"(?m)^diff --git ", text)[1:]:
            name = chunk.split()[0]
            added = [line[1:] for line in chunk.splitlines() if line.startswith("+") and not line.startswith("+++")]
            self.assertTrue(any("ESP_IDF_VERSION_MAJOR >= 5" in line for line in added), name)

    def test_no_hub_of_one_maker_or_model_is_told_apart(self):
        for path in (ROOT / "firmware" / "usermod").glob("*.cpp"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"id(Vendor|Product)\s*[!=]=", path.name)


class TheBoardsSuite(unittest.TestCase):
    def test_it_takes_the_trials_images_when_told_to(self):
        text = BOARD_SUPPORT.read_text(encoding="utf-8")
        self.assertRegex(text, r'(?m)^TRIAL = os\.environ\.get\("ODRIG_BOARD_IMAGES"\) == "trial"$')
        self.assertIn("build.TRIAL_OF", text)


class TheDocument(unittest.TestCase):
    def test_it_says_how_the_trial_is_built_and_what_it_fetches(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        for expected in ("python3 firmware/fw.py build --trial", "`odrig-trial.bin`", "`odrig-trial-probe.bin`", "build/firmware/newer/",
                         "ODRIG_BOARD_IMAGES=trial", PLATFORM, "platformio-6.2.0-py3-none-any.whl",
                         "https://github.com/espressif/arduino-esp32/releases/download/3.3.12/esp32-core-3.3.12-libs.tar.xz"):
            self.assertIn(expected, text)
        self.assertRegex(text, r"(?m)^  newer/ ")


if __name__ == "__main__":
    unittest.main()

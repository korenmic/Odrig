import configparser
import os
import unittest
from unittest import mock

from fwtool import build, paths, wled

from . import support


class BuildingMicroSD(unittest.TestCase):
    def build(self, status=0):
        with mock.patch.object(build.toolchain, "python_environment"), \
                mock.patch.object(build.toolchain, "newer_environment") as newer, \
                mock.patch.object(build.wled, "restore_and_patch") as patched, \
                mock.patch.object(build.wled, "write_override") as overridden, \
                mock.patch.object(build.subprocess, "run", return_value=mock.Mock(returncode=status)) as ran, \
                mock.patch.object(build, "keep", return_value=1500000) as kept, \
                mock.patch.object(build, "sha256", return_value="48e51d84"):
            result = support.run_main("build", "--microsd")
        return result, ran, newer, patched, overridden, kept

    def test_micro_sd_uses_the_newer_toolchain_and_its_own_output(self):
        result, ran, newer, patched, overridden, kept = self.build()
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(ran.call_args.args[0], [
            str(paths.NEWER_PYTHON), "-m", "platformio", "run", "-d", str(paths.WLED), "-e", "odrig_microsd",
        ])
        made = ran.call_args.kwargs["env"]
        self.assertEqual(made["PLATFORMIO_CORE_DIR"], str(paths.NEWER_PIO_CORE))
        self.assertEqual(made["PATH"].split(os.pathsep)[0], str(paths.NEWER_VENV / "bin"))
        newer.assert_called_once_with()
        patched.assert_called_once_with(patches=paths.PATCHES)
        overridden.assert_called_once_with()
        kept.assert_called_once_with(
            paths.WLED / ".pio" / "build" / "odrig_microsd" / "firmware.bin", paths.OUT / "odrig-microsd.bin",
        )
        self.assertIn("odrig-microsd.bin: 1500000 bytes, SHA-256 48e51d84", result.out)

    def test_failed_micro_sd_build_reports_its_environment(self):
        result, _, _, _, _, kept = self.build(status=1)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: build-failed: .*odrig_microsd\n$")
        kept.assert_not_called()

    def test_micro_sd_rejects_other_build_variants_before_building(self):
        for other in ("--stock", "--probe", "--trial", "--standalone"):
            with self.subTest(other=other), mock.patch.object(build, "build") as built:
                result = support.run_main("build", "--microsd", other)
            self.assertEqual(result.status, 2, result.err)
            self.assertIn("--microsd does not go with", result.err)
            built.assert_not_called()

    def test_micro_sd_image_does_not_replace_the_default_image(self):
        self.assertEqual(build.KINDS.get("microsd"), ("odrig_microsd", "odrig-microsd.bin"))
        self.assertEqual(build.image_path("firmware"), paths.OUT / "odrig-firmware.bin")
        self.assertEqual(build.checksum_path(build.image_path("microsd")), paths.OUT / "odrig-microsd.bin.sha256")
        self.assertIn("microsd", build.ON_NEWER)

    def test_micro_sd_inherits_the_trial_and_selects_spi_storage_only_in_its_variant(self):
        environments = configparser.ConfigParser(interpolation=None)
        environments.read_string(wled.override_text())
        self.assertIn("env:odrig_microsd", environments)
        microsd = environments["env:odrig_microsd"]
        self.assertEqual(microsd["extends"], "env:odrig_trial")
        self.assertEqual(microsd["build_flags"].split("\n"), [
            "${env:odrig_trial.build_flags}", "-D ODRIG_DRIVE_SD_SPI",
        ])
        for section in ("env:odrig", "env:odrig_probe", "env:odrig_trial", "env:odrig_trial_probe"):
            self.assertNotIn("ODRIG_DRIVE_SD_SPI", environments[section].get("build_flags", ""))

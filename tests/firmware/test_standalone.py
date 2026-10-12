import pathlib
import re
import tempfile
import unittest
from unittest import mock

from fwtool import build, paths, standalone, wled

from . import ROOT, support

TEMPLATE = ROOT / "firmware" / "standalone" / "platformio.ini.in"
SOURCES = ROOT / "firmware" / "standalone"


def setting(text, name, environment="odrig_standalone"):
    """The value of one setting of an environment of a project file, on one line."""
    section = re.search(rf"(?ms)^\[env:{re.escape(environment)}\]\n(.*?)(?=^\[|\Z)", text).group(1)
    found = re.search(rf"(?m)^{re.escape(name)} = (.*)$", section)
    return None if found is None else found.group(1).strip()


def pins(text):
    """What the project file takes over from WLED's own, each as the text that WLED's
    file must hold for it."""
    libraries = [line.strip() for line in re.search(r"(?ms)^lib_deps =\n(.*?)(?=^\S)", text).group(1).splitlines() if line.strip()]
    return {
        "the platform": f"platform = {setting(text, 'platform')}",
        "the LED library": next(line for line in libraries if "NeoPixelBus" in line),
        "the web server": next(line for line in libraries if "ESPAsyncWebServer" in line),
        "the TCP library": next(line for line in libraries if "AsyncTCP @" in line),
        "the board": f"board = {setting(text, 'board')}",
        "the memory type": f"board_build.arduino.memory_type = {setting(text, 'board_build.arduino.memory_type')}",
        "the partition table": f"extreme_partitions = tools/{pathlib.PurePosixPath(setting(text, 'board_build.partitions')).name}",
        "the flash size": f"board_upload.flash_size = {setting(text, 'board_upload.flash_size')}",
        "the largest image": f"board_upload.maximum_size = {setting(text, 'board_upload.maximum_size')}",
        "the flash frequency": f"board_build.f_flash = {setting(text, 'board_build.f_flash')}",
        "the flash mode": f"board_build.flash_mode = {setting(text, 'board_build.flash_mode')}",
    }


# The pins that WLED's file sets in its environment for this board, and not anywhere.
OF_THE_ENVIRONMENT = ("the board", "the memory type", "the flash size", "the largest image", "the flash frequency", "the flash mode")
WLEDS_ENVIRONMENT = "esp32s3dev_16MB_opi"


def differing(text, wleds):
    """The names of the pins of a project file that WLED's file does not have."""
    environment = re.search(rf"(?ms)^\[env:{WLEDS_ENVIRONMENT}\]\n(.*?)(?=^\[)", wleds).group(1)
    return [name for name, wanted in pins(text).items() if wanted not in (environment if name in OF_THE_ENVIRONMENT else wleds)]


class TheProject(unittest.TestCase):
    def test_the_project_file_names_the_repository_and_wleds_checkout(self):
        text = standalone.project_text("/a/repository", "/a/work/WLED")
        self.assertNotIn("@", text.replace("AsyncTCP @", ""))
        self.assertIn("src_dir = /a/repository/firmware/standalone/src\n", text)
        self.assertEqual(setting(text, "board_build.partitions"), "/a/work/WLED/tools/WLED_ESP32_16MB_9MB_FS.csv")
        self.assertIn("  odrig_core = symlink:///a/repository/core\n", text)
        for folder in ("firmware/standalone/platform", "firmware/usermod", "core/include"):
            self.assertIn(f"  -I/a/repository/{folder}\n", text)

    def test_it_is_built_for_the_board_as_wled_is_and_with_the_arduino_framework(self):
        text = TEMPLATE.read_text()
        self.assertEqual(setting(text, "framework"), "arduino")
        self.assertEqual(setting(text, "board_build.filesystem"), "littlefs")
        for flag in ("-D ARDUINO_USB_CDC_ON_BOOT=1", "-DBOARD_HAS_PSRAM"):
            self.assertIn(flag, text)
        self.assertNotRegex(text, r"-O\d|-Os|-Ofast|build_unflags|debug_tool|upload_protocol")

    def test_the_probe_build_is_the_same_environment_with_the_probe_flag(self):
        text = TEMPLATE.read_text()
        self.assertEqual(setting(text, "extends", "odrig_standalone_probe"), "env:odrig_standalone")
        probe = re.search(r"(?ms)^\[env:odrig_standalone_probe\]\n(.*)\Z", text).group(1)
        self.assertIn("${env:odrig_standalone.build_flags}", probe)
        self.assertIn("-D ODRIG_PROBE", probe)
        self.assertNotIn("ODRIG_PROBE", text.split("[env:odrig_standalone_probe]")[0])

    def test_a_path_with_a_space_in_it_is_refused(self):
        self.assertEqual(support.reason_of(self, lambda: standalone.project_text("/a/my repository", "/a/work/WLED")), "build-failed")
        self.assertEqual(support.reason_of(self, lambda: standalone.project_text("/a/repository", "/a/my work/WLED")), "build-failed")

    def test_the_project_file_is_written_into_its_folder_and_left_alone_when_it_is_there(self):
        with tempfile.TemporaryDirectory() as holder:
            folder = pathlib.Path(holder, "work", "standalone")
            self.assertEqual(standalone.write_project(folder, "/a/repository", "/a/work/WLED"), folder)
            written = folder / "platformio.ini"
            self.assertEqual(written.read_text(), standalone.project_text("/a/repository", "/a/work/WLED"))
            stamp = written.stat().st_mtime_ns
            standalone.write_project(folder, "/a/repository", "/a/work/WLED")
            self.assertEqual(written.stat().st_mtime_ns, stamp)
            standalone.write_project(folder, "/another/repository", "/a/work/WLED")
            self.assertIn("/another/repository", written.read_text())

    def test_the_project_is_in_the_work_folder(self):
        self.assertEqual(paths.STANDALONE, ROOT / "build" / "firmware" / "standalone")


class ThePins(unittest.TestCase):
    def test_the_platform_the_libraries_and_the_board_are_those_of_wled(self):
        wled.check()
        wleds = (paths.WLED / "platformio.ini").read_text(encoding="utf-8")
        self.assertEqual(differing(TEMPLATE.read_text(), wleds), [])
        self.assertIn("board_build.partitions = ${esp32.extreme_partitions}", wleds)

    def test_a_pin_that_differs_is_named(self):
        wleds = (paths.WLED / "platformio.ini").read_text(encoding="utf-8")
        text = TEMPLATE.read_text()
        changed = {
            "the LED library": text.replace("NeoPixelBus.git#1d7ff38f", "NeoPixelBus.git#2d7ff38f"),
            "the platform": text.replace("2024.06.00", "2024.07.00"),
            "the web server": text.replace("#v2.4.2", "#v2.4.3"),
            "the TCP library": text.replace("AsyncTCP @ 3.4.7", "AsyncTCP @ 3.4.8"),
            "the board": text.replace("board = esp32-s3-devkitc-1", "board = esp32-s3-devkitm-1"),
            "the partition table": text.replace("16MB_9MB_FS.csv", "16MB.csv"),
            "the flash mode": text.replace("flash_mode = qio", "flash_mode = dio"),
        }
        for name, other in changed.items():
            with self.subTest(pin=name):
                self.assertNotEqual(other, text)
                self.assertEqual(differing(other, wleds), [name])


class TheKinds(unittest.TestCase):
    def build(self, *arguments, status=0):
        ran = []

        def run(command, **named):
            ran.append((command, named))
            return mock.Mock(returncode=status)
        with tempfile.TemporaryDirectory() as holder, mock.patch.object(build.toolchain, "python_environment"), \
                mock.patch.object(build.wled, "restore_and_patch") as patched, mock.patch.object(build.wled, "write_override") as overridden, \
                mock.patch.object(build.wled, "check") as checked, mock.patch.object(paths, "STANDALONE", pathlib.Path(holder, "standalone")), \
                mock.patch.object(build.standalone, "write_project", side_effect=lambda: paths.STANDALONE) as written, \
                mock.patch.object(build.subprocess, "run", run), mock.patch.object(build, "keep", return_value=175104), \
                mock.patch.object(build, "sha256", return_value="0" * 64):
            result = support.run_main("build", *arguments)
            folder = str(paths.STANDALONE)
        return result, ran, folder, (patched, overridden, checked, written)

    def test_the_two_images_and_their_environments(self):
        self.assertEqual(build.KINDS["standalone"], ("odrig_standalone", "odrig-standalone.bin"))
        self.assertEqual(build.KINDS["standalone-probe"], ("odrig_standalone_probe", "odrig-standalone-probe.bin"))
        self.assertEqual(build.WITHOUT_WLED, ("standalone", "standalone-probe"))
        self.assertEqual(build.image_path("standalone"), ROOT / "build" / "firmware" / "out" / "odrig-standalone.bin")

    def test_the_standalone_firmware_is_built_in_its_own_folder_and_wled_is_not_patched(self):
        for arguments, environment, image in ((["--standalone"], "odrig_standalone", "odrig-standalone.bin"),
                                              (["--standalone", "--probe"], "odrig_standalone_probe", "odrig-standalone-probe.bin"),
                                              (["--probe", "--standalone"], "odrig_standalone_probe", "odrig-standalone-probe.bin")):
            with self.subTest(arguments=arguments):
                result, ran, folder, (patched, overridden, checked, written) = self.build(*arguments)
                self.assertEqual(result.status, 0, result.err)
                self.assertEqual(ran[0][0][1:], ["-m", "platformio", "run", "-d", folder, "-e", environment])
                self.assertEqual(ran[0][1]["env"]["PLATFORMIO_CORE_DIR"], str(paths.PIO_CORE))
                patched.assert_not_called()
                overridden.assert_not_called()
                checked.assert_called_once_with()
                written.assert_called_once_with()
                self.assertIn(f"{image}: 175104 bytes", result.out)

    def test_the_other_kinds_are_built_in_wleds_folder_as_before(self):
        result, ran, _, (patched, overridden, _, written) = self.build("--probe")
        self.assertEqual(ran[0][0][1:], ["-m", "platformio", "run", "-d", str(paths.WLED), "-e", "odrig_probe"])
        patched.assert_called_once()
        overridden.assert_called_once()
        written.assert_not_called()

    def test_standalone_and_stock_do_not_go_together(self):
        self.assertEqual(support.run_main("build", "--standalone", "--stock").status, 2)
        with mock.patch.object(build.toolchain, "python_environment", side_effect=AssertionError("something was set up")):
            done = support.run_tool("build", "--stock", "--standalone")
        self.assertEqual(done.status, 2)
        self.assertIn("--standalone does not go with --stock", done.err)

    def test_flash_takes_the_standalone_image_when_told_and_no_image_is_named(self):
        with tempfile.TemporaryDirectory() as holder:
            image = pathlib.Path(holder, "an-image.bin")
            image.write_bytes(support.PROGRAM)
            build.write_checksum(image)
            for arguments, wanted in ((["--standalone"], "standalone"), ([], "firmware")):
                with support.no_board(answer='{"ok":true}'), mock.patch.object(build, "checked_image", side_effect=lambda path: image) as checked:
                    self.assertEqual(support.run_main("flash", *arguments).status, 0)
                checked.assert_called_once_with(build.image_path(wanted))
            with support.no_board(answer='{"ok":true}') as esptool:
                self.assertEqual(support.run_main("flash", "--standalone", "--image", image).status, 0)
            self.assertEqual(esptool.written(), [("0x10000", "an-image.bin")])


class TheSources(unittest.TestCase):
    def test_no_file_of_the_standalone_firmware_names_a_header_of_wled(self):
        files = sorted(path for path in SOURCES.rglob("*") if path.is_file())
        self.assertIn(SOURCES / "src" / "main.cpp", files)
        for path in files:
            self.assertNotRegex(path.read_text(encoding="utf-8"), r'#include\s+[<"]wled\.h[>"]|wled00/', path.name)


if __name__ == "__main__":
    unittest.main()

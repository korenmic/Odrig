import contextlib
import io
import pathlib
import tempfile
import unittest
from unittest import mock

from fwtool import Failure, build, cli, toolchain

from . import support


class UsageErrors(unittest.TestCase):
    def test_no_command_is_a_usage_error(self):
        result = support.run_tool()
        self.assertEqual(result.status, 2)
        self.assertIn("usage:", result.err)
        self.assertEqual(result.out, "")

    def test_an_unknown_command_is_a_usage_error(self):
        self.assertEqual(support.run_tool("fly").status, 2)

    def test_an_unknown_option_is_a_usage_error(self):
        for command in ("setup", "build", "flash", "restore-stock", "set-wifi", "install-firmware", "test", "test-board"):
            self.assertEqual(support.run_tool(command, "--sideways").status, 2, command)
        for command in ("install-show", "read-show"):
            self.assertEqual(support.run_tool(command).status, 2, command)
            self.assertEqual(support.run_tool(command, "--sideways").status, 2, command)

    def test_a_usage_error_is_found_before_anything_is_set_up(self):
        said = io.StringIO()
        with mock.patch.object(toolchain, "python_environment", side_effect=AssertionError("set up")):
            with contextlib.redirect_stderr(said), self.assertRaises(SystemExit) as stopped:
                cli.launch(["fly"])
        self.assertEqual(stopped.exception.code, 2)
        self.assertIn("usage:", said.getvalue())


class Failures(unittest.TestCase):
    def test_a_failure_is_one_error_line_and_status_1(self):
        with mock.patch.object(toolchain, "setup", side_effect=Failure("setup-failed", "pip install failed with status 1")):
            result = support.run_main("setup")
        self.assertEqual(result.status, 1)
        self.assertEqual(result.err, "error: setup-failed: pip install failed with status 1\n")
        self.assertEqual(result.out, "")

    def test_a_failure_while_the_environment_is_made_is_reported_the_same_way(self):
        with mock.patch.object(toolchain, "python_environment", side_effect=Failure("wled-mismatch", "at another commit")):
            with mock.patch.object(cli.subprocess, "run", side_effect=AssertionError("ran the command")):
                with mock.patch("sys.stderr") as err:
                    status = cli.launch(["setup"])
        self.assertEqual(status, 1)
        self.assertEqual("".join(call.args[0] for call in err.write.call_args_list), "error: wled-mismatch: at another commit\n")


class Images(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name)

    def flash(self, image):
        with support.untouched_board():
            return support.run_main("flash", "--image", image)

    def test_flashing_an_image_that_is_not_there_is_image_missing(self):
        result = self.flash(self.folder / "absent.bin")
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: image-missing: .*absent\.bin.*\n$")

    def test_flashing_an_image_without_its_checksum_is_image_missing(self):
        (self.folder / "image.bin").write_bytes(b"image")
        self.assertRegex(self.flash(self.folder / "image.bin").err, r"^error: image-missing: ")

    def test_flashing_an_image_that_differs_from_its_checksum_is_checksum_mismatch(self):
        image = self.folder / "image.bin"
        image.write_bytes(b"image")
        build.write_checksum(image)
        image.write_bytes(b"imagf")
        result = self.flash(image)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: checksum-mismatch: .*\n$")

    def test_flashing_an_image_larger_than_the_application_partition_is_image_too_large(self):
        image = self.folder / "image.bin"
        image.write_bytes(bytes(3145728 + 1))
        build.write_checksum(image)
        result = self.flash(image)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: image-too-large: .*3145729.*3145728\n$")

    def test_a_built_image_larger_than_the_application_partition_is_not_kept(self):
        built = self.folder / "firmware.bin"
        built.write_bytes(bytes(3145728 + 1))
        with self.assertRaises(Failure) as caught:
            build.keep(built, self.folder / "out" / "odrig-firmware.bin")
        self.assertEqual(caught.exception.reason, "image-too-large")
        self.assertFalse((self.folder / "out").exists())

    def test_a_built_image_is_kept_with_its_sha_256_beside_it(self):
        built = self.folder / "firmware.bin"
        built.write_bytes(bytes(3145728))
        kept = self.folder / "out" / "odrig-firmware.bin"
        self.assertEqual(build.keep(built, kept), 3145728)
        self.assertEqual(kept.read_bytes(), built.read_bytes())
        self.assertEqual((self.folder / "out" / "odrig-firmware.bin.sha256").read_text(), f"{build.sha256(kept)}  odrig-firmware.bin\n")
        self.assertEqual(build.checked_image(kept), kept)

    def test_a_build_that_left_no_image_is_build_failed(self):
        self.assertEqual(support.reason_of(self, lambda: build.keep(self.folder / "absent.bin", self.folder / "out" / "x.bin")), "build-failed")

    def test_the_three_images_and_their_environments(self):
        self.assertEqual(build.KINDS["stock"], ("esp32s3dev_16MB_opi", "stock-built.bin"))
        self.assertEqual(build.KINDS["firmware"].image, "odrig-firmware.bin")
        self.assertEqual(build.KINDS["probe"].image, "odrig-probe.bin")
        self.assertEqual(build.APPLICATION_SIZE, 3145728)


class Building(unittest.TestCase):
    def build(self, *arguments, status=0):
        ran = []
        def run(command, **named):
            ran.append((command, named))
            return mock.Mock(returncode=status)
        with mock.patch.object(build.toolchain, "python_environment"), mock.patch.object(build.wled, "restore_and_patch") as patched, mock.patch.object(build.wled, "write_override"), mock.patch.object(build.subprocess, "run", run), mock.patch.object(build, "keep", return_value=1232912), mock.patch.object(build, "sha256", return_value="48e51d84"):
            result = support.run_main("build", *arguments)
        return result, ran, patched

    def test_stock_builds_wleds_own_environment_with_no_patch(self):
        result, ran, patched = self.build("--stock")
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(ran[0][0][1:], ["-m", "platformio", "run", "-d", str(build.paths.WLED), "-e", "esp32s3dev_16MB_opi"])
        self.assertEqual(patched.call_args.kwargs, {"patches": None})
        self.assertIn("stock-built.bin: 1232912 bytes", result.out)

    def test_the_build_runs_in_the_environment_that_keeps_everything_in_the_work_folder(self):
        _, ran, _ = self.build("--stock")
        self.assertEqual(ran[0][1]["env"]["PLATFORMIO_CORE_DIR"], str(build.paths.PIO_CORE))
        self.assertEqual(ran[0][1]["env"]["PLATFORMIO_BUILD_CACHE_DIR"], str(build.paths.PIO_CACHE))

    def test_the_firmware_and_the_probe_build_have_environments_of_their_own_and_get_the_patches(self):
        for arguments, environment, image in (([], "odrig", "odrig-firmware.bin"), (["--probe"], "odrig_probe", "odrig-probe.bin")):
            result, ran, patched = self.build(*arguments)
            self.assertEqual(result.status, 0, result.err)
            self.assertEqual(ran[0][0][-2:], ["-e", environment])
            self.assertEqual(patched.call_args.kwargs, {"patches": build.paths.PATCHES})
            self.assertIn(f"{image}: ", result.out)

    def test_stock_and_probe_do_not_go_together(self):
        self.assertEqual(support.run_main("build", "--stock", "--probe").status, 2)

    def test_a_failed_build_is_build_failed(self):
        result, _, _ = self.build("--stock", status=1)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: build-failed: .*esp32s3dev_16MB_opi\n$")


class Commands(unittest.TestCase):
    def test_setup_names_the_work_folder_and_the_tools_in_it(self):
        result = support.run_tool("setup")
        self.assertEqual(result.status, 0, result.err)
        self.assertIn(f"work folder: {support.ROOT / 'build' / 'firmware'}\n", result.out)
        for tool in ("python: Python 3.", "platformio: PlatformIO Core, version 6.1.", "node: v20.18.", "esptool: esptool v5.4.0"):
            self.assertIn(tool, result.out)

    def test_the_suite_is_chosen_by_its_folder(self):
        with mock.patch.object(cli.subprocess, "run") as run:
            run.return_value.returncode = 0
            self.assertEqual(support.run_main("test").status, 0)
        command = run.call_args.args[0]
        self.assertEqual(command[1:], ["-m", "unittest", "discover", "-s", "tests/firmware", "-t", "."])
        self.assertEqual(run.call_args.kwargs["cwd"], support.ROOT)

    def test_the_status_of_the_suite_is_the_status_of_the_command(self):
        with mock.patch.object(cli.subprocess, "run") as run:
            run.return_value.returncode = 1
            self.assertEqual(support.run_main("test").status, 1)

    def test_the_board_suite_is_chosen_by_its_folder_and_given_the_port(self):
        with mock.patch.object(cli.subprocess, "run") as run, mock.patch.object(cli.board, "find", return_value="/dev/cu.found") as find:
            run.return_value.returncode = 0
            self.assertEqual(support.run_main("test-board", "--port", "/dev/cu.given").status, 0)
        find.assert_called_once_with("/dev/cu.given")
        self.assertEqual(run.call_args.args[0][1:], ["-m", "unittest", "discover", "-s", "tests/board", "-t", "."])
        self.assertEqual(run.call_args.kwargs["env"]["ODRIG_BOARD_PORT"], "/dev/cu.found")

    def test_the_air_suite_is_chosen_by_its_folder_and_given_the_port_and_the_address(self):
        with mock.patch.object(cli.subprocess, "run") as run, mock.patch.object(cli.board, "find", return_value="/dev/cu.found"):
            run.return_value.returncode = 0
            self.assertEqual(support.run_main("test-air", "--http", "4.3.2.1").status, 0)
        self.assertEqual(run.call_args.args[0][1:], ["-m", "unittest", "discover", "-s", "tests/air", "-t", "."])
        self.assertEqual(run.call_args.kwargs["env"]["ODRIG_BOARD_PORT"], "/dev/cu.found")
        self.assertEqual(run.call_args.kwargs["env"]["ODRIG_BOARD_HTTP"], "4.3.2.1")

    def test_the_air_suite_needs_an_address_and_a_board(self):
        self.assertEqual(support.run_main("test-air").status, 2)
        with mock.patch.object(cli.subprocess, "run", side_effect=AssertionError("ran the suite")), mock.patch.object(cli.board, "find", side_effect=Failure("no-board", "there is no /dev/cu.usbmodem*")):
            result = support.run_main("test-air", "--http", "4.3.2.1")
        self.assertEqual((result.status, result.err), (1, "error: no-board: there is no /dev/cu.usbmodem*\n"))

    def test_the_board_suite_runs_nothing_without_a_board(self):
        with mock.patch.object(cli.subprocess, "run", side_effect=AssertionError("ran the suite")), mock.patch.object(cli.board, "find", side_effect=Failure("no-board", "there is no /dev/cu.usbmodem*")):
            result = support.run_main("test-board")
        self.assertEqual(result.status, 1)
        self.assertEqual(result.err, "error: no-board: there is no /dev/cu.usbmodem*\n")

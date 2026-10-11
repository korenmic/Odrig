import contextlib
import io
import unittest
from unittest import mock

from fwtool import Failure, cli, toolchain

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
        for command in ("setup", "test"):
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

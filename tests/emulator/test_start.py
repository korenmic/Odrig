import pathlib
import signal
import socket
import tempfile
import unittest

from emulator import app
from tests.core import support as core_support

from . import support


class Start(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))

    def example(self):
        return support.entered(self, support.example_show())

    def started(self, folder, *options, **settings):
        return support.entered(self, support.Emulator(folder, *options, **settings))

    def assert_refused(self, result, reason):
        self.assertEqual(result.status, 1)
        self.assertEqual(result.out, "")
        self.assertRegex(result.err, rf"\Aerror: {reason}: .+\n\Z")

    def test_the_page_line_names_127_0_0_1_and_the_port_in_use(self):
        emulator = self.started(self.example())
        self.assertRegex(emulator.lines[0], r"\Apage: http://127\.0\.0\.1:[0-9]+/\Z")
        self.assertGreater(emulator.port, 0)
        self.assertFalse(support.refused(emulator.port))
        self.assertEqual(emulator.status()["playing"], 3)

    def test_the_port_option_names_the_port(self):
        port = support.free_port()
        emulator = self.started(self.example(), port=port)
        self.assertEqual(emulator.lines[0], f"page: http://127.0.0.1:{port}/")
        self.assertEqual(emulator.status()["ok"], True)

    def test_sigterm_and_sigint_end_it_with_status_0(self):
        folder = self.example()
        for number in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=number.name):
                emulator = support.Emulator(folder)
                self.assertEqual(emulator.status()["ok"], True)
                result = emulator.stop(number)
                self.assertEqual((result.status, result.err), (0, ""))
                self.assertTrue(support.refused(emulator.port))

    def test_a_port_that_is_taken_is_address_in_use(self):
        with socket.socket() as holder:
            holder.bind(("127.0.0.1", 0))
            holder.listen(1)
            port = holder.getsockname()[1]
            result = support.run_module(self.example(), "--port", port)
            self.assert_refused(result, "address-in-use")
            self.assertIn(f"127.0.0.1:{port}", result.err)

    def test_a_path_that_is_no_folder_is_not_a_folder(self):
        a_file = self.work / "file"
        a_file.write_bytes(b"")
        for path in (self.work / "none", a_file):
            self.assert_refused(support.run_module(path, "--port", 0), "not-a-folder")

    def test_a_wrong_core_is_core_not_built_and_names_the_command(self):
        result = support.run_module(self.example(), "--port", 0, "--core", self.work / "libodrig_core.dylib")
        self.assert_refused(result, "core-not-built")
        self.assertIn("make -C core shared", result.err)

    def test_a_folder_without_a_show_starts_and_reports_mapping_missing(self):
        emulator = self.started(self.work)
        status = emulator.status()
        self.assertEqual((status["ok"], status["error"], status["playing"]), (True, "mapping-missing", None))
        self.assertEqual(emulator.command("play 1"), b'{"ok":false,"error":"show-invalid"}\n')
        self.assertEqual(emulator.command("brightness 5"), b'{"ok":true}\n')
        self.assertEqual(emulator.status()["brightness"], 5)
        self.assertEqual(emulator.stop().status, 0)

    def test_a_show_with_a_missing_animation_reports_file_missing_with_its_name(self):
        files = core_support.example_show()
        del files["hello.odrg"]
        emulator = self.started(support.installed(self.work / "show", files))
        self.assertEqual(emulator.status()["error"], "file-missing hello.odrg")
        self.assertEqual(emulator.command("play 2"), b'{"ok":false,"error":"show-invalid"}\n')

    def test_verbose_prints_the_diagnostic_lines_of_the_core_to_standard_error(self):
        quiet = support.Emulator(self.work)
        self.assertEqual(quiet.stop().err, "")
        emulator = support.Emulator(self.work, "--verbose")
        result = emulator.stop()
        self.assertEqual(result.status, 0)
        self.assertEqual(result.err, "core: mapping-missing\n")

    def test_a_usage_error_is_status_2(self):
        folder = self.example()
        for argv in (
            [],
            [folder, "--seconds", 1],
            [folder, "--script", self.work / "script.txt"],
            [folder, "--port", 70000],
            [folder, "--port", "-1"],
            [folder, "--port", "http"],
            [folder, "--record", self.work / "out.odrr", "--seconds", 1, "--port", 0],
            [folder, "--record", self.work / "out.odrr", "--seconds", 1, "--verbose"],
            [folder, "--width", 60],
            [folder, "--address", "0.0.0.0"],
        ):
            result = support.run(*argv)
            self.assertEqual(result.status, 2, argv)
            self.assertIn("usage:", result.err)
            self.assertEqual(result.out, "")
        self.assertEqual(list(self.work.iterdir()), [])

    def test_no_option_names_a_size_or_an_address(self):
        options = {option for action in app.parser()._actions for option in action.option_strings}
        self.assertEqual(options, {"-h", "--help", "--port", "--core", "--verbose", "--record", "--seconds", "--script"})


if __name__ == "__main__":
    unittest.main()

import json
import os
import pathlib
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from emulator import app, binding, httpd
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

    def test_exactly_the_two_lines_are_printed_in_order(self):
        link = self.work / "serial"
        emulator = self.started(self.example(), serial_link=link)
        self.assertEqual(emulator.serial, str(link) if support.HAS_SERIAL else None)
        named = f"serial: {link}" if support.HAS_SERIAL else f"tcp: {emulator.tcp}"
        self.assertEqual(emulator.status()["ok"], True)
        with support.lines(emulator) as port:
            self.assertEqual(port.ask("on"), b'{"ok":true}\n')
        result = emulator.stop()
        self.assertEqual(result.out, f"page: http://127.0.0.1:{emulator.port}/\n{named}\n")
        self.assertEqual((result.status, result.err), (0, ""))

    @unittest.skipUnless(support.HAS_SERIAL, support.NO_SERIAL)
    def test_the_link_is_a_symbolic_link_to_a_terminal_device_and_is_gone_after_the_end(self):
        link = self.work / "serial"
        for number in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=number.name):
                emulator = support.Emulator(self.example(), serial_link=link)
                self.assertTrue(link.is_symlink())
                self.assertRegex(os.readlink(link), r"\A/dev/ttys[0-9]+\Z")
                self.assertTrue(stat.S_ISCHR(os.stat(link).st_mode))
                self.assertEqual(emulator.stop(number).status, 0)
                self.assertFalse(os.path.lexists(link))
        self.assertEqual(list(self.work.iterdir()), [])

    @unittest.skipUnless(support.HAS_SERIAL, support.NO_SERIAL)
    def test_a_link_left_by_an_earlier_run_is_replaced(self):
        link = self.work / "serial"
        os.symlink("/dev/ttys999", link)
        emulator = self.started(self.example(), serial_link=link)
        self.assertNotEqual(os.readlink(link), "/dev/ttys999")
        with support.Serial(link) as port:
            self.assertEqual(port.ask("on"), b'{"ok":true}\n')
        emulator.stop()
        self.assertFalse(os.path.lexists(link))

    @unittest.skipUnless(support.HAS_SERIAL, support.NO_SERIAL)
    def test_a_regular_file_at_the_link_path_is_serial_unavailable_and_stays_untouched(self):
        link = self.work / "serial"
        link.write_bytes(b"something of the user's")
        port = support.free_port()
        result = support.run_module(self.example(), "--port", port, "--serial-link", link)
        self.assert_refused(result, "serial-unavailable")
        self.assertIn(str(link), result.err)
        self.assertEqual(link.read_bytes(), b"something of the user's")
        self.assertTrue(support.refused(port))

    @unittest.skipUnless(support.HAS_SERIAL, support.NO_SERIAL)
    def test_without_the_option_the_link_is_in_the_build_folder_of_the_repository_whatever_the_working_folder(self):
        expected = support.ROOT / "build" / "emulator" / "serial"
        process = subprocess.Popen(
            [sys.executable, "-m", "emulator", str(self.example()), "--port", "0"],
            cwd=self.work, env={**os.environ, "PYTHONPATH": str(support.ROOT)}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            lines = [process.stdout.readline(), process.stdout.readline()]
            self.assertRegex(lines[0], r"\Apage: http://127\.0\.0\.1:[0-9]+/\n\Z")
            self.assertEqual(lines[1], f"serial: {expected}\n")
            self.assertTrue(expected.is_symlink())
            with support.Serial(expected) as port:
                self.assertEqual(port.ask("on"), b'{"ok":true}\n')
        finally:
            process.send_signal(signal.SIGTERM)
            out, err = process.communicate(timeout=10)
        self.assertEqual((process.returncode, out, err), (0, "", ""))
        self.assertFalse(os.path.lexists(expected))
        self.assertEqual(list(self.work.iterdir()), [])

    def test_an_emulator_that_cannot_be_sent_its_signal_is_ended_all_the_same(self):
        emulator = support.Emulator(self.example())
        page = emulator.port
        send = emulator.process.send_signal

        def refused(number):
            """Refuses the signal that asks the emulator to stop, and no other: where a
            process is ended by a signal too, that one goes through."""
            if number == support.STOP:
                raise OSError(6, "The handle is invalid")
            return send(number)

        with mock.patch.object(emulator.process, "send_signal", side_effect=refused):
            emulator.stop()
        self.assertIsNotNone(emulator.process.poll())
        self.assertTrue(support.refused(page))

    def test_the_port_option_names_the_port(self):
        port = support.free_port()
        emulator = self.started(self.example(), port=port)
        self.assertEqual(emulator.lines[0], f"page: http://127.0.0.1:{port}/")
        self.assertEqual(emulator.status()["ok"], True)

    def test_each_signal_that_ends_it_ends_it_with_status_0(self):
        folder = self.example()
        self.assertIn(support.STOPS, ((signal.SIGTERM, signal.SIGINT), (getattr(signal, "CTRL_BREAK_EVENT", None),)))
        for number in support.STOPS:
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
            link = self.work / "serial"
            result = support.run_module(self.example(), "--port", port, *support.port_options(link))
            self.assert_refused(result, "address-in-use")
            self.assertIn(f"127.0.0.1:{port}", result.err)
            self.assertFalse(os.path.lexists(link))
            self.assertEqual(list(self.work.iterdir()), [])

    def test_a_path_that_is_no_folder_is_not_a_folder(self):
        a_file = self.work / "file"
        a_file.write_bytes(b"")
        for path in (self.work / "none", a_file):
            self.assert_refused(support.run_module(path, "--port", 0, *support.port_options(self.work / "serial")), "not-a-folder")
        self.assertEqual([entry.name for entry in self.work.iterdir()], ["file"])

    def test_a_wrong_core_is_core_not_built_and_names_the_command(self):
        result = support.run_module(self.example(), "--port", 0, *support.port_options(self.work / "serial"), "--core", self.work / binding.LIBRARY_NAME)
        self.assert_refused(result, "core-not-built")
        self.assertIn(f"`{binding.BUILD_COMMAND}`", result.err)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_a_folder_without_a_show_starts_and_reports_mapping_missing(self):
        emulator = self.started(self.work)
        status = emulator.status()
        self.assertEqual((status["ok"], status["error"], status["playing"]), (True, "mapping-missing", None))
        self.assertEqual(emulator.command("play 1"), b'{"ok":false,"error":"show-invalid"}\n')
        self.assertEqual(emulator.command("brightness 5"), b'{"ok":true}\n')
        self.assertEqual(emulator.status()["brightness"], 5)
        self.assertEqual(emulator.stop().status, 0)

    def test_a_show_with_a_missing_animation_plays_the_others_and_names_it_in_its_list(self):
        files = core_support.example_show()
        del files["hello.odrg"]
        emulator = self.started(support.installed(self.work / "show", files))
        self.assertIsNone(emulator.status()["error"])
        self.assertEqual(emulator.command("play 1"), b'{"ok":false,"error":"unavailable"}\n')
        self.assertEqual(emulator.command("play 2"), b'{"ok":true}\n')
        items = json.loads(emulator.command("list"))["items"]
        self.assertEqual(items[0], {"id": 1, "file": "hello.odrg", "bytes": None, "ignored": False, "external": False, "type": "frames", "fault": "file-missing"})

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
            [folder, "--record", self.work / "out.odrr", "--seconds", 1, "--serial-link", self.work / "serial"],
            [folder, "--serial-link"],
            [folder, "--storage"],
            [folder, "--storage", "-1"],
            [folder, "--storage", "4294967296"],
            [folder, "--storage", "10M"],
            [folder, "--storage", "1.5"],
            [folder, "--storage", ""],
            [folder, "--record", self.work / "out.odrr", "--seconds", 1, "--storage", "many"],
            [folder, "--width", 60],
            [folder, "--address", "0.0.0.0"],
            [folder, "--lan", "yes"],
            [folder, "--record", self.work / "out.odrr", "--seconds", 1, "--lan"],
        ):
            result = support.run(*argv)
            self.assertEqual(result.status, 2, argv)
            self.assertIn("usage:", result.err)
            self.assertEqual(result.out, "")
        self.assertEqual(list(self.work.iterdir()), [])

    def test_without_options_the_port_is_8600_and_the_library_is_the_one_the_makefile_builds(self):
        self.assertEqual(app.PORT, 8600)
        self.assertEqual(app.SERIAL_LINK, support.ROOT / "build" / "emulator" / "serial")
        self.assertEqual(app.LIBRARY, support.LIBRARY)
        arguments = app.parse([str(self.work)])
        self.assertEqual((arguments.port, arguments.serial_link, arguments.core, arguments.verbose, arguments.record), (None, None, str(support.LIBRARY), False, None))
        self.assertEqual(arguments.storage, 13500416)

    def test_the_storage_option_takes_a_whole_number_of_bytes_in_real_time_and_in_record_mode(self):
        for text, value in (("0", 0), ("1", 1), ("13500416", 13500416), ("4294967295", 4294967295)):
            self.assertEqual(app.parse([str(self.work), "--storage", text]).storage, value)
            self.assertEqual(app.parse([str(self.work), "--record", "out.odrr", "--seconds", "1", "--storage", text]).storage, value)

    def test_no_option_names_the_size_of_the_canvas_or_an_address(self):
        options = {option for action in app.parser()._actions for option in action.option_strings}
        self.assertEqual(options, {"-h", "--help", "--port", "--serial-link", "--tcp-port", "--core", "--verbose", "--storage", "--lan", "--drive", "--record", "--seconds", "--script"})
        self.assertIs(app.parse([str(self.work)]).lan, False)
        self.assertIs(app.parse([str(self.work), "--lan"]).lan, True)

    WARNING = "warning: --lan: anyone on the local network can send commands to this emulator and open its page\n"

    def test_with_lan_one_more_line_names_the_address_for_a_phone_and_a_warning_is_written(self):
        emulator = self.started(self.example(), "--lan")
        self.assertRegex(emulator.lan, rf"\A(http://[0-9]+(\.[0-9]+){{3}}:{emulator.port}/|no address)\Z")
        self.assertFalse(emulator.lan.startswith("http://127."))
        self.assertEqual(emulator.status()["ok"], True)
        result = emulator.stop()
        printed = result.out.splitlines()
        self.assertEqual(printed[0], f"page: http://127.0.0.1:{emulator.port}/")
        self.assertEqual(printed[-1], f"lan: {emulator.lan}")
        self.assertEqual(len(printed), 3)
        self.assertEqual((result.status, result.err), (0, self.WARNING))

    def test_the_address_for_a_phone_is_the_one_of_the_default_route_or_none(self):
        address = httpd.lan_address()
        if address is not None:
            self.assertRegex(address, r"\A[0-9]+(\.[0-9]+){3}\Z")
            self.assertFalse(address.startswith("127."))


if __name__ == "__main__":
    unittest.main()

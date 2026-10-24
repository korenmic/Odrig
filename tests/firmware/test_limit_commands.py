import pathlib
import unittest
from unittest import mock

from fwtool import Failure, board, build, limit, storage, wifi

from . import support
from .test_wifi_commands import LAYOUT_LINE, NAME, PASSWORD, REPLY, STORAGE_AT, OnASmallLayout, applied, options_of


class WithALimitFile(OnASmallLayout):
    """The small layout of the network's command tests, and a limit file beside the work
    folder. The board's storage holds a limit of 850."""

    def limit_file(self, milliamps):
        path = self.work.parent / "limit.json"
        path.write_text('{"milliamps": %d}' % milliamps)
        return path

    def run_limit(self, command, esptool, *arguments, answer=REPLY, status=None):
        with support.no_board(esptool, answer=answer):
            with mock.patch.dict(board.EXPECTED, {} if status is None else {"status": status}):
                result = support.run_main(command, *arguments)
        self.results.append(result)
        return result


class SetLimit(WithALimitFile):
    def set_limit(self, esptool, milliamps, *extra, **named):
        return self.run_limit("set-limit", esptool, "--settings", self.limit_file(milliamps), *extra, **named)

    def test_it_writes_the_limit_into_storage_and_prints_two_lines(self):
        esptool = self.esptool()
        result = self.set_limit(esptool, 0)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out, f"{LAYOUT_LINE}\nlimit: off\n{REPLY}\n")
        self.assertEqual(result.err, "")
        board_now = self.on_the_board(esptool)
        self.assertEqual(limit.stored(board_now), 0)
        self.assertTrue(storage.show_of(board_now) == storage.show_of(self.old))

    def test_a_limit_above_0_is_printed_in_milliamps(self):
        esptool = self.esptool()
        result = self.set_limit(esptool, 36000)
        self.assertEqual(result.out, f"{LAYOUT_LINE}\nlimit: 36000 mA\n{REPLY}\n")
        self.assertEqual(limit.stored(self.on_the_board(esptool)), 36000)

    def test_it_writes_once_as_data_inside_storage_and_compares_what_it_wrote(self):
        esptool = self.esptool()
        self.set_limit(esptool, 0)
        self.assertEqual(esptool.commands(), ["read-flash", "read-flash", "write-flash", "verify-flash", "chip-id"])
        write = next(call for call in esptool.calls if "write-flash" in call)
        self.assertIn("--force", write)
        for address, content in esptool.wrote:
            self.assertTrue(STORAGE_AT <= address and address + len(content) <= STORAGE_AT + len(self.old), hex(address))
        self.assertNotIn("erase-region", esptool.words())
        last = esptool.calls[-1]
        self.assertEqual(last[last.index("--after") + 1], "hard-reset")

    def test_on_a_board_that_holds_the_limit_it_writes_nothing_and_prints_the_same(self):
        esptool = self.esptool()
        result = self.set_limit(esptool, 850)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out, f"{LAYOUT_LINE}\nlimit: 850 mA\n{REPLY}\n")
        self.assertEqual(esptool.wrote, [])
        self.assertNotIn("write-flash", esptool.commands())
        self.assertEqual(esptool.commands(), ["read-flash", "read-flash", "chip-id"])

    def test_its_status_is_0_also_when_the_reply_reports_an_invalid_show(self):
        answer = '{"ok":true,"on":true,"brightness":0,"playing":null,"animation":null,"fps":50,"error":"show-missing"}'
        self.assertEqual(self.set_limit(self.esptool(), 0, answer=answer).status, 0)

    def test_the_reply_is_waited_for_20_seconds_or_as_long_as_told(self):
        esptool = self.esptool()
        self.set_limit(esptool, 0)
        self.set_limit(esptool, 0, "--wait", "240")
        self.assertEqual(esptool.waited, [20.0, 240.0])

    def test_a_reply_that_does_not_come_is_no_reply_after_the_limit_was_stored(self):
        def silent(port, wait=0):
            raise Failure("no-reply", "nothing arrived")
        esptool = self.esptool()
        result = self.set_limit(esptool, 0, status=silent)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"\Aerror: no-reply: [^\n]*\n\Z")
        self.assertEqual(limit.stored(self.on_the_board(esptool)), 0)

    def test_a_configuration_that_is_no_object_is_refused_and_nothing_is_written(self):
        for content in (b"[]", b'{"hw":5}', b'{"hw":{"led":[]}}'):
            with self.subTest(content=content):
                esptool = self.esptool(support.storage_image({**support.BENCH_FILES, "/cfg.json": content}), failing_verifies=1)
                result = self.set_limit(esptool, 0)
                self.assertEqual(result.status, 1)
                self.assertRegex(result.err, r"\Aerror: wled-settings-malformed: [^\n]*/cfg\.json[^\n]*\n\Z")
                self.assertEqual(esptool.wrote, [])
                self.assertEqual(esptool.commands()[-1], "chip-id")

    def test_without_the_option_the_limit_file_is_read(self):
        esptool = self.esptool(limit.apply(self.old, 0))
        result = self.run_limit("set-limit", esptool)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out.splitlines()[:2], [LAYOUT_LINE, "limit: 850 mA"])
        self.assertEqual(limit.stored(applied(limit.apply(self.old, 0), esptool.wrote)), 850)

    def test_its_options(self):
        self.assertEqual(options_of("set-limit"), {"-h", "--help", "--port", "--settings", "--wait"})


class ReadLimit(WithALimitFile):
    def read_limit(self, image):
        esptool = self.esptool(image)
        return esptool, self.run_limit("read-limit", esptool)

    def test_it_prints_the_limit_the_board_holds(self):
        esptool, result = self.read_limit(self.old)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out, f"{LAYOUT_LINE}\nlimit: 850 mA\n")
        self.assertEqual(result.err, "")

    def test_a_limit_of_0_is_off(self):
        self.assertEqual(self.read_limit(limit.apply(self.old, 0))[1].out, f"{LAYOUT_LINE}\nlimit: off\n")

    def test_a_board_without_the_member_uses_wleds_own(self):
        for content in (b'{"def":{"on":true}}', b'{"hw":{"led":{"fps":50}}}', b"not JSON"):
            with self.subTest(content=content):
                self.assertEqual(self.read_limit(support.storage_image({"/cfg.json": content}))[1].out, f"{LAYOUT_LINE}\nlimit: not stored; WLED uses 850 mA\n")
                for path in (self.work / "storage").iterdir():
                    path.unlink()
        self.assertEqual(self.read_limit(support.storage_image({"/odrig/show.json": b"a show"}))[1].out, f"{LAYOUT_LINE}\nlimit: not stored; WLED uses 850 mA\n")

    def test_it_reads_the_table_and_storage_restarts_the_board_and_writes_nothing(self):
        esptool, _ = self.read_limit(self.old)
        self.assertEqual(esptool.commands(), ["read-flash", "read-flash", "chip-id"])
        self.assertEqual(esptool.wrote, [])
        last = esptool.calls[-1]
        self.assertEqual(last[last.index("--after") + 1], "hard-reset")
        for word in ("write-flash", "erase-region", "erase-flash"):
            self.assertNotIn(word, esptool.words())

    def test_its_options(self):
        self.assertEqual(options_of("read-limit"), {"-h", "--help", "--port"})


class InstallFirmware(WithALimitFile):
    def install(self, esptool, milliamps, *extra, **named):
        with mock.patch.object(build, "checked_image", side_effect=lambda image: self.image):
            return self.run_limit("install-firmware", esptool, "--settings", self.settings_file, "--limit", self.limit_file(milliamps), *extra, **named)

    def test_one_write_of_storage_holds_the_name_the_password_and_the_limit(self):
        esptool = self.esptool()
        result = self.install(esptool, 0)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out, f"{LAYOUT_LINE}\nname: {NAME}\npassword: set\nlimit: off\n{REPLY}\n")
        self.assertEqual(esptool.commands(), ["read-flash", "erase-region", "write-flash", "read-flash", "read-flash", "write-flash", "verify-flash", "chip-id"])
        in_storage = [(address, content) for address, content in esptool.wrote if address >= STORAGE_AT]
        board_now = applied(self.old, in_storage)
        self.assertEqual(limit.stored(board_now), 0)
        self.assertTrue(wifi.holds(board_now, self.settings))

    def test_a_refused_limit_file_makes_no_call_at_all(self):
        path = self.limit_file(0)
        path.write_text('{"milliamps": 65536}')
        with support.untouched_board(), mock.patch.object(build, "checked_image", side_effect=lambda image: self.image) as checked:
            result = support.run_main("install-firmware", "--settings", self.settings_file, "--limit", path)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"\Aerror: limit-invalid: [^\n]*\n\Z")
        checked.assert_not_called()

    def test_the_settings_file_is_judged_before_the_limit_file(self):
        self.settings_file.write_text('{"name": "", "password": "long enough"}')
        with support.untouched_board():
            result = support.run_main("install-firmware", "--settings", self.settings_file, "--limit", pathlib.Path(self.work, "absent.json"))
        self.assertRegex(result.err, r"\Aerror: wifi-name-invalid: ")

    def test_nothing_of_the_run_shows_the_password(self):
        self.install(self.esptool(), 0)
        self.assertEqual([result.status for result in self.results], [0])
        self.assertFalse(PASSWORD in self.results[0].out + self.results[0].err)
        self.nothing_shows_the_password()


if __name__ == "__main__":
    unittest.main()

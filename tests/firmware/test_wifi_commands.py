import pathlib
import tempfile
import unittest
from unittest import mock

from fwtool import Failure, board, cli, paths, storage, wifi

from . import support

STORAGE_AT = 0x610000
REPLY = '{"ok":true,"on":true,"brightness":32,"playing":3,"animation":1,"fps":50,"error":null}'

# Settings made for these tests. The password is found nowhere else, so that a run can be
# searched for it.
NAME = "odrig-in-a-command-test"
PASSWORD = "seen-only-in-the-storage-image"


def applied(old, wrote):
    """A storage image with the recorded writes laid over it."""
    made = bytearray(old)
    for address, content in wrote:
        made[address - STORAGE_AT:address - STORAGE_AT + len(content)] = content
    return bytes(made)


def options_of(command):
    actions = next(action for action in cli.parser()._actions if getattr(action, "choices", None) and command in action.choices)
    return {option for action in actions.choices[command]._actions for option in action.option_strings}


class OnASmallLayout(unittest.TestCase):
    """A work folder of its own, a settings file outside it, and the stand-in for esptool."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.work = pathlib.Path(holder.name, "work")
        self.work.mkdir()
        patched = mock.patch.object(paths, "STORAGE", self.work / "storage")
        patched.start()
        self.addCleanup(patched.stop)
        self.settings_file = pathlib.Path(holder.name, "given.json")
        self.settings_file.write_text('{"name": "%s", "password": "%s"}' % (NAME, PASSWORD))
        self.settings = wifi.Settings(NAME, PASSWORD)
        self.old = support.storage_image(support.BENCH_FILES)
        self.table = support.partition_table(support.small_layout())
        self.results = []
        self.esptools = []

    def esptool(self, image=None, **named):
        """The stand-in with a board that holds an image. It confirms the checksum of
        whatever image the work folder keeps, unless it is told to fail that comparison."""
        made = support.RecordedEsptool(self.table, {STORAGE_AT: self.old if image is None else image}, **named)
        self.esptools.append(made)
        return made

    def run_command(self, command, esptool, *extra, answer=REPLY, status=None):
        with support.no_board(esptool, answer=answer):
            replaced = {} if status is None else {"status": status}
            with mock.patch.dict(board.EXPECTED, replaced):
                result = support.run_main(command, "--settings", self.settings_file, *extra)
        self.results.append(result)
        return result

    def on_the_board(self, esptool, image=None):
        return applied(self.old if image is None else image, esptool.wrote)

    def kept(self):
        """The storage images the work folder keeps, by the last part of their names."""
        folder = self.work / "storage"
        return {path.name.split("-", 1)[1]: path.read_bytes() for path in folder.iterdir()} if folder.is_dir() else {}

    def nothing_shows_the_password(self):
        secret = PASSWORD.encode("ascii")
        for result in self.results:
            self.assertFalse(PASSWORD in result.out, "standard output")
            self.assertFalse(PASSWORD in result.err, "standard error")
        for esptool in self.esptools:
            self.assertFalse(any(PASSWORD in word for word in esptool.words()), "an argument of esptool")
        for path in sorted(self.work.rglob("*")):
            if path.is_file():
                self.assertEqual(path.suffix, ".bin", path.name)
                self.assertEqual(path.parent, self.work / "storage", path.name)
        self.assertTrue(any(secret in content for content in self.kept().values()))


class SetWifi(OnASmallLayout):
    def set_wifi(self, esptool, *extra, **named):
        return self.run_command("set-wifi", esptool, *extra, **named)

    def test_it_writes_the_settings_into_storage_and_prints_three_lines(self):
        esptool = self.esptool()
        result = self.set_wifi(esptool)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out, f"name: {NAME}\npassword: set\n{REPLY}\n")
        self.assertEqual(result.err, "")
        board_now = self.on_the_board(esptool)
        self.assertTrue(wifi.holds(board_now, self.settings))
        self.assertTrue(storage.show_of(board_now) == storage.show_of(self.old))

    def test_it_reads_the_table_and_storage_writes_once_as_data_and_compares_the_partition(self):
        esptool = self.esptool()
        self.set_wifi(esptool)
        self.assertEqual(esptool.commands(), ["read-flash", "read-flash", "write-flash", "verify-flash"])
        self.assertEqual(esptool.calls[0][esptool.calls[0].index("read-flash") + 1:][:2], ["0x8000", "0xc00"])
        write = next(call for call in esptool.calls if "write-flash" in call)
        self.assertIn("--force", write)
        for address, content in esptool.wrote:
            self.assertTrue(STORAGE_AT <= address and address + len(content) <= STORAGE_AT + len(self.old), hex(address))
            self.assertEqual((address - STORAGE_AT) % support.BLOCK_SIZE, 0)
        address, image = esptool.pairs(esptool.call("verify-flash"))[0]
        self.assertEqual(address, "0x610000")
        self.assertEqual(pathlib.Path(image).parent, self.work / "storage")
        self.assertTrue(storage.kept_images(len(self.old))[0].read_bytes() == self.on_the_board(esptool))
        self.assertNotIn("erase-region", esptool.words())
        self.assertNotIn("erase-flash", esptool.words())
        last = esptool.calls[-1]
        self.assertEqual(last[last.index("--after") + 1], "hard-reset")
        for call in esptool.calls[:-1]:
            self.assertEqual(call[call.index("--after") + 1], "no-reset")

    def test_storage_from_before_and_the_new_image_are_kept(self):
        esptool = self.esptool()
        self.set_wifi(esptool)
        kept = self.kept()
        self.assertEqual(sorted(kept), ["after.bin", "before.bin"])
        self.assertTrue(kept["before.bin"] == self.old)
        self.assertTrue(kept["after.bin"] == self.on_the_board(esptool))

    def test_its_status_is_0_also_when_the_reply_reports_an_invalid_show(self):
        answer = '{"ok":true,"on":true,"brightness":0,"playing":null,"animation":null,"fps":50,"error":"show-missing"}'
        result = self.set_wifi(self.esptool(), answer=answer)
        self.assertEqual(result.status, 0)
        self.assertEqual(result.out.splitlines()[-1], answer)

    def test_run_again_on_what_was_written_it_writes_nothing(self):
        first = self.esptool()
        self.set_wifi(first)
        second = self.esptool(self.on_the_board(first))
        result = self.set_wifi(second)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out, f"name: {NAME}\npassword: set\n{REPLY}\n")
        self.assertEqual(second.commands(), ["read-flash", "verify-flash", "verify-flash"])
        self.assertEqual(second.wrote, [])

    def test_the_reply_is_waited_for_20_seconds_or_as_long_as_told(self):
        esptool = self.esptool()
        self.set_wifi(esptool)
        self.set_wifi(esptool, "--wait", "240")
        self.assertEqual(esptool.waited, [20.0, 240.0])
        self.assertEqual(self.set_wifi(esptool, "--wait", "0").status, 2)

    def test_a_reply_that_does_not_come_is_no_reply_after_the_settings_were_stored(self):
        def silent(port, wait=0):
            raise Failure("no-reply", f"no reply to status within {wait:g} seconds: nothing arrived")
        esptool = self.esptool()
        result = self.set_wifi(esptool, status=silent)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"\Aerror: no-reply: [^\n]*\n\Z")
        self.assertEqual(result.out, "")
        self.assertTrue(wifi.holds(self.on_the_board(esptool), self.settings))
        self.assertIn("after.bin", self.kept())

    def test_a_comparison_that_fails_is_verify_failed_and_the_new_image_is_not_kept(self):
        esptool = self.esptool(failing_verifies=1)
        result = self.set_wifi(esptool)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"\Aerror: verify-failed: [^\n]*\n\Z")
        self.assertEqual(esptool.commands(), ["read-flash", "read-flash", "write-flash", "verify-flash", "chip-id"])
        last = esptool.calls[-1]
        self.assertEqual(last[last.index("--after") + 1], "hard-reset")
        self.assertEqual(sorted(self.kept()), ["before.bin"])

    def test_settings_of_wled_that_are_no_object_are_refused_and_nothing_is_written(self):
        for content in (b"[]", b'{"ap":5}', b"not JSON"):
            with self.subTest(content=content):
                esptool = self.esptool(support.storage_image({**support.BENCH_FILES, "/cfg.json": content}), failing_verifies=1)
                result = self.set_wifi(esptool)
                self.assertEqual(result.status, 1)
                self.assertRegex(result.err, r"\Aerror: wled-settings-malformed: [^\n]*/cfg\.json[^\n]*\n\Z")
                self.assertEqual(esptool.wrote, [])
                self.assertEqual(esptool.commands()[-1], "chip-id")
                self.assertNotIn("write-flash", esptool.commands())

    def test_without_the_option_the_settings_file_is_read(self):
        esptool = self.esptool()
        with support.no_board(esptool, answer=REPLY):
            result = support.run_main("set-wifi")
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out.splitlines()[:2], ["name: odrig", "password: set"])
        self.assertTrue(wifi.holds(self.on_the_board(esptool), wifi.read()))
        self.assertFalse(wifi.read().password in result.out + result.err)

    def test_it_has_no_option_that_carries_a_name_or_a_password(self):
        self.assertEqual(options_of("set-wifi"), {"-h", "--help", "--port", "--settings", "--wait"})

    def test_nothing_of_these_runs_shows_the_password(self):
        def silent(port, wait=0):
            raise Failure("no-reply", "nothing arrived")
        first = self.esptool()
        self.set_wifi(first)
        self.set_wifi(self.esptool(self.on_the_board(first)))
        self.set_wifi(self.esptool(failing_verifies=1), status=silent)
        self.set_wifi(self.esptool(failing_verifies=2))
        self.set_wifi(self.esptool(support.storage_image({**support.BENCH_FILES, "/wsec.json": b'"a text"'}), failing_verifies=1))
        self.assertEqual([result.status for result in self.results], [0, 0, 1, 1, 1])
        self.nothing_shows_the_password()


if __name__ == "__main__":
    unittest.main()

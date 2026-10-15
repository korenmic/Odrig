import pathlib
import re
import subprocess
import tempfile
import unittest
from unittest import mock

from littlefs.errors import LittleFSError

from fwtool import Failure, board, build, cli, paths, storage, wifi

from . import support

STORAGE_AT = 0x610000
REPLY = '{"ok":true,"on":true,"brightness":32,"playing":3,"animation":1,"fps":50,"error":null}'
# The line with which a command says which layout it found: WLED's, with the small storage.
LAYOUT_LINE = "layout: WLED's, storage 262144 bytes"

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
        self.image = pathlib.Path(holder.name, "odrig-firmware.bin")
        self.image.write_bytes((support.PROGRAM + bytes(range(256)) * 16)[:4096])
        build.write_checksum(self.image)

    def esptool(self, image=None, **named):
        """The stand-in with a board that holds an image. It confirms the checksum of
        whatever image the work folder keeps, unless it is told to fail that comparison."""
        made = support.RecordedEsptool(self.table, {STORAGE_AT: self.old if image is None else image}, **named)
        self.esptools.append(made)
        return made

    def run_command(self, command, esptool, *extra, answer=REPLY, status=None):
        with support.no_board(esptool, answer=answer):
            replaced = {} if status is None else {"status": status}
            # The reply after the storage was written is the one of a board that has read
            # its animations.
            settled = board.settled if status is None else status
            with mock.patch.dict(board.EXPECTED, replaced), mock.patch.object(board, "settled", settled):
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
        self.assertEqual(result.out, f"{LAYOUT_LINE}\nname: {NAME}\npassword: set\n{REPLY}\n")
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
        self.assertEqual(result.out, f"{LAYOUT_LINE}\nname: {NAME}\npassword: set\n{REPLY}\n")
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
        self.assertEqual(result.out, f"{LAYOUT_LINE}\n")
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

    def test_settings_that_do_not_fit_into_storage_are_no_space_and_nothing_is_written(self):
        given = dict(support.BENCH_FILES)
        given["/cfg.json"] = b'{"um":{"note":"' + b"n" * 9000 + b'"}}'
        system = storage.mount(support.storage_image(given, blocks=16))
        full, number = bytes(system.context.buffer), 0
        with self.assertRaises(LittleFSError):
            while True:
                with system.open(f"/fill-{number}.bin", "wb") as file:
                    file.write(bytes(range(256)) * 16)
                full, number = bytes(system.context.buffer), number + 1
        self.table = support.partition_table(support.small_layout(blocks=16))
        esptool = self.esptool(full)
        result = self.set_wifi(esptool)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"\Aerror: no-space: [^\n]*\n\Z")
        self.assertEqual(esptool.wrote, [])
        self.assertEqual(esptool.commands(), ["read-flash", "read-flash", "chip-id"])

    def test_without_the_option_the_settings_file_is_read(self):
        esptool = self.esptool()
        with support.no_board(esptool, answer=REPLY):
            result = support.run_main("set-wifi")
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out.splitlines()[:3], [LAYOUT_LINE, "name: odrig", "password: set"])
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


class InstallFirmware(OnASmallLayout):
    def install(self, esptool, *extra, **named):
        with mock.patch.object(build, "checked_image", side_effect=lambda image: self.image) as self.checked:
            return self.run_command("install-firmware", esptool, *extra, **named)

    def test_it_writes_the_firmware_and_then_does_what_set_wifi_does(self):
        esptool = self.esptool()
        result = self.install(esptool)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out, f"{LAYOUT_LINE}\nname: {NAME}\npassword: set\nlimit: 850 mA\n{REPLY}\n")
        self.assertEqual(esptool.commands(), ["read-flash", "erase-region", "write-flash", "read-flash", "read-flash", "write-flash", "verify-flash"])
        self.checked.assert_called_once_with(build.image_path("firmware"))
        program, data = [call for call in esptool.calls if "write-flash" in call]
        self.assertEqual([(address, pathlib.Path(name).name) for address, name in esptool.pairs(program[program.index("write-flash") + 1:])], [("0x10000", "odrig-firmware.bin")])
        self.assertNotIn("--force", program)
        self.assertIn("--force", data)
        erase = next(call for call in esptool.calls if "erase-region" in call)
        self.assertEqual(erase[erase.index("erase-region") + 1:], ["0xe000", "0x2000"])
        in_storage = [(address, content) for address, content in esptool.wrote if address >= STORAGE_AT]
        self.assertEqual(len(in_storage), len(esptool.wrote) - 1)
        self.assertTrue(wifi.holds(applied(self.old, in_storage), self.settings))

    def test_storage_is_read_only_after_the_firmware_has_answered(self):
        esptool = self.esptool()
        answered = []

        def status(port, wait=0):
            answered.append(len(esptool.calls))
            return REPLY
        self.install(esptool, status=status)
        self.assertEqual(answered, [3, 7])
        reads_of_storage = [number for number, call in enumerate(esptool.calls) if "read-flash" in call and "0x610000" in call]
        self.assertEqual(reads_of_storage, [4])

    def test_the_reply_is_waited_for_after_each_of_the_two_restarts(self):
        esptool = self.esptool()
        self.install(esptool)
        self.install(esptool, "--wait", "90")
        self.assertEqual(esptool.waited, [300.0, 300.0, 90.0, 90.0])

    def test_without_the_option_the_settings_file_is_read(self):
        esptool = self.esptool()
        with support.no_board(esptool, answer=REPLY), mock.patch.object(build, "checked_image", side_effect=lambda image: self.image):
            result = support.run_main("install-firmware")
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(result.out.splitlines()[:3], [LAYOUT_LINE, "name: odrig", "password: set"])
        self.assertFalse(wifi.read().password in result.out + result.err)

    def test_a_refused_settings_file_makes_no_call_at_all(self):
        self.settings_file.write_text('{"name": "%s", "password": "short"}' % NAME)
        with support.untouched_board(), mock.patch.object(build, "checked_image", side_effect=lambda image: self.image) as checked:
            result = support.run_main("install-firmware", "--settings", self.settings_file)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"\Aerror: wifi-password-invalid: [^\n]*\n\Z")
        checked.assert_not_called()

    def test_without_a_built_image_it_makes_no_call_at_all(self):
        with support.untouched_board(), mock.patch.object(build, "image_path", lambda kind: self.work / "absent.bin"):
            result = support.run_main("install-firmware", "--settings", self.settings_file)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"\Aerror: image-missing: [^\n]*\n\Z")

    def test_a_board_that_does_not_answer_after_the_flash_gets_no_settings(self):
        def silent(port, wait=0):
            raise Failure("no-reply", "nothing arrived")
        esptool = self.esptool()
        result = self.install(esptool, status=silent)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"\Aerror: no-reply: ")
        self.assertEqual(esptool.commands(), ["read-flash", "erase-region", "write-flash"])

    def test_it_has_no_option_that_carries_a_name_or_a_password(self):
        self.assertEqual(options_of("install-firmware"), {"-h", "--help", "--port", "--settings", "--limit", "--wait"})

    def test_nothing_of_these_runs_shows_the_password(self):
        first = self.esptool()
        self.install(first)
        self.install(self.esptool(applied(self.old, [(address, content) for address, content in first.wrote if address >= STORAGE_AT])))
        self.install(self.esptool(failing_verifies=2))
        self.assertEqual([result.status for result in self.results], [0, 0, 1])
        self.nothing_shows_the_password()


class WhereThePasswordGoes(unittest.TestCase):
    """What the sources say, beside what the runs show."""

    def sources(self, *folders):
        listed = subprocess.run(["git", "-C", str(support.ROOT), "ls-files", "-z", *folders], capture_output=True, check=True).stdout.decode("utf-8")
        return [support.ROOT / name for name in listed.split("\0") if name.endswith(".py")]

    def test_only_the_module_of_the_settings_reads_the_password_of_the_settings(self):
        reading = [path.name for path in self.sources("firmware") if re.search(r"\.password\b", path.read_text(encoding="utf-8"))]
        self.assertEqual(reading, ["wifi.py"])

    def test_no_command_takes_a_name_or_a_password_from_the_environment(self):
        for path in self.sources("firmware/fwtool"):
            if path.name in ("wifi.py", "cli.py"):
                self.assertNotRegex(path.read_text(encoding="utf-8"), r"os\.environ|getenv", path.name)

    def test_no_tool_and_no_test_changes_the_network_settings_of_this_computer(self):
        this = pathlib.Path(__file__).resolve()
        for path in self.sources("firmware", "tests/firmware", "tests/board", "tests/air", "odrigctl"):
            if path.resolve() != this:
                self.assertNotRegex(path.read_text(encoding="utf-8"), r"networksetup|airport -|nmcli|netsh wlan|CoreWLAN", path.name)


class Flash(OnASmallLayout):
    def test_flash_makes_no_call_that_reads_or_writes_storage(self):
        esptool = self.esptool()
        with support.no_board(esptool, answer=REPLY):
            result = support.run_main("flash", "--image", self.image)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(esptool.commands(), ["read-flash", "erase-region", "write-flash"])
        self.assertEqual(esptool.call("read-flash")[:2], ["0x8000", "0xc00"])
        self.assertEqual([address for address, _ in esptool.wrote], [0x10000])
        self.assertFalse(any(word.startswith("0x61") for word in esptool.words()))
        self.assertEqual(self.kept(), {})
        self.assertEqual(options_of("flash"), {"-h", "--help", "--port", "--image", "--standalone", "--expect", "--wait"})


if __name__ == "__main__":
    unittest.main()

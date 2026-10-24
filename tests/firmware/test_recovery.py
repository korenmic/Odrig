"""A change of the board's storage written in its order, cut at each of its steps, and
finished or given up by `recover-storage`, on a stand-in board of each layout."""

import pathlib
import shutil
import signal
import tempfile
import unittest
from unittest import mock

from fwtool import journal, paths, storage

from . import support

BLOCKS = 64
LAYOUTS = {"WLED's": (support.small_layout(BLOCKS), 0x610000), "bigger": (support.small_bigger_layout(BLOCKS), 0x310000)}


class Killed(BaseException):
    """The tool's process ends at once, as by a power cut of the computer."""


class Board:
    """Stands in for esptool on a board whose storage it keeps: what is written lands in
    the storage, a comparison compares with it, and `fault` makes one call of a command go
    wrong: `(command, number, kind)`, the kind being `fail` (nothing done), `cut` (the
    first half of the first stretch written, then a failure), `interrupt` (half written,
    then an interrupt from the keyboard; a held one lets the call finish) or `kill`."""

    def __init__(self, table, address, image, fault=None):
        self.table = table
        self.address = address
        self.flash = bytearray(image)
        self.fault = fault
        self.calls = []
        self.waited = []
        self.restarts = 0

    def commands(self):
        names = ("read-flash", "erase-region", "write-flash", "verify-flash", "chip-id")
        return [next(word for word in call if word in names) for call in self.calls]

    def storage(self):
        return bytes(self.flash)

    def __call__(self, arguments):
        self.calls.append(list(arguments))
        command = self.commands()[-1]
        number = self.commands().count(command)
        kind = self.fault[2] if self.fault is not None and self.fault[:2] == (command, number) else None
        # esptool resets the chip as `--after` says when its command has ended, also with an
        # error.
        if arguments[arguments.index("--after") + 1] == "hard-reset":
            self.restarts += 1
        if kind == "fail":
            return 2, f"A fatal error occurred: {command} failed"
        if command == "read-flash":
            address, size, path = arguments[arguments.index("read-flash") + 1:][:3]
            address, size = int(address, 16), int(size, 16)
            content = self.table if address == 0x8000 else bytes(self.flash[address - self.address:address - self.address + size])
            pathlib.Path(path).write_bytes(content)
        elif command == "write-flash":
            pairs = support.RecordedEsptool.pairs(arguments[arguments.index("write-flash") + 1:])
            for at, (address, name) in enumerate(pairs):
                content = pathlib.Path(name).read_bytes()
                offset = int(address, 16) - self.address
                if at == 0 and kind in ("cut", "interrupt", "kill"):
                    half = len(content) // 2
                    self.flash[offset:offset + half] = content[:half]
                    if kind == "cut":
                        return 2, "A fatal error occurred: the port went away"
                    if kind == "kill":
                        raise Killed()
                    signal.raise_signal(signal.SIGINT)
                self.flash[offset:offset + len(content)] = content
        elif command == "verify-flash":
            if kind == "interrupt":
                signal.raise_signal(signal.SIGINT)
            for address, name in support.RecordedEsptool.pairs(arguments[arguments.index("verify-flash") + 1:]):
                content = pathlib.Path(name).read_bytes()
                offset = int(address, 16) - self.address
                if bytes(self.flash[offset:offset + len(content)]) != content:
                    return 2, "A fatal error occurred: Verification failed"
        return 0, "done"


class Change(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name)
        patched = mock.patch.object(paths, "STORAGE", self.folder / "storage")
        patched.start()
        self.addCleanup(patched.stop)
        self.old = support.storage_image()
        with support.example_show() as packed:
            shutil.copytree(packed, self.folder / "show")
        self.show = self.folder / "show"
        self.files = storage.folder_files(self.show)
        self.new = storage.with_show(self.old, self.files)
        self.found = storage.plan(self.old, self.new)

    def board(self, layout="WLED's", fault=None, image=None):
        table, address = LAYOUTS[layout]
        return Board(support.partition_table(table), address, self.old if image is None else image, fault)

    def run_on(self, board, *arguments):
        with support.no_board(board, answer=support.VALID):
            return support.run_main(*arguments)

    def left(self):
        """The files the work folder holds, by their names less the time."""
        folder = self.folder / "storage"
        return sorted(path.name.split("-", 1)[-1] for path in folder.iterdir()) if folder.is_dir() else []

    def assert_old(self, board):
        self.assertEqual(storage.show_of(board.storage()), storage.show_of(self.old))
        self.assertEqual(storage.other_files(board.storage()), storage.other_files(self.old))

    def test_the_example_change_has_free_blocks_and_blocks_in_use(self):
        self.assertGreater(len(self.found.free), 0)
        self.assertGreater(len(self.found.in_use), 0)

    def test_the_free_blocks_are_written_first_then_the_blocks_in_use_and_every_run_is_compared(self):
        for layout in LAYOUTS:
            with self.subTest(layout=layout):
                shutil.rmtree(self.folder / "storage", ignore_errors=True)
                board = self.board(layout)
                result = self.run_on(board, "install-show", self.show)
                self.assertEqual(result.status, 0, result.err)
                self.assertEqual(board.commands(), ["read-flash", "read-flash", "write-flash", "write-flash", "verify-flash", "chip-id"])
                first, second = [support.RecordedEsptool.pairs(call[call.index("write-flash") + 1:]) for call in board.calls if "write-flash" in call]
                address = LAYOUTS[layout][1]
                self.assertEqual([int(at, 16) - address for at, _ in first], [offset for offset, _ in self.found.free])
                self.assertEqual([int(at, 16) - address for at, _ in second], [offset for offset, _ in self.found.in_use])
                compared = support.RecordedEsptool.pairs(board.calls[-2][board.calls[-2].index("verify-flash") + 1:])
                self.assertEqual(sorted(int(at, 16) - address for at, _ in compared), sorted(offset for offset, _ in self.found.free + self.found.in_use))
                self.assertEqual([call[call.index("--after") + 1] for call in board.calls], ["no-reset"] * 5 + ["hard-reset"])
                self.assertEqual(board.storage(), self.new)
                self.assertEqual(self.left(), ["after.bin", "before.bin"])
                written = storage.run_bytes(self.found.free) + storage.run_bytes(self.found.in_use)
                self.assertIn(f"storage: committed: {written} bytes written and compared; the board restarts\n", result.out)

    def test_a_cut_before_the_commit_leaves_the_storage_from_before_and_the_board_restarted(self):
        for kind, reason in (("fail", "esptool-failed"), ("cut", "esptool-failed"), ("interrupt", "cancelled")):
            with self.subTest(kind=kind):
                shutil.rmtree(self.folder / "storage", ignore_errors=True)
                board = self.board(fault=("write-flash", 1, kind))
                result = self.run_on(board, "install-show", self.show)
                self.assertEqual(result.status, 1)
                self.assertRegex(result.err, rf"^error: {reason}: .*the change was not made: no block the board's file system uses was written, and the board holds its storage from before\n$")
                self.assert_old(board)
                self.assertEqual(board.commands()[-1], "chip-id")
                self.assertEqual(self.left(), ["before.bin"])
                again = self.run_on(Board(board.table, board.address, board.storage()), "install-show", self.show)
                self.assertEqual(again.status, 0, again.err)

    def test_a_cut_in_the_commit_or_the_comparison_leaves_the_journal_and_the_board_in_its_bootloader(self):
        for fault in (("write-flash", 2, "fail"), ("write-flash", 2, "cut"), ("verify-flash", 1, "fail")):
            with self.subTest(fault=fault):
                shutil.rmtree(self.folder / "storage", ignore_errors=True)
                board = self.board(fault=fault)
                result = self.run_on(board, "install-show", self.show)
                self.assertEqual(result.status, 1)
                self.assertRegex(result.err, r"^error: recovery-needed: .*The board stays in its bootloader, so that it does not start on a storage it may not read; run python3 firmware/fw\.py recover-storage\n$")
                self.assertEqual(board.restarts, 0)
                self.assertNotIn("chip-id", board.commands())
                self.assertEqual(journal.read()["step"], "commit" if fault[0] == "write-flash" else "compare")
                self.assertEqual(self.left(), ["after.bin.part", "before.bin", "change.json"])
                recovered = self.run_on(Board(board.table, board.address, board.storage()), "recover-storage")
                self.assertEqual(recovered.status, 0, recovered.err)
                self.assertIn("storage: committed: the change was finished", recovered.out)
                self.assertEqual(self.left(), ["after.bin", "before.bin"])

    def test_after_a_recovery_the_board_holds_the_new_image(self):
        board = self.board(fault=("write-flash", 2, "cut"))
        self.run_on(board, "install-show", self.show)
        healthy = Board(board.table, board.address, board.storage())
        result = self.run_on(healthy, "recover-storage")
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(healthy.storage(), self.new)
        self.assertEqual(healthy.commands(), ["read-flash", "verify-flash", "write-flash", "write-flash", "verify-flash", "chip-id"])
        self.assertEqual(healthy.restarts, 1)
        self.assertIsNone(journal.read())
        self.assertEqual(storage.kept_images(len(self.old))[0].read_bytes(), self.new)

    def test_an_interrupt_in_the_commit_or_the_comparison_waits_for_it_to_end(self):
        for fault in (("write-flash", 2, "interrupt"), ("verify-flash", 1, "interrupt")):
            with self.subTest(fault=fault):
                shutil.rmtree(self.folder / "storage", ignore_errors=True)
                board = self.board(fault=fault)
                result = self.run_on(board, "install-show", self.show)
                self.assertEqual(result.status, 0, result.err)
                self.assertEqual(board.storage(), self.new)
                self.assertIn("; an interrupt came while the change was committed and waited for it; the board restarts\n", result.out)
                self.assertIsNone(journal.read())

    def test_while_a_change_is_unfinished_no_other_command_touches_the_board(self):
        board = self.board(fault=("write-flash", 2, "fail"))
        self.run_on(board, "install-show", self.show)
        image = self.folder / "image.bin"
        image.write_bytes(support.PROGRAM + bytes(4096 - len(support.PROGRAM)))
        (self.folder / "image.bin.sha256").write_text(__import__("hashlib").sha256(image.read_bytes()).hexdigest() + "  image.bin\n")
        limit = self.folder / "limit.json"
        limit.write_text('{"milliamps": 850}')
        for command in (["install-show", self.show], ["set-limit", "--settings", limit], ["read-show", self.folder / "out"], ["read-limit"],
                        ["flash", "--image", image], ["big-storage"]):
            with self.subTest(command=command[0]), support.untouched_board():
                result = support.run_main(*command)
                self.assertEqual(result.status, 1)
                self.assertRegex(result.err, r"^error: recovery-needed: a change of the board's storage was begun and not finished, at its step commit, .* run python3 firmware/fw\.py recover-storage first\n$")

    def test_a_change_cut_before_its_commit_by_the_end_of_the_tool_is_given_up(self):
        board = self.board(fault=("write-flash", 1, "kill"))
        with self.assertRaises(Killed):
            self.run_on(board, "install-show", self.show)
        self.assertEqual(journal.read()["step"], "free")
        healthy = Board(board.table, board.address, board.storage())
        result = self.run_on(healthy, "recover-storage")
        self.assertEqual(result.status, 0, result.err)
        self.assertIn("storage: given up: the change was cut before its commit; the board holds its storage from before; the board restarts\n", result.out)
        self.assertEqual(healthy.commands(), ["read-flash", "chip-id"])
        self.assert_old(healthy)
        self.assertEqual(self.left(), ["before.bin"])

    def test_storage_that_changed_outside_the_change_is_not_written_but_whole_on_request(self):
        board = self.board(fault=("write-flash", 2, "fail"))
        self.run_on(board, "install-show", self.show)
        changed = bytearray(board.storage())
        free, in_use = journal.runs_of(journal.read(), self.new)
        outside = journal.outside(free + in_use, len(self.new))[-1][0]
        changed[outside] ^= 0xFF
        other = Board(board.table, board.address, bytes(changed))
        result = self.run_on(other, "recover-storage")
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: storage-changed: .*recover-storage --whole writes the new image whole\n$")
        self.assertNotIn("write-flash", other.commands())
        self.assertEqual(other.restarts, 0)
        self.assertEqual(journal.read()["step"], "commit")
        whole = self.run_on(other, "recover-storage", "--whole")
        self.assertEqual(whole.status, 0, whole.err)
        self.assertEqual(other.storage(), self.new)
        self.assertIsNone(journal.read())

    def test_a_recovery_that_is_cut_can_be_run_again(self):
        board = self.board(fault=("write-flash", 2, "fail"))
        self.run_on(board, "install-show", self.show)
        cut = Board(board.table, board.address, board.storage(), fault=("write-flash", 2, "cut"))
        result = self.run_on(cut, "recover-storage")
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: recovery-needed: .*the recovery was cut and the journal stays: run python3 firmware/fw\.py recover-storage again\n$")
        healthy = Board(cut.table, cut.address, cut.storage())
        self.assertEqual(self.run_on(healthy, "recover-storage").status, 0)
        self.assertEqual(healthy.storage(), self.new)

    def test_the_outside_of_a_change_is_every_stretch_no_run_covers(self):
        runs = [(4096, b"x" * 4096), (0, b"y" * 4096), (12288, b"z" * 8192)]
        self.assertEqual(journal.outside(runs, 8 * 4096), [(8192, 4096), (20480, 12288)])

    def test_without_a_journal_recovery_touches_nothing(self):
        with support.untouched_board():
            result = support.run_main("recover-storage")
        self.assertEqual((result.status, result.out, result.err), (0, "storage: nothing to recover: no change of the board's storage is unfinished\n", ""))

    def test_settings_are_written_in_the_same_order(self):
        limit = self.folder / "limit.json"
        limit.write_text('{"milliamps": 1200}')
        board = self.board(fault=("write-flash", 1, "fail"))
        installed = self.run_on(self.board(), "install-show", self.show)
        self.assertEqual(installed.status, 0, installed.err)
        board = Board(board.table, board.address, storage.kept_images(len(self.old))[0].read_bytes(), fault=("verify-flash", 2, "fail"))
        result = self.run_on(board, "set-limit", "--settings", limit)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: recovery-needed: ")
        self.assertEqual(self.run_on(Board(board.table, board.address, board.storage()), "recover-storage").status, 0)


if __name__ == "__main__":
    unittest.main()

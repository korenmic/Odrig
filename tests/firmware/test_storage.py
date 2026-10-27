import pathlib
import shutil
import struct
import tempfile
import unittest
from unittest import mock

from fwtool import paths, storage
from odrig import limits

from . import support

# Budgets' files as the core writes them: the installation's, and another the board holds.
INSTALLATION_BUDGETS = limits.dumps(60000, [(1, 3000), (2, 3000)])
BOARD_BUDGETS = limits.dumps(730, [(2, 400)])
# Budgets' files the core would not read.
UNREADABLE_BUDGETS = (
    b'{"version":1,"wall":730',
    b'{"version":2,"wall":730,"legs":[]}',
    b'{"version":1,"wall":250001,"legs":[]}',
    b'{"version":1,"wall":730,"legs":[[1,400],[1,500]]}',
    b'{"version":1,"wall":730}',
    b'{"version":1,"wall":730,"legs":[],"extra":1}',
)


def disk_version(image):
    return struct.unpack_from("<I", image, image.find(b"littlefs") + 12)[0]


def applied(old, runs):
    """An image with stretches of another written over it."""
    made = bytearray(old)
    for offset, content in runs:
        made[offset:offset + len(content)] = content
    return bytes(made)


class Temporary(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name)


class WithShow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = support.storage_image()
        with support.example_show() as folder:
            cls.files = support.files_of(folder)
        cls.new = storage.with_show(cls.old, cls.files)

    def test_the_example_show_is_three_json_and_odrg_files(self):
        self.assertEqual(sorted(self.files), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])

    def test_the_folder_holds_exactly_the_new_files_with_their_bytes(self):
        self.assertEqual(storage.show_of(self.new), self.files)
        self.assertNotIn("old.odrg", storage.show_of(self.new))

    def test_every_other_file_is_unchanged(self):
        expected = {path: content for path, content in support.WLED_FILES.items() if not path.startswith("/odrig/")}
        self.assertEqual(storage.other_files(self.new), expected)
        self.assertEqual(sorted(expected), ["/cfg.json", "/hello.gif", "/presets.json", "/wsec.json"])

    def test_the_disk_version_in_the_superblock_is_unchanged(self):
        self.assertEqual(disk_version(self.old), support.DISK_VERSION_2_0)
        self.assertEqual(disk_version(self.new), support.DISK_VERSION_2_0)
        self.assertEqual(storage.geometry(self.new), (support.DISK_VERSION_2_0, 4096, 64))

    def test_an_image_of_a_newer_disk_version_keeps_that_version(self):
        newer = support.storage_image(version=0x00020001)
        self.assertEqual(disk_version(storage.with_show(newer, self.files)), 0x00020001)

    def test_the_image_keeps_its_size(self):
        self.assertEqual(len(self.new), len(self.old))

    def test_the_runs_of_changed_blocks_applied_to_the_old_image_give_the_new_one(self):
        runs = storage.runs(self.old, self.new, 4096)
        self.assertGreater(len(runs), 0)
        self.assertEqual(applied(self.old, runs), self.new)
        for offset, content in runs:
            self.assertEqual(offset % 4096, 0)
            self.assertEqual(len(content) % 4096, 0)

    def test_neighbouring_changed_blocks_are_one_run_and_unchanged_blocks_are_in_none(self):
        old = bytes(4096 * 8)
        new = bytearray(old)
        for block in (1, 2, 3, 6, 7):
            new[block * 4096 + 5] = 1
        runs = storage.runs(old, bytes(new), 4096)
        self.assertEqual([(offset, len(content)) for offset, content in runs], [(4096, 3 * 4096), (6 * 4096, 2 * 4096)])
        self.assertEqual(storage.runs(old, old, 4096), [])

    def test_installing_the_same_show_again_changes_no_block(self):
        again = storage.with_show(self.new, self.files)
        self.assertEqual(again, self.new)
        self.assertEqual(storage.runs(self.new, again, 4096), [])

    def test_a_storage_without_the_folder_gets_it(self):
        bare = support.storage_image({"/cfg.json": b"{}"})
        self.assertEqual(storage.show_of(bare), {})
        self.assertEqual(storage.show_of(storage.with_show(bare, self.files)), self.files)

    def test_a_show_larger_than_the_free_room_is_no_space(self):
        large = dict(self.files, **{"large.odrg": bytes(range(256)) * 1024})
        self.assertEqual(support.reason_of(self, lambda: storage.with_show(self.old, large)), "no-space")

    def test_an_image_without_a_file_system_is_a_layout_mismatch(self):
        self.assertEqual(support.reason_of(self, lambda: storage.with_show(b"\xff" * 4096 * 64, self.files)), "layout-mismatch")
        self.assertEqual(support.reason_of(self, lambda: storage.show_of(self.old[:4096 * 32])), "layout-mismatch")


class ShowFolders(Temporary):
    def setUp(self):
        super().setUp()
        with support.example_show() as packed:
            shutil.copytree(packed, self.folder / "show")
        self.show = self.folder / "show"

    def reason(self, check=True):
        return support.reason_of(self, lambda: storage.folder_files(self.show, check=check))

    def test_a_packed_show_is_accepted_as_it_is(self):
        files = storage.folder_files(self.show)
        self.assertEqual({name: data for name, data in files.items() if name not in storage.CATALOG_NAMES}, support.files_of(self.show))
        self.assertIn("catalog.txt", files)

    def test_a_saved_playlist_order_is_a_file_of_the_show(self):
        (self.show / "order.txt").write_bytes(b"odrig-order 1\ni 2\n")
        self.assertEqual(storage.folder_files(self.show)["order.txt"], b"odrig-order 1\ni 2\n")

    def test_a_budgets_file_is_a_file_of_the_show_and_is_read_only_when_it_is_installed(self):
        for content in (INSTALLATION_BUDGETS, UNREADABLE_BUDGETS[0]):
            with self.subTest(content=content):
                (self.show / "limits.json").write_bytes(content)
                self.assertEqual(storage.folder_files(self.show)["limits.json"], content)

    def test_a_folder_without_its_mapping_is_refused_with_the_converters_reason(self):
        (self.show / "mapping.json").unlink()
        self.assertEqual(self.reason(), "mapping-missing")

    def test_a_malformed_mapping_and_a_malformed_show_are_refused(self):
        kept = (self.show / "show.json").read_bytes()
        (self.show / "show.json").write_text("{")
        self.assertEqual(self.reason(), "show-malformed")
        (self.show / "show.json").write_bytes(kept)
        (self.show / "mapping.json").write_text("[]")
        self.assertEqual(self.reason(), "mapping-malformed")

    def test_a_folder_without_its_show_is_refused(self):
        (self.show / "show.json").unlink()
        self.assertEqual(self.reason(), "show-missing")

    def test_a_missing_a_damaged_and_a_wrong_sized_animation_are_refused(self):
        kept = (self.show / "dvd.odrg").read_bytes()
        (self.show / "dvd.odrg").unlink()
        self.assertEqual(self.reason(), "file-missing")
        (self.show / "dvd.odrg").write_bytes(kept[:-3])
        self.assertEqual(self.reason(), "file-malformed")
        (self.show / "dvd.odrg").write_bytes(kept)
        (self.show / "mapping.json").write_bytes((support.ROOT / "mapping" / "legs-20.json").read_bytes())
        self.assertEqual(self.reason(), "size-mismatch")

    def test_a_file_the_show_does_not_name_and_a_folder_inside_are_refused(self):
        (self.show / "notes.txt").write_text("not of the show")
        self.assertEqual(self.reason(), "not-a-show-folder")
        (self.show / "notes.txt").unlink()
        (self.show / "inner").mkdir()
        self.assertEqual(self.reason(), "not-a-show-folder")
        self.assertEqual(self.reason(check=False), "not-a-show-folder")

    def test_what_is_no_folder_is_refused(self):
        self.show = self.folder / "absent"
        self.assertEqual(self.reason(), "not-a-show-folder")
        self.assertEqual(self.reason(check=False), "not-a-show-folder")

    def test_without_the_check_any_flat_folder_of_files_is_taken(self):
        (self.show / "show.json").unlink()
        (self.show / "dvd.odrg").write_bytes(b"damaged")
        (self.show / "notes.txt").write_text("not of the show")
        files = storage.folder_files(self.show, check=False)
        self.assertEqual(files, support.files_of(self.show))
        self.assertEqual(sorted(files), ["dvd.odrg", "hello.odrg", "mapping.json", "notes.txt"])


# The line with which a command says which layout it found: WLED's, with the small storage.
LAYOUT_LINE = "layout: WLED's, storage 262144 bytes"


class Commands(Temporary):
    def setUp(self):
        super().setUp()
        patched = mock.patch.object(paths, "STORAGE", self.folder / "storage")
        patched.start()
        self.addCleanup(patched.stop)
        self.old = support.storage_image()
        self.table = support.partition_table(support.small_layout())
        with support.example_show() as packed:
            shutil.copytree(packed, self.folder / "show")
        self.show = self.folder / "show"

    def esptool(self, image=None, **named):
        return support.RecordedEsptool(self.table, {0x610000: self.old if image is None else image}, **named)

    def install(self, esptool, *extra, answer='{"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}'):
        with support.no_board(esptool, answer=answer):
            return support.run_main("install-show", self.show, *extra)

    def on_the_board(self, esptool):
        """The storage as the recorded writes leave it."""
        return applied(self.old, [(address - 0x610000, content) for address, content in esptool.wrote])

    def another_board(self, files=None):
        """A board that holds other files: its storage, and no image kept from the last."""
        self.old = support.storage_image(files)
        shutil.rmtree(self.folder / "storage", ignore_errors=True)

    def test_install_show_puts_the_folder_into_storage_and_prints_the_reply(self):
        esptool = self.esptool()
        result = self.install(esptool)
        self.assertEqual(result.status, 0, result.err)
        lines = result.out.splitlines()
        self.assertEqual((lines[0], lines[-2], lines[-1]), (LAYOUT_LINE, '{"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}', "outcome: healthy"))
        self.assertEqual(storage.show_of(self.on_the_board(esptool)), storage.folder_files(self.show))
        self.assertEqual(storage.other_files(self.on_the_board(esptool)), storage.other_files(self.old))

    def test_it_says_how_the_show_changes_before_it_writes(self):
        first = self.esptool()
        result = self.install(first)
        files = storage.folder_files(self.show)
        added = sorted(name for name in files if name != "mapping.json")
        self.assertEqual(sorted(added), sorted(["dvd.odrg", "hello.odrg", "show.json", *(name for name in files if name in storage.CATALOG_NAMES)]))
        self.assertEqual(result.out.splitlines()[1:len(added) + 4], [
            "show: kept 0 files",
            *(f"show: added {name}, {len(files[name])} bytes" for name in added),
            f"show: replaced mapping.json, {len(files['mapping.json'])} bytes, was 16",
            "show: removed old.odrg, 1800 bytes",
        ])
        again = self.install(self.esptool(self.on_the_board(first)))
        self.assertIn(f"show: kept {len(files)} files; nothing added, replaced or removed\n", again.out)

    def test_the_boards_saved_order_is_kept_for_a_folder_without_one(self):
        order = b"odrig-order 1\ni 2\nx sunrise.odrg\n"
        self.old = support.storage_image(dict(support.WLED_FILES, **{"/odrig/order.txt": order}))
        esptool = self.esptool()
        result = self.install(esptool)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(storage.show_of(self.on_the_board(esptool)), dict(storage.folder_files(self.show), **{"order.txt": order}))
        self.assertIn("show: kept 1 files\n", result.out)
        (self.show / "order.txt").write_bytes(b"odrig-order 1\ni 1\n")
        esptool = self.esptool()
        self.install(esptool)
        self.assertEqual(storage.show_of(self.on_the_board(esptool))["order.txt"], b"odrig-order 1\ni 1\n")

    def test_the_boards_saved_playlist_is_kept_for_a_folder_without_one(self):
        playlist = b"odrig-playlist 1\nnight\n5400000\n"
        self.old = support.storage_image(dict(support.WLED_FILES, **{"/odrig/playlist.txt": playlist}))
        esptool = self.esptool()
        result = self.install(esptool)
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(storage.show_of(self.on_the_board(esptool)), dict(storage.folder_files(self.show), **{"playlist.txt": playlist}))
        self.assertIn("show: kept 1 files\n", result.out)

    def test_with_limits_the_folders_budgets_file_is_installed(self):
        (self.show / "limits.json").write_bytes(INSTALLATION_BUDGETS)
        for board_budgets in (None, BOARD_BUDGETS):
            with self.subTest(board_budgets=board_budgets):
                self.another_board(support.WLED_FILES if board_budgets is None else dict(support.WLED_FILES, **{"/odrig/limits.json": board_budgets}))
                esptool = self.esptool()
                result = self.install(esptool, "--limits")
                self.assertEqual(result.status, 0, result.err)
                self.assertEqual(storage.show_of(self.on_the_board(esptool))["limits.json"], INSTALLATION_BUDGETS)
                self.assertEqual(storage.show_of(self.on_the_board(esptool)), storage.folder_files(self.show))
                said = f"show: added limits.json, {len(INSTALLATION_BUDGETS)} bytes\n" if board_budgets is None else f"show: replaced limits.json, {len(INSTALLATION_BUDGETS)} bytes, was {len(BOARD_BUDGETS)}\n"
                self.assertIn(said, result.out)

    def test_without_limits_the_boards_budgets_file_is_kept_and_the_folders_left_out(self):
        for content in (None, INSTALLATION_BUDGETS, UNREADABLE_BUDGETS[0]):
            for extra in ((), ("--no-check",)):
                with self.subTest(content=content, extra=extra):
                    self.another_board(dict(support.WLED_FILES, **{"/odrig/limits.json": BOARD_BUDGETS}))
                    if content is not None:
                        (self.show / "limits.json").write_bytes(content)
                    esptool = self.esptool()
                    result = self.install(esptool, *extra)
                    self.assertEqual(result.status, 0, result.err)
                    on_the_board = storage.show_of(self.on_the_board(esptool))
                    self.assertEqual(on_the_board["limits.json"], BOARD_BUDGETS)
                    self.assertEqual({name: data for name, data in on_the_board.items() if name not in storage.CATALOG_NAMES},
                                     dict({name: data for name, data in support.files_of(self.show).items() if name != "limits.json"}, **{"limits.json": BOARD_BUDGETS}))
                    self.assertIn("show: kept 1 files\n", result.out)
                    self.assertNotIn("limits.json", "".join(line for line in result.out.splitlines(True) if line.startswith("show: ")))

    def test_without_limits_a_board_without_a_budgets_file_keeps_none(self):
        for content in (INSTALLATION_BUDGETS, UNREADABLE_BUDGETS[0]):
            for extra in ((), ("--no-check",)):
                with self.subTest(content=content, extra=extra):
                    self.another_board()
                    (self.show / "limits.json").write_bytes(content)
                    esptool = self.esptool()
                    result = self.install(esptool, *extra)
                    self.assertEqual(result.status, 0, result.err)
                    self.assertNotIn("limits.json", storage.show_of(self.on_the_board(esptool)))
                    self.assertNotIn("limits.json", result.out)

    def test_limits_with_a_folder_without_a_budgets_file_is_refused_before_the_board_is_touched(self):
        for extra in ((), ("--no-check",)):
            with self.subTest(extra=extra):
                with support.untouched_board():
                    result = support.run_main("install-show", self.show, "--limits", *extra)
                self.assertEqual((result.status, result.out), (1, ""))
                self.assertRegex(result.err, r"\Aerror: limits-missing: .*limits\.json")

    def test_limits_with_a_budgets_file_the_core_would_not_read_is_refused_before_the_board_is_touched(self):
        for content in UNREADABLE_BUDGETS:
            for extra in ((), ("--no-check",)):
                with self.subTest(content=content, extra=extra):
                    (self.show / "limits.json").write_bytes(content)
                    with support.untouched_board():
                        result = support.run_main("install-show", self.show, "--limits", *extra)
                    self.assertEqual((result.status, result.out), (1, ""))
                    self.assertRegex(result.err, r"\Aerror: limits-malformed: .*limits\.json: ")

    def test_read_show_keeps_the_budgets_file_and_its_copy_goes_back_only_with_limits(self):
        (self.show / "limits.json").write_bytes(BOARD_BUDGETS)
        installed = self.esptool()
        self.assertEqual(self.install(installed, "--limits").status, 0)
        board = self.on_the_board(installed)
        with support.no_board(self.esptool(board)):
            result = support.run_main("read-show", self.folder / "copy")
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(support.files_of(self.folder / "copy"), storage.show_of(board))
        self.assertEqual(support.files_of(self.folder / "copy")["limits.json"], BOARD_BUDGETS)
        self.assertIn(f"limits.json: {len(BOARD_BUDGETS)} bytes\n", result.out)
        self.show = self.folder / "copy"
        self.assertEqual(storage.folder_files(self.show)["limits.json"], BOARD_BUDGETS)
        self.another_board()
        without = self.esptool()
        self.assertEqual(self.install(without).status, 0)
        self.assertNotIn("limits.json", storage.show_of(self.on_the_board(without)))
        self.old = self.on_the_board(without)
        again = self.esptool()
        self.assertEqual(self.install(again, "--limits").status, 0)
        self.assertEqual(storage.show_of(self.on_the_board(again))["limits.json"], BOARD_BUDGETS)
        self.assertEqual(storage.show_of(self.on_the_board(again)), storage.show_of(board))

    def test_a_dry_run_says_what_would_change_and_writes_nothing(self):
        esptool = self.esptool()
        result = self.install(esptool, "--dry-run")
        self.assertEqual((result.status, result.err), (0, ""))
        lines = result.out.splitlines()
        self.assertEqual((lines[0], lines[1], lines[-1]), (LAYOUT_LINE, "show: kept 0 files", "storage: dry run: nothing written; the board restarts"))
        self.assertRegex(lines[-2], r"\Astorage: \d+ blocks to write, \d+ bytes: \d+ free first, then \d+ in use\Z")
        self.assertEqual(esptool.commands(), ["read-flash", "read-flash", "chip-id"])
        self.assertEqual((esptool.wrote, esptool.waited), ([], []))
        self.assertEqual([path.name.split("-", 1)[1] for path in storage.kept_images(len(self.old))], ["before.bin"])

    def test_copies_of_the_files_removed_or_replaced_are_kept_before_the_write(self):
        esptool = self.esptool()
        result = self.install(esptool, "--keep-copies", self.folder / "copies")
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(support.files_of(self.folder / "copies"), {"mapping.json": b"an older mapping", "old.odrg": b"an older animation" * 100})
        self.assertIn(f"kept copies: 2 files in {self.folder / 'copies'}\n", result.out)

    def test_a_folder_for_the_copies_that_is_not_empty_is_refused_before_the_board_is_touched(self):
        (self.folder / "full").mkdir()
        (self.folder / "full" / "x").write_text("x")
        with support.untouched_board():
            result = support.run_main("install-show", self.show, "--keep-copies", self.folder / "full")
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: output-not-empty: ")

    def test_the_reply_is_waited_for_300_seconds_or_as_long_as_told(self):
        esptool = self.esptool()
        self.install(esptool)
        self.install(esptool, "--wait", "240")
        self.assertEqual(esptool.waited, [300.0, 240.0])
        self.assertEqual(self.install(esptool, "--wait", "0").status, 2)

    def test_a_reply_that_reports_a_reason_is_status_1(self):
        answer = '{"ok":true,"on":true,"brightness":0,"playing":null,"animation":null,"fps":50,"error":"show-missing"}'
        result = self.install(self.esptool(), "--no-check", answer=answer)
        self.assertEqual(result.status, 1)
        lines = result.out.splitlines()
        self.assertEqual((lines[0], lines[-2], lines[-1]), (LAYOUT_LINE, answer, "outcome: recovery: show-missing"))
        self.assertEqual(result.err, "")

    def test_the_reply_printed_is_the_one_the_board_gives_once_it_has_read_its_animations(self):
        talks = support.Talking({"status": [support.VALID], "list": [support.BUSY, support.BUSY, support.BUSY, support.LISTED]})
        with support.no_board(self.esptool(), talks=talks):
            result = support.run_main("install-show", self.show)
        lines = result.out.splitlines()
        self.assertEqual((result.status, lines[0], lines[-2], lines[-1], result.err), (0, LAYOUT_LINE, support.VALID, "outcome: healthy", ""))
        self.assertEqual(talks.sent, ["status", "list", "list", "list", "list", "status"])

    def test_a_show_that_turns_invalid_while_the_board_reads_it_is_status_1(self):
        invalid = '{"ok":true,"on":true,"brightness":128,"playing":null,"animation":null,"fps":50,"error":"file-malformed dvd.odrg truncated"}'
        talks = support.Talking({"status": [support.VALID, invalid], "list": [support.BUSY, support.BUSY, '{"ok":false,"error":"show-invalid"}']})
        with support.no_board(self.esptool(), talks=talks):
            result = support.run_main("install-show", self.show, "--no-check")
        lines = result.out.splitlines()
        self.assertEqual((result.status, lines[0], lines[-2], lines[-1], result.err), (1, LAYOUT_LINE, invalid, "outcome: recovery: file-malformed dvd.odrg truncated", ""))

    def test_the_outcome_of_a_board_that_reports_its_readiness(self):
        checking = '{"ok":true,"on":true,"brightness":128,"playing":"all","animation":1,"fps":50,"error":null,"readiness":"checking","checked":1,"to_check":1,"unavailable":0,"checking":"dvd.odrg","host":null}'
        degraded = checking.replace('"checking","checked":1,"to_check":1,"unavailable":0,"checking":"dvd.odrg"', '"degraded","checked":2,"to_check":0,"unavailable":1,"checking":null')
        ready = degraded.replace('"degraded"', '"ready"').replace('"unavailable":1', '"unavailable":0')
        for final, line in ((degraded, "outcome: degraded: 1 unavailable"), (ready, "outcome: healthy")):
            with self.subTest(line):
                talks = support.Talking({"status": [checking, checking, final], "list": ['{"ok":true,"items":[],"next":null}']})
                with support.no_board(self.esptool(), talks=talks):
                    result = support.run_main("install-show", self.show)
                lines = result.out.splitlines()
                self.assertEqual((result.status, lines[0], lines[-2], lines[-1], result.err), (0, LAYOUT_LINE, final, line, ""))
                self.assertEqual(talks.sent, ["status", "status", "status"])

    def test_a_board_still_checking_when_the_time_is_over_is_not_known_yet(self):
        checking = '{"ok":true,"on":true,"brightness":128,"playing":"all","animation":1,"fps":50,"error":null,"readiness":"checking","checked":0,"to_check":2,"unavailable":0,"checking":"hello.odrg","host":null}'
        talks = support.Talking({"status": [checking]})
        with support.no_board(self.esptool(), talks=talks):
            result = support.run_main("install-show", self.show, "--wait", "4")
        lines = result.out.splitlines()
        self.assertEqual((result.status, lines[0]), (1, LAYOUT_LINE))
        self.assertFalse([line for line in lines if line.startswith("{") or line.startswith("outcome: ")], lines)
        self.assertIn("error: check-not-done: ", result.err)
        self.assertIn("its state is not known yet", result.err)

    def test_a_board_that_is_still_reading_when_the_time_is_over_is_check_not_done(self):
        talks = support.Talking({"status": [support.VALID], "list": [support.BUSY]})
        with support.no_board(self.esptool(), talks=talks):
            result = support.run_main("install-show", self.show, "--wait", "4")
        self.assertEqual((result.status, result.out.splitlines()[0]), (1, LAYOUT_LINE))
        self.assertFalse(result.out.splitlines()[-1].startswith("{"))
        self.assertRegex(result.err, r"\Aerror: check-not-done: the board was still reading its animations after 4 seconds; give it longer with --wait\n\Z")

    def test_a_copy_of_storage_from_before_and_the_new_image_are_kept_in_the_work_folder(self):
        esptool = self.esptool()
        self.install(esptool)
        kept = {path.name.split("-", 1)[1]: path.read_bytes() for path in (self.folder / "storage").iterdir()}
        self.assertEqual(sorted(kept), ["after.bin", "before.bin"])
        self.assertEqual(kept["before.bin"], self.old)
        self.assertEqual(kept["after.bin"], self.on_the_board(esptool))

    def test_the_written_runs_are_compared_with_the_new_image_and_the_board_restarted_last(self):
        esptool = self.esptool()
        self.install(esptool)
        self.assertEqual(esptool.commands(), ["read-flash", "read-flash", "write-flash", "write-flash", "verify-flash", "chip-id"])
        written = sorted(address for call in esptool.calls if "write-flash" in call for address, _ in esptool.pairs(call[call.index("write-flash") + 1:]))
        compared = esptool.pairs(esptool.call("verify-flash"))
        self.assertEqual(sorted(address for address, _ in compared), written)
        new = storage.kept_images(len(self.old))[0].read_bytes()
        self.assertEqual(new, self.on_the_board(esptool))
        for address, piece in compared:
            self.assertEqual(pathlib.Path(piece).parent, self.folder / "storage")
            self.assertFalse(pathlib.Path(piece).exists())
        self.assertEqual([call[call.index("--after") + 1] for call in esptool.calls], ["no-reset"] * 5 + ["hard-reset"])

    def test_an_invalid_show_folder_is_refused_before_the_board_is_touched(self):
        (self.show / "dvd.odrg").unlink()
        with support.untouched_board():
            result = support.run_main("install-show", self.show)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: file-missing: .*dvd\.odrg")

    def test_with_no_check_an_invalid_show_folder_is_installed(self):
        (self.show / "dvd.odrg").unlink()
        esptool = self.esptool()
        self.install(esptool, "--no-check")
        self.assertEqual(storage.show_of(self.on_the_board(esptool)), support.files_of(self.show))

    def test_a_show_that_does_not_fit_is_no_space_and_nothing_is_written(self):
        (self.show / "large.odrg").write_bytes(bytes(range(256)) * 1024)
        esptool = self.esptool()
        result = self.install(esptool, "--no-check")
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: no-space: ")
        self.assertEqual(esptool.wrote, [])
        self.assertNotIn("write-flash", esptool.commands())

    def test_the_kept_image_is_taken_when_the_chip_reports_its_checksum(self):
        first = self.esptool()
        self.install(first)
        second = self.esptool(self.on_the_board(first))
        result = self.install(second)
        self.assertEqual(second.commands(), ["read-flash", "verify-flash", "chip-id"])
        self.assertIn("storage: unchanged: nothing written; the board restarts\n", result.out)
        self.assertEqual(second.call("read-flash")[:2], ["0x8000", "0xc00"])
        self.assertEqual(second.wrote, [])

    def test_storage_is_read_again_when_the_chip_reports_another_checksum(self):
        first = self.esptool()
        self.install(first)
        second = self.esptool(failing_verifies=1)
        self.install(second)
        self.assertEqual(second.commands(), ["read-flash", "verify-flash", "read-flash", "write-flash", "write-flash", "verify-flash", "chip-id"])
        self.assertEqual(storage.show_of(self.on_the_board(second)), storage.folder_files(self.show))

    def test_a_board_that_holds_something_else_after_the_write_needs_the_recovery(self):
        esptool = self.esptool(failing_verifies=1)
        result = self.install(esptool)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: recovery-needed: .*run python3 firmware/fw\.py recover-storage\n")
        self.assertEqual(esptool.commands()[-1], "verify-flash")

    def test_read_show_gives_the_files_back(self):
        esptool = self.esptool()
        self.install(esptool)
        with support.no_board(self.esptool(self.on_the_board(esptool), failing_verifies=1)) as reading:
            result = support.run_main("read-show", self.folder / "copy")
        self.assertEqual(result.status, 0, result.err)
        self.assertEqual(support.files_of(self.folder / "copy"), storage.folder_files(self.show))
        self.assertEqual(reading.commands(), ["read-flash", "verify-flash", "read-flash", "chip-id"])
        self.assertEqual(reading.wrote, [])
        self.assertIn("hello.odrg: ", result.out)

    def test_read_show_refuses_a_folder_that_is_not_empty_and_one_in_the_factory_backup(self):
        (self.folder / "full").mkdir()
        (self.folder / "full" / "x").write_text("x")
        with support.untouched_board():
            self.assertRegex(support.run_main("read-show", self.folder / "full").err, r"^error: output-not-empty: ")
            self.assertRegex(support.run_main("read-show", paths.PROTECTED / "show").err, r"^error: backup-protected: ")

    def test_only_the_newest_images_are_kept(self):
        (self.folder / "storage").mkdir()
        for number in range(12):
            (self.folder / "storage" / f"2026010{number:02d}-before.bin").write_bytes(bytes(8))
        waiting = storage.pending(bytes(8))
        self.assertNotIn(waiting, storage.kept_images(8))
        storage.keep(waiting, 8)
        self.assertEqual(len(list((self.folder / "storage").iterdir())), storage.KEPT_IMAGES)
        self.assertEqual(len(storage.kept_images(8)), storage.KEPT_IMAGES)
        self.assertTrue(storage.kept_images(8)[0].name.endswith("-after.bin"))

    def test_an_image_that_did_not_reach_the_board_is_not_kept_as_the_boards(self):
        serving = self.esptool()

        def refusing(arguments):
            if "write-flash" in arguments:
                return 2, "A fatal error occurred: the write failed"
            return serving(arguments)

        result = self.install(refusing)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"^error: esptool-failed: ")
        kept = sorted(path.name.split("-", 1)[1] for path in (self.folder / "storage").iterdir())
        self.assertEqual(kept, ["before.bin"])

    def test_a_new_image_that_the_board_does_not_hold_after_the_write_is_not_kept(self):
        self.install(self.esptool(failing_verifies=1))
        self.assertEqual([path.name.split("-", 1)[1] for path in storage.kept_images(len(self.old))], ["before.bin"])
        self.assertEqual(sorted(path.name for path in (self.folder / "storage").iterdir())[-1], "change.json")

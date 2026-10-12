import json
import unittest

from . import support
from .test_playback import T0, every_20_ms, playing, refreshes

BLOCK = support.STORAGE_BLOCK
BOARD = support.BOARD_STORAGE


def refused(code):
    return f'{{"ok":false,"error":"{code}"}}'


def replies(lines):
    return [line[len("reply "):] for line in lines if line.startswith("reply ")]


def invalid_show():
    files = support.example_show()
    del files["dvd.odrg"]
    return files


class Content(unittest.TestCase):
    def run_both(self, files, script, options=(), storage=BOARD):
        """Runs a script on the core, on a folder, and on the reference player, and
        compares every line. `storage` is what the reference player reports as the total,
        or None for a host that cannot tell."""
        printed = support.start(files, script, options).lines
        expected = support.ReferencePlayer(files, storage=storage).run(script)
        self.assertEqual(len(printed), len(expected))
        for number, (line, wanted) in enumerate(zip(printed, expected)):
            if line != wanted:
                self.fail(f"line {number} differs: the core printed {line[:120]}, the reference {wanted[:120]}")
        return printed

    def space(self, files, options=(), storage=BOARD):
        printed = self.run_both(files, [support.line(T0, "space")], options, storage)
        return json.loads(printed[0][len("reply "):])


class Space(Content):
    def test_it_reports_the_free_and_the_total_bytes_and_the_number_of_animations(self):
        files = support.example_show()
        self.assertEqual(sorted(files), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])
        self.assertTrue(all(len(content) <= BLOCK for content in files.values()))
        printed = self.run_both(files, [support.line(T0, "space")])
        self.assertEqual(printed, ['reply {"ok":true,"free":10338304,"total":10354688,"animations":2}'])
        self.assertEqual(BOARD - 4 * BLOCK, 10338304)

    def test_the_total_is_the_one_the_host_reports(self):
        files = support.example_show()
        for total in (0, 1, 4 * BLOCK - 1, 4 * BLOCK, 4 * BLOCK + 1, 1000000, 4294967295):
            with self.subTest(total=total):
                reply = self.space(files, ["--storage", str(total)], total)
                self.assertEqual(reply, {"ok": True, "free": max(0, total - 4 * BLOCK), "total": total, "animations": 2})

    def test_every_file_of_the_folder_takes_whole_blocks(self):
        for size, blocks in ((0, 0), (1, 1), (BLOCK - 1, 1), (BLOCK, 1), (BLOCK + 1, 2), (10 * BLOCK, 10), (10 * BLOCK + 1, 11)):
            with self.subTest(size=size):
                files = support.example_show()
                files["extra.odrg"] = bytes(size)
                reply = self.space(files)
                self.assertEqual(reply["free"], BOARD - (4 + blocks) * BLOCK)
                self.assertEqual(reply["animations"], 2)

    def test_the_files_held_in_memory_give_the_figures_of_a_folder(self):
        files = support.example_show()
        files["extra.odrg"] = bytes(3 * BLOCK + 5)
        script = [support.line(T0, "space")]
        in_memory = support.start_each([files, support.demo_show()], script)
        self.assertEqual(in_memory[0].lines, support.start(files, script).lines)
        self.assertEqual(json.loads(replies(in_memory[0].lines)[0])["free"], BOARD - 8 * BLOCK)
        self.assertEqual(in_memory[1].lines, support.ReferencePlayer(support.demo_show()).run(script))

    def test_the_animations_are_the_animation_items_and_not_the_cycles_or_the_files(self):
        clip = support.clip(3, 60, 6)
        cases = (
            ([{"id": 1, "file": "a.odrg"}], 1),
            ([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "a.odrg"}, {"id": 9, "file": "a.odrg"}], 3),
            ([{"id": 5, "file": "a.odrg"}, {"id": 6, "cycle": [5, 5], "seconds": 3}, {"id": 7, "cycle": [5], "seconds": 1}], 1),
            ([{"id": number, "file": "a.odrg"} for number in range(1, 41)] + [{"id": 100, "cycle": list(range(1, 41)), "seconds": 9}], 40),
        )
        for items, animations in cases:
            files = {"mapping.json": support.mapping_texts()["legs-2"], "show.json": support.show_text(items), "a.odrg": clip}
            self.assertEqual(self.space(files)["animations"], animations)

    def test_with_an_invalid_show_the_space_is_reported_and_the_animations_are_0(self):
        reply = self.space(invalid_show())
        self.assertEqual(reply, {"ok": True, "free": BOARD - 3 * BLOCK, "total": BOARD, "animations": 0})
        self.assertEqual(self.space({}), {"ok": True, "free": BOARD, "total": BOARD, "animations": 0})
        self.assertEqual(self.space({"mapping.json": "{"})["animations"], 0)
        no_show = support.example_show()
        del no_show["show.json"]
        self.assertEqual(self.space(no_show)["animations"], 0)

    def test_with_a_show_that_became_invalid_while_it_played_the_animations_are_0(self):
        files = playing(support.example_show(), 2)
        script = [support.line(T0, "space"), f"poll {T0}", f"poll {T0 + 20}", support.line(T0 + 30, "space"), support.line(T0 + 30, "status")]
        lines = support.start(files, script, ["--remove-after", "dvd.odrg", "1"]).lines
        first, second, status = (json.loads(reply) for reply in replies(lines))
        self.assertEqual((first["animations"], second["animations"]), (2, 0))
        self.assertEqual(status["error"], "file-missing dvd.odrg")
        self.assertEqual((second["free"], second["total"]), (first["free"], first["total"]))

    def test_space_with_any_argument_is_a_bad_argument(self):
        lines = ["space ", "space  ", "space 1", "space space", "space 0 0", "space a b c d e f g", "space" + " " * 2043]
        for options, storage in (((), BOARD), (("--space-unknown",), None), (("--no-storage",), None)):
            printed = self.run_both(support.example_show(), [support.line(T0, line) for line in lines], options, storage)
            self.assertEqual(replies(printed), [refused("bad-argument")] * len(lines))

    def test_other_spellings_are_unknown_commands(self):
        lines = ["Space", "SPACE", " space", "spaces", "spac", "space\t", "free"]
        printed = self.run_both(support.example_show(), [support.line(T0, line) for line in lines])
        self.assertEqual(replies(printed), [refused("unknown-command")] * len(lines))

    def test_a_host_that_cannot_tell_the_space_gives_storage_error(self):
        for files in (support.example_show(), invalid_show(), {}):
            printed = self.run_both(files, [support.line(T0, "space")], ["--space-unknown"], None)
            self.assertEqual(replies(printed), [refused("storage-error")])

    def test_a_host_without_storage_functions_gives_storage_error(self):
        printed = self.run_both(support.example_show(), [support.line(T0, "space"), support.fed(T0, b"space\r\n")], ["--no-storage"], None)
        self.assertEqual(replies(printed), [refused("storage-error")] * 2)

    def test_a_host_that_can_only_tell_its_space_answers(self):
        files = support.example_show()
        with_storage = support.start(files, [support.line(T0, "space")])
        only_space = support.start(files, [support.line(T0, "space")], ["--only-space"])
        self.assertEqual(only_space.lines, with_storage.lines)
        self.assertEqual(replies(only_space.lines), ['{"ok":true,"free":10338304,"total":10354688,"animations":2}'])

    def test_of_two_codes_that_apply_the_first_of_the_order_is_given(self):
        lines = {"space" + " " * 2044: "line-too-long", "spaces 1": "unknown-command", "space 1": "bad-argument", "space": "storage-error"}
        printed = self.run_both(support.example_show(), [support.line(T0, line) for line in lines], ["--space-unknown"], None)
        self.assertEqual(replies(printed), [refused(code) for code in lines.values()])

    def test_space_through_the_byte_entry(self):
        printed = self.run_both(support.example_show(), [support.fed(T0, b"spa"), support.fed(T0 + 1, b"ce\r\nspace\n")])
        self.assertEqual(printed[0], f"fed {b'space'.hex()}")
        self.assertEqual(replies(printed), ['{"ok":true,"free":10338304,"total":10354688,"animations":2}'] * 2)

    def test_space_changes_nothing_and_does_not_disturb_playback(self):
        files = playing(support.example_show(), 3)
        plain = every_20_ms(120) + [support.line(T0 + 2400, "status")]
        asked = []
        for number, line in enumerate(every_20_ms(120)):
            asked.append(line)
            if number % 7 == 3:
                asked.append(support.line(T0 + 20 * number + 5, "space"))
        asked.append(support.line(T0 + 2400, "status"))
        with_space = self.run_both(files, asked)
        without = self.run_both(files, plain)
        self.assertEqual([line for line in with_space if not line.startswith('reply {"ok":true,"free"')], without)
        self.assertEqual(len(refreshes([line for line in with_space if not line.startswith("reply")])[0]), 120)
        self.assertEqual(len({line for line in with_space if line.startswith('reply {"ok":true,"free"')}), 1)

    def test_space_makes_no_storage_call(self):
        run = support.start(support.example_show(), [support.line(T0, "space")] * 3, ["--trace-store"])
        self.assertEqual(run.stored, ())
        self.assertEqual(len(run.lines), 3)
        self.assertTrue(all(line.startswith("reply ") for line in run.lines))


class HostWithoutStorage(Content):
    def test_a_session_runs_as_ever_on_a_host_without_storage_functions(self):
        files = playing(support.example_show(), 3)
        script = every_20_ms(60) + [support.line(T0 + 1200, "play 2"), support.line(T0 + 1200, "status")] + every_20_ms(20, T0 + 1200)
        with_storage = support.start(files, script)
        for option in ("--no-storage", "--only-space"):
            without = support.start(files, script, [option])
            self.assertEqual(without.lines, with_storage.lines, option)
            self.assertEqual(without.memory, with_storage.memory, option)
            self.assertIsNone(without.error)


class StorageGuards(unittest.TestCase):
    GUARDS = ("write", "write-none", "close-none", "two-files", "name", "rename-open", "remove-open", "read-at", "read-at-offset")

    def test_each_misuse_of_the_storage_functions_stops_the_test_host(self):
        for what in self.GUARDS:
            with self.subTest(what=what):
                result = support.host("guard", what)
                self.assertEqual((result.status, result.out, result.err), (71, "file misuse\n", ""))

    def test_the_guards_are_the_ones_the_test_host_names(self):
        usage = support.host("guard", "no-such-guard")
        self.assertEqual(usage.status, 64)
        for what in self.GUARDS:
            self.assertRegex(usage.err, rf"[ |]{what}[ \n|]")

    def test_an_option_of_storage_without_a_whole_number_in_range_is_a_usage_error(self):
        for option in ("--storage", "--store-fails-at", "--cut-at", "--cut-keeps"):
            self.assertEqual(support.host("session", "/nonexistent", option).status, 64, option)
        for value in ("-1", "4294967296", "1e3", "", "12 "):
            self.assertEqual(support.host("session", "/nonexistent", "--storage", value).status, 64, value)


if __name__ == "__main__":
    unittest.main()

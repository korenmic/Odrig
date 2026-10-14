import json
import random
import unittest
import zlib

from odrig import odrg

from . import support
from .test_session import scripted_session


def two_leg_show():
    """The example show: two legs, two animations and a cycle."""
    return support.example_show()


class Guard(unittest.TestCase):
    def test_memory_asked_of_the_host_after_startup_stops_the_program(self):
        result = support.host("guard", "alloc")
        self.assertEqual(result.status, 70)
        self.assertEqual(result.out, "allocation after startup\n")
        self.assertEqual(result.err, "")

    def test_memory_asked_of_the_program_after_startup_stops_the_program(self):
        result = support.host("guard", "new")
        self.assertEqual(result.status, 70)
        self.assertEqual(result.out, "allocation after startup\n")
        self.assertEqual(result.err, "")

    def test_a_session_runs_under_the_guard_and_ends_well(self):
        run = support.start(two_leg_show(), ["error", "error"])
        self.assertEqual(run.status, 0)
        self.assertEqual(len(run.lines), 2)


class MemoryTheHostCannotSupply(unittest.TestCase):
    def test_without_the_first_block_there_is_no_core(self):
        run = support.start(two_leg_show(), ["error"], ["--alloc-fails-at", "1"])
        self.assertEqual(run.core, "null")
        self.assertEqual(run.lines, [])
        self.assertIsNone(run.memory)

    def test_without_any_later_block_the_show_is_invalid_with_out_of_memory(self):
        plain = support.start(two_leg_show(), ["error"])
        blocks = plain.memory[1]
        self.assertEqual(blocks, 16)
        for number in range(2, blocks + 1):
            with self.subTest(block=number):
                run = support.start(two_leg_show(), ["error"], ["--alloc-fails-at", str(number)])
                self.assertEqual(run.core, "ok")
                self.assertEqual(run.error, "out-of-memory")
                self.assertEqual(run.logs, ("out-of-memory",))
                self.assertEqual(run.lines, ["error out-of-memory"])
                self.assertIn(run.legs, ((), plain.legs))
                self.assertLess(run.memory[0], plain.memory[0])

    def test_a_block_that_is_never_asked_for_cannot_fail(self):
        plain = support.start(two_leg_show(), ["error"])
        run = support.start(two_leg_show(), ["error"], ["--alloc-fails-at", str(plain.memory[1] + 1)])
        self.assertEqual(run, plain)

    def test_memory_that_fails_before_the_mapping_is_set_up_leaves_no_legs(self):
        for number in (2, 3, 4, 5, 6, 7):
            run = support.start(two_leg_show(), options=["--alloc-fails-at", str(number)])
            self.assertEqual((run.error, run.legs), ("out-of-memory", ()))

    def test_memory_that_fails_after_the_mapping_is_set_up_leaves_the_legs(self):
        for number in (8, 9, 10, 11, 12, 13, 14, 15, 16):
            run = support.start(two_leg_show(), options=["--alloc-fails-at", str(number)])
            self.assertEqual((run.error, run.legs), ("out-of-memory", ((1, 1, 180), (2, 2, 180))))

    def test_without_the_blocks_of_the_byte_entry_bytes_get_no_reply_and_a_line_gets_one(self):
        script = [support.fed(5, b"status\n"), support.fed(6, b"x" * 3000 + b"\non\n"), support.line(7, "status"), support.line(8, "play 1"), support.fed(9, b"off\n"), support.line(10, "status")]
        for number in (2, 3):
            run = support.start(two_leg_show(), script, ["--alloc-fails-at", str(number)])
            self.assertEqual(run.error, "out-of-memory")
            self.assertEqual(len(run.lines), 3)
            first, play, last = (json.loads(line[len("reply "):]) for line in run.lines)
            self.assertEqual((first["error"], first["on"], first["playing"]), ("out-of-memory", True, None))
            self.assertEqual(play, {"ok": False, "error": "show-invalid"})
            self.assertEqual(last, first)


def hundred_items():
    """A show of 100 items on the target file: 80 animations, each with a file of its own,
    and 20 cycles of 10 entries."""
    clip = support.clip(1, 60, 60, (20, 20))
    items = [{"id": number, "file": f"clip-{number:02d}.odrg"} for number in range(1, 81)]
    items += [{"id": 80 + number, "cycle": [1 + (7 * number + entry) % 80 for entry in range(10)], "seconds": number} for number in range(1, 21)]
    files = {"mapping.json": support.mapping_texts()["legs-20"], "show.json": support.show_text(items, 128, 100)}
    files.update({item["file"]: clip for item in items[:80]})
    return files


def stored_clip(frames, compressed):
    """An ODRG file for the 60 x 60 canvas with this many frames of 20 ms, each stored."""
    rng = random.Random(4)
    palette = [rng.randbytes(3) for _ in range(9)]
    pictures = [bytes(rng.randrange(9) for _ in range(3600)) for _ in range(8)]
    records = [odrg.stored_record(pictures[number % 8], 20) for number in range(frames)]
    deflate = (lambda body: zlib.compress(body, 6, wbits=-15)) if compressed else None
    return odrg.container(60, 60, palette, records, deflate)


class FixedMemory(unittest.TestCase):
    def test_the_target_file_with_a_show_of_100_items_asks_for_less_than_131072_bytes(self):
        files = hundred_items()
        listed = json.loads(files["show.json"])["items"]
        self.assertEqual(len(listed), 100)
        self.assertEqual(len({item["file"] for item in listed if "file" in item}), 80)
        self.assertEqual([len(item["cycle"]) for item in listed if "cycle" in item], [10] * 20)
        run = support.start(files, [support.line(0, "status")])
        self.assertIsNone(run.error)
        self.assertEqual(run.legs, tuple((number, pin, 180) for number, pin in enumerate((*range(1, 19), 21, 47), start=1)))
        asked, blocks = run.memory
        self.assertLess(asked, 131072)
        self.assertEqual(blocks, 16)
        # Every block but the core object and the decoders of the check has a size that is
        # fixed or follows from the mapping and the show: the line and the reply of the
        # byte entry, legs, the pixel of each LED, LED data, strip check, pixel buffer,
        # window, the chunk buffer, the pixel buffer and the window of the check, and the
        # tables of items, cycle entries and files, the first and the last with room for
        # 32 items more than the 100 of the show.
        tables = 2049 + 1024 + 20 * 12 + 3600 * 2 + 3600 * 3 + 8 + 10800 + 32768 + 1500 + 10800 + 32768 + 132 * 16 + 200 * 2 + 132 * 48
        self.assertEqual(tables, 118805)
        # What the compiler settles: the core object, at most 4,096 bytes, and the second
        # source and decoders, about 2,500.
        settled = asked - tables
        self.assertGreater(settled, 4000)
        self.assertLessEqual(settled, 4096 + 2600)

    def test_a_host_without_storage_is_asked_for_four_blocks_fewer(self):
        files = hundred_items()
        with_storage = support.start(files).memory
        for option in ("--no-storage", "--only-space"):
            without = support.start(files, options=[option]).memory
            self.assertEqual(without[1], 12)
            self.assertEqual(with_storage[1] - without[1], 4)
            saved = with_storage[0] - without[0]
            self.assertGreater(saved, 1500 + 10800 + 32768 + 2000)
            self.assertLess(saved, 1500 + 10800 + 32768 + 3000)

    def test_a_session_of_content_commands_asks_for_no_memory(self):
        # The test host stops a run in which the core asks for memory after its start,
        # from the host or from the program.
        files = hundred_items()
        script = [support.line(0, "space"), support.line(0, "list")]
        for number in (100, 81, 50, 1, 99, 100, 7, 83, 3):
            script += [support.line(0, f"remove {number}"), support.line(0, f"list {number % 60}"), "poll 0", support.line(0, "space")]
        with support.installed(files) as folder:
            run = support.session(folder, script)
        self.assertEqual(run.status, 0)
        codes = [json.loads(line[len("reply "):]).get("error") for line in run.lines if line.startswith("reply")]
        self.assertEqual(set(codes), {None, "unknown-id", "in-use"})
        self.assertEqual(run.memory, support.start(files).memory)

    def test_the_check_after_the_start_and_playing_before_it_ask_for_no_memory(self):
        # The test host stops a run in which the core asks for memory after its start.
        files = hundred_items()
        in_step = [f"poll {20 * step}" for step in range(40)] + [support.line(800, "status")]
        apart = [f"poll {1000 * step}" for step in range(200)] + [support.line(200000, "status")]
        for script in (in_step, apart):
            run = support.start(files, script, check_first=False)
            self.assertEqual(run.status, 0)
            self.assertIn('"error":null', run.lines[-1])
            self.assertEqual(run.memory, support.start(files).memory)

    def test_the_memory_does_not_depend_on_the_length_of_a_clip(self):
        sizes = {}
        memory = set()
        for frames in (50, 3000):
            for compressed in (False, True):
                clip = stored_clip(frames, compressed)
                files = {
                    "mapping.json": support.mapping_texts()["legs-20"],
                    "show.json": support.show_text([{"id": 1, "file": "clip.odrg"}], 255, 1),
                    "clip.odrg": clip,
                }
                # The whole clip is played, and a loop more.
                script = [f"poll {time}" for time in range(0, 40 * frames, 500)] + [support.line(40 * frames, "status")]
                run = support.start(files, script)
                self.assertIsNone(run.error)
                self.assertIn('"playing":"all","animation":1', run.lines[-1])
                self.assertIn('"error":null', run.lines[-1])
                sizes[frames, compressed] = len(clip)
                memory.add(run.memory)
        # A clip of 1 second and one of 60 seconds: 180 KB and 10.8 MB without compression.
        self.assertLess(sizes[50, False], 200000)
        self.assertGreater(sizes[3000, False], 10000000)
        self.assertLess(sizes[3000, True], sizes[3000, False] // 50)
        self.assertEqual(len(memory), 1)

    def test_no_read_asks_for_more_than_512_bytes(self):
        # The test host stops when it is asked for more, and every session of the suite,
        # among them one over a file of several megabytes, runs on it without stopping.
        result = support.host("guard", "read")
        self.assertEqual(result.status, 71)
        self.assertEqual(result.out, "file misuse\n")
        with support.installed(hundred_items()) as folder:
            self.assertEqual(support.session(folder, ["poll 0"]).status, 0)


class RepeatableOutput(unittest.TestCase):
    def output(self, options=()):
        script = scripted_session()[:1200]
        with support.installed(support.example_show()) as folder:
            result = support.host("session", folder, *options, stdin="".join(f"{line}\n" for line in script).encode("ascii"))
        self.assertEqual((result.status, result.err), (0, ""))
        return result.out

    def test_one_session_run_twice_prints_identical_output(self):
        first = self.output()
        self.assertGreater(first.count("\n"), 3000)
        self.assertIn("reply ", first)
        self.assertEqual(self.output(), first)

    def test_memory_filled_with_the_byte_a5_gives_the_output_of_zeroed_memory(self):
        self.assertEqual(self.output(["--dirty-memory"]), self.output())

    def test_an_invalid_show_on_dirty_memory_gives_the_output_of_zeroed_memory(self):
        for files in ({}, {"mapping.json": support.mapping_texts()["legs-2"]}, {"mapping.json": "{}"}):
            script = [support.line(5, "status"), "poll 5", "poll 25", "error"]
            self.assertEqual(support.start(files, script, ["--dirty-memory"]), support.start(files, script))


if __name__ == "__main__":
    unittest.main()

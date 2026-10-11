import unittest

from . import support


def two_leg_show():
    """The smallest installed file set this file needs: the two-leg mapping."""
    return {"mapping.json": support.mapping_texts()["legs-2"]}


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
        self.assertGreaterEqual(blocks, 7)
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

    def test_memory_that_fails_while_the_mapping_is_set_up_leaves_no_legs(self):
        for number in (2, 3, 4, 5):
            run = support.start(two_leg_show(), options=["--alloc-fails-at", str(number)])
            self.assertEqual((run.error, run.legs), ("out-of-memory", ()))

    def test_memory_that_fails_after_the_mapping_is_set_up_leaves_the_legs(self):
        for number in (6, 7):
            run = support.start(two_leg_show(), options=["--alloc-fails-at", str(number)])
            self.assertEqual((run.error, run.legs), ("out-of-memory", ((1, 1, 180), (2, 2, 180))))


if __name__ == "__main__":
    unittest.main()

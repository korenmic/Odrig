import json
import unittest

from . import huge_tail, support
from .test_playback import T0

# What one call of the core may read of files while it settles the reproducer: a few of
# the host's reads, never the whole file.
MOST_BYTES_IN_A_CALL = 4096


def show_of_the_reproducer():
    data = huge_tail.huge_tail()
    show = {"version": 1, "brightness": 128, "items": [{"id": 1, "file": "huge.odrg"}]}
    return {"mapping.json": support.one_leg_mapping(huge_tail.WIDTH, huge_tail.HEIGHT), "huge.odrg": data, "show.json": json.dumps(show)}, data


def calls(printed):
    """What each traced call read of files, in bytes."""
    return [int(line.split()[1]) for line in printed if line.startswith("call ")]


class TheReproducer(unittest.TestCase):
    @unittest.expectedFailure
    def test_no_call_of_the_core_reads_the_whole_reproducer(self):
        files, data = show_of_the_reproducer()
        script = [f"poll {T0 + 20 * step}" for step in range(40)]
        run = support.start(files, script, options=["--trace-calls"], check_first=False)
        read = calls(run.lines)
        self.assertEqual(len(read), 40)
        self.assertLessEqual(max(read), MOST_BYTES_IN_A_CALL, f"the most one call read: {max(read)} of {len(data)} bytes")


if __name__ == "__main__":
    unittest.main()

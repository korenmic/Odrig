import json
import unittest

from . import support
from .test_body_faults import cut_clip
from .test_playback import T0

# A canvas of 3 x 2, on which cut_clip makes its files.
WIDTH, HEIGHT = 3, 2


def good(seed):
    return support.clip(seed, WIDTH, HEIGHT, (20,) * 5)


def bad_files():
    """The ways the second animation of a show can be bad: a body cut short, a header that
    is not one, and a file that is not there."""
    return {
        "a body cut short": (cut_clip(10, 3), "truncated"),
        "a bad header": (b"ODRX" + good(2)[4:], "bad-magic"),
        "no file": (None, "file-missing"),
    }


def show_with_a_bad_second(data):
    """Three animations, ids 1 to 3, whose second is `data`, or missing when it is None."""
    files = {
        "mapping.json": support.one_leg_mapping(WIDTH, HEIGHT),
        "show.json": support.show_text([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "file": "c.odrg"}]),
        "a.odrg": good(1),
        "c.odrg": good(3),
    }
    if data is not None:
        files["b.odrg"] = data
    return files


def replies(run):
    return [json.loads(line[len("reply "):]) for line in run.lines if line.startswith("reply ")]


class OneBadFileEndsTheShow(unittest.TestCase):
    """What a bad animation did to the whole show before it was quarantined."""

    def session(self, data):
        script = [f"poll {T0 + 20 * step}" for step in range(20)]
        script += [support.line(T0 + 400, command) for command in ("status", "list", "remove 3", "status")]
        return support.start(show_with_a_bad_second(data), script)

    @unittest.expectedFailure
    def test_the_show_stays_valid_and_plays_the_others(self):
        for name, (data, _) in bad_files().items():
            with self.subTest(name):
                state = replies(self.session(data))[0]
                self.assertEqual((state["error"], state["playing"]), (None, "all"))
                self.assertIn(state["animation"], (1, 3))

    @unittest.expectedFailure
    def test_list_and_remove_are_answered(self):
        for name, (data, reason) in bad_files().items():
            with self.subTest(name):
                listed, removed = replies(self.session(data))[1:3]
                self.assertEqual([item["id"] for item in listed["items"]], [1, 2, 3])
                self.assertEqual(listed["items"][1]["fault"], reason)
                self.assertEqual(removed, {"ok": True})


if __name__ == "__main__":
    unittest.main()

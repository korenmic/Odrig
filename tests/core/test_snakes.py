import json
import subprocess
import sys
import unittest
import zlib

from . import support
from .test_playback import T0, refreshes

PINS = list(range(1, 19)) + [21, 47]
REVISION = zlib.crc32(bytes(PINS))


def answers(run):
    return [json.loads(line[len("reply "):]) for line in run.lines if line.startswith("reply ")]


def files():
    """The demo show on the target file, at brightness 32."""
    result = support.demo_show()
    show = json.loads(result["show.json"])
    show["brightness"] = 32
    result["show.json"] = json.dumps(show).encode()
    return result


def lit(leg, led):
    """The column and the row, from 1, of the pixel of an LED of a leg of the target file:
    each snake starts at the bottom of its first column and runs up, down, up."""
    column = (leg - 1) * 3 + led // 60 + 1
    row = led % 60 + 1 if led // 60 != 1 else 60 - led % 60
    return column, row


def snake_pixel(snake, column, row):
    """Whether the test of a snake lights the pixel at this column and row."""
    return column == 3 * snake - 2 + (row - 1) // 20


def pictures(run):
    produced, _ = refreshes([line for line in run.lines if line.startswith(("refresh ", "data ", "idle "))])
    return [legs for _, legs in produced]


class TheSnakeTests(unittest.TestCase):
    def assert_snake(self, legs, snake, level=32):
        self.assertEqual(len(legs), 20)
        count = 0
        for leg, data in legs.items():
            for led in range(180):
                column, row = lit(leg, led)
                want = level if snake_pixel(snake, column, row) else 0
                count += want != 0
                self.assertEqual(data[led * 3:led * 3 + 3], bytes([want]) * 3, (snake, leg, led))
        self.assertEqual(count, 60)

    def test_each_snake_shows_its_own_diagonal_across_its_three_columns_and_nothing_else(self):
        script = []
        for snake in range(1, 21):
            script += [support.line(T0 + 40 * snake, f"mapping test snake {snake}"), f"poll {T0 + 40 * snake + 20}"]
        run = support.start(files(), [f"poll {T0}"] + script)
        self.assertEqual(answers(run), [{"ok": True}] * 20)
        shown = pictures(run)[1:]
        self.assertEqual(len(shown), 20)
        for snake, legs in enumerate(shown, start=1):
            with self.subTest(snake=snake):
                self.assert_snake(legs, snake)

    def test_the_test_follows_the_saved_mapping(self):
        swapped = PINS.copy()
        swapped[0], swapped[19] = swapped[19], swapped[0]
        line = f"mapping set {REVISION} " + ",".join(map(str, swapped))
        run = support.start(files(), [f"poll {T0}", support.line(T0 + 1, line), support.line(T0 + 2, "mapping test snake 1"), f"poll {T0 + 20}", support.line(T0 + 21, "mapping get")])
        self.assertEqual(answers(run)[:2], [{"ok": True}, {"ok": True}])
        self.assertEqual(answers(run)[2]["pins"], swapped)
        self.assert_snake(pictures(run)[1], 1)

    def test_mapping_get_says_which_test_shows(self):
        script = [support.line(T0, "mapping get"), support.line(T0 + 1, "mapping test on"), support.line(T0 + 2, "mapping get"), support.line(T0 + 3, "mapping test snake 7"),
                  support.line(T0 + 4, "mapping get"), support.line(T0 + 5, "mapping test snake 7"), support.line(T0 + 6, "mapping test off"), support.line(T0 + 7, "mapping get")]
        found = [(reply["test"], reply["snake"]) for reply in answers(support.start(files(), script)) if "test" in reply]
        self.assertEqual(found, [(False, None), (True, None), (True, 7), (False, None)])

    def test_switching_tests_keeps_what_played_before_the_first_and_stopping_resumes_it(self):
        script = [f"poll {T0}", support.line(T0 + 1, "play 2"), f"poll {T0 + 20}", support.line(T0 + 21, "mapping test snake 3"), f"poll {T0 + 40}",
                  support.line(T0 + 41, "mapping test on"), support.line(T0 + 42, "mapping test snake 5"), support.line(T0 + 43, "status"), f"poll {T0 + 62000}",
                  support.line(T0 + 62001, "status"), support.line(T0 + 62002, "mapping test off"), f"poll {T0 + 62020}", support.line(T0 + 62021, "status")]
        replies = answers(support.start(files(), script))
        states = [(reply["playing"], reply["animation"]) for reply in replies if "on" in reply]
        self.assertEqual(states, [(None, None), (None, None), ("all", 2)])

    def test_play_ends_a_test_and_a_restart_shows_none(self):
        run, left = support.start_and_keep(files(), [support.line(T0, "mapping test snake 9"), support.line(T0 + 1, "play 1"), f"poll {T0 + 20}", support.line(T0 + 21, "mapping get"), support.line(T0 + 22, "status")])
        replies = answers(run)
        self.assertEqual((replies[2]["test"], replies[2]["snake"]), (False, None))
        self.assertEqual(replies[3]["animation"], 1)
        again = answers(support.start(left, [support.line(T0, "mapping get")]))[0]
        self.assertEqual((again["test"], again["snake"]), (False, None))

    def test_power_and_brightness_stay_under_their_controls(self):
        script = [f"poll {T0}", support.line(T0 + 1, "mapping test snake 2"), support.line(T0 + 2, "brightness 7"), f"poll {T0 + 20}", support.line(T0 + 21, "off"), f"poll {T0 + 40}"]
        shown = pictures(support.start(files(), script))
        self.assert_snake(shown[1], 2, level=(255 * 7 + 127) // 255)
        self.assertTrue(all(not any(data) for data in shown[2].values()))

    def test_while_a_test_shows_uploads_and_removals_are_busy_and_no_file_changes(self):
        source = files()
        script = [support.line(T0, "mapping test snake 4"), support.line(T0 + 1, "upload begin 99 new.odrg 100"), support.line(T0 + 2, "remove 1"), support.line(T0 + 3, "remove many 1"),
                  support.line(T0 + 4, "ignore 1 1"), support.line(T0 + 5, "list"), support.line(T0 + 6, "order get")]
        run, left = support.start_and_keep(source, script)
        replies = answers(run)
        self.assertEqual(replies[1:5], [{"ok": False, "error": "busy"}] * 4)
        self.assertEqual([item["id"] for item in replies[5]["items"]], [1, 2])
        self.assertEqual(replies[6]["ids"], [1, 2])
        self.assertEqual(left, source)

    def test_its_entry_is_refused_as_the_diagonals_is(self):
        run = support.start(support.example_show(), [support.line(T0, "mapping test snake 1")])
        self.assertEqual(answers(run), [{"ok": False, "error": "bad-argument"}])
        run = support.start(files(), [support.line(T0, "mapping test snake 1")], check_first=False)
        self.assertEqual(answers(run), [{"ok": False, "error": "busy"}])
        upload = support.start(files(), [support.line(T0, "upload begin 99 new.odrg 100"), support.line(T0 + 1, "mapping test snake 1")])
        self.assertEqual(answers(upload)[1], {"ok": False, "error": "busy"})
        broken = {**files(), "dvd.odrg": b"nothing"}
        run = support.start(broken, [support.line(T0, "mapping test snake 1")])
        self.assertEqual(answers(run), [{"ok": False, "error": "show-invalid"}])

    def test_malformed_words_are_bad_arguments_and_change_nothing(self):
        lines = ["mapping test snake", "mapping test snake 0", "mapping test snake 21", "mapping test snake x", "mapping test snake 1 2", "mapping test snakes 1", "mapping test snake 01x"]
        run, left = support.start_and_keep(files(), [support.line(T0, line) for line in lines] + [support.line(T0 + 1, "mapping get")])
        self.assertEqual(answers(run)[:-1], [{"ok": False, "error": "bad-argument"}] * len(lines))
        self.assertFalse(answers(run)[-1]["test"])
        self.assertEqual(left, files())

    def test_the_embedded_pictures_are_the_converters_output_of_their_tracked_source(self):
        done = subprocess.run([sys.executable, str(support.ROOT / "core" / "snakes.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        source = json.loads((support.ROOT / "core" / "assets" / "mapping-snakes.json").read_text())
        self.assertEqual((source["width"], source["height"], len(source["frames"])), (60, 60, 20))
        for snake, frame in enumerate(source["frames"], start=1):
            white = [(at % 60 + 1, at // 60 + 1) for at, colour in enumerate(frame["pixels"]) if colour != 0]
            self.assertEqual(sorted(white), sorted((3 * snake - 2 + (row - 1) // 20, row) for row in range(1, 61)))


if __name__ == "__main__":
    unittest.main()

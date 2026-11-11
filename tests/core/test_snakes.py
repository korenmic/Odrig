import json
import unittest
import zlib

from . import support
from .test_playback import T0, refreshes

PINS = list(range(1, 19)) + [21, 47]
REVISION = zlib.crc32(bytes(PINS))
# The test's block: 3 x 3 pixels, up one row every 40 ms from the bottom row to the top,
# 57 rows, and back.
BLOCK = 3
STEP_MS = 40
TRAVEL = 60 - BLOCK


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


def block_at(ms):
    """The lowest row of the block, from 0, `ms` after the first poll."""
    phase = (ms // STEP_MS) % (2 * TRAVEL)
    return phase if phase <= TRAVEL else 2 * TRAVEL - phase


def snake_pixel(snake, at, column, row):
    """Whether the test of a snake, with its block's lowest row at `at`, lights the pixel at
    this column and row, from 1."""
    return 3 * snake - 2 <= column <= 3 * snake and at + 1 <= row <= at + BLOCK


def pictures(run):
    produced, _ = refreshes([line for line in run.lines if line.startswith(("refresh ", "data ", "idle "))])
    return [legs for _, legs in produced]


class TheSnakeTests(unittest.TestCase):
    def assert_snake(self, legs, snake, ms, level=32):
        """The picture of a poll `ms` after the first: the block of the snake's test at the
        place of that time, white at the level, and every other LED dark."""
        self.assertEqual(len(legs), 20)
        at = block_at(ms)
        count = 0
        for leg, data in legs.items():
            for led in range(180):
                column, row = lit(leg, led)
                want = level if snake_pixel(snake, at, column, row) else 0
                count += want != 0
                self.assertEqual(data[led * 3:led * 3 + 3], bytes([want]) * 3, (snake, leg, led, at))
        self.assertEqual(count, BLOCK * BLOCK)

    def test_each_snake_shows_its_own_block_in_its_three_columns_and_nothing_else(self):
        script = []
        for snake in range(1, 21):
            script += [support.line(T0 + 40 * snake, f"mapping test snake {snake}"), f"poll {T0 + 40 * snake + 20}"]
        run = support.start(files(), [f"poll {T0}"] + script)
        self.assertEqual(answers(run), [{"ok": True}] * 20)
        shown = pictures(run)[1:]
        self.assertEqual(len(shown), 20)
        for snake, legs in enumerate(shown, start=1):
            with self.subTest(snake=snake):
                self.assert_snake(legs, snake, 40 * snake + 20)

    def test_the_block_runs_from_the_bottom_of_the_snake_to_its_top_and_back_and_lights_every_led_of_it(self):
        # Polls at the grid's pace through one way up and down, 4,560 ms, and one more.
        polls = 2 * TRAVEL * STEP_MS // 20 + 1
        script = [f"poll {T0}", support.line(T0 + 1, "mapping test snake 5")] + [f"poll {T0 + 20 * k}" for k in range(1, polls + 1)]
        run = support.start(files(), script)
        shown = pictures(run)[1:]
        self.assertEqual(len(shown), polls)
        places = []
        lit_ever = set()
        for k, legs in enumerate(shown, start=1):
            self.assert_snake(legs, 5, 20 * k)
            places.append(block_at(20 * k))
            lit_ever |= {(leg, led) for leg, data in legs.items() for led in range(180) if any(data[led * 3:led * 3 + 3])}
        # One row at a time, every place from the bottom to the top, the top once in a way,
        # and back to the bottom; every LED of the snake lit at some time, and no other LED.
        self.assertTrue(all(abs(after - before) <= 1 for before, after in zip(places, places[1:])))
        self.assertEqual((places[0], min(places), max(places), places.index(TRAVEL), places[-1]), (0, 0, TRAVEL, 2 * TRAVEL - 1, 0))
        # The top is reached once in a way: two polls fall into each 40 ms place.
        self.assertEqual(sum(1 for before, after in zip([None] + places, places) if after == TRAVEL and before != TRAVEL), 1)
        self.assertEqual(lit_ever, {(5, led) for led in range(180)})

    def test_the_test_follows_the_saved_mapping(self):
        swapped = PINS.copy()
        swapped[0], swapped[19] = swapped[19], swapped[0]
        line = f"mapping set {REVISION} " + ",".join(map(str, swapped))
        run = support.start(files(), [f"poll {T0}", support.line(T0 + 1, line), support.line(T0 + 2, "mapping test snake 1"), f"poll {T0 + 20}", support.line(T0 + 21, "mapping get")])
        self.assertEqual(answers(run)[:2], [{"ok": True}, {"ok": True}])
        self.assertEqual(answers(run)[2]["pins"], swapped)
        self.assert_snake(pictures(run)[1], 1, 20)

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
        self.assert_snake(shown[1], 2, 20, level=(255 * 7 + 127) // 255)
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
        broken = {**files(), "show.json": "{"}
        run = support.start(broken, [support.line(T0, "mapping test snake 1")])
        self.assertEqual(answers(run), [{"ok": False, "error": "show-invalid"}])

    def test_malformed_words_are_bad_arguments_and_change_nothing(self):
        lines = ["mapping test snake", "mapping test snake 0", "mapping test snake 21", "mapping test snake x", "mapping test snake 1 2", "mapping test snakes 1", "mapping test snake 01x"]
        run, left = support.start_and_keep(files(), [support.line(T0, line) for line in lines] + [support.line(T0 + 1, "mapping get")])
        self.assertEqual(answers(run)[:-1], [{"ok": False, "error": "bad-argument"}] * len(lines))
        self.assertFalse(answers(run)[-1]["test"])
        self.assertEqual(left, files())


def swapped_pins():
    pins = PINS.copy()
    pins[0], pins[19] = pins[19], pins[0]
    return pins


def mapping_save(pins):
    return f"mapping set {REVISION} " + ",".join(map(str, pins))


class TestsWheneverPlayDoes(unittest.TestCase):
    """A test starts while the check after the start goes on and while an upload is open,
    as an animation does; the upload goes on to its end under the test."""

    assert_snake = TheSnakeTests.assert_snake

    def upload_under_a_test(self, number, name, data, before, test):
        """The lines that play `before`, open an upload, start a test, send the rest of the
        upload and poll until its check is done, then end it; the time after the end."""
        begin, *pieces = support.upload_lines(number, name, data)
        script = [f"poll {T0}"]
        if before is not None:
            script.append(support.line(T0 + 1, f"play {before}"))
        script += [f"poll {T0 + 20}", support.line(T0 + 21, begin), support.line(T0 + 22, test)]
        script += [support.line(T0 + 23, piece) for piece in pieces]
        script += [f"poll {T0 + 20 * k}" for k in range(2, 101)]
        script.append(support.line(T0 + 2001, support.upload_end(data)))
        return script, len(pieces)

    def test_a_test_and_a_mapping_save_are_taken_while_the_check_after_the_start_goes_on(self):
        swapped = swapped_pins()
        script = [f"poll {T0}", support.line(T0 + 1, "status"), support.line(T0 + 2, "mapping test on"), support.line(T0 + 3, "mapping test snake 6"),
                  support.line(T0 + 4, mapping_save(swapped))]
        script += [f"poll {T0 + 20 * k}" for k in range(1, 501)]
        script += [support.line(T0 + 10001, "status"), support.line(T0 + 10002, "mapping get")]
        run = support.start(files(), script, check_first=False)
        replies = answers(run)
        self.assertEqual((replies[0]["readiness"], replies[0]["to_check"] > 0), ("checking", True))
        self.assertEqual(replies[1:4], [{"ok": True}] * 3)
        after, mapping = replies[4:]
        self.assertNotEqual(after["readiness"], "checking")
        self.assertEqual((after["to_check"], after["playing"], after["animation"]), (0, None, None))
        self.assertEqual((mapping["test"], mapping["snake"], mapping["pins"]), (True, 6, swapped))
        self.assert_snake(pictures(run)[-1], 6, 20 * 500)

    def test_an_upload_open_when_a_test_starts_ends_under_it_and_the_tests_end_resumes_what_played(self):
        data = support.clip(11, 60, 60, (20, 20, 20))
        script, pieces = self.upload_under_a_test(3, "new.odrg", data, 2, "mapping test snake 4")
        script += [f"poll {T0 + 2020}", support.line(T0 + 2021, "status"), support.line(T0 + 2022, "list"), support.line(T0 + 2023, "mapping test off"),
                   f"poll {T0 + 2040}", support.line(T0 + 2041, "status")]
        run, left = support.start_and_keep(files(), script)
        replies = answers(run)
        self.assertEqual(replies[0], {"ok": True})
        self.assertEqual(replies[2], {"ok": True})
        self.assertTrue(all(reply["ok"] for reply in replies[3:3 + pieces]), replies[3:3 + pieces])
        self.assertEqual(replies[3 + pieces], {"ok": True})
        during, listed, stopped, after = replies[4 + pieces:]
        self.assertEqual((during["playing"], during["animation"]), (None, None))
        self.assertEqual([item["id"] for item in listed["items"]], [1, 2, 3])
        self.assertEqual(stopped, {"ok": True})
        self.assertEqual((after["playing"], after["animation"]), ("all", 2))
        self.assertEqual(left["new.odrg"], data)
        self.assert_snake(pictures(run)[-2], 4, 2020)

    def test_an_upload_under_a_test_that_replaces_the_animation_that_played_plays_it_at_the_tests_end(self):
        data = support.clip(12, 60, 60, (20, 20))
        script, pieces = self.upload_under_a_test(2, "dvd.odrg", data, 2, "mapping test on")
        script += [f"poll {T0 + 2020}", support.line(T0 + 2021, "status"), support.line(T0 + 2022, "mapping test off"), f"poll {T0 + 2040}", support.line(T0 + 2041, "status")]
        run, left = support.start_and_keep(files(), script)
        replies = answers(run)
        self.assertEqual(replies[3 + pieces], {"ok": True})
        during, _, after = replies[4 + pieces:]
        self.assertEqual((during["playing"], during["animation"]), (None, None))
        self.assertEqual((after["playing"], after["animation"]), ("all", 2))
        self.assertEqual(left["dvd.odrg"], data)

    def test_when_nothing_played_the_first_animation_uploaded_under_a_test_plays_at_its_end(self):
        empty = {"mapping.json": files()["mapping.json"], "show.json": support.show_text([], brightness=32)}
        data = support.clip(13, 60, 60, (20, 20))
        script, pieces = self.upload_under_a_test(1, "first.odrg", data, None, "mapping test snake 1")
        script += [f"poll {T0 + 2020}", support.line(T0 + 2021, "status"), support.line(T0 + 2022, "mapping test off"), f"poll {T0 + 2040}", support.line(T0 + 2041, "status")]
        run = support.start(empty, script)
        replies = answers(run)
        self.assertEqual(replies[1], {"ok": True})
        self.assertEqual(replies[2 + pieces], {"ok": True})
        during, _, after = replies[3 + pieces:]
        self.assertEqual((during["playing"], during["animation"]), (None, None))
        self.assertEqual((after["playing"], after["animation"]), ("all", 1))
        self.assert_snake(pictures(run)[-2], 1, 2020)

    def test_an_upload_cancelled_under_a_test_changes_nothing_and_the_test_shows_on(self):
        source = files()
        data = support.clip(14, 60, 60, (20, 20))
        begin, first, *_ = support.upload_lines(3, "new.odrg", data)
        script = [f"poll {T0}", support.line(T0 + 1, begin), support.line(T0 + 2, "mapping test snake 2"), support.line(T0 + 3, first), support.line(T0 + 4, "upload cancel"),
                  f"poll {T0 + 20}", support.line(T0 + 21, "mapping get"), support.line(T0 + 22, "list")]
        run, left = support.start_and_keep(source, script)
        replies = answers(run)
        self.assertEqual((replies[1], replies[2]["ok"], replies[3]), ({"ok": True}, True, {"ok": True}))
        self.assertEqual((replies[4]["test"], replies[4]["snake"]), (True, 2))
        self.assertEqual([item["id"] for item in replies[5]["items"]], [1, 2])
        self.assertEqual(left, source)
        self.assert_snake(pictures(run)[-1], 2, 20)

    def test_what_a_test_refuses_stays_refused_and_a_mapping_save_waits_for_an_open_upload(self):
        swapped = swapped_pins()
        script = [support.line(T0, "mapping test on"), support.line(T0 + 1, "catalog rebuild internal"), support.line(T0 + 2, "upload begin 3 new.odrg 100"),
                  support.line(T0 + 3, "mapping test off"), support.line(T0 + 4, "upload begin 3 new.odrg 100"), support.line(T0 + 5, mapping_save(swapped)),
                  support.line(T0 + 6, "upload cancel"), support.line(T0 + 7, mapping_save(swapped))]
        replies = answers(support.start(files(), script))
        busy = {"ok": False, "error": "busy"}
        self.assertEqual(replies[:4], [{"ok": True}, busy, busy, {"ok": True}])
        self.assertEqual((replies[4]["ok"], replies[5], replies[6], replies[7]), (True, busy, {"ok": True}, {"ok": True}))


if __name__ == "__main__":
    unittest.main()

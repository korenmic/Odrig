import json
import unittest

from odrig import jsonframes, mapping, odrg

from . import support

T0 = 1000


def animation_item(number, file):
    return {"id": number, "file": file}


def playing(files, start):
    """The file set with a show that plays one of its items from power-on."""
    listed = json.loads(files["show.json"])
    files = dict(files)
    files["show.json"] = support.show_text(listed["items"], listed["brightness"], start)
    return files


def one_clip(mapping_text, clip, brightness=255, start=1):
    """A file set of one animation, `clip.odrg`, that plays from power-on."""
    return {
        "mapping.json": mapping_text,
        "show.json": support.show_text([animation_item(1, "clip.odrg")], brightness, start),
        "clip.odrg": clip,
    }


def polls(times):
    return [f"poll {time}" for time in times]


def every_20_ms(count, start=T0):
    return polls(start + 20 * step for step in range(count))


def refreshes(lines):
    """`(timestamp, {leg: LED data})` for each refresh among the lines of a session, and the
    timestamps of the polls that found none due."""
    produced = []
    idle = []
    for line in lines:
        word, _, rest = line.partition(" ")
        if word == "refresh":
            produced.append((int(rest), {}))
        elif word == "data":
            leg, _, data = rest.partition(" ")
            produced[-1][1][int(leg)] = bytes.fromhex(data)
        elif word == "idle":
            idle.append(int(rest))
        else:
            raise AssertionError(f"not a line of a poll: {line[:60]}")
    return produced, idle


class Playback(unittest.TestCase):
    def assert_as_the_reference(self, files, script, options=()):
        """Runs a script on the core and on the reference player and compares every line."""
        printed = support.start(files, script, options).lines
        expected = support.ReferencePlayer(files).run(script)
        self.assertEqual(len(printed), len(expected))
        for number, (line, wanted) in enumerate(zip(printed, expected)):
            if line != wanted:
                self.fail(f"line {number} differs: the core printed {line[:90]}, the reference {wanted[:90]}")
        return printed


class OneLoopAndIntoTheNext(Playback):
    def play_one_loop(self, files, frames_of_20_ms):
        script = every_20_ms(frames_of_20_ms + 10)
        printed = self.assert_as_the_reference(files, script)
        produced, idle = refreshes(printed)
        self.assertEqual(len(produced), frames_of_20_ms + 10)
        self.assertEqual(idle, [])
        self.assertTrue(any(any(data) for data in produced[0][1].values()))
        # The loop starts again: the pictures after one loop are those of its start.
        for step in range(10):
            self.assertEqual(produced[frames_of_20_ms + step][1], produced[step][1], f"refresh {step} of the next loop")
        return produced

    def test_hello_world_on_the_two_leg_mapping(self):
        files = playing(support.example_show(), 1)
        frames = odrg.decode(files["hello.odrg"]).records
        self.assertEqual(sum(duration for duration, _ in frames), 5100)
        produced = self.play_one_loop(files, 255)
        self.assertEqual({leg: len(data) for leg, data in produced[0][1].items()}, {1: 540, 2: 540})

    def test_dvd_bounce_on_the_two_leg_mapping(self):
        files = playing(support.example_show(), 2)
        frames = odrg.decode(files["dvd.odrg"]).records
        total = sum(duration for duration, _ in frames)
        self.assertGreater(total, 40000)
        self.assertEqual(total % 20, 0)
        self.play_one_loop(files, total // 20)

    def test_hello_world_on_the_target_file(self):
        files = playing(support.demo_show(), 1)
        decoded = odrg.decode(files["hello.odrg"])
        self.assertEqual((decoded.width, decoded.height), (60, 60))
        self.assertEqual(sum(duration for duration, _ in decoded.records), 5100)
        produced = self.play_one_loop(files, 255)
        self.assertEqual({leg: len(data) for leg, data in produced[0][1].items()}, {leg: 540 for leg in range(1, 21)})
        self.assertEqual(len({tuple(sorted(legs.items())) for _, legs in produced[:255]}), 255)

    def test_dvd_bounce_on_the_target_file(self):
        files = playing(support.demo_show(), 2)
        decoded = odrg.decode(files["dvd.odrg"])
        self.assertEqual((decoded.width, decoded.height), (60, 60))
        total = sum(duration for duration, _ in decoded.records)
        self.assertEqual(total, 116 * 180)
        produced = self.play_one_loop(files, total // 20)
        # The square passes over LEDs of every leg in one loop.
        lit = {leg for _, legs in produced for leg, data in legs.items() if any(data)}
        self.assertEqual(lit, set(range(1, 21)))

    def test_the_dense_clip_on_the_target_file(self):
        files = one_clip(support.mapping_texts()["legs-20"], support.dense_clip(60, 60, 10), brightness=128)
        self.assertEqual(files["clip.odrg"][5], 1)
        produced = self.play_one_loop(files, 500)
        self.assertEqual(sorted(produced[0][1]), list(range(1, 21)))
        self.assertEqual({len(data) for data in produced[0][1].values()}, {540})
        self.assertNotEqual(produced[0][1], produced[1][1])

    def test_the_dense_clip_without_compression(self):
        files = one_clip(support.mapping_texts()["legs-20"], support.dense_clip(60, 60, 1, compressed=False))
        self.assertEqual(files["clip.odrg"][5], 0)
        self.play_one_loop(files, 50)


class EveryLedShowsItsPixel(Playback):
    def test_on_every_mapping_each_led_shows_the_pixel_the_rule_gives_it(self):
        texts = support.mapping_texts()
        self.assertLessEqual({"legs-2", "legs-20", *support.MADE_UP_MAPPINGS, *support.MADE_UP_COLUMN_MAPPINGS}, set(texts))
        kinds = set()
        for name, text in texts.items():
            with self.subTest(mapping=name):
                listed = json.loads(text)
                if "width" in listed:
                    kinds.add("rows")
                    width = listed["width"]
                    height = sum(len(leg["rows"]) for leg in listed["legs"])
                else:
                    kinds.add("columns")
                    height = listed["height"]
                    width = sum(len(leg["columns"]) for leg in listed["legs"])
                # Pixel (x, y) has the colour (x, y, 200), so an LED tells which pixel it shows.
                picture = b"".join(bytes((x, y, 200)) for y in range(1, height + 1) for x in range(1, width + 1))
                clip = odrg.encode(jsonframes.Animation(width, height, ((1000, picture),)))
                produced, _ = refreshes(support.start(one_clip(text, clip), every_20_ms(3)).lines)
                self.assertEqual(len(produced), 3)
                self.assertEqual([leg["leg"] for leg in listed["legs"]], list(produced[0][1]))
                shown = []
                for leg in listed["legs"]:
                    data = produced[2][1][leg["leg"]]
                    if "width" in listed:
                        self.assertEqual(len(data), 3 * width * len(leg["rows"]))
                        for n in range(1, width * len(leg["rows"]) + 1):
                            r = (n - 1) // width
                            i = (n - 1) % width
                            y = leg["rows"][r]
                            starts_on_the_first_side = r % 2 == 0
                            from_the_right = (leg["first_led"] == "right") == starts_on_the_first_side
                            x = width - i if from_the_right else 1 + i
                            self.assertEqual(tuple(data[3 * (n - 1):3 * n]), (x, y, 200), f"LED {n} of leg {leg['leg']}")
                            shown.append((x, y))
                    else:
                        self.assertEqual(len(data), 3 * height * len(leg["columns"]))
                        for n in range(1, height * len(leg["columns"]) + 1):
                            s = (n - 1) // height
                            i = (n - 1) % height
                            x = leg["columns"][s]
                            starts_at_the_first_end = s % 2 == 0
                            from_the_bottom = (leg["first_led"] == "bottom") == starts_at_the_first_end
                            y = 1 + i if from_the_bottom else height - i
                            self.assertEqual(tuple(data[3 * (n - 1):3 * n]), (x, y, 200), f"LED {n} of leg {leg['leg']}")
                            shown.append((x, y))
                # Every pixel of the canvas is shown by exactly one LED.
                self.assertEqual(sorted(shown), [(x, y) for x in range(1, width + 1) for y in range(1, height + 1)])
        self.assertEqual(kinds, {"rows", "columns"})

    def test_the_first_and_last_leds_of_the_two_leg_mapping_are_where_the_document_says(self):
        text = support.mapping_texts()["legs-2"]
        picture = b"".join(bytes((x, y, 200)) for y in range(1, 7) for x in range(1, 61))
        clip = odrg.encode(jsonframes.Animation(60, 6, ((20, picture),)))
        produced, _ = refreshes(support.start(one_clip(text, clip), every_20_ms(1)).lines)
        legs = produced[0][1]

        def led(leg, n):
            return tuple(legs[leg][3 * (n - 1):3 * n][:2])

        self.assertEqual([led(1, n) for n in (1, 60, 61, 120, 121, 180)], [(60, 6), (1, 6), (1, 5), (60, 5), (60, 4), (1, 4)])
        self.assertEqual([led(2, n) for n in (1, 60, 61, 120, 121, 180)], [(60, 3), (1, 3), (1, 2), (60, 2), (60, 1), (1, 1)])

    def test_a_palette_file_and_a_file_without_palette_show_the_same_picture(self):
        text = support.mapping_texts()["another-order"]
        animation = support.seeded_animation(3, 4, 5, (20, 40, 20, 20), colours=6)
        with_palette = odrg.encode(animation)
        self.assertNotEqual(with_palette[10:12], b"\0\0")
        records = []
        old = bytes(60)
        for ms, picture in animation.frames:
            records.append(odrg.best_record(old, picture, 4, 3, ms))
            old = picture
        without = odrg.container(4, 5, None, records)
        self.assertEqual(without[10:12], b"\0\0")
        script = every_20_ms(12)
        first = self.assert_as_the_reference(one_clip(text, with_palette), script)
        second = self.assert_as_the_reference(one_clip(text, without), script)
        self.assertEqual(first, second)


class ColumnLegs(Playback):
    def leds(self, text, width, height):
        """The pixel `(x, y)` each LED of each leg shows, read from a picture in which
        every pixel has a colour of its own."""
        picture = b"".join(bytes((x, y, 200)) for y in range(1, height + 1) for x in range(1, width + 1))
        clip = odrg.encode(jsonframes.Animation(width, height, ((20, picture),)))
        produced, _ = refreshes(support.start(one_clip(text, clip), every_20_ms(1)).lines)
        return {leg: [tuple(data[at:at + 2]) for at in range(0, len(data), 3)] for leg, data in produced[0][1].items()}

    def test_the_ends_of_the_columns_of_legs_that_start_at_the_bottom(self):
        text = json.dumps({
            "version": 1,
            "height": 60,
            "legs": [
                {"leg": 1, "pin": 1, "first_led": "bottom", "columns": [1, 2, 3]},
                {"leg": 2, "pin": 2, "first_led": "bottom", "columns": [4, 5, 6]},
            ],
        })
        legs = self.leds(text, 6, 60)
        self.assertEqual([len(places) for places in legs.values()], [180, 180])
        self.assertEqual([legs[1][n - 1] for n in (1, 60, 61, 120, 121, 180)], [(1, 1), (1, 60), (2, 60), (2, 1), (3, 1), (3, 60)])
        self.assertEqual([legs[2][n - 1] for n in (1, 60, 61, 120, 121, 180)], [(4, 1), (4, 60), (5, 60), (5, 1), (6, 1), (6, 60)])

    def test_the_ends_of_the_columns_of_a_leg_that_starts_at_the_top(self):
        legs = self.leds(support.column_mapping_texts()["top-start"], 3, 7)
        self.assertEqual([legs[1][n - 1] for n in (1, 2, 7, 8, 14, 15, 21)], [(1, 7), (1, 6), (1, 1), (2, 1), (2, 7), (3, 7), (3, 1)])

    def test_columns_that_are_not_neighbours_are_sent_in_the_order_of_the_chain(self):
        legs = self.leds(support.column_mapping_texts()["columns-apart"], 5, 4)
        self.assertEqual(legs[7], [(2, 1), (2, 2), (2, 3), (2, 4), (4, 4), (4, 3), (4, 2), (4, 1)])
        self.assertEqual(legs[2], [(1, 4), (1, 3), (1, 2), (1, 1), (5, 1), (5, 2), (5, 3), (5, 4), (3, 4), (3, 3), (3, 2), (3, 1)])

    def test_a_clip_plays_on_every_column_leg_mapping_as_the_reference_plays_it(self):
        for name, text in support.column_mapping_texts().items():
            for compressed in (True, False):
                with self.subTest(mapping=name, compressed=compressed):
                    canvas = mapping.loads(text.encode("utf-8"))
                    self.assertEqual(canvas.kind, mapping.COLUMNS)
                    clip = support.clip(8, canvas.width, canvas.height, (20, 40, 7, 13, 60, 20, 20), compressed=compressed)
                    files = one_clip(text, clip, brightness=128)
                    produced, idle = refreshes(self.assert_as_the_reference(files, polls(range(T0, T0 + 500, 4))))
                    self.assertEqual(len(produced), 25)
                    self.assertEqual(len(idle), 100)
                    self.assertEqual({leg: len(data) for leg, data in produced[0][1].items()},
                                     {leg.leg: 3 * canvas.height * len(leg.strips) for leg in canvas.legs})
                    self.assertTrue(any(any(data) for data in produced[0][1].values()))
                    # The loop of 180 ms starts again: the picture after one loop is that of its start.
                    self.assertEqual(produced[9][1], produced[0][1])
                    self.assertGreater(len({tuple(sorted(data.items())) for _, data in produced}), 1)

    def test_a_row_leg_file_and_a_column_leg_file_of_one_canvas_send_the_same_pixels_in_another_order(self):
        rows = json.dumps({"version": 1, "width": 3, "legs": [{"leg": 1, "pin": 1, "first_led": "left", "rows": [1, 2]}]})
        columns = json.dumps({"version": 1, "height": 2, "legs": [{"leg": 1, "pin": 1, "first_led": "bottom", "columns": [1, 2, 3]}]})
        self.assertEqual(self.leds(rows, 3, 2)[1], [(1, 1), (2, 1), (3, 1), (3, 2), (2, 2), (1, 2)])
        self.assertEqual(self.leds(columns, 3, 2)[1], [(1, 1), (1, 2), (2, 2), (2, 1), (3, 1), (3, 2)])


class Brightness(Playback):
    def test_hello_world_at_brightness_255_128_1_and_0(self):
        script = every_20_ms(40)
        at = {}
        for brightness in (255, 128, 1, 0):
            files = playing(support.example_show(), 1)
            files["show.json"] = support.show_text(json.loads(files["show.json"])["items"], brightness, 1)
            at[brightness], _ = refreshes(self.assert_as_the_reference(files, script))
        for number in range(40):
            for leg in (1, 2):
                full = at[255][number][1][leg]
                self.assertEqual(at[128][number][1][leg], bytes((value * 128 + 127) // 255 for value in full))
                self.assertEqual(at[1][number][1][leg], bytes(1 if value >= 128 else 0 for value in full))
                self.assertEqual(at[0][number][1][leg], bytes(len(full)))
        self.assertTrue(any(value >= 128 for value in at[255][0][1][1]))

    def test_at_brightness_255_the_leds_get_the_colours_of_the_source(self):
        files = playing(support.example_show(), 1)
        files["show.json"] = support.show_text(json.loads(files["show.json"])["items"], 255, 1)
        produced, _ = refreshes(support.start(files, every_20_ms(1)).lines)
        source = jsonframes.loads((support.ROOT / "animations" / "hello.json").read_bytes())
        picture = source.frames[0][1]
        canvas = mapping.loads(files["mapping.json"])
        for leg in canvas.legs:
            expected = b"".join(picture[3 * place:3 * place + 3] for place in support.led_pixels(canvas, leg))
            self.assertEqual(produced[0][1][leg.leg], expected)


class TheGrid(Playback):
    def hello(self):
        return playing(support.example_show(), 1)

    def test_polls_1_ms_apart_give_one_refresh_for_each_grid_time(self):
        printed = self.assert_as_the_reference(self.hello(), polls(range(T0, T0 + 201)))
        produced, idle = refreshes(printed)
        self.assertEqual([time for time, _ in produced], list(range(T0, T0 + 201, 20)))
        self.assertEqual(len(idle), 201 - 11)

    def test_polls_50_ms_apart_give_one_refresh_for_each_poll_with_the_picture_of_its_time(self):
        times = list(range(T0, T0 + 6000, 50))
        late, idle = refreshes(self.assert_as_the_reference(self.hello(), polls(times)))
        self.assertEqual([time for time, _ in late], times)
        self.assertEqual(idle, [])
        regular, _ = refreshes(support.start(self.hello(), every_20_ms(300)).lines)
        pictures = dict(regular)
        for time, legs in late:
            # 50 ms after a grid time is 10 ms into a frame of 20 ms: the frame of 40 ms.
            self.assertEqual(legs, pictures[time - (time - T0) % 20], f"at {time}")

    def test_a_poll_that_comes_late_shows_the_picture_of_its_own_time_and_skips_no_later_grid_time(self):
        times = [T0, T0 + 33, T0 + 40, T0 + 59, T0 + 60, T0 + 79, T0 + 139, T0 + 140]
        produced, idle = refreshes(self.assert_as_the_reference(self.hello(), polls(times)))
        self.assertEqual([time for time, _ in produced], [T0, T0 + 33, T0 + 40, T0 + 60, T0 + 139, T0 + 140])
        self.assertEqual(idle, [T0 + 59, T0 + 79])

    def test_a_poll_after_a_gap_of_several_loops_gives_the_picture_of_its_time(self):
        times = [T0, T0 + 3 * 5100 + 1240, T0 + 3 * 5100 + 1260, T0 + 40 * 5100 + 777, T0 + 41 * 5100]
        produced, idle = refreshes(self.assert_as_the_reference(self.hello(), polls(times)))
        self.assertEqual(idle, [])
        regular = dict(refreshes(support.start(self.hello(), every_20_ms(256)).lines)[0])
        self.assertEqual(produced[1][1], regular[T0 + 1240])
        self.assertEqual(produced[2][1], regular[T0 + 1260])
        self.assertEqual(produced[3][1], regular[T0 + 760])
        self.assertEqual(produced[4][1], regular[T0])

    def test_skipped_refreshes_do_not_change_the_pictures_that_follow(self):
        regular = dict(refreshes(support.start(self.hello(), every_20_ms(200)).lines)[0])
        kept = [T0 + 20 * step for step in (0, 1, 2, 9, 10, 50, 51, 120, 199)]
        thinned, _ = refreshes(support.start(self.hello(), polls(kept)).lines)
        self.assertEqual([time for time, _ in thinned], kept)
        for time, legs in thinned:
            self.assertEqual(legs, regular[time], f"at {time}")

    def test_a_timestamp_below_the_latest_counts_as_the_latest(self):
        times = [T0, T0 + 100, T0 + 40, T0 + 60, T0 + 119, T0 + 120, T0, T0 + 140]
        produced, idle = refreshes(self.assert_as_the_reference(self.hello(), polls(times)))
        self.assertEqual([time for time, _ in produced], [T0, T0 + 100, T0 + 120, T0 + 140])
        self.assertEqual(idle, [T0 + 40, T0 + 60, T0 + 119, T0])

    def test_a_timestamp_below_the_power_on_moment_counts_as_that_moment(self):
        produced, idle = refreshes(self.assert_as_the_reference(self.hello(), polls([T0, 0, T0 - 1, T0 + 19, T0 + 20])))
        self.assertEqual([time for time, _ in produced], [T0, T0 + 20])
        self.assertEqual(idle, [0, T0 - 1, T0 + 19])

    def test_the_grid_starts_at_the_first_timestamp_whatever_it_is(self):
        for start in (0, 7, 999, 2 ** 32 - 30, 2 ** 53 + 1, 9 * 10 ** 18):
            with self.subTest(start=start):
                times = [start, start + 19, start + 20, start + 5100, start + 5119, start + 5120]
                produced, idle = refreshes(self.assert_as_the_reference(self.hello(), polls(times)))
                self.assertEqual(idle, [start + 19, start + 5119])
                self.assertEqual(produced[0][1], produced[2][1])
                self.assertEqual(produced[1][1], produced[3][1])

    def test_the_same_polls_give_the_same_pictures_from_any_power_on_moment(self):
        first, _ = refreshes(support.start(self.hello(), every_20_ms(30, start=0)).lines)
        second, _ = refreshes(support.start(self.hello(), every_20_ms(30, start=123456789)).lines)
        self.assertEqual([legs for _, legs in first], [legs for _, legs in second])


class NothingToShow(Playback):
    def assert_dark(self, files, legs):
        script = every_20_ms(5)
        produced, idle = refreshes(self.assert_as_the_reference(files, script))
        self.assertEqual(len(produced), 5)
        self.assertEqual(idle, [])
        for _, data in produced:
            self.assertEqual(sorted(data), legs)
            for rgb in data.values():
                self.assertEqual(rgb, bytes(540))

    def test_a_show_without_start_gives_dark_refreshes(self):
        files = support.example_show()
        files["show.json"] = support.show_text(json.loads(files["show.json"])["items"], 128)
        self.assert_dark(files, [1, 2])

    def test_an_invalid_show_gives_dark_refreshes(self):
        missing_file = support.example_show()
        del missing_file["dvd.odrg"]
        self.assert_dark(playing(missing_file, 1), [1, 2])
        no_show = support.example_show()
        del no_show["show.json"]
        self.assert_dark(no_show, [1, 2])
        self.assert_dark(playing(support.example_show(), 9), [1, 2])

    def test_a_show_that_ran_out_of_memory_after_the_mapping_gives_dark_refreshes(self):
        for block in (8, 9, 12):
            run = support.start(playing(support.example_show(), 1), every_20_ms(3), ["--alloc-fails-at", str(block)])
            produced, idle = refreshes(run.lines)
            self.assertEqual(run.error, "out-of-memory")
            self.assertEqual([data for _, data in produced], [{1: bytes(540), 2: bytes(540)}] * 3)

    def test_an_invalid_mapping_gives_idle(self):
        for change in ({"mapping.json": None}, {"mapping.json": "{}"}):
            files = playing(support.example_show(), 1)
            for name, content in change.items():
                if content is None:
                    del files[name]
                else:
                    files[name] = content
            script = every_20_ms(5)
            printed = self.assert_as_the_reference(files, script)
            self.assertEqual(printed, [f"idle {T0 + 20 * step}" for step in range(5)])

    def test_a_mapping_that_ran_out_of_memory_gives_idle(self):
        run = support.start(playing(support.example_show(), 1), every_20_ms(2), ["--alloc-fails-at", "6"])
        self.assertEqual(run.lines, [f"idle {T0}", f"idle {T0 + 20}"])


class ShortFiles(Playback):
    def test_a_file_of_one_frame(self):
        text = support.mapping_texts()["two-and-four-rows"]
        for duration in (1, 20, 65535):
            with self.subTest(duration=duration):
                clip = support.clip(5, 5, 6, (duration,))
                produced, _ = refreshes(self.assert_as_the_reference(one_clip(text, clip), polls([T0, T0 + 20, T0 + 40, T0 + 70000, T0 + 131080])))
                self.assertEqual(len({tuple(sorted(data.items())) for _, data in produced}), 1)
                self.assertTrue(any(any(rgb) for rgb in produced[0][1].values()))

    def test_a_file_whose_frames_last_1_ms(self):
        text = support.mapping_texts()["left-start"]
        clip = support.clip(6, 7, 3, (1,) * 7)
        produced, _ = refreshes(self.assert_as_the_reference(one_clip(text, clip), polls(range(T0, T0 + 300))))
        self.assertEqual(len(produced), 15)
        # A refresh every 20 ms shows frame (20 * k) mod 7 of the seven.
        pictures = [data for _, data in produced]
        self.assertEqual(pictures[7], pictures[0])
        self.assertEqual(len({tuple(sorted(data.items())) for data in pictures[:7]}), 7)
        late = polls(T0 + offset for offset in (0, 23, 41, 66, 85, 100, 127, 145, 163, 181))
        self.assert_as_the_reference(one_clip(text, clip), late)

    def test_frames_of_uneven_lengths(self):
        text = support.mapping_texts()["another-order"]
        clip = support.clip(7, 4, 5, (7, 13, 20, 1, 59, 300, 65535, 2, 40))
        self.assert_as_the_reference(one_clip(text, clip), polls(range(T0, T0 + 500, 3)))
        self.assert_as_the_reference(one_clip(text, clip), polls(range(T0, T0 + 3 * 65977, 1777)))


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from . import support
from .test_playback import T0, Playback, every_20_ms, polls, refreshes

OK = "reply " + '{"ok":true}'


def at(time, text):
    return support.line(T0 + time, text)


def status_at(time):
    return at(time, "status")


def state(line):
    """The members of a status reply, from the line the test host prints for it."""
    return json.loads(line[len("reply "):])


def hello_only(brightness=255):
    files = support.example_show()
    files["show.json"] = support.show_text([{"id": 1, "file": "hello.odrg"}, {"id": 2, "file": "dvd.odrg"}], brightness, 1)
    return files


class StatusReply(Playback):
    def test_its_exact_bytes(self):
        printed = self.assert_as_the_reference(support.example_show(), [status_at(0)])
        self.assertEqual(printed, ['reply {"ok":true,"on":true,"brightness":128,"dimming":{"value":128,"saved":null,"error":null},"mini":{"supported":false,"on":false,"pending":false,"requested":false,"error":null,"brightness":40},"playing":3,"animation":1,"fps":0,"error":null,"width":60,"height":6,"readiness":"ready","checked":2,"to_check":0,"unavailable":0,"checking":null,"host":null,"seed":null,"repeat":null,"loop":null,"saved":null,"file":"hello.odrg","playlist":null,"clocks":false,"clock_message":false,"left":86400}'])

    def test_its_exact_bytes_when_nothing_plays_and_the_show_is_invalid(self):
        files = support.with_show_fault(support.example_show())
        printed = self.assert_as_the_reference(files, [at(0, "off"), status_at(0)])
        self.assertEqual(
            printed[1],
            'reply {"ok":true,"on":false,"brightness":0,"dimming":null,"mini":{"supported":false,"on":false,"pending":false,"requested":false,"error":null,"brightness":0},"playing":null,"animation":null,"fps":0,"error":"undefined-id 99","width":60,"height":6,"readiness":"recovery","checked":0,"to_check":0,"unavailable":0,"checking":null,"host":null,"seed":null,"repeat":null,"loop":null,"saved":null,"file":null,"playlist":null,"clocks":false,"clock_message":false,"left":86400}',
        )

    def test_it_is_the_reply_of_the_document(self):
        text = (support.ROOT / "docs" / "commands.md").read_text(encoding="utf-8")
        example = '{"ok":true,"on":true,"brightness":128,"dimming":{"value":128,"saved":null,"error":null},"mini":{"supported":false,"on":false,"pending":false,"requested":false,"error":null,"brightness":40},"playing":3,"animation":1,"fps":50,"error":null,"width":60,"height":6,"readiness":"ready","checked":2,"to_check":0,"unavailable":0,"checking":null,"host":null,"seed":null,"repeat":null,"loop":null,"saved":null,"file":"hello.odrg","playlist":null,"clocks":false,"clock_message":false,"left":86399}'
        self.assertIn(example, text)
        script = every_20_ms(50) + [status_at(1000)]
        printed = self.assert_as_the_reference(support.example_show(), script)
        self.assertEqual(printed[-1], f"reply {example}")


class TheCanvas(Playback):
    def canvas(self, files):
        printed = self.assert_as_the_reference(files, [status_at(0)])
        reply = state(printed[0])
        return reply["width"], reply["height"]

    def test_it_is_the_canvas_of_the_installed_mapping(self):
        self.assertEqual(self.canvas(support.example_show()), (60, 6))
        files = support.example_show()
        files["mapping.json"] = support.one_leg_mapping(5, 3)
        files["show.json"] = support.show_text([], 128)
        self.assertEqual(self.canvas(files), (5, 3))

    def test_it_is_null_without_a_mapping_and_with_one_the_core_refuses(self):
        files = support.example_show()
        del files["mapping.json"]
        self.assertEqual(self.canvas(files), (None, None))
        files["mapping.json"] = "{"
        self.assertEqual(self.canvas(files), (None, None))

    def test_it_is_reported_while_the_show_is_invalid_for_another_reason(self):
        files = support.with_show_fault(support.example_show())
        printed = self.assert_as_the_reference(files, [status_at(0)])
        reply = state(printed[0])
        self.assertEqual((reply["error"], reply["width"], reply["height"]), ("undefined-id 99", 60, 6))


class RefreshRate(Playback):
    def fps(self, poll_times, status_times):
        """The `fps` that `status` reports at each of the status times, after all polls up
        to that time."""
        script = []
        waiting = sorted(poll_times)
        for time in sorted(status_times):
            while waiting and waiting[0] <= time:
                script.append(f"poll {T0 + waiting.pop(0)}")
            script.append(status_at(time))
        printed = self.assert_as_the_reference(hello_only(), script)
        return [state(line)["fps"] for line in printed if line.startswith("reply ")]

    def test_it_is_0_in_the_first_second(self):
        self.assertEqual(self.fps(range(0, 1000, 20), [0, 1, 500, 999]), [0, 0, 0, 0])

    def test_it_is_50_with_regular_polls(self):
        self.assertEqual(self.fps(range(0, 5000, 20), [1000, 1500, 1999, 2000, 3000, 4999]), [50, 50, 50, 50, 50, 50])

    def test_it_is_the_real_count_with_late_polls(self):
        every_50 = self.fps(range(0, 3000, 50), [1000, 2000, 2999])
        self.assertEqual(every_50, [20, 20, 20])
        uneven = list(range(0, 1000, 20)) + [1000, 1300, 1999] + list(range(2000, 3000, 100)) + [3999]
        self.assertEqual(self.fps(uneven, [1000, 2000, 3000, 4000]), [50, 3, 10, 1])

    def test_polls_that_find_no_refresh_due_are_not_counted(self):
        self.assertEqual(self.fps(range(0, 2000, 1), [1000, 2000]), [50, 50])

    def test_it_is_0_after_a_second_without_polls(self):
        polled = list(range(0, 1000, 20)) + list(range(2000, 2500, 20))
        self.assertEqual(self.fps(polled, [1000, 1999, 2000, 2999, 3000, 3999, 4000, 60000]), [50, 50, 0, 0, 25, 25, 0, 0])

    def test_it_is_0_when_nothing_was_ever_polled(self):
        self.assertEqual(self.fps([], [0, 1000, 99999]), [0, 0, 0])

    def test_the_seconds_are_counted_from_the_power_on_moment(self):
        # Power-on is the first call, here a status at 400 ms; a second ends at 1,400 ms.
        script = [status_at(400)] + polls(T0 + time for time in range(400, 1400, 20)) + [status_at(1399), status_at(1400)]
        printed = self.assert_as_the_reference(hello_only(), script)
        answers = [state(line)["fps"] for line in printed if line.startswith("reply ")]
        self.assertEqual(answers, [0, 0, 50])

    def test_refreshes_are_counted_whatever_they_show(self):
        dark = support.example_show()
        del dark["show.json"]
        printed = self.assert_as_the_reference(dark, every_20_ms(50) + [at(500, "off"), status_at(1000)])
        self.assertEqual(state(printed[-1])["fps"], 50)
        no_mapping = support.example_show()
        del no_mapping["mapping.json"]
        printed = self.assert_as_the_reference(no_mapping, every_20_ms(50) + [status_at(1000)])
        self.assertEqual(state(printed[-1])["fps"], 0)


class Animation(Playback):
    def test_it_follows_the_cycle(self):
        script = [status_at(0)]
        for time in range(0, 31000, 20):
            script.append(f"poll {T0 + time}")
            if time in (0, 14980, 15000, 29980, 30000):
                script.append(status_at(time))
        printed = self.assert_as_the_reference(support.example_show(), script)
        seen = [(state(line)["playing"], state(line)["animation"]) for line in printed if line.startswith("reply ")]
        self.assertEqual(seen, [(3, 1), (3, 1), (3, 1), (3, 2), (3, 2), (3, 1)])

    def test_straight_after_play_it_is_the_first_animation_of_the_item(self):
        script = polls(T0 + time for time in range(0, 16000, 20)) + [status_at(16000), at(16000, "play 3"), status_at(16000), at(16000, "play 2"), status_at(16000)]
        printed = self.assert_as_the_reference(support.example_show(), script)
        seen = [(state(line)["playing"], state(line)["animation"]) for line in printed[-5::2]]
        self.assertEqual(seen, [(3, 2), (3, 1), ("all", 2)])

    def test_it_is_the_first_entry_of_a_cycle_that_starts_with_its_second_item(self):
        files = support.example_show()
        files["show.json"] = support.show_text(json.loads(files["show.json"])["items"] + [{"id": 9, "cycle": [2, 1], "seconds": 1}], 128, 9)
        printed = self.assert_as_the_reference(files, [status_at(0), f"poll {T0}", f"poll {T0 + 1000}", status_at(1000)])
        self.assertEqual((state(printed[0])["playing"], state(printed[0])["animation"]), (9, 2))
        self.assertEqual(state(printed[-1])["animation"], 1)

    def test_it_is_reported_while_the_leds_are_off(self):
        script = [at(0, "off")] + polls(T0 + time for time in range(0, 15020, 20)) + [status_at(15010)]
        printed = self.assert_as_the_reference(support.example_show(), script)
        last = state(printed[-1])
        self.assertEqual((last["on"], last["playing"], last["animation"]), (False, 3, 2))

    def test_it_is_null_when_nothing_plays(self):
        files = support.example_show()
        files["show.json"] = support.show_text([], 128)
        printed = self.assert_as_the_reference(files, [status_at(0), f"poll {T0}", status_at(10)])
        for line in (printed[0], printed[-1]):
            self.assertEqual((state(line)["playing"], state(line)["animation"]), (None, None))


class StateAfterStartup(Playback):
    def started(self, files, options=()):
        """The status at power-on, without what it says of the check."""
        run = support.start(files, [status_at(0)], options)
        return support.without_readiness(state(run.lines[0]))

    def test_a_valid_show_is_on_at_its_brightness_with_its_start_item_playing(self):
        self.assertEqual(
            self.started(support.example_show()),
            {"ok": True, "on": True, "brightness": 128, "playing": 3, "animation": 1, "fps": 0, "error": None, "width": 60, "height": 6, "seed": None},
        )
        self.assertEqual(self.started(hello_only(7))["brightness"], 7)

    def test_a_valid_show_without_start_plays_the_playlist_from_its_first_animation(self):
        files = support.example_show()
        files["show.json"] = support.show_text(json.loads(files["show.json"])["items"], 31)
        self.assertEqual(
            self.started(files),
            {"ok": True, "on": True, "brightness": 31, "playing": "all", "animation": 1, "fps": 0, "error": None, "width": 60, "height": 6, "seed": None},
        )

    def test_a_valid_show_without_an_animation_plays_nothing(self):
        files = support.example_show()
        files["show.json"] = support.show_text([], 31)
        self.assertEqual(
            self.started(files),
            {"ok": True, "on": True, "brightness": 31, "playing": None, "animation": None, "fps": 0, "error": None, "width": 60, "height": 6, "seed": None},
        )

    def test_an_invalid_show_is_on_and_plays_nothing(self):
        items = json.loads(support.example_show()["show.json"])["items"]

        def with_show(text):
            files = support.example_show()
            files["show.json"] = text
            return files

        def without(name):
            files = support.example_show()
            del files[name]
            return files

        # The brightness is the show's once its ids are checked, and 0 before that. The
        # canvas is the mapping's once the mapping is read.
        cases = (
            (without("mapping.json"), (), "mapping-missing", 0, None),
            (with_show("{}") | {"mapping.json": "{}"}, (), "mapping-malformed", 0, None),
            (without("show.json"), (), "show-missing", 0, 60),
            (with_show('{"version": 1, "brightness": 99, "items": {}}'), (), "show-malformed", 0, 60),
            (with_show(support.show_text(items + [items[0]], 99, 3)), (), "duplicate-id 1", 0, 60),
            (with_show(support.show_text(items, 99, 8)), (), "undefined-id 8", 0, 60),
            (with_show(support.show_text(items + [{"id": 4, "cycle": [3], "seconds": 1}], 99, 3)), (), "nested-cycle 4", 0, 60),
            (with_show(support.show_text(items, 99, 3)), ("--read-fails", "show.json", "20"), "read-error show.json", 0, 60),
            (with_show(support.show_text(items, 99, 3)), ("--alloc-fails-at", "8"), "out-of-memory", 0, 60),
            (with_show(support.show_text(items, 99, 3)), ("--alloc-fails-at", "12"), "out-of-memory", 0, 60),
        )
        for files, options, error, brightness, width in cases:
            with self.subTest(error=error):
                height = None if width is None else 6
                self.assertEqual(
                    self.started(files, options),
                    {"ok": True, "on": True, "brightness": brightness, "playing": None, "animation": None, "fps": 0, "error": error, "width": width, "height": height, "seed": None},
                )

    def test_a_bad_file_leaves_the_show_valid_and_playing(self):
        items = json.loads(support.example_show()["show.json"])["items"]

        def with_show(**changed):
            files = support.example_show()
            files["show.json"] = support.show_text(items, 99, 3)
            for name, content in changed.items():
                files[name.replace("_", ".")] = content
            return files

        missing = with_show()
        del missing["dvd.odrg"]
        # The cycle that starts plays its first usable animation.
        cases = (
            (with_show(hello_odrg=b""), (), 2),
            (missing, (), 1),
            (with_show(dvd_odrg=support.clip(1, 2, 2)), (), 1),
            (with_show(), ("--read-fails", "dvd.odrg", "20"), 1),
        )
        for files, options, animation in cases:
            with self.subTest(animation=animation, options=options):
                self.assertEqual(
                    self.started(files, options),
                    {"ok": True, "on": True, "brightness": 99, "playing": 3, "animation": animation, "fps": 0, "error": None, "width": 60, "height": 6, "seed": None},
                )

    def test_a_jump_off_and_brightness_are_not_kept_from_one_startup_to_the_next(self):
        files = support.example_show()
        with support.installed(files) as folder:
            first = support.session(folder, [at(0, "off"), at(0, "brightness 3"), at(0, "play 2"), status_at(0)])
            second = support.session(folder, [status_at(0)])
        self.assertEqual((state(first.lines[-1])["playing"], state(first.lines[-1])["animation"]), ("all", 2))
        self.assertEqual(
            support.without_readiness(state(second.lines[0])),
            {"ok": True, "on": True, "brightness": 128, "playing": 3, "animation": 1, "fps": 0, "error": None, "width": 60, "height": 6, "seed": None},
        )


class CommandsAndTheLeds(Playback):
    def run_script(self, script, files=None):
        printed = self.assert_as_the_reference(files or hello_only(), script)
        produced, _ = refreshes([line for line in printed if not line.startswith("reply ")])
        return printed, {time - T0: legs for time, legs in produced}

    def alone(self, count=120):
        produced, _ = refreshes(support.start(hello_only(), every_20_ms(count)).lines)
        return {time - T0: legs for time, legs in produced}

    @staticmethod
    def dimmed(legs, brightness):
        return {leg: bytes((value * brightness + 127) // 255 for value in rgb) for leg, rgb in legs.items()}

    def test_a_command_changes_status_at_once_and_the_leds_at_the_next_refresh(self):
        script = [f"poll {T0}", at(5, "brightness 10"), status_at(5), f"poll {T0 + 19}", f"poll {T0 + 20}", at(25, "off"), status_at(25), f"poll {T0 + 40}", at(45, "on"), f"poll {T0 + 60}"]
        printed, shown = self.run_script(script)
        alone = self.alone()
        self.assertEqual(state(printed[4])["brightness"], 10)
        self.assertEqual(printed[5], f"idle {T0 + 19}")
        self.assertIs(state(printed[10])["on"], False)
        self.assertEqual(shown[0], alone[0])
        self.assertEqual(shown[20], self.dimmed(alone[20], 10))
        self.assertEqual(shown[40], {1: bytes(540), 2: bytes(540)})
        self.assertEqual(shown[60], self.dimmed(alone[60], 10))

    def test_the_leds_get_every_colour_value_times_the_brightness_rounded(self):
        script = []
        for step, brightness in enumerate((255, 254, 128, 127, 2, 1, 0, 200)):
            script += [at(20 * step, f"brightness {brightness}"), f"poll {T0 + 20 * step}"]
        _, shown = self.run_script(script)
        alone = self.alone()
        for step, brightness in enumerate((255, 254, 128, 127, 2, 1, 0, 200)):
            self.assertEqual(shown[20 * step], self.dimmed(alone[20 * step], brightness), f"brightness {brightness}")
        self.assertEqual(shown[120], {1: bytes(540), 2: bytes(540)})

    def test_switched_off_the_leds_are_dark_and_the_time_goes_on(self):
        script = polls(T0 + time for time in range(0, 200, 20)) + [at(200, "off")] + polls(T0 + time for time in range(200, 1200, 20))
        script += [at(1200, "on")] + polls(T0 + time for time in range(1200, 1400, 20))
        _, shown = self.run_script(script)
        alone = self.alone()
        for time in range(0, 1400, 20):
            expected = {1: bytes(540), 2: bytes(540)} if 200 <= time < 1200 else alone[time]
            self.assertEqual(shown[time], expected, f"at {time} ms")

    def test_off_and_on_without_a_poll_between_them_leave_no_dark_refresh(self):
        script = [f"poll {T0}", at(1, "off"), at(2, "on"), f"poll {T0 + 20}"]
        _, shown = self.run_script(script)
        self.assertEqual(shown[20], self.alone()[20])

    def test_the_time_of_an_item_starts_at_the_grid_time_of_the_first_refresh_after_play(self):
        alone = self.alone()
        # A command between two grid times: the item starts at the next refresh.
        script = polls([T0, T0 + 20]) + [at(27, "play 1")] + polls([T0 + 39, T0 + 40, T0 + 60, T0 + 80])
        printed, shown = self.run_script(script)
        self.assertIn(f"idle {T0 + 39}", printed)
        self.assertEqual([shown[time] for time in (40, 60, 80)], [alone[0], alone[20], alone[40]])
        # A first refresh that comes late: time zero is its grid time, not its timestamp.
        script = polls([T0, T0 + 20]) + [at(27, "play 1")] + polls([T0 + 53, T0 + 60, T0 + 80])
        _, shown = self.run_script(script)
        self.assertEqual([shown[time] for time in (53, 60, 80)], [alone[0], alone[20], alone[40]])
        # No refresh for a long time after the command: time zero is still that of the first.
        script = polls([T0]) + [at(27, "play 1")] + polls([T0 + 5000, T0 + 5020, T0 + 5100])
        _, shown = self.run_script(script)
        self.assertEqual([shown[time] for time in (5000, 5020, 5100)], [alone[0], alone[20], alone[100]])

    def test_play_of_the_item_that_is_playing_starts_it_again(self):
        script = polls(T0 + time for time in range(0, 1000, 20)) + [at(1000, "play 1")] + polls(T0 + time for time in range(1000, 1200, 20))
        _, shown = self.run_script(script)
        alone = self.alone()
        self.assertEqual(shown[980], alone[980])
        for time in range(1000, 1200, 20):
            self.assertEqual(shown[time], alone[time - 1000], f"at {time} ms")

    def test_play_while_switched_off_starts_the_item_and_stays_dark(self):
        script = [at(0, "off"), f"poll {T0}", at(100, "play 2"), f"poll {T0 + 100}", status_at(100), at(300, "on"), f"poll {T0 + 300}"]
        printed, shown = self.run_script(script)
        self.assertEqual(shown[100], {1: bytes(540), 2: bytes(540)})
        replies = [line for line in printed if line.startswith("reply ")]
        self.assertEqual((state(replies[2])["playing"], state(replies[2])["animation"]), ("all", 2))
        dvd = support.example_show()
        dvd["show.json"] = support.show_text([{"id": 2, "file": "dvd.odrg"}], 255, 2)
        produced, _ = refreshes(support.start(dvd, every_20_ms(11)).lines)
        self.assertEqual(shown[300], produced[10][1])

    def test_the_timestamp_of_a_command_moves_the_clock(self):
        script = [f"poll {T0}", status_at(500), f"poll {T0 + 100}", f"poll {T0 + 500}", f"poll {T0 + 519}", f"poll {T0 + 520}"]
        printed, shown = self.run_script(script)
        # The poll at 100 ms comes after a call at 500 ms, so it happens at 500 ms.
        self.assertEqual([line.split()[0] for line in printed if not line.startswith(("data", "reply"))], ["refresh", "refresh", "idle", "idle", "refresh"])
        self.assertEqual(shown[100], self.alone()[500])

    def test_a_command_can_be_the_first_call(self):
        script = [at(7, "play 2"), f"poll {T0}", f"poll {T0 + 7}", f"poll {T0 + 26}", f"poll {T0 + 27}"]
        printed, _ = self.run_script(script)
        # Power-on is the command's 7 ms, and the grid starts there.
        self.assertEqual([line.split()[0] for line in printed if not line.startswith(("data", "reply"))], ["refresh", "idle", "idle", "refresh"])


if __name__ == "__main__":
    unittest.main()

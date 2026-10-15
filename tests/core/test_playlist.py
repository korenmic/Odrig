import json
import unittest

from . import support
from .test_commands import OK, refused
from .test_playback import T0, Playback, polls, refreshes

CANVAS = (3, 2)
SECOND = (1000,)


def loop_of(seconds, seed):
    """An animation whose loop lasts this many seconds, a picture for each second."""
    return support.clip(seed, *CANVAS, SECOND * seconds)


def show_of(items, files, start=None, **more):
    """A file set on a canvas of one leg: a show of these items, at full brightness."""
    show = {"version": 1, "brightness": 255, "items": list(items), **more}
    if start is not None:
        show["start"] = start
    return {"mapping.json": support.one_leg_mapping(*CANVAS), "show.json": json.dumps(show), **files}


def three(first=None, second=None, third=None, start=None, **more):
    """Animations 1, 2 and 3 with loops of 4, 10 and 45 seconds, each with more members."""
    items = [{"id": 1, "file": "four.odrg", **(first or {})}, {"id": 2, "file": "ten.odrg", **(second or {})}, {"id": 3, "file": "long.odrg", **(third or {})}]
    files = {"four.odrg": loop_of(4, 1), "ten.odrg": loop_of(10, 2), "long.odrg": loop_of(45, 3)}
    return show_of(items, files, start, **more)


def asked_at(times):
    """A refresh and then `status` at each of these times after power-on."""
    script = []
    for time in times:
        script += [f"poll {T0 + time}", support.line(T0 + time, "status")]
    return script


def told(time, command):
    """A command line at this time after power-on."""
    return support.line(T0 + time, command)


def with_a_cycle(files, cycle, start=None, first=False):
    """The file set with a cycle item more in its show, the last item or the first one, and
    played at power-on when `start` names it."""
    show = json.loads(files["show.json"])
    show["items"].insert(0 if first else len(show["items"]), cycle)
    if start is not None:
        show["start"] = start
    return {**files, "show.json": json.dumps(show)}


# A cycle of animation 3 and then animation 1, two seconds each.
CYCLE = {"id": 8, "cycle": [3, 1], "seconds": 2}


class ThePlaylist(Playback):
    def playing_in(self, files, script):
        """What `status` says plays and what is on the LEDs, for each `status` of a session,
        on the core and on the reference player alike. The first turn begins at power-on:
        a refresh is asked for then, before the script."""
        printed = self.assert_as_the_reference(files, [f"poll {T0}"] + list(script))
        states = [json.loads(line[len("reply "):]) for line in printed if line.startswith('reply {"ok":true,"on"')]
        return [(state["playing"], state["animation"]) for state in states]

    def playing_at(self, files, times):
        seen = self.playing_in(files, asked_at(times))
        self.assertEqual(len(seen), len(times))
        return seen

    def animation_in(self, files, script):
        seen = self.playing_in(files, script)
        self.assertEqual({playing for playing, _ in seen}, {"all"})
        return [animation for _, animation in seen]

    def animation_at(self, files, times):
        return self.animation_in(files, asked_at(times))

    def pictures_in(self, files, script):
        """The LED data of each refresh of a session, after the one at power-on that the
        session begins with."""
        printed = self.assert_as_the_reference(files, [f"poll {T0}"] + list(script))
        produced, idle = refreshes([line for line in printed if not line.startswith("reply")])
        self.assertEqual(idle, [])
        return [legs[1] for _, legs in produced][1:]

    def pictures_at(self, files, times):
        """The LED data of the refresh at each of these times. The first turn begins at
        power-on: a refresh is asked for then, whatever the times are."""
        first = [] if times[0] == 0 else [0]
        printed = self.assert_as_the_reference(files, polls(T0 + time for time in first + list(times)))
        produced, idle = refreshes(printed)
        self.assertEqual(idle, [])
        return [legs[1] for _, legs in produced][len(first):]


class TheTurn(ThePlaylist):
    def test_without_numbers_an_animation_plays_the_fewest_loops_that_last_30_seconds(self):
        # 4 seconds: 8 loops, 32 seconds. 10 seconds: 3 loops, 30 seconds. 45 seconds: once.
        times = [0, 29980, 30000, 31980, 32000, 61980, 62000, 106980, 107000, 138980, 139000, 168980, 169000]
        self.assertEqual(self.animation_at(three(), times), [1, 1, 1, 1, 2, 2, 3, 3, 1, 1, 2, 2, 3])

    def test_the_loop_an_animation_is_in_when_the_time_is_up_is_played_to_its_end(self):
        first, at_30, last, after = self.pictures_at(three(), [28000, 30000, 31980, 32000])
        alone = self.pictures_at(show_of([{"id": 1, "file": "four.odrg"}], {"four.odrg": loop_of(4, 1)}), [0, 2000, 3980])
        self.assertEqual([first, at_30, last], alone)
        self.assertNotEqual(after, alone[0])

    def test_a_repeat_count_is_the_number_of_loops(self):
        files = three(first={"repeat": 1}, second={"repeat": 3}, third={"repeat": 2})
        times = [0, 3980, 4000, 33980, 34000, 123980, 124000, 127980, 128000]
        self.assertEqual(self.animation_at(files, times), [1, 1, 2, 2, 3, 3, 1, 1, 2])

    def test_a_longest_time_ends_the_turn_in_the_middle_of_a_loop(self):
        files = three(first={"max_seconds": 7}, second={"repeat": 2, "max_seconds": 15}, third={"max_seconds": 60})
        times = [0, 6980, 7000, 21980, 22000, 66980, 67000, 73980, 74000]
        self.assertEqual(self.animation_at(files, times), [1, 1, 2, 2, 3, 3, 1, 1, 2])

    def test_a_longest_time_above_the_turn_changes_nothing(self):
        files = three(first={"max_seconds": 33}, second={"repeat": 1, "max_seconds": 65535})
        self.assertEqual(self.animation_at(files, [31980, 32000, 41980, 42000]), [1, 2, 2, 3])

    def test_a_turn_begins_with_the_first_frame_also_after_a_turn_that_was_cut(self):
        # A loop of 10 seconds cut at 7: the second turn starts at the first second again.
        files = show_of([{"id": 1, "file": "ten.odrg", "max_seconds": 7}], {"ten.odrg": loop_of(10, 2)})
        seen = self.pictures_at(files, [0, 1000, 6000, 6980, 7000, 8000, 13980, 14000])
        self.assertEqual(seen[4], seen[0])
        self.assertEqual(seen[5], seen[1])
        self.assertEqual(seen[7], seen[0])
        self.assertNotEqual(seen[3], seen[0])
        self.assertEqual(seen[3], seen[2])

    def test_the_shortest_time_of_the_show_takes_the_place_of_the_30_seconds(self):
        # At least 5 seconds: 2 loops of 4, 1 loop of 10, 1 loop of 45.
        times = [0, 7980, 8000, 17980, 18000, 62980, 63000]
        self.assertEqual(self.animation_at(three(min_seconds=5), times), [1, 1, 2, 2, 3, 3, 1])
        # At least 100 seconds: 25 loops of 4, 10 loops of 10, 3 loops of 45.
        times = [99980, 100000, 199980, 200000, 334980, 335000]
        self.assertEqual(self.animation_at(three(min_seconds=100), times), [1, 2, 2, 3, 3, 1])

    def test_a_loop_that_is_no_whole_number_of_seconds(self):
        clip = support.clip(5, *CANVAS, (700, 700, 700))
        files = show_of([{"id": 1, "file": "odd.odrg"}, {"id": 2, "file": "four.odrg"}], {"odd.odrg": clip, "four.odrg": loop_of(4, 1)})
        # 2,100 ms: 15 loops, 31,500 ms.
        self.assertEqual(self.animation_at(files, [31480, 31500, 63480, 63500]), [1, 2, 2, 1])


class TheOrder(ThePlaylist):
    def test_the_animations_play_in_the_order_of_the_show_and_then_from_the_first_again(self):
        files = three(first={"repeat": 1}, second={"repeat": 1}, third={"repeat": 1})
        times = [0, 4000, 14000, 59000, 63000, 73000, 118000]
        self.assertEqual(self.animation_at(files, times), [1, 2, 3, 1, 2, 3, 1])

    def test_a_cycle_among_the_items_has_no_turn(self):
        items = [{"id": 9, "cycle": [2], "seconds": 3}, {"id": 2, "file": "ten.odrg", "repeat": 1}, {"id": 7, "cycle": [1, 2], "seconds": 3},
                 {"id": 1, "file": "four.odrg", "repeat": 1}, {"id": 8, "cycle": [1], "seconds": 3}]
        files = show_of(items, {"four.odrg": loop_of(4, 1), "ten.odrg": loop_of(10, 2)})
        self.assertEqual(self.animation_at(files, [0, 9980, 10000, 13980, 14000, 24000]), [2, 2, 1, 1, 2, 1])

    def test_one_animation_has_turn_after_turn(self):
        files = show_of([{"id": 5, "file": "four.odrg", "repeat": 2}], {"four.odrg": loop_of(4, 1)})
        self.assertEqual(self.animation_at(files, [0, 7980, 8000, 100000]), [5, 5, 5, 5])
        seen = self.pictures_at(files, [0, 1000, 8000, 9000])
        self.assertEqual(seen[2:], seen[:2])

    def test_two_items_with_the_same_file_have_a_turn_each(self):
        items = [{"id": 1, "file": "four.odrg", "repeat": 1}, {"id": 2, "file": "four.odrg", "repeat": 2}]
        files = show_of(items, {"four.odrg": loop_of(4, 1)})
        self.assertEqual(self.animation_at(files, [0, 3980, 4000, 11980, 12000]), [1, 1, 2, 2, 1])


class TheClock(ThePlaylist):
    def test_a_turn_begins_where_the_one_before_it_ended_however_late_the_refresh_is(self):
        files = three(first={"repeat": 1}, second={"repeat": 1}, third={"repeat": 1})
        # No refresh between 3 and 9 seconds: the second turn began at 4 all the same.
        late = self.pictures_at(files, [0, 3000, 9000, 13980, 14000])
        regular = self.pictures_at(files, [0, 3000, 4000, 9000, 13980, 14000])
        self.assertEqual(late[2:], regular[3:])

    def test_a_long_time_without_a_refresh_lands_in_the_turn_of_its_moment(self):
        # One round is 32 + 30 + 45 = 107 seconds. 500 seconds is 72 seconds into a round.
        self.assertEqual(self.animation_at(three(), [0, 500000, 535000, 535020]), [1, 3, 1, 1])
        after_the_gap = self.pictures_at(three(), [0, 500000, 501000])
        in_the_first_round = self.pictures_at(three(), [0, 72000, 73000])
        self.assertEqual(after_the_gap[1:], in_the_first_round[1:])

    def test_a_gap_of_many_rounds_of_a_short_playlist(self):
        files = show_of([{"id": 1, "file": "a.odrg", "repeat": 1}, {"id": 2, "file": "b.odrg", "repeat": 1}],
                        {"a.odrg": support.clip(1, *CANVAS, (20,)), "b.odrg": support.clip(2, *CANVAS, (20, 20))})
        # A round is 60 ms. Ten million rounds later the playlist is where the clock says.
        self.assertEqual(self.animation_at(files, [0, 20, 40, 60, 600000000, 600000020, 600000040, 600000060]), [1, 2, 2, 1, 1, 2, 2, 1])

    def test_switched_off_the_time_of_the_playlist_goes_on(self):
        files = three(first={"repeat": 1}, second={"repeat": 1})
        script = [f"poll {T0}", support.line(T0 + 1000, "off")] + asked_at([3000, 5000]) + [support.line(T0 + 6000, "on")] + asked_at([6000, 13980, 14000])
        printed = self.assert_as_the_reference(files, script)
        states = [json.loads(line[len("reply "):]) for line in printed if line.startswith('reply {"ok":true,"on"')]
        self.assertEqual([(state["on"], state["animation"]) for state in states], [(False, 1), (False, 2), (True, 2), (True, 2), (True, 3)])
        produced, _ = refreshes([line for line in printed if not line.startswith("reply")])
        self.assertEqual([any(legs[1]) for _, legs in produced], [True, False, False, True, True, True])

    def test_the_first_turn_begins_at_the_first_refresh(self):
        files = three(first={"repeat": 1})
        # Power-on is a status at 500 ms. The first refresh is asked for at 2,000, and the
        # turn of 4 seconds begins there and ends at 6,000.
        script = [support.line(T0 + 500, "status")] + asked_at([2000, 5980, 6000])
        printed = self.assert_as_the_reference(files, script)
        states = [json.loads(line[len("reply "):]) for line in printed if line.startswith('reply {"ok":true,"on"')]
        self.assertEqual([(state["playing"], state["animation"]) for state in states], [("all", 1), ("all", 1), ("all", 1), ("all", 2)])


class TheStart(ThePlaylist):
    def test_a_show_without_start_plays_the_playlist_from_its_first_animation(self):
        self.assertEqual(self.playing_at(three(), [0, 1000]), [("all", 1), ("all", 1)])
        printed = self.assert_as_the_reference(three(), [support.line(T0, "status")])
        self.assertEqual(printed, ['reply {"ok":true,"on":true,"brightness":255,"playing":"all","animation":1,"fps":0,"error":null,"width":3,"height":2}'])

    def test_a_start_that_names_an_animation_begins_the_playlist_there(self):
        files = three(first={"repeat": 1}, second={"repeat": 1}, third={"repeat": 1}, start=2)
        self.assertEqual(self.playing_at(files, [0, 9980, 10000, 54980, 55000, 59000]),
                         [("all", 2), ("all", 2), ("all", 3), ("all", 3), ("all", 1), ("all", 2)])
        self.assertEqual(self.playing_at(three(start=3), [0, 44980, 45000]), [("all", 3), ("all", 3), ("all", 1)])

    def test_a_start_that_names_a_cycle_plays_the_cycle(self):
        files = with_a_cycle(three(), CYCLE, start=8)
        self.assertEqual(self.playing_at(files, [0, 1980, 2000, 3980, 4000, 100000]), [(8, 3), (8, 3), (8, 1), (8, 1), (8, 3), (8, 3)])

    def test_a_show_without_an_animation_plays_nothing(self):
        files = show_of([], {})
        self.assertEqual(self.playing_at(files, [0, 40000]), [(None, None), (None, None)])
        self.assertEqual(self.pictures_at(files, [0, 20]), [bytes(18), bytes(18)])

    def test_an_invalid_show_plays_nothing(self):
        files = three()
        del files["ten.odrg"]
        printed = self.assert_as_the_reference(files, asked_at([0]))
        self.assertIn('"playing":null,"animation":null', printed[-1])
        self.assertIn('"error":"file-missing ten.odrg"', printed[-1])


class TheJump(ThePlaylist):
    def test_play_of_an_animation_begins_its_turn_and_the_playlist_goes_on_after_it(self):
        # At 5 seconds, in the turn of animation 1: the 30 seconds of animation 2, then the
        # 45 of animation 3, then the 32 of animation 1.
        script = [told(5000, "play 2")] + asked_at([5000, 34980, 35000, 79980, 80000, 111980, 112000])
        self.assertEqual(self.animation_in(three(), script), [2, 2, 3, 3, 1, 1, 2])

    def test_the_turn_begins_with_the_first_frame_at_the_refresh_after_the_command(self):
        # The command comes between two refreshes, and the turn of 10 seconds begins at 5,020.
        files = three(second={"repeat": 1})
        seen = self.pictures_in(files, [told(5010, "play 2")] + polls(T0 + time for time in (5020, 6020, 15000, 15020)))
        alone = self.pictures_at(show_of([{"id": 1, "file": "ten.odrg"}], {"ten.odrg": loop_of(10, 2)}), [0, 1000, 9980])
        self.assertEqual(seen[:3], alone)
        self.assertNotEqual(seen[3], alone[2])

    def test_a_jump_to_the_animation_whose_turn_it_is_begins_the_turn_again(self):
        script = [told(20000, "play 1")] + asked_at([20000, 51980, 52000])
        self.assertEqual(self.animation_in(three(), script), [1, 1, 2])
        again = self.pictures_in(three(), [told(2000, "play 1"), f"poll {T0 + 2000}"])
        self.assertEqual(again, self.pictures_at(three(), [0]))

    def test_a_jump_to_the_last_animation_goes_on_with_the_first(self):
        script = [told(1000, "play 3")] + asked_at([1000, 45980, 46000, 77980, 78000])
        self.assertEqual(self.animation_in(three(), script), [3, 3, 1, 1, 2])

    def test_a_jump_out_of_a_cycle_plays_the_playlist(self):
        files = with_a_cycle(three(), CYCLE, start=8)
        script = asked_at([1000]) + [told(1500, "play 2")] + asked_at([1500, 31480, 31500, 76480, 76500])
        self.assertEqual(self.playing_in(files, script), [(8, 3), ("all", 2), ("all", 2), ("all", 3), ("all", 3), ("all", 1)])

    def test_a_jump_before_the_first_refresh(self):
        printed = self.assert_as_the_reference(three(), [told(0, "play 3")] + asked_at([400, 45380, 45400]))
        states = [json.loads(line[len("reply "):]) for line in printed if line.startswith('reply {"ok":true,"on"')]
        self.assertEqual([(state["playing"], state["animation"]) for state in states], [("all", 3), ("all", 3), ("all", 1)])

    def test_a_jump_while_the_leds_are_off(self):
        files = three(second={"repeat": 1})
        script = [told(1000, "off"), told(2000, "play 2")] + asked_at([2000, 11980, 12000]) + [told(13000, "on")] + asked_at([13000])
        self.assertEqual(self.animation_in(files, script), [2, 2, 3, 3])

    def test_play_of_a_cycle_plays_the_cycle_and_not_the_playlist(self):
        files = with_a_cycle(three(), CYCLE)
        script = asked_at([1000]) + [told(5000, "play 8")] + asked_at([5000, 6980, 7000, 8980, 9000, 505000])
        self.assertEqual(self.playing_in(files, script), [("all", 1), (8, 3), (8, 3), (8, 1), (8, 1), (8, 3), (8, 3)])

    def test_a_refused_play_leaves_the_playlist_where_it_is(self):
        refusals = [told(5000, line) for line in ("play 9", "play 0", "play 65536", "play 2 2", "play", "play two")]
        self.assertEqual(self.animation_in(three(), refusals + asked_at([5000, 31980, 32000])), [1, 1, 2])


class PlayAll(ThePlaylist):
    def replies_to(self, files, lines):
        printed = self.assert_as_the_reference(files, [told(0, line) for line in lines])
        return [line[len("reply "):] for line in printed]

    def test_from_a_cycle_the_playlist_plays_from_its_first_animation(self):
        files = with_a_cycle(three(), CYCLE, start=8)
        script = asked_at([1000]) + [told(1500, "play all")] + asked_at([1500, 33480, 33500])
        self.assertEqual(self.playing_in(files, script), [(8, 3), ("all", 1), ("all", 1), ("all", 2)])

    def test_in_the_middle_of_the_playlist_it_goes_back_to_the_first_animation(self):
        # At 40 seconds it is the turn of animation 2.
        script = asked_at([40000]) + [told(40010, "play all")] + asked_at([40020, 72000, 72020])
        self.assertEqual(self.animation_in(three(), script), [2, 1, 1, 2])
        seen = self.pictures_in(three(), [told(40010, "play all"), f"poll {T0 + 40020}"])
        self.assertEqual(seen, self.pictures_at(three(), [0]))

    def test_during_the_first_turn_it_begins_that_turn_again(self):
        script = [told(20000, "play all")] + asked_at([20000, 51980, 52000])
        self.assertEqual(self.animation_in(three(), script), [1, 1, 2])

    def test_it_begins_with_the_first_animation_whatever_the_show_starts_with(self):
        script = asked_at([1000]) + [told(2000, "play all")] + asked_at([2000])
        self.assertEqual(self.animation_in(three(start=3), script), [3, 1])

    def test_a_cycle_that_is_the_first_item_is_not_where_it_begins(self):
        files = with_a_cycle(three(), CYCLE, start=8, first=True)
        self.assertEqual(self.playing_in(files, [told(1000, "play all")] + asked_at([1000])), [("all", 1)])

    def test_before_the_first_refresh(self):
        printed = self.assert_as_the_reference(three(start=2), [told(0, "play all")] + asked_at([400, 32380, 32400]))
        states = [json.loads(line[len("reply "):]) for line in printed if line.startswith('reply {"ok":true,"on"')]
        self.assertEqual([state["animation"] for state in states], [1, 1, 2])

    def test_it_is_answered_as_every_command_that_was_carried_out(self):
        self.assertEqual(self.replies_to(three(), ["play all", "play all"]), [OK, OK])
        endings = [support.linehex(T0, b"play all" + ending) for ending in (b"\n", b"\r\n", b"\r")]
        printed = self.assert_as_the_reference(three(), endings)
        self.assertEqual([line[len("reply "):] for line in printed], [OK] * 3)

    def test_a_show_without_an_animation_refuses_it_with_unknown_id(self):
        self.assertEqual(self.replies_to(show_of([], {}), ["play all"]), [refused("unknown-id")])

    def test_an_invalid_show_refuses_it_with_show_invalid(self):
        files = three()
        del files["ten.odrg"]
        self.assertEqual(self.replies_to(files, ["play all"]), [refused("show-invalid")])

    WRONG = ["play all 1", "play all all", "play all ", "play  all", "play ALL", "play All", "play al", "play alll", "play all\t", "play 1 all", "play -all", "play all,"]

    def test_a_word_too_many_or_another_word_is_a_bad_argument(self):
        self.assertEqual(self.replies_to(three(), self.WRONG), [refused("bad-argument")] * len(self.WRONG))

    def test_a_bad_argument_is_named_before_an_invalid_show(self):
        files = three()
        del files["ten.odrg"]
        self.assertEqual(self.replies_to(files, self.WRONG), [refused("bad-argument")] * len(self.WRONG))

    def test_a_refused_one_leaves_what_plays(self):
        files = with_a_cycle(three(), CYCLE, start=8)
        script = asked_at([1000]) + [told(1500, line) for line in self.WRONG] + asked_at([1500])
        self.assertEqual(self.playing_in(files, script), [(8, 3), (8, 3)])

    def test_the_bytes_of_a_transport_are_answered_as_the_lines_are(self):
        lines = [b"play all", b"status", b"play 3", b"status", b"play all now", b"play 9", b"play all", b"status"]
        as_lines = self.assert_as_the_reference(three(), [support.linehex(T0, line) for line in lines])
        text = b"\n".join(lines) + b"\n"
        pieces = [text[at:at + 7] for at in range(0, len(text), 7)]
        as_bytes = self.assert_as_the_reference(three(), [support.fed(T0, piece) for piece in pieces])
        self.assertEqual([line for line in as_bytes if line.startswith("reply ")], as_lines)
        self.assertEqual([bytes.fromhex(line[4:]) for line in as_bytes if line.startswith("fed")], lines)
        self.assertIn('"playing":"all","animation":3', as_lines[3])
        self.assertIn('"playing":"all","animation":1', as_lines[7])


if __name__ == "__main__":
    unittest.main()

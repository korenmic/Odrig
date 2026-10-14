import json
import unittest

from . import support
from .test_commands import OK, refused
from .test_playback import T0, Playback
from .test_playlist import asked_at, show_of, three, told, with_a_cycle

CANVAS = (3, 2)


def frames(count, seed=1):
    """An animation of this many frames of 20 ms on the small canvas."""
    return support.clip(seed, *CANVAS, (20,) * count)


def animations(**files):
    """A file set on the small canvas: a show of these files, by their names without the
    ending, with the ids 1, 2 and so on in the order given."""
    items = [{"id": number, "file": f"{name}.odrg"} for number, name in enumerate(files, start=1)]
    return show_of(items, {f"{name}.odrg": content for name, content in files.items()})


def replies(printed):
    return [line[len("reply "):] for line in printed if line.startswith("reply ")]


class TheStart(unittest.TestCase):
    def test_the_start_opens_each_file_once_and_reads_no_frame_record(self):
        files = support.example_show()
        files["dense.odrg"] = support.dense_clip(60, 6, 2)
        names = ["hello.odrg", "dvd.odrg", "dense.odrg"]
        files["show.json"] = support.show_text([{"id": number, "file": name} for number, name in enumerate(names, start=1)])
        run = support.start(files, options=["--trace-files", "--trace-reads"], check_first=False)
        self.assertIsNone(run.error)
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], names)
        self.assertEqual([name for name, _ in run.taken if name.endswith(".odrg")], names)
        # The header is 16 bytes, and the core asks for a file in pieces of 512 bytes: one
        # piece, whatever the size of the file.
        for name, taken in run.taken:
            if name.endswith(".odrg"):
                self.assertGreater(len(files[name]), 1024)
                self.assertLessEqual(taken, 512, f"the start read {taken} of the {len(files[name])} bytes of {name}")

    def test_the_first_refresh_after_power_on_shows_the_first_picture(self):
        files = three()
        run = support.start(files, [f"poll {T0}", support.line(T0, "status")], check_first=False)
        self.assertEqual(run.lines, support.ReferencePlayer(files, check_first=False).run([f"poll {T0}", support.line(T0, "status")]))
        self.assertEqual(run.lines[0], f"refresh {T0}")
        self.assertTrue(any(bytes.fromhex(run.lines[1].split()[2])))
        state = json.loads(run.lines[2][len("reply "):])
        self.assertEqual((state["playing"], state["animation"], state["error"]), ("all", 1, None))


class TheCheck(Playback):
    def listed_after(self, files, times):
        """Asks for a refresh and then for the list at each of these times after power-on,
        on the core and on the reference player alike. Returns the number of the refresh
        after which the list is first given, counted from 1; none is refused after it."""
        script = []
        for time in times:
            script += [f"poll {T0 + time}", told(time, "list")]
        given = replies(self.assert_as_the_reference(files, script, check_first=False))
        self.assertEqual(len(given), len(times))
        busy = given.count(refused("busy"))
        self.assertEqual(given[:busy], [refused("busy")] * busy)
        self.assertLess(busy, len(given), "the check did not end")
        for reply in given[busy:]:
            self.assertTrue(json.loads(reply)["ok"])
        return busy + 1

    # The check takes no step at the first refresh and then, while each refresh follows the
    # one before it without a gap, 1, 2, 3 and so on to 16 steps at a refresh. A file of n
    # frames takes n + 2 steps.

    def test_a_file_of_ten_frames_is_read_at_the_sixth_refresh(self):
        # 12 steps: 0 + 1 + 2 + 3 + 4 = 10 after five refreshes, 15 after six.
        self.assertEqual(self.listed_after(animations(a=frames(10)), range(0, 300, 20)), 6)

    def test_the_files_are_read_one_after_another(self):
        # 5, 3 and 42 steps: 45 after ten refreshes, 55 after eleven.
        files = animations(a=frames(3, 1), b=frames(1, 2), c=frames(40, 3))
        self.assertEqual(self.listed_after(files, range(0, 400, 20)), 11)

    def test_a_file_that_two_items_name_is_read_once(self):
        files = animations(a=frames(10))
        files["show.json"] = json.dumps({"version": 1, "brightness": 255, "items": [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "a.odrg"}, {"id": 3, "cycle": [2, 1], "seconds": 5}]})
        self.assertEqual(self.listed_after(files, range(0, 300, 20)), 6)

    def test_it_takes_at_most_sixteen_steps_at_a_refresh(self):
        # 202 steps: 136 after seventeen refreshes, and sixteen more at each one after.
        self.assertEqual(self.listed_after(animations(a=frames(200)), range(0, 600, 20)), 22)

    def test_a_refresh_after_a_gap_takes_no_step_and_the_count_begins_again(self):
        # 12 steps. Three refreshes in a row take 0, 1 and 2. The one at 100 ms comes after
        # a gap and takes none; those after it take 1, 2, 3 and 4: 13 at the eighth.
        self.assertEqual(self.listed_after(animations(a=frames(10)), (0, 20, 40, 100, 120, 140, 160, 180, 200)), 8)

    def test_a_refresh_that_is_asked_for_late_inside_its_grid_time_is_no_gap(self):
        self.assertEqual(self.listed_after(animations(a=frames(10)), (0, 39, 41, 79, 80, 119, 139)), 6)

    def test_refreshes_that_never_follow_one_another_leave_the_check_where_it_is(self):
        script = []
        for time in range(0, 4000, 40):
            script += [f"poll {T0 + time}", told(time, "list")]
        given = replies(self.assert_as_the_reference(animations(a=frames(10)), script, check_first=False))
        self.assertEqual(set(given), {refused("busy")})

    def test_a_show_without_a_file_has_nothing_to_check(self):
        files = show_of([], {})
        given = replies(self.assert_as_the_reference(files, [told(0, "list")], check_first=False))
        self.assertEqual(given, ['{"ok":true,"items":[],"next":null}'])

    def test_the_list_then_has_the_bytes_of_every_file(self):
        files = animations(a=frames(3, 1), b=frames(7, 2))
        script = [f"poll {T0 + 20 * step}" for step in range(12)] + [told(240, "list")]
        listed = json.loads(replies(self.assert_as_the_reference(files, script, check_first=False))[-1])
        self.assertEqual([(item["file"], item["bytes"]) for item in listed["items"]], [("a.odrg", len(files["a.odrg"])), ("b.odrg", len(files["b.odrg"]))])

    def test_the_pictures_are_those_of_a_core_that_has_read_every_file(self):
        files = animations(a=frames(30, 1), b=frames(90, 2), c=frames(200, 3))
        files["show.json"] = json.dumps({"version": 1, "brightness": 255, "min_seconds": 1, "items": [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "file": "c.odrg"}]})
        script = [f"poll {T0 + 20 * step}" for step in range(600)]
        printed = self.assert_as_the_reference(files, script, check_first=False)
        self.assertEqual(printed, support.start(files, script).lines)


class Busy(Playback):
    NEW = frames(2, 9)

    def files(self):
        return animations(a=frames(10, 1), b=frames(10, 2))

    def asked(self, commands, files=None):
        """The replies to these commands at power-on, before any refresh."""
        files = files or self.files()
        return replies(self.assert_as_the_reference(files, [told(0, command) for command in commands], check_first=False))

    def test_list_remove_and_upload_begin_are_busy_while_the_files_are_being_read(self):
        commands = ["list", "list 2", "remove 2", f"upload begin 9 new.odrg {len(self.NEW)}", f"upload begin 1 a.odrg {len(self.NEW)}"]
        self.assertEqual(self.asked(commands), [refused("busy")] * len(commands))

    def test_they_work_once_every_file_is_read(self):
        # 24 steps, taken after eight refreshes.
        commands = ["list", "remove 2", f"upload begin 9 new.odrg {len(self.NEW)}", "upload cancel", "list"]
        script = [told(0, command) for command in commands[:3]]
        script += [f"poll {T0 + 20 * step}" for step in range(7)] + [told(120, "list")]
        script += [f"poll {T0 + 140}"] + [told(140, command) for command in commands]
        given = replies(self.assert_as_the_reference(self.files(), script, check_first=False))
        self.assertEqual(given[:4], [refused("busy")] * 4)
        self.assertEqual(len(json.loads(given[4])["items"]), 2)
        self.assertEqual(given[5:8], [OK, '{"ok":true,"chunk":1500}', OK])
        self.assertEqual(len(json.loads(given[8])["items"]), 1)

    def test_every_other_command_is_answered_while_the_files_are_being_read(self):
        commands = ["status", "space", "play 2", "play all", "off", "on", "brightness 9", "status"]
        given = self.asked(commands + ["list"])
        self.assertEqual(given[-1], refused("busy"))
        for command, reply in zip(commands, given):
            self.assertTrue(json.loads(reply)["ok"], command)
        self.assertEqual(given[:-1], replies(support.start(self.files(), [told(0, command) for command in commands]).lines))

    def test_without_an_upload_data_end_and_cancel_are_no_upload(self):
        commands = ["upload data 0 AAAA", "upload end 00000000", "upload cancel"]
        self.assertEqual(self.asked(commands), [refused("no-upload")] * 3)

    def test_a_code_that_stands_earlier_is_given_and_one_that_stands_later_is_not(self):
        earlier = ["list x", "list 1 2", "remove 0", "remove", "upload begin 9 new.odrg", "upload begin 0 new.odrg 5", "upload begin 9 NEW.odrg 5"]
        self.assertEqual(self.asked(earlier), [refused("bad-argument")] * len(earlier))
        # Without the check these are `unknown-id`, `in-use` and `no-space`.
        later = ["remove 77", "upload begin 9 a.odrg 50", "upload begin 9 new.odrg 4000000000"]
        self.assertEqual(self.asked(later), [refused("busy")] * len(later))

    def test_an_invalid_show_is_show_invalid(self):
        files = self.files()
        del files["b.odrg"]
        commands = ["list", "remove 2", f"upload begin 9 new.odrg {len(self.NEW)}"]
        self.assertEqual(self.asked(commands, files), [refused("show-invalid")] * 3)


class PlayedBeforeItsFileIsRead(Playback):
    """Refreshes that never follow one another in step leave the check where it is, so no
    file of these sessions is read by it: what the core knows of a length, it learned by
    playing."""

    def unread(self, files, script):
        """Runs a script on the core and on the reference player, with no file read at
        the start, and compares every line. The check has not ended when the script has:
        `list` is `busy`. And the lines are those of a core that has read every file."""
        last = max(int(line.split()[1]) for line in script)
        printed = self.assert_as_the_reference(files, [*script, support.line(last, "list")], check_first=False)
        self.assertEqual(printed[-1], f"reply {refused('busy')}")
        self.assertEqual(printed[:-1], support.start(files, script).lines)
        return printed[:-1]

    def animation_at(self, files, times, commands=()):
        """The animation `status` names at each of these times after power-on, with these
        `(time, command)` given on the way."""
        script = asked_at(times)
        for time, command in commands:
            at = next(index for index, line in enumerate(script) if int(line.split()[1]) >= T0 + time)
            script.insert(at, told(time, command))
        states = [json.loads(line[len("reply "):]) for line in self.unread(files, script) if line.startswith('reply {"ok":true,"on"')]
        self.assertEqual(len(states), len(times))
        return [state["animation"] for state in states]

    def turns(self, shown, step):
        """The animations in the order of their turns, each with the time its turn lasted,
        from what was shown at times one step apart. The last turn is cut by the end."""
        found = []
        for animation in shown:
            if found and found[-1][0] == animation:
                found[-1][1] += step
            else:
                found.append([animation, step])
        return [tuple(turn) for turn in found[:-1]]

    def test_the_playlist_gives_each_animation_its_turn(self):
        # Loops of 4, 10 and 45 seconds, and 30 seconds at least: 32, 30 and 45 seconds.
        shown = self.animation_at(three(), range(0, 150000, 500))
        self.assertEqual(self.turns(shown, 500), [(1, 32000), (2, 30000), (3, 45000), (1, 32000)])

    def test_with_repeat_a_turn_is_that_many_loops(self):
        shown = self.animation_at(three(first={"repeat": 2}, third={"repeat": 1}), range(0, 100000, 500))
        self.assertEqual(self.turns(shown, 500), [(1, 8000), (2, 30000), (3, 45000), (1, 8000)])

    def test_max_seconds_ends_a_turn_inside_the_first_loop_and_after_it(self):
        # 7 seconds of a loop of 45, whose end is never seen; 25 seconds of loops of 10.
        files = three(second={"max_seconds": 25}, third={"max_seconds": 7})
        shown = self.animation_at(files, range(0, 140000, 500))
        self.assertEqual(self.turns(shown, 500), [(1, 32000), (2, 25000), (3, 7000), (1, 32000), (2, 25000), (3, 7000)])

    def test_max_seconds_at_the_end_of_the_loop_and_one_frame_before_it(self):
        files = three(first={"max_seconds": 4}, second={"max_seconds": 9})
        shown = self.animation_at(files, range(0, 80000, 500))
        self.assertEqual(self.turns(shown, 500), [(1, 4000), (2, 9000), (3, 45000), (1, 4000), (2, 9000)])

    def test_a_jump_begins_the_turn_of_an_animation_that_was_never_shown(self):
        shown = self.animation_at(three(), range(0, 100000, 500), [(5000, "play 3"), (60000, "play 2")])
        self.assertEqual(self.turns(shown, 500), [(1, 5000), (3, 45000), (1, 10000), (2, 30000)])

    def test_a_cycle_shows_each_animation_from_the_start_of_its_turn(self):
        # Turns of two seconds, shorter than every loop.
        files = with_a_cycle(three(), {"id": 8, "cycle": [3, 1, 2], "seconds": 2}, start=8)
        shown = self.animation_at(files, range(0, 20000, 500))
        self.assertEqual(self.turns(shown, 500), [(3, 2000), (1, 2000), (2, 2000)] * 3)

    def test_a_cycle_whose_turns_are_longer_than_a_loop_plays_the_loop_again(self):
        files = with_a_cycle(three(), {"id": 8, "cycle": [1, 2], "seconds": 13}, start=8)
        shown = self.animation_at(files, range(0, 60000, 500))
        self.assertEqual(self.turns(shown, 500), [(1, 13000), (2, 13000), (1, 13000), (2, 13000)])

    def test_every_picture_of_frames_of_twenty_milliseconds(self):
        files = animations(a=frames(30, 1), b=frames(90, 2), c=frames(200, 3))
        files["show.json"] = json.dumps({"version": 1, "brightness": 255, "min_seconds": 2, "items": [{"id": 1, "file": "a.odrg", "repeat": 3}, {"id": 2, "file": "b.odrg", "max_seconds": 1}, {"id": 3, "file": "c.odrg"}]})
        self.unread(files, [f"poll {T0 + 40 * step}" for step in range(500)])

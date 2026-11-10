"""The plan: the turns the board has decided to play, the one on the LEDs and those it decides
ahead while planning is on, each with its start, its end, its animation and a widget's seed,
under a version that grows at every change."""

import json
import unittest

from . import support
from .test_clock_modes import mode_file
from .test_clocks import CANVAS, clock_of, show_of
from .test_drive import asked, replies
from .test_playback import T0

WINDOW = 86_400_000

# The board's folders `clocks` (number 1, id 20) and `clocks/message` (2, 21).
CLOCK_FOLDERS = "odrig-folders 1 3\n1 20 0 clocks\n2 21 0 clocks/message\n"


def loop_of(seconds, seed):
    """An animation of the canvas whose loop lasts this many seconds."""
    return support.clip(seed, *CANVAS, (1000,) * seconds)


def plans(run):
    return [reply for reply in replies(run) if "planning" in reply]


def states(run):
    return [reply for reply in replies(run) if "on" in reply and "planning" not in reply]


def widget_faces(items=None):
    """A show whose clocks play between its animations: two faces, clocks of their own in the
    board's folder `clocks`, and a message in `clocks/message`, after each clock."""
    items = items or [{"id": 1, "file": "four.odrg"}, {"id": 15, "file": "art.odrg"}]
    clocks = [{"id": 11, "file": "1/f1.odrg"}, {"id": 12, "file": "1/f2.odrg"}, {"id": 13, "file": "2/m1.odrg"}]
    files = {"four.odrg": loop_of(4, 1), "art.odrg": loop_of(4, 25), "1/f1.odrg": clock_of(seconds=3), "1/f2.odrg": clock_of(seconds=2),
             "2/m1.odrg": loop_of(1, 23)}
    source = show_of([*items, *clocks], files, min_seconds=4)
    source["folders.txt"] = CLOCK_FOLDERS
    source["clocks.txt"] = mode_file("between", True)
    return source


def session(source, script):
    return support.start(source, [f"poll {T0}", *script])


def at_starts(items, after=40):
    """A refresh and `status` just after the start of each item."""
    return [line for item in items for line in asked(item["start"] - T0 + after, "status")]


class TheReply(unittest.TestCase):
    def test_with_planning_off_it_holds_the_turn_on_the_leds_alone(self):
        source = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": loop_of(2, 1), "b.odrg": loop_of(3, 2)}, min_seconds=4)
        run = support.start(source, [f"poll {T0}", *asked(100, "plan")])
        (plan,) = plans(run)
        self.assertEqual(set(plan), {"ok", "planning", "version", "now", "on", "brightness", "rotation", "mini", "test", "snake", "items"})
        self.assertEqual((plan["planning"], plan["now"], plan["on"], plan["brightness"], plan["rotation"], plan["mini"], plan["test"], plan["snake"]),
                         (False, T0 + 100, True, 255, 0, False, False, None))
        self.assertGreaterEqual(plan["version"], 1)
        (item,) = plan["items"]
        self.assertEqual((item["start"], item["end"], item["id"], item["loop"]), (T0, T0 + 4000, 1, 2000))
        self.assertNotIn("from", item)
        self.assertNotIn("seed", item)

    def test_with_planning_on_it_holds_the_next_turns_and_each_plays_as_planned(self):
        source = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "file": "c.odrgx"}],
                         {"a.odrg": loop_of(2, 1), "b.odrg": loop_of(3, 2), "c.odrgx": clock_of(seconds=2)}, min_seconds=4)
        first = support.start(source, [f"poll {T0}", *asked(100, "plan on", "plan")])
        plan = plans(first)[0]
        self.assertTrue(plan["planning"])
        items = plan["items"]
        self.assertEqual(len(items), 8)
        self.assertEqual([item["id"] for item in items], [1, 2, 3] * 2 + [1, 2])
        for before, after in zip(items, items[1:]):
            self.assertEqual(before["end"], after["start"])
        self.assertEqual([item["end"] - item["start"] for item in items[:3]], [4000, 6000, 4000])
        self.assertEqual([("seed" in item) for item in items], [False, False, True] * 2 + [False, False])
        run = support.start(source, [f"poll {T0}", *asked(100, "plan on"), *at_starts(items)])
        played = [(state["animation"], state["seed"]) for state in states(run)]
        self.assertEqual(played, [(item["id"], item.get("seed")) for item in items])

    def test_a_break_pauses_a_long_turn_and_the_plan_says_where_it_goes_on(self):
        source = widget_faces([{"id": 1, "file": "four.odrg", "repeat": 90}])
        run = session(source, asked(200000, "plan on", "plan"))
        planned = plans(run)[0]["items"]
        paused, face, message, resumed = planned[:4]
        self.assertEqual((paused["id"], paused["start"], paused["end"]), (1, T0, T0 + 300000))
        self.assertIn(face["id"], (11, 12))
        self.assertIn("seed", face)
        self.assertEqual((face["start"], message["id"], message["start"]), (paused["end"], 13, face["end"]))
        self.assertEqual((resumed["id"], resumed["start"], resumed["from"]), (1, message["end"], 300000))
        check = session(source, [*asked(200000, "plan on"), *at_starts(planned[1:])])
        self.assertEqual([state["animation"] for state in states(check)], [item["id"] for item in planned[1:]])
        self.assertEqual(states(check)[0]["seed"], face["seed"])

    def test_the_breaks_of_the_clocks_are_planned_with_their_seeds(self):
        source = widget_faces()
        run = session(source, asked(100, "plan on", "plan"))
        items = plans(run)[0]["items"]
        faces = [item for item in items if item["id"] in (11, 12)]
        self.assertTrue(faces)
        self.assertTrue(all("seed" in item for item in faces))
        check = session(source, [*asked(100, "plan on"), *at_starts(items)])
        self.assertEqual([(state["animation"], state["seed"]) for state in states(check)], [(item["id"], item.get("seed")) for item in items])

    def test_a_cycle_gives_its_turns(self):
        source = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrgx"}, {"id": 5, "cycle": [1, 2], "seconds": 3}],
                         {"a.odrg": loop_of(2, 1), "b.odrgx": clock_of(seconds=2)})
        run = support.start(source, [f"poll {T0}", *asked(100, "play 5"), *asked(1100, "plan on", "plan")])
        items = plans(run)[0]["items"]
        self.assertEqual([item["id"] for item in items], [1, 2] * 4)
        self.assertEqual({item["end"] - item["start"] for item in items}, {3000})
        check = support.start(source, [f"poll {T0}", *asked(100, "play 5"), *asked(1100, "plan on"), *at_starts(items)])
        self.assertEqual([(state["animation"], state["seed"]) for state in states(check)], [(item["id"], item.get("seed")) for item in items])

    def test_it_stops_at_a_turn_whose_length_is_not_known(self):
        source = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": loop_of(2, 1), "b.odrg": loop_of(3, 2)})
        run = support.start(source, [support.line(T0, "plan on"), support.line(T0, "plan")], check_first=False)
        (item,) = plans(run)[0]["items"]
        self.assertEqual((item["id"], item["end"]), (1, None))
        self.assertNotIn("loop", item)

    def test_it_stops_at_the_turn_during_which_the_window_passes(self):
        source = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": loop_of(2, 1), "b.odrg": loop_of(3, 2)}, min_seconds=4)
        run = support.start(source, [f"poll {T0}", *asked(WINDOW - 9000, "plan on", "plan")])
        items = plans(run)[0]["items"]
        self.assertLess(len(items), 8)
        self.assertTrue(all(item["start"] < T0 + WINDOW for item in items))
        self.assertGreaterEqual(items[-1]["end"], T0 + WINDOW)

    def test_nothing_is_planned_while_a_test_shows_or_nothing_plays(self):
        show = {"version": 1, "brightness": 255, "items": [{"id": 1, "file": "a.odrg"}]}
        source = {"mapping.json": support.mapping_texts()["legs-20"], "show.json": json.dumps(show), "a.odrg": support.clip(1, 60, 60, (1000, 1000))}
        run = support.start(source, [f"poll {T0}", *asked(100, "mapping test on", "plan"), *asked(200, "mapping test off", "off", "plan")])
        test, off = plans(run)
        self.assertEqual((test["test"], test["items"]), (True, []))
        self.assertEqual((off["test"], off["on"], len(off["items"])), (False, False, 1))
        empty = support.start(show_of([], {}), [f"poll {T0}", *asked(100, "plan")])
        self.assertEqual(plans(empty)[0]["items"], [])

    def test_the_forms_and_the_room_of_a_reply(self):
        source = show_of([{"id": number, "file": f"f{number}.odrg"} for number in range(1, 9)],
                         {f"f{number}.odrg": loop_of(1, number) for number in range(1, 9)}, min_seconds=1)
        lines = ["plan since", "plan since x", "plan on now", "plan push", "plan maybe", "plan since 4294967296"]
        run = support.start(source, [f"poll {T0}", *asked(100, *lines), *asked(200, "plan on", "plan")])
        self.assertEqual(replies(run)[:len(lines)], [{"ok": False, "error": "bad-argument"}] * len(lines))
        printed = [line for line in run.lines if line.startswith('reply {"ok":true,"planning"')]
        self.assertTrue(all(len(line) - len("reply ") + 1 <= 1024 for line in printed))
        self.assertEqual(len(plans(run)[-1]["items"]), 8)


class Versions(unittest.TestCase):
    def source(self):
        return show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": loop_of(2, 1), "b.odrg": loop_of(3, 2)}, min_seconds=4)

    def test_a_reading_line_keeps_the_version_and_a_changing_one_makes_a_new_one(self):
        reading = ["status", "space", "fault", "list", "list in 9", "read 1 0", "saved 1", "catalog", "catalog page internal 0 0", "order get",
                   "mapping get", "rotation", "time", "schedule", "plan"]
        script = [f"poll {T0}", *asked(100, "plan"), *(support.line(T0 + 100, line) for line in reading), support.line(T0 + 100, "plan")]
        versions = [plan["version"] for plan in plans(support.start(self.source(), script))]
        self.assertEqual(len(versions), 3)
        self.assertEqual(set(versions), {versions[0]})
        for line in ("play 2", "brightness 9", "off", "plan on", "clocks on", "repeat 1 3", "nonsense"):
            with self.subTest(line=line):
                run = support.start(self.source(), [f"poll {T0}", *asked(100, "plan", line, "plan")])
                before, after = (plan["version"] for plan in plans(run))
                self.assertGreater(after, before)

    def test_since_answers_unchanged_with_the_version_it_is_given_and_the_plan_otherwise(self):
        run = support.start(self.source(), [f"poll {T0}", *asked(100, "plan")])
        version = plans(run)[0]["version"]
        script = [f"poll {T0}", *asked(100, f"plan since {version}", f"plan since {version + 1}", "play 2", f"plan since {version}")]
        same, other, _, changed = replies(support.start(self.source(), script))
        self.assertEqual(same, {"ok": True, "planning": False, "version": version, "now": T0 + 100, "unchanged": True})
        self.assertEqual(other["version"], version)
        self.assertIn("items", other)
        self.assertGreater(changed["version"], version)
        self.assertEqual(changed["items"][0]["id"], 2)

    def test_a_turn_that_ends_makes_a_new_version_and_a_refresh_within_a_turn_none(self):
        script = [f"poll {T0}", *asked(100, "plan"), *asked(2000, "plan"), *asked(4100, "plan")]
        first, within, after = (plan["version"] for plan in plans(support.start(self.source(), script)))
        self.assertEqual(within, first)
        self.assertGreater(after, within)


def given(run):
    """What a session's ways were given: each `#plan` line's plan, or None when none was due."""
    lines = []
    for line in run.lines:
        if line.startswith("planline "):
            rest = line[len("planline "):]
            if rest == "none":
                lines.append(None)
            else:
                assert rest.startswith("#plan "), rest
                lines.append(json.loads(rest[len("#plan "):]))
    return lines


class Push(unittest.TestCase):
    def source(self):
        return show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": loop_of(2, 1), "b.odrg": loop_of(3, 2)}, min_seconds=4)

    def test_no_way_has_a_push_and_a_way_of_1_to_8_has_one(self):
        at = T0 + 100
        script = [f"poll {T0}", *asked(100, "plan push on", "plan push off"), f"lineon 1 {at} plan push on", f"lineon 8 {at} plan push off",
                  f"lineon 0 {at} plan push on", f"lineon 9 {at} plan push on", f"lineon 1 {at} plan push", f"lineon 1 {at} status"]
        answers = replies(support.start(self.source(), script))
        unsupported = {"ok": False, "error": "unsupported"}
        self.assertEqual(answers[:6], [unsupported, unsupported, {"ok": True}, {"ok": True}, unsupported, unsupported])
        self.assertEqual(answers[6], {"ok": False, "error": "bad-argument"})
        self.assertEqual(answers[7]["playing"], "all")

    def test_a_way_is_given_the_plan_at_once_and_after_every_new_version(self):
        script = [f"poll {T0}", f"lineon 1 {T0 + 100} plan push on", f"planline 1 {T0 + 100}", f"planline 1 {T0 + 100}", f"planline 2 {T0 + 100}",
                  support.line(T0 + 200, "status"), f"planline 1 {T0 + 200}", support.line(T0 + 200, "play 2"), f"planline 1 {T0 + 200}",
                  *asked(4300, "status"), f"planline 1 {T0 + 4300}", f"planline 1 {T0 + 4300}"]
        first, again, other, unread, played, turned, after = given(support.start(self.source(), script))
        self.assertEqual((again, other, unread, after), (None, None, None, None))
        self.assertEqual(first["items"][0]["id"], 1)
        self.assertGreater(played["version"], first["version"])
        self.assertEqual(played["items"][0]["id"], 2)
        self.assertGreater(turned["version"], played["version"])

    def test_the_line_given_is_the_reply_of_plan(self):
        at = T0 + 300
        script = [f"poll {T0}", f"lineon 3 {at} plan push on", f"lineon 3 {at} plan on", f"planline 3 {at}", support.line(at, "plan")]
        run = support.start(self.source(), script)
        (line,) = given(run)
        self.assertEqual(line, plans(run)[-1])
        self.assertEqual(len(line["items"]), 8)

    def test_push_off_ends_it_on_its_way_alone(self):
        at = T0 + 100
        script = [f"poll {T0}", f"lineon 1 {at} plan push on", f"lineon 2 {at} plan push on", f"planline 1 {at}", f"planline 2 {at}",
                  f"lineon 1 {at} plan push off", support.line(at, "play 2"), f"planline 1 {at}", f"planline 2 {at}"]
        one, two, stopped, going = given(support.start(self.source(), script))
        self.assertIsNotNone(one)
        self.assertIsNotNone(two)
        self.assertIsNone(stopped)
        self.assertEqual(going["items"][0]["id"], 2)

    def test_the_bytes_of_a_way_carry_its_push(self):
        at = T0 + 100
        script = [f"poll {T0}", f"byteson 4 {at} {b'plan push on'.hex()}0a", f"planline 4 {at}", f"bytes {at} {b'plan push on'.hex()}0a"]
        run = support.start(self.source(), script)
        answers = replies(run)
        self.assertEqual(answers, [{"ok": True}, {"ok": False, "error": "unsupported"}])
        self.assertEqual(len(given(run)), 1)
        self.assertIsNotNone(given(run)[0])


class Draws(unittest.TestCase):
    def test_while_planning_is_on_a_seed_is_the_same_however_the_refreshes_come(self):
        source = show_of([{"id": 1, "file": "a.odrg"}, {"id": 3, "file": "c.odrgx"}], {"a.odrg": loop_of(2, 1), "c.odrgx": clock_of(seconds=2)}, min_seconds=4)
        steady = [f"poll {T0 + 20 * step}" for step in range(1, 260)]
        seeds = []
        for polls in ([], steady):
            run = support.start(source, [f"poll {T0}", support.line(T0, "plan on"), *polls, *asked(5000, "status")])
            seeds.append(states(run)[-1]["seed"])
        self.assertEqual(seeds[0], seeds[1])


if __name__ == "__main__":
    unittest.main()

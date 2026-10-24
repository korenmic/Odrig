import json
import re
import struct
import unittest

from odrig import odrgx

from . import support
from .test_content import animation, small_show
from .test_playback import T0, Playback, refreshes
from .test_upload import Script, Uploads, bad_file

WIDGETS = support.ROOT / "tests" / "vectors" / "widgets"
CANVAS = (20, 10)
ANALOG, DIGITAL, MELTING = 1, 2, 3


def clock_of(widget=ANALOG, seconds=2, canvas=CANVAS, least=60, greatest=600):
    """The container of a clock, with the colours of the vectors."""
    payload = struct.pack("<BBH3s3s3s3sHH", widget, 0, seconds, bytes.fromhex("f4ecd0"), bytes.fromhex("202020"),
                          bytes.fromhex("d4a017"), bytes.fromhex("000000"), least, greatest)
    return odrgx.wrap(3, *canvas, 1000 * seconds, payload)


def reasons_of_a_widget():
    text = (support.ROOT / "docs" / "reasons.md").read_text(encoding="utf-8")
    section = text.split("\n## Widgets in ODRGX\n")[1].split("\n## ")[0]
    return set(re.findall(r"(?m)^\| `([a-z0-9-]+)` \|", section))


def show_of(items, files, **more):
    show = {"version": 1, "brightness": 255, "items": list(items), **more}
    return {"mapping.json": support.one_leg_mapping(*CANVAS), "show.json": json.dumps(show), **files}


def statuses(printed):
    return [json.loads(line[len("reply "):]) for line in printed if line.startswith('reply {"ok":true,"on"')]


def polls_and_status(times):
    script = []
    for time in times:
        script += [f"poll {T0 + time}", support.line(T0 + time, "status")]
    return script


class TheVectors(unittest.TestCase):
    def test_a_valid_clock_is_read_whole_with_its_seconds_as_its_loop(self):
        paths = sorted((WIDGETS / "valid").glob("*.odrgx"))
        self.assertGreaterEqual(len(paths), 4)
        for path, decoded in zip(paths, support.decode_each([path.read_bytes() for path in paths])):
            with self.subTest(vector=path.name):
                seconds = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))["seconds"]
                self.assertIsNone(decoded.reason)
                self.assertEqual(decoded.container, (3, 1000 * seconds, 20))
                self.assertEqual(list(decoded.records), [])

    def test_an_invalid_clock_is_refused_with_the_reason_of_its_name(self):
        paths = sorted((WIDGETS / "invalid").glob("*.odrgx"))
        self.assertGreaterEqual(len(paths), 14)
        for path, decoded in zip(paths, support.decode_each([path.read_bytes() for path in paths])):
            with self.subTest(vector=path.name):
                self.assertEqual(decoded.reason, path.name.split(".")[0])

    def test_the_core_has_every_reason_of_a_widget(self):
        self.assertIn("unknown-widget", reasons_of_a_widget())
        self.assertLessEqual(reasons_of_a_widget(), set(support.host_lines("reasons")))

    def test_a_seed_gives_the_same_pictures_again_and_another_seed_others(self):
        for widget in (ANALOG, DIGITAL, MELTING):
            with self.subTest(widget=widget):
                data = clock_of(widget, canvas=(60, 60))
                times = [0, 1000, 10000, 20000]
                self.assertEqual(support.rendered(data, times, 7), support.rendered(data, times, 7))
                self.assertNotEqual(support.rendered(data, times, 7), support.rendered(data, times, 8))


class ClocksInAShow(Playback):
    def test_a_turn_keeps_its_seed_through_its_loops_and_the_next_turn_gets_another(self):
        files = show_of([{"id": 1, "file": "a.odrgx"}], {"a.odrgx": clock_of(seconds=2)}, min_seconds=3)
        printed = self.assert_as_the_reference(files, [f"poll {T0}"] + polls_and_status([0, 20, 1980, 2000, 3980, 4000, 4020, 8000]))
        seeds = [state["seed"] for state in statuses(printed)]
        self.assertTrue(all(isinstance(seed, int) and seed > 0 for seed in seeds))
        self.assertEqual(len(set(seeds[:5])), 1)
        self.assertEqual(seeds[5], seeds[6])
        self.assertEqual(len({seeds[0], seeds[5], seeds[7]}), 3)

    def test_play_gives_a_new_seed_at_the_first_refresh_and_none_before_it(self):
        files = show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": clock_of(), "b.odrg": support.clip(1, *CANVAS, (1000,))})
        script = [f"poll {T0}", support.line(T0, "status"), support.line(T0 + 500, "play 1"), support.line(T0 + 500, "status"),
                  f"poll {T0 + 520}", support.line(T0 + 520, "status"), support.line(T0 + 530, "list"), support.line(T0 + 530, "status"),
                  f"poll {T0 + 540}", support.line(T0 + 540, "status")]
        seeds = [state["seed"] for state in statuses(self.assert_as_the_reference(files, script))]
        self.assertIsNone(seeds[1])
        self.assertNotEqual(seeds[2], seeds[0])
        self.assertEqual(seeds[2:], [seeds[2]] * 3)

    def test_no_seed_while_frames_or_nothing_play(self):
        files = show_of([{"id": 2, "file": "b.odrg"}, {"id": 1, "file": "a.odrgx"}], {"a.odrgx": clock_of(), "b.odrg": support.clip(1, *CANVAS, (1000,))}, min_seconds=1)
        printed = self.assert_as_the_reference(files, [f"poll {T0}"] + polls_and_status([0, 980, 1000, 3000]))
        self.assertEqual([(state["animation"], state["seed"] is None) for state in statuses(printed)], [(2, True), (2, True), (1, False), (2, True)])

    def test_the_pictures_follow_the_time_of_the_turn_however_the_refreshes_come(self):
        files = show_of([{"id": 1, "file": "a.odrgx"}], {"a.odrgx": clock_of(MELTING, seconds=30)})
        late = [f"poll {T0}", f"poll {T0 + 1337}", f"poll {T0 + 5013}", support.line(T0 + 5013, "status"), f"poll {T0 + 9000}"]
        steady = [f"poll {T0 + 20 * step}" for step in range(251)] + [support.line(T0 + 5013, "status")]
        steady += [f"poll {T0 + 5020 + 20 * step}" for step in range(200)]
        first = self.assert_as_the_reference(files, late)
        second = self.assert_as_the_reference(files, steady)
        # The seed is chosen at the first refresh, from the polls before it, which the two
        # runs share; afterwards only the time of the turn counts.
        self.assertEqual(statuses(first)[0]["seed"], statuses(second)[0]["seed"])
        at_9000 = [refreshes([line for line in printed if not line.startswith("reply")])[0][-1] for printed in (first, second)]
        self.assertEqual(at_9000[0][0], T0 + 9000)
        self.assertEqual(at_9000[0], at_9000[1])

    def test_a_clock_has_the_loops_of_its_seconds_and_a_longest_time_cuts_its_turn(self):
        files = show_of([{"id": 1, "file": "a.odrgx", "max_seconds": 3}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": clock_of(seconds=2), "b.odrg": support.clip(1, *CANVAS, (1000,))}, min_seconds=5)
        printed = self.assert_as_the_reference(files, [f"poll {T0}"] + polls_and_status([0, 2980, 3000, 3980, 4000, 7980, 8000]))
        self.assertEqual([state["animation"] for state in statuses(printed)], [1, 1, 2, 2, 2, 2, 1])

    def test_a_cycle_gives_a_clock_its_seconds(self):
        files = show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "cycle": [1, 2], "seconds": 1}], {"a.odrgx": clock_of(seconds=2), "b.odrg": support.clip(1, *CANVAS, (1000,))}, start=3)
        printed = self.assert_as_the_reference(files, [f"poll {T0}"] + polls_and_status([0, 980, 1000, 2000, 2020]))
        states = statuses(printed)
        self.assertEqual([state["animation"] for state in states], [1, 1, 2, 1, 1])
        self.assertNotEqual(states[0]["seed"], states[3]["seed"])

    def test_list_gives_a_clock_its_type(self):
        files = show_of([{"id": 1, "file": "a.odrgx"}], {"a.odrgx": clock_of()})
        items = json.loads(support.start(files, [f"poll {T0}", support.line(T0, "list")]).lines[-1][len("reply "):])["items"]
        self.assertEqual(items[0]["type"], "widget")

    def test_a_clock_of_another_canvas_or_with_a_fault_is_refused_at_the_start(self):
        cases = {
            "error size-mismatch a.odrgx": clock_of(canvas=(21, 10)),
            "error file-malformed a.odrgx unknown-widget": clock_of(widget=4),
            "error file-malformed a.odrgx bad-settings": clock_of(least=601),
            "error file-malformed a.odrgx loop-mismatch": bytes(clock_of()[:12]) + struct.pack("<I", 1999) + bytes(clock_of()[16:]),
        }
        for error, data in cases.items():
            with self.subTest(error=error):
                self.assertEqual(support.start(show_of([{"id": 1, "file": "a.odrgx"}], {"a.odrgx": data}), ["error"]).lines, [error])


class UploadsOfClocks(Uploads):
    def test_a_clock_is_uploaded_listed_with_its_type_and_played(self):
        files = small_show([animation(1, "one.odrg")])
        clock = clock_of(DIGITAL, canvas=(60, 6))
        script = Script().polls(10).upload(7, "clock.odrgx", clock).line("list", "play 7", "status").polls(10).line("status")
        given = self.play(files, script)
        self.assertEqual(given[2], '{"ok":true}')
        self.assertEqual(json.loads(given[3])["items"][-1], {"id": 7, "file": "clock.odrgx", "bytes": len(clock), "ignored": False, "type": "widget"})
        self.assertIsNone(json.loads(given[5])["seed"])
        self.assertEqual(json.loads(given[6])["animation"], 7)
        self.assertIsInstance(json.loads(given[6])["seed"], int)

    def test_an_invalid_clock_is_refused_with_its_reason(self):
        files = small_show([animation(1, "one.odrg")])
        for reason, data in (("unknown-widget", clock_of(0, canvas=(60, 6))), ("bad-settings", clock_of(seconds=0, canvas=(60, 6))),
                             ("size-mismatch", clock_of(canvas=(59, 6)))):
            with self.subTest(reason=reason):
                given = self.play(files, Script().polls(5).upload(7, "new.odrgx", data))
                self.assertEqual(given[-1], bad_file(reason))

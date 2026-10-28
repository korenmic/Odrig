import json
import re
import struct
import unittest

from odrig import odrgx

from . import support
from .test_content import animation, small_show
from .test_drive import DONE, asked, logged, refusal, replies
from .test_playback import T0, Playback, refreshes
from .test_playlist import three
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


def statuses_and_lists(lines):
    """The replies of a session, as values."""
    return [json.loads(line[len("reply "):]) for line in lines if line.startswith("reply ")]


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

    def test_a_clock_of_another_canvas_or_with_a_fault_is_quarantined_at_the_start(self):
        cases = {
            "size-mismatch": clock_of(canvas=(21, 10)),
            "unknown-widget": clock_of(widget=6),
            "bad-settings": clock_of(least=601),
            "loop-mismatch": bytes(clock_of()[:12]) + struct.pack("<I", 1999) + bytes(clock_of()[16:]),
        }
        for reason, data in cases.items():
            with self.subTest(reason=reason):
                files = show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": data, "b.odrg": support.clip(1, *CANVAS, (1000,))})
                run = support.start(files, ["error", f"poll {T0}", support.line(T0, "list"), support.line(T0, "status")])
                self.assertEqual(run.lines[0], "error none")
                self.assertIn(f"file a.odrgx unavailable: {reason}", run.logs)
                listed, status = statuses_and_lists(run.lines)
                self.assertEqual(listed["items"][0]["fault"], reason)
                self.assertEqual((status["animation"], status["seed"]), (2, None))


class UploadsOfClocks(Uploads):
    def test_a_clock_is_uploaded_listed_with_its_type_and_played(self):
        files = small_show([animation(1, "one.odrg")])
        clock = clock_of(DIGITAL, canvas=(60, 6))
        script = Script().polls(10).upload(7, "clock.odrgx", clock).line("list", "play 7", "status").polls(10).line("status")
        given = self.play(files, script)
        self.assertEqual(given[2], '{"ok":true}')
        self.assertEqual(json.loads(given[3])["items"][-1], {"id": 7, "file": "clock.odrgx", "bytes": len(clock), "ignored": False, "external": False, "type": "widget"})
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


SETTINGS = ["clocks on", "clocks off", "clocks message on", "clocks message off"]


def clocks_file(clocks, message):
    return f"odrig-clocks 1\nclocks {clocks}\nmessage {message}\n".encode("ascii")


def settings_of(run):
    """The two settings each `status` of a session reports."""
    return [(state["clocks"], state["clock_message"]) for state in replies(run) if "on" in state]


def answers_of(run):
    """The replies of a session that are no `status`."""
    return [reply for reply in replies(run) if "on" not in reply]


class TheSettings(Playback):
    BAD = ["clocks", "clocks x", "clocks on x", "clocks  on", "clocks On", "clocks message", "clocks message x", "clocks message on x", "clocks messages on", "clocks off message",
           "clocks on message"]

    def test_words_out_of_the_four_lines_are_refused_first_and_an_invalid_show_next(self):
        invalid = support.with_show_fault(three())
        for files in (three(), invalid):
            printed = self.assert_as_the_reference(files, [f"poll {T0}"] + asked(100, *self.BAD))
            self.assertEqual([json.loads(line[len("reply "):]) for line in printed if line.startswith("reply ")], [refusal("bad-argument")] * len(self.BAD))
        run = support.start(invalid, [f"poll {T0}"] + asked(100, *SETTINGS))
        self.assertEqual(replies(run), [refusal("show-invalid")] * 4)

    def test_busy_until_the_check_after_the_start_ends_and_while_an_upload_is_open(self):
        script = [support.line(T0, "clocks on"), support.line(T0, "status")]
        printed = self.assert_as_the_reference(three(), script, check_first=False)
        self.assertEqual(printed[0], 'reply {"ok":false,"error":"busy"}')
        script = [f"poll {T0}"] + asked(100, "upload begin 9 new.odrg 100", "clocks message on", "upload cancel", "clocks message on", "status")
        run = support.start(three(), script)
        self.assertEqual(answers_of(run)[1:], [refusal("busy"), DONE, DONE])
        self.assertEqual(settings_of(run), [(False, True)])

    def test_each_line_is_saved_and_reported_and_kept_across_a_restart(self):
        script = [f"poll {T0}"] + asked(100, "status", "clocks on", "status", "clocks message on", "status", "clocks off", "status")
        self.assert_as_the_reference(three(), script)
        run, kept = support.start_and_keep(three(), script)
        self.assertEqual(answers_of(run), [DONE] * 3)
        self.assertEqual(settings_of(run), [(False, False), (True, False), (True, True), (False, True)])
        self.assertEqual(kept["clocks.txt"], clocks_file("off", "on"))
        restarted = support.start({**three(), "clocks.txt": kept["clocks.txt"]}, asked(0, "status"))
        self.assertEqual(settings_of(restarted), [(False, True)])

    def test_a_setting_in_force_writes_nothing(self):
        run, kept = support.start_and_keep(three(), [f"poll {T0}"] + asked(100, "clocks off", "clocks message off"), ["--trace-store"])
        self.assertEqual(answers_of(run), [DONE] * 2)
        self.assertFalse(any(line.startswith("store ") for line in run.lines))
        self.assertNotIn("clocks.txt", kept)
        files = {**three(), "clocks.txt": clocks_file("on", "off")}
        run = support.start(files, [f"poll {T0}"] + asked(100, "clocks on", "clocks message off"), ["--trace-store"])
        self.assertFalse(any(line.startswith("store ") for line in run.lines))

    def test_the_file_is_read_whole_and_strictly(self):
        for clocks in ("on", "off"):
            for message in ("on", "off"):
                run = support.start({**three(), "clocks.txt": clocks_file(clocks, message)}, asked(0, "status"))
                self.assertEqual(settings_of(run), [(clocks == "on", message == "on")])
                self.assertNotIn("clocks unreadable", logged(run))
        whole = clocks_file("on", "on")
        for data in (b"", whole[:-1], whole + b"\n", whole.replace(b"\n", b"\r\n"), whole.replace(b" 1", b" 2"), b"odrig-clocks 1\nmessage on\nclocks on\n",
                     b"odrig-clocks 1\nclocks yes\nmessage on\n", whole + b"x" * 60, b"odrig-clocks 1\nclocks on\n"):
            with self.subTest(data=data):
                files = {**three(), "clocks.txt": data}
                run, kept = support.start_and_keep(files, asked(0, "status", "clocks message on", "status"))
                self.assertEqual(logged(run).count("clocks unreadable"), 1)
                self.assertEqual(list(run.logs), support.ReferencePlayer(files).start_logs)
                self.assertEqual(settings_of(run), [(False, False), (False, True)])
                self.assertEqual(kept["clocks.txt"], clocks_file("off", "on"))

    def test_a_part_left_by_a_cut_is_removed_at_the_start(self):
        run, kept = support.start_and_keep({**three(), "clocks.part": clocks_file("on", "on")}, asked(0, "status"))
        self.assertNotIn("clocks.part", kept)
        self.assertEqual(settings_of(run), [(False, False)])

    def test_a_failed_call_says_storage_error_and_changes_nothing(self):
        files = {**three(), "clocks.txt": clocks_file("off", "on")}
        script = [f"poll {T0}"] + asked(1000, "clocks on", "status")
        observed = support.start(files, script, ["--trace-store"])
        first = len(observed.stored) + 1
        calls = sum(line.startswith("store ") for line in observed.lines)
        self.assertGreaterEqual(calls, 4)
        for at in range(first, first + calls):
            with self.subTest(at=at):
                run, kept = support.start_and_keep(files, script, ["--store-fails-at", str(at)])
                self.assertEqual(answers_of(run), [refusal("storage-error")])
                self.assertEqual(settings_of(run), [(False, True)])
                self.assertEqual(kept["clocks.txt"], files["clocks.txt"])
                self.assertNotIn("clocks.part", kept)

    def test_a_cut_at_any_call_leaves_the_old_settings_or_the_new(self):
        files = {**three(), "clocks.txt": clocks_file("off", "on")}
        script = [f"poll {T0}"] + asked(1000, "clocks on")
        observed = support.start(files, script, ["--trace-store"])
        first = len(observed.stored) + 1
        calls = sum(line.startswith("store ") for line in observed.lines)
        for at in range(first, first + calls):
            for keeps in (0, 1):
                with self.subTest(at=at, keeps=keeps):
                    _, left = support.start_and_keep(files, script, ["--cut-at", str(at), "--cut-keeps", str(keeps)], status=75)
                    recovered, settled = support.start_and_keep(left, asked(0, "status"))
                    self.assertIn(settings_of(recovered)[0], [(False, True), (True, True)])
                    self.assertNotIn("clocks unreadable", logged(recovered))
                    self.assertNotIn("clocks.part", settled)

    def test_a_host_whose_storage_cannot_be_changed_says_storage_error(self):
        files = {**three(), "clocks.txt": clocks_file("on", "on")}
        run = support.start(files, [f"poll {T0}"] + asked(100, "status", "clocks on", "clocks off", "status"), ["--no-storage"])
        self.assertEqual(answers_of(run), [refusal("storage-error")] * 2)
        self.assertEqual(settings_of(run), [(False, False)] * 2)

    def test_the_members_stand_before_left_which_stays_last(self):
        run = support.start(three(), asked(0, "status"))
        self.assertEqual(list(replies(run)[0])[-3:], ["clocks", "clock_message", "left"])

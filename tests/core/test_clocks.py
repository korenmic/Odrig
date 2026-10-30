import json
import re
import struct
import unittest

from odrig import odrgx

from . import support
from .test_content import animation, small_show
from .test_catalog_drive import card
from .test_drive import DONE, a_drive, asked, logged, pictures, refusal, replies, with_drive
from .test_playback import T0, Playback, refreshes
from .test_playlist import loop_of, three
from .test_playlist import show_of as plain_show_of
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
            "unknown-widget": clock_of(widget=7),
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


# A card with two animations of 4 seconds at its root, three clocks of 6 seconds, two loops
# of 3 by the show's `min_seconds` of 4, and the message of 1 second. Its ids, by the walk:
# `a.odrg` 60001, `b.odrg` 60002, the clocks 60003 to 60005, the message 60006, the folder
# `clocks` 60007 and `clocks/message` 60008.
SHOW4 = plain_show_of([{"id": 1, "file": "four.odrg"}], {"four.odrg": loop_of(4, 1)}, min_seconds=4)
CLOCKS = {"clocks/c1.odrg": loop_of(3, 7), "clocks/c2.odrg": loop_of(3, 8), "clocks/c3.odrg": loop_of(3, 9), "clocks/message/m.odrg": loop_of(1, 10)}
CARD = {"a.odrg": loop_of(4, 5), "b.odrg": loop_of(4, 6), **CLOCKS}
CLOCK_FILES = {"clocks/c1.odrg", "clocks/c2.odrg", "clocks/c3.odrg"}
MESSAGE = "clocks/message/m.odrg"


def with_clocks(files, clocks="on", message="on"):
    return {**files, "clocks.txt": clocks_file(clocks, message)}


def on_card(files, card_files, script):
    """A session from a refresh at power-on, with a card of these files."""
    return with_drive(files, card_files, [f"poll {T0}"] + list(script))


def at_times(*times):
    """A refresh and `status` at each of these times after power-on."""
    return [line for time in times for line in asked(time, "status")]


def files_of(run):
    """The file each `status` of a session names, `clock` for any of the three clocks."""
    return ["clock" if state["file"] in CLOCK_FILES else state["file"] for state in replies(run) if "on" in state]


def states_of(run):
    return [state for state in replies(run) if "on" in state]


class TheClocksFolders(unittest.TestCase):
    def test_the_card_has_the_ids_of_the_walk(self):
        reply = replies(on_card(SHOW4, CARD, asked(0, "list in 60007", "list in 60008")))
        self.assertEqual([(item["id"], item.get("file", item.get("playlist"))) for item in reply[0]["items"]],
                         [(60008, "clocks/message"), (60003, "clocks/c1.odrg"), (60004, "clocks/c2.odrg"), (60005, "clocks/c3.odrg")])
        self.assertEqual([(item["id"], item["file"]) for item in reply[1]["items"]], [(60006, MESSAGE)])

    def test_while_the_clocks_are_off_they_are_files_of_the_card_like_any_other(self):
        run = on_card(with_clocks(SHOW4, "off"), CARD, at_times(1000, 5000, 9000, 13000, 19000, 25000, 31000, 35000))
        self.assertEqual([state["file"] for state in states_of(run)],
                         ["four.odrg", "a.odrg", "b.odrg", "clocks/c1.odrg", "clocks/c2.odrg", "clocks/c3.odrg", MESSAGE, "four.odrg"])

    def test_while_they_are_on_every_playlist_passes_over_their_folders(self):
        run = on_card(with_clocks(SHOW4), CARD, at_times(1000, 5000, 9000, 13000, 17000))
        self.assertEqual(files_of(run), ["four.odrg", "a.odrg", "b.odrg", "four.odrg", "a.odrg"])
        # A clock played by its id is a jump, after which the playlist passes over the rest;
        # the folder `clocks` made current has nothing to play, and the root plays in its place.
        script = asked(1000, "play 60004") + at_times(1020, 7000, 7100) + asked(8000, "play 60007", "status") + at_times(9000) + asked(10000, "play 60008", "status")
        states = states_of(on_card(with_clocks(SHOW4), CARD, script))
        self.assertEqual([state["file"] for state in states], ["clocks/c2.odrg", "clocks/c2.odrg", "four.odrg", "four.odrg", "four.odrg", "four.odrg"])
        self.assertEqual([state["playing"] for state in states][3:], [60007, 60007, 60008])


class ABreak(unittest.TestCase):
    TIMES = (1000, 5000, 9000, 13000, 17000, 21000, 25500, 26500, 27500, 31500, 35500, 39500, 43500, 47500, 53500, 54500)

    def test_a_clock_comes_after_5_turns_and_the_message_once_after_it(self):
        run = on_card(with_clocks(SHOW4), CARD, at_times(*self.TIMES))
        self.assertEqual(files_of(run), ["four.odrg", "a.odrg", "b.odrg", "four.odrg", "a.odrg", "clock", "clock", MESSAGE, "b.odrg", "four.odrg", "a.odrg", "b.odrg",
                                         "four.odrg", "clock", MESSAGE, "a.odrg"])
        states = states_of(run)
        self.assertEqual(states[5]["file"], states[6]["file"])
        self.assertEqual([(state["playing"], state["repeat"], state["loop"]) for state in states[5:8]], [("all", 2, 1), ("all", 2, 2), ("all", 1, 1)])
        self.assertEqual(states[7]["animation"], 60006)

    def test_without_the_message_the_playlist_goes_on_after_the_clock(self):
        run = on_card(with_clocks(SHOW4, message="off"), CARD, at_times(21000, 26500, 30500))
        self.assertEqual(files_of(run), ["clock", "b.odrg", "four.odrg"])

    def test_a_card_with_a_catalog_has_its_breaks_where_one_without_has_them(self):
        times = (1000, 5000, 9000, 13000, 17000, 21000, 26500, 27500)
        with a_drive(card(CARD)) as top:
            run = support.start(with_clocks(SHOW4), [f"poll {T0}"] + at_times(*times), ["--drive", top])
        self.assertEqual(files_of(run), ["four.odrg", "a.odrg", "b.odrg", "four.odrg", "a.odrg", "clock", MESSAGE, "b.odrg"])

    def test_with_no_clock_that_plays_nothing_plays_in_its_place(self):
        card_files = {"a.odrg": loop_of(4, 5), "b.odrg": loop_of(4, 6)}
        script = [f"poll {T0 + step}" for step in range(0, 60000, 500)]
        self.assertEqual(pictures(on_card(with_clocks(SHOW4), card_files, script)), pictures(on_card(SHOW4, card_files, script)))

    def test_the_order_has_each_clock_once_before_a_new_one_is_drawn(self):
        # Turns of 1 second and clocks of 5: a break of 5 seconds every 10.
        show = plain_show_of([{"id": 1, "file": "one.odrg"}], {"one.odrg": loop_of(1, 1)}, min_seconds=1)
        clocks = {"clocks/c1.odrg": loop_of(5, 7), "clocks/c2.odrg": loop_of(5, 8), "clocks/c3.odrg": loop_of(5, 9)}
        for first in (0, 7, 13):
            with self.subTest(first=first):
                script = [f"poll {T0 + first}"] + at_times(*(5500 + 10000 * k for k in range(6)))
                played = [state["file"] for state in states_of(with_drive(with_clocks(show, message="off"), clocks, script))]
                self.assertEqual(sorted(played[:3]), sorted(CLOCK_FILES))
                self.assertEqual(sorted(played[3:]), sorted(CLOCK_FILES))


class APause(unittest.TestCase):
    def test_5_minutes_in_a_turn_pause_it_and_it_goes_on_after_the_break_at_its_frame_and_count(self):
        show = plain_show_of([{"id": 1, "file": "long.odrg"}], {"long.odrg": loop_of(45, 3)}, min_seconds=4)
        script = asked(1000, "repeat 1 9") + at_times(299000, 301000, 306500, 308000, 411000, 413000)
        states = states_of(on_card(with_clocks(show), CLOCKS, script))
        self.assertEqual(["clock" if state["file"] in CLOCK_FILES else state["file"] for state in states], ["long.odrg", "clock", MESSAGE, "long.odrg", "long.odrg", "long.odrg"])
        self.assertEqual([(state["repeat"], state["loop"]) for state in states], [(9, 7), (2, 1), (1, 1), (9, 7), (9, 9), (1, 1)])
        # The picture 1 second after the break is the turn's at 301 seconds.
        resumed = pictures(on_card(with_clocks(show), CLOCKS, asked(1000, "repeat 1 9") + [f"poll {T0 + 308000}"]))[-1]
        straight = pictures(on_card(show, CLOCKS, asked(1000, "repeat 1 9") + [f"poll {T0 + 301000}"]))[-1]
        self.assertEqual(resumed, straight)

    def test_a_clock_of_the_show_keeps_its_seed_through_the_break(self):
        clock_files = {f"clocks/c{n}.odrg": support.clip(n, *CANVAS, (1000,) * 3) for n in (1, 2, 3)}
        files = show_of([{"id": 1, "file": "clock.odrgx"}], {"clock.odrgx": clock_of(ANALOG, seconds=60)}, min_seconds=4)
        script = asked(1000, "repeat 1 6") + at_times(299000, 301000, 308000)
        before, during, after = states_of(on_card(with_clocks(files, message="off"), clock_files, script))
        self.assertEqual((before["animation"], after["animation"]), (1, 1))
        self.assertIn(during["file"], CLOCK_FILES)
        self.assertIsInstance(before["seed"], int)
        self.assertEqual(after["seed"], before["seed"])
        self.assertEqual((after["repeat"], after["loop"]), (6, 6))


class CommandsDuringABreak(unittest.TestCase):
    def run_at_21(self, *commands, files=None, more=(), message="on"):
        script = at_times(1000, 5000, 9000, 13000, 17000) + asked(21000, *commands) + list(more)
        return on_card(with_clocks(files or SHOW4, message=message), CARD, script)

    def test_a_play_cuts_it_and_resumes_nothing(self):
        run = self.run_at_21("play 60001", "status", more=at_times(21020, 24000, 26000))
        self.assertEqual(files_of(run)[5:], ["a.odrg", "a.odrg", "a.odrg", "b.odrg"])

    def test_clocks_off_lets_it_end_with_its_message_and_none_begins_after_it(self):
        # The folder is the card's again: the walk goes on from `b.odrg` into it.
        run = self.run_at_21("clocks off", more=at_times(26500, 27500, 31500, 37500, 43500, 49500))
        self.assertEqual([state["file"] for state in states_of(run)][5:], [MESSAGE, "b.odrg", "clocks/c1.odrg", "clocks/c2.odrg", "clocks/c3.odrg", MESSAGE])

    def test_the_message_switched_off_still_follows_this_clock_and_switched_on_follows_it_too(self):
        run = self.run_at_21("clocks message off", more=at_times(26500, 47500, 53500))
        self.assertEqual(files_of(run)[5:], [MESSAGE, "clock", "a.odrg"])
        run = self.run_at_21("clocks message on", message="off", more=at_times(26500, 27500))
        self.assertEqual(files_of(run)[5:], [MESSAGE, "b.odrg"])

    def test_on_off_brightness_and_list_change_nothing_of_it(self):
        run = self.run_at_21("status", "off", "brightness 10", "list", "on", more=at_times(25500, 26500, 27500))
        states = states_of(run)[5:]
        self.assertEqual(states[0]["file"], states[1]["file"])
        self.assertEqual(files_of(run)[5:], ["clock", "clock", MESSAGE, "b.odrg"])

    def test_repeat_acts_on_the_clocks_turn(self):
        clock = states_of(self.run_at_21("status"))[5]["animation"]
        run = self.run_at_21("status", f"repeat {clock} 3", more=at_times(28500, 29500))
        self.assertEqual([(state["animation"], state["repeat"]) for state in states_of(run)[5:]], [(clock, 2), (clock, 3), (60006, 1)])

    def test_a_test_of_the_mapping_ends_it_and_its_end_plays_what_the_break_gave_way_to(self):
        target = support.demo_show()["mapping.json"]
        size = (60, 60)
        show = {"mapping.json": target, "show.json": json.dumps({"version": 1, "brightness": 128, "min_seconds": 4, "items": [{"id": 1, "file": "four.odrg"}]}),
                "four.odrg": support.clip(1, *size, (2000, 2000))}
        card_files = {name: support.clip(index, *size, (2000, 2000) if name in ("a.odrg", "b.odrg") else (3000,) if "message" not in name else (1000,))
                      for index, name in enumerate(CARD, 2)}
        script = at_times(1000, 5000, 9000, 13000, 17000, 21000) + asked(21500, "mapping test on") + asked(22000, "mapping test off") + at_times(22020, 25500, 26500)
        run = on_card(with_clocks(show), card_files, script)
        self.assertEqual(files_of(run)[5:], ["clock", "b.odrg", "b.odrg", "four.odrg"])


class TheWindow(unittest.TestCase):
    def test_a_window_that_passes_during_a_break_is_taken_at_its_end(self):
        # Turns of 1 second, `one.odrg` and `a.odrg` in turn, clocks of 5 seconds and the
        # message of 1: a break from 5 to 11 seconds of every 11. The window ends 1 second
        # into the clock of the break whose playlist would go on with `a.odrg`.
        show = plain_show_of([{"id": 1, "file": "one.odrg"}], {"one.odrg": loop_of(1, 1)}, min_seconds=1)
        card_files = {"a.odrg": loop_of(1, 5), "clocks/c1.odrg": loop_of(5, 7), "clocks/c2.odrg": loop_of(5, 8), "clocks/c3.odrg": loop_of(5, 9), "clocks/message/m.odrg": loop_of(1, 10)}
        window = 86_400_000
        run = on_card(with_clocks(show), card_files, at_times(11500, window + 1000, window + 4500, window + 5500))
        states = states_of(run)
        self.assertEqual(files_of(run), ["a.odrg", "clock", MESSAGE, "one.odrg"])
        self.assertEqual(states[2]["left"], 0)
        self.assertEqual(states[3]["left"], 86399)


class TheShuffle(unittest.TestCase):
    def test_the_core_draws_the_permutation_of_the_twin(self):
        for key in (0, 1, 0x9E3779B9, 0xFFFFFFFF):
            for count in (1, 2, 3, 4, 5, 7, 16, 17, 100, 256):
                with self.subTest(key=key, count=count):
                    drawn = [int(word) for word in support.host_lines("shuffle", str(key), str(count))[0].split()]
                    self.assertEqual(drawn, [support.clock_shuffle(key, count, index) for index in range(count)])
                    self.assertEqual(sorted(drawn), list(range(count)))

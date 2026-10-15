import contextlib
import json
import os
import pathlib
import tempfile
import unittest

from . import support
from .test_commands import OK, refused
from .test_playback import T0, refreshes
from .test_playlist import CANVAS, loop_of, show_of

# A show of one animation, with a loop of four seconds, whose turns last four seconds: a
# drive's animation with a loop of three seconds then has a turn of six, and one of two
# seconds a turn of four.
SHOW = show_of([{"id": 1, "file": "four.odrg"}], {"four.odrg": loop_of(4, 1)}, min_seconds=4)

# The files of a drive's folder `odrig`: two animations, named so that the one with the
# capital letters comes first, and files the host passes over.
DRIVE = {"b.odrg": loop_of(2, 5), "A.ODRG": loop_of(3, 6), ".hidden.odrg": loop_of(3, 7), "notes.txt": b"notes", "b.odrg.txt": loop_of(2, 8)}


@contextlib.contextmanager
def a_drive(files):
    """A folder that stands for the top of a drive whose folder `odrig` holds these files."""
    with tempfile.TemporaryDirectory() as top:
        folder = pathlib.Path(top, "odrig")
        folder.mkdir()
        for name, content in files.items():
            pathlib.Path(folder, name).write_bytes(content)
        yield top


def with_drive(files, drive, script=(), options=(), check_first=True):
    """A session on these installed files with a drive of these files, plugged in at the start
    unless the options say otherwise."""
    with a_drive(drive) as top:
        return support.start(files, script, ["--drive", top, *options], check_first=check_first)


def refusal(code):
    return json.loads(refused(code))


DONE = json.loads(OK)


def replies(run):
    return [json.loads(line[len("reply "):]) for line in run.lines if line.startswith("reply ")]


def listed(reply):
    """The id and the file of each item of a reply of `list`."""
    return [(item["id"], item.get("file")) for item in reply["items"]]


def statuses(run):
    return [(reply["playing"], reply["animation"]) for reply in replies(run) if "on" in reply]


def asked(time, *commands):
    """A refresh at this time after power-on, and these command lines then."""
    return [f"poll {T0 + time}", *(support.line(T0 + time, command) for command in commands)]


def pictures(run):
    """The LED data of each refresh of a session, by leg."""
    return [produced for _, produced in refreshes([line for line in run.lines if line.split(" ")[0] in ("refresh", "data", "idle")])[0]]


def logged(run):
    """The diagnostic texts of a session: those of its start and those after it."""
    return list(run.logs) + [line[len("log "):] for line in run.lines if line.startswith("log ")]


class TheDrivesList(unittest.TestCase):
    def test_its_animations_are_listed_after_the_shows_items_in_the_order_of_their_names(self):
        run = with_drive(SHOW, DRIVE, asked(0, "list"))
        self.assertEqual(listed(replies(run)[0]), [(1, "four.odrg"), (60001, "A.ODRG"), (60002, "b.odrg")])
        self.assertEqual([item["bytes"] for item in replies(run)[0]["items"]], [len(SHOW["four.odrg"]), len(DRIVE["A.ODRG"]), len(DRIVE["b.odrg"])])

    def test_a_file_of_another_canvas_and_a_damaged_one_are_left_out_and_logged(self):
        drive = {"a.odrg": loop_of(2, 5), "broken.odrg": loop_of(2, 6)[:-3], "wide.odrg": support.clip(7, CANVAS[0] + 1, CANVAS[1], (1000,)), "z.odrg": loop_of(3, 8)}
        run = with_drive(SHOW, drive, asked(0, "list", "status"))
        self.assertEqual(listed(replies(run)[0]), [(1, "four.odrg"), (60001, "a.odrg"), (60002, "z.odrg")])
        self.assertEqual(logged(run), ["drive file broken.odrg left out: truncated", "drive file wide.odrg left out: size-mismatch"])
        self.assertIsNone(replies(run)[1]["error"])

    def test_its_ids_are_the_lowest_from_60001_that_the_show_does_not_use(self):
        files = show_of([{"id": 60001, "file": "four.odrg"}, {"id": 60003, "file": "four.odrg"}], {"four.odrg": loop_of(4, 1)})
        drive = {"a.odrg": loop_of(2, 5), "b.odrg": loop_of(2, 6), "c.odrg": loop_of(2, 7)}
        run = with_drive(files, drive, asked(0, "list"))
        self.assertEqual([id for id, _ in listed(replies(run)[0])], [60001, 60003, 60002, 60004, 60005])

    def test_the_same_files_get_the_same_ids_when_the_drive_is_plugged_in_again(self):
        script = asked(0, "list") + ["drive pull"] + asked(20, "list") + ["drive plug"] + [f"poll {T0 + 40 + 20 * step}" for step in range(20)] + asked(500, "list")
        run = with_drive(SHOW, DRIVE, script)
        first, gone, again = replies(run)
        self.assertEqual(listed(gone), [(1, "four.odrg")])
        self.assertEqual(listed(again), listed(first))

    @unittest.skipIf(os.name == "nt", "Windows does not allow these characters in a file name")
    def test_a_name_is_written_so_that_the_reply_stays_json_of_printable_characters(self):
        names = ['quote".odrg', "back\\slash.odrg", "control\x01.odrg", "שלום.odrg", "\U0001f600.odrg"]
        run = with_drive(SHOW, {name: loop_of(2, 5) for name in names}, asked(0, "list"))
        line = next(line for line in run.lines if line.startswith("reply "))
        self.assertTrue(all(" " <= character <= "~" for character in line), line)
        self.assertIn('"file":"control\\u0001.odrg"', line)
        self.assertIn('"file":"\\u05e9\\u05dc\\u05d5\\u05dd.odrg"', line)
        self.assertIn('"file":"\\ud83d\\ude00.odrg"', line)
        self.assertEqual(sorted(file for _, file in listed(replies(run)[0])[1:]), sorted(names))

    def test_a_long_list_is_paged_across_the_shows_items_and_the_drives_animations(self):
        drive = {f"{index:02d}-{'x' * 100}.odrg": loop_of(1, index) for index in range(20)}
        script = asked(0, "list", "list 1", "list 20", "list 21")
        whole, on, last, beyond = replies(with_drive(SHOW, drive, script))
        self.assertEqual(listed(whole)[0], (1, "four.odrg"))
        self.assertIsNotNone(whole["next"])
        pages = []
        start = 1
        while start is not None:
            page = replies(with_drive(SHOW, drive, asked(0, f"list {start}")))[0]
            pages += listed(page)
            start = page["next"]
        self.assertEqual(pages, [(60001 + index, name) for index, name in enumerate(sorted(drive))])
        self.assertEqual(listed(on)[0], (60001, sorted(drive)[0]))
        self.assertEqual((listed(last), last["next"]), ([(60020, sorted(drive)[19])], None))
        self.assertEqual(beyond, {"ok": True, "items": [], "next": None})

    def test_a_host_without_a_drive_lists_and_plays_as_it_did(self):
        script = asked(0, "list", "status", "play 60001")
        without = support.start(SHOW, script)
        with a_drive(DRIVE) as top:
            fixed = support.start(SHOW, script, ["--drive", top, "--only-space"])
        self.assertEqual(replies(without)[0], {"ok": True, "items": [{"id": 1, "file": "four.odrg", "bytes": len(SHOW["four.odrg"])}], "next": None})
        self.assertEqual(replies(without)[2], refusal("unknown-id"))
        self.assertEqual(replies(fixed), replies(without))


class TheCheckOfTheDrive(unittest.TestCase):
    def lists(self, drive, script_after=(), count=40):
        """`list` at each of `count` refreshes from power-on, 20 ms apart, with the drive's
        files to be checked."""
        script = []
        for step in range(count):
            script += asked(20 * step, "list")
        return with_drive(SHOW, drive, script + list(script_after), check_first=False)

    def test_its_files_are_checked_after_the_installed_ones_and_join_one_by_one(self):
        drive = {"a.odrg": loop_of(12, 5), "b.odrg": loop_of(12, 6)}
        seen = []
        for reply in replies(self.lists(drive)):
            item = "busy" if reply == refusal("busy") else [id for id, _ in listed(reply)]
            if not seen or seen[-1] != item:
                seen.append(item)
        self.assertEqual(seen, ["busy", [1], [1, 60001], [1, 60001, 60002]])

    def test_an_upload_while_the_drive_is_checked_is_installed_and_the_check_goes_on(self):
        drive = {"a.odrg": loop_of(12, 5), "b.odrg": loop_of(12, 6)}
        data = loop_of(2, 9)
        script = asked(0) + asked(20) + asked(40) + asked(60, "list", *support.upload_lines(5, "new.odrg", data))
        script += [f"poll {T0 + 20 * step}" for step in range(4, 20)] + [support.line(T0 + 380, support.upload_end(data))]
        script += [line for step in range(20, 60) for line in asked(20 * step, "list")]
        run = with_drive(SHOW, drive, script, check_first=False)
        answers = replies(run)
        self.assertEqual(listed(answers[0]), [(1, "four.odrg")])
        self.assertEqual((answers[1]["ok"], answers[2].get("received"), answers[3]), (True, len(data), DONE))
        self.assertNotIn(refusal("busy"), answers)
        self.assertEqual([id for id, _ in listed(answers[-1])], [1, 5, 60001, 60002])

    def test_the_memory_has_room_for_256_animations_of_a_drive(self):
        from .test_memory import hundred_items

        files = hundred_items()
        without, blocks = support.start(files).memory
        with a_drive({}) as top:
            drive, drive_blocks = support.start(files, options=["--drive", top]).memory
        self.assertEqual((drive - without, drive_blocks - blocks), (4096, 1))
        self.assertLess(drive, 131072)
        self.assertIn(f"the target file takes {drive:,} bytes", (support.ROOT / "docs" / "core.md").read_text(encoding="utf-8"))


class TheDrivesAnimationsInTheShow(unittest.TestCase):
    def test_they_have_their_turns_after_the_shows_animations(self):
        times = (100, 3900, 4100, 9900, 10100, 13900, 14100)
        run = with_drive(SHOW, DRIVE, asked(0) + [line for time in times for line in asked(time, "status")])
        self.assertEqual([animation for _, animation in statuses(run)], [1, 1, 60001, 60001, 60002, 60002, 1])

    def test_play_plays_one_and_status_names_it_and_the_leds_show_its_frames(self):
        script = asked(0, "play 60002") + asked(20, "status") + asked(1020)
        run = with_drive(SHOW, DRIVE, script)
        self.assertEqual(replies(run)[0], DONE)
        self.assertEqual(statuses(run), [("all", 60002)])
        installed = show_of([{"id": 1, "file": "four.odrg"}, {"id": 2, "file": "b.odrg"}], {"four.odrg": loop_of(4, 1), "b.odrg": DRIVE["b.odrg"]}, min_seconds=4)
        same = support.start(installed, asked(0, "play 2") + asked(20) + asked(1020))
        self.assertEqual(pictures(run)[1:], pictures(same)[1:])

    def test_a_show_without_an_animation_of_its_own_plays_the_drives(self):
        files = show_of([], {})
        run = with_drive(files, DRIVE, asked(0, "status") + asked(5000, "status"))
        self.assertEqual(statuses(run), [("all", 60001), ("all", 60001)])

    def test_remove_and_upload_begin_of_a_drives_id_are_refused_as_in_use(self):
        run = with_drive(SHOW, DRIVE, asked(0, "remove 60001", "upload begin 60002 b.odrg 47", "list"))
        self.assertEqual(replies(run)[:2], [refusal("in-use"), refusal("in-use")])
        self.assertEqual(len(replies(run)[2]["items"]), 3)

    def test_space_counts_the_shows_animations_only(self):
        run = with_drive(SHOW, DRIVE, asked(0, "space"))
        self.assertEqual(replies(run)[0]["animations"], 1)


class PluggingInAndPullingOut(unittest.TestCase):
    def test_a_drive_plugged_in_while_the_core_runs_is_taken_up(self):
        script = asked(0, "list") + ["drive plug"] + [f"poll {T0 + 20 * step}" for step in range(1, 30)] + asked(600, "list")
        before, after = replies(with_drive(SHOW, DRIVE, script, ["--drive-pulled"]))
        self.assertEqual(listed(before), [(1, "four.odrg")])
        self.assertEqual(listed(after), [(1, "four.odrg"), (60001, "A.ODRG"), (60002, "b.odrg")])

    def test_pulled_out_while_one_of_its_animations_plays_the_next_one_left_plays_from_its_first_frame(self):
        script = asked(0, "play 60001") + asked(20, "status") + ["drive pull"] + asked(40, "status", "list")
        run = with_drive(SHOW, DRIVE, script)
        self.assertEqual(statuses(run), [("all", 60001), ("all", 1)])
        self.assertEqual(listed(replies(run)[3]), [(1, "four.odrg")])
        from_start = support.start(SHOW, asked(0, "play 1") + asked(20))
        self.assertEqual(pictures(run)[2], pictures(from_start)[1])

    def test_pulled_out_with_no_animation_left_nothing_plays_and_the_leds_are_dark(self):
        run = with_drive(show_of([], {}), DRIVE, asked(0, "status") + ["drive pull"] + asked(20, "status"))
        self.assertEqual(statuses(run), [("all", 60001), (None, None)])
        self.assertEqual(set(pictures(run)[1].values()), {bytes(3 * CANVAS[0] * CANVAS[1])})


class FaultsWhilePlaying(unittest.TestCase):
    def test_a_file_whose_reading_fails_while_it_plays_is_left_out_and_the_show_stays_valid(self):
        script = asked(0, "play 60002") + asked(20, "status", "list")
        run = with_drive(SHOW, DRIVE, script, ["--drive-read-fails", "b.odrg", "20"])
        _, status, reply = replies(run)
        self.assertEqual((status["playing"], status["animation"], status["error"]), ("all", 1, None))
        self.assertEqual(listed(reply), [(1, "four.odrg"), (60001, "A.ODRG")])
        self.assertEqual(logged(run), ["drive file b.odrg left out: read-error"])

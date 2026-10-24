import json
import unittest

from . import support
from . import huge_tail
from .test_body_faults import cut_clip
from .test_drive import a_drive
from .test_playback import T0

# A canvas of 3 x 2, on which cut_clip makes its files.
WIDTH, HEIGHT = 3, 2


def good(seed):
    return support.clip(seed, WIDTH, HEIGHT, (20,) * 5)


def bad_files():
    """The ways the second animation of a show can be bad: a body cut short, a header that
    is not one, and a file that is not there."""
    return {
        "a body cut short": (cut_clip(10, 3), "truncated"),
        "a bad header": (b"ODRX" + good(2)[4:], "bad-magic"),
        "no file": (None, "file-missing"),
    }


def show_with_a_bad_second(data):
    """Three animations, ids 1 to 3, whose second is `data`, or missing when it is None."""
    files = {
        "mapping.json": support.one_leg_mapping(WIDTH, HEIGHT),
        "show.json": support.show_text([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "file": "c.odrg"}]),
        "a.odrg": good(1),
        "c.odrg": good(3),
    }
    if data is not None:
        files["b.odrg"] = data
    return files


def replies(run):
    return [json.loads(line[len("reply "):]) for line in run.lines if line.startswith("reply ")]


class OneBadFileEndsTheShow(unittest.TestCase):
    """What a bad animation did to the whole show before it was quarantined."""

    def session(self, data):
        script = [f"poll {T0 + 20 * step}" for step in range(20)]
        script += [support.line(T0 + 400, command) for command in ("status", "list", "remove 3", "status")]
        return support.start(show_with_a_bad_second(data), script)

    def test_the_show_stays_valid_and_plays_the_others(self):
        for name, (data, _) in bad_files().items():
            with self.subTest(name):
                state = replies(self.session(data))[0]
                self.assertEqual((state["error"], state["playing"]), (None, "all"))
                self.assertIn(state["animation"], (1, 3))

    def test_list_and_remove_are_answered(self):
        for name, (data, reason) in bad_files().items():
            with self.subTest(name):
                listed, removed = replies(self.session(data))[1:3]
                self.assertEqual([item["id"] for item in listed["items"]], [1, 2, 3])
                self.assertEqual(listed["items"][1]["fault"], reason)
                self.assertEqual(removed, {"ok": True})



def show_of(items, files, start=None):
    """A show on the 3 x 2 canvas with these items and files."""
    return {"mapping.json": support.one_leg_mapping(WIDTH, HEIGHT), "show.json": support.show_text(items, start=start), **files}


def every_20_ms(count, start=0):
    return [f"poll {T0 + start + 20 * step}" for step in range(count)]


def logged(run):
    return list(run.logs) + [line[len("log "):] for line in run.lines if line.startswith("log ")]


class Compared:
    """Sessions on the core and on the reference player, compared line by line, the lines
    of the log among them."""

    def compare(self, files, script, options=(), check_first=True):
        run = support.start(files, script, options, check_first=check_first)
        reference = support.ReferencePlayer(files, check_first=check_first)
        expected = reference.run(script)
        self.assertEqual(list(run.logs), reference.start_logs)
        self.assertEqual(len(run.lines), len(expected), (run.lines[-3:], expected[-3:]))
        for number, (line, wanted) in enumerate(zip(run.lines, expected)):
            if line != wanted:
                self.fail(f"line {number} differs: the core printed {line[:90]}, the reference {wanted[:90]}")
        return run

    def asked(self, time, *commands):
        return [support.line(T0 + time, command) for command in commands]


class AsTheReference(Compared, unittest.TestCase):
    def test_a_bad_file_at_the_start_or_found_by_the_check(self):
        for name, (data, reason) in bad_files().items():
            for check_first in (True, False):
                with self.subTest(name, check_first=check_first):
                    script = every_20_ms(30) + self.asked(600, "status", "list", "space")
                    run = self.compare(show_with_a_bad_second(data), script, check_first=check_first)
                    self.assertIn(f"file b.odrg unavailable: {reason}", logged(run))

    def test_a_bad_body_met_by_the_player_keeps_the_picture_and_the_playlist_goes_on(self):
        # Refreshes 40 ms apart: the check takes a step at every tenth, and the first file,
        # of 400 frames, keeps it busy, so the player meets the fault.
        files = show_of([{"id": 1, "file": "b.odrg"}, {"id": 2, "file": "a.odrg"}, {"id": 3, "file": "long.odrg"}],
                        {"a.odrg": good(1), "b.odrg": cut_clip(10, 3), "long.odrg": support.clip(4, WIDTH, HEIGHT, (20,) * 400)})
        files["show.json"] = support.show_text([{"id": 3, "file": "long.odrg"}, {"id": 1, "file": "b.odrg"}, {"id": 2, "file": "a.odrg"}], start=1)
        script = [f"poll {T0 + 40 * step}" for step in range(40)] + self.asked(1600, "status", "list")
        run = self.compare(files, script, check_first=False)
        self.assertEqual(logged(run), ["file b.odrg unavailable: truncated"])

    def test_every_animation_bad(self):
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": b"ODRX" + good(1)[4:], "b.odrg": cut_clip(10, 3)})
        script = every_20_ms(20) + self.asked(400, "status", "list", "play 1", "play all", "space")
        run = self.compare(files, script)
        state = replies(run)[0]
        self.assertEqual((state["error"], state["playing"], state["animation"]), (None, None, None))
        self.assertEqual(replies(run)[2:4], [{"ok": False, "error": "unavailable"}, {"ok": False, "error": "unknown-id"}])

    def test_a_cycle_plays_its_next_usable_animation_and_gives_way_when_it_has_none(self):
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "file": "c.odrg"},
                         {"id": 4, "cycle": [1, 2, 3], "seconds": 1}, {"id": 5, "cycle": [2], "seconds": 1}],
                        {"a.odrg": good(1), "b.odrg": cut_clip(10, 3), "c.odrg": good(3)}, start=4)
        script = every_20_ms(200) + self.asked(4000, "status", "play 5", "play 4", "status")
        run = self.compare(files, script)
        self.assertEqual(replies(run)[1], {"ok": False, "error": "unavailable"})

    def test_a_cycle_whose_only_animation_turns_bad_gives_way_to_the_playlist(self):
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 5, "cycle": [2], "seconds": 1}],
                        {"a.odrg": good(1), "b.odrg": cut_clip(10, 3)}, start=5)
        self.compare(files, every_20_ms(60) + self.asked(1200, "status"), check_first=False)

    def test_the_start_names_a_bad_animation(self):
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "file": "c.odrg"}],
                        {"a.odrg": good(1), "b.odrg": b"ODRX" + good(2)[4:], "c.odrg": good(3)}, start=2)
        run = self.compare(files, every_20_ms(10) + self.asked(200, "status"))
        self.assertEqual(replies(run)[0]["animation"], 3)

    def test_show_faults_still_make_the_show_invalid(self):
        files = show_with_a_bad_second(cut_clip(10, 3))
        files["show.json"] = support.show_text([{"id": 1, "file": "a.odrg"}, {"id": 4, "cycle": [9], "seconds": 1}])
        run = self.compare(files, every_20_ms(5) + self.asked(100, "status", "list"))
        self.assertEqual(replies(run)[0]["error"], "undefined-id 9")
        self.assertEqual(replies(run)[1], {"ok": False, "error": "show-invalid"})

    def test_an_upload_that_replaces_a_bad_animation_makes_it_play(self):
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": b"ODRX" + good(1)[4:], "b.odrg": cut_clip(10, 3)})
        data = good(5)
        script = every_20_ms(5) + [support.line(T0 + 100, line) for line in support.upload_lines(2, "b.odrg", data)]
        script += every_20_ms(20, start=120) + self.asked(520, support.upload_end(data), "status", "list")
        run = self.compare(files, script + every_20_ms(5, start=540))
        state, listed = replies(run)[-2:]
        self.assertEqual((state["playing"], state["animation"]), ("all", 2))
        self.assertNotIn("fault", listed["items"][1])


class NotReadAgain(unittest.TestCase):
    def test_a_quarantined_file_is_opened_once_in_many_turns(self):
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": good(1), "b.odrg": b"ODRX" + good(2)[4:]})
        files["show.json"] = json.dumps({"version": 1, "brightness": 128, "min_seconds": 1, "items": [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}]})
        script = every_20_ms(500) + [support.line(T0 + 10000, command) for command in ("list", "play 2", "list")]
        run = support.start(files, script, ["--trace-files"], check_first=False)
        opened = [line for line in [*map(lambda pair: f"open {pair[0]} {pair[1]}", run.opened)] if " b.odrg " in line]
        opened += [line for line in run.lines if line.startswith("open b.odrg")]
        self.assertEqual(opened, ["open b.odrg 1"])

    def test_ignoring_a_quarantined_animation_does_not_revive_it(self):
        files = show_with_a_bad_second(cut_clip(10, 3))
        script = every_20_ms(20) + [support.line(T0 + 400, command) for command in ("ignore 2 1", "ignore 2 0", "list", "play 2")]
        run = support.start(files, script)
        changed, back, listed, played = replies(run)
        self.assertEqual((changed, back), ({"ok": True}, {"ok": True}))
        self.assertEqual((listed["items"][1]["ignored"], listed["items"][1]["fault"]), (False, "truncated"))
        self.assertEqual(played, {"ok": False, "error": "unavailable"})

    def test_a_file_that_played_and_then_cannot_be_read_is_quarantined(self):
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "c.odrg"}], {"a.odrg": good(1), "c.odrg": good(3)})
        files["show.json"] = json.dumps({"version": 1, "brightness": 128, "min_seconds": 1, "items": [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "c.odrg"}]})
        # Its first two openings read it, the check's and the player's first turn.
        script = every_20_ms(300) + [support.line(T0 + 6000, command) for command in ("status", "list")]
        run = support.start(files, script, ["--read-fails-after", "a.odrg", "16", "2"], check_first=False)
        self.assertEqual(logged(run), ["file a.odrg unavailable: read-error"])
        state, listed = replies(run)
        self.assertEqual((state["error"], state["animation"]), (None, 2))
        self.assertEqual(listed["items"][0]["fault"], "read-error")



class RepairDuringTheCheck(Compared, unittest.TestCase):
    def files(self):
        """A long first animation, which keeps the check busy, a second with a bad header,
        and a third."""
        return show_of([{"id": 1, "file": "long.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "file": "c.odrg"}],
                       {"long.odrg": support.clip(4, WIDTH, HEIGHT, (20,) * 400), "b.odrg": b"ODRX" + good(2)[4:], "c.odrg": good(3)})

    def test_a_bad_animation_is_replaced_while_the_check_goes_on_and_the_check_ends(self):
        data = good(5)
        script = every_20_ms(10) + [support.line(T0 + 200, line) for line in support.upload_lines(2, "b.odrg", data)]
        script += every_20_ms(10, start=220) + self.asked(420, support.upload_end(data), "list", "play 2")
        script += every_20_ms(60, start=440) + self.asked(1640, "list", "status")
        run = self.compare(self.files(), script, check_first=False)
        ended, during, played, after, state = replies(run)[-5:]
        self.assertEqual(ended, {"ok": True})
        self.assertEqual([item.get("fault") for item in during["items"]], [None, None, None])
        self.assertIsNone(during["items"][0]["bytes"])
        self.assertEqual(played, {"ok": True})
        self.assertNotIn(None, [item["bytes"] for item in after["items"]])
        self.assertEqual(state["animation"], 2)

    def test_ignore_and_remove_many_are_answered_during_the_check(self):
        script = every_20_ms(3) + [support.line(T0 + 60, command) for command in ("ignore 3 1", "remove many 2,3", "list")]
        run = support.start(self.files(), script, check_first=False)
        ignored, removed, listed = replies(run)
        self.assertEqual((ignored, removed), ({"ok": True}, {"ok": True}))
        self.assertEqual([item["id"] for item in listed["items"]], [1])



class TheDrivesFiles(unittest.TestCase):
    """A file of a drive left out is remembered for the boot by its name and its first read."""

    LONG = 8 * 1024 * 1024

    def session(self, script, drive, other=None):
        files = {"mapping.json": support.one_leg_mapping(4, 4), "sound.odrg": support.clip(1, 4, 4), "show.json": support.show_text([{"id": 1, "file": "sound.odrg"}])}
        with a_drive(drive) as top, a_drive(other or {}) as second:
            script = [line.replace("SECOND", second) for line in script]
            return support.start(files, script, ["--drive", top], check_first=False)

    def left_out_at(self, run):
        """The time after power-on of each refresh with a line of the log before it."""
        times = []
        for number, line in enumerate(run.lines):
            if line.startswith("log "):
                times.append(int(run.lines[number + 1].split()[1]) - T0)
        return times

    def test_the_same_file_taken_up_again_is_left_out_after_one_read(self):
        bad = huge_tail.huge_tail(self.LONG, 4, 4)
        script = every_20_ms(40) + ["drive pull"] + every_20_ms(2, start=800) + ["drive plug"] + every_20_ms(5, start=840)
        script += [support.line(T0 + 940, "list")]
        run = self.session(script, {"huge.odrg": bad})
        text = f"drive file huge.odrg left out: {huge_tail.REASON}"
        self.assertEqual(logged(run), [text, text])
        first, again = self.left_out_at(run)
        # The first time it settles in 256 slices; the second, its first read is enough.
        self.assertGreater(first, 300)
        self.assertLessEqual(again, 880)
        self.assertEqual(replies(run)[-1]["items"][1], {"id": 60001, "file": "huge.odrg", "bytes": None, "external": True, "fault": huge_tail.REASON})

    def test_another_file_of_the_same_name_is_checked_anew(self):
        bad = huge_tail.huge_tail(self.LONG, 4, 4)
        script = every_20_ms(40) + ["drive pull", "drive plug SECOND"] + every_20_ms(10, start=800) + [support.line(T0 + 1000, "list")]
        run = self.session(script, {"huge.odrg": bad}, {"huge.odrg": support.clip(9, 4, 4)})
        self.assertEqual(logged(run), [f"drive file huge.odrg left out: {huge_tail.REASON}"])
        self.assertEqual([(item["id"], item.get("fault")) for item in replies(run)[-1]["items"]], [(1, None), (60001, None)])

    def test_a_drives_files_get_their_ids_at_once_and_a_left_out_one_is_unavailable(self):
        drive = {"a.odrg": b"ODRX" + support.clip(2, 4, 4)[4:], "b.odrg": support.clip(3, 4, 4)}
        script = every_20_ms(10) + [support.line(T0 + 200, command) for command in ("list", "play 60001", "play 60002", "remove 60001", "upload begin 60001 new.odrg 10")]
        run = self.session(script, drive)
        listed, played, playing, removed, uploaded = replies(run)
        self.assertEqual([(item["id"], item.get("fault")) for item in listed["items"]], [(1, None), (60001, "bad-magic"), (60002, None)])
        self.assertEqual((played, playing), ({"ok": False, "error": "unavailable"}, {"ok": True}))
        self.assertEqual((removed, uploaded), ({"ok": False, "error": "in-use"}, {"ok": False, "error": "in-use"}))


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from . import support
from .test_commands import refused
from .test_playback import T0
from .test_startup import VECTORS


def body_faults():
    """The invalid vectors the start takes, because their header is sound: the name of
    each, its bytes, and what the core's decoder makes of it."""
    found = []
    for path in sorted(VECTORS.iterdir()):
        data = path.read_bytes()
        decoded = support.found_in(data)
        if decoded.header is not None:
            found.append((path.name, data, decoded))
    return found


def show_with(data, sound=None, cycle=None, alone=False, **members):
    """A show on the canvas a file states, with that file as `faulty.odrg`, item 2. With
    `sound`, a sound animation of that many frames of 20 ms is item 1, before it. With
    `cycle`, a cycle with turns of that many seconds is item 3 and plays: of the two, or
    with `alone` of the faulty one only."""
    width, height = (int.from_bytes(data[at:at + 2], "little") for at in (6, 8))
    files = {"mapping.json": support.one_leg_mapping(width, height), "faulty.odrg": data}
    items = [{"id": 2, "file": "faulty.odrg", **members}]
    if sound is not None:
        files["sound.odrg"] = support.clip(1, width, height, (20,) * sound)
        items.insert(0, {"id": 1, "file": "sound.odrg"})
    show = {"version": 1, "brightness": 255, "items": items}
    if cycle is not None:
        show["items"].append({"id": 3, "cycle": [2] if alone else [1, 2], "seconds": cycle})
        show["start"] = 3
    files["show.json"] = json.dumps(show)
    return files


def steps_after(refreshes):
    """The steps the check has taken after this many refreshes in a row."""
    return sum(min(row, 16) for row in range(1, refreshes))


def cut_clip(frames, kept):
    """An animation of frames of 20 ms on a small canvas, cut inside the record after
    `kept` whole ones."""
    whole = support.clip(7, 3, 2, (20,) * frames, compressed=False)
    for size in range(len(whole) - 1, 16, -1):
        if len(support.found_in(whole[:size]).records) == kept:
            return whole[:size]
    raise AssertionError("no cut leaves that many records")


class BodyFaults(unittest.TestCase):
    def session(self, files, script):
        """Runs a script on the core as it is after power-on, and on the reference
        player, and compares every line. Returns the lines without those of the log, and
        each text of the log with the time, after power-on, of the refresh it came with."""
        run = support.start(files, script, check_first=False)
        self.assertIsNone(run.error, "the start takes the file")
        printed = [line for line in run.lines if not line.startswith("log ")]
        expected = support.ReferencePlayer(files, check_first=False).run(script)
        self.assertEqual([line for line in run.lines if line.startswith("log ")], [line for line in expected if line.startswith("log ")])
        expected = [line for line in expected if not line.startswith("log ")]
        self.assertEqual(len(printed), len(expected))
        for number, (line, wanted) in enumerate(zip(printed, expected)):
            if line != wanted:
                self.fail(f"line {number} differs: the core printed {line[:90]}, the reference {wanted[:90]}")
        logs = []
        for number, line in enumerate(run.lines):
            if line.startswith("log "):
                # The core gives the text to the host during the poll, so it is printed
                # before the refresh of that poll.
                self.assertTrue(run.lines[number + 1].startswith("refresh "))
                logs.append((int(run.lines[number + 1].split()[1]) - T0, line[4:]))
        return printed, logs

    def assert_lit(self, printed):
        """Every refresh shows a picture: no fault darkens the LEDs."""
        for line in printed:
            word, _, rest = line.partition(" ")
            if word == "data":
                self.assertTrue(any(bytes.fromhex(rest.split()[1])), line[:40])

    def assert_still_checked(self, printed):
        """The last reply, to `list`, lists the faulty animation as usable, with its size
        not known yet: the check has not come to it."""
        faulty = [item for item in json.loads(printed[-1][len("reply "):])["items"] if item["id"] == 2]
        self.assertEqual((faulty[0]["bytes"], faulty[0].get("fault")), (None, None))

    def assert_quarantined(self, printed, reason, playing="all"):
        """The last two replies: `status` with no error, the sound animation on the LEDs
        and this playing, and `list` with the faulty animation and its fault, or `busy`
        while the check goes on."""
        state, listed = [line[len("reply "):] for line in printed if line.startswith("reply ")][-2:]
        state = json.loads(state)
        self.assertEqual((state["error"], state["playing"], state["animation"]), (None, playing, 1))
        if listed != refused("busy"):
            faulty = [item for item in json.loads(listed)["items"] if item["id"] == 2]
            self.assertEqual(faulty[0]["fault"], reason)


class FoundByTheCheck(BodyFaults):
    SOUND = 4

    def test_every_vector_as_the_second_animation_ends_the_show_at_the_step_that_reads_it(self):
        vectors = body_faults()
        self.assertGreaterEqual(len(vectors), 20)
        for name, data, decoded in vectors:
            with self.subTest(vector=name):
                # The check reads the sound file in its frames and two steps, opens the
                # faulty one, decodes its sound records, and fails at the step after.
                steps = self.SOUND + 2 + 1 + len(decoded.records) + 1
                refresh = next(count for count in range(1, 100) if steps_after(count) >= steps)
                time = 20 * (refresh - 1)
                script = [f"poll {T0 + 20 * step}" for step in range(refresh + 3)]
                script += [support.line(T0 + 20 * refresh + 40, "status"), support.line(T0 + 20 * refresh + 40, "list")]
                text = f"file faulty.odrg unavailable: {name.split('.')[0]}"
                printed, logs = self.session(show_with(data, sound=self.SOUND), script)
                self.assertEqual(logs, [(time, text)])
                self.assert_lit(printed)
                self.assert_quarantined(printed, name.split(".")[0])

    def test_two_faulty_files_are_quarantined_in_the_order_the_show_names_them(self):
        files = show_with(cut_clip(10, 3), sound=2)
        files["other.odrg"] = cut_clip(10, 1)
        show = json.loads(files["show.json"])
        show["items"].append({"id": 4, "file": "other.odrg"})
        files["show.json"] = json.dumps(show)
        script = [f"poll {T0 + 20 * step}" for step in range(12)] + [support.line(T0 + 240, "status"), support.line(T0 + 240, "list")]
        printed, logs = self.session(files, script)
        self.assertEqual([text for _, text in logs], ["file faulty.odrg unavailable: truncated", "file other.odrg unavailable: truncated"])
        self.assert_quarantined(printed, "truncated")

    def test_a_file_that_cannot_be_read_to_its_end_is_a_read_error(self):
        files = show_with(support.clip(3, 3, 2, (20,) * 6), sound=self.SOUND)
        script = [f"poll {T0 + 20 * step}" for step in range(12)] + [support.line(T0 + 240, "status")]
        for offset in (16, 40, len(files["faulty.odrg"])):
            with self.subTest(offset=offset):
                run = support.start(files, script, ["--read-fails", "faulty.odrg", str(offset)], check_first=False)
                self.assertIsNone(run.error, "the start reads the header")
                self.assertEqual([line for line in run.lines if line.startswith("log ")], ["log file faulty.odrg unavailable: read-error"])
                state = json.loads(run.lines[-1][len("reply "):])
                self.assertEqual((state["error"], state["playing"], state["animation"]), (None, "all", 1))


class FoundByThePlayer(BodyFaults):
    """No refresh of these sessions follows another in step, so the check takes a step at
    every tenth of them, and the first file of the show keeps it busy for longer than a
    session lasts: 402 steps. What is found here, the player finds."""

    LONG = 400

    def every_40_ms(self, last):
        self.assertLess(last // 40 // 10, self.LONG)
        script = [f"poll {T0 + time}" for time in range(0, last + 1, 40)]
        return script + [support.line(T0 + last, "status"), support.line(T0 + last, "list")]

    def test_every_vector_played_in_a_cycle_ends_the_show_where_its_sound_frames_end(self):
        for name, data, decoded in body_faults():
            with self.subTest(vector=name):
                frames = decoded.header[3]
                sound_ms = sum(duration for duration, _ in decoded.records)
                # A turn that is longer than the frames before the fault.
                files = show_with(data, sound=self.LONG, cycle=sound_ms // 1000 + 1, alone=True)
                printed, logs = self.session(files, self.every_40_ms(sound_ms + 400))
                if len(decoded.records) == frames:
                    # Every frame decodes, and the fault lies after the last one: the
                    # player never comes to it.
                    self.assertEqual(logs, [])
                    self.assert_still_checked(printed)
                else:
                    # The cycle lists the faulty one alone: the playlist plays from then on.
                    text = f"file faulty.odrg unavailable: {name.split('.')[0]}"
                    time = -(-sound_ms // 40) * 40
                    self.assertEqual(logs, [(time, text)])
                    self.assert_quarantined(printed, name.split(".")[0])

    def test_the_frames_before_the_fault_are_shown(self):
        files = show_with(cut_clip(100, 75), sound=self.LONG, cycle=3, alone=True)
        printed, logs = self.session(files, self.every_40_ms(2000))
        # 75 frames of 20 ms: the first refresh at or after 1,500 ms is the one at 1,520.
        self.assertEqual(logs, [(1520, "file faulty.odrg unavailable: truncated")])
        # The refresh that meets the fault keeps the picture before it.
        self.assertEqual(printed[printed.index(f"refresh {T0 + 1520}") + 1], printed[printed.index(f"refresh {T0 + 1480}") + 1])
        whole = support.clip(7, 3, 2, (20,) * 100, compressed=False)
        sound = support.start(show_with(whole, sound=self.LONG, cycle=3, alone=True), self.every_40_ms(2000), check_first=False).lines
        cut = printed.index(f"refresh {T0 + 1520}")
        self.assertEqual(printed[:cut], sound[:cut])

    def test_in_the_playlist_it_is_found_in_the_turn_of_the_faulty_animation(self):
        # The sound animation has its turn first: four loops of 8 seconds.
        files = show_with(cut_clip(100, 75), sound=self.LONG)
        printed, logs = self.session(files, self.every_40_ms(35000))
        self.assertEqual(logs, [(33520, "file faulty.odrg unavailable: truncated")])
        self.assert_lit(printed)
        self.assert_quarantined(printed, "truncated")

    def test_max_seconds_before_the_fault_ends_the_turn_and_the_show_plays_on(self):
        files = show_with(cut_clip(100, 75), sound=self.LONG, max_seconds=1)
        show = json.loads(files["show.json"])
        show["items"][0]["repeat"] = 1
        files["show.json"] = json.dumps(show)
        # 8 seconds of the sound one, 1 of the faulty one, and again.
        printed, logs = self.session(files, self.every_40_ms(20000))
        self.assertEqual(logs, [])
        self.assertIsNone(json.loads(printed[-2][len("reply "):])["error"])
        self.assert_still_checked(printed)

    def test_in_a_cycle_it_is_found_when_a_turn_is_long_enough_to_come_to_it(self):
        data = cut_clip(100, 75)
        for seconds, found in ((1, None), (2, 3520)):
            with self.subTest(seconds=seconds):
                printed, logs = self.session(show_with(data, sound=self.LONG, cycle=seconds), self.every_40_ms(9000))
                if found is None:
                    self.assertEqual(logs, [])
                    self.assert_still_checked(printed)
                else:
                    # The cycle shows its usable animation in the faulty one's turns.
                    self.assertEqual(logs, [(found, "file faulty.odrg unavailable: truncated")])
                    self.assert_lit(printed)
                    self.assert_quarantined(printed, "truncated", playing=3)


class FoundByTheCheckOfALateHost(BodyFaults):
    def test_a_host_that_is_always_late_still_comes_to_the_fault(self):
        # The fault lies after the last frame, where the player never reads. The check
        # takes its 6 and 12 steps at every tenth refresh: the last at the 180th.
        whole = support.clip(7, 3, 2, (20,) * 10, compressed=False)
        files = show_with(whole + b"\0", sound=4)
        script = [f"poll {T0 + 40 * step}" for step in range(190)] + [support.line(T0 + 7600, "status"), support.line(T0 + 7600, "list")]
        printed, logs = self.session(files, script)
        self.assertEqual(logs, [(40 * 179, "file faulty.odrg unavailable: trailing-bytes")])
        self.assert_lit(printed)
        self.assert_quarantined(printed, "trailing-bytes")

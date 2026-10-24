import json
import random
import unittest

from odrig import odrg

from . import huge_tail, support, test_decoder
from .test_body_faults import cut_clip, show_with
from .test_drive import a_drive, logged, replies
from .test_playback import T0, refreshes
from .test_vectors import INVALID, VALID

# What one call of the core may read of files while it settles the reproducer: a few of
# the host's reads, never the whole file.
MOST_BYTES_IN_A_CALL = 4096

# The bytes of a body one call of the decoder settles, as the core is built, and the most
# bytes of a body the player decodes at one refresh, a record's boundary after it.
SETTLE_SLICE = 32768
CATCH_UP = 131072

# A reproducer on a canvas of 4 x 4 whose tail settles in 32 slices, and one of 256.
SMALL_TAIL = 1024 * 1024
LONGER_TAIL = 8 * 1024 * 1024
TEXT = f"file faulty.odrg unavailable: {huge_tail.REASON}"


def show_of_the_reproducer():
    data = huge_tail.huge_tail()
    show = {"version": 1, "brightness": 128, "items": [{"id": 1, "file": "huge.odrg"}]}
    return {"mapping.json": support.one_leg_mapping(huge_tail.WIDTH, huge_tail.HEIGHT), "huge.odrg": data, "show.json": json.dumps(show)}, data


def small(tail=SMALL_TAIL):
    """A reproducer on a canvas of 4 x 4 with a tail of this many bytes."""
    return huge_tail.huge_tail(tail, 4, 4)


def calls(printed):
    """What each traced call read of files, in bytes."""
    return [int(line.split()[1]) for line in printed if line.startswith("call ")]


def every_20_ms(count, start=0):
    return [f"poll {T0 + start + 20 * step}" for step in range(count)]


def texts(run):
    """Every reply and every text of the log of a session."""
    return [line[len("reply "):] for line in run.lines if line.startswith("reply ")] + logged(run)


class TheReproducer(unittest.TestCase):
    def test_no_call_of_the_core_reads_the_whole_reproducer(self):
        files, data = show_of_the_reproducer()
        script = [f"poll {T0 + 20 * step}" for step in range(40)]
        run = support.start(files, script, options=["--trace-calls"], check_first=False)
        read = calls(run.lines)
        self.assertEqual(len(read), 40)
        self.assertLessEqual(max(read), MOST_BYTES_IN_A_CALL, f"the most one call read: {max(read)} of {len(data)} bytes")

    def test_its_tail_is_settled_in_slices_and_its_reason_is_the_one_of_the_whole_file(self):
        data = huge_tail.huge_tail()
        (decoded, pending), = support.decode_in_slices([data], SETTLE_SLICE)
        self.assertEqual(decoded.reason, huge_tail.REASON)
        self.assertEqual(decoded, support.found_in(data))
        self.assertEqual(pending, huge_tail.TAIL // SETTLE_SLICE)


class SettlingInSlicesOfSevenBytes(unittest.TestCase):
    def compare(self, files, slice_bytes=7):
        """Every file gives the same records and reason in slices of 7 bytes, or of the bytes
        given, as in one call; returns the number of files that needed more than one call."""
        whole = support.decode_each(files)
        sliced = support.decode_in_slices(files, slice_bytes)
        for position, (data, alone, (decoded, pending)) in enumerate(zip(files, whole, sliced)):
            self.assertEqual(decoded, alone, f"file {position}: {data[:60].hex()}")
            if alone.reason is None:
                self.assertEqual(pending, 0)
        return sum(1 for _, pending in sliced if pending != 0)

    def test_every_vector(self):
        paths = sorted(VALID.glob("*.odrg")) + sorted(INVALID.iterdir())
        files = [path.read_bytes() for path in paths]
        self.compare(files)
        # The vectors are small: their defects settle within a few bytes.
        self.assertGreater(self.compare(files, 1), 0)

    def test_copies_with_bytes_changed_cut_out_or_put_in(self):
        rng = random.Random(31)
        originals = test_decoder.DamagedFiles().originals()
        copies = []
        while len(copies) < 1500:
            copy = bytearray(rng.choice(originals))
            for _ in range(rng.randint(1, 3)):
                at = rng.randrange(len(copy))
                change = rng.random()
                if change < 0.6:
                    copy[at] = rng.choice([value for value in range(256) if value != copy[at]])
                elif change < 0.8:
                    del copy[at:at + rng.randint(1, 4)]
                else:
                    copy[at:at] = rng.randbytes(rng.randint(1, 4))
            copies.append(bytes(copy))
        self.assertGreater(self.compare(copies), 200)

    def test_the_reproducer_with_a_short_tail(self):
        self.assertEqual(self.compare([small(4096), huge_tail.huge_tail(70000)]), 2)


class TheChecksAndThePlayerGoOnWhileItSettles(unittest.TestCase):
    def assert_no_pending(self, run):
        for text in texts(run):
            self.assertNotIn("pending", text)
            self.assertNotIn('"reason":""', text)
            self.assertFalse(text.endswith(" ") or "  " in text, text)

    def test_the_check_after_the_start_comes_to_the_reason(self):
        files = show_with(small(LONGER_TAIL), sound=2)
        script = every_20_ms(60) + [support.line(T0 + 1200, "status")]
        run = support.start(files, script, options=["--trace-calls"], check_first=False)
        self.assertLessEqual(max(calls(run.lines)), MOST_BYTES_IN_A_CALL)
        self.assertEqual([text for text in logged(run)], [TEXT])
        self.assertEqual((replies(run)[-1]["error"], replies(run)[-1]["animation"]), (None, 1))
        # A status between the steps of the check is answered while it settles.
        early = support.start(files, every_20_ms(8) + [support.line(T0 + 160, "status")], check_first=False)
        self.assertIsNone(replies(early)[-1]["error"])
        self.assert_no_pending(run)

    def test_the_player_comes_to_the_reason(self):
        # Refreshes 40 ms apart: the check takes a step at every tenth, and a long sound
        # file keeps it busy, so the player meets the fault.
        files = show_with(small(LONGER_TAIL), sound=400, cycle=15, alone=True)
        script = [f"poll {T0 + 40 * step}" for step in range(270)] + [support.line(T0 + 10800, "status")]
        run = support.start(files, script, options=["--trace-calls"], check_first=False)
        self.assertLessEqual(max(calls(run.lines)), MOST_BYTES_IN_A_CALL)
        self.assertEqual(logged(run), [TEXT])
        # The cycle lists no usable animation any more: the playlist plays the sound one.
        self.assertEqual([replies(run)[-1][member] for member in ("error", "playing", "animation")], [None, "all", 1])
        self.assert_no_pending(run)

    def test_the_start_of_a_host_that_cannot_change_its_storage_reads_on_to_the_reason(self):
        files = show_with(small(), sound=2)
        run = support.start(files, every_20_ms(3) + [support.line(T0 + 60, "status")], options=["--no-storage"], check_first=False)
        self.assertIsNone(run.error)
        self.assertEqual(list(run.logs), [TEXT])
        self.assertEqual((replies(run)[-1]["error"], replies(run)[-1]["animation"]), (None, 1))
        self.assert_no_pending(run)

    def test_the_check_of_an_upload_answers_busy_until_it_has_settled(self):
        data = small()
        lines = support.upload_lines(9, "new.odrg", data)
        script = [support.line(T0, line) for line in lines]
        # The check takes a step at each refresh: its header, its record and 32 slices.
        for step in range(1, 40):
            script += [f"poll {T0 + 20 * step}", support.line(T0 + 20 * step, support.upload_end(data))]
            if step == 3:
                script.append(support.line(T0 + 20 * step, "status"))
        run = support.start(show_with(support.clip(1, 4, 4), sound=2), script)
        ends = [reply for reply in replies(run)[len(lines):] if "playing" not in reply]
        busy = 0
        while ends[busy] == {"ok": False, "error": "busy"}:
            busy += 1
        self.assertGreater(busy, 32)
        self.assertEqual(ends[busy], {"ok": False, "error": "bad-file", "reason": huge_tail.REASON})
        self.assertEqual(ends[busy + 1], {"ok": False, "error": "no-upload"})
        self.assert_no_pending(run)

    def test_a_file_that_cannot_be_read_while_it_settles_is_a_read_error(self):
        files = show_with(small(LONGER_TAIL), sound=2)
        script = every_20_ms(40) + [support.line(T0 + 800, "status")]
        run = support.start(files, script, options=["--read-fails", "faulty.odrg", "4000"], check_first=False)
        self.assertEqual(logged(run), ["file faulty.odrg unavailable: read-error"])
        self.assertIsNone(replies(run)[-1]["error"])
        self.assert_no_pending(run)

    def drive_session(self, pull_at=None):
        files = {"mapping.json": support.one_leg_mapping(4, 4), "sound.odrg": support.clip(1, 4, 4), "show.json": support.show_text([{"id": 1, "file": "sound.odrg"}])}
        script = []
        for step in range(40):
            if step == pull_at:
                script.append("drive pull")
            script.append(f"poll {T0 + 20 * step}")
        script.append(support.line(T0 + 800, "list"))
        with a_drive({"huge.odrg": small(LONGER_TAIL)}) as top:
            return support.start(files, script, ["--drive", top], check_first=False)

    def test_a_drives_file_is_left_out_with_its_reason(self):
        run = self.drive_session()
        self.assertEqual(logged(run), [f"drive file huge.odrg left out: {huge_tail.REASON}"])
        self.assertEqual([item["id"] for item in replies(run)[-1]["items"]], [1])
        # The slices of the drive's file outlast the refreshes before the pull below.
        position = next(number for number, line in enumerate(run.lines) if line.startswith("log "))
        self.assertGreater(int(run.lines[position + 1].split()[1]), T0 + 20 * 8)
        self.assert_no_pending(run)

    def test_a_drive_pulled_out_while_its_file_settles_is_dropped_without_a_reason(self):
        run = self.drive_session(pull_at=8)
        self.assertEqual(logged(run), [])
        self.assertEqual([item["id"] for item in replies(run)[-1]["items"]], [1])
        self.assert_no_pending(run)



def pictures_of(lines):
    """`(time after power-on, LED data of every leg)` for each refresh of a session."""
    produced, _ = refreshes([line for line in lines if line.split(" ")[0] in ("refresh", "data", "idle")])
    return [(time - T0, tuple(sorted(data.items()))) for time, data in produced]


class PlaybackInSlices(unittest.TestCase):
    def test_frames_of_1_ms_after_a_pause_catch_up_over_several_refreshes(self):
        # Records of 773 bytes: about 170 a refresh, while the time goes on by 20.
        animation = support.seeded_animation(31, 16, 16, (1,) * 2000, colours=1000)
        clip = odrg.encode(animation, compressed=False)
        files = {"mapping.json": support.one_leg_mapping(16, 16), "show.json": support.show_text([{"id": 1, "file": "clip.odrg"}]), "clip.odrg": clip}
        # Ten refreshes, a pause of eleven seconds, and forty refreshes: the first of them
        # lies 1,000 ms into a loop of 2,000.
        script = every_20_ms(10) + every_20_ms(40, start=11000)
        run = support.start(files, script, options=["--trace-calls"])
        record = (len(clip) - 16) // 2000
        self.assertLessEqual(max(calls(run.lines)), CATCH_UP + record + 512)
        printed = pictures_of(run.lines)
        expected = pictures_of(support.ReferencePlayer(files).run(script))
        self.assertEqual(printed[:10], expected[:10])
        before = printed[9][1]
        caught = next(number for number in range(10, 50) if printed[number] == expected[number])
        self.assertGreaterEqual(caught - 10, 3, "the catching up takes several refreshes")
        self.assertEqual([picture for _, picture in printed[10:caught]], [before] * (caught - 10))
        self.assertEqual(printed[caught:], expected[caught:])

    def test_the_demo_show_plays_as_before_through_a_pause(self):
        files = support.demo_show()
        script = every_20_ms(100) + every_20_ms(100, start=4000) + [support.line(T0 + 6000, "status")]
        run = support.start(files, script)
        self.assertEqual(run.lines, support.ReferencePlayer(files).run(script))

    def test_while_a_file_settles_the_refreshes_keep_the_picture_before(self):
        # A cycle of a sound file and the reproducer, turns of 15 seconds, refreshes 40 ms
        # apart so that the player meets the fault: from 15,000 ms on it settles, one slice
        # a refresh, and the LEDs keep the picture of 14,960 ms until the reason comes, and
        # at its refresh; then the cycle shows its usable animation in the rest of the turn.
        files = show_with(small(LONGER_TAIL), sound=400, cycle=15)
        script = [f"poll {T0 + 40 * step}" for step in range(660)]
        run = support.start(files, script, check_first=False)
        printed = pictures_of(run.lines)
        position = next(number for number, line in enumerate(run.lines) if line.startswith("log "))
        self.assertEqual(run.lines[position], f"log {TEXT}")
        failed = int(run.lines[position + 1].split()[1]) - T0
        self.assertGreater(failed, 15000 + 40 * 200)
        held = dict(printed)[14960]
        self.assertNotEqual(held, tuple((leg, bytes(len(data))) for leg, data in held))
        for time, picture in printed:
            if 15000 <= time <= failed:
                self.assertEqual(picture, held, time)
            elif time > failed:
                self.assertNotEqual(picture, tuple((leg, bytes(len(data))) for leg, data in held), time)



def fault_of(run):
    """`(work, record, body bytes, reason, name)` of the last `fault` line of a session, or
    None for `fault none`."""
    line = [line for line in run.lines if line.startswith("fault ")][-1]
    if line == "fault none":
        return None
    _, work, record, body, reason, name = line.split(" ", 5)
    return work, int(record), int(body), reason, name


class TheFaultsContext(unittest.TestCase):
    # The body of the reproducer on 4 x 4 before its tail: a palette of two colours and one
    # stored record.
    BODY = 6 + 5 + 16
    WANTED = huge_tail.REASON

    def test_there_is_none_before_a_fault(self):
        run = support.start(show_with(support.clip(1, 4, 4), sound=2), every_20_ms(5) + ["fault"])
        self.assertIsNone(fault_of(run))

    def test_the_check_after_the_start(self):
        run = support.start(show_with(small(), sound=2), every_20_ms(30) + ["fault"], check_first=False)
        self.assertEqual(fault_of(run), ("start", 0, self.BODY + SMALL_TAIL, self.WANTED, "faulty.odrg"))

    def test_the_start_of_a_host_that_cannot_change_its_storage(self):
        run = support.start(show_with(small(), sound=2), ["fault"], options=["--no-storage"], check_first=False)
        self.assertEqual(fault_of(run), ("start", 0, self.BODY + SMALL_TAIL, self.WANTED, "faulty.odrg"))

    def test_playback(self):
        files = show_with(small(), sound=400, cycle=5, alone=True)
        run = support.start(files, [f"poll {T0 + 40 * step}" for step in range(60)] + ["fault"], check_first=False)
        self.assertEqual(fault_of(run), ("play", 0, self.BODY + SMALL_TAIL, self.WANTED, "faulty.odrg"))

    def test_the_check_of_an_upload(self):
        data = small()
        script = [support.line(T0, line) for line in support.upload_lines(9, "new.odrg", data)] + every_20_ms(40, start=20) + ["fault"]
        run = support.start(show_with(support.clip(1, 4, 4), sound=2), script)
        self.assertEqual(fault_of(run), ("upload", 0, self.BODY + SMALL_TAIL, self.WANTED, "new.odrg"))

    def test_the_check_of_a_drives_file(self):
        files = {"mapping.json": support.one_leg_mapping(4, 4), "sound.odrg": support.clip(1, 4, 4), "show.json": support.show_text([{"id": 1, "file": "sound.odrg"}])}
        with a_drive({"huge.odrg": small()}) as top:
            run = support.start(files, every_20_ms(20) + ["fault"], ["--drive", top], check_first=False)
        self.assertEqual(fault_of(run), ("drive", 0, self.BODY + SMALL_TAIL, self.WANTED, "huge.odrg"))

    def test_a_file_cut_short_in_its_fourth_record(self):
        data = cut_clip(10, 3)
        run = support.start(show_with(data, sound=2), every_20_ms(10) + ["fault"], check_first=False)
        self.assertEqual(fault_of(run), ("start", 3, len(data) - 16, "truncated", "faulty.odrg"))

    def test_the_latest_fault_replaces_the_one_before(self):
        files = {"mapping.json": support.one_leg_mapping(3, 2), "sound.odrg": support.clip(1, 3, 2), "show.json": support.show_text([{"id": 1, "file": "sound.odrg"}])}
        drive = {"a.odrg": cut_clip(10, 3), "b.odrg": cut_clip(10, 1)}
        with a_drive(drive) as top:
            # The check takes 1 + 2 + 3 + 4 steps at the first five refreshes: the sound
            # file's five, and a.odrg's header, three records and the cut one.
            first = support.start(files, every_20_ms(5) + ["fault"], ["--drive", top], check_first=False)
            both = support.start(files, every_20_ms(10) + ["fault"], ["--drive", top], check_first=False)
        self.assertEqual(fault_of(first)[:2], ("drive", 3))
        self.assertEqual(fault_of(first)[4], "a.odrg")
        self.assertEqual(fault_of(both)[:2], ("drive", 1))
        self.assertEqual(fault_of(both)[3:], ("truncated", "b.odrg"))


if __name__ == "__main__":
    unittest.main()

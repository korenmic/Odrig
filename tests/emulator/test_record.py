import io
import json
import pathlib
import struct
import tempfile
import time
import unittest

from emulator import recfile, record
from tests.core import support as core_support

from . import support

SCRIPT = (
    (0, "status"),
    (10, "brightness 200"),
    (30, "status"),
    (1000, "off"),
    (1010, "status"),
    (2000, "on"),
    (2500, "play 2"),
    (2515, "status"),
    (3000, "play 1"),
    (3500, "play 99"),
    (3510, "play abc"),
    (3520, "brightness 256"),
    (3530, "dance"),
    (3540, "play"),
    (3550, "on now"),
    (3560, ""),
    (3570, "play " + "1" * 2050),
    (3580, "brightness 0"),
    (3700, "brightness 64"),
    (3995, "status"),
)


def script_text(commands):
    return "".join(f"{time} {line}\n" for time, line in commands)


def tick_times(seconds):
    return range(0, int(seconds * 1000), 20)


class Recording(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = pathlib.Path(temporary.name)
        self.out = self.work / "out.odrr"

    def example(self):
        packed = support.example_show()
        folder = packed.__enter__()
        self.addCleanup(packed.__exit__, None, None, None)
        return folder

    def installed(self, files):
        folder = self.work / f"show-{len(list(self.work.iterdir()))}"
        folder.mkdir()
        for name, content in files.items():
            (folder / name).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return folder

    def record(self, folder, seconds, commands=None, out=None):
        """Records a show and returns `(recording, printed lines)`."""
        options = []
        if commands is not None:
            script = self.work / "script.txt"
            script.write_text(script_text(commands), encoding="utf-8")
            options = ["--script", script]
        out = self.out if out is None else out
        result = support.run(folder, "--record", out, "--seconds", seconds, *options)
        self.assertEqual((result.status, result.err), (0, ""))
        return recfile.read(out), result.out.splitlines()

    def assert_equals_reference(self, recording, refreshes):
        """Every tick of a recording against what the reference player gives for it."""
        self.assertEqual(len(recording.ticks), len(refreshes))
        for tick, refresh in zip(recording.ticks, refreshes):
            if tick.produced != (refresh is not None):
                self.fail(f"tick {tick.ms}: the core {'produced' if tick.produced else 'did not produce'} a refresh, unlike the reference")
            expected = refresh if refresh is not None else tuple(bytes(3 * count) for _, _, count in recording.legs)
            for (leg, _, _), got, wanted in zip(recording.legs, recfile.split(recording, tick.data), expected):
                if got != wanted:
                    self.fail(f"tick {tick.ms}: the LED data of leg {leg} differs from the reference")

    def assert_nothing_left(self):
        self.assertFalse(self.out.exists())
        self.assertEqual([path.name for path in self.work.iterdir() if path.name.endswith(".part")], [])

    def test_a_script_that_uploads_acts_on_the_folder_and_gives_the_same_recording_from_the_same_folder(self):
        clip = core_support.clip(9, 60, 6, (20,) * 10)
        lines = core_support.upload_lines(9, "clip.odrg", clip, 100)
        commands = [(100 + number, line) for number, line in enumerate(lines)]
        commands += [(200, core_support.upload_end(clip)), (420, core_support.upload_end(clip)), (430, "play 9"), (440, "list"), (900, "remove 2"), (910, "status")]
        recordings = []
        for number in (1, 2):
            folder = self.installed(support.files_of(self.example()))
            recording, printed = self.record(folder, 2, commands, self.work / f"{number}.odrr")
            files = support.files_of(folder)
            self.assertEqual(files["clip.odrg"], clip)
            self.assertEqual(sorted(files), ["clip.odrg", "dvd.odrg", "hello.odrg", "mapping.json", "show.json"])
            recordings.append(((self.work / f"{number}.odrr").read_bytes(), printed, files))
        self.assertEqual(recordings[0], recordings[1])
        printed = recordings[0][1]
        self.assertIn('reply 200 {"ok":false,"error":"busy"}', printed)
        self.assertIn('reply 420 {"ok":true}', printed)
        self.assertIn('reply 900 {"ok":false,"error":"in-use"}', printed)
        self.assertEqual(json.loads(printed[-1].split(" ", 2)[2])["playing"], 9)
        refreshes, replies = support.reference(support.files_of(self.example()), tick_times(2), commands)
        self.assertEqual(printed, [f"reply {time} {reply.decode('ascii')[:-1]}" for (time, _), reply in zip(commands, replies)])
        self.assert_equals_reference(recfile.read(self.work / "1.odrr"), refreshes)

    def test_the_storage_option_goes_with_record_mode(self):
        folder = self.installed(support.files_of(self.example()))
        commands = [(0, "space"), (10, "upload begin 9 clip.odrg 5000")]
        script = self.work / "script.txt"
        script.write_text(script_text(commands), encoding="utf-8")
        result = support.run(folder, "--record", self.out, "--seconds", 1, "--script", script, "--storage", 30000)
        self.assertEqual((result.status, result.err), (0, ""))
        self.assertEqual(result.out.splitlines(), ['reply 0 {"ok":true,"free":13616,"total":30000,"animations":2}', 'reply 10 {"ok":false,"error":"no-space"}'])

    def test_60_seconds_of_the_example_show_equal_the_reference_at_every_tick(self):
        folder = self.example()
        recording, printed = self.record(folder, 60)
        self.assertEqual(printed, [])
        self.assertEqual([tick.ms for tick in recording.ticks], list(tick_times(60)))
        refreshes, _ = support.reference(support.files_of(folder), tick_times(60))
        self.assert_equals_reference(recording, refreshes)
        self.assertTrue(all(tick.produced for tick in recording.ticks))

    def test_the_picture_changes_animation_at_15_30_and_45_seconds(self):
        folder = self.example()
        hello, dvd = ({tick.data for tick in self.record(folder, 15, [(0, f"play {item}")], self.work / f"{item}.odrr")[0].ticks} for item in (1, 2))
        self.assertFalse(hello & dvd)
        recording, _ = self.record(folder, 60)
        for tick in recording.ticks:
            turn = tick.ms // 15000
            self.assertIn(tick.data, dvd if turn % 2 else hello, tick.ms)
        by_time = {tick.ms: tick.data for tick in recording.ticks}
        self.assertEqual(by_time[30000], by_time[0])
        self.assertEqual(by_time[45000], by_time[15000])
        self.assertNotEqual(by_time[15000], by_time[0])

    def test_status_names_the_animation_on_each_side_of_a_change(self):
        folder = self.example()
        commands = [(time, "status") for time in (14990, 15010, 29990, 30010, 44990, 45010)]
        _, printed = self.record(folder, 46, commands)
        animations = [json.loads(line.split(" ", 2)[2])["animation"] for line in printed]
        self.assertEqual(animations, [1, 2, 2, 1, 1, 2])
        _, replies = support.reference(support.files_of(folder), tick_times(46), commands)
        self.assertEqual(printed, [f"reply {time} {reply.decode('ascii')[:-1]}" for (time, _), reply in zip(commands, replies)])

    def test_a_script_with_every_command_gives_the_replies_and_the_led_data_of_the_reference(self):
        folder = self.example()
        recording, printed = self.record(folder, 4, SCRIPT)
        refreshes, replies = support.reference(support.files_of(folder), tick_times(4), SCRIPT)
        self.assertEqual(printed, [f"reply {time} {reply.decode('ascii')[:-1]}" for (time, _), reply in zip(SCRIPT, replies)])
        self.assert_equals_reference(recording, refreshes)
        codes = [json.loads(reply).get("error") for reply in replies]
        self.assertEqual(sorted(set(filter(None, codes))), ["bad-argument", "line-too-long", "unknown-command", "unknown-id"])
        self.assertEqual({line for _, line in SCRIPT} >= {"status", "on", "off", "play 2", "brightness 200"}, True)
        self.assertTrue(any(time % 20 for time, _ in SCRIPT))
        by_time = {tick.ms: tick.data for tick in recording.ticks}
        self.assertEqual(by_time[1000], bytes(1080))
        self.assertEqual(by_time[1980], bytes(1080))
        self.assertTrue(any(by_time[2000]))
        self.assertEqual(max(by_time[20]), 200)
        self.assertEqual(by_time[3580], bytes(1080))
        self.assertEqual(max(by_time[3700]), 64)

    def test_play_on_an_invalid_show_is_show_invalid_and_the_leds_stay_dark(self):
        files = core_support.example_show()
        del files["dvd.odrg"]
        folder = self.installed(files)
        commands = [(100, "play 1"), (200, "status")]
        recording, printed = self.record(folder, 1, commands)
        self.assertEqual(printed[0], 'reply 100 {"ok":false,"error":"show-invalid"}')
        self.assertEqual(json.loads(printed[1].split(" ", 2)[2])["error"], "file-missing dvd.odrg")
        refreshes, _ = support.reference(files, tick_times(1), commands)
        self.assert_equals_reference(recording, refreshes)
        self.assertTrue(all(tick.produced and tick.data == bytes(1080) for tick in recording.ticks))

    def test_a_flipped_first_led_reverses_every_row_of_that_leg_and_of_no_other(self):
        folder = self.example()
        refreshes, _ = support.reference(support.files_of(folder), tick_times(20))
        mapping = json.loads((folder / "mapping.json").read_text(encoding="utf-8"))
        self.assertEqual((mapping["legs"][1]["leg"], mapping["legs"][1]["first_led"]), (2, "right"))
        mapping["legs"][1]["first_led"] = "left"
        (folder / "mapping.json").write_text(json.dumps(mapping), encoding="utf-8")
        recording, _ = self.record(folder, 20)
        self.assertEqual(recording.legs, ((1, 1, 180), (2, 2, 180)))
        differing = 0
        for tick, (first, second) in zip(recording.ticks, refreshes):
            got_first, got_second = recfile.split(recording, tick.data)
            self.assertEqual(got_first, first, f"tick {tick.ms}: leg 1")
            for row in range(3):
                got = [got_second[offset:offset + 3] for offset in range(180 * row, 180 * (row + 1), 3)]
                wanted = [second[offset:offset + 3] for offset in range(180 * row, 180 * (row + 1), 3)]
                self.assertEqual(got, wanted[::-1], f"tick {tick.ms}: row {row} of leg 2")
            differing += got_second != second
        self.assertEqual(len(recording.ticks), 1000)
        self.assertGreater(differing, 500)

    def test_a_first_led_at_the_top_reverses_every_column_of_that_leg_of_the_target_file_and_of_no_other(self):
        target = core_support.mapping_texts()["legs-20"]
        files = {
            "mapping.json": target,
            "show.json": core_support.show_text([{"id": 1, "file": "clip.odrg"}], brightness=255, start=1),
            "clip.odrg": core_support.clip("upright", 60, 60, durations=(20,) * 25),
        }
        refreshes, _ = support.reference(files, tick_times(1))
        mapping = json.loads(target)
        self.assertEqual((mapping["legs"][6]["leg"], mapping["legs"][6]["first_led"], mapping["legs"][6]["columns"]), (7, "bottom", [19, 20, 21]))
        mapping["legs"][6]["first_led"] = "top"
        recording, _ = self.record(self.installed({**files, "mapping.json": json.dumps(mapping)}), 1)
        self.assertEqual(recording.legs, tuple((leg["leg"], leg["pin"], 180) for leg in mapping["legs"]))
        self.assertEqual(len(recording.legs), 20)
        differing = 0
        for tick, reference in zip(recording.ticks, refreshes):
            for index, (got, wanted) in enumerate(zip(recfile.split(recording, tick.data), reference)):
                if index != 6:
                    self.assertEqual(got, wanted, f"tick {tick.ms}: leg {index + 1}")
                    continue
                for column in range(3):
                    got_leds = [got[offset:offset + 3] for offset in range(180 * column, 180 * (column + 1), 3)]
                    wanted_leds = [wanted[offset:offset + 3] for offset in range(180 * column, 180 * (column + 1), 3)]
                    self.assertEqual(got_leds, wanted_leds[::-1], f"tick {tick.ms}: column {column} of leg 7")
                differing += got != wanted
        self.assertEqual(len(recording.ticks), 50)
        self.assertEqual(differing, 50)

    def test_every_made_up_column_leg_mapping_is_recorded_with_its_own_legs_as_the_reference_plays_it(self):
        texts = core_support.column_mapping_texts()
        self.assertEqual(sorted(texts), ["columns-apart", "one-led-column", "top-start", "two-and-four-columns"])
        sizes = set()
        for name, text in texts.items():
            with self.subTest(mapping=name):
                listed = json.loads(text)
                height = listed["height"]
                width = sum(len(leg["columns"]) for leg in listed["legs"])
                sizes.add((width, height))
                files = {
                    "mapping.json": text,
                    "show.json": core_support.show_text([{"id": 1, "file": "clip.odrg"}], brightness=255, start=1),
                    "clip.odrg": core_support.clip(name, width, height, durations=(20, 40, 20, 60, 20)),
                }
                recording, printed = self.record(self.installed(files), 1)
                self.assertEqual(printed, [])
                self.assertEqual(recording.legs, tuple((leg["leg"], leg["pin"], height * len(leg["columns"])) for leg in listed["legs"]))
                self.assertEqual(recording.led_bytes, 3 * width * height)
                refreshes, _ = support.reference(files, tick_times(1))
                self.assert_equals_reference(recording, refreshes)
                self.assertTrue(all(tick.produced for tick in recording.ticks))
                self.assertGreater(len({tick.data for tick in recording.ticks}), 1)
        self.assertEqual(sizes, {(5, 4), (1, 1), (3, 7), (6, 5)})

    def test_an_invalid_mapping_gives_no_legs_and_no_refresh(self):
        files = core_support.example_show()
        files["mapping.json"] = b'{"version": 1, "width": 60}'
        folder = self.installed(files)
        recording, printed = self.record(folder, 1, [(500, "status")])
        self.assertEqual(recording.legs, ())
        self.assertEqual(recording.led_bytes, 0)
        self.assertEqual([(tick.ms, tick.produced, tick.data) for tick in recording.ticks], [(ms, False, b"") for ms in tick_times(1)])
        self.assertEqual(self.out.stat().st_size, 16 + 50 * 9)
        self.assertEqual(json.loads(printed[0].split(" ", 2)[2])["error"], "mapping-malformed")

    def test_two_runs_give_identical_bytes(self):
        folder = self.example()
        self.record(folder, 17, SCRIPT)
        first = self.out.read_bytes()
        _, printed = self.record(folder, 17, SCRIPT, self.work / "second.odrr")
        self.assertEqual((self.work / "second.odrr").read_bytes(), first)
        self.assertEqual(len(printed), len(SCRIPT))

    def test_600_seconds_of_a_one_frame_show_are_recorded_in_under_60_seconds(self):
        folder = self.installed({
            "mapping.json": core_support.one_leg_mapping(8, 4),
            "show.json": core_support.show_text([{"id": 1, "file": "one.odrg"}], brightness=255, start=1),
            "one.odrg": core_support.clip("one frame", 8, 4, durations=(20,)),
        })
        started = time.monotonic()
        recording, _ = self.record(folder, 600)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 60, "600 seconds of a one-frame show took 60 seconds or more to record on this Mac")
        self.assertEqual(len(recording.ticks), 30000)
        self.assertEqual(recording.ticks[-1].ms, 599980)
        self.assertEqual({tick.data for tick in recording.ticks}, {recording.ticks[0].data})
        self.assertTrue(any(recording.ticks[0].data))

    def test_the_header_fields_and_the_file_size_for_a_known_length(self):
        self.record(self.example(), 1)
        data = self.out.read_bytes()
        self.assertEqual(data[:4], bytes.fromhex("4F445252"))
        self.assertEqual(data[:4], b"ODRR")
        version, zero, legs, tick_ms, led_bytes = struct.unpack_from("<BBHII", data, 4)
        self.assertEqual((version, zero, legs, tick_ms, led_bytes), (1, 0, 2, 20, 1080))
        self.assertEqual(struct.unpack_from("<HHIHHI", data, 16), (1, 1, 180, 2, 2, 180))
        self.assertEqual(len(data), 16 + 2 * 8 + 50 * (9 + 1080))
        self.assertEqual(struct.unpack_from("<QB", data, 32), (0, 1))
        self.assertEqual(struct.unpack_from("<QB", data, 32 + 49 * 1089), (980, 1))

    def test_the_ticks_are_the_grid_times_below_the_length(self):
        folder = self.example()
        for seconds, expected in (("0.02", [0]), ("0.03", [0, 20]), ("0.05", [0, 20, 40]), ("0.1", [0, 20, 40, 60, 80]), ("0.0006", [0])):
            recording, _ = self.record(folder, seconds)
            self.assertEqual([tick.ms for tick in recording.ticks], expected, seconds)

    def test_a_command_later_than_the_last_tick_is_still_answered(self):
        folder = self.example()
        commands = [(990, "brightness 3"), (999, "status")]
        _, printed = self.record(folder, 1, commands)
        _, replies = support.reference(support.files_of(folder), tick_times(1), commands)
        self.assertEqual(printed, [f"reply {time} {reply.decode('ascii')[:-1]}" for (time, _), reply in zip(commands, replies)])
        self.assertEqual(json.loads(printed[1].split(" ", 2)[2])["brightness"], 3)

    def test_a_script_may_hold_comments_empty_lines_and_carriage_returns(self):
        folder = self.example()
        script = self.work / "script.txt"
        script.write_bytes(b"# a comment\n\n0 status\r\n\r\n20 brightness 5\r\n# 30 off\n40 status")
        result = support.run(folder, "--record", self.out, "--seconds", 1, "--script", script)
        self.assertEqual((result.status, result.err), (0, ""))
        printed = result.out.splitlines()
        self.assertEqual([line.split(" ", 2)[1] for line in printed], ["0", "20", "40"])
        self.assertEqual(json.loads(printed[2].split(" ", 2)[2])["brightness"], 5)
        self.assertEqual(json.loads(printed[2].split(" ", 2)[2])["on"], True)

    def test_a_refused_script_gives_bad_script_and_no_file(self):
        folder = self.example()
        cases = {
            "a line without a time": "0 status\nstatus\n",
            "a time without a space": "0 status\n20status\n",
            "a time that is no number": "0 status\n2x status\n",
            "a negative time": "-20 status\n",
            "a space before the time": " 20 status\n",
            "a time that goes backwards": "40 status\n20 status\n",
            "a time at the length of the recording": "0 status\n1000 status\n",
            "a time after the length of the recording": "5000 status\n",
        }
        for name, text in cases.items():
            with self.subTest(name):
                script = self.work / "script.txt"
                script.write_text(text, encoding="utf-8")
                result = support.run(folder, "--record", self.out, "--seconds", 1, "--script", script)
                self.assertEqual(result.status, 1)
                self.assertEqual(result.out, "")
                self.assertRegex(result.err, r"\Aerror: bad-script: .+\n\Z")
                self.assert_nothing_left()

    def test_a_script_that_cannot_be_read_gives_bad_script_and_no_file(self):
        folder = self.example()
        not_utf8 = self.work / "latin.txt"
        not_utf8.write_bytes(b"0 status\n20 caf\xe9\n")
        for script in (self.work / "no-such-script.txt", self.work, not_utf8):
            result = support.run(folder, "--record", self.out, "--seconds", 1, "--script", script)
            self.assertEqual(result.status, 1)
            self.assertRegex(result.err, r"\Aerror: bad-script: .+\n\Z")
            self.assert_nothing_left()

    def test_a_length_that_is_not_above_zero_gives_bad_length_and_no_file(self):
        folder = self.example()
        for seconds in ("0", "0.0", "-1", "0.0004", "-0.02"):
            result = support.run(folder, "--record", self.out, f"--seconds={seconds}")
            self.assertEqual(result.status, 1, seconds)
            self.assertRegex(result.err, r"\Aerror: bad-length: .+\n\Z")
            self.assert_nothing_left()

    def test_a_refused_start_leaves_an_earlier_record_file_as_it_was(self):
        folder = self.example()
        self.out.write_bytes(b"an earlier recording")
        script = self.work / "script.txt"
        script.write_text("status\n", encoding="utf-8")
        self.assertEqual(support.run(folder, "--record", self.out, "--seconds", 1, "--script", script).status, 1)
        self.assertEqual(support.run(folder, "--record", self.out, "--seconds", 0).status, 1)
        self.assertEqual(support.run(folder, "--record", self.out, "--seconds", 1, "--core", self.work / "none.dylib").status, 1)
        self.assertEqual(self.out.read_bytes(), b"an earlier recording")
        self.assertEqual(sorted(path.name for path in self.work.iterdir()), ["out.odrr", "script.txt"])

    def test_a_folder_that_does_not_exist_is_not_a_folder(self):
        a_file = self.work / "file"
        a_file.write_bytes(b"")
        for folder in (self.work / "no-such-folder", a_file):
            result = support.run(folder, "--record", self.out, "--seconds", 1)
            self.assertEqual(result.status, 1)
            self.assertRegex(result.err, r"\Aerror: not-a-folder: .+\n\Z")
            self.assert_nothing_left()

    def test_a_wrong_core_is_core_not_built(self):
        result = support.run(self.example(), "--record", self.out, "--seconds", 1, "--core", self.work / "libodrig_core.dylib")
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"\Aerror: core-not-built: .+\n\Z")
        self.assertIn("make -C core shared", result.err)
        self.assert_nothing_left()

    def test_a_record_file_that_cannot_be_written_is_cannot_write(self):
        result = support.run(self.example(), "--record", self.work / "no-such-folder" / "out.odrr", "--seconds", 1)
        self.assertEqual(result.status, 1)
        self.assertRegex(result.err, r"\Aerror: cannot-write: .+\n\Z")
        self.assertEqual(list(self.work.iterdir()), [])

    def test_a_usage_error_is_status_2(self):
        folder = self.example()
        for argv in (
            ["--record", self.out, "--seconds", 1],
            [folder, "--record", self.out, "--seconds", "soon"],
            [folder, "--record", self.out, "--seconds", "inf"],
            [folder, "--record", self.out],
            [folder, "--record", self.out, "--seconds", 1, "--size", "60x6"],
            [folder, folder, "--record", self.out, "--seconds", 1],
        ):
            result = support.run(*argv)
            self.assertEqual(result.status, 2, argv)
            self.assertIn("usage:", result.err)
            self.assertEqual(result.out, "")
            self.assert_nothing_left()

    def test_the_module_records_when_run_as_a_program(self):
        folder = self.example()
        script = self.work / "script.txt"
        script.write_text("0 status\n", encoding="utf-8")
        result = support.run_module(folder, "--record", self.out, "--seconds", "0.5", "--script", script)
        self.assertEqual((result.status, result.err), (0, ""))
        self.assertEqual(result.out, 'reply 0 {"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":0,"error":null}\n')
        self.assertEqual(len(recfile.read(self.out).ticks), 25)
        failed = support.run_module(self.work / "none", "--record", self.out, "--seconds", "0.5")
        self.assertEqual(failed.status, 1)
        self.assertRegex(failed.err, r"\Aerror: not-a-folder: .+\n\Z")
        self.assertEqual(support.run_module("--seconds").status, 2)


class Calls(unittest.TestCase):
    class Core:
        """Stands in for the core and writes down every call."""

        def __init__(self):
            self.calls = []

        def poll(self, now):
            self.calls.append(("poll", now))
            return True

        def frame(self):
            return b"\x01\x02\x03"

        def command(self, now, line):
            self.calls.append(("command", now, line))
            return b'{"ok":true}\n'

    def test_record_mode_gives_the_core_the_scripted_commands_and_nothing_of_its_own(self):
        core = self.Core()
        commands = [record.Command(0, b"status"), record.Command(25, b"off"), record.Command(40, b"on"), record.Command(70, b"play 1")]
        printed = io.StringIO()
        ticks = list(record.ticks(core, 4, commands, printed))
        self.assertEqual(core.calls, [
            ("command", 0, b"status"), ("poll", 0), ("poll", 20),
            ("command", 25, b"off"), ("command", 40, b"on"), ("poll", 40), ("poll", 60),
            ("command", 70, b"play 1"),
        ])
        self.assertEqual(ticks, [(ms, True, b"\x01\x02\x03") for ms in (0, 20, 40, 60)])
        self.assertEqual(printed.getvalue(), "".join(f'reply {time} {{"ok":true}}\n' for time in (0, 25, 40, 70)))

    def test_the_number_of_ticks_is_the_length_over_20_rounded_up(self):
        self.assertEqual([record.tick_count(ms) for ms in (1, 19, 20, 21, 40, 60000)], [1, 1, 1, 2, 2, 3000])


if __name__ == "__main__":
    unittest.main()

import json
import pathlib
import subprocess
import tempfile
import unittest

from . import support
from .test_clocks import clock_of
from .test_content import animation, small_show
from .test_drive import with_drive
from .test_playback import T0, Playback, refreshes
from .test_upload import Script, Uploads, bad_file

PICTURES = support.ROOT / "tests" / "vectors" / "pictures"
CANVAS = (20, 10)


def picture_of(widget="picture-dial", canvas=CANVAS, **settings):
    """The container the converter writes of the source of a picture clock on a canvas:
    a frame of 1 about a face of 2, with a hand and a cap, or a field of the time."""
    width, height = canvas
    rows = ["".join("1" if y in (0, height - 1) or x in (0, width - 1) else "2" for x in range(width)) for y in range(height)]
    source = {
        "version": 1, "type": "widget", "width": width, "height": height, "widget": widget, "seconds": 2, "speed_min": 600,
        "speed_max": 3600, "direction": "random", "turns": 100, "palette": [0x000000, 0xd4a017, 0xf4ecd0], "picture": rows,
    }
    if widget == "picture-dial":
        source["hands"] = [{"unit": "minute", "color": 0, "x": width, "y": height, "length": height - 2, "tail": 1, "half": 1, "offset": 0}]
        source["caps"] = [{"x": width, "y": height, "radius": 2, "color": 1}]
    else:
        source["fields"] = [{"left": 1, "top": 1, "width": width - 2, "height": min(height - 2, 7), "font": "tiny", "pattern": "Mm:Ss",
                             "digits": 0, "colons": 1, "blink": True, "offset": 0}]
    source.update(settings)
    with tempfile.TemporaryDirectory() as folder:
        given = pathlib.Path(folder) / "clock.json"
        made = pathlib.Path(folder) / "clock.odrgx"
        given.write_text(json.dumps(source), encoding="utf-8")
        done = subprocess.run(["node", str(support.CONVERTER), "encode", str(given), str(made)], capture_output=True, text=True)
        if done.returncode != 0:
            raise AssertionError(f"the converter did not encode the clock: {done.stderr.strip()}")
        return made.read_bytes()


def converter_pictures(path, times, seed):
    """The pictures the converter's library draws of a file at these times into its turn,
    with a seed."""
    library = (support.ROOT / "converter" / "lib" / "index.js").as_uri()
    code = (f"import {{odrgx}} from {json.dumps(library)}; import fs from 'node:fs';"
            "const [file, seed, ...times] = process.argv.slice(1);"
            "const decoded = odrgx.decode(new Uint8Array(fs.readFileSync(file)));"
            "for (const t of times) console.log(Buffer.from(odrgx.pictureAt(decoded, Number(t), Number(seed))).toString('hex'));")
    done = subprocess.run(["node", "--input-type=module", "-e", code, str(path), str(seed), *map(str, times)], capture_output=True, text=True, check=True)
    return [bytes.fromhex(line) for line in done.stdout.split()]


def show_of(items, files, **more):
    show = {"version": 1, "brightness": 255, "items": list(items), **more}
    return {"mapping.json": support.one_leg_mapping(*CANVAS), "show.json": json.dumps(show), **files}


def polled(printed):
    """The lines of a session that answer its polls."""
    return [line for line in printed if line.split(" ")[0] in ("refresh", "data", "idle")]


def statuses(printed):
    return [json.loads(line[len("reply "):]) for line in printed if line.startswith('reply {"ok":true,"on"')]


def polls_and_status(times):
    script = []
    for time in times:
        script += [f"poll {T0 + time}", support.line(T0 + time, "status")]
    return script


class TheVectors(unittest.TestCase):
    def test_a_valid_picture_clock_is_read_whole_with_its_seconds_as_its_loop(self):
        paths = sorted((PICTURES / "valid").glob("*.odrgx"))
        self.assertGreaterEqual(len(paths), 6)
        for path, decoded in zip(paths, support.decode_each([path.read_bytes() for path in paths])):
            with self.subTest(vector=path.name):
                seconds = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))["seconds"]
                self.assertIsNone(decoded.reason)
                self.assertEqual(decoded.container, (3, 1000 * seconds, len(path.read_bytes()) - 20))
                self.assertEqual(list(decoded.records), [])

    def test_an_invalid_picture_clock_is_refused_with_the_reason_of_its_name(self):
        paths = sorted((PICTURES / "invalid").glob("*.odrgx"))
        self.assertGreaterEqual(len(paths), 20)
        for path, decoded in zip(paths, support.decode_each([path.read_bytes() for path in paths])):
            with self.subTest(vector=path.name):
                self.assertEqual(decoded.reason, path.name.split(".")[0])

    def test_a_picture_clock_shows_only_the_colours_of_its_palette_and_its_hands_move(self):
        data = (PICTURES / "valid" / "dial.odrgx").read_bytes()
        palette = {bytes.fromhex(colour) for colour in ("000000", "d4a017", "f4ecd0", "404040", "c02020")}
        pictures = support.rendered(data, [0, 5000, 10000], 3)
        for picture in pictures:
            self.assertLessEqual({picture[at:at + 3] for at in range(0, len(picture), 3)}, palette)
        self.assertEqual(len(set(pictures)), 3)

    def test_the_core_draws_as_the_converter_long_into_a_turn(self):
        times = [600000, 3600000, 43210987, 4000000000]
        for name in ("dial.odrgx", "dial.small.odrgx", "display.odrgx", "display.large.odrgx"):
            for seed in (5, 2864038069):
                with self.subTest(vector=name, seed=seed):
                    path = PICTURES / "valid" / name
                    self.assertEqual(support.rendered(path.read_bytes(), times, seed), converter_pictures(path, times, seed))

    def test_two_seeds_give_other_times(self):
        for name in ("dial.odrgx", "display.odrgx"):
            with self.subTest(vector=name):
                data = (PICTURES / "valid" / name).read_bytes()
                times = [0, 1000, 10000, 20000]
                self.assertEqual(support.rendered(data, times, 7), support.rendered(data, times, 7))
                self.assertNotEqual(support.rendered(data, times, 7), support.rendered(data, times, 8))


class PictureClocksInAShow(Playback):
    def test_a_picture_dial_and_a_display_play_as_the_reference_and_each_turn_gets_its_seed(self):
        files = show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrgx"}],
                        {"a.odrgx": picture_of(seconds=1), "b.odrgx": picture_of("picture-display", seconds=1)}, min_seconds=1)
        script = [f"poll {T0}"] + polls_and_status([0, 20, 500, 980, 1000, 1500, 1980, 2000, 2020])
        script += [f"poll {T0 + 20 * step}" for step in range(102, 200)]
        printed = self.assert_as_the_reference(files, script)
        states = statuses(printed)
        self.assertEqual([state["animation"] for state in states], [1, 1, 1, 1, 2, 2, 2, 1, 1])
        seeds = [state["seed"] for state in states]
        self.assertEqual(len(set(seeds[:4])), 1)
        self.assertEqual(len(set(seeds[4:7])), 1)
        self.assertEqual(len({seeds[0], seeds[4], seeds[7]}), 3)
        produced, _ = refreshes(polled(printed))
        self.assertGreater(len({repr(sorted(data.items())) for _, data in produced}), 10)

    def test_the_pictures_follow_the_time_of_the_turn_however_the_refreshes_come(self):
        files = show_of([{"id": 1, "file": "a.odrgx"}], {"a.odrgx": picture_of(seconds=30)})
        late = [f"poll {T0}", f"poll {T0 + 1337}", f"poll {T0 + 5013}", f"poll {T0 + 9000}"]
        steady = [f"poll {T0 + 20 * step}" for step in range(451)]
        first = self.assert_as_the_reference(files, late)
        second = self.assert_as_the_reference(files, steady)
        at_9000 = [refreshes(polled(printed))[0][-1] for printed in (first, second)]
        self.assertEqual(at_9000[0][0], T0 + 9000)
        self.assertEqual(at_9000[0], at_9000[1])

    def test_a_picture_clock_with_a_fault_is_quarantined_at_the_start(self):
        cases = {
            "bad-picture": (PICTURES / "invalid" / "bad-picture.frames.odrgx").read_bytes(),
            "unknown-font": (PICTURES / "invalid" / "unknown-font.odrgx").read_bytes(),
            "size-mismatch": picture_of(canvas=(21, 10)),
        }
        for reason, data in cases.items():
            with self.subTest(reason=reason):
                mapping = support.one_leg_mapping(60, 60) if reason != "size-mismatch" else support.one_leg_mapping(*CANVAS)
                files = {"mapping.json": mapping, "show.json": json.dumps({"version": 1, "brightness": 255, "items": [{"id": 1, "file": "a.odrgx"}]}), "a.odrgx": data}
                run = support.start(files, ["error", f"poll {T0}", support.line(T0, "list")])
                self.assertIn(f"file a.odrgx unavailable: {reason}", run.logs)


class UploadsOfPictureClocks(Uploads):
    def test_a_picture_clock_is_uploaded_listed_and_played(self):
        files = small_show([animation(1, "one.odrg")])
        clock = picture_of(canvas=(60, 6))
        script = Script().polls(10).upload(7, "clock.odrgx", clock).line("list", "play 7", "status").polls(10).line("status")
        given = self.play(files, script)
        self.assertEqual(given[2], '{"ok":true}')
        self.assertEqual(json.loads(given[3])["items"][-1], {"id": 7, "file": "clock.odrgx", "bytes": len(clock), "ignored": False, "external": False, "type": "widget"})
        self.assertEqual(json.loads(given[6])["animation"], 7)
        self.assertIsInstance(json.loads(given[6])["seed"], int)

    def test_an_invalid_picture_clock_is_refused_with_its_reason(self):
        files = small_show([animation(1, "one.odrg")])
        good = picture_of(canvas=(60, 6))
        picture = 20 + 12 + 10 + 6
        for reason, data in (("bad-picture", good[:picture + 12] + b"\x02" + good[picture + 13:]),
                             ("bad-settings", good[:20 + 13] + b"\x07" + good[20 + 14:]),
                             ("size-mismatch", picture_of(canvas=(59, 6)))):
            with self.subTest(reason=reason):
                given = self.play(files, Script().polls(5).upload(7, "new.odrgx", data))
                self.assertEqual(given[-1], bad_file(reason))


class PictureClocksOnADrive(unittest.TestCase):
    def test_a_picture_clock_of_a_drive_is_listed_and_plays_its_moving_hands(self):
        files = show_of([{"id": 1, "file": "a.odrgx"}], {"a.odrgx": clock_of()})
        drive = {"pic.odrgx": picture_of()}
        script = [f"poll {T0}", support.line(T0, "list"), support.line(T0, "play 60001")]
        script += [f"poll {T0 + 20 * step}" for step in range(1, 60)] + [support.line(T0 + 1200, "status")]
        run = with_drive(files, drive, script)
        replies = [json.loads(line[len("reply "):]) for line in run.lines if line.startswith("reply ")]
        drives = [item for item in replies[0]["items"] if item["id"] >= 60001]
        self.assertEqual([(item["file"], item["type"]) for item in drives], [("pic.odrgx", "widget")])
        self.assertEqual(replies[-1]["animation"], 60001)
        self.assertIsInstance(replies[-1]["seed"], int)
        produced, _ = refreshes(polled(run.lines))
        pictures = {repr(sorted(data.items())) for _, data in produced[1:]}
        self.assertGreater(len(pictures), 5)


class TheMemory(unittest.TestCase):
    def test_a_show_of_picture_clocks_asks_for_the_memory_of_one_without_them(self):
        target = support.mapping_texts()["legs-20"]
        dial = (PICTURES / "valid" / "dial.odrgx").read_bytes()
        display = (PICTURES / "valid" / "display.odrgx").read_bytes()
        items = [{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrgx"}]
        with_pictures = {"mapping.json": target, "show.json": support.show_text(items, 255, 1), "a.odrgx": dial, "b.odrgx": display}
        without = {"mapping.json": target, "show.json": support.show_text(items, 255, 1), "a.odrgx": clock_of(canvas=(60, 60)),
                   "b.odrgx": clock_of(canvas=(60, 60))}
        script = [f"poll {T0 + 20 * step}" for step in range(200)] + [support.line(T0 + 4000, "status")]
        played = support.start(with_pictures, script)
        self.assertIsNone(played.error)
        self.assertIn('"animation":', played.lines[-1])
        self.assertEqual(played.memory, support.start(without).memory)

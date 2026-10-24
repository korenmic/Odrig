import json
import pathlib
import re
import struct
import subprocess
import tempfile
import unittest
import zlib

from odrig import jsonframes, odrg, odrgx

from . import support
from .test_content import animation, small_show
from .test_playback import T0, Playback, every_20_ms, refreshes
from .test_upload import Script, Uploads, bad_file

TEXTS = support.ROOT / "tests" / "vectors" / "texts"
PICTURES = support.ROOT / "tests" / "vectors" / "procedural"
CANVAS = (20, 10)

# A text on the canvas of these tests: "Hi" in the small font, moving left.
SOURCE = {
    "version": 1,
    "type": "text",
    "width": CANVAS[0],
    "height": CANVAS[1],
    "text": "Hi",
    "font": "small",
    "color": 0xFFC040,
    "background": 0x000010,
    "align": "center",
    "valign": "middle",
    "direction": "auto",
    "wrap": False,
    "effect": "marquee",
    "motion": "left",
    "speed": 20,
    "pause_ms": 1000,
}


def text_of(**settings):
    """The container the converter writes of the source of a text, `encode`."""
    with tempfile.TemporaryDirectory() as folder:
        given = pathlib.Path(folder) / "text.json"
        made = pathlib.Path(folder) / "text.odrgx"
        given.write_text(json.dumps({**SOURCE, **settings}), encoding="utf-8")
        done = subprocess.run(["node", str(support.CONVERTER), "encode", str(given), str(made)], capture_output=True, text=True)
        if done.returncode != 0:
            raise AssertionError(f"the converter did not encode the text: {done.stderr.strip()}")
        return made.read_bytes()


def pass_of(data):
    return odrgx.read_header(data).loop_ms


def with_bad_glyph(data):
    """The text with the font index of its first glyph out of the font."""
    count = struct.unpack_from("<H", data, 20 + 18)[0]
    at = 20 + 28 + count
    return data[:at] + b"\xff\xff" + data[at + 2:]


def png_pixels(path):
    """The pixels of a PNG of the picture vectors in the pixel order of docs/format.md, the
    PNG's bottom row first. The vectors are 8-bit RGB with no filter on their rows."""
    data = path.read_bytes()
    at, stream = 8, b""
    while at < len(data):
        length, kind = struct.unpack_from(">I4s", data, at)
        body = data[at + 8:at + 8 + length]
        if kind == b"IHDR":
            width, height, depth, colour = struct.unpack_from(">IIBB", body)
            if (depth, colour) != (8, 2):
                raise AssertionError(f"{path.name} is not 8-bit RGB")
        elif kind == b"IDAT":
            stream += body
        at += 12 + length
    raw = zlib.decompress(stream)
    stride = 3 * width + 1
    rows = [raw[row * stride:(row + 1) * stride] for row in range(height)]
    if any(row[0] != 0 for row in rows):
        raise AssertionError(f"{path.name} has a filter on a row")
    return width, height, b"".join(row[1:] for row in reversed(rows))


def reasons_of_a_text():
    text = (support.ROOT / "docs" / "reasons.md").read_text(encoding="utf-8")
    section = text.split("\n## Texts in ODRGX\n")[1].split("\n## ")[0]
    return set(re.findall(r"(?m)^\| `([a-z0-9-]+)` \|", section))


def show_of(items, files, **more):
    """A file set on the canvas of these tests, one leg: a show of these items."""
    show = {"version": 1, "brightness": 255, "items": list(items), **more}
    return {"mapping.json": support.one_leg_mapping(*CANVAS), "show.json": json.dumps(show), **files}


def asked_at(times):
    script = []
    for time in times:
        script += [f"poll {T0 + time}", support.line(T0 + time, "status")]
    return script


class TheVectors(unittest.TestCase):
    def test_a_valid_text_is_read_whole_with_its_pass_as_its_loop(self):
        paths = sorted((TEXTS / "valid").glob("*.odrgx"))
        self.assertGreaterEqual(len(paths), 7)
        for path, decoded in zip(paths, support.decode_each([path.read_bytes() for path in paths])):
            with self.subTest(vector=path.name):
                data = path.read_bytes()
                self.assertIsNone(decoded.reason)
                self.assertEqual(decoded.container, (2, pass_of(data), len(data) - 20))
                self.assertEqual(list(decoded.records), [])

    def test_an_invalid_text_is_refused_with_the_reason_of_its_name(self):
        paths = sorted((TEXTS / "invalid").glob("*.odrgx"))
        self.assertGreaterEqual(len(paths), 20)
        for path, decoded in zip(paths, support.decode_each([path.read_bytes() for path in paths])):
            with self.subTest(vector=path.name):
                self.assertEqual(decoded.reason, path.name.split(".")[0])

    def test_the_core_has_every_reason_of_a_text(self):
        self.assertIn("bad-glyph", reasons_of_a_text())
        self.assertLessEqual(reasons_of_a_text(), set(support.host_lines("reasons")))


class ThePictures(unittest.TestCase):
    def test_the_core_draws_every_reference_picture_as_the_converter_does(self):
        manifest = json.loads((PICTURES / "manifest.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(manifest), 19)
        for entry in manifest:
            with self.subTest(picture=entry["picture"]):
                width, height, pixels = png_pixels(PICTURES / entry["picture"])
                data = (support.ROOT / "tests" / "vectors" / entry["file"]).read_bytes()
                self.assertEqual((width, height), (odrgx.read_header(data).width, odrgx.read_header(data).height))
                self.assertEqual(support.rendered(data, [entry["ms"]]), [pixels])

    def test_a_text_is_drawn_again_after_each_pass(self):
        data = text_of()
        total = pass_of(data)
        self.assertEqual(support.rendered(data, [0, 300, total, total + 300]), support.rendered(data, [0, 300]) * 2)

    def test_a_drawn_text_shows_its_colour_on_its_background(self):
        picture = support.rendered(text_of(effect="static", pause_ms=500), [0])[0]
        colours = {picture[at:at + 3] for at in range(0, len(picture), 3)}
        self.assertEqual(colours, {bytes.fromhex("ffc040"), bytes.fromhex("000010")})


class TextsInAShow(Playback):
    def playing_at(self, files, times):
        printed = self.assert_as_the_reference(files, [f"poll {T0}"] + asked_at(times))
        states = [json.loads(line[len("reply "):]) for line in printed if line.startswith('reply {"ok":true,"on"')]
        self.assertEqual(len(states), len(times))
        return [state["animation"] for state in states]

    def test_a_text_plays_as_the_frames_of_its_pictures(self):
        # At 25 pixels a second the text moves every 40 ms, and its pass is whole refreshes.
        text = text_of(speed=25)
        total = pass_of(text)
        self.assertEqual(total % 20, 0)
        frames = jsonframes.Animation(*CANVAS, tuple((20, picture) for picture in support.rendered(text, range(0, total, 20))))
        drawn = self.assert_as_the_reference(show_of([{"id": 1, "file": "a.odrgx"}], {"a.odrgx": text}), every_20_ms(2 * total // 20 + 5))
        played = self.assert_as_the_reference(show_of([{"id": 1, "file": "a.odrg"}], {"a.odrg": odrg.encode(frames)}), every_20_ms(2 * total // 20 + 5))
        self.assertEqual(refreshes(drawn), refreshes(played))

    def test_a_text_has_the_fewest_passes_that_last_the_shortest_time(self):
        text = text_of()
        total = pass_of(text)
        files = show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": text, "b.odrg": support.clip(2, *CANVAS, (1000,))}, min_seconds=3)
        turn = -(-3000 // total) * total
        self.assertEqual(self.playing_at(files, [0, turn - 20, turn, turn + 2980, turn + 3000]), [1, 1, 2, 2, 1])

    def test_a_longest_time_ends_a_text_at_the_end_of_the_pass_it_falls_in(self):
        text = text_of()
        total = pass_of(text)
        self.assertNotEqual(2000 % total, 0)
        files = show_of([{"id": 1, "file": "a.odrgx", "max_seconds": 2}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": text, "b.odrg": support.clip(2, *CANVAS, (1000,))}, min_seconds=10)
        turn = -(-2000 // total) * total
        self.assertEqual(self.playing_at(files, [0, 1980, turn - 20, turn]), [1, 1, 1, 2])

    def test_a_cycle_gives_a_text_its_whole_passes(self):
        text = text_of()
        total = pass_of(text)
        files = show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "cycle": [1, 2], "seconds": 2}], {"a.odrgx": text, "b.odrg": support.clip(2, *CANVAS, (1000,))}, start=3)
        turn = -(-2000 // total) * total
        script = [f"poll {T0}"] + asked_at([0, turn - 20, turn, turn + 1980, turn + 2000, 2 * turn + 2000])
        printed = self.assert_as_the_reference(files, script)
        states = [json.loads(line[len("reply "):]) for line in printed if line.startswith('reply {"ok":true,"on"')]
        self.assertEqual([(state["playing"], state["animation"]) for state in states], [(3, 1), (3, 1), (3, 2), (3, 2), (3, 1), (3, 2)])

    def test_play_and_off_act_at_once_in_the_middle_of_a_pass(self):
        text = text_of()
        files = show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": text, "b.odrg": support.clip(2, *CANVAS, (1000,))})
        script = [f"poll {T0}", f"poll {T0 + 500}", support.line(T0 + 510, "play 2"), f"poll {T0 + 520}", support.line(T0 + 530, "status"),
                  support.line(T0 + 540, "play 1"), support.line(T0 + 550, "off"), f"poll {T0 + 560}", support.line(T0 + 570, "on"), f"poll {T0 + 580}"]
        printed = self.assert_as_the_reference(files, script)
        self.assertIn('"animation":2', [line for line in printed if line.startswith('reply {"ok":true,"on"')][0])
        produced, _ = refreshes([line for line in printed if not line.startswith("reply")])
        self.assertFalse(any(any(data) for data in produced[-2][1].values()))
        self.assertTrue(any(any(data) for data in produced[-1][1].values()))

    def test_list_gives_a_text_its_type(self):
        text = text_of()
        files = show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": text, "b.odrg": support.clip(2, *CANVAS, (1000,))})
        items = json.loads(support.start(files, [f"poll {T0}", support.line(T0, "list")]).lines[-1][len("reply "):])["items"]
        self.assertEqual([item["type"] for item in items], ["text", "frames"])

    def test_a_text_of_another_canvas_is_quarantined_at_the_start(self):
        files = show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": text_of(width=21), "b.odrg": support.clip(2, *CANVAS, (1000,))})
        run = support.start(files, ["error", f"poll {T0}", support.line(T0, "list"), support.line(T0, "status")])
        self.assertEqual(run.lines[0], "error none")
        self.assertIn("file a.odrgx unavailable: size-mismatch", run.logs)
        listed, status = (json.loads(line[len("reply "):]) for line in run.lines if line.startswith("reply "))
        self.assertEqual(listed["items"][0]["fault"], "size-mismatch")
        self.assertEqual(status["animation"], 2)

    def test_a_text_with_a_fault_is_quarantined_and_the_show_goes_on(self):
        bad = with_bad_glyph(text_of())
        self.assertEqual(support.decode_each([bad])[0].reason, "bad-glyph")
        files = show_of([{"id": 1, "file": "b.odrg"}, {"id": 2, "file": "a.odrgx"}], {"a.odrgx": bad, "b.odrg": support.clip(2, *CANVAS, (1000,))}, min_seconds=1)
        # Read whole at the start, the text is quarantined there. After power-on its check
        # finds the fault, with the frames of the other animation on the LEDs meanwhile.
        run = support.start(files, ["error"])
        self.assertEqual(run.lines, ["error none"])
        self.assertIn("file a.odrgx unavailable: bad-glyph", run.logs)
        run = support.start(files, every_20_ms(60) + ["error"], check_first=False)
        self.assertEqual([line for line in run.lines if line.startswith("log ")], ["log file a.odrgx unavailable: bad-glyph"])
        self.assertEqual(run.lines, support.ReferencePlayer(files, check_first=False).run(every_20_ms(60) + ["error"]))
        self.assertEqual(run.lines[-1], "error none")


class UploadsOfTexts(Uploads):
    def test_a_text_is_uploaded_listed_with_its_type_and_played(self):
        files = small_show([animation(1, "one.odrg")])
        text = text_of(width=60, height=6, motion="up")
        script = Script().polls(10).upload(7, "hello.odrgx", text).line("list", "play 7", "status").polls(10)
        given = self.play(files, script)
        self.assertEqual(given[2], '{"ok":true}')
        self.assertEqual(json.loads(given[3])["items"][-1], {"id": 7, "file": "hello.odrgx", "bytes": len(text), "ignored": False, "external": False, "type": "text"})
        self.assertEqual(json.loads(given[5])["animation"], 7)
        self.assertEqual(self.left["hello.odrgx"], text)

    def test_an_invalid_text_is_refused_with_its_reason(self):
        files = small_show([animation(1, "one.odrg")])
        good = text_of(width=60, height=6, motion="up")
        cases = {
            "bad-glyph": with_bad_glyph(good),
            "unknown-font": good[:20] + b"\x09" + good[21:],
            "loop-mismatch": good[:12] + (pass_of(good) + 1).to_bytes(4, "little") + good[16:],
            "size-mismatch": text_of(width=59, height=6, motion="up"),
        }
        for reason, data in cases.items():
            with self.subTest(reason=reason):
                given = self.play(files, Script().polls(5).upload(7, "new.odrgx", data))
                self.assertEqual(given[-1], bad_file(reason))

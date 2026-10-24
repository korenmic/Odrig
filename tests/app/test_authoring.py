import json
import pathlib
import subprocess
import tempfile
import time
import unittest

from odrig import odrgx
from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered
from .test_upload import OK, SPACE, begun, taken

# The text the tests make, as its JSON source has it, for a canvas.
TEXT = {
    "version": 1, "type": "text", "text": "Hi there", "font": "small", "color": 0xFFD040, "background": 0, "align": "center", "valign": "middle",
    "direction": "auto", "wrap": False, "effect": "marquee", "motion": "left", "speed": 20, "pause_ms": 1000,
}


# The clock the tests make, as its JSON source has it, for a canvas.
CLOCK = {
    "version": 1, "type": "widget", "widget": "analog", "seconds": 30, "face": 0xF4ECD0, "hands": 0x202020, "rim": 0xD4A017, "background": 0,
    "speed_min": 60, "speed_max": 600,
}


def status_of(width, height):
    return (200, json.dumps({"ok": True, "on": True, "brightness": 128, "playing": "all", "animation": 1, "fps": 50, "error": None, "width": width,
                             "height": height, "seed": None}, separators=(",", ":")) + "\n")


def stand_in_of(width, height, **upload):
    """A stand-in target with a canvas, two animations and room in its storage, whose
    replies to the words after `upload` are given."""

    def answer(line):
        word = line.split(b" ")[1].decode("ascii")
        reply = upload.get(word, OK)
        return reply(line) if callable(reply) else reply

    return {"status": status_of(width, height), "list": support.LISTED, "space": SPACE, "upload": answer}


def encoded(source):
    """The container the converter's command line writes of a JSON source."""
    with tempfile.TemporaryDirectory() as folder:
        given = pathlib.Path(folder, "source.json")
        made = pathlib.Path(folder, "made.odrgx")
        given.write_text(json.dumps(source), encoding="utf-8")
        subprocess.run(["node", str(support.CONVERTER_TOOL), "encode", str(given), str(made)], check=True, capture_output=True)
        return made.read_bytes()


def top_row_first(picture, width, height):
    """A picture in the pixel order of docs/format.md as a canvas holds it: the top row
    first, three numbers for each pixel."""
    rows = [picture[3 * width * row:3 * width * (row + 1)] for row in range(height)]
    return list(b"".join(reversed(rows)))


class MakingAText(unittest.TestCase):
    def test_the_preview_moves_and_draws_what_the_player_draws_at_its_time(self):
        fields = [["text-words", "Hi there"]]
        with support.StandIn(stand_in_of(60, 60)) as stand_in:
            found = support.run("author-text", address=stand_in.address, settings={"rows": 2, "fields": fields}).seen
        data = encoded({**TEXT, "width": 60, "height": 60})
        loop = odrgx.read_header(data).loop_ms
        self.assertEqual(found["says"], [f"One pass takes {loop / 1000:.2f} seconds."])
        first, later = found["pictures"]
        self.assertGreaterEqual(later["ms"], first["ms"] + 300)
        for shown in (first, later):
            self.assertEqual((shown["width"], shown["height"]), (60, 60))
            self.assertEqual(shown["rgb"], top_row_first(core_support.rendered(data, [shown["ms"]])[0], 60, 60), shown["ms"])
        self.assertNotEqual(first["rgb"], later["rgb"])

    def test_a_character_no_font_has_and_a_block_that_does_not_fit_are_named(self):
        fields = [["text-words", "naïve"], ["text-words", "Hello"], ["text-effect", "static"], ["text-effect", "marquee"], ["text-motion", "up"]]
        with support.StandIn(stand_in_of(60, 6)) as stand_in:
            found = support.run("author-text", address=stand_in.address, settings={"rows": 2, "fields": fields}).seen
        says = found["says"]
        self.assertEqual(says[0], 'The fonts have no letter for "ï" (U+00EF). Write English letters, digits, signs and Hebrew letters. (unsupported-character)')
        self.assertEqual(says[1], "The text cannot be seen whole on the canvas with this effect: a marquee or a pan up or down shows all of it. (does-not-fit)")
        self.assertEqual(says[2], "The text cannot be seen whole on the canvas with this effect: a pan or a marquee shows all of it. (does-not-fit)")
        self.assertEqual(says[3], says[1])
        self.assertRegex(says[4], r"\AOne pass takes [0-9]+\.[0-9]{2} seconds\.\Z")
        self.assertTrue(found["preview"])

    def test_a_text_is_uploaded_as_a_new_animation_listed_as_a_text(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        fields = [["text-words", "Hi"], ["text-motion", "up"]]
        found = support.run("author-text", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "fields": fields, "upload": True}).seen
        self.assertEqual(found["message"], "Uploaded as animation 4 hi.odrgx. It plays in the playlist.")
        data = encoded({**TEXT, "text": "Hi", "motion": "up", "width": 60, "height": 6})
        self.assertEqual((folder / "hi.odrgx").read_bytes(), data)
        self.assertIn({"id": 4, "file": "hi.odrgx", "bytes": len(data), "ignored": False, "external": False, "type": "text"}, json.loads(emulator.command("list"))["items"])
        self.assertEqual([row["id"] for row in found["after"]["rows"]], [1, 2, 4])

    def test_an_upload_of_a_text_can_be_cancelled(self):
        def slowly(line):
            time.sleep(1.5)
            return taken(line)

        with support.StandIn(stand_in_of(60, 6, begin=begun, data=slowly)) as stand_in:
            found = support.run("author-text", address=stand_in.address, settings={"rows": 2, "fields": [["text-words", "Hello world"], ["text-motion", "up"]], "upload": True, "cancel": True}).seen
            sent = [line for _, line in stand_in.lines]
        self.assertEqual(found["uploading"], "Cancelled.")
        self.assertIn(b"upload cancel", sent)
        self.assertTrue(any(line.startswith(b"upload begin 3 hello-world.odrgx ") for line in sent), sent)


class MakingAClock(unittest.TestCase):
    def test_the_preview_draws_the_clock_of_its_seed_and_a_new_time_draws_another(self):
        fields = [["clock-widget", "melting"], ["clock-seconds", "45"]]
        with support.StandIn(stand_in_of(60, 60)) as stand_in:
            found = support.run("author-clock", address=stand_in.address, settings={"rows": 2, "fields": fields}).seen
        self.assertEqual(found["title"], "A clock")
        self.assertEqual(found["says"], ["One loop takes 30.00 seconds.", "One loop takes 45.00 seconds."])
        data = encoded({**CLOCK, "widget": "melting", "seconds": 45, "width": 60, "height": 60})
        first, later, other = found["pictures"]
        self.assertEqual(first["seed"], later["seed"])
        self.assertNotEqual(other["seed"], first["seed"])
        for shown in found["pictures"]:
            self.assertEqual(shown["rgb"], top_row_first(core_support.rendered(data, [shown["ms"]], shown["seed"])[0], 60, 60), (shown["ms"], shown["seed"]))
        self.assertNotEqual(first["rgb"], later["rgb"])

    def test_a_number_out_of_its_range_is_named(self):
        fields = [["clock-seconds", "0"], ["clock-seconds", "30"], ["clock-speed-max", "59"], ["clock-speed-max", "x"]]
        with support.StandIn(stand_in_of(60, 6)) as stand_in:
            found = support.run("author-clock", address=stand_in.address, settings={"rows": 2, "fields": fields}).seen
        self.assertEqual(found["says"], ["The animation cannot be made: seconds is below 1. (out-of-range)", "One loop takes 30.00 seconds.",
                                         "The animation cannot be made: speed_max is below 60. (out-of-range)",
                                         "The animation cannot be made: speed_max is not an integer. (bad-type)"])

    def test_a_clock_is_uploaded_as_a_new_animation_listed_as_a_widget(self):
        folder = entered(self, emulator_support.example_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        fields = [["clock-widget", "digital"]]
        found = support.run("author-clock", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "fields": fields, "upload": True}).seen
        self.assertEqual(found["message"], "Uploaded as animation 4 clock-digital.odrgx. It plays in the playlist.")
        data = encoded({**CLOCK, "widget": "digital", "width": 60, "height": 6})
        self.assertEqual((folder / "clock-digital.odrgx").read_bytes(), data)
        self.assertIn({"id": 4, "file": "clock-digital.odrgx", "bytes": len(data), "ignored": False, "external": False, "type": "widget"},
                      json.loads(emulator.command("list"))["items"])
        self.assertEqual([row["id"] for row in found["after"]["rows"]], [1, 2, 4])

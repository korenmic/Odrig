import json
import pathlib
import subprocess
import tempfile
import time
import unittest

from odrig import odrgx
from odrigctl import client, content
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


class EditingAnInstalledOne(unittest.TestCase):
    """A show on the two-leg mapping, 60 x 6: frames, a text the playlist ignores, frames, a
    clock."""

    def emulator(self, more=None):
        hello = encoded({**TEXT, "text": "Hello", "motion": "up", "width": 60, "height": 6})
        clock = encoded({**CLOCK, "width": 60, "height": 6})
        items = [{"id": 1, "file": "one.odrg"}, {"id": 5, "file": "hello.odrgx", "ignored": True}, {"id": 2, "file": "two.odrg"}, {"id": 7, "file": "clock-analog.odrgx"}]
        files = {"mapping.json": core_support.mapping_texts()["legs-2"], "show.json": json.dumps({"version": 1, "brightness": 128, "items": items}),
                 "one.odrg": core_support.clip(1, 60, 6), "two.odrg": core_support.clip(2, 60, 6), "hello.odrgx": hello, "clock-analog.odrgx": clock}
        for number, name, data in more or ():
            items.append({"id": number, "file": name})
            files[name] = data
        files["show.json"] = json.dumps({"version": 1, "brightness": 128, "items": items})
        folder = emulator_support.installed(pathlib.Path(entered(self, tempfile.TemporaryDirectory()), "show"), files)
        return entered(self, emulator_support.Emulator(folder)), folder

    def test_a_generated_message_clock_opens_no_form_and_keeps_its_bytes(self):
        from tests.core.test_message_clock import message_file
        from tests.core.test_mini import files_for
        files = files_for()
        data = message_file()
        files["message.odrgx"] = data
        files["show.json"] = core_support.show_text([
            {"id": 1, "file": "picture.odrg"}, {"id": 2, "file": "message.odrgx"}], 40, 1)
        folder = emulator_support.installed(pathlib.Path(entered(self, tempfile.TemporaryDirectory()), "show"), files)
        emulator = entered(self, emulator_support.Emulator(folder))
        found = support.run("author-edit", address=f"127.0.0.1:{emulator.port}",
                            settings={"rows": 2, "edit": 2, "refused": True}).seen
        self.assertEqual(found["message"], "Generated message clocks can be previewed and uploaded, but cannot be edited in this form.")
        self.assertFalse(found["formShown"])
        self.assertEqual((folder / "message.odrgx").read_bytes(), data)
        self.assertFalse((folder / "upload.part").exists())

    def test_a_saved_text_keeps_its_id_its_place_and_its_inclusion(self):
        emulator, folder = self.emulator()
        found = support.run("author-edit", address=f"127.0.0.1:{emulator.port}", settings={"rows": 4, "edit": 5, "fields": [["text-words", "Hi there"]]}).seen
        self.assertEqual(found["opened"], {"title": "Animation 5 hello.odrgx", "words": "Hello", "seconds": "30", "button": "Save"})
        self.assertRegex(found["says"], r"\AOne pass takes [0-9.]+ seconds\.\Z")
        self.assertEqual(found["message"], "Saved animation 5 hello.odrgx.")
        saved = encoded({**TEXT, "text": "Hi there", "motion": "up", "width": 60, "height": 6})
        self.assertEqual((folder / "hello.odrgx").read_bytes(), saved)
        items = json.loads(emulator.command("list"))["items"]
        self.assertEqual([item["id"] for item in items], [1, 5, 2, 7])
        self.assertEqual(items[1], {"id": 5, "file": "hello.odrgx", "bytes": len(saved), "ignored": True, "external": False, "type": "text"})
        self.assertEqual([row["id"] for row in found["rows"]], [1, 5, 2, 7])

    def test_a_saved_clock_keeps_its_place(self):
        emulator, folder = self.emulator()
        found = support.run("author-edit", address=f"127.0.0.1:{emulator.port}", settings={"rows": 4, "edit": 7, "fields": [["clock-seconds", "20"]]}).seen
        self.assertEqual((found["opened"]["title"], found["opened"]["seconds"]), ("Animation 7 clock-analog.odrgx", "30"))
        self.assertEqual(found["message"], "Saved animation 7 clock-analog.odrgx.")
        saved = encoded({**CLOCK, "seconds": 20, "width": 60, "height": 6})
        self.assertEqual((folder / "clock-analog.odrgx").read_bytes(), saved)
        self.assertEqual([item["id"] for item in json.loads(emulator.command("list"))["items"]], [1, 5, 2, 7])

    def test_a_picture_clock_opens_no_form_and_the_app_says_why(self):
        rows = ["".join("1" if x in (0, 59) else "0" for x in range(60)) for _ in range(6)]
        picture = encoded({"version": 1, "type": "widget", "width": 60, "height": 6, "widget": "picture-display", "seconds": 30, "speed_min": 60,
                           "speed_max": 600, "direction": "random", "turns": 30, "palette": [0, 0xFFD040], "picture": rows,
                           "fields": [{"left": 20, "top": 0, "width": 20, "height": 6, "font": "tiny", "pattern": "Ih:Mm", "digits": 1, "colons": 1,
                                       "blink": True, "offset": 0}]})
        emulator, folder = self.emulator([(8, "picture.odrgx", picture)])
        found = support.run("author-edit", address=f"127.0.0.1:{emulator.port}", settings={"rows": 5, "edit": 8, "refused": True}).seen
        self.assertEqual(found["message"], "This clock is made from a picture: it cannot be edited here.")
        self.assertFalse(found["formShown"])
        self.assertEqual((folder / "picture.odrgx").read_bytes(), picture)
        self.assertNotIn("upload.part", [path.name for path in folder.iterdir()])

    def test_a_change_by_another_controller_is_said_and_nothing_is_overwritten(self):
        emulator, folder = self.emulator()
        other = encoded({**TEXT, "text": "Other", "motion": "up", "width": 60, "height": 6})

        def elsewhere():
            with client.Session(http=f"127.0.0.1:{emulator.port}", timeout=5) as session:
                self.assertTrue(content.is_ok(content.upload(session, 5, "hello.odrgx", other)))

        found = support.run("author-edit", address=f"127.0.0.1:{emulator.port}", settings={"rows": 4, "edit": 5, "fields": [["text-words", "Hi there"]], "changedElsewhere": True},
                            steps=[elsewhere]).seen
        self.assertEqual(found["message"], "Another controller changed this animation since it was opened. Your changes are still here; open it again to see the new one. (stale)")
        self.assertEqual((folder / "hello.odrgx").read_bytes(), other)
        self.assertEqual(found["after"], {"title": "Animation 5 hello.odrgx", "words": "Hi there", "seconds": "30", "button": "Save"})
        self.assertNotIn("upload.part", [path.name for path in folder.iterdir()])

    def test_only_a_text_or_a_clock_of_the_boards_own_storage_has_edit(self):
        items = [{"id": 1, "file": "hello.odrgx", "bytes": 60, "ignored": False, "external": False, "type": "text"},
                 {"id": 2, "file": "two.odrg", "bytes": 900, "ignored": False, "external": False, "type": "frames"},
                 {"id": 3, "file": "clock-analog.odrgx", "bytes": 40, "ignored": False, "external": False, "type": "widget"},
                 {"id": 60001, "file": "sunrise.odrgx", "bytes": 40, "external": True, "type": "widget"}]
        listed = (200, json.dumps({"ok": True, "items": items, "next": None}, separators=(",", ":")) + "\n")
        with support.StandIn({**stand_in_of(60, 6), "list": listed}) as stand_in:
            found = support.run("author-edit", address=stand_in.address, settings={"rows": 4, "menus": [1, 2, 3, 60001]}).seen
        self.assertEqual({id: "Edit" in menu for id, menu in found["menus"].items()}, {"1": True, "2": False, "3": True, "60001": False})

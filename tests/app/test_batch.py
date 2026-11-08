"""Ready-made animations picked several at once and uploaded as one run."""

import json
import math
import pathlib
import tempfile
import unittest

from odrig import catalog
from tests.core import support as core_support
from tests.emulator import support as emulator_support
from . import support
from .test_target import entered

NAME_RULE = "Use a filename of at most 32 lowercase letters, digits, dots, - or _, ending in .odrg or .odrgx."


def kb(size):
    return str(math.ceil(size / 1000))


class Picking(unittest.TestCase):
    """The list a pick of several files makes, before anything is sent."""

    def setUp(self):
        self.show = entered(self, emulator_support.example_show())
        self.hello = (self.show / "hello.odrg").read_bytes()
        self.dvd = (self.show / "dvd.odrg").read_bytes()
        self.media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        for name, data in (("hello.odrg", self.hello), ("dvd.odrg", self.dvd), ("notes.png", b"not an animation"),
                           ("big.odrg", core_support.clip(1, 60, 60, (20, 20)))):
            (self.media / name).write_bytes(data)

    def test_files_picked_at_once_are_listed_checked_and_named_and_add_more_adds_to_them(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        found = support.run("batch", address=f"127.0.0.1:{emulator.port}", media=self.media, settings={
            "rows": 2,
            "first": [["hello.odrg", "Sun Rise.odrg"], "hello.odrg", ["dvd.odrg", "HELLO.odrg"]],
            "more": [["notes.png", "notes.txt"], "big.odrg", "hello.odrg"],
            "renames": [[0, "Bad Name.odrg"], [0, "hello-2.odrg"], [0, "sun-rise.odrg"]],
            "remove": [4, 3, 2, 1],
        }).seen
        self.assertEqual(found["chooser"], ["Choose ready-made animations"])
        self.assertTrue(found["multiple"])
        three = [{"name": "sun-rise.odrg", "state": "waiting", "why": None}, {"name": "hello-2.odrg", "state": "waiting", "why": None},
                 {"name": "hello-3.odrg", "state": "waiting", "why": None}]
        self.assertEqual(found["listed"], three)
        self.assertTrue(found["formHidden"])
        total = 2 * len(self.hello) + len(self.dvd)
        self.assertEqual(found["sum"], f"3 animations, {kb(total)} KB.")
        self.assertEqual(found["button"], {"words": "Upload 3 animations", "disabled": False, "reason": None})
        # The same file picked again is listed once; one of another ending and one of another
        # canvas are refused with today's words.
        self.assertEqual(found["more"], three + [
            {"name": "notes.txt", "state": "refused: Choose an .odrg or .odrgx animation file.", "why": None},
            {"name": "big.odrg", "state": "refused: The animation canvas is 60 × 60; the target needs 60 × 6.", "why": None}])
        self.assertEqual(found["sumMore"], f"3 animations, {kb(total)} KB.")
        mend = {"words": "Upload 3 animations", "disabled": True, "reason": "Mend the names marked in the list."}
        self.assertEqual(found["renamed"], [
            {"rows": [NAME_RULE, None, None, None, None], "button": mend},
            {"rows": ["Another file of this batch has this name.", "Another file of this batch has this name.", None, None, None], "button": mend},
            {"rows": [None] * 5, "button": {"words": "Upload 3 animations", "disabled": False, "reason": None}},
        ])
        # Four rows removed leave one, which stays a list.
        self.assertEqual(found["afterRemove"], ["sun-rise.odrg"])
        self.assertTrue(found["listShown"])

    def test_names_follow_the_storage_until_the_start(self):
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        emulator_support.installed(top / "odrig", {"sun-rise.odrg": self.hello})
        emulator = entered(self, emulator_support.Emulator(self.show, "--drive", top))
        found = support.run("batch", address=f"127.0.0.1:{emulator.port}", media=self.media, settings={
            "rows": 3, "first": [["hello.odrg", "Sun Rise.odrg"], "hello.odrg"], "renames": [[1, "kept.odrg"]], "store": "internal"}).seen
        # On the card the card's root has sun-rise.odrg; in the board's storage the root has
        # hello.odrg. The edited name stays.
        self.assertEqual([row["name"] for row in found["listed"]], ["sun-rise-2.odrg", "hello.odrg"])
        self.assertEqual(found["storage"], "external")
        self.assertEqual(found["afterStore"], ["sun-rise.odrg", "kept.odrg"])
        self.assertEqual(found["destination"], "Internal /")

    def test_the_sum_against_the_free_space_disables_the_button(self):
        emulator = entered(self, emulator_support.Emulator(self.show, "--storage", 28000))
        found = support.run("batch", address=f"127.0.0.1:{emulator.port}", media=self.media, settings={
            "rows": 2, "first": [["hello.odrg", "a.odrg"], ["hello.odrg", "b.odrg"], ["dvd.odrg", "c.odrg"], ["dvd.odrg", "d.odrg"]]}).seen
        self.assertTrue(found["button"]["disabled"])
        self.assertRegex(found["button"]["reason"], r"\AThese animations need [0-9]+ KB and the installation has [0-9]+ KB free\.\Z")

    def test_one_file_opens_todays_form(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        found = support.run("batch", address=f"127.0.0.1:{emulator.port}", media=self.media, settings={"mode": "one", "rows": 2, "file": "hello.odrg"}).seen
        self.assertTrue(found["facts"].startswith("Ready-made animation, 60 × 6,"))
        self.assertIsNone(found["list"])
        self.assertEqual(found["button"], "Upload to the installation")


class Look(unittest.TestCase):
    """The list before and after its run, and its line on a scrolled screen, at the sizes
    of test_look."""

    def test_the_list_and_its_line_keep_the_look_rules(self):
        from .test_look import SIZES, apart, contrast
        show = entered(self, emulator_support.example_show())
        hello = (show / "hello.odrg").read_bytes()
        media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (media / "hello.odrg").write_bytes(hello)
        broken = bytearray(core_support.clip(4, 60, 6, (20,) * 3))
        broken[len(broken) // 2:] = b"\xff" * (len(broken) - len(broken) // 2)
        (media / "broken.odrg").write_bytes(bytes(broken))
        (media / "big.odrg").write_bytes(core_support.clip(1, 60, 60, (20, 20)))
        files = [["hello.odrg", "a-file-name-of-twenty-seven-x.odrg"], ["broken.odrg", "broken.odrg"], ["big.odrg", "big.odrg"], ["hello.odrg", "short.odrg"]]
        for size in SIZES:
            fresh = entered(self, emulator_support.example_show())
            emulator = entered(self, emulator_support.Emulator(fresh))
            found = support.run("batch", address=f"127.0.0.1:{emulator.port}", media=media, size=size, settings={"mode": "look", "rows": 2, "files": files}).seen
            for name in ("before", "after"):
                screen = found[name]
                where = f"{size[0]} wide, {name}"
                self.assertLessEqual(screen["scrollWidth"], screen["width"], where)
                controls = [control for control in screen["controls"] if control["group"] == "screen"]
                for control in controls:
                    self.assertGreaterEqual(control["bottom"] - control["top"], 44 - 0.01, f"{where}: {control['what']}")
                    self.assertGreaterEqual(control["right"] - control["left"], 44 - 0.01, f"{where}: {control['what']}")
                for position, first in enumerate(controls):
                    for second in controls[position + 1:]:
                        self.assertGreaterEqual(apart(first, second), 8 - 0.01, f"{where}: {first['what']} and {second['what']}")
                for text in screen["texts"]:
                    if not text["stale"]:
                        self.assertGreaterEqual(contrast(text["colour"], text["behind"]), 7, f"{where}: {text['what']}")
                        self.assertGreaterEqual(text["size"], 14, f"{where}: {text['what']}")
            self.assertTrue(found["line"]["shown"], size)
            self.assertGreater(found["scrolled"], 0, size)
            self.assertGreaterEqual(found["line"]["top"], 0, size)
            self.assertLess(found["line"]["bottom"], 120, size)


BUSY = (200, '{"ok":false,"error":"busy"}\n')
STALE = (200, '{"ok":false,"error":"stale"}\n')
WAITING = "Waiting for the installation to answer."


class Between:
    """A stand-in that hands each line to the emulator, and can answer some lines itself:
    with a refusal, with nothing while it is silent, or with a card gone from `space`."""

    def __init__(self, emulator):
        self.emulator = emulator
        self.rules = []
        self.silent = False
        self.card_gone = False
        self.lines = []
        # The card goes once the first upload has ended with success.
        self.gone_after_an_end = False

    def __call__(self, line):
        self.lines.append(line)
        if self.silent:
            return None
        for rule in self.rules:
            reply = rule(line)
            if reply is not None:
                return reply
        reply = self.emulator.command(line.decode("utf-8")).decode("utf-8")
        if self.card_gone and line == b"space":
            given = json.loads(reply)
            given["external"] = {"present": False, "free": None, "total": None, "read_only": True}
            reply = json.dumps(given) + "\n"
        if self.gone_after_an_end and line.startswith(b"upload end ") and reply.startswith('{"ok":true'):
            self.card_gone = True
        return 200, reply

    def times(self, start, reply, count):
        """Answers the first `count` lines that begin with `start` with `reply`."""
        left = [count]

        def rule(line):
            if line.startswith(start) and left[0] > 0:
                left[0] -= 1
                return reply
            return None

        self.rules.append(rule)

    def sent(self, start):
        return [line for line in self.lines if line.startswith(start)]


class Running(unittest.TestCase):
    """The run of a list: one file after another, while the app is used."""

    def setUp(self):
        self.show = entered(self, emulator_support.example_show())
        self.hello = (self.show / "hello.odrg").read_bytes()
        self.media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        (self.media / "hello.odrg").write_bytes(self.hello)
        # A file of many pieces, so that something can happen while it is sent.
        self.long = core_support.clip(3, 60, 6, (20,) * 400, compressed=False)
        (self.media / "long.odrg").write_bytes(self.long)
        broken = bytearray(core_support.clip(4, 60, 6, (20,) * 3))
        broken[len(broken) // 2:] = b"\xff" * (len(broken) - len(broken) // 2)
        (self.media / "broken.odrg").write_bytes(bytes(broken))

    def ran(self, address, files, steps=(), **settings):
        return support.run("batch", address=address, media=self.media, steps=steps, settings={"mode": "run", "rows": 2, "files": files, **settings}).seen

    def between(self, emulator):
        between = Between(emulator)
        stand_in = entered(self, support.StandIn(between))
        return between, stand_in.address

    def test_ten_files_go_to_the_boards_storage_one_after_another_while_the_app_is_used(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        names = [f"clip-{number:02}.odrg" for number in range(1, 11)]
        found = self.ran(f"127.0.0.1:{emulator.port}", [["hello.odrg", name] for name in names],
                         actions=[["row", 0, "^(sending|uploaded)"], ["elsewhere"], ["forms"]], tap=True)
        self.assertEqual(found["rows"], [f"uploaded as animation {id}" for id in range(4, 14)])
        self.assertEqual(found["end"], "10 of 10 uploaded.")
        self.assertTrue(any(line.startswith("Uploading 1 of 10: clip-01.odrg") for line in found["lines"]), found["lines"])
        self.assertTrue(any(line.startswith("Uploading 10 of 10: clip-10.odrg") for line in found["lines"]), found["lines"])
        self.assertTrue(found["onAnimations"].startswith("Uploading "), found["onAnimations"])
        self.assertTrue(found["deletionLocked"])
        self.assertEqual(found["single"], {"disabled": True, "reason": "A batch upload is under way.", "list": True})
        self.assertEqual(found["second"], "A batch upload is under way. Choose these when it has ended.")
        self.assertEqual(found["text"], {"disabled": True, "reason": "A batch upload is under way."})
        self.assertEqual(found["tapped"], {"screen": "upload", "line": None})
        self.assertIsNone(found["retry"])
        for name in names:
            self.assertEqual((self.show / name).read_bytes(), self.hello)
        listed = [item["file"] for item in json.loads((self.show / "show.json").read_text(encoding="utf-8"))["items"] if "file" in item]
        self.assertEqual(listed[-10:], names)

    def test_ten_files_go_to_a_card_folder_whose_catalog_moves_at_each_file(self):
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        drive = top / "odrig"
        (drive / "night" / "deep").mkdir(parents=True)
        (drive / "night" / "deep" / "old.odrg").write_bytes(self.hello)
        _, refused = catalog.rebuild(catalog.Storage(drive, drive=True), names=["night/deep/old.odrg"], canvas=(60, 6))
        self.assertEqual(refused, [])
        emulator = entered(self, emulator_support.Emulator(self.show, "--drive", top))
        names = [f"star-{number:02}.odrg" for number in range(1, 11)]
        found = self.ran(f"127.0.0.1:{emulator.port}", [["hello.odrg", name] for name in names], rows=2, path="night/deep")
        self.assertTrue(all(row.startswith("uploaded") for row in found["rows"]), found["rows"])
        self.assertEqual(found["end"], "10 of 10 uploaded.")
        for name in names:
            self.assertEqual((drive / "night" / "deep" / name).read_bytes(), self.hello)

    def test_a_file_refused_in_the_middle_is_marked_and_the_run_goes_on(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        found = self.ran(f"127.0.0.1:{emulator.port}", [["hello.odrg", "a.odrg"], ["broken.odrg", "b.odrg"], ["hello.odrg", "c.odrg"]])
        self.assertEqual(found["rows"][0], "uploaded as animation 4")
        self.assertTrue(found["rows"][1].startswith("failed: "), found["rows"])
        self.assertEqual(found["rows"][2], "uploaded as animation 5")
        self.assertEqual(found["end"], "2 of 3 uploaded, 1 failed.")
        self.assertEqual(found["retry"], "Try the failed again")
        self.assertFalse((self.show / "b.odrg").exists())

    def test_a_busy_begin_is_tried_again_and_a_busy_end_is_not_counted(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        between, address = self.between(emulator)
        between.times(b"upload begin ", BUSY, 2)
        between.times(b"upload end ", BUSY, 1)
        found = self.ran(address, [["hello.odrg", "a.odrg"], ["hello.odrg", "b.odrg"]], actions=[["row", 0, "try 2 of 30"]])
        self.assertEqual(found["rows"], ["uploaded as animation 4", "uploaded as animation 5"])
        self.assertEqual(len(between.sent(b"upload begin ")), 4)

    def test_a_stale_begin_starts_the_turn_again_once_and_a_second_fails_the_file(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        between, address = self.between(emulator)
        between.times(b"upload begin 4 a.odrg ", STALE, 1)
        between.times(b"upload begin 5 b.odrg ", STALE, 2)
        found = self.ran(address, [["hello.odrg", "a.odrg"], ["hello.odrg", "b.odrg"]])
        self.assertEqual(found["rows"][0], "uploaded as animation 4")
        self.assertEqual(found["rows"][1], "failed: The chosen id was taken, or the firmware cannot confirm a safe new upload. No file bytes were sent.")

    def test_an_upload_dropped_while_the_app_was_away_starts_again_once(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        between, address = self.between(emulator)
        found = self.ran(address, [["long.odrg", "a.odrg"], ["hello.odrg", "b.odrg"]],
                         actions=[["row", 0, "^sending [1-9]"], ["hide"], ["sleep", 300], ["step"], ["show"]],
                         steps=[lambda: emulator.command("upload cancel")])
        self.assertEqual(found["rows"], ["uploaded as animation 4", "uploaded as animation 5"])
        self.assertIn("Paused while the app was not on the screen.", found["lines"])
        self.assertEqual(len(between.sent(b"upload begin 4 ")), 2)
        self.assertEqual((self.show / "a.odrg").read_bytes(), self.long)

    def test_an_upload_dropped_while_the_app_was_shown_fails_its_file(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        between, address = self.between(emulator)
        found = self.ran(address, [["long.odrg", "a.odrg"], ["hello.odrg", "b.odrg"]], actions=[["row", 0, "^sending [1-9]"], ["step"]],
                         steps=[lambda: emulator.command("upload cancel")])
        self.assertTrue(found["rows"][0].startswith("failed: "), found["rows"])
        self.assertEqual(found["rows"][1], "uploaded as animation 4")

    def test_a_target_that_stops_answering_is_waited_for_and_the_run_goes_on(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        between, address = self.between(emulator)

        def silent():
            between.silent = True

        def speaks():
            between.silent = False

        found = self.ran(address, [["long.odrg", "a.odrg"], ["hello.odrg", "b.odrg"]],
                         actions=[["row", 0, "^sending [1-9]"], ["step"], ["line", WAITING, 30000], ["step"]], steps=[silent, speaks], timeout=120000)
        self.assertEqual(found["rows"], ["uploaded as animation 4", "uploaded as animation 5"])
        self.assertEqual((self.show / "a.odrg").read_bytes(), self.long)

    def test_a_card_taken_out_at_a_files_turn_ends_the_run(self):
        top = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        drive = top / "odrig"
        drive.mkdir()
        (drive / "old.odrg").write_bytes(self.hello)
        _, refused = catalog.rebuild(catalog.Storage(drive, drive=True), names=["old.odrg"], canvas=(60, 6))
        self.assertEqual(refused, [])
        emulator = entered(self, emulator_support.Emulator(self.show, "--drive", top))
        between, address = self.between(emulator)
        between.gone_after_an_end = True
        found = self.ran(address, [["hello.odrg", f"{letter}.odrg"] for letter in "abcd"], rows=3)
        self.assertTrue(found["rows"][0].startswith("uploaded"), found["rows"])
        self.assertEqual(found["rows"][1:], ["failed: External storage is absent or read-only. Check the displayed destination before retrying.", "not sent", "not sent"])
        self.assertEqual(found["end"], "1 of 4 uploaded, 1 failed, 2 not sent.")

    def test_a_change_of_target_ends_the_run(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        found = self.ran(f"127.0.0.1:{emulator.port}", [["long.odrg", "a.odrg"], ["hello.odrg", "b.odrg"], ["hello.odrg", "c.odrg"]],
                         actions=[["row", 0, "^sending [1-9]"], ["target"]])
        self.assertEqual(found["rows"], ["failed: The target changed.", "not sent", "not sent"])

    def test_stop_ends_the_run_after_the_file_in_progress_and_the_failed_are_tried_again(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        found = self.ran(f"127.0.0.1:{emulator.port}", [["long.odrg", "a.odrg"], ["hello.odrg", "b.odrg"], ["hello.odrg", "c.odrg"]],
                         actions=[["row", 0, "^sending [1-9]"], ["stop"]], retry=True)
        self.assertEqual(found["rows"], ["uploaded as animation 4", "not sent", "not sent"])
        self.assertEqual(found["end"], "1 of 3 uploaded, 2 not sent.")
        self.assertEqual(found["retried"], ["uploaded as animation 4", "uploaded as animation 5", "uploaded as animation 6"])
        self.assertEqual(found["retriedEnd"], "2 of 2 uploaded.")


if __name__ == "__main__":
    unittest.main()

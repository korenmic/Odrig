import json
import pathlib
import tempfile
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

MAPPING = core_support.mapping_texts()["legs-2"]


def clip(seed, durations=(20, 20, 20)):
    return core_support.clip(seed, 60, 6, durations)


class Show(unittest.TestCase):
    def folder(self, items, files, **more):
        """A show folder on the two-leg mapping, with these items and files."""
        work = entered(self, tempfile.TemporaryDirectory())
        show = {"version": 1, "brightness": 128, "items": list(items), **more}
        return emulator_support.installed(pathlib.Path(work, "show"), {"mapping.json": MAPPING, "show.json": json.dumps(show), **files})

    def emulator(self, folder, **settings):
        started = entered(self, emulator_support.Emulator(folder, **settings))
        return started, f"127.0.0.1:{started.port}"

    def listed(self, emulator):
        """Every item the emulator lists, asked for part by part, and the number of parts."""
        items, position, parts = [], 0, 0
        while position is not None:
            reply = json.loads(emulator.command(f"list {position}"))
            items += reply["items"]
            position = reply["next"]
            parts += 1
        return items, parts


class TheState(Show):
    def test_the_demo_show_plays_its_playlist_and_the_screen_says_what_status_says(self):
        emulator, address = self.emulator(entered(self, emulator_support.demo_show()))
        found = support.run("state", address=address, settings={"rows": 2, "until": "Now 1 hello\\.odrg .*(49|50|51) refreshes a second"})
        status = emulator.status()
        self.assertEqual((status["on"], status["brightness"], status["playing"], status["animation"], status["error"]), (True, 128, "all", 1, None))
        self.assertEqual({name: found.seen[name] for name in ("power", "brightness", "playing", "now")},
                         {"power": "ON", "brightness": "Brightness 128", "playing": "Playlist", "now": "Now 1 hello.odrg"})
        self.assertRegex(found.seen["fps"], r"\A(49|50|51) refreshes a second\Z")
        self.assertEqual(found.seen["rows"], [{"id": 1, "text": "1 hello.odrg", "marked": True}, {"id": 2, "text": "2 dvd.odrg", "marked": False}])
        self.assertEqual((found.seen["none"], found.seen["silent"], found.seen["dimmed"]), (None, None, False))

    def test_a_cycle_that_plays_is_named_by_its_id_and_is_no_row(self):
        emulator, address = self.emulator(entered(self, emulator_support.example_show()))
        self.assertEqual(emulator.status()["playing"], 3)
        found = support.run("state", address=address, settings={"rows": 2, "until": "Now 1 hello\\.odrg"})
        self.assertEqual((found.seen["playing"], found.seen["now"]), ("Cycle 3", "Now 1 hello.odrg"))
        self.assertEqual([row["text"] for row in found.seen["rows"]], ["1 hello.odrg", "2 dvd.odrg"])
        self.assertEqual([item["id"] for item in self.listed(emulator)[0]], [1, 2, 3])

    def test_a_show_without_an_animation_says_so_and_nothing_plays(self):
        emulator, address = self.emulator(self.folder([], {}))
        found = support.run("state", address=address, settings={"rows": 0, "until": "No animation is installed\\."})
        self.assertEqual({name: found.seen[name] for name in ("power", "playing", "now", "none")},
                         {"power": "ON", "playing": "Nothing plays", "now": None, "none": "No animation is installed."})
        self.assertEqual(found.seen["rows"], [])

    def test_an_invalid_show_has_its_reason_in_the_place_of_what_plays(self):
        folder = entered(self, emulator_support.example_show())
        emulator_support.with_show_fault(folder)
        emulator, address = self.emulator(folder)
        found = support.run("state", address=address, settings={"rows": 0, "line": "^The installed show is invalid"})
        self.assertEqual(found.seen["playing"], "The installed show is invalid: undefined-id 99.")
        self.assertEqual((found.seen["now"], found.seen["rows"], found.seen["none"]), (None, [], None))
        self.assertEqual(found.seen["power"], "ON")

    def test_what_somebody_else_sets_is_on_the_screen_within_two_seconds(self):
        emulator, address = self.emulator(entered(self, emulator_support.demo_show()))

        def others():
            self.assertEqual(emulator.command("brightness 40"), b'{"ok":true}\n')
            self.assertEqual(emulator.command("off"), b'{"ok":true}\n')

        found = support.run("changed", address=address, steps=[others], settings={"rows": 2, "until": "Brightness 40", "within": 4000})
        self.assertEqual((found.seen["before"]["power"], found.seen["before"]["brightness"]), ("ON", "Brightness 128"))
        self.assertEqual((found.seen["after"]["power"], found.seen["after"]["brightness"]), ("OFF", "Brightness 40"))
        self.assertLess(found.seen["ms"], 2000)


class TheList(Show):
    def test_a_show_whose_items_take_more_than_one_reply_is_listed_whole(self):
        items = [{"id": 100 + number, "file": f"animation-{number:02d}.odrg"} for number in range(1, 41)]
        folder = self.folder(items, {item["file"]: clip(item["id"]) for item in items})
        emulator, address = self.emulator(folder)
        listed, parts = self.listed(emulator)
        self.assertEqual((len(listed), parts > 1), (40, True))
        found = support.run("state", address=address, settings={"rows": 40})
        self.assertEqual([row["text"] for row in found.seen["rows"]], [f"{item['id']} {item['file']}" for item in items])
        self.assertEqual([row["id"] for row in found.seen["rows"] if row["marked"]], [101])

    def test_the_mark_moves_on_with_the_playlist(self):
        # Two animations of one second, each played twice in its turn.
        second = (500, 500)
        items = [{"id": 1, "file": "one.odrg", "repeat": 2}, {"id": 2, "file": "two.odrg", "repeat": 2}]
        emulator, address = self.emulator(self.folder(items, {"one.odrg": clip(1, second), "two.odrg": clip(2, second)}))
        found = support.run("follows", address=address, settings={"rows": 2, "ms": 6500})
        marks = [seen["marked"] for seen in found.seen]
        self.assertEqual({len(marked) for marked in marks}, {1})
        order = [marked[0] for marked in marks]
        self.assertGreaterEqual(len(order), 3)
        self.assertTrue(all(first != second for first, second in zip(order, order[1:])), order)
        self.assertEqual({seen["playing"] for seen in found.seen}, {"Playlist"})
        for seen in found.seen:
            self.assertEqual(seen["now"], f"Now {seen['marked'][0]} {'one' if seen['marked'][0] == 1 else 'two'}.odrg")

    def upload(self, emulator, number, name):
        work = entered(self, tempfile.TemporaryDirectory())
        path = pathlib.Path(work, name)
        path.write_bytes(clip(77))
        done = emulator_support.run_tool("--http", f"127.0.0.1:{emulator.port}", "upload", number, path)
        self.assertEqual((done.status, done.out), (0, '{"ok":true}\n'), done.err)

    def test_an_animation_that_somebody_else_uploads_is_in_the_list_within_twelve_seconds(self):
        emulator, address = self.emulator(entered(self, emulator_support.example_show()))
        found = support.run("changed", address=address, steps=[lambda: self.upload(emulator, 9, "new.odrg")], settings={"rows": 2, "until": "new\\.odrg 9 \u00b7", "within": 13000})
        self.assertEqual([row["text"] for row in found.seen["after"]["rows"]], ["1 hello.odrg", "2 dvd.odrg", "9 new.odrg"])
        self.assertLess(found.seen["ms"], 12000)

    def test_an_animation_the_list_does_not_have_is_asked_for_at_once_when_it_plays(self):
        emulator, address = self.emulator(entered(self, emulator_support.example_show()))

        def uploaded_and_played():
            self.upload(emulator, 9, "new.odrg")
            self.assertEqual(emulator.command("play 9"), b'{"ok":true}\n')

        found = support.run("changed", address=address, steps=[uploaded_and_played], settings={"rows": 2, "until": "Now 9 new\\.odrg", "within": 5000})
        self.assertLess(found.seen["ms"], 3000)
        self.assertEqual((found.seen["after"]["playing"], found.seen["after"]["now"]), ("Playlist", "Now 9 new.odrg"))
        self.assertEqual([(row["id"], row["marked"]) for row in found.seen["after"]["rows"]], [(1, False), (2, False), (9, True)])


class WhileItDoesNotAnswer(Show):
    def test_the_values_are_dimmed_and_a_line_says_for_how_long(self):
        folder = entered(self, emulator_support.demo_show())
        port = support.free_port()
        first = emulator_support.Emulator(folder, port=port)
        self.addCleanup(first.stop)
        steps = [first.stop, lambda: entered(self, emulator_support.Emulator(folder, port=port))]
        found = support.run("unanswered", address=f"127.0.0.1:{port}", steps=steps, settings={"rows": 2})
        self.assertEqual((found.seen["before"]["silent"], found.seen["before"]["dimmed"], found.seen["before"]["listDimmed"]), (None, False, False))
        # The screen keeps what the last replies said, dimmed, and stays the show screen.
        first_seen = found.seen["first"]
        self.assertEqual((first_seen["dimmed"], first_seen["listDimmed"], first_seen["shown"]), (True, True, "animations"))
        self.assertEqual((first_seen["power"], first_seen["playing"], len(first_seen["rows"])), ("ON", "Playlist", 2))
        said = r"\AThe installation has not answered for ([0-9]+) seconds?\.\Z"
        self.assertRegex(first_seen["silent"], said)
        self.assertRegex(found.seen["later"]["silent"], said)
        seconds = [int(seen["silent"].split(" for ")[1].split(" ")[0]) for seen in (first_seen, found.seen["later"])]
        self.assertIn(seconds[1] - seconds[0], (2, 3), seconds)
        self.assertEqual((found.seen["again"]["silent"], found.seen["again"]["dimmed"], found.seen["again"]["listDimmed"]), (None, False, False))


class OffTheScreen(Show):
    def test_nothing_is_sent_while_the_app_is_not_on_the_screen_and_a_status_at_once_when_it_is_again(self):
        target = entered(self, support.StandIn(support.SOUND))
        counts = []
        count = lambda: counts.append(len(target.lines))
        support.run("hidden", address=target.address, steps=[count, count, count], settings={"rows": 2})
        hidden, three_seconds_later, shown_again = counts
        self.assertEqual(three_seconds_later, hidden)
        self.assertGreater(shown_again, three_seconds_later)
        self.assertEqual(target.lines[three_seconds_later], ("/odrig", b"status"))


if __name__ == "__main__":
    unittest.main()



class ATargetThatStillReads(unittest.TestCase):
    """After its start a target plays at once and reads its animations while it plays.
    Until it has, it answers `list` with `busy`."""

    BUSY = {"status": support.PLAYING, "list": (200, '{"ok":false,"error":"busy"}\n')}

    def test_the_list_is_asked_for_again_a_second_later_and_the_rows_come(self):
        # Two rounds of status and list, together with capacity and the catalogs, find the
        # target reading.
        with support.StandIn(self.BUSY, self.BUSY, self.BUSY, self.BUSY, self.BUSY, self.BUSY, support.SOUND) as target:
            found = support.run("reads", address=target.address, settings={"rows": 2})
        before, after = found.seen["before"], found.seen["after"]
        self.assertEqual((before["power"], before["playing"], before["rows"], before["none"], before["message"]), ("ON", "Playlist", [], None, None))
        self.assertEqual([row["text"] for row in after["rows"]], ["1 one.odrg", "2 two.odrg"])
        self.assertEqual((after["none"], after["silent"], after["message"]), (None, None, None))
        self.assertLess(found.seen["ms"], 4000)
        asked = [line for _, line in target.lines if line.startswith(b"list")]
        self.assertGreaterEqual(len(asked), 3)
        self.assertEqual(set(asked), {b"list 0"})

    def test_an_emulator_that_has_just_started_shows_its_state_and_its_rows_while_it_reads_them(self):
        # Four dense animations of twenty seconds and more: the core reads them for five
        # seconds at the least.
        work = entered(self, tempfile.TemporaryDirectory())
        files = {"mapping.json": MAPPING}
        items = []
        for number, seconds in enumerate((20, 21, 22, 23), start=1):
            files[f"dense{number}.odrg"] = core_support.dense_clip(60, 6, seconds)
            items.append({"id": number, "file": f"dense{number}.odrg"})
        files["show.json"] = json.dumps({"version": 1, "brightness": 128, "items": items})
        folder = emulator_support.installed(pathlib.Path(work, "show"), files)
        emulator = entered(self, emulator_support.Emulator(folder, checked=False))
        # The list is given at once, with no sizes while the files are read.
        self.assertIn(None, [item["bytes"] for item in json.loads(emulator.command("list"))["items"]])
        found = support.run("reads", address=f"127.0.0.1:{emulator.port}", settings={"rows": 4})
        before, after = found.seen["before"], found.seen["after"]
        self.assertEqual((before["power"], before["playing"], before["message"]), ("ON", "Playlist", None))
        self.assertEqual([row["text"] for row in after["rows"]], [f"{number} dense{number}.odrg" for number in (1, 2, 3, 4)])
        self.assertIsNone(after["message"])

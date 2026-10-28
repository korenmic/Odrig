import json
import unittest

from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

OK = (200, '{"ok":true}\n')
# A stand-in target that carries out every command of the app.
OBEYS = {**support.SOUND, "play": OK, "on": OK, "off": OK, "brightness": OK}


class Controls(unittest.TestCase):
    def emulator(self, show=emulator_support.demo_show):
        started = entered(self, emulator_support.Emulator(entered(self, show())))
        return started, f"127.0.0.1:{started.port}"

    def sent(self, emulator, scenario, done, **settings):
        """Runs a scenario against an emulator. Gives what it found, and the command lines
        the emulator took over HTTP that are no `status`, no `list`, no `space`, no saved
        order and no catalog, each with the time it came at, up to the first one that `done`
        says is the last."""
        with emulator_support.EventStream(emulator.port) as stream:
            found = support.run(scenario, address=f"127.0.0.1:{emulator.port}", settings=settings)
            events = stream.read_until(lambda events: any(done(json.loads(event.data)["line"]) for event in events if event.kind == "log"), 10)
        logged = emulator_support.of_kind(events, "log")
        self.assertEqual({entry["transport"] for entry in logged}, {"http"})
        return found.seen, [(entry["line"], entry["ms"]) for entry in logged if entry["line"].split(" ")[0] not in ("status", "list", "space", "catalog") and not entry["line"].startswith("order get")]


class Buttons(Controls):
    def test_off_and_on_switch_the_leds_and_the_one_in_effect_is_marked(self):
        emulator, address = self.emulator()
        presses = [{"press": "Off", "until": "OFF Brightness"}, {"press": "On", "until": "ON Brightness"}]
        seen, lines = self.sent(emulator, "presses", lambda line: line == "on", rows=2, presses=presses)
        self.assertEqual([line for line, _ in lines], ["off", "on"])
        self.assertEqual([(step["power"], step["on"], step["off"]) for step in seen], [("OFF", False, True), ("ON", True, False)])
        self.assertIs(emulator.status()["on"], True)
        self.assertEqual({step["message"] for step in seen}, {None})

    def test_an_animation_of_the_list_is_played_and_the_playlist_goes_back_to_its_start(self):
        emulator, address = self.emulator()
        presses = [{"row": 2, "until": "Now 2 dvd\\.odrg"}, {"press": "Play this folder", "pressIn": "#level-head", "until": "Now 1 hello\\.odrg"}]
        seen, lines = self.sent(emulator, "presses", lambda line: line == "play all", rows=2, presses=presses)
        self.assertEqual([line for line, _ in lines], ["play 2", "play all"])
        self.assertEqual([(step["playing"], step["now"], [row["id"] for row in step["rows"] if row["marked"]]) for step in seen],
                         [("Playlist", "Now 2 dvd.odrg", [2]), ("Playlist", "Now 1 hello.odrg", [1])])
        status = emulator.status()
        self.assertEqual((status["playing"], status["animation"]), ("all", 1))

    def test_from_a_cycle_the_playlist_button_goes_to_the_playlist_and_no_button_plays_a_cycle(self):
        emulator, address = self.emulator(emulator_support.example_show)
        self.assertEqual(emulator.status()["playing"], 3)
        presses = [{"press": "Play this folder", "pressIn": "#level-head", "until": "Now 1 hello\\.odrg .*Playlist"}]
        seen, lines = self.sent(emulator, "presses", lambda line: line == "play all", rows=2, presses=presses)
        self.assertEqual([line for line, _ in lines], ["play all"])
        self.assertEqual(emulator.status()["playing"], "all")
        self.assertEqual(seen[0]["buttons"], ["Ignore 1 hello.odrg in playlist", "Select 1 hello.odrg", "Delete 1 hello.odrg", "Repeat 1 hello.odrg this turn",
                                              "Save the repeat of 1 hello.odrg for every turn", "Restore the default repeat of 1 hello.odrg", "On", "Off", "Add animation", "Select", "All, 2", "Internal, 2", "External, 0", "All, 2", "Normal, 2", "Text, 0",
                                              "Widget, 0", "Play this folder", "Play 1 hello.odrg", "Actions for 1 hello.odrg", "Play 2 dvd.odrg", "Actions for 2 dvd.odrg"])


class TheSlider(Controls):
    def test_while_it_is_moved_at_most_five_commands_a_second_go_out_and_the_last_value_is_always_sent(self):
        emulator, address = self.emulator()
        values = list(range(10, 70))
        seen, lines = self.sent(emulator, "slides", lambda line: line == "brightness 69", rows=2, values=values, every=20, looks=[600])
        self.assertEqual({line.split(" ")[0] for line, _ in lines}, {"brightness"})
        times = [ms for _, ms in lines]
        # Sixty moves in a little over a second.
        self.assertGreaterEqual(len(lines), 4)
        self.assertLessEqual(len(lines), 9)
        for position, began in enumerate(times):
            self.assertLessEqual(sum(1 for ms in times[position:] if ms < began + 900), 5, lines)
        self.assertEqual(lines[-1][0], "brightness 69")
        self.assertEqual(emulator.status()["brightness"], 69)
        self.assertEqual((seen[0]["slider"], seen[0]["number"], seen[0]["brightness"]), (69, "69", "Brightness 69"))

    def test_a_single_move_is_sent_at_once(self):
        emulator, address = self.emulator()
        seen, lines = self.sent(emulator, "slides", lambda line: line == "brightness 33", rows=2, values=[33], every=0, looks=[400])
        self.assertEqual([line for line, _ in lines], ["brightness 33"])
        self.assertEqual(emulator.status()["brightness"], 33)

    def test_a_status_does_not_move_it_while_it_is_held(self):
        emulator, address = self.emulator()
        others = [lambda: emulator.command("brightness 10"), lambda: emulator.command("brightness 30")]
        found = support.run("held", address=address, steps=others, settings={"rows": 2})
        self.assertEqual(found.seen["whileHeld"], {**found.seen["whileHeld"], "slider": 200, "number": "200", "brightness": "Brightness 10"})
        self.assertEqual((found.seen["letGo"]["slider"], found.seen["letGo"]["brightness"]), (200, "Brightness 200"))
        self.assertEqual(found.seen["later"], {**found.seen["later"], "slider": 30, "number": "30", "brightness": "Brightness 30"})

    def test_a_status_does_not_move_it_for_a_second_after_its_command(self):
        # The stand-in obeys nothing: its status says 128 whatever it was sent.
        target = entered(self, support.StandIn(OBEYS))
        found = support.run("slides", address=target.address, settings={"rows": 2, "values": [200], "every": 0, "looks": [600, 2200]})
        soon, later = found.seen
        self.assertEqual((soon["slider"], soon["brightness"]), (200, "Brightness 128"))
        self.assertEqual((later["slider"], later["number"]), (128, "128"))
        self.assertEqual([line for _, line in target.lines].count(b"brightness 200"), 1)


class TheField(Controls):
    """The brightness typed into the field beside the slider."""

    def standing(self, acts):
        """Runs the acts against a stand-in whose status says 128 whatever it was sent.
        Gives the looks and the brightness lines it was sent."""
        target = entered(self, support.StandIn(OBEYS))
        found = support.run("typed", address=target.address, settings={"rows": 2, "acts": acts})
        return found.seen, [line.decode() for _, line in target.lines if line.startswith(b"brightness")]

    def test_enter_sends_the_typed_value_and_the_slider_stands_at_it(self):
        emulator, address = self.emulator()
        acts = [{"type": "8", "look": "typed"}, {"enter": True, "until": "Brightness 8", "look": "entered"}]
        seen, lines = self.sent(emulator, "typed", lambda line: line == "brightness 8", rows=2, acts=acts)
        self.assertEqual([line for line, _ in lines], ["brightness 8"])
        self.assertEqual((seen["typed"]["slider"], seen["typed"]["number"], seen["typed"]["brightness"]), (8, "8", "Brightness 128"))
        self.assertEqual((seen["entered"]["slider"], seen["entered"]["number"], seen["entered"]["focused"]), (8, "8", True))
        self.assertEqual(emulator.status()["brightness"], 8)

    def test_leaving_the_field_sends_the_typed_value(self):
        emulator, address = self.emulator()
        acts = [{"type": "40"}, {"leave": True, "until": "Brightness 40", "look": "left"}]
        seen, lines = self.sent(emulator, "typed", lambda line: line == "brightness 40", rows=2, acts=acts)
        self.assertEqual([line for line, _ in lines], ["brightness 40"])
        self.assertEqual((seen["left"]["slider"], seen["left"]["number"], seen["left"]["focused"]), (40, "40", False))
        self.assertEqual(emulator.status()["brightness"], 40)

    def test_enter_and_then_leaving_the_field_send_once(self):
        seen, lines = self.standing([{"type": "41"}, {"enter": True, "wait": 300}, {"leave": True, "wait": 300, "look": "left"}])
        self.assertEqual(lines, ["brightness 41"])
        self.assertEqual((seen["left"]["slider"], seen["left"]["number"]), (41, "41"))

    def test_typed_values_move_the_slider_and_nothing_is_sent_while_typing(self):
        acts = [{"type": "1", "look": "1"}, {"type": "12", "look": "12"}, {"type": "120", "look": "120"}, {"type": "1200", "look": "1200"},
                {"type": "12a0", "look": "letter"}, {"type": "", "look": "empty"}, {"wait": 1300, "look": "later"}]
        seen, lines = self.standing(acts)
        self.assertEqual(lines, [])
        self.assertEqual([(seen[name]["slider"], seen[name]["number"]) for name in ("1", "12", "120", "1200", "letter", "empty", "later")],
                         [(1, "1"), (12, "12"), (120, "120"), (120, "1200"), (120, "120"), (120, ""), (120, "")])

    def test_a_move_of_the_slider_wins_over_text_not_sent(self):
        emulator, address = self.emulator()
        acts = [{"type": "200", "look": "typed"}, {"slide": 30, "look": "slid"}, {"release": True, "until": "Brightness 30", "look": "released"}]
        seen, lines = self.sent(emulator, "typed", lambda line: line == "brightness 30", rows=2, acts=acts)
        self.assertEqual([line for line, _ in lines], ["brightness 30"])
        self.assertEqual((seen["typed"]["slider"], seen["typed"]["focused"]), (200, True))
        self.assertEqual((seen["slid"]["slider"], seen["slid"]["number"], seen["slid"]["focused"]), (30, "30", False))
        self.assertEqual((seen["released"]["slider"], seen["released"]["number"]), (30, "30"))

    def test_leading_zeros_are_read_away_and_the_same_value_again_sends_nothing(self):
        seen, lines = self.standing([{"type": "080", "look": "typed"}, {"enter": True, "wait": 200, "look": "entered"}, {"type": "080"}, {"enter": True, "wait": 200, "look": "again"}])
        self.assertEqual(lines, ["brightness 80"])
        self.assertEqual((seen["typed"]["slider"], seen["typed"]["number"]), (80, "080"))
        self.assertEqual((seen["entered"]["slider"], seen["entered"]["number"]), (80, "80"))
        self.assertEqual((seen["again"]["slider"], seen["again"]["number"]), (80, "80"))

    def test_the_value_in_force_an_empty_field_and_256_send_nothing_and_256_is_said_under_the_slider(self):
        acts = [{"type": "128"}, {"enter": True, "look": "equal"}, {"type": ""}, {"enter": True, "look": "empty"}, {"type": "256", "look": "typed"},
                {"enter": True, "look": "over"}, {"type": "2", "look": "next"}, {"type": "256"}, {"leave": True, "wait": 300, "look": "left"}]
        seen, lines = self.standing(acts)
        self.assertEqual(lines, [])
        for name in ("equal", "empty", "over", "left"):
            self.assertEqual((seen[name]["slider"], seen[name]["number"]), (128, "128"), name)
        self.assertEqual((seen["typed"]["slider"], seen["typed"]["number"]), (128, "256"))
        self.assertEqual([seen[name]["range"] for name in ("equal", "empty", "over", "next", "left")],
                         [None, None, "The brightness is 0 to 255.", None, "The brightness is 0 to 255."])
        self.assertEqual(seen["over"]["focused"], True)

    def test_a_commit_while_the_app_is_hidden_sends_nothing(self):
        acts = [{"type": "77"}, {"hide": True, "wait": 100}, {"leave": True, "look": "hidden"}, {"hide": False, "wait": 1500, "look": "back"}]
        seen, lines = self.standing(acts)
        self.assertEqual(lines, [])
        self.assertEqual((seen["hidden"]["slider"], seen["hidden"]["number"], seen["hidden"]["range"]), (128, "128", None))
        self.assertEqual((seen["back"]["slider"], seen["back"]["number"]), (128, "128"))

    def test_a_status_leaves_the_field_alone_while_it_holds_text_not_sent(self):
        emulator, address = self.emulator()
        acts = [{"type": "90", "look": "typed"}, {"step": True, "until": "Brightness 10", "wait": 1300, "look": "whileTyped"}, {"type": ""},
                {"leave": True, "look": "left"}, {"wait": 1300, "look": "later"}]
        found = support.run("typed", address=address, steps=[lambda: emulator.command("brightness 10")], settings={"rows": 2, "acts": acts})
        seen = found.seen
        self.assertEqual((seen["whileTyped"]["slider"], seen["whileTyped"]["number"], seen["whileTyped"]["brightness"]), (90, "90", "Brightness 10"))
        self.assertEqual((seen["left"]["slider"], seen["left"]["number"]), (128, "128"))
        self.assertEqual((seen["later"]["slider"], seen["later"]["number"]), (10, "10"))
        self.assertEqual(emulator.status()["brightness"], 10)

    def test_commits_in_a_row_keep_at_most_five_sends_a_second_and_the_last_is_sent(self):
        emulator, address = self.emulator()
        acts = [act for value in range(10, 70) for act in ({"type": str(value)}, {"enter": True, "wait": 20})] + [{"until": "Brightness 69", "look": "last"}]
        seen, lines = self.sent(emulator, "typed", lambda line: line == "brightness 69", rows=2, acts=acts)
        self.assertEqual({line.split(" ")[0] for line, _ in lines}, {"brightness"})
        times = [ms for _, ms in lines]
        self.assertGreaterEqual(len(lines), 4)
        for position, began in enumerate(times):
            self.assertLessEqual(sum(1 for ms in times[position:] if ms < began + 900), 5, lines)
        self.assertEqual(lines[-1][0], "brightness 69")
        self.assertEqual((seen["last"]["slider"], seen["last"]["number"]), (69, "69"))


class TheOrder(Controls):
    def lines(self, target):
        return [line.decode() for _, line in target.lines]

    def test_what_the_operator_asked_for_is_sent_before_a_status_that_waits_and_a_status_follows_it_at_once(self):
        slow = entered(self, support.StandIn(OBEYS, delay=1.2))
        support.run("acts", address=slow.address, settings={"acts": [{"after": 300, "press": "Off"}], "then": 4200})
        lines = self.lines(slow)
        self.assertEqual(lines[:2], ["status", "status"])
        self.assertEqual(lines[2:4], ["off", "status"], lines)
        self.assertEqual(lines.count("off"), 1)
        self.assertEqual(slow.together, 1)

    def test_a_brightness_that_waits_is_replaced_by_a_newer_one(self):
        slow = entered(self, support.StandIn(OBEYS, delay=1.0))
        acts = [{"after": 100, "slide": 50}, {"after": 250, "slide": 60}, {"after": 250, "slide": 70}, {"after": 50}]
        support.run("acts", address=slow.address, settings={"acts": acts, "then": 2600})
        lines = self.lines(slow)
        self.assertEqual([line for line in lines if line.startswith("brightness")], ["brightness 70"], lines)
        self.assertEqual(lines[lines.index("brightness 70") + 1], "status")

    def test_a_command_that_got_no_answer_is_not_sent_again(self):
        deaf = entered(self, support.StandIn({**OBEYS, "off": None}))
        found = support.run("acts", address=deaf.address, settings={"acts": [{"after": 300, "press": "Off"}], "then": 7500})
        lines = self.lines(deaf)
        self.assertEqual(lines.count("off"), 1)
        # After the five seconds of the time limit the app asks for the status again.
        self.assertIn("status", lines[lines.index("off") + 1:])
        self.assertEqual(found.seen["link"], "Answers")


if __name__ == "__main__":
    unittest.main()

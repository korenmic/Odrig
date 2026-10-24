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
        the emulator took over HTTP that are no `status` and no `list`, each with the time
        it came at, up to the first one that `done` says is the last."""
        with emulator_support.EventStream(emulator.port) as stream:
            found = support.run(scenario, address=f"127.0.0.1:{emulator.port}", settings=settings)
            events = stream.read_until(lambda events: any(done(json.loads(event.data)["line"]) for event in events if event.kind == "log"), 10)
        logged = emulator_support.of_kind(events, "log")
        self.assertEqual({entry["transport"] for entry in logged}, {"http"})
        return found.seen, [(entry["line"], entry["ms"]) for entry in logged if entry["line"].split(" ")[0] not in ("status", "list", "space")]


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
        presses = [{"press": "2 dvd.odrg", "until": "Now 2 dvd\\.odrg"}, {"press": "Playlist from the start", "until": "Now 1 hello\\.odrg"}]
        seen, lines = self.sent(emulator, "presses", lambda line: line == "play all", rows=2, presses=presses)
        self.assertEqual([line for line, _ in lines], ["play 2", "play all"])
        self.assertEqual([(step["playing"], step["now"], [row["id"] for row in step["rows"] if row["marked"]]) for step in seen],
                         [("Playlist", "Now 2 dvd.odrg", [2]), ("Playlist", "Now 1 hello.odrg", [1])])
        status = emulator.status()
        self.assertEqual((status["playing"], status["animation"]), ("all", 1))

    def test_from_a_cycle_the_playlist_button_goes_to_the_playlist_and_no_button_plays_a_cycle(self):
        emulator, address = self.emulator(emulator_support.example_show)
        self.assertEqual(emulator.status()["playing"], 3)
        presses = [{"press": "Playlist from the start", "until": "Playlist Now 1 hello\\.odrg"}]
        seen, lines = self.sent(emulator, "presses", lambda line: line == "play all", rows=2, presses=presses)
        self.assertEqual([line for line, _ in lines], ["play all"])
        self.assertEqual(emulator.status()["playing"], "all")
        self.assertEqual(seen[0]["buttons"], ["On", "Off", "Playlist from the start", "1 hello.odrg", "2 dvd.odrg"])


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

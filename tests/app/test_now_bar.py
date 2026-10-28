import json
import unittest

from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

OK = (200, '{"ok":true}\n')
# The animations of the stand-in: internal ones of each kind, one ignored, and the card's,
# one in a folder of it; and its cycle and its folder.
ITEMS = [
    {"id": 1, "file": "one.odrg", "bytes": 1000, "ignored": False, "external": False, "type": "frames"},
    {"id": 2, "file": "two.odrg", "bytes": 1000, "ignored": True, "external": False, "type": "frames"},
    {"id": 3, "file": "words.odrgx", "bytes": 1000, "ignored": False, "external": False, "type": "text"},
    {"id": 4, "file": "time.odrgx", "bytes": 1000, "ignored": False, "external": False, "type": "widget"},
    {"id": 60001, "file": "card.odrg", "bytes": 1000, "external": True, "type": "frames"},
    {"id": 60002, "file": "night/deep.odrg", "bytes": 1000, "external": True, "type": "frames"},
    {"id": 9, "cycle": [1, 3]},
    {"id": 60003, "playlist": "night", "external": True},
]


def status_of(animation, playing="all", on=True, error=None, **more):
    return json.dumps({"ok": True, "on": on, "brightness": 128, "playing": playing, "animation": animation, "fps": 50, "error": error, **more}) + "\n"


def space_of(writable):
    external = {"present": True, "free": 1000000, "total": 2000000, "read_only": not writable}
    return json.dumps({"ok": True, "free": 8372224, "total": 10354688, "animations": 4, "external": external}) + "\n"


class Target:
    """A stand-in whose status says what the test sets, and which lists ITEMS."""

    def __init__(self, test, items=ITEMS, writable=True, **replies):
        self.status = status_of(1)
        self.items = items
        listed = json.dumps({"ok": True, "items": items, "next": None}) + "\n"
        self.stand_in = entered(test, support.StandIn({"status": lambda line: (200, self.status), "list": (200, listed), "space": (200, space_of(writable)),
                                                        "ignore": OK, "remove": OK, **replies}))

    def lines(self):
        return [line.decode() for _, line in self.stand_in.lines]

    def sent(self):
        """The lines the app sent that are no request of its own."""
        return [line for line in self.lines() if line.split(" ")[0] not in ("status", "list", "space", "order", "catalog", "fault")]


def run(target, acts, rows=5, size=support.SIZE, steps=()):
    return support.run("nowbar", address=target.stand_in.address, settings={"rows": rows, "acts": acts}, size=size, steps=steps).seen


INTERNAL = [["Ignore", "Select", "Delete"], []]


class ThePlaceAndTheStates(unittest.TestCase):
    def test_it_stands_between_the_name_and_the_line_of_what_plays_while_a_playlist_turn_plays(self):
        emulator = entered(self, emulator_support.Emulator(entered(self, emulator_support.demo_show())))
        seen = support.run("nowbar", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "acts": [{"untilBar": "Select 1 hello.odrg", "look": "first"}]}).seen
        bar = seen["first"]["bar"]
        self.assertEqual((bar["previous"], bar["next"]), ("now", "playing"))
        self.assertEqual(bar["lines"][0], ["Ignore", "Select", "Delete"])
        self.assertEqual(bar["named"][:3], ["Ignore 1 hello.odrg in playlist", "Select 1 hello.odrg", "Delete 1 hello.odrg"])

    def test_it_is_hidden_while_nothing_a_cycle_a_test_or_an_invalid_show_plays_and_while_the_list_has_not_the_animation(self):
        target = Target(self)
        states = [("all", 1, None, True), (None, None, None, False), (9, 1, None, False), (None, None, "undefined-id 99", False), ("all", 77, None, False),
                  (60003, 60002, None, True), ("all", 1, None, True)]
        steps = [lambda playing=playing, animation=animation, error=error: setattr(target, "status", status_of(animation, playing, error=error))
                 for playing, animation, error, _ in states]
        acts = [act for number in range(len(states)) for act in ({"step": True}, {"wait": 1300, "look": str(number)})]
        seen = run(target, acts, steps=steps)
        self.assertEqual([seen[str(number)]["bar"] is not None for number in range(len(states))], [shows for *_, shows in states])

    def test_it_shows_while_the_leds_are_off(self):
        target = Target(self)
        target.status = status_of(1, on=False)
        seen = run(target, [{"untilBar": "Select 1 one.odrg", "look": "off"}])
        self.assertEqual(seen["off"]["bar"]["lines"], INTERNAL)


class ItsActions(unittest.TestCase):
    def lines_for(self, animation, **target):
        stand_in = Target(self, **target)
        stand_in.status = status_of(animation)
        rows = 5 if target.get("items") is None else len([item for item in target["items"] if "file" in item])
        seen = run(stand_in, [{"wait": 1500, "look": "bar"}], rows=rows)
        return seen["bar"]["bar"]

    def test_they_are_the_row_menus_but_the_moves_in_short_words_on_two_lines(self):
        cases = (
            (1, {}, INTERNAL, ["Ignore 1 one.odrg in playlist", "Select 1 one.odrg", "Delete 1 one.odrg"]),
            (2, {}, [["Restore", "Select", "Delete"], []], ["Restore 2 two.odrg to playlist", "Select 2 two.odrg", "Delete 2 two.odrg"]),
            (3, {}, [["Ignore", "Select", "Delete"], ["Edit"]], ["Ignore 3 words.odrgx in playlist", "Select 3 words.odrgx", "Delete 3 words.odrgx", "Edit 3 words.odrgx"]),
            (4, {}, [["Ignore", "Select", "Delete"], ["Edit"]], ["Ignore 4 time.odrgx in playlist", "Select 4 time.odrgx", "Delete 4 time.odrgx", "Edit 4 time.odrgx"]),
            (60001, {}, [["Delete"], []], ["Delete 60001 card.odrg"]),
            (60001, {"writable": False}, [["External storage is read-only."], []], []),
            (1, {"items": [{"id": 1, "file": "one.odrg", "bytes": 1000, "external": False}]}, [["This software allows no change."], []], []),
        )
        for animation, target, lines, named in cases:
            with self.subTest(animation=animation, target=target):
                bar = self.lines_for(animation, **target)
                self.assertEqual(bar["lines"], lines)
                self.assertEqual(bar["named"], named)

    def test_ignore_ends_the_turn_and_the_bar_follows_the_next_animation(self):
        emulator = entered(self, emulator_support.Emulator(entered(self, emulator_support.demo_show())))
        acts = [{"untilBar": "Select 1 hello.odrg"}, {"bar": "Ignore 1 hello.odrg in playlist"}, {"untilBar": "Select 2 dvd.odrg", "look": "after"}]
        seen = support.run("nowbar", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "acts": acts}).seen
        self.assertEqual(seen["after"]["now"], "Now 2 dvd.odrg")
        self.assertEqual(emulator.status()["animation"], 2)

    def test_delete_asks_the_menus_question_first(self):
        target = Target(self)
        seen = run(target, [{"untilBar": "Delete 1 one.odrg"}, {"bar": "Delete 1 one.odrg", "look": "asked"}, {"press": "Keep it", "wait": 400, "look": "kept"}])
        self.assertEqual(seen["asked"]["question"], "Remove animation 1 one.odrg from the installation?")
        self.assertIsNone(seen["kept"]["question"])
        self.assertEqual(target.sent(), [])
        seen = run(target, [{"untilBar": "Delete 1 one.odrg"}, {"bar": "Delete 1 one.odrg"}, {"press": "Remove it", "wait": 600}])
        self.assertEqual(target.sent(), ["remove 1"])

    def test_select_turns_on_the_selection_at_the_root_with_the_filters_showing_the_row_ticked_just_below_the_panel(self):
        items = [{"id": number, "file": f"animation-{number:02d}.odrg", "bytes": 1000, "ignored": False, "external": False, "type": "frames"} for number in range(1, 31)]
        items += [{"id": 60001, "file": "night/deep.odrg", "bytes": 1000, "external": True, "type": "frames"}, {"id": 60003, "playlist": "night", "external": True}]
        target = Target(self, items=items)
        target.status = status_of(25)
        acts = [{"untilBar": "Select 25 animation-25.odrg"}, {"open": "night"}, {"filter": ["type", "Text"], "look": "before"}, {"bar": "Select 25 animation-25.odrg", "wait": 300, "look": "after"}]
        seen = run(target, acts, rows=30)
        self.assertEqual((seen["before"]["level"], seen["before"]["filters"]), ("night", ["All", "Text"]))
        after = seen["after"]
        self.assertEqual((after["level"], after["filters"], after["selecting"], after["checked"]), ("Root", ["All", "All"], True, [25]))
        self.assertGreater(after["scrolled"], 0)
        self.assertAlmostEqual(after["rowTops"]["25"], after["panelBottom"] + 8, delta=1)

    def test_its_buttons_are_disabled_while_the_installation_does_not_answer(self):
        target = Target(self)
        steps = [lambda: target.stand_in.replies.__setitem__(0, {**target.stand_in.replies[0], "status": None})]
        seen = run(target, [{"untilBar": "Select 1 one.odrg", "look": "answers"}, {"step": True}, {"until": "has not answered", "ms": 12000, "look": "silent"}], steps=steps)
        self.assertEqual(seen["answers"]["bar"]["lines"], INTERNAL)
        self.assertEqual(seen["silent"]["bar"]["lines"], [["Ignore (disabled)", "Select (disabled)", "Delete (disabled)"], []])
        self.assertTrue(seen["silent"]["stale"])

    def test_its_buttons_are_disabled_while_the_selection_is_locked(self):
        target = Target(self, **{"remove": lambda line: (support.time.sleep(2.5), OK)[1]})
        acts = [{"untilBar": "Select 1 one.odrg"}, {"press": "Select", "in": "#list-head"}, {"press": "Select all"}, {"press": "Delete selected"},
                {"press": "Remove it", "wait": 600, "look": "deleting"}, {"wait": 4000, "look": "after"}]
        seen = run(target, acts)
        self.assertEqual(seen["deleting"]["bar"]["lines"], [["Ignore (disabled)", "Select (disabled)", "Delete (disabled)"], []])
        self.assertEqual(seen["after"]["bar"]["lines"], INTERNAL)


if __name__ == "__main__":
    unittest.main()

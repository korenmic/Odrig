import json
import pathlib
import re
import tempfile
import unittest

from tests.core import support as core_support

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



def long_loops(folder):
    """A show on the two-leg mapping whose two animations loop in 5 seconds: 6 loops of the
    show's 30 seconds each."""
    items = [{"id": 1, "file": "hello.odrg"}, {"id": 2, "file": "dvd.odrg"}]
    files = {"mapping.json": core_support.mapping_texts()["legs-2"], "show.json": json.dumps({"version": 1, "brightness": 128, "items": items}),
             "hello.odrg": core_support.clip(1, 60, 6, (1000,) * 5), "dvd.odrg": core_support.clip(2, 60, 6, (1000,) * 5)}
    return emulator_support.installed(pathlib.Path(folder, "show"), files)


TURN = re.compile(r"\AAnimation 1 hello\.odrg plays (\d+) loops? this turn; loop (\d+) is playing\.\Z")


class RepeatThis(unittest.TestCase):
    def emulator(self):
        work = entered(self, tempfile.TemporaryDirectory())
        folder = long_loops(work)
        emulator = entered(self, emulator_support.Emulator(folder))
        return emulator, folder

    def run_on(self, emulator, acts):
        with emulator_support.EventStream(emulator.port) as stream:
            seen = support.run("nowbar", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "acts": acts}).seen
            logged = emulator_support.of_kind(stream.read_for(0.5), "log")
        return seen, [entry["line"] for entry in logged if entry["line"].startswith("repeat")]

    def test_its_button_sends_the_typed_count_and_the_app_says_the_turn(self):
        emulator, _ = self.emulator()
        acts = [{"untilBar": "Repeat 1 hello.odrg this turn", "look": "before"}, {"type": "9"}, {"bar": "Repeat 1 hello.odrg this turn"},
                {"until": "plays 9 loops this turn", "look": "after"}]
        seen, lines = self.run_on(emulator, acts)
        self.assertEqual(seen["before"]["bar"]["lines"], [["Ignore", "Select", "Delete"], ["Repeat this", "[6]"], ["Save", "Restore default (disabled)"]])
        self.assertEqual(seen["before"]["bar"]["named"][3:], ["Repeat 1 hello.odrg this turn", "Loops of 1 hello.odrg this turn", "Save the repeat of 1 hello.odrg for every turn",
                                                              "Restore the default repeat of 1 hello.odrg"])
        self.assertEqual(lines, ["repeat 1 9"])
        self.assertRegex(seen["after"]["message"], TURN)
        self.assertEqual(seen["after"]["question"], None)
        self.assertEqual(emulator.status()["repeat"], 9)

    def test_done_sends_it_and_never_saves(self):
        emulator, folder = self.emulator()
        seen, lines = self.run_on(emulator, [{"untilBar": "Repeat 1 hello.odrg this turn"}, {"type": "7"}, {"enter": True}, {"until": "plays 7 loops this turn", "look": "after"}])
        self.assertEqual(lines, ["repeat 1 7"])
        self.assertTrue(seen["after"]["focused"])
        self.assertFalse((folder / "repeats.txt").exists())

    def test_save_keeps_the_typed_count_or_the_one_in_force_and_restore_default_brings_the_own_count_back(self):
        emulator, folder = self.emulator()
        acts = [{"untilBar": "Save the repeat of 1 hello.odrg for every turn"}, {"bar": "Save the repeat of 1 hello.odrg for every turn"},
                {"until": "Saved: animation 1 hello.odrg plays 6 loops every turn", "look": "untouched"}, {"type": "4"}, {"leave": True},
                {"bar": "Save the repeat of 1 hello.odrg for every turn"}, {"until": "Saved: animation 1 hello.odrg plays 4 loops every turn", "wait": 1300, "look": "typed"},
                {"bar": "Restore the default repeat of 1 hello.odrg"}, {"until": "Default restored", "wait": 1300, "look": "restored"}]
        seen, lines = self.run_on(emulator, acts)
        self.assertEqual(lines, ["repeat 1 6 save", "repeat 1 4 save", "repeat 1 default"])
        self.assertRegex(seen["untouched"]["message"], r"\ASaved: animation 1 hello\.odrg plays 6 loops every turn\. It plays 6 loops this turn; loop \d is playing\.\Z")
        self.assertEqual((seen["typed"]["bar"]["lines"][2], seen["typed"]["field"]), (["Save", "Restore default"], "4"))
        self.assertRegex(seen["restored"]["message"], r"\ADefault restored: animation 1 hello\.odrg plays its own count again\. It plays 6 loops this turn; loop \d is playing\.\Z")
        self.assertEqual((seen["restored"]["bar"]["lines"][2], seen["restored"]["field"]), (["Save", "Restore default (disabled)"], "6"))
        self.assertEqual((folder / "repeats.txt").read_bytes(), b"odrig-repeats 1\n")
        self.assertIsNone(seen["restored"]["question"])

    def test_0_65536_and_an_empty_field_send_nothing_and_say_the_range(self):
        target = Target(self)
        target.status = status_of(1, repeat=8, loop=3, saved=None)
        acts = [{"untilBar": "Repeat 1 one.odrg this turn"}]
        for text in ("0", "65536", ""):
            acts += [{"type": text}, {"bar": "Repeat 1 one.odrg this turn", "look": f"repeat {text}"}, {"press": "OK"}, {"type": text},
                     {"bar": "Save the repeat of 1 one.odrg for every turn", "look": f"save {text}"}, {"press": "OK"}, {"type": text}, {"enter": True, "look": f"enter {text}"},
                     {"press": "OK"}]
        seen = run(target, acts)
        self.assertEqual(target.sent(), [])
        for name, look in seen.items():
            self.assertEqual((look["message"], look["field"]), ("A repeat is 1 to 65,535.", "8"), name)

    def test_the_field_is_kept_while_it_has_the_focus_and_its_text_is_dropped_a_second_after_it_is_left(self):
        target = Target(self)
        target.status = status_of(1, repeat=8, loop=3, saved=None)
        steps = [lambda: setattr(target, "status", status_of(2, repeat=5, loop=1, saved=None))]
        acts = [{"untilBar": "Repeat 1 one.odrg this turn"}, {"type": "12"}, {"step": True, "wait": 2500, "look": "focused"}, {"leave": True, "wait": 300, "look": "left"},
                {"wait": 2200, "look": "later"}]
        seen = run(target, acts, steps=steps)
        self.assertEqual((seen["focused"]["field"], seen["focused"]["now"], seen["focused"]["bar"]["named"][0]), ("12", "Now 2 two.odrg", "Ignore 1 one.odrg in playlist"))
        self.assertEqual((seen["left"]["field"], seen["left"]["bar"]["named"][0]), ("12", "Ignore 1 one.odrg in playlist"))
        self.assertEqual((seen["later"]["field"], seen["later"]["bar"]["named"][0]), ("5", "Restore 2 two.odrg to playlist"))
        self.assertEqual(target.sent(), [])

    def test_the_refusals_and_a_missing_reply_are_said(self):
        cases = ((("repeat", (200, '{"ok":false,"error":"stale"}\n')), "Repeat 1 one.odrg this turn", "That animation's turn had already ended. (stale)"),
                 (("repeat", (200, '{"ok":false,"error":"no-space"}\n')), "Save the repeat of 1 one.odrg for every turn",
                  "The installation has no room for another saved repeat: it keeps them for at most 32 files of a card or drive and 512 files in all. (no-space)"),
                 (("repeat", (200, '{"ok":false,"error":"in-use"}\n')), "Save the repeat of 1 one.odrg for every turn", "That is a cycle or a folder, which keeps no repeat. (in-use)"),
                 (("repeat", (200, '{"ok":false,"error":"busy"}\n')), "Save the repeat of 1 one.odrg for every turn", "The installation is busy. Try again in a moment. (busy)"),
                 (("repeat", None), "Save the repeat of 1 one.odrg for every turn", "No confirmed reply. The saved repeat is read again before another change."),
                 (("repeat", None), "Repeat 1 one.odrg this turn", "No confirmed reply. The turn's count is read again before another change."))
        for (word, reply), button, said in cases:
            with self.subTest(button=button, said=said):
                target = Target(self, **{word: reply})
                target.status = status_of(1, repeat=8, loop=3, saved=None)
                seen = run(target, [{"untilBar": button}, {"bar": button}, {"until": re.escape(said[:30]), "ms": 12000, "look": "said"}])
                self.assertEqual(seen["said"]["message"], said)

    def test_its_buttons_are_disabled_while_a_line_is_out_and_restore_default_while_nothing_is_saved(self):
        target = Target(self, **{"repeat": lambda line: (support.time.sleep(2), OK)[1]})
        target.status = status_of(1, repeat=8, loop=3, saved=2)
        acts = [{"untilBar": "Restore the default repeat of 1 one.odrg", "look": "saved"}, {"bar": "Restore the default repeat of 1 one.odrg", "wait": 300, "look": "out"},
                {"wait": 3000, "look": "after"}]
        seen = run(target, acts)
        self.assertEqual(seen["saved"]["bar"]["lines"][1:], [["Repeat this", "[8]"], ["Save", "Restore default"]])
        self.assertEqual(seen["out"]["bar"]["lines"][1:], [["Repeat this (disabled)", "[8]"], ["Save (disabled)", "Restore default (disabled)"]])
        self.assertEqual(seen["after"]["bar"]["lines"][1:], [["Repeat this", "[8]"], ["Save", "Restore default"]])
        self.assertEqual(target.sent(), ["repeat 1 default"])

    def test_an_installation_without_the_members_gets_neither_line_and_is_sent_none(self):
        target = Target(self)
        target.status = status_of(1, repeat=8, loop=3)
        seen = run(target, [{"untilBar": "Repeat 1 one.odrg this turn", "look": "repeat"}])
        self.assertEqual(seen["repeat"]["bar"]["lines"], [["Ignore", "Select", "Delete"], ["Repeat this", "[8]"]])
        target.status = status_of(1)
        seen = run(target, [{"untilBar": "Select 1 one.odrg", "look": "none"}])
        self.assertEqual(seen["none"]["bar"]["lines"], INTERNAL)
        self.assertIsNone(seen["none"]["field"])


if __name__ == "__main__":
    unittest.main()

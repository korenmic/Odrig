import json
import unittest

from . import support
from .test_look import SIZES, apart, contrast
from .test_target import entered

OK = (200, '{"ok":true}\n')
# Whole rows of the list: 80 pixels.
ROW = 80
# How far a box may stand off by the rounding of a browser.
SLACK = 0.5
# The chevron of the collapse button: up while the panel is whole, down while it is
# collapsed.
UP = "M6 15l6-6 6 6"
DOWN = "M6 9l6 6 6-6"


def status_of(on):
    return json.dumps({"ok": True, "on": on, "brightness": 128, "playing": "all", "animation": 1, "fps": 50, "error": None}) + "\n"


class Target:
    """A stand-in that lists two animations, plays the first in the playlist, takes `on`
    and `off` without changing its status, and reports the LEDs on or off as the test
    sets."""

    def __init__(self, test, on=True):
        self.on = on
        self.stand_in = entered(test, support.StandIn({"status": lambda line: (200, status_of(self.on)), "list": support.LISTED, "on": OK, "off": OK}))

    def switched(self):
        """The lines of the power the app sent, in order."""
        return [line.decode() for _, line in self.stand_in.lines if line in (b"on", b"off")]


def run(target, acts, size=support.SIZE, steps=()):
    return support.run("paneltop", address=target.stand_in.address, settings={"rows": 2, "acts": acts}, size=size, steps=steps).seen


def room(look):
    """The room left for the list between the panel and the tabs."""
    return look["view"] - look["band"] - look["height"] - look["nav"]


class ThePowerIcon(unittest.TestCase):
    def test_it_sends_off_while_the_status_says_on_and_on_while_it_says_off_and_is_pressed_as_the_status_says(self):
        target = Target(self, on=True)
        acts = [{"pressed": "true", "look": "on"}, {"press": "power-toggle", "wait": 800, "look": "sent"}, {"step": True, "pressed": "false", "look": "off"},
                {"press": "power-toggle", "wait": 800}, {"step": True, "pressed": "true", "look": "again"}]
        steps = [lambda: setattr(target, "on", False), lambda: setattr(target, "on", True)]
        seen = run(target, acts, steps=steps)
        self.assertEqual(target.switched(), ["off", "on"])
        # The icon is pressed as the status says, not as the press would have it: after
        # `off` it stays pressed until a status says the LEDs are off.
        self.assertEqual([seen[name]["power"]["pressed"] for name in ("on", "sent", "off", "again")], ["true", "true", "false", "true"])
        self.assertEqual(seen["on"]["power"]["label"], "LEDs on or off")

    def test_the_line_of_what_plays_and_the_on_and_off_buttons_are_not_shown(self):
        seen = run(Target(self), [{"wait": 1200, "look": "first"}])
        gone = seen["first"]["gone"]
        self.assertFalse(gone["playing"])
        self.assertEqual(gone["words"], "Playlist")
        self.assertEqual(gone["onOff"], [])
        self.assertNotIn("On", gone["buttons"])
        self.assertNotIn("Off", gone["buttons"])


class WhatAnimationsHasNoMore(unittest.TestCase):
    def test_no_select_of_the_list_and_no_add_animation_and_the_bar_keeps_its_select(self):
        seen = run(Target(self), [{"wait": 1200, "look": "first"}])
        first = seen["first"]
        self.assertFalse(first["gone"]["selectMode"])
        self.assertFalse(first["gone"]["addAnimation"])
        self.assertNotIn("Select", first["gone"]["buttons"])
        self.assertNotIn("Add animation", first["gone"]["buttons"])
        self.assertIn("Select", first["bar"])


class TheCollapseButton(unittest.TestCase):
    def test_it_collapses_the_panel_to_its_top_row_and_expands_it_again_and_the_choice_is_kept(self):
        for size in ((320, 568), (412, 915)):
            with self.subTest(size=size):
                acts = [{"wait": 1200, "look": "expanded"}, {"press": "now-collapse", "look": "collapsed"}, {"wait": 1200, "look": "settled"},
                        {"reload": True, "wait": 1200, "look": "reloaded"}, {"press": "now-collapse", "look": "expandedAgain"},
                        {"reload": True, "wait": 1200, "look": "reloadedExpanded"}]
                seen = run(Target(self), acts, size=size)
                expanded, collapsed = seen["expanded"], seen["collapsed"]
                self.assertEqual((expanded["collapsed"], expanded["collapse"]["expanded"], expanded["collapse"]["label"], expanded["mark"], expanded["kept"]),
                                 (False, "true", "Collapse the panel", UP, None))
                self.assertGreater(len(expanded["parts"]), 1)
                for name in ("collapsed", "settled", "reloaded"):
                    look = seen[name]
                    self.assertEqual((look["collapsed"], look["collapse"]["expanded"], look["collapse"]["label"], look["mark"], look["kept"]),
                                     (True, "false", "Expand the panel", DOWN, "collapsed"), name)
                    # Only the top row is left, with the power icon in it.
                    self.assertEqual(look["parts"], ["now-top"], name)
                    self.assertLessEqual(look["height"], look["row"]["bottom"] - look["row"]["top"] + 2 * 6 + 2 + SLACK, name)
                    self.assertIsNotNone(look["power"], name)
                # The list has more room, and its first row stands higher.
                self.assertGreater(room(collapsed), room(expanded))
                self.assertLess(collapsed["firstRow"], expanded["firstRow"])
                for name in ("expandedAgain", "reloadedExpanded"):
                    look = seen[name]
                    self.assertEqual((look["collapsed"], look["collapse"]["expanded"], look["collapse"]["label"], look["mark"], look["kept"]),
                                     (False, "true", "Collapse the panel", UP, "expanded"), name)
                    self.assertEqual(look["parts"], expanded["parts"], name)
                    self.assertAlmostEqual(look["height"], expanded["height"], delta=SLACK, msg=name)
                # The top stays frozen whenever a whole row fits under it, measured again at
                # once when the panel collapses or expands.
                for name, look in seen.items():
                    self.assertEqual(look["frozen"], room(look) >= ROW, name)
                    if look["frozen"]:
                        self.assertAlmostEqual(float(look["padding"][:-2]), look["band"] + look["height"], delta=SLACK, msg=name)
                    else:
                        self.assertEqual(look["padding"], "", name)
                if size == (320, 568):
                    self.assertFalse(expanded["frozen"])
                    self.assertTrue(collapsed["frozen"])
                    self.assertFalse(seen["expandedAgain"]["frozen"])


class TheLook(unittest.TestCase):
    def test_both_buttons_are_48_pixels_round_at_the_ends_of_the_top_row_and_keep_the_look_rules(self):
        for size in SIZES:
            with self.subTest(size=size):
                target = Target(self, on=True)
                acts = [{"pressed": "true", "wait": 1200, "look": "on"}, {"step": True, "pressed": "false", "look": "off"},
                        {"press": "now-collapse", "wait": 300, "look": "collapsed"}, {"press": "now-collapse", "wait": 300}]
                seen = run(target, acts, size=size, steps=[lambda: setattr(target, "on", False)])
                for name, look in seen.items():
                    where = f"{size[0]} wide, {name}"
                    power, collapse = look["power"], look["collapse"]
                    for what, button in (("power-toggle", power), ("now-collapse", collapse)):
                        self.assertAlmostEqual(button["right"] - button["left"], 48, delta=0.01, msg=f"{where}: {what}")
                        self.assertAlmostEqual(button["bottom"] - button["top"], 48, delta=0.01, msg=f"{where}: {what}")
                        self.assertGreaterEqual(button["radius"], 24, f"{where}: {what}")
                        self.assertGreaterEqual(contrast(button["icon"], button["behind"]), 7, f"{where}: the icon of {what} is {button['icon']} on {button['behind']}")
                        self.assertGreaterEqual(button["left"], 0, f"{where}: {what}")
                        self.assertLessEqual(button["right"], size[0] + 0.01, f"{where}: {what}")
                        for other in look["others"]:
                            self.assertGreaterEqual(apart(button, other), 8 - 0.01, f"{where}: {what} and {other['what']}")
                    # The power icon at the left of the panel's top row, the collapse button at
                    # its right, on one line.
                    self.assertAlmostEqual(power["left"], look["inner"]["left"], delta=SLACK, msg=where)
                    self.assertAlmostEqual(collapse["right"], look["inner"]["right"], delta=SLACK, msg=where)
                    self.assertAlmostEqual(power["top"] + power["bottom"], collapse["top"] + collapse["bottom"], delta=2 * SLACK, msg=where)
                    self.assertGreaterEqual(apart(power, collapse), 8 - 0.01, where)
                self.assertEqual((seen["on"]["power"]["pressed"], seen["off"]["power"]["pressed"]), ("true", "false"))


if __name__ == "__main__":
    unittest.main()

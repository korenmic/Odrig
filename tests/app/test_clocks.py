import json
import unittest

from tests.emulator import support as emulator_support

from . import support
from .test_look import SIZES, apart, contrast
from .test_target import entered

OK = (200, '{"ok":true}\n')
LABELS = ["Clocks", "The message after each clock"]
SMALLS = ["Between animations inserts a clock after every 5 animations or 5 minutes. Clocks only restricts playback to the external clocks folder.",
          "One complete animation from clocks/message plays after each clock in either enabled mode."]
SAVED = {"clocks on": "Saved: a clock plays between the animations.", "clocks off": "Saved: clocks are off.",
         "clocks message on": "Saved: a complete message plays after each clock.", "clocks message off": "Saved: no message after the clocks."}
REFUSED = {"busy": "The target is busy checking or uploading files. Try again after it finishes.",
           "show-invalid": "The target has an invalid show. Fix its show before changing the clocks.",
           "storage-error": "The target could not save the setting. The setting in force is shown."}


class Target:
    """A stand-in whose `status` reports the two settings it keeps, which `clocks` changes, or
    refuses with the code the test sets; `answering` false makes every reply a failure."""

    def __init__(self, test, clocks=False, message=False, members=True):
        self.clocks = clocks
        self.message = message
        self.members = members
        self.refusal = None
        self.answering = True
        self.stand_in = entered(test, support.StandIn(self.reply))

    def reply(self, line):
        if not self.answering:
            return (500, "")
        word = line.split(b" ")[0]
        if word == b"status":
            return self.status()
        if word == b"list":
            return support.LISTED
        if word == b"clocks":
            return self.change(line)
        return (200, '{"ok":false,"error":"unknown-command"}\n')

    def status(self):
        members = {"clocks": self.clocks, "clock_message": self.message} if self.members else {}
        return (200, json.dumps({"ok": True, "on": True, "brightness": 128, "playing": "all", "animation": 1, "fps": 50, "error": None, **members, "left": 0}) + "\n")

    def change(self, line):
        if self.refusal is not None:
            return (200, json.dumps({"ok": False, "error": self.refusal}) + "\n")
        words = line.decode().split()
        if words[1] == "message":
            self.message = words[2] == "on"
        else:
            self.clocks = words[1] == "on"
        return OK

    def sent(self):
        return [line.decode() for _, line in self.stand_in.lines if line.startswith(b"clocks")]


def run(target, acts, steps=(), size=support.SIZE):
    return support.run("clocks", address=target.stand_in.address, settings={"rows": 2, "acts": acts}, steps=steps, size=size).seen


class AgainstTheEmulator(unittest.TestCase):
    def test_each_box_saves_its_setting_in_the_player_and_follows_its_status(self):
        folder = entered(self, emulator_support.demo_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        acts = [{"tap": "clocks", "look": "out1", "answered": "saved1"}, {"tap": "clock-message", "look": "out2", "answered": "saved2"},
                {"step": True, "until": {"checked": [False, True]}, "look": "followed"}]
        seen = support.run("clocks", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "acts": acts},
                           steps=[lambda: emulator.command("clocks off")]).seen
        self.assertFalse(seen["first"]["hidden"])
        self.assertEqual(seen["first"]["checked"], [False, False])
        self.assertEqual((seen["saved1"]["said"], seen["saved1"]["checked"]), (SAVED["clocks on"], [True, False]))
        self.assertEqual((seen["saved2"]["said"], seen["saved2"]["checked"]), (SAVED["clocks message on"], [True, True]))
        self.assertEqual(seen["followed"]["checked"], [False, True])
        status = json.loads(emulator.command("status"))
        self.assertEqual((status["clocks"], status["clock_message"]), (False, True))
        self.assertEqual((folder / "clocks.txt").read_bytes(), b"odrig-clocks 2\nmode off\nmessage on\n")


class ThePanel(unittest.TestCase):
    def test_it_follows_the_first_panel_of_settings_with_its_two_boxes_and_the_settings_in_force(self):
        seen = run(Target(self, clocks=True, message=False), [])
        first = seen["first"]
        self.assertFalse(first["hidden"])
        self.assertEqual((first["title"], first["after"]), ("Clocks", "show-tests"))
        self.assertEqual(first["labels"], LABELS)
        self.assertEqual(first["smalls"], SMALLS)
        self.assertEqual(first["checked"], [True, False])
        self.assertEqual(first["disabled"], [False, False])
        self.assertIsNone(first["said"])
        self.assertEqual(first["role"], "status")

    def test_it_is_hidden_for_a_player_without_the_members(self):
        seen = run(Target(self, members=False), [])
        self.assertTrue(seen["first"]["hidden"])

    def test_each_box_sends_its_line_at_once_says_what_was_saved_and_follows_status(self):
        target = Target(self)
        acts = [{"tap": "clocks", "look": "out1", "answered": "saved1"}, {"wait": 1500, "look": "later1"},
                {"tap": "clock-message", "look": "out2", "answered": "saved2"},
                {"tap": "clocks", "look": "out3", "answered": "saved3"},
                {"tap": "clock-message", "look": "out4", "answered": "saved4"}, {"wait": 1500, "look": "later4"}]
        seen = run(target, acts)
        self.assertEqual(target.sent(), ["clocks on", "clocks message on", "clocks off", "clocks message off"])
        for number, (line, checked) in enumerate((("clocks on", [True, False]), ("clocks message on", [True, True]), ("clocks off", [False, True]),
                                                  ("clocks message off", [False, False])), start=1):
            # Both boxes are disabled while the line is out, the tapped one showing the tap.
            self.assertEqual(seen[f"out{number}"]["disabled"], [True, True], line)
            self.assertEqual(seen[f"out{number}"]["checked"], checked, line)
            self.assertIsNone(seen[f"out{number}"]["said"], line)
            self.assertEqual(seen[f"saved{number}"]["said"], SAVED[line], line)
            self.assertEqual(seen[f"saved{number}"]["checked"], checked, line)
        self.assertEqual(seen["later1"]["checked"], [True, False])
        self.assertEqual(seen["later4"]["checked"], [False, False])
        self.assertEqual((target.clocks, target.message), (False, False))

    def test_the_boxes_follow_a_change_another_controller_made(self):
        target = Target(self)

        def elsewhere():
            target.clocks, target.message = True, True
        seen = run(target, [{"step": True, "until": {"checked": [True, True]}, "look": "followed"}], steps=[elsewhere])
        self.assertEqual(seen["followed"]["checked"], [True, True])
        self.assertEqual(target.sent(), [])

    def test_a_refusal_is_said_and_the_box_shows_the_setting_in_force_again(self):
        target = Target(self, clocks=True)
        steps = [lambda code=code: setattr(target, "refusal", code) for code in REFUSED]
        acts = [act for number in range(len(REFUSED)) for act in ({"step": True}, {"tap": "clocks" if number % 2 == 0 else "clock-message", "look": f"out{number}", "answered": f"said{number}"})]
        seen = run(target, acts, steps=steps)
        self.assertEqual(target.sent(), ["clocks off", "clocks message on", "clocks off"])
        for number, code in enumerate(REFUSED):
            self.assertEqual(seen[f"said{number}"]["said"], REFUSED[code], code)
            self.assertEqual(seen[f"said{number}"]["checked"], [True, False], code)
        self.assertEqual((target.clocks, target.message), (True, False))

    def test_the_boxes_are_disabled_while_the_installation_does_not_answer(self):
        target = Target(self, message=True)
        steps = [lambda: setattr(target, "answering", False), lambda: setattr(target, "answering", True)]
        acts = [{"step": True, "until": {"checked": [False, True], "disabled": [True, True]}, "look": "silent"},
                {"step": True, "until": {"checked": [False, True], "disabled": [False, False]}, "look": "again"}]
        seen = run(target, acts, steps=steps)
        self.assertFalse(seen["silent"]["hidden"])
        self.assertEqual(seen["silent"]["disabled"], [True, True])
        self.assertEqual(seen["again"]["disabled"], [False, False])


class Look(unittest.TestCase):
    def test_the_panel_keeps_the_rules_of_the_look_upright_narrow_and_sideways(self):
        target = Target(self)
        for size in SIZES:
            where = f"{size[0]} wide"
            screen = run(target, [{"tap": "clocks", "look": "out", "answered": "said"}, {"measure": "settings"}], size=size)["settings"]
            controls = [control for control in screen["controls"] if control["group"] == "screen"]
            boxes = [control for control in controls if control["what"] in ("clocks", "clock-message")]
            self.assertEqual(len(boxes), 2, where)
            self.assertLessEqual(screen["scrollWidth"], screen["width"], where)
            for control in boxes:
                self.assertGreaterEqual(control["bottom"] - control["top"], 48 - 0.01, f"{where}: {control['what']}")
                self.assertGreaterEqual(control["left"], 0, f"{where}: {control['what']}")
                self.assertLessEqual(control["right"], size[0] + 0.01, f"{where}: {control['what']}")
                for other in controls:
                    if other is not control:
                        self.assertGreaterEqual(apart(control, other), 8 - 0.01, f"{where}: {control['what']} and {other['what']}")
            texts = [text for text in screen["texts"] if text["what"] in ("clocks-said", "title", "small") or text["what"] == "Clocks"]
            self.assertGreaterEqual(len(texts), 5, where)
            for text in texts:
                self.assertGreaterEqual(contrast(text["colour"], text["behind"]), 7, f"{where}: {text['what']}")
                self.assertGreaterEqual(text["size"], 14, f"{where}: {text['what']}")


if __name__ == "__main__":
    unittest.main()

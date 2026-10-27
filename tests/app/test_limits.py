"""Settings' panel of the current limits, in Chrome against the emulator and against
stand-in targets: the rows, the reads every two seconds, the saves, the range, the
refusals, the warnings and the marks, a field with the focus or text not saved, and an
installation whose software has no limits."""

import json
import pathlib
import tempfile
import threading
import time
import unittest

from tests.emulator import support as emulator_support
from tests.mapping.test_core import PINS, files

from . import support
from .test_target import entered

OK = (200, '{"ok":true}\n')
SNAKES = [str(snake) for snake in range(1, 21)]
LABELS = [f"Snake {snake} \u00b7 columns {snake * 3 - 2}\u2013{snake * 3}" for snake in range(1, 21)]
LOWEST = "At this budget every LED is held at its lowest level."
NONE = "This installation's software has no current limits."
DEFAULTS = "No budgets are saved: the wall's budget is the installation's default."


class Budgets:
    """A target with current limits. `mapping get` reports the installation's twenty
    snakes, or with `editable` false a mapping of two legs; `limits` gives `part` legs a
    reply, each of 180 LEDs with an estimate of 300 mA and its number, those in `limited`
    and the wall when it is in `limited` dimmed, each part after `read_slow` seconds; a save
    is answered after `slow` seconds, refused with the next of `refusals` while there are
    any, and otherwise saved. `log` holds each line of `limits` with the time it came, and
    `answered` each save with the time it was answered."""

    def __init__(self, saved=False, wall=730, legs=None, editable=True, part=10, limited=(), refusals=(), slow=0.0, read_slow=0.0):
        self.saved = saved
        self.wall = wall
        self.legs = {leg: 0 for leg in range(1, 21 if editable else 3)}
        self.legs.update(legs or {})
        self.editable = editable
        self.part = part
        self.limited = set(limited)
        self.refusals = list(refusals)
        self.slow = slow
        self.read_slow = read_slow
        self.log = []
        self.answered = []
        self.lock = threading.Lock()

    def mapping(self, line):
        if self.editable:
            return (200, json.dumps({"ok": True, "editable": True, "pins": PINS, "revision": 123, "cross": False, "test": False, "snake": None}) + "\n")
        return (200, json.dumps({"ok": True, "editable": False, "pins": [], "revision": 0, "cross": False, "test": False, "snake": None}) + "\n")

    def limits(self, line):
        words = line.decode("ascii").split(" ")
        with self.lock:
            self.log.append((time.monotonic(), line.decode("ascii")))
        if len(words) == 1 or (len(words) == 2 and words[1].isdigit()):
            time.sleep(self.read_slow)
            with self.lock:
                start = int(words[1]) if len(words) == 2 else 0
                legs = sorted(self.legs)
                entries = [[leg, 180, self.legs[leg], 300 + leg, int(leg in self.limited)] for leg in legs[start:start + self.part]]
                wall = [180 * len(legs), self.wall, sum(300 + leg for leg in legs), int("wall" in self.limited)]
                following = start + self.part if start + self.part < len(legs) else None
                return (200, json.dumps({"ok": True, "saved": self.saved, "wall": wall, "legs": entries, "next": following}) + "\n")
        time.sleep(self.slow)
        with self.lock:
            self.answered.append((time.monotonic(), line.decode("ascii")))
            if self.refusals:
                return (200, json.dumps({"ok": False, "error": self.refusals.pop(0)}) + "\n")
            if words[1] == "wall":
                self.wall = int(words[2])
            else:
                self.legs[int(words[2])] = int(words[3])
            self.saved = True
            return OK

    def replies(self):
        return {**support.SOUND, "mapping": self.mapping, "limits": self.limits}

    def saves(self):
        return [line for _, line in self.log if len(line.split(" ")) > 2]

    def reads(self):
        """The times of the reads of the limits, each its first part."""
        return [moment for moment, line in self.log if line == "limits"]


class AgainstTheEmulator(unittest.TestCase):
    def test_the_panel_reads_saves_warns_and_marks_and_keeps_a_field_being_typed_in(self):
        work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        folder = emulator_support.installed(work / "show", files())
        with emulator_support.Emulator(folder) as target:
            found = support.run("limits", address=f"127.0.0.1:{target.port}",
                                steps=[lambda: (target.command("limits snake 3 77"), target.command("limits snake 4 150"))]).seen
            reply = json.loads(target.command("limits"))
        first = found["first"]
        self.assertEqual(first["heading"], "Current limits")
        for words in ("a ceiling, in mA, on WLED's estimate", "not a measurement", "A low wall budget also dims the diagonal that the mapping from a photo reads"):
            self.assertIn(words, first["explanation"])
        self.assertEqual(first["keys"], ["wall", *SNAKES])
        self.assertEqual(first["labels"], ["The wall's budget, mA", *LABELS])
        # The emulator has no default: no limit, shown as an empty field.
        self.assertEqual(set(first["values"].values()), {""})
        self.assertEqual(first["placeholders"], ["No limit"])
        self.assertEqual(len(first["estimates"]), 21)
        for estimate in first["estimates"]:
            self.assertRegex(estimate, r"\AEstimate [0-9]{1,3}(,[0-9]{3})* mA\Z")
        self.assertEqual((first["dimmed"], first["warnings"]), ([], []))
        self.assertEqual(first["defaults"], DEFAULTS)
        self.assertIsNone(first["summary"])
        # The wall's budget, saved by leaving the field: the budgets are saved now, and 2,000
        # mA is at most the wall's 3,600 LEDs.
        self.assertEqual(found["wallSaid"], "Saved: the wall's budget is 2,000 mA.")
        self.assertIsNone(found["afterWall"]["defaults"])
        self.assertEqual(found["afterWall"]["warnings"], ["wall"])
        self.assertEqual(found["afterWall"]["warning"], [LOWEST])
        # Snake 1's, saved by Enter, is marked dimmed once it holds the snake.
        self.assertEqual(found["oneSaid"], "Saved: snake 1's budget is 100 mA.")
        self.assertIn("1", found["afterOne"]["warnings"])
        self.assertIn("1", found["afterOne"]["dimmed"])
        self.assertEqual(found["afterOne"]["marks"], ["Dimmed"])
        # Emptied, it saves no limit, and the warning goes.
        self.assertEqual(found["emptied"], "Saved: snake 1 has no limit.")
        self.assertEqual(found["afterEmptied"]["values"]["1"], "")
        self.assertNotIn("1", found["afterEmptied"]["warnings"])
        # Out of range: nothing sent, the range said, the saved value shown.
        self.assertEqual(found["range"], "A snake's budget is 0 to 65,535 mA, 0 for no limit. Its saved budget is shown.")
        self.assertEqual(found["rangeValue"], "")
        # Snake 3's field kept its focus and its text through the reads, which showed snake
        # 4's budget set elsewhere; left, it was saved.
        self.assertTrue(found["focusKept"])
        self.assertEqual(found["textKept"], "123")
        self.assertEqual(found["whileTyping"]["values"]["3"], "123")
        self.assertEqual(found["whileTyping"]["values"]["4"], "150")
        self.assertIn("4", found["whileTyping"]["warnings"])
        self.assertEqual(found["threeSaid"], "Saved: snake 3's budget is 123 mA.")
        self.assertEqual(found["wallAgain"], "Saved: the wall's budget is 5,000 mA.")
        self.assertNotIn("wall", found["last"]["warnings"])
        self.assertEqual(sorted(found["last"]["warnings"]), ["3", "4"])
        self.assertEqual(reply["saved"], True)
        self.assertEqual(reply["wall"][:2], [3600, 5000])
        self.assertEqual({leg: budget for leg, _, budget, _, _ in reply["legs"] if budget}, {3: 123, 4: 150})


class AgainstStandIns(unittest.TestCase):
    def test_the_limits_are_read_in_parts_every_two_seconds_and_only_changed_text_in_range_is_sent(self):
        budgets = Budgets(legs={3: 90}, limited=("wall", 7))
        with support.StandIn(budgets.replies()) as target:
            found = support.run("limits", address=target.address, settings={"mode": "lines"}).seen
        first = found["first"]
        self.assertEqual(first["keys"], ["wall", *SNAKES])
        self.assertEqual((first["values"]["wall"], first["values"]["3"], first["values"]["1"]), ("730", "90", ""))
        self.assertEqual(first["estimates"][:2], ["Estimate 6,210 mA", "Estimate 301 mA"])
        self.assertEqual(first["defaults"], DEFAULTS)
        # 730 mA and 90 mA are at most the LEDs of the wall and of a snake.
        self.assertEqual(first["warnings"], ["wall", "3"])
        self.assertEqual(sorted(first["dimmed"]), ["7", "wall"])
        # Each read asks for the second part at once, and the reads come every two seconds.
        lines = [line for _, line in budgets.log]
        saved_at = next(moment for moment, line in budgets.log if line == budgets.saves()[0])
        before = [moment for moment in budgets.reads() if moment < saved_at]
        self.assertGreaterEqual(len(before), 3, lines)
        for at, line in enumerate(lines[:-1]):
            if line == "limits":
                self.assertEqual(lines[at + 1], "limits 10", lines)
        for earlier, later in zip(before, before[1:]):
            self.assertGreaterEqual(later - earlier, 1.3, before)
            self.assertLessEqual(later - earlier, 4.5, before)
        # The value read, written otherwise, is not sent, nor is a value out of range.
        self.assertEqual(found["equal"], {"value": "730", "said": None})
        self.assertEqual(found["wallRange"], {"value": "730", "said": "The wall's budget is 0 to 250,000 mA, 0 for no limit. Its saved budget is shown."})
        self.assertEqual(found["snakeRange"], {"value": "", "said": "A snake's budget is 0 to 65,535 mA, 0 for no limit. Its saved budget is shown."})
        self.assertIsNone(found["emptyAtZero"])
        self.assertEqual(found["emptied"], "Saved: snake 3 has no limit.")
        self.assertEqual(found["afterEmptied"]["warnings"], ["wall"])
        self.assertEqual(found["wall"], "Saved: the wall's budget is 2,000 mA.")
        self.assertIsNone(found["afterWall"]["defaults"])
        # The warning stands beside a budget from 1 to the LEDs' count, 180 for a snake.
        self.assertEqual(found["atCount"], "Saved: snake 4's budget is 180 mA.")
        self.assertIn("4", found["afterAtCount"]["warnings"])
        self.assertEqual(found["aboveCount"], "Saved: snake 4's budget is 181 mA.")
        self.assertNotIn("4", found["afterAboveCount"]["warnings"])
        self.assertEqual(budgets.saves(), ["limits snake 3 0", "limits wall 2000", "limits snake 4 180", "limits snake 4 181"])

    def test_nothing_is_read_while_a_save_is_out(self):
        budgets = Budgets(slow=3.0)
        with support.StandIn(budgets.replies()) as target:
            found = support.run("limits", address=target.address, settings={"mode": "slow"}).seen
            together = target.together
        self.assertEqual(found["during"], {"said": "Saving\u2026", "value": "500"})
        self.assertEqual(found["said"], "Saved: snake 1's budget is 500 mA.")
        self.assertEqual(found["value"], "500")
        self.assertEqual(together, 1)
        [(asked_at, _)] = [(moment, line) for moment, line in budgets.log if line == "limits snake 1 500"]
        [(answered_at, _)] = budgets.answered
        # While it was out nothing was read; once it was answered the limits were read once.
        self.assertEqual([moment for moment in budgets.reads() if asked_at < moment < answered_at], [])
        self.assertEqual(len([moment for moment in budgets.reads() if answered_at <= moment <= answered_at + 1.2]), 1, budgets.log)

    def test_slow_reads_still_come_every_two_seconds_and_enter_sends_only_changed_text(self):
        budgets = Budgets(legs={3: 90}, read_slow=0.4)

        def elsewhere():
            with budgets.lock:
                budgets.legs[3] = 200

        with support.StandIn(budgets.replies()) as target:
            found = support.run("limits", address=target.address, settings={"mode": "stale"}, steps=[elsewhere]).seen
        # Each read takes two parts of 0.4 seconds; after the first, the reads come every two
        # seconds all the same.
        reads = budgets.reads()
        self.assertGreaterEqual(len(reads), 5, budgets.log)
        for earlier, later in zip(reads[1:], reads[2:]):
            self.assertLessEqual(later - earlier, 2.6, reads)
        # Snake 3's budget, changed elsewhere while its field had the focus, was read and its
        # field kept its text; Enter with that text unchanged sent nothing, and once the field
        # was left it showed the budget read.
        self.assertEqual(found["focused"], {"value": "90", "focus": True})
        self.assertEqual(found["afterEnter"], {"value": "90", "said": None})
        self.assertEqual(found["left"], "200")
        self.assertEqual(budgets.saves(), [])

    def test_each_refusal_is_said_in_its_own_words_and_the_saved_value_shown_again(self):
        codes = ["storage-error", "busy", "show-invalid", "bad-argument", "weird"]
        keys = ["1", "2", "3", "4", "wall"]
        budgets = Budgets(refusals=codes)
        with support.StandIn(budgets.replies()) as target:
            found = support.run("limits", address=target.address, settings={"mode": "refused", "keys": keys}).seen
        said = {key: found[key]["said"] for key in keys}
        self.assertEqual(said, {
            "1": "The installation could not save its budgets. Its saved budget is shown.",
            "2": "The installation is busy reading its animations, uploading or rebuilding a catalog. Try again after it finishes.",
            "3": "The installation has an invalid show. Fix its show before setting a budget.",
            "4": "The installation cannot take this budget: the value is out of its range, or its mapping has no such snake.",
            "wall": "The installation refused the budget: weird.",
        })
        self.assertEqual([found[key]["value"] for key in keys], ["", "", "", "", "730"])
        self.assertTrue(all(found[key]["problem"] for key in keys))
        self.assertEqual((found["later"]["1"], found["later"]["wall"]), ("", "730"))
        self.assertEqual(budgets.saves(), ["limits snake 1 50", "limits snake 2 50", "limits snake 3 50", "limits snake 4 50", "limits wall 50"])

    def test_an_installation_without_limits_is_asked_once_and_another_shows_the_wall_alone(self):
        other = Budgets(editable=False, wall=0)
        with support.StandIn(support.SOUND) as older, support.StandIn(other.replies()) as target:
            found = support.run("limits", address=older.address, settings={"mode": "none", "other": target.address}).seen
            asked = [line for _, line in older.lines if line.startswith(b"limits")]
        without = found["without"]
        self.assertEqual(without["summary"], NONE)
        self.assertIn("not a measurement", without["explanation"])
        self.assertEqual((without["inputs"], without["keys"], without["defaults"]), (0, [], None))
        self.assertEqual(asked, [b"limits"])
        # A mapping that is not the twenty snakes has the wall's field alone.
        self.assertEqual(found["other"]["keys"], ["wall"])
        self.assertEqual(found["other"]["inputs"], 1)
        self.assertEqual(found["other"]["values"], {"wall": ""})
        self.assertEqual(found["other"]["estimates"], ["Estimate 603 mA"])
        self.assertIsNone(found["other"]["summary"])
        self.assertTrue(other.reads())


class TheProtocol(unittest.TestCase):
    def test_the_replies_to_limits_are_checked_and_the_lines_are_those_of_the_commands(self):
        good = {"ok": True, "saved": False, "wall": [3600, 730, 3780, 1], "legs": [[1, 180, 0, 189, 0], [2, 180, 500, 451, 1]], "next": 2}
        replies = [
            [0, good], [0, {**good, "next": None}], [2, good], [2, {**good, "next": 3}],
            [0, {**good, "saved": "no"}], [0, {**good, "wall": [3600, 730, 3780]}], [0, {**good, "wall": [3600, 730, 3780, 2]}],
            [0, {**good, "wall": [3600, 250001, 3780, 0]}], [0, {**good, "legs": [[0, 180, 0, 189, 0]]}], [0, {**good, "legs": [[256, 180, 0, 189, 0]]}],
            [0, {**good, "legs": [[1, 180, 65536, 189, 0]]}], [0, {**good, "legs": [[1, 180, 0, 189]]}], [0, {**good, "legs": [[1, 180, 0, -1, 0]]}],
            [0, {**good, "legs": None}], [0, {**good, "next": 65536}], [0, {"ok": False, "error": "unknown-command"}],
        ]
        found = support.run("limits-protocol", settings={"replies": replies}).seen
        self.assertEqual(found["found"][0], {"saved": False, "wall": {"leds": 3600, "budget": 730, "estimate": 3780, "limited": True},
                                             "legs": [{"leg": 1, "leds": 180, "budget": 0, "estimate": 189, "limited": False},
                                                      {"leg": 2, "leds": 180, "budget": 500, "estimate": 451, "limited": True}], "next": 2})
        self.assertIsNone(found["found"][1]["next"])
        # `next` lies after the part asked for.
        self.assertEqual(found["found"][2], {"error": "bad-reply"})
        self.assertEqual(found["found"][3]["next"], 3)
        self.assertEqual(found["found"][4:7], [{"error": "bad-reply"}] * 3)
        # A host's default may be larger than a budget that can be set.
        self.assertEqual(found["found"][7]["wall"]["budget"], 250001)
        self.assertEqual(found["found"][8:15], [{"error": "bad-reply"}] * 7)
        self.assertEqual(found["found"][15], {"error": "unknown-command"})
        self.assertEqual(found["sent"][:4], ["limits", "limits", "limits 2", "limits 2"])
        self.assertEqual(found["sent"][-2:], ["limits wall 2000", "limits snake 3 0"])


if __name__ == "__main__":
    unittest.main()

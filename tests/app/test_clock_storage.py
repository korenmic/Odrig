"""The preferred storage of the clocks in the shared app: `clock_storage` taken from `status`,
the line `clocks storage sd|internal`, the dropdown under the clock mode's in Settings with
its states, and its words on a target that does not report it."""

import json
import threading
import unittest

from tests.emulator import support as emulator_support
from . import support
from .test_clock_modes import STATUS, ModeTarget
from .test_target import entered

SAVED = {"sd": "Saved: matching files play from the SD card.", "internal": "Saved: matching files play from internal storage."}
OLDER = "This target plays the card's clocks and messages only. Update its firmware to use those of the board's own storage."


class StorageTarget(ModeTarget):
    """The stand-in of the clock modes that reports `clock_storage` and takes `clocks storage`,
    or, with `storage` None, one that does neither."""

    def __init__(self, test, storage="sd", mode="between"):
        self.storage = storage
        self.apply_storage = True
        self.lose_storage_reply = False
        self.storage_gate = None
        super().__init__(test, mode)

    def reply(self, line):
        words = line.decode().split()
        if words[:2] == ["clocks", "storage"]:
            self.change_seen.set()
            if self.storage_gate is not None:
                self.storage_gate.wait(5)
            if self.refusal:
                return self.answer(dict(ok=False, error=self.refusal))
            if self.apply_storage:
                self.storage = words[2]
            if self.lose_storage_reply:
                self.lose_storage_reply = False
                return 500, ""
            return self.answer(dict(ok=True))
        status, body = super().reply(line)
        if words[0] == "status" and self.storage is not None:
            return self.answer({**json.loads(body), "clock_storage": self.storage})
        return status, body


def ui(target, acts, **kwargs):
    return support.run("clock-storage-ui", address=target.stand_in.address, settings=dict(rows=2, acts=acts), **kwargs).seen


class TheProtocol(unittest.TestCase):
    def protocol(self, replies):
        return support.run("clock-mode-protocol", settings={"replies": replies}).seen

    def test_status_gives_the_preferred_storage_and_whether_the_target_reports_it(self):
        replies = [dict(command="status", reply={**STATUS, "clock_mode": "between", "clock_only": None, "clock_storage": storage})
                   for storage in ("sd", "internal")] + [dict(command="status", reply={**STATUS, "clock_mode": "between", "clock_only": None})]
        seen = self.protocol(replies)["results"]
        self.assertEqual([(found["hasClockStorage"], found["clockStorage"]) for found in seen], [(True, "sd"), (True, "internal"), (False, None)])

    def test_another_value_of_the_storage_is_a_bad_reply(self):
        bad = ["SD", "card", None, 1, True, ""]
        seen = self.protocol([dict(command="status", reply={**STATUS, "clock_storage": value}) for value in bad])
        self.assertEqual(seen["results"], [dict(error="bad-reply")] * len(bad))

    def test_each_choice_sends_its_line_and_another_is_refused_before_it_is_sent(self):
        seen = self.protocol([dict(command="clockStorage", args=[storage], reply=dict(ok=True)) for storage in ("sd", "internal", "card")])
        self.assertEqual(seen["sent"], ["clocks storage sd", "clocks storage internal"])
        self.assertEqual(seen["results"][2], dict(error="RangeError"))


class TheDropdown(unittest.TestCase):
    def test_it_stands_under_the_modes_with_its_words_and_two_options(self):
        seen = ui(StorageTarget(self, "internal"), [])["first"]
        self.assertEqual(seen["order"], ["clocks", "clock-storage", "clock-message"])
        self.assertEqual(seen["label"], "Preferred storage for matching clock/message files")
        self.assertEqual(seen["explanation"], "Applies when the same relative path and file type exist in both storages.")
        self.assertEqual(seen["options"], [dict(value="sd", text="SD card"), dict(value="internal", text="Internal storage")])
        self.assertEqual((seen["value"], seen["disabled"], seen["support"]), ("internal", False, None))
        self.assertEqual(seen["description"], "Between animations inserts a clock after every 5 animations or 5 minutes. Clocks only restricts playback to the clocks folders.")

    def test_a_choice_is_sent_and_saved_only_after_a_status_confirms_it(self):
        target = StorageTarget(self)
        target.storage_gate = threading.Event()
        self.addCleanup(target.storage_gate.set)
        acts = [{"storage": "internal"}, {"step": True},
                {"until": {"value": "internal", "disabled": False, "said": "Saved:"}, "look": "saved"},
                {"storage": "sd"}, {"until": {"value": "sd", "disabled": False, "said": SAVED["sd"]}, "look": "back"}]
        seen = ui(target, acts, steps=[target.storage_gate.set])
        self.assertEqual(seen["pending"]["value"], "sd")
        self.assertEqual(seen["saved"]["said"], SAVED["internal"])
        self.assertEqual(target.lines("clocks"), ["clocks storage internal", "clocks storage sd"])
        self.assertEqual(target.storage, "sd")

    def test_it_is_disabled_while_its_line_is_out(self):
        target = StorageTarget(self)
        target.storage_gate = threading.Event()
        self.addCleanup(target.storage_gate.set)
        seen = ui(target, [{"storage": "internal"}, {"look": "out"}, {"step": True}, {"until": {"said": SAVED["internal"]}}],
                  steps=[target.storage_gate.set])
        self.assertTrue(seen["out"]["disabled"])
        self.assertTrue(seen["out"]["modeDisabled"])
        self.assertEqual(seen["out"]["value"], "internal")

    def test_a_refusal_is_explained_with_the_value_in_force(self):
        target = StorageTarget(self)
        target.refusal = "storage-error"
        seen = ui(target, [{"storage": "internal", "until": {"disabled": False, "said": "could not save"}, "look": "refused"}])
        self.assertEqual(seen["refused"]["value"], "sd")
        self.assertEqual(seen["refused"]["said"], "The target could not save the setting. The setting in force is shown.")
        self.assertEqual(target.storage, "sd")

    def test_a_lost_reply_is_said_unconfirmed_until_a_status_shows_the_value(self):
        target = StorageTarget(self)
        target.lose_storage_reply = True
        seen = ui(target, [{"storage": "internal", "until": {"value": "internal", "disabled": False, "said": "not confirmed"}, "look": "after"}])
        self.assertNotIn("Saved:", seen["after"]["said"])
        self.assertEqual(target.storage, "internal")

    def test_another_reported_value_is_shown_as_such(self):
        target = StorageTarget(self)
        target.apply_storage = False
        seen = ui(target, [{"storage": "internal", "until": {"value": "sd", "disabled": False, "said": "different setting"}, "look": "after"}])
        self.assertEqual(seen["after"]["said"], "The target reports a different setting. The setting in force is shown.")

    def test_a_change_of_target_clears_a_pending_choice(self):
        first, second = StorageTarget(self), StorageTarget(self, "internal")
        first.storage_gate = threading.Event()
        self.addCleanup(first.storage_gate.set)

        def arrived():
            self.assertTrue(first.change_seen.wait(3))
        acts = [{"storage": "internal"}, {"step": True}, {"target": second.stand_in.address}, {"step": True},
                {"until": {"value": "internal", "disabled": False}, "wait": 800, "look": "second"}]
        seen = ui(first, acts, steps=[arrived, first.storage_gate.set])
        self.assertEqual(seen["second"]["said"], "")
        self.assertEqual(second.lines("clocks"), [])

    def test_it_is_disabled_while_the_saved_settings_are_unreadable(self):
        target = StorageTarget(self, mode="only")
        target.clock_error = "unreadable"
        target.only_state = "no-clocks"
        seen = support.run("clock-storage-ui", address=target.stand_in.address, settings=dict(rows=1, acts=[{"wait": 1200, "look": "later"}])).seen
        self.assertTrue(seen["later"]["disabled"])
        self.assertFalse(seen["later"]["modeDisabled"])

    def test_an_older_target_shows_it_disabled_at_the_sd_card_with_why(self):
        seen = ui(StorageTarget(self, None), [{"wait": 1200, "look": "later"}])["later"]
        self.assertEqual((seen["value"], seen["disabled"]), ("sd", True))
        self.assertEqual(seen["support"], OLDER)
        self.assertEqual(seen["description"], "Between animations inserts a clock after every 5 animations or 5 minutes. Clocks only restricts playback to the external clocks folder.")

    def test_the_waiting_reasons_of_only_name_both_storages(self):
        reasons = {"no-card": "Clocks only is waiting: internal storage has no clocks folder and no external storage is present.",
                   "missing-folder": "Clocks only is waiting: neither storage has a clocks folder.",
                   "no-clocks": "Clocks only is waiting: no included, available clock face can play."}
        for state, words in reasons.items():
            with self.subTest(state=state):
                target = StorageTarget(self, mode="only")
                target.only_folder = None
                target.only_state = state
                seen = support.run("clock-storage-ui", address=target.stand_in.address, settings=dict(rows=0, acts=[{"wait": 1200, "look": "later"}])).seen
                self.assertEqual(seen["later"]["reason"], words)

    def test_the_choice_reaches_the_emulator_and_is_kept_in_its_clocks_file(self):
        folder = entered(self, emulator_support.demo_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        seen = support.run("clock-storage-ui", address=f"127.0.0.1:{emulator.port}",
                           settings=dict(rows=2, acts=[{"storage": "internal", "until": {"said": SAVED["internal"], "disabled": False}, "look": "saved"}])).seen
        self.assertEqual(seen["saved"]["value"], "internal")
        self.assertEqual(json.loads(emulator.command("status"))["clock_storage"], "internal")
        self.assertEqual((folder / "clocks.txt").read_bytes(), b"odrig-clocks 3\nmode off\nmessage off\nstorage internal\n")


class TheMessages(unittest.TestCase):
    def test_the_refusals_of_only_name_the_clocks_folders_of_a_target_that_plays_both(self):
        refusals = [["in-use", "play 60001", None, True], ["in-use", "upload", None, True], ["in-use", "play 60001", None], ["in-use", "upload", None]]
        seen = support.run("texts", settings=dict(refusals=refusals, failures=[])).seen["refusals"]
        self.assertEqual(seen["in-use | play 60001 | null | both"],
                         "Clocks only allows playback inside the clocks folders. Leave Clocks only in Settings to play elsewhere. (in-use)")
        self.assertEqual(seen["in-use | upload | null | both"],
                         "Clocks only: choose a folder inside Clocks, a writable one on the card, or leave this mode in Settings. (in-use)")
        self.assertEqual(seen["in-use | play 60001 | null"],
                         "Clocks only allows playback inside the Clocks folder. Leave Clocks only in Settings to play elsewhere. (in-use)")
        self.assertEqual(seen["in-use | upload | null"],
                         "Clocks only: choose a writable external folder inside Clocks, or leave this mode in Settings. (in-use)")


if __name__ == "__main__":
    unittest.main()

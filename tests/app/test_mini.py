import json
import threading
import unittest

from tests.emulator import support as emulator_support
from . import support
from .test_clocks import Target as ClocksTarget
from .test_target import entered
from .test_look import SIZES


class Target(ClocksTarget):
    def __init__(self, test, active=False, supported=True, legacy=False):
        super().__init__(test)
        self.mini = dict(supported=supported, on=active, pending=False, requested=active, error=None, brightness=40)
        self.legacy = legacy
        self.accept = True
        self.lose_reply = False
        self.command_seen = threading.Event()

    def status(self):
        code, body = super().status()
        reply = json.loads(body)
        if not self.legacy:
            reply["mini"] = self.mini.copy()
        return code, json.dumps(reply) + "\n"

    def reply(self, line):
        if line.startswith(b"debug mini ") and self.answering:
            if self.refusal:
                return 200, json.dumps(dict(ok=False, error=self.refusal)) + "\n"
            self.mini["requested"] = line.endswith(b"on")
            self.mini["pending"] = not self.accept
            if self.accept:
                self.mini.update(on=self.mini["requested"], error=None)
            self.command_seen.set()
            if self.lose_reply:
                self.answering = False
                return 500, ""
            return 200, '{"ok":true}\n'
        return super().reply(line)

    def sent(self):
        return [line.decode() for _, line in self.stand_in.lines if line.startswith(b"debug")]


def run(target, acts=(), **kwargs):
    return support.run("mini", address=target.stand_in.address, settings={"acts": acts}, **kwargs).seen


class MiniatureControls(unittest.TestCase):
    def test_pending_is_not_optimistic_and_acknowledgement_is_followed(self):
        target = Target(self)
        target.accept = False
        def acknowledge():
            self.assertTrue(target.command_seen.wait(5))
            target.mini.update(on=True, pending=False)
        seen = run(target, [dict(tap="debug-mini", look="out"),
            dict(until=dict(text="Switching", checked=False, disabled=True), look="pending"),
            dict(step=True, until=dict(checked=True, disabled=False), look="active"),
            dict(reload=True, until=dict(checked=True, disabled=False), look="reloaded")], steps=[acknowledge])
        self.assertFalse(seen["out"]["checked"])
        self.assertTrue(seen["out"]["disabled"])
        self.assertIn("brightness", seen["active"]["indicator"])
        self.assertEqual(target.sent(), ["debug mini on"])

    def test_refusal_retains_the_confirmed_state_and_external_changes_are_followed(self):
        target = Target(self, active=True)
        target.refusal = "busy"
        def elsewhere():
            target.mini["on"] = False
        seen = run(target, [dict(tap="debug-mini", until=dict(text="busy", disabled=False), look="refused"),
            dict(step=True, until=dict(checked=False), look="external")], steps=[elsewhere])
        self.assertTrue(seen["refused"]["checked"])
        self.assertIsNone(seen["external"]["indicator"])
        self.assertEqual(target.sent(), ["debug mini off"])

    def test_lost_reply_is_unknown_then_reconnect_reads_status_without_resending(self):
        target = Target(self)
        target.lose_reply = True
        def recover():
            target.answering = True
        seen = run(target, [dict(tap="debug-mini", until=dict(unknown=True, disabled=True), look="lost"),
            dict(step=True, until=dict(checked=True, unknown=False, disabled=False), look="recovered")], steps=[recover])
        self.assertIn("unknown", seen["lost"]["indicator"])
        self.assertEqual(target.sent(), ["debug mini on"])

    def test_legacy_and_unsupported_targets_are_explicitly_unavailable(self):
        for target in (Target(self, legacy=True), Target(self, supported=False)):
            seen = run(target, [dict(tap="debug-mini")])["first"]
            self.assertTrue(seen["disabled"])
            self.assertTrue(seen["unknown"])
            self.assertIn("does not support", seen["said"])
            self.assertEqual(target.sent(), [])

    def test_setup_failure_can_retry_on_or_restore_normal_outputs(self):
        target = Target(self)
        target.mini.update(on=None, error="output-setup-failed", requested=True)
        seen = run(target, [dict(tap="mini-restore", until=dict(checked=False, unknown=False, disabled=False), look="restored")])
        self.assertTrue(seen["first"]["unknown"])
        self.assertEqual(seen["first"]["restore"], "Restore normal outputs")
        self.assertEqual(target.sent(), ["debug mini off"])
        target.mini.update(on=None, error="output-setup-failed", requested=True)
        seen = run(target, [dict(tap="debug-mini", until=dict(checked=True, unknown=False, disabled=False), look="retried")])
        self.assertEqual(target.sent(), ["debug mini off", "debug mini on"])

    def test_target_change_clears_active_state_without_enabling_the_new_target(self):
        first, second = Target(self, active=True), Target(self)
        seen = run(first, [dict(target=second.stand_in.address, until=dict(checked=False, disabled=False), look="second")])
        self.assertFalse(seen["changed"]["checked"])
        self.assertIsNone(seen["second"]["indicator"])
        self.assertEqual(first.sent() + second.sent(), [])

    def test_a_late_command_reply_from_the_previous_target_cannot_change_the_new_one(self):
        first, second = Target(self, active=True), Target(self)
        first.stand_in.delay = 0.5
        def sent():
            self.assertTrue(first.command_seen.wait(5))
        seen = run(first, [dict(tap="debug-mini", look="sending"), dict(step=True),
            dict(target=second.stand_in.address, until=dict(checked=False, disabled=False), look="second")], steps=[sent])
        self.assertTrue(seen["sending"]["checked"])
        self.assertTrue(seen["sending"]["disabled"])
        self.assertFalse(seen["changed"]["checked"])
        self.assertEqual(first.sent(), ["debug mini off"])
        self.assertEqual(second.sent(), [])

    def test_malformed_status_becomes_unknown_until_valid_readback(self):
        target = Target(self, active=True)
        def malformed():
            target.mini["on"] = "false"
        def recover():
            target.mini["on"] = False
        seen = run(target, [dict(step=True, until=dict(unknown=True, disabled=True), look="malformed"),
            dict(step=True, until=dict(unknown=False, checked=False, disabled=False), look="valid")], steps=[malformed, recover])
        self.assertIn("unknown", seen["malformed"]["indicator"])
        self.assertEqual(target.sent(), [])

    def test_small_and_landscape_layouts_and_global_active_indication(self):
        target = Target(self, active=True)
        for size in SIZES:
            seen = run(target, [dict(measure="layout"), dict(screen="Animations", look="away")], size=size)
            layout = seen["layout"]
            self.assertLessEqual(layout["scrollWidth"], layout["width"])
            box = next(control for control in layout["controls"] if control["what"] == "debug-mini")
            self.assertGreaterEqual(box["bottom"] - box["top"], 48)
            self.assertGreaterEqual(box["left"], 0)
            self.assertLessEqual(box["right"], size[0])
            self.assertIn("brightness", seen["away"]["indicator"])

    def test_browser_controls_the_real_emulator_and_tracks_another_controller(self):
        folder = entered(self, emulator_support.demo_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        seen = support.run("mini", address=f"127.0.0.1:{emulator.port}", settings={"acts": [
            dict(tap="debug-mini", until=dict(checked=True, disabled=False), look="active"),
            dict(step=True, until=dict(checked=False), look="elsewhere")]},
            steps=[lambda: emulator.command("debug mini off")]).seen
        self.assertIn("active", seen["active"]["said"])
        self.assertIsNone(seen["elsewhere"]["indicator"])


if __name__ == "__main__":
    unittest.main()

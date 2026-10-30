import json
import threading
import unittest

from tests.emulator import support as emulator_support
from . import support
from .test_clocks import Target as ClocksTarget
from .test_target import entered


class Target(ClocksTarget):
    def __init__(self, test, saved=None, legacy=False, unsupported=False):
        super().__init__(test)
        self.default = 128
        self.saved = {1: saved, 2: None}
        self.animation = 1
        self.file = "hello.odrg"
        self.legacy = legacy
        self.unsupported = unsupported
        self.dimming_error = None
        self.malformed = False
        self.lose_reply = False
        self.command_seen = threading.Event()
        self.on = True

    def status(self):
        code, body = super().status()
        reply = json.loads(body)
        saved = self.saved.get(self.animation)
        reply.update(brightness=self.default, animation=self.animation, file=self.file, on=self.on)
        if not self.legacy:
            reply["dimming"] = {"value": saved if saved is not None else self.default,
                "saved": saved, "error": self.dimming_error}
            if self.malformed:
                reply["dimming"]["saved"] = False
            if self.unsupported:
                reply["dimming"] = None
        return code, json.dumps(reply) + "\n"

    def reply(self, line):
        if line.startswith(b"brightness ") and self.answering:
            if self.refusal:
                return 200, json.dumps(dict(ok=False, error=self.refusal)) + "\n"
            words = line.decode().split()
            if len(words) == 2:
                self.default = int(words[1])
            elif words[-1] == "default":
                self.saved[int(words[1])] = None
            else:
                self.saved[int(words[1])] = int(words[2])
            self.command_seen.set()
            if self.lose_reply:
                self.answering = False
                return 500, ""
            return 200, '{"ok":true}\n'
        return super().reply(line)

    def sent(self):
        return [line.decode() for _, line in self.stand_in.lines if line.startswith(b"brightness")]


def run(target, acts=(), **kwargs):
    return support.run("brightness", address=target.stand_in.address, settings={"acts": acts}, **kwargs).seen


class BrightnessControls(unittest.TestCase):
    def test_capture_waits_for_an_already_entered_default_value(self):
        target = Target(self)
        target.stand_in.delay = 0.3
        seen = run(target, [dict(type="0", enter=True),
            dict(tap=True, until=dict(checked=True, disabled=False), look="saved")])
        self.assertEqual(target.sent(), ["brightness 0", "brightness 1 0 save"])
        self.assertEqual(seen["saved"]["number"], "0")

    def test_dirty_numeric_value_is_confirmed_before_capture_and_default_restoration(self):
        target = Target(self)
        seen = run(target, [dict(type="0"), dict(tap=True, until=dict(checked=True, disabled=False), look="saved"),
            dict(tap=True, until=dict(checked=False, disabled=False), look="default")])
        self.assertEqual(target.sent(), ["brightness 0", "brightness 1 0 save", "brightness 1 default"])
        self.assertEqual((seen["saved"]["slider"], seen["saved"]["label"]), (0, "This animation’s brightness"))
        self.assertEqual(seen["default"]["label"], "Default brightness")
        lines = [line for _, line in target.stand_in.lines]
        start, end = lines.index(b"brightness 0"), lines.index(b"brightness 1 0 save")
        self.assertIn(b"status", lines[start + 1:end])

    def test_pointer_mode_change_commits_dirty_override_before_removing_it(self):
        target = Target(self, saved=20)
        seen = run(target, [dict(type="24"), dict(pointer=True, leave=True, tap=True,
            until=dict(checked=False, disabled=False), look="default")])
        self.assertEqual(target.sent(), ["brightness 1 24 save", "brightness 1 default"])
        self.assertEqual(seen["default"]["number"], "128")

    def test_refused_numeric_commit_does_not_proceed_to_capture(self):
        target = Target(self)
        target.refusal = "busy"
        seen = run(target, [dict(type="0", enter=True), dict(tap=True, wait=1500, look="refused")])
        self.assertFalse(seen["refused"]["checked"])
        self.assertEqual(target.sent(), ["brightness 0"])

    def test_saved_slider_drag_sends_one_durable_value_on_release(self):
        target = Target(self, saved=0)
        seen = run(target, [dict(slide=100), dict(slide=70, wait=350), dict(step=True, look="held"),
            dict(release=True, until=dict(slider=70, disabled=False), wait=300, look="saved")],
            steps=[lambda: self.assertEqual(target.sent(), [])])
        self.assertTrue(seen["first"]["checked"])
        self.assertEqual(seen["held"]["number"], "70")
        self.assertEqual(target.sent(), ["brightness 1 70 save"])
        self.assertEqual(target.default, 128)

    def test_each_override_release_commits_even_after_a_fast_external_change(self):
        target = Target(self, saved=20)
        def elsewhere():
            target.saved[1] = 10
        run(target, [dict(slide=70, release=True, until=dict(disabled=False)),
            dict(step=True), dict(slide=70, release=True, wait=400)], steps=[elsewhere])
        self.assertEqual(target.sent(), ["brightness 1 70 save", "brightness 1 70 save"])
        self.assertEqual(target.saved[1], 70)

    def test_invalid_dirty_text_blocks_mode_change(self):
        target = Target(self)
        seen = run(target, [dict(type="999"), dict(tap=True, look="invalid")])
        self.assertFalse(seen["invalid"]["checked"])
        self.assertEqual(seen["invalid"]["range"], "The brightness is 0 to 255.")
        self.assertEqual(target.sent(), [])

    def test_numeric_override_edits_and_reload_follow_confirmed_zero_while_off(self):
        target = Target(self, saved=0)
        target.on = False
        seen = run(target, [dict(type="24"), dict(enter=True, until=dict(number="24", disabled=False)),
            dict(reload=True, until=dict(checked=True, number="24"), look="reloaded")])
        self.assertEqual(seen["first"]["slider"], 0)
        self.assertEqual(seen["reloaded"]["file"], "Animation 1: hello.odrg")
        self.assertEqual(target.sent(), ["brightness 1 24 save"])
        self.assertEqual(target.default, 128)

    def test_another_controller_updates_value_and_mode(self):
        target = Target(self, saved=20)
        def elsewhere():
            target.saved[1] = None
            target.default = 83
        seen = run(target, [dict(step=True, until=dict(checked=False, slider=83), look="other")], steps=[elsewhere])
        self.assertEqual(seen["other"]["label"], "Default brightness")
        self.assertEqual(target.sent(), [])

    def test_animation_identity_change_cancels_held_and_dirty_edits(self):
        for act in (dict(slide=70), dict(type="70")):
            with self.subTest(edit=act):
                target = Target(self, saved=20)
                def changed():
                    target.animation, target.file = 2, "dvd.odrg"
                seen = run(target, [act, dict(step=True, until=dict(file="Animation 2: dvd.odrg", number="128"), look="changed"),
                    dict(release=True, wait=300)], steps=[changed])
                self.assertFalse(seen["changed"]["checked"])
                self.assertEqual(target.sent(), [])

    def test_save_queued_behind_new_identity_status_is_cancelled_before_sending(self):
        target = Target(self, saved=20)
        reported = threading.Event()
        original = target.status
        def changed_status():
            target.animation, target.file = 2, "dvd.odrg"
            reported.set()
            return original()
        def arm():
            target.stand_in.delay = 0.8
            target.status = changed_status
        def waiting():
            self.assertTrue(reported.wait(5))
        seen = run(target, [dict(step=True), dict(step=True), dict(slide=70, release=True),
            dict(until=dict(file="Animation 2: dvd.odrg", disabled=False, slider=128), wait=1200, look="new")], steps=[arm, waiting])
        self.assertFalse(seen["new"]["checked"])
        self.assertEqual(target.sent(), [])

    def test_refusal_keeps_confirmed_preference(self):
        target = Target(self, saved=20)
        target.refusal = "storage-error"
        seen = run(target, [dict(tap=True, until=dict(text="could not save", disabled=False), look="refused")])
        self.assertTrue(seen["refused"]["checked"])
        self.assertEqual(target.sent(), ["brightness 1 default"])

    def test_lost_reply_reads_fresh_status_without_resending(self):
        target = Target(self)
        target.lose_reply = True
        def recover():
            target.answering = True
        seen = run(target, [dict(tap=True, until=dict(unknown=True, disabled=True), look="lost"),
            dict(step=True, until=dict(checked=True, unknown=False, disabled=False), look="recovered")], steps=[recover])
        self.assertIn("unknown", seen["lost"]["said"])
        self.assertEqual(target.sent(), ["brightness 1 128 save"])

    def test_legacy_error_and_no_animation_disable_only_override(self):
        legacy, unsupported, damaged, empty = Target(self, legacy=True), Target(self, unsupported=True), Target(self), Target(self)
        damaged.dimming_error = "settings-unreadable"
        empty.animation, empty.file = None, None
        for target, text in ((legacy, "does not support"), (unsupported, "does not support"), (damaged, "unreadable"), (empty, "Play an animation")):
            with self.subTest(reason=text):
                seen = run(target, [dict(tap=True)])["first"]
                self.assertTrue(seen["disabled"])
                self.assertIn(text, seen["said"])
                self.assertEqual(target.sent(), [])

    def test_malformed_dimming_is_unknown_until_recovery(self):
        target = Target(self, saved=20)
        def malformed():
            target.malformed = True
        def recover():
            target.malformed, target.saved[1] = False, None
        seen = run(target, [dict(step=True, until=dict(unknown=True, disabled=True)),
            dict(step=True, until=dict(unknown=False, checked=False, disabled=False), look="recovered")], steps=[malformed, recover])
        self.assertEqual(seen["recovered"]["slider"], 128)
        self.assertEqual(target.sent(), [])

    def test_other_command_replies_cannot_revalidate_a_failed_brightness_status(self):
        target = Target(self, saved=20)
        def malformed():
            target.malformed = True
        seen = run(target, [dict(step=True, until=dict(unknown=True, disabled=True)),
            dict(powerProbe=True)], steps=[malformed])
        self.assertFalse(seen["probeEnabled"])
        self.assertEqual(target.sent(), [])

    def test_late_reply_keeps_captured_target_and_cannot_repaint_new_target(self):
        first, second = Target(self, saved=20), Target(self, saved=0)
        first.stand_in.delay = 0.5
        def sent():
            self.assertTrue(first.command_seen.wait(5))
        seen = run(first, [dict(tap=True), dict(step=True),
            dict(target=second.stand_in.address, until=dict(checked=True, slider=0, disabled=False), look="second")], steps=[sent])
        self.assertTrue(seen["changed"]["unknown"])
        self.assertEqual(first.sent(), ["brightness 1 default"])
        self.assertEqual(second.sent(), [])

    def test_small_and_landscape_layouts_fit_and_keep_touch_room(self):
        target = Target(self, saved=0)
        for size in ((320, 740), (740, 360), (480, 900)):
            with self.subTest(size=size):
                seen = run(target, [dict(measure="layout")], size=size)["layout"]
                self.assertLessEqual(seen["scrollWidth"], seen["width"])
                box = next(control for control in seen["controls"] if control["what"] == "level-override")
                self.assertGreaterEqual(box["bottom"] - box["top"], 48)
                self.assertGreaterEqual(box["left"], 0)
                self.assertLessEqual(box["right"], size[0])
                slider = next(control for control in seen["controls"] if control["what"] == "level")
                self.assertGreater(min(box["bottom"], slider["bottom"]), max(box["top"], slider["top"]))

    def test_real_emulator_capture_other_controller_and_persistence_on_reload(self):
        folder = entered(self, emulator_support.demo_show())
        emulator = entered(self, emulator_support.Emulator(folder))
        self.assertEqual(json.loads(emulator.command("play 1")), {"ok": True})
        def elsewhere():
            self.assertEqual(json.loads(emulator.command("brightness 83")), {"ok": True})
        seen = support.run("brightness", address=f"127.0.0.1:{emulator.port}", settings={"acts": [
            dict(type="0"), dict(tap=True, until=dict(checked=True, disabled=False)),
            dict(step=True, wait=1200, look="other"), dict(reload=True, until=dict(checked=True, slider=0)),
            dict(tap=True, until=dict(checked=False, slider=83, disabled=False), look="default")]}, steps=[elsewhere]).seen
        self.assertEqual(seen["other"]["slider"], 0)
        self.assertEqual(seen["default"]["number"], "83")
        self.assertEqual((folder / "brightness.txt").read_bytes(), b"odrig-brightness 1\n")

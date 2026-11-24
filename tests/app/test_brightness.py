import json
import threading
import unittest

from tests.emulator import support as emulator_support
from . import support
from .test_clocks import Target as ClocksTarget
from .test_target import entered

# The line of the file while a gesture on animation 1 lasts after another began to play.
AWAY = "Animation 1: hello.odrg, no longer playing"
# The panel's line after a confirmed change of the default.
DEFAULT_LINE = ("The default, {}, is for every animation without its own brightness, until the installation starts again. "
                "Tick Override for this animation to keep a value for the animation playing.")


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
        # `saved <id>` answers what the stand-in keeps, or the value named here.
        self.readback = {}

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
        if line.startswith(b"saved ") and self.answering:
            number = int(line.split()[1])
            value = self.readback.get(number, self.saved.get(number))
            return 200, json.dumps({"ok": True, "brightness": value, "repeat": None, "start": False}) + "\n"
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

    def test_a_held_drag_or_typed_value_stays_with_its_animation_across_a_change(self):
        for act, end in ((dict(slide=70), dict(release=True)), (dict(type="70"), dict(enter=True))):
            with self.subTest(edit=act):
                target = Target(self, saved=20)
                def changed():
                    target.animation, target.file = 2, "dvd.odrg"
                seen = run(target, [act, dict(step=True, until=dict(file=AWAY), look="away"),
                    dict(**end, until=dict(text="Saved 70 for hello.odrg.", file="Animation 2: dvd.odrg"), look="saved")], steps=[changed])
                away = seen["away"]
                self.assertEqual((away["number"], away["label"], away["checked"]), ("70", "This animation’s brightness", True))
                self.assertEqual(target.sent(), ["brightness 1 70 save"])
                self.assertIn(b"saved 1", [line for _, line in target.stand_in.lines])
                self.assertEqual((target.saved, target.default), ({1: 70, 2: None}, 128))
                self.assertEqual((seen["saved"]["number"], seen["saved"]["checked"]), ("128", False))

    def test_a_default_drag_across_a_change_stays_an_edit_of_the_default(self):
        target = Target(self)
        def changed():
            target.animation, target.file = 2, "dvd.odrg"
        seen = run(target, [dict(slide=70), dict(step=True, until=dict(file=AWAY), look="away"),
            dict(slide=60), dict(release=True, until=dict(file="Animation 2: dvd.odrg", number="60", text="The default, 60,"), look="after")],
            steps=[changed])
        self.assertEqual(seen["away"]["label"], "Default brightness")
        self.assertEqual(seen["after"]["said"], DEFAULT_LINE.format(60))
        self.assertEqual((target.default, target.saved), (60, {1: None, 2: None}))
        self.assertTrue(target.sent())
        self.assertTrue(all(len(line.split()) == 2 for line in target.sent()), target.sent())

    def test_a_confirmed_default_says_it_is_not_kept_after_a_start(self):
        target = Target(self)
        seen = run(target, [dict(type="40", enter=True, until=dict(text="The default, 40,"), look="said")])
        self.assertEqual(seen["said"]["said"], DEFAULT_LINE.format(40))
        self.assertEqual(target.sent(), ["brightness 40"])

    def test_a_move_to_another_animation_holds_new_gestures_for_a_second(self):
        target = Target(self, saved=20)
        def changed():
            target.animation, target.file = 2, "dvd.odrg"
        seen = run(target, [dict(step=True, until=dict(file="Animation 2: dvd.odrg"), look="held"), dict(tap=True, look="tapped"),
            dict(wait=1300, look="free"), dict(tap=True, until=dict(checked=True, disabled=False), look="taken")], steps=[changed])
        first, held, free = seen["first"], seen["held"], seen["free"]
        self.assertEqual((first["bold"], first["disabled"], first["sliderDisabled"]), (False, False, False))
        self.assertEqual((held["bold"], held["disabled"], held["sliderDisabled"], held["fieldDisabled"]), (True, True, True, True))
        self.assertFalse(seen["tapped"]["checked"])
        self.assertEqual((free["bold"], free["disabled"], free["sliderDisabled"], free["fieldDisabled"]), (False, False, False, False))
        self.assertEqual(target.sent(), ["brightness 2 128 save"])

    def test_the_end_of_a_gesture_that_moves_the_panel_holds_the_next(self):
        target = Target(self, saved=20)
        def changed():
            target.animation, target.file = 2, "dvd.odrg"
        seen = run(target, [dict(slide=70), dict(step=True, until=dict(file=AWAY)),
            dict(release=True, until=dict(file="Animation 2: dvd.odrg"), look="moved")], steps=[changed])
        self.assertTrue(seen["moved"]["bold"])
        self.assertTrue(seen["moved"]["sliderDisabled"])

    def test_an_override_drag_across_a_clock_stays_with_its_animation(self):
        target = Target(self, saved=20)
        def clock():
            target.animation, target.file = 60003, "clocks/c1.odrg"
        seen = run(target, [dict(slide=70), dict(step=True, until=dict(file=AWAY)),
            dict(release=True, until=dict(text="Saved 70 for hello.odrg.", file="Animation 60003: clocks/c1.odrg"), look="saved")], steps=[clock])
        self.assertEqual(target.sent(), ["brightness 1 70 save"])
        self.assertEqual((target.saved.get(60003), target.default), (None, 128))
        self.assertFalse(seen["saved"]["checked"])

    def test_a_refused_save_for_an_animation_no_longer_playing_is_said(self):
        target = Target(self, saved=20)
        def changed():
            target.animation, target.file = 2, "dvd.odrg"
            target.refusal = "unknown-id"
        seen = run(target, [dict(slide=70), dict(step=True, until=dict(file=AWAY)),
            dict(release=True, until=dict(text="Not saved for hello.odrg."), look="refused")], steps=[changed])
        self.assertEqual(seen["refused"]["said"], "Not saved for hello.odrg. This animation is no longer listed. Read fresh status before trying again.")
        self.assertEqual((target.sent(), target.saved[1]), (["brightness 1 70 save"], 20))

    def test_a_read_back_that_differs_is_said(self):
        target = Target(self, saved=20)
        target.readback = {1: 33}
        def changed():
            target.animation, target.file = 2, "dvd.odrg"
        seen = run(target, [dict(slide=70), dict(step=True, until=dict(file=AWAY)),
            dict(release=True, until=dict(text="keeps"), look="differs")], steps=[changed])
        self.assertEqual(seen["differs"]["said"], "hello.odrg keeps 33.")
        self.assertEqual(target.sent(), ["brightness 1 70 save"])

    def test_a_lost_reply_for_an_animation_no_longer_playing_is_said_and_not_sent_again(self):
        target = Target(self, saved=20)
        target.lose_reply = True
        def changed():
            target.animation, target.file = 2, "dvd.odrg"
        def recover():
            target.answering = True
        seen = run(target, [dict(slide=70), dict(step=True, until=dict(file=AWAY)),
            dict(release=True, until=dict(unknown=True)),
            dict(step=True, until=dict(unknown=False, text="no reply came"), look="said")], steps=[changed, recover])
        self.assertEqual(seen["said"]["said"], "Brightness for hello.odrg is unknown: no reply came. It is not sent again.")
        self.assertEqual(target.sent(), ["brightness 1 70 save"])

    def test_a_target_chosen_during_a_drag_takes_nothing_and_says_so(self):
        first, second = Target(self, saved=20), Target(self, saved=0)
        seen = run(first, [dict(slide=70),
            dict(target=second.stand_in.address, until=dict(checked=True, slider=0, disabled=False), look="second"),
            dict(release=True, wait=400)])
        self.assertEqual((first.sent(), second.sent()), ([], []))
        self.assertEqual(seen["second"]["said"], "Not saved for hello.odrg: another installation was chosen.")

    def lagging(self, target):
        """Steps that make the stand-in play animation 2 from its next status, whose reply comes
        0.8 s late, and wait until it has been asked: the panel still shows animation 1."""
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
        return [arm, waiting]

    def test_a_save_queued_behind_a_change_still_goes_to_its_animation(self):
        target = Target(self, saved=20)
        seen = run(target, [dict(step=True), dict(step=True), dict(slide=70, release=True),
            dict(until=dict(file="Animation 2: dvd.odrg", text="Saved 70 for hello.odrg.", disabled=False), look="new")],
            steps=self.lagging(target))
        self.assertFalse(seen["new"]["checked"])
        self.assertEqual(target.sent(), ["brightness 1 70 save"])
        self.assertEqual(target.saved, {1: 70, 2: None})

    def test_a_press_while_the_panel_still_shows_the_animation_that_left_saves_for_it(self):
        target = Target(self)
        seen = run(target, [dict(step=True), dict(step=True), dict(tap=True),
            dict(until=dict(file="Animation 2: dvd.odrg", text="Saved 128 for hello.odrg."), look="saved")],
            steps=self.lagging(target))
        self.assertFalse(seen["saved"]["checked"])
        self.assertEqual(target.sent(), ["brightness 1 128 save"])
        self.assertEqual(target.saved, {1: 128, 2: None})

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

    def test_uncertainty_discards_a_held_override_instead_of_resending_it(self):
        target = Target(self, saved=20)
        def malformed():
            target.malformed = True
        def recover():
            target.malformed = False
        seen = run(target, [dict(slide=70), dict(step=True, until=dict(unknown=True, disabled=True)),
            dict(step=True, until=dict(unknown=False, disabled=False), look="recovered"),
            dict(release=True, wait=300)], steps=[malformed, recover])
        self.assertEqual(seen["recovered"]["number"], "20")
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
                zoom = next(control for control in seen["controls"] if control["what"] == "level-zoom")
                self.assertGreaterEqual(zoom["bottom"] - zoom["top"], 48 - 0.01)
                self.assertGreaterEqual(zoom["left"], 0)
                self.assertLessEqual(zoom["right"], size[0])
                self.assertLessEqual(zoom["bottom"], slider["top"])

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


class Zoom(unittest.TestCase):
    """The brightness zoom: two pins that set the range the slider moves through, kept on the
    phone and never sent."""

    def test_the_zoom_sets_the_range_the_slider_moves_through(self):
        target = Target(self)
        seen = run(target, [dict(zoom=[2, 12], look="zoomed"), dict(slide=12, release=True, until=dict(number="12"), wait=300)])
        self.assertEqual((seen["first"]["min"], seen["first"]["max"], seen["first"]["zoomSaid"]), (0, 255, "Zoom 0 to 255"))
        zoomed = seen["zoomed"]
        self.assertEqual((zoomed["min"], zoomed["max"], zoomed["zoomSaid"]), (2, 12, "Zoom 2 to 12"))
        self.assertEqual((target.sent(), target.default), (["brightness 12"], 12))

    def test_the_pins_never_cross_and_send_nothing(self):
        target = Target(self)
        seen = run(target, [dict(zoom=[2, 12]), dict(pin=["start", 200], look="start"), dict(pin=["end", 0], look="end")])
        self.assertEqual((seen["start"]["zoomStart"], seen["start"]["zoomEnd"], seen["start"]["min"]), (11, 12, 11))
        self.assertEqual((seen["end"]["zoomStart"], seen["end"]["zoomEnd"], seen["end"]["max"]), (11, 12, 12))
        self.assertEqual(target.sent(), [])

    def test_a_value_outside_the_zoom_stands_in_the_field_and_never_moves_the_zoom(self):
        target = Target(self)
        seen = run(target, [dict(zoom=[2, 12], look="above"),
            dict(type="1", enter=True, until=dict(outside="1 is below the zoom 2 to 12."), look="below")])
        above, below = seen["above"], seen["below"]
        self.assertEqual((above["number"], above["slider"], above["outside"]), ("128", 12, "128 is above the zoom 2 to 12."))
        self.assertEqual((below["number"], below["slider"], below["zoomStart"], below["zoomEnd"]), ("1", 2, 2, 12))
        self.assertEqual(target.sent(), ["brightness 1"])

    def test_both_modes_and_a_reload_keep_the_zoom(self):
        target = Target(self, saved=5)
        seen = run(target, [dict(zoom=[2, 12], look="override"), dict(tap=True, until=dict(checked=False, disabled=False), look="default"),
            dict(reload=True, until=dict(zoomStart=2, zoomEnd=12), look="reloaded")])
        self.assertEqual((seen["override"]["label"], seen["override"]["slider"], seen["override"]["outside"]),
                         ("This animation’s brightness", 5, None))
        default = seen["default"]
        self.assertEqual((default["label"], default["min"], default["max"], default["outside"]),
                         ("Default brightness", 2, 12, "128 is above the zoom 2 to 12."))
        self.assertEqual((seen["reloaded"]["min"], seen["reloaded"]["max"]), (2, 12))
        self.assertEqual(target.sent(), ["brightness 1 default"])


class ZoomKept(unittest.TestCase):
    def test_the_kept_pair_is_read_back_and_anything_else_is_the_full_range(self):
        seen = support.run("zoom-kept").seen
        full, narrow = {"start": 0, "end": 255}, {"start": 2, "end": 12}
        self.assertEqual((seen["none"], seen["throwing"], seen["empty"], seen["threw"]), (full, full, full, False))
        self.assertEqual(seen["malformed"], [full] * 8)
        self.assertEqual((seen["good"], seen["full"], seen["readBack"]), (narrow, full, narrow))
        self.assertEqual(seen["written"], {"odrig.brightness-zoom": "2 12"})
        self.assertEqual(seen["words"], "Zoom 2 to 12")
        self.assertEqual(seen["outside"], ["40 is above the zoom 2 to 12.", "1 is below the zoom 2 to 12.", None, None])
        self.assertEqual(seen["moved"], [{"start": 11, "end": 12}, {"start": 2, "end": 3}, full, {"start": 0, "end": 12}])

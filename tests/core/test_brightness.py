import json
import pathlib
import unittest

from . import support
from .test_mini import files_for
from .test_mini import ENABLE, frame as miniature_frame, projected
from .test_drive import SHOW, DRIVE, a_drive, asked, with_drive
from .test_texts import text_of
from .test_clocks import clock_of
from .test_pictures import picture_of
from . import test_clocks as clocks
from .test_upload import Script


def files():
    return files_for([[(255, 127, 33)] * 60 for _ in range(60)])


def replies(run):
    return [json.loads(line[6:]) for line in run.lines if line.startswith("reply ")]


def last_rgb(run):
    return bytes.fromhex(next(line.split()[2] for line in reversed(run.lines) if line.startswith("data 1 ")))


def preferences(source, *lines):
    return {**source, "brightness.txt": "odrig-brightness 1\n" + "".join(line + "\n" for line in lines)}


class AnimationBrightness(unittest.TestCase):
    def test_saved_value_replaces_default_and_survives_restart(self):
        with support.installed(files()) as folder:
            saved = support.session(folder, ["poll 0", support.line(0, "brightness 1 15 save"), "poll 20", support.line(20, "status")])
            self.assertEqual(replies(saved)[0], {"ok": True})
            self.assertEqual(replies(saved)[1]["dimming"], dict(value=15, saved=15, error=None))
            self.assertEqual(last_rgb(saved)[:3], bytes((15, 7, 2)))
            self.assertEqual(support.folder_files(folder)["brightness.txt"], b"odrig-brightness 1\n15 f picture.odrg\n")
            again = support.session(folder, [support.line(0, "brightness 0"), "poll 0", support.line(0, "status")])
            self.assertEqual(replies(again)[-1]["brightness"], 0)
            self.assertEqual(replies(again)[-1]["dimming"]["value"], 15)
            self.assertEqual(last_rgb(again)[:3], bytes((15, 7, 2)))

    def test_zero_is_present_and_removal_uses_default_without_changing_show(self):
        original = files()
        with support.installed(original) as folder:
            saved = support.session(folder, ["poll 0", support.line(0, "brightness 1 0 save"), "poll 20", support.line(20, "status")])
            self.assertEqual(replies(saved)[0], {"ok": True})
            self.assertEqual(replies(saved)[-1]["dimming"], dict(value=0, saved=0, error=None))
            self.assertFalse(any(last_rgb(saved)))
            removed = support.session(folder, ["poll 0", support.line(0, "brightness 1 default"), "poll 20", support.line(20, "status")])
            self.assertEqual(replies(removed)[0], {"ok": True})
            self.assertEqual(replies(removed)[-1]["dimming"], dict(value=255, saved=None, error=None))
            self.assertEqual(last_rgb(removed)[:3], bytes((255, 127, 33)))
            show = original["show.json"].encode() if isinstance(original["show.json"], str) else original["show.json"]
            self.assertEqual(support.folder_files(folder)["show.json"], show)

    def test_corrupt_settings_report_trouble_without_invalidating_the_show(self):
        source = files()
        source["brightness.txt"] = b"odrig-brightness 1\n20 f picture.odrg\ntruncated"
        run = support.start(source, ["poll 0", support.line(0, "status"), support.line(0, "brightness 1 9 save")])
        self.assertIsNone(run.error)
        self.assertEqual(replies(run)[0]["dimming"], dict(value=255, saved=None, error="settings-unreadable"))
        self.assertEqual(replies(run)[1], dict(ok=False, error="storage-error"))
        self.assertEqual(last_rgb(run)[:3], bytes((255, 127, 33)))

    def test_bad_forms_are_refused_without_creating_settings(self):
        bad = ["brightness 1 256 save", "brightness 0 15 save", "brightness 1 -1 save", "brightness 1 default extra",
               "brightness 1 15 keep", "brightness 1 15 save extra"]
        with support.installed(files()) as folder:
            run = support.session(folder, [support.line(0, line) for line in bad])
            self.assertEqual(replies(run), [dict(ok=False, error="bad-argument")] * len(bad))
            self.assertNotIn("brightness.txt", support.folder_files(folder))

    def test_duplicate_items_share_the_file_and_cycles_unknown_ids_are_refused(self):
        source = files()
        show = json.loads(source["show.json"])
        show["items"] += [{"id": 7, "file": "picture.odrg"}, {"id": 9, "cycle": [1, 7], "seconds": 1}]
        source["show.json"] = json.dumps(show)
        run, kept = support.start_and_keep(source, ["poll 0", support.line(0, "brightness 7 17 save"),
            "poll 20", support.line(20, "status"), support.line(20, "brightness 9 10 save"), support.line(20, "brightness 99 default")])
        self.assertEqual(replies(run)[1]["dimming"]["saved"], 17)
        self.assertEqual(replies(run)[2:], [dict(ok=False, error="in-use"), dict(ok=False, error="unknown-id")])
        self.assertEqual(kept["brightness.txt"], b"odrig-brightness 1\n17 f picture.odrg\n")

    def test_zero_default_does_not_suppress_override_but_power_always_does(self):
        source = preferences(files(), "15 f picture.odrg")
        run = support.start(source, [support.line(0, "brightness 0"), "poll 0", support.line(0, "off"),
            "poll 20", support.line(20, "on"), "poll 40", support.line(40, "status")])
        frames = [bytes.fromhex(line.split()[2]) for line in run.lines if line.startswith("data 1 ")]
        self.assertEqual(frames[0][:3], bytes((15, 7, 2)))
        self.assertFalse(any(frames[1]))
        self.assertEqual(frames[2], frames[0])
        self.assertEqual(replies(run)[-1]["brightness"], 0)
        self.assertEqual(replies(run)[-1]["dimming"]["value"], 15)

    def test_miniature_caps_the_selected_override_without_changing_the_default(self):
        pixels = [[(255, 127, 33)] * 60 for _ in range(60)]
        source = preferences(files(), "80 f picture.odrg")
        run = support.start(source, [*ENABLE, support.line(0, "brightness 0"), "poll 0", "mini frame", support.line(0, "status")])
        state = replies(run)[-1]
        self.assertEqual((state["brightness"], state["dimming"]["value"], state["mini"]["brightness"]), (0, 80, 40))
        self.assertEqual(last_rgb(run)[:3], bytes((80, 40, 10)))
        self.assertEqual(miniature_frame(run), projected(pixels, 40))

    def test_unchanged_save_writes_nothing(self):
        source = preferences(files(), "15 f picture.odrg", "0 x absent/same.odrg")
        run, kept = support.start_and_keep(source, ["poll 0", support.line(0, "brightness 1 15 save")], ["--trace-store"])
        self.assertEqual(replies(run), [dict(ok=True)])
        self.assertFalse(any(line.startswith("store ") for line in run.lines))
        self.assertEqual(kept["brightness.txt"], source["brightness.txt"].encode())

    def test_full_settings_never_evict_unlisted_paths(self):
        source = preferences(files(), *(f"7 f old-{n}.odrg" for n in range(512)))
        run, kept = support.start_and_keep(source, [support.line(0, "brightness 1 12 save")])
        self.assertEqual(replies(run), [dict(ok=False, error="no-space")])
        self.assertEqual(kept["brightness.txt"], source["brightness.txt"].encode())

    def test_existing_entry_can_change_or_be_removed_at_full_capacity(self):
        source = preferences(files(), *(f"7 f old-{n}.odrg" for n in range(511)), "30 f picture.odrg")
        run, kept = support.start_and_keep(source, ["poll 0", support.line(0, "brightness 1 15 save"),
            "poll 20", support.line(20, "status"), support.line(20, "brightness 1 default"), "poll 40", support.line(40, "status")])
        self.assertEqual(replies(run)[0], dict(ok=True))
        self.assertEqual(replies(run)[1]["dimming"]["saved"], 15)
        self.assertEqual(replies(run)[2], dict(ok=True))
        self.assertIsNone(replies(run)[3]["dimming"]["saved"])
        self.assertEqual(len(kept["brightness.txt"].splitlines()), 512)
        self.assertNotIn(b"picture.odrg", kept["brightness.txt"])
        self.assertIn(b"old-510.odrg", kept["brightness.txt"])

    def test_malformed_files_discard_partial_preferences(self):
        malformed = [b"", b"odrig-brightness 2\n", b"odrig-brightness 1\n00 f picture.odrg\n",
                     b"odrig-brightness 1\n256 f picture.odrg\n", b"odrig-brightness 1\n1 z picture.odrg\n",
                     preferences(files(), *(f"1 x absent-{n}.odrg" for n in range(33)))["brightness.txt"].encode()]
        for content in malformed:
            with self.subTest(content=content[:60]):
                run = support.start({**files(), "brightness.txt": content}, ["poll 0", support.line(0, "status")])
                self.assertIsNone(run.error)
                self.assertEqual(replies(run)[0]["dimming"], dict(value=255, saved=None, error="settings-unreadable"))
                self.assertIn("brightness unreadable", run.logs)

    def test_first_duplicate_value_wins_including_zero(self):
        run = support.start(preferences(files(), "0 f picture.odrg", "90 f picture.odrg"), ["poll 0", support.line(0, "status")])
        self.assertEqual(replies(run)[0]["dimming"], dict(value=0, saved=0, error=None))
        self.assertFalse(any(last_rgb(run)))

    def test_noncurrent_files_are_set_before_their_first_frame(self):
        source = files()
        show = json.loads(source["show.json"])
        show["items"].append(dict(id=2, file="other.odrg"))
        source["show.json"] = json.dumps(show)
        source["other.odrg"] = source["picture.odrg"]
        run = support.start(source, ["poll 0", support.line(0, "brightness 2 18 save"), support.line(0, "status"),
            support.line(0, "play 2"), "poll 20", support.line(20, "status")])
        self.assertIsNone(replies(run)[1]["dimming"]["saved"])
        self.assertEqual(replies(run)[-1]["animation"], 2)
        self.assertEqual(replies(run)[-1]["dimming"]["value"], 18)
        self.assertEqual(last_rgb(run)[:3], bytes((18, 9, 2)))

    def test_text_and_widget_selection_matches_the_same_default_without_timing_changes(self):
        contents = [text_of(width=60, height=60, effect="static"),
                    *(clock_of(widget, canvas=(60, 60)) for widget in (1, 2, 3)),
                    *(picture_of(widget, canvas=(60, 60)) for widget in ("picture-dial", "picture-display"))]
        for content in contents:
            source = files()
            source["picture.odrg"] = content
            default = dict(source)
            show = json.loads(default["show.json"])
            show["brightness"] = 15
            default["show.json"] = json.dumps(show)
            script = ["poll 0", "poll 20", "poll 1200", support.line(1200, "status")]
            plain = support.start(default, script)
            overridden = support.start(preferences(source, "15 f picture.odrg"), script)
            self.assertEqual([line for line in overridden.lines if line.startswith("data ")],
                             [line for line in plain.lines if line.startswith("data ")])
            a, b = replies(plain)[0], replies(overridden)[0]
            self.assertEqual((a["seed"], a["loop"], a["repeat"]), (b["seed"], b["loop"], b["repeat"]))
            self.assertEqual(b["dimming"]["saved"], 15)

    def test_clock_message_and_resumed_animation_select_their_own_brightness(self):
        show = clocks.plain_show_of([dict(id=1, file="long.odrg")], {"long.odrg": clocks.loop_of(45, 3)}, min_seconds=4)
        initial = json.loads(show["show.json"])["brightness"]
        for saved in (True, False):
            lines = [*(f"22 x {name}" for name in sorted(clocks.CLOCK_FILES)), f"33 x {clocks.MESSAGE}"]
            if saved:
                lines.append("11 f long.odrg")
            source = preferences(clocks.with_clocks(show), *lines)
            script = asked(1000, "repeat 1 9") + clocks.at_times(299000, 301000)
            script += asked(302000, "brightness 5") + clocks.at_times(306500, 308000)
            states = clocks.states_of(clocks.on_card(source, clocks.CLOCKS, script))
            self.assertEqual([state["dimming"]["value"] for state in states], [11 if saved else initial, 22, 33, 11 if saved else 5])
            self.assertEqual((states[0]["loop"], states[0]["repeat"]), (states[-1]["loop"], states[-1]["repeat"]))

    def test_restored_path_keeps_its_preference_and_a_renamed_file_does_not(self):
        source = preferences(files(), "19 f picture.odrg")
        data = source["picture.odrg"]
        script = Script().polls(1).line("remove 1").polls(2).upload(7, "picture.odrg", data).polls(2).line("play 7").polls(1).line("status")
        script.upload(7, "renamed.odrg", data).polls(2).line("play 7").polls(1).line("status")
        run, kept = support.start_and_keep(source, script.lines)
        states = [reply for reply in replies(run) if "dimming" in reply]
        self.assertEqual([state["dimming"]["saved"] for state in states], [19, None])
        self.assertEqual(kept["brightness.txt"], source["brightness.txt"].encode())


class ExternalBrightness(unittest.TestCase):
    def test_namespaces_and_duplicate_basenames_in_folders_remain_distinct(self):
        source = files()
        data = source.pop("picture.odrg")
        source["same.odrg"] = data
        show = json.loads(source["show.json"])
        show["items"][0]["file"] = "same.odrg"
        source["show.json"] = json.dumps(show)
        source = preferences(source, "10 f same.odrg", "20 x same.odrg", "30 x x/same.odrg", "40 x y/same.odrg")
        script = asked(0, "status")
        for n, identity in enumerate((60001, 60002, 60003), 1):
            script += asked(n * 40, f"play {identity}") + asked(n * 40 + 20, "status")
        run = with_drive(source, {"same.odrg": data, "x/same.odrg": data, "y/same.odrg": data}, script)
        states = [reply for reply in replies(run) if "dimming" in reply]
        self.assertEqual([state["dimming"]["saved"] for state in states], [10, 20, 30, 40])

    def test_read_only_drive_saves_in_internal_storage_and_survives_restart(self):
        with a_drive(DRIVE) as top:
            original = support.folder_files(pathlib.Path(top, "odrig"))
            run, kept = support.start_and_keep(SHOW, asked(0, "play 60001") + asked(20, "brightness 60001 11 save", "status"),
                                               ["--drive", top])
            self.assertEqual(replies(run)[1], dict(ok=True))
            self.assertEqual(replies(run)[-1]["dimming"]["saved"], 11)
            self.assertEqual(kept["brightness.txt"], b"odrig-brightness 1\n11 x A.ODRG\n")
            again = support.start(kept, asked(0, "play 60001") + asked(20, "status"), ["--drive", top])
            self.assertEqual(replies(again)[-1]["dimming"]["value"], 11)
            show = json.loads(kept["show.json"])
            show["items"][0]["id"] = 60001
            if show.get("start") == 1:
                show["start"] = 60001
            reassigned = {**kept, "show.json": json.dumps(show)}
            moved = support.start(reassigned, asked(0, "play 60002") + asked(20, "status"), ["--drive", top])
            self.assertEqual(replies(moved)[-1]["dimming"]["saved"], 11)
            self.assertEqual(support.folder_files(pathlib.Path(top, "odrig")), original)

    def test_retained_absent_card_paths_count_toward_capacity(self):
        source = preferences(SHOW, *(f"1 x absent-{n}.odrg" for n in range(32)))
        with a_drive(DRIVE) as top:
            run, kept = support.start_and_keep(source, asked(0, "brightness 60001 11 save"), ["--drive", top])
        self.assertEqual(replies(run), [dict(ok=False, error="no-space")])
        self.assertEqual(kept["brightness.txt"], source["brightness.txt"].encode())

    def test_pull_and_remount_restore_the_path_preference(self):
        source = preferences(SHOW, "11 x A.ODRG")
        script = asked(0, "play 60001") + asked(20, "status") + ["drive pull"] + asked(40, "status") + ["drive plug"]
        script += [f"poll {1040 + 20 * n}" for n in range(1, 40)] + asked(1000, "play 60001") + asked(1020, "status")
        run = with_drive(source, DRIVE, script)
        states = [reply for reply in replies(run) if "dimming" in reply]
        self.assertEqual([state["dimming"]["saved"] for state in states], [11, None, 11])


class BrightnessPowerCuts(unittest.TestCase):
    def test_failed_storage_calls_preserve_published_settings_and_runtime_value(self):
        source = preferences(files(), "30 f picture.odrg", "7 f absent.odrg")
        for command in ("brightness 1 15 save", "brightness 1 default"):
            script = ["poll 0", support.line(0, command), support.line(0, "status")]
            observed = support.start(source, script, ["--trace-store"])
            first = len(observed.stored) + 1
            calls = sum(line.startswith("store ") for line in observed.lines)
            for at in range(first, first + calls):
                with self.subTest(command=command, at=at):
                    run, kept = support.start_and_keep(source, script, ["--store-fails-at", str(at)])
                    self.assertEqual(replies(run)[0], dict(ok=False, error="storage-error"))
                    self.assertEqual(replies(run)[-1]["dimming"]["saved"], 30)
                    self.assertEqual(kept["brightness.txt"], source["brightness.txt"].encode())
                    self.assertNotIn("brightness.part", kept)

    def test_read_and_part_verification_failures_do_not_publish_a_phantom_save(self):
        source = preferences(files(), "30 f picture.odrg", "7 f absent.odrg")
        for name, offset in (("brightness.txt", "0"), ("brightness.txt", "20"), ("brightness.part", "0")):
            run, kept = support.start_and_keep(source, ["poll 0", support.line(0, "brightness 1 15 save"), support.line(0, "status")],
                                               ["--command-read-fails", name, offset])
            self.assertEqual(replies(run)[0], dict(ok=False, error="storage-error"))
            self.assertEqual(replies(run)[1]["dimming"]["saved"], 30)
            self.assertEqual(kept["brightness.txt"], source["brightness.txt"].encode())
            self.assertNotIn("brightness.part", kept)

    def test_every_save_or_remove_storage_cut_leaves_old_or_new_settings(self):
        source = preferences(files(), "30 f picture.odrg", "7 f absent.odrg")
        old = source["brightness.txt"].encode()
        for command, expected in (("brightness 1 15 save", b"odrig-brightness 1\n15 f picture.odrg\n7 f absent.odrg\n"),
                                  ("brightness 1 default", b"odrig-brightness 1\n7 f absent.odrg\n")):
            script = ["poll 0", support.line(0, command)]
            observed, whole = support.start_and_keep(source, script, ["--trace-store"])
            self.assertEqual(whole["brightness.txt"], expected)
            first = len(observed.stored) + 1
            calls = sum(line.startswith("store ") for line in observed.lines)
            self.assertEqual(calls, 4)
            for at in range(first, first + calls):
                for keeps in (0, 1):
                    with self.subTest(command=command, at=at, keeps=keeps):
                        _, left = support.start_and_keep(source, script, ["--cut-at", str(at), "--cut-keeps", str(keeps)], status=75)
                        recovered, settled = support.start_and_keep(left, ["poll 0", support.line(0, "status")])
                        self.assertIn(settled["brightness.txt"], (old, expected))
                        value = 30 if settled["brightness.txt"] == old else (15 if "save" in command else None)
                        self.assertEqual(replies(recovered)[0]["dimming"]["saved"], value)


if __name__ == "__main__":
    unittest.main()

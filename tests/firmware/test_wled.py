import pathlib
import tempfile
import unittest
from unittest import mock

from fwtool import wled

from . import support


class TemporaryFolder(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = pathlib.Path(holder.name).resolve()


class Pinned(unittest.TestCase):
    def test_the_tag_and_the_commit_are_those_of_wled_16_0_1(self):
        self.assertEqual(wled.URL, "https://github.com/wled/WLED.git")
        self.assertEqual(wled.TAG, "v16.0.1")
        self.assertEqual(wled.COMMIT, "29b389df1c1aaec6ff53aea742d17063b985906c")


class CommitCheck(TemporaryFolder):
    def test_a_checkout_at_the_pinned_commit_passes(self):
        commit = support.repository(self.folder / "wled", {"a.txt": "one\n"})
        wled.check(self.folder / "wled", commit)

    def test_a_checkout_at_another_commit_is_a_mismatch(self):
        first = support.repository(self.folder / "wled", {"a.txt": "one\n"})
        (self.folder / "wled" / "a.txt").write_text("two\n")
        support.git(self.folder / "wled", "commit", "--quiet", "-am", "second")
        with self.assertRaises(wled.Failure) as caught:
            wled.check(self.folder / "wled", first)
        self.assertEqual(caught.exception.reason, "wled-mismatch")
        self.assertIn(first, caught.exception.detail)
        self.assertEqual(support.reason_of(self, lambda: wled.check(self.folder / "wled", wled.COMMIT)), "wled-mismatch")

    def test_a_folder_that_is_no_checkout_is_a_mismatch(self):
        (self.folder / "plain").mkdir()
        self.assertEqual(support.reason_of(self, lambda: wled.check(self.folder / "plain", wled.COMMIT)), "wled-mismatch")
        self.assertEqual(support.reason_of(self, lambda: wled.check(self.folder / "absent", wled.COMMIT)), "wled-mismatch")

    def test_a_folder_inside_another_checkout_is_a_mismatch(self):
        commit = support.repository(self.folder / "outer", {"a.txt": "one\n"})
        (self.folder / "outer" / "inner").mkdir()
        self.assertEqual(support.reason_of(self, lambda: wled.check(self.folder / "outer" / "inner", commit)), "wled-mismatch")


class Fetch(TemporaryFolder):
    def test_a_folder_that_is_there_is_not_fetched_again(self):
        (self.folder / "wled").mkdir()
        with mock.patch.object(wled.subprocess, "run", side_effect=AssertionError("ran git")):
            self.assertFalse(wled.fetch(self.folder / "wled"))

    def test_a_missing_folder_is_cloned_at_the_tag(self):
        commit = support.repository(self.folder / "origin", {"a.txt": "one\n"})
        support.git(self.folder / "origin", "tag", "v1")
        (self.folder / "origin" / "a.txt").write_text("later\n")
        support.git(self.folder / "origin", "commit", "--quiet", "-am", "after the tag")
        self.assertTrue(wled.fetch(self.folder / "work" / "wled", url=(self.folder / "origin").as_uri(), tag="v1"))
        wled.check(self.folder / "work" / "wled", commit)

    def test_a_clone_that_fails_is_a_failed_setup(self):
        action = lambda: wled.fetch(self.folder / "wled", url=(self.folder / "nowhere").as_uri(), tag="v1")
        self.assertEqual(support.reason_of(self, action), "setup-failed")


class Patches(TemporaryFolder):
    def setUp(self):
        super().setUp()
        self.checkout = self.folder / "wled"
        self.patches = self.folder / "patches"
        self.patches.mkdir()
        self.commit = support.repository(self.checkout, {"a.txt": "one\n", "b.txt": "left alone\n"})

    def change_as_patch(self, change):
        """The text of the patch that makes a change. The change is taken back."""
        change()
        support.git(self.checkout, "add", "-A")
        text = support.git(self.checkout, "diff", "--cached") + "\n"
        support.git(self.checkout, "reset", "--quiet", "--hard")
        return text

    def patch(self, name, change):
        (self.patches / name).write_text(self.change_as_patch(change))

    def apply(self):
        return wled.restore_and_patch(self.checkout, self.patches, self.commit)

    def test_no_patch_leaves_the_pinned_files(self):
        self.assertEqual(self.apply(), [])
        self.assertEqual((self.checkout / "a.txt").read_text(), "one\n")

    def test_patches_are_applied_in_the_order_of_their_names(self):
        to_two = self.change_as_patch(lambda: (self.checkout / "a.txt").write_text("two\n"))
        (self.checkout / "a.txt").write_text("two\n")
        support.git(self.checkout, "commit", "--quiet", "-am", "moved on")
        to_three = self.change_as_patch(lambda: (self.checkout / "a.txt").write_text("three\n"))
        support.git(self.checkout, "reset", "--quiet", "--hard", self.commit)
        (self.patches / "100-to-three.patch").write_text(to_three)
        (self.patches / "020-to-two.patch").write_text(to_two)
        self.assertEqual([path.name for path in wled.patch_files(self.patches)], ["020-to-two.patch", "100-to-three.patch"])
        self.assertEqual(self.apply(), ["020-to-two.patch", "100-to-three.patch"])
        self.assertEqual((self.checkout / "a.txt").read_text(), "three\n")

    def test_only_patch_files_are_applied(self):
        (self.patches / "README.md").write_text("not a patch\n")
        self.assertEqual(self.apply(), [])

    def test_changed_files_are_brought_back_before_the_patches(self):
        self.patch("010-a.patch", lambda: (self.checkout / "a.txt").write_text("two\n"))
        (self.checkout / "b.txt").write_text("edited by hand\n")
        for _ in range(2):
            self.assertEqual(self.apply(), ["010-a.patch"])
            self.assertEqual((self.checkout / "a.txt").read_text(), "two\n")
            self.assertEqual((self.checkout / "b.txt").read_text(), "left alone\n")

    def test_a_patch_that_adds_a_file_can_be_applied_again(self):
        self.patch("010-new.patch", lambda: (self.checkout / "new.txt").write_text("new\n"))
        for _ in range(2):
            self.assertEqual(self.apply(), ["010-new.patch"])
            self.assertEqual((self.checkout / "new.txt").read_text(), "new\n")

    def test_ignored_files_stay_where_they_are(self):
        (self.checkout / ".gitignore").write_text("kept/\n")
        support.git(self.checkout, "add", ".gitignore")
        support.git(self.checkout, "commit", "--quiet", "-m", "ignore")
        self.commit = support.git(self.checkout, "rev-parse", "HEAD")
        (self.checkout / "kept").mkdir()
        (self.checkout / "kept" / "built.o").write_text("built\n")
        self.apply()
        self.assertEqual((self.checkout / "kept" / "built.o").read_text(), "built\n")

    def test_a_patch_that_does_not_apply_stops_with_patch_failed(self):
        (self.patches / "010-bad.patch").write_text("--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-something else\n+two\n")
        with self.assertRaises(wled.Failure) as caught:
            self.apply()
        self.assertEqual(caught.exception.reason, "patch-failed")
        self.assertIn("010-bad.patch", caught.exception.detail)

    def test_a_checkout_at_another_commit_is_not_patched(self):
        self.assertEqual(support.reason_of(self, lambda: wled.restore_and_patch(self.checkout, self.patches, wled.COMMIT)), "wled-mismatch")

    def test_the_patch_files_of_the_repository_are_found_beside_their_readme(self):
        self.assertEqual([path.suffix for path in wled.patch_files()], [".patch"] * len(wled.patch_files()))
        self.assertEqual([path.name for path in wled.patch_files()], sorted(path.name for path in wled.patch_files()))
        self.assertTrue((wled.paths.PATCHES / "README.md").is_file())


class Override(TemporaryFolder):
    def test_it_is_the_template_with_the_repository_path_in_place_of_the_marker(self):
        template = wled.TEMPLATE.read_text()
        self.assertEqual(wled.TEMPLATE, support.FIRMWARE / "platformio_override.ini.in")
        self.assertIn("@REPO@", template)
        text = wled.override_text()
        self.assertEqual(text, template.replace("@REPO@", str(support.ROOT)))
        self.assertNotIn("@REPO@", text)

    def test_it_names_the_usermod_as_a_library_outside_wleds_folder(self):
        text = wled.override_text()
        self.assertIn(f"  odrig = symlink://{support.ROOT}/firmware/usermod\n", text)
        self.assertRegex(text, r"(?m)^custom_usermods =\n  odrig = symlink://")

    def test_it_switches_wleds_serial_handling_off_and_leaves_the_audio_usermod_out(self):
        text = wled.override_text()
        self.assertRegex(text, r"(?m)^  -D WLED_DISABLE_ADALIGHT$")
        self.assertNotIn("audioreactive", text)

    def test_it_has_the_two_environments_on_wleds_own(self):
        text = wled.override_text()
        self.assertRegex(text, r"(?m)^\[env:odrig\]\nextends = env:esp32s3dev_16MB_opi$")
        self.assertRegex(text, r"(?m)^\[env:odrig_probe\]\nextends = env:odrig$")
        self.assertRegex(text, r"(?m)^  -D ODRIG_PROBE$")
        self.assertIn('-D WLED_RELEASE_NAME=\\"odrig_ESP32-S3_16MB_opi\\"', text)
        for setting in ("board", "platform", "board_build.partitions", "board_build.flash_mode", "board_upload.flash_size"):
            self.assertNotRegex(text, rf"(?m)^{setting}\s*=", setting)

    def test_a_repository_path_with_a_space_is_refused(self):
        spaced = self.folder / "my odrig"
        spaced.mkdir()
        self.assertEqual(support.reason_of(self, lambda: wled.override_text(root=spaced)), "build-failed")

    def test_the_file_is_written_into_wleds_folder_and_left_alone_when_it_is_right(self):
        path = wled.write_override(self.folder)
        self.assertEqual(path, self.folder / "platformio_override.ini")
        self.assertEqual(path.read_text(), wled.override_text())
        before = path.stat().st_mtime_ns
        wled.write_override(self.folder)
        self.assertEqual(path.stat().st_mtime_ns, before)
        path.write_text("something else\n")
        wled.write_override(self.folder)
        self.assertEqual(path.read_text(), wled.override_text())

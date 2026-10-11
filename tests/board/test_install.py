import json
import pathlib
import shutil
import tempfile
import unittest

from odrig import jsonframes, odrg
from odrig.generators import dvd_bounce

from fwtool import paths, storage

from . import PORT, support

WLED_FILES = ("/cfg.json", "/presets.json")


def one_animation(folder, name):
    """A show file with one item, the animation of that name, written into a folder."""
    show = pathlib.Path(folder, "show.json")
    show.write_text(json.dumps({"version": 1, "brightness": support.DIM, "items": [{"id": 1, "file": name}], "start": 1}))
    return show


def missing_animation(folder):
    (folder / "dvd.odrg").unlink()


def damaged_animation(folder):
    whole = (folder / "dvd.odrg").read_bytes()
    (folder / "dvd.odrg").write_bytes(whole[:len(whole) // 2])


def animation_of_another_canvas_size(folder):
    (folder / "dvd.odrg").write_bytes(odrg.encode(jsonframes.Animation(60, 3, tuple(dvd_bounce.frames(60, 3)))))


def no_show_file(folder):
    (folder / "show.json").unlink()


INVALID = {
    "a missing animation": (missing_animation, "file-missing dvd.odrg"),
    "a damaged animation": (damaged_animation, "file-malformed dvd.odrg truncated"),
    "an animation of another canvas size": (animation_of_another_canvas_size, "size-mismatch dvd.odrg"),
    "no show.json": (no_show_file, "show-missing"),
}


class Install(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("firmware")

    def test_the_dim_example_show_is_installed_plays_and_is_read_back_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as work, support.dim_show(show=one_animation(work, "hello.odrg")) as other:
            support.ensure_installed(other)
        before = support.storage_image()
        with support.dim_show() as folder, tempfile.TemporaryDirectory() as out:
            done = support.install(folder)
            self.assertEqual(done.status, 0, done.err)
            reply = json.loads(done.out)
            self.assertEqual((reply["ok"], reply["error"], reply["playing"], reply["brightness"]), (True, None, 3, support.DIM))
            self.assertEqual(done.out.count("\n"), 1)
            read = support.on_port("read-show", pathlib.Path(out, "copy"))
            self.assertEqual(read.status, 0, read.err)
            self.assertEqual(support.files_of(pathlib.Path(out, "copy")), support.files_of(folder))
            self.assertEqual(sorted(support.files_of(folder)), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])
        after = support.storage_image()
        kept = [path.read_bytes() for path in storage.kept_images(len(before))]
        self.assertEqual(kept[0], after, "the board changed its storage after the tool wrote it")
        self.assertIn(before, kept, "no copy of storage from before the install is in the work folder")
        old, new = storage.other_files(before), storage.other_files(after)
        for name in WLED_FILES:
            self.assertIn(name, old)
            self.assertEqual(new[name], old[name], name)
        self.assertEqual(new, old)
        self.assertTrue(paths.inside(storage.kept_images(len(before))[0], paths.STORAGE))
        status, reply = support.command(PORT, "status")
        self.assertEqual((status, reply["error"], reply["playing"]), (0, None, 3))

    def test_a_second_install_of_another_show_leaves_no_file_of_the_first(self):
        with support.dim_show() as first, tempfile.TemporaryDirectory() as work:
            support.ensure_installed(first)
            self.assertIn("dvd.odrg", support.installed())
            with support.dim_show(show=one_animation(work, "hello.odrg")) as second:
                done = support.install(second)
                self.assertEqual(done.status, 0, done.err)
                self.assertEqual(json.loads(done.out)["playing"], 1)
                self.assertEqual(support.installed(), support.files_of(second))
                self.assertEqual(sorted(support.installed()), ["hello.odrg", "mapping.json", "show.json"])

    def test_an_invalid_show_has_the_reason_the_emulator_gives_and_plays_nothing(self):
        for what, (damage, expected) in INVALID.items():
            with self.subTest(what), support.dim_show() as packed, tempfile.TemporaryDirectory() as work:
                folder = pathlib.Path(work, "show")
                shutil.copytree(packed, folder)
                damage(folder)
                reason = support.reason_in_the_emulator(folder)
                self.assertEqual(reason, expected)
                done = support.install(folder, "--no-check")
                self.assertEqual(done.status, 1, done.err)
                self.assertEqual(done.err, "")
                self.assertEqual(json.loads(done.out)["error"], reason)
                self.assertEqual(support.command(PORT, "status")[1]["error"], reason)
                self.assertEqual(support.command(PORT, "play", "1"), (1, {"ok": False, "error": "show-invalid"}))
                self.assertEqual(support.command(PORT, "status")[1]["playing"], None)

    def test_an_invalid_show_is_refused_without_no_check_before_the_board_is_touched(self):
        with support.dim_show() as packed, tempfile.TemporaryDirectory() as work:
            folder = pathlib.Path(work, "show")
            shutil.copytree(packed, folder)
            missing_animation(folder)
            done = support.install(folder)
        self.assertEqual(done.status, 1)
        self.assertRegex(done.err, r"^error: file-missing: ")

    def test_a_show_brighter_than_the_wired_strip_allows_is_not_installed(self):
        with support.dim_show(brightness=41) as folder:
            with self.assertRaises(AssertionError):
                support.install(folder)
        with support.dim_show(brightness=40) as folder:
            self.assertEqual(support.brightness_of(folder), 40)

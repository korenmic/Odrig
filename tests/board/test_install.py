import json
import pathlib
import tempfile
import unittest

from fwtool import paths, storage

from . import support

WLED_FILES = ("/cfg.json", "/presets.json")


def one_animation(folder, name):
    """A show file with one item, the animation of that name, written into a folder."""
    show = pathlib.Path(folder, "show.json")
    show.write_text(json.dumps({"version": 1, "brightness": support.DIM, "items": [{"id": 1, "file": name}], "start": 1}))
    return show


class Install(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("probe")

    def installed_without_a_reply(self, folder):
        """Installs a folder on a build that answers no `status`: every check of the tool
        passes and then no reply comes."""
        done = support.install(folder)
        self.assertEqual(done.status, 1)
        self.assertRegex(done.err, r"^error: no-reply: no reply to status within 20 seconds")
        return done

    def test_the_dim_example_show_is_installed_and_read_back_byte_for_byte(self):
        before = support.storage_image()
        with support.dim_show() as folder, tempfile.TemporaryDirectory() as out:
            self.installed_without_a_reply(folder)
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

    def test_a_second_install_of_another_show_leaves_no_file_of_the_first(self):
        with support.dim_show() as first, tempfile.TemporaryDirectory() as work:
            self.installed_without_a_reply(first)
            self.assertIn("dvd.odrg", support.installed())
            with support.dim_show(show=one_animation(work, "hello.odrg")) as second:
                self.installed_without_a_reply(second)
                self.assertEqual(support.installed(), support.files_of(second))
                self.assertEqual(sorted(support.installed()), ["hello.odrg", "mapping.json", "show.json"])

    def test_a_show_brighter_than_the_wired_strip_allows_is_not_installed(self):
        with support.dim_show(brightness=41) as folder:
            with self.assertRaises(AssertionError):
                support.install(folder)
        with support.dim_show(brightness=40) as folder:
            self.assertEqual(support.brightness_of(folder), 40)

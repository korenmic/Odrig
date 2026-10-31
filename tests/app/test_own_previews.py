"""The previews this phone makes of what it uploads: an animation from Upload and a text from
its form get their previews in their rows, kept in IndexedDB across a reload; the default
catalog's key wins and the phone's copy of it is dropped at the start; a preview that cannot
be made keeps nothing and says nothing; and a web view without IndexedDB keeps the preview for
the run alone. In Chrome against the emulator."""

import json
import pathlib
import tempfile
import unittest
import zlib

from odrig import catalog
from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

MAPPING = (support.ROOT / "mapping" / "legs-20.json").read_text(encoding="utf-8")


def a_default_key():
    text = (support.THUMBNAILS / "catalog.js").read_text(encoding="ascii")
    return next(line.split('"')[1] for line in text.splitlines() if line.startswith('  "'))


class OwnPreviews(unittest.TestCase):
    def setUp(self):
        work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        items = [{"id": 1, "file": "one.odrg"}, {"id": 2, "file": "two.odrg"}]
        files = {"one.odrg": core_support.clip(1, 60, 60, (40, 40)), "two.odrg": core_support.clip(2, 60, 60, (40, 40))}
        self.show = emulator_support.installed(work / "show", {"mapping.json": MAPPING, "show.json": json.dumps({"version": 1, "brightness": 128, "items": items}), **files})
        made, refused = catalog.rebuild(catalog.Storage(self.show), names=["one.odrg", "two.odrg"], canvas=(60, 60))
        self.assertEqual(refused, [])
        self.media = work / "media"
        self.media.mkdir()
        support.make_media(self.media)
        self.emulator = entered(self, emulator_support.Emulator(self.show))
        self.address = f"127.0.0.1:{self.emulator.port}"

    def key_of(self, name):
        data = (self.show / name).read_bytes()
        return f"{zlib.crc32(data):08x}-{len(data)}"

    def test_a_generated_message_clock_becomes_a_decodable_browser_preview(self):
        from tests.core.test_message_clock import message_file
        data = message_file([('hello', 0), ('still', 4)])
        key = f"{zlib.crc32(data):08x}-{len(data)}"
        seen = support.run('ownpreviews', address=self.address,
                           settings={'mode': 'generated', 'bytes': list(data), 'key': key}).seen
        self.assertEqual(seen['size'], [60, 60])
        self.assertEqual(seen['signature'], list(b'GIF89a'))
        self.assertIsNone(seen['message'])

    def test_an_uploaded_animation_gets_its_preview_kept_across_a_reload(self):
        seen = support.run("ownpreviews", address=self.address, settings={"file": "clip.gif", "name": "clip.odrg"}, media=self.media).seen
        self.assertRegex(seen["message"], r"\AUploaded as animation 3 clip\.odrg\.")
        self.assertEqual((seen["uploaded"]["loaded"], seen["reloaded"]["loaded"]), (True, True))
        self.assertEqual(seen["stored"], [self.key_of("clip.odrg")])

    def test_a_text_saved_from_its_form_gets_its_preview(self):
        seen = support.run("ownpreviews", address=self.address, settings={"text": "Hi", "name": "hi.odrgx"}).seen
        self.assertRegex(seen["message"], r"\AUploaded as animation 3 hi\.odrgx\.")
        self.assertTrue(seen["uploaded"]["loaded"] and seen["reloaded"]["loaded"])
        self.assertEqual(seen["stored"], [self.key_of("hi.odrgx")])

    def test_the_default_catalog_wins_and_its_key_is_dropped_from_the_phone_at_the_start(self):
        key = a_default_key()
        seen = support.run("ownpreviews", address=self.address, settings={"mode": "start", "defaultKey": key}).seen
        self.assertEqual(seen["stored"], ["0badcafe-12"])
        self.assertEqual(seen["defaultSource"], f"thumbnails/{key}.gif")
        self.assertTrue(seen["ownSource"].startswith("blob:"))

    def test_a_preview_that_cannot_be_made_keeps_nothing_and_says_nothing(self):
        data = bytes([79, 68, 82, 71, 9, 9, 9])
        seen = support.run("ownpreviews", address=self.address, settings={"mode": "refused", "refusedKey": f"{zlib.crc32(data):08x}-{len(data)}"}).seen
        self.assertEqual((seen["source"], seen["stored"], seen["message"]), (None, [], None))

    def test_a_start_that_a_later_one_overtakes_leaves_the_database_it_opens(self):
        seen = support.run("ownpreviews", address=self.address, settings={"mode": "overtaken"}).seen
        self.assertNotIn("overtaken internal", seen["kept"])

    def test_without_indexeddb_the_preview_is_kept_for_the_run_alone(self):
        seen = support.run("ownpreviews", address=self.address, settings={"mode": "no-database", "file": "clip.gif", "name": "clip.odrg"}, media=self.media).seen
        self.assertTrue(seen["uploaded"]["loaded"])
        self.assertEqual(seen["stored"], [])
        self.assertTrue(seen["reloaded"]["row"])
        self.assertIsNone(seen["reloaded"]["src"])


if __name__ == "__main__":
    unittest.main()

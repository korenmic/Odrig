"""The previews this phone makes of what it uploads: made as the upload starts, written and
placed on success, found by the place on a storage without a catalog, kept across a reload,
and dropped when the file leaves its list."""

import json
import pathlib
import tempfile
import time
import unittest



from tests.core import support as core_support
from tests.emulator import support as emulator_support
from . import support
from .test_target import entered


def key(data):
    import zlib

    return f"{zlib.crc32(data):08x}-{len(data)}"


class PhonePreviews(unittest.TestCase):
    def setUp(self):
        # A show packed by the converter, which has no catalog.
        self.show = entered(self, emulator_support.example_show())
        self.media = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        # A compressed file whose key the default catalog does not hold.
        self.data = core_support.clip(41, 60, 6, (20,) * 40, compressed=True)
        self.assertTrue(self.data[5] & 1, "the file is compressed")
        (self.media / "fresh.odrg").write_bytes(self.data)

    def run_on(self, address, **settings):
        return support.run("phone-previews", address=address, media=self.media, settings={"rows": 2, "file": "fresh.odrg", **settings}).seen

    def test_a_compressed_ready_made_upload_shows_its_preview_without_a_catalog_and_after_a_reload(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        with emulator_support.EventStream(emulator.port) as stream:
            found = self.run_on(f"127.0.0.1:{emulator.port}", reload=True)
            lines = [entry["line"] for entry in emulator_support.of_kind(stream.read_for(1), "log")]
        self.assertEqual(found["note"], "Preview made on this phone. The original animation bytes are kept.")
        self.assertEqual(found["message"], "Uploaded as animation 4 fresh.odrg. It plays in the playlist.")
        self.assertTrue(found["square"] is not None and found["square"].startswith("blob:"), found["square"])
        self.assertTrue(found["afterReload"] is not None and found["afterReload"].startswith("blob:"), found["afterReload"])
        self.assertEqual(found["stored"]["version"], 3)
        self.assertEqual(found["stored"]["stores"], ["keys", "previews", "uploads"])
        self.assertIn(key(self.data), found["stored"]["previews"])
        self.assertEqual(found["stored"]["uploads"], {"internal": [["fresh.odrg", key(self.data)]]})
        self.assertFalse(any(line.startswith("catalog page") for line in lines), lines)

    def test_a_target_that_refuses_catalog_pages_shows_the_preview_by_its_place(self):
        emulator = entered(self, emulator_support.Emulator(self.show))

        def answer(line):
            if line.startswith(b"catalog"):
                return 200, '{"ok":false,"error":"unknown-command"}\n'
            return 200, emulator.command(line.decode("utf-8")).decode("utf-8")

        stand_in = entered(self, support.StandIn(answer))
        found = self.run_on(stand_in.address)
        self.assertTrue(found["square"] is not None and found["square"].startswith("blob:"), found["square"])

    def test_a_refused_upload_keeps_no_place_and_writes_nothing(self):
        emulator = entered(self, emulator_support.Emulator(self.show, "--storage", 20000))
        found = self.run_on(f"127.0.0.1:{emulator.port}")
        self.assertIn("(no-space)", found["message"])
        self.assertNotIn(key(self.data), found["stored"]["previews"])
        self.assertEqual(found["stored"]["uploads"], {})

    def test_a_complete_list_without_the_file_drops_its_place(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        found = support.run("phone-previews", address=f"127.0.0.1:{emulator.port}", media=self.media,
                            settings={"rows": 2, "file": "fresh.odrg", "removedElsewhere": True}, steps=[lambda: emulator.command("remove 4")]).seen
        self.assertEqual(found["stored"]["uploads"], {"internal": [["fresh.odrg", key(self.data)]]})
        self.assertEqual(found["afterRemoval"], {})

    def test_a_row_of_another_size_takes_no_kept_place(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        other = core_support.clip(42, 60, 6, (20,) * 10, compressed=True)

        def replaced():
            for line in core_support.upload_lines(4, "fresh.odrg", other):
                emulator.command(line)
            for _ in range(200):
                if json.loads(emulator.command(core_support.upload_end(other))) != {"ok": False, "error": "busy"}:
                    break
                time.sleep(0.05)

        found = support.run("phone-previews", address=f"127.0.0.1:{emulator.port}", media=self.media,
                            settings={"rows": 2, "file": "fresh.odrg", "resized": True}, steps=[replaced]).seen
        self.assertTrue(found["square"].startswith("blob:"))
        self.assertIsNone(found["afterResize"])

    def test_an_older_database_goes_to_version_3_with_its_records(self):
        emulator = entered(self, emulator_support.Emulator(self.show))
        for version in (1, 2):
            with self.subTest(version=version):
                found = support.run("phone-previews", address=f"127.0.0.1:{emulator.port}", settings={"rows": 2, "older": version}).seen
                self.assertEqual(found["version"], 3)
                self.assertEqual(found["stores"], ["keys", "previews", "uploads"])
                self.assertEqual(found["previews"], ["00000000-1"])
                self.assertEqual(found["keys"], ["127.0.0.1:1 internal"] if version == 2 else [])


if __name__ == "__main__":
    unittest.main()

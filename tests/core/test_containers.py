import json
import re
import unittest

from odrig import jsonframes, odrg, odrgx

from . import support
from .test_content import OK
from .test_drive import asked, listed, logged, pictures, replies, with_drive
from .test_playlist import CANVAS, loop_of, show_of
from .test_upload import Script, Uploads, bad_file
from .test_content import animation, small_show

VECTORS = support.ROOT / "tests" / "vectors" / "containers"


def wrapped(data):
    """A container of the frames of an ODRG file."""
    decoded = odrg.decode(data)
    return odrgx.wrap(1, decoded.width, decoded.height, sum(duration for duration, _ in decoded.records), data)


def reasons_of_a_container():
    text = (support.ROOT / "docs" / "reasons.md").read_text(encoding="utf-8")
    section = text.split("\n## ODRGX files\n")[1].split("\n## ")[0]
    return set(re.findall(r"(?m)^\| `([a-z0-9-]+)` \|", section))


def seconds_of_polls(seconds):
    """Refreshes every 20 ms for this many seconds after power-on."""
    return [f"poll {1000 + time}" for time in range(0, seconds * 1000, 20)]


class TheVectors(unittest.TestCase):
    def test_a_valid_container_of_frames_gives_the_frames_of_its_odrg_file(self):
        paths = sorted((VECTORS / "valid").glob("*.odrgx"))
        for path, decoded in zip(paths, support.decode_each([path.read_bytes() for path in paths])):
            with self.subTest(vector=path.name):
                expected = jsonframes.loads(path.with_suffix(".json").read_bytes())
                self.assertIsNone(decoded.reason)
                self.assertEqual(decoded.container, (1, sum(ms for ms, _ in expected.frames), len(path.read_bytes()) - 20))
                self.assertEqual(list(decoded.records), [tuple(frame) for frame in expected.frames])

    def test_an_invalid_container_is_refused_with_the_reason_of_its_name(self):
        paths = sorted((VECTORS / "invalid").iterdir())
        self.assertGreaterEqual(len(paths), 12)
        for path, decoded in zip(paths, support.decode_each([path.read_bytes() for path in paths])):
            with self.subTest(vector=path.name):
                self.assertEqual(decoded.reason, path.name.split(".")[0])

    def test_the_core_has_every_reason_of_a_container(self):
        self.assertIn("loop-mismatch", reasons_of_a_container())
        self.assertLessEqual(reasons_of_a_container(), set(support.host_lines("reasons")))

    def test_an_odrg_file_is_read_as_before(self):
        data = (support.ROOT / "tests" / "vectors" / "valid" / "durations.odrg").read_bytes()
        decoded = support.decode_each([data])[0]
        self.assertIsNone(decoded.container)
        self.assertIsNone(decoded.reason)


class ShowsOfContainers(unittest.TestCase):
    def play(self, files, seconds=12, check_first=True):
        return pictures(support.start(files, seconds_of_polls(seconds), check_first=check_first))

    def test_a_container_of_frames_plays_the_pictures_of_its_odrg_file_at_the_same_times(self):
        clip = loop_of(3, 4)
        for check_first in (True, False):
            with self.subTest(check_first=check_first):
                plain = self.play(show_of([{"id": 1, "file": "a.odrg"}], {"a.odrg": clip}), check_first=check_first)
                boxed = self.play(show_of([{"id": 1, "file": "a.odrgx"}], {"a.odrgx": wrapped(clip)}), check_first=check_first)
                self.assertEqual(len(boxed), 600)
                self.assertEqual(boxed, plain)

    def test_a_show_of_both_kinds_plays_its_playlist_in_turn(self):
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrgx"}], {"a.odrg": loop_of(2, 5), "b.odrgx": wrapped(loop_of(3, 6))}, min_seconds=3)
        same = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}], {"a.odrg": loop_of(2, 5), "b.odrg": loop_of(3, 6)}, min_seconds=3)
        self.assertEqual(self.play(files, 14), self.play(same, 14))

    def test_list_gives_the_type_of_every_animation(self):
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrgx"}, {"id": 3, "cycle": [1, 2], "seconds": 5}], {"a.odrg": loop_of(2, 5), "b.odrgx": wrapped(loop_of(3, 6))})
        items = json.loads(support.start(files, asked(0, "list")).lines[-1][len("reply "):])["items"]
        self.assertEqual([item.get("type") for item in items], ["frames", "frames", None])
        self.assertEqual(items[1], {"id": 2, "file": "b.odrgx", "bytes": len(files["b.odrgx"]), "ignored": False, "external": False, "type": "frames"})

    def test_a_container_with_a_fault_in_its_header_or_its_payload_is_quarantined(self):
        good = wrapped(loop_of(2, 7))
        cases = {
            "unknown-type": bytes(good[:5]) + b"\x09" + bytes(good[6:]),
            "canvas-mismatch": bytes(good[:8]) + b"\x09\x00" + bytes(good[10:]),
            "size-mismatch": wrapped(support.clip(3, CANVAS[0] + 1, CANVAS[1], (1000,))),
            "loop-mismatch": bytes(good[:12]) + (1).to_bytes(4, "little") + bytes(good[16:]),
            "payload-size": bytes(good[:16]) + (len(good) - 19).to_bytes(4, "little") + bytes(good[20:]),
        }
        for reason, data in cases.items():
            with self.subTest(reason=reason):
                files = show_of([{"id": 1, "file": "a.odrgx"}, {"id": 2, "file": "b.odrg"}], {"a.odrgx": data, "b.odrg": loop_of(2, 5)})
                run = support.start(files, ["error", *asked(0, "list")])
                self.assertEqual(run.lines[0], "error none")
                self.assertIn(f"file a.odrgx unavailable: {reason}", run.logs)
                self.assertEqual(replies(run)[0]["items"][0]["fault"], reason)

    def test_a_container_named_odrg_and_an_odrg_file_named_odrgx_are_read_by_their_bytes(self):
        clip = loop_of(2, 9)
        expected = self.play(show_of([{"id": 1, "file": "a.odrg"}], {"a.odrg": clip}), 4)
        self.assertEqual(self.play(show_of([{"id": 1, "file": "a.odrg"}], {"a.odrg": wrapped(clip)}), 4), expected)
        self.assertEqual(self.play(show_of([{"id": 1, "file": "a.odrgx"}], {"a.odrgx": clip}), 4), expected)

    def test_a_name_with_another_ending_is_still_refused(self):
        run = support.start(show_of([{"id": 1, "file": "a.odrgy"}], {"a.odrgy": loop_of(2, 9)}), ["error"])
        self.assertEqual(run.lines, ["error show-malformed"])


class UploadsOfContainers(Uploads):
    def test_a_container_is_uploaded_listed_with_its_type_and_played(self):
        files = small_show([animation(1, "one.odrg")])
        boxed = wrapped(support.clip(5, 60, 6, (20, 40, 20, 100)))
        script = Script().polls(10).upload(7, "new.odrgx", boxed).line("list", "play 7", "status").polls(10)
        given = self.play(files, script)
        self.assertEqual(given[2], OK)
        self.assertEqual(json.loads(given[3])["items"][-1], {"id": 7, "file": "new.odrgx", "bytes": len(boxed), "ignored": False, "external": False, "type": "frames"})
        self.assertEqual(json.loads(given[5])["animation"], 7)
        self.assertEqual(self.left["new.odrgx"], boxed)

    def test_an_invalid_container_is_refused_with_its_reason(self):
        files = small_show([animation(1, "one.odrg")])
        good = wrapped(support.clip(5, 60, 6, (20, 40)))
        for reason, data in (("loop-mismatch", bytes(good[:12]) + (7).to_bytes(4, "little") + bytes(good[16:])),
                             ("bad-container", bytes(good[:4]) + b"\x02" + bytes(good[5:]))):
            with self.subTest(reason=reason):
                given = self.play(files, Script().polls(5).upload(7, "new.odrgx", data))
                self.assertEqual(given[-1], bad_file(reason))


class ContainersOfADrive(unittest.TestCase):
    def test_a_drives_odrgx_file_is_listed_with_its_type_and_plays(self):
        clip = loop_of(2, 5)
        run = with_drive(show_of([], {}), {"a.odrgx": wrapped(clip), "b.ODRGX": wrapped(loop_of(3, 6)), "c.odrg": loop_of(2, 7)}, asked(0, "list") + seconds_of_polls(2))
        self.assertEqual(listed(replies(run)[0]), [(60001, "a.odrgx"), (60002, "b.ODRGX"), (60003, "c.odrg")])
        self.assertEqual([item["type"] for item in replies(run)[0]["items"]], ["frames", "frames", "frames"])
        self.assertEqual(logged(run), [])
        alone = pictures(with_drive(show_of([], {}), {"a.odrg": clip}, asked(0) + seconds_of_polls(2)))
        self.assertEqual(pictures(run), alone)

    def test_a_broken_container_of_a_drive_is_left_out_with_its_reason(self):
        good = wrapped(loop_of(2, 5))
        broken = bytes(good[:12]) + (3).to_bytes(4, "little") + bytes(good[16:])
        run = with_drive(show_of([], {}), {"a.odrgx": broken, "b.odrgx": good}, asked(0, "list"))
        self.assertEqual(listed(replies(run)[0]), [(60001, "a.odrgx"), (60002, "b.odrgx")])
        self.assertEqual([item.get("fault") for item in replies(run)[0]["items"]], ["loop-mismatch", None])
        self.assertEqual(logged(run), ["drive file a.odrgx left out: loop-mismatch"])


if __name__ == "__main__":
    unittest.main()

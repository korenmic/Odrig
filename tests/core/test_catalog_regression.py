"""The work that catalogs take away: a start that opens and reads every installed
animation, and a drive whose every file is read before it plays and whose copied files
join the playlist. The catalogs here are written by hand, in the format of
docs/catalog.md, apart from the project's own writer."""

import binascii
import unittest

from odrig import odrg

from . import support
from .test_drive import a_drive, asked, replies
from .test_playback import T0
from .test_playlist import CANVAS, loop_of, show_of


def page_of(name):
    """The page of a name: the low four bits of the FNV-1a hash of its bytes."""
    value = 2166136261
    for byte in name.encode("ascii"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value & 15


def crc(data):
    return binascii.crc32(data) & 0xFFFFFFFF


def catalog(files, generation=1):
    """The files of a catalog of these animations, given as name and content, in order."""
    pages = [b""] * 16
    for name, data in files.items():
        decoded = odrg.decode(data)
        total = sum(duration for duration, _ in decoded.records)
        line = f"{crc(data):08x} {len(data)} {decoded.width} {decoded.height} {total} frames {name}\n"
        pages[page_of(name)] += line.encode("ascii")
    made = {}
    marker = f"odrig-catalog 1 check 1 generation {generation:08x}\n"
    for number, page in enumerate(pages):
        lines = page.count(b"\n")
        marker += f"page {number:02d} {lines:04d} {crc(page) if lines else 0:08x}\n"
        if lines:
            made[f"catalog-{number:02d}.txt"] = page
    marker = marker.encode("ascii")
    made["catalog.txt"] = marker + f"crc {crc(marker):08x}\n".encode("ascii")
    return made


ANIMATIONS = {"one.odrg": loop_of(4, 1), "two.odrg": loop_of(6, 2), "three.odrg": loop_of(8, 3)}
SHOW = show_of([{"id": 1, "file": "one.odrg"}, {"id": 2, "file": "two.odrg"}, {"id": 3, "file": "three.odrg"}], ANIMATIONS, min_seconds=4)
# The drive's files are dense, so that what reads them stands out from the catalog's bytes.
DRIVE = {"sun.odrg": support.dense_clip(*CANVAS, 20), "moon.odrg": support.dense_clip(*CANVAS, 30)}


def grid(step):
    """The grid time of the refresh `step` after power-on."""
    return T0 + 20 * step


def read_bytes(run):
    """What `read` and `read_at` gave the core in a session, after its start."""
    return sum(int(line.split()[1]) for line in run.lines if line.startswith("call "))


class TheStart(unittest.TestCase):
    def test_the_marker_is_409_bytes(self):
        self.assertEqual(len(catalog(ANIMATIONS)["catalog.txt"]), 409)

    def test_a_start_with_a_catalog_of_every_file_opens_none_of_them(self):
        run = support.start({**SHOW, **catalog(ANIMATIONS)}, asked(0, "status"), ["--trace-files"], check_first=False)
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], [])

    def test_a_start_with_a_catalog_of_every_file_lists_every_size_at_once(self):
        run = support.start({**SHOW, **catalog(ANIMATIONS)}, asked(0, "list"), check_first=False)
        self.assertEqual([item["bytes"] for item in replies(run)[0]["items"]], [len(data) for data in ANIMATIONS.values()])


class TheDrive(unittest.TestCase):
    def session(self, drive, script):
        with a_drive(drive) as top:
            return support.start({**SHOW, **catalog(ANIMATIONS)}, script, ["--drive", top, "--trace-calls"], check_first=False)

    @unittest.expectedFailure
    def test_a_drive_with_a_catalog_has_none_of_its_animations_read_before_one_plays(self):
        # Animation 1 plays alone, so that no file of the drive is played.
        script = asked(0, "play 1") + [f"poll {grid(step)}" for step in range(400)] + asked(8100, "list")
        run = self.session({**DRIVE, **catalog(DRIVE)}, script)
        listed = [item["file"] for item in replies(run)[-1]["items"]]
        self.assertEqual(sorted(listed[3:]), sorted(DRIVE))
        self.assertLess(read_bytes(run), sum(len(data) for data in DRIVE.values()))

    @unittest.expectedFailure
    def test_a_file_copied_onto_a_drive_with_a_catalog_is_not_an_animation(self):
        copied = {**DRIVE, **catalog(DRIVE), "copied.odrg": loop_of(2, 7)}
        script = [f"poll {grid(step)}" for step in range(400)] + asked(8100, "list")
        run = self.session(copied, script)
        self.assertNotIn("copied.odrg", [item["file"] for item in replies(run)[-1]["items"]])


if __name__ == "__main__":
    unittest.main()

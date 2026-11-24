"""`read <id> <offset> <count>`: the bytes of a file, 1 to 720 of them, from an offset, with
the refusals of the form without a count, and a reply that fits with a size of ten digits."""

import dataclasses
import json
import unittest
from unittest import mock

from odrig import catalog

from . import support
from .test_clocks import DIGITAL, clock_of
from .test_content import animation, cycle, refused, small_show
from .test_drive import a_drive, replies, with_drive
from .test_editing import data_of
from .test_playback import T0
from .test_upload import Script, Uploads

# The most bytes `read` gives with a count, and the room of a reply with its newline.
MOST = 720
REPLY_MAX = 1024
CANVAS = (60, 6)


class Counted(Uploads):
    def files(self):
        """A show of a frames file of more than 1,440 bytes, a clock, and a cycle."""
        return small_show([animation(1, "one.odrg"), animation(2, "clock.odrgx"), cycle(3, [1, 2])],
                          files={"one.odrg": support.clip(4, 60, 6, (20,) * 12), "clock.odrgx": clock_of(DIGITAL, canvas=(60, 6))})

    def test_a_count_reads_that_many_bytes_from_the_offset_and_no_more_than_the_file_has(self):
        files = self.files()
        whole = files["one.odrg"]
        self.assertGreater(len(whole), 2 * MOST)
        size = len(whole)
        given = self.play(files, Script().polls(1).line("read 1 0 1", f"read 1 0 {MOST}", "read 1 7 300", f"read 1 {size - 5} {MOST}", f"read 1 {size} 1", "read 2 0 720"))
        self.assertEqual([data_of(reply) for reply in given],
                         [(whole[:1], size), (whole[:MOST], size), (whole[7:307], size), (whole[-5:], size), (b"", size), (files["clock.odrgx"], 40)])

    def test_a_file_is_read_whole_in_pieces_of_720_bytes(self):
        files = self.files()
        whole = files["one.odrg"]
        offsets = list(range(0, len(whole) + 1, MOST))
        given = self.play(files, Script().polls(1).line(*(f"read 1 {offset} {MOST}" for offset in offsets)))
        self.assertEqual(b"".join(data_of(reply)[0] for reply in given), whole)
        self.assertEqual([len(data_of(reply)[0]) for reply in given[:-1]], [MOST] * (len(offsets) - 1))

    def test_the_form_without_a_count_still_gives_600_bytes(self):
        files = self.files()
        given = self.play(files, Script().polls(1).line("read 1 0", f"read 1 0 {MOST}"))
        self.assertEqual([len(data_of(reply)[0]) for reply in given], [600, MOST])

    def test_the_count_is_1_to_720_in_decimal_digits(self):
        files = self.files()
        lines = ["read 1 0 0", f"read 1 0 {MOST + 1}", "read 1 0 4294967296", "read 1 0 x", "read 1 0 -1", "read 1 0 1 1", "read 1 0 ", "read 9 0 0"]
        given = self.play(files, Script().polls(1).line(*lines))
        self.assertEqual(given, [refused("bad-argument")] * len(lines))

    def test_its_refusals_are_those_of_the_form_without_a_count(self):
        files = self.files()
        lines = ["read 9 0 10", "read 3 0 10", f"read 1 {len(files['one.odrg']) + 1} 10", "read 0 0 10"]
        given = self.play(files, Script().polls(1).line(*lines))
        self.assertEqual(given, [refused("unknown-id"), refused("unknown-id"), refused("bad-argument"), refused("bad-argument")])
        self.assertEqual(support.start(files, [support.line(T0, "read 1 0 10")], check_first=False).lines, ["reply " + refused("busy")])
        missing = self.files()
        del missing["one.odrg"]
        self.assertEqual(support.start(missing, [support.line(T0, "read 1 0 10")]).lines, ["reply " + refused("unavailable")])
        missing["show.json"] = "{"
        self.assertEqual(support.start(missing, [support.line(T0, "read 2 0 10")]).lines, ["reply " + refused("show-invalid")])
        for option in ("--no-storage", "--only-space"):
            with self.subTest(option=option):
                self.assertEqual(support.start(self.files(), [support.line(T0, "read 2 0 10")], [option]).lines, ["reply " + refused("storage-error")])
        failing = support.start(self.files(), [support.line(T0, f"read 1 0 {MOST}"), support.line(T0, f"read 1 {MOST} {MOST}")], ["--command-read-fails", "one.odrg", "800"])
        self.assertEqual(json.loads(failing.lines[0][len("reply "):])["ok"], True)
        self.assertEqual(failing.lines[1], "reply " + refused("storage-error"))

    def test_the_bytes_of_a_transport_get_the_same_reply(self):
        files = self.files()
        by_line = self.play(files, Script().polls(1).line(f"read 1 600 {MOST}"))
        by_bytes = self.play(files, Script().polls(1).bytes(f"read 1 600 {MOST}\r\n".encode("ascii")))
        self.assertEqual(by_bytes, by_line)


def a_card(files, size):
    """The files of a card's folder `odrig` with a catalog whose entries all give this size."""
    real = catalog.entry_of
    storage = catalog.MemoryStorage(files, drive=True)
    with mock.patch.object(catalog, "entry_of", lambda name, data, canvas=CANVAS: dataclasses.replace(real(name, data, canvas), bytes=size)):
        _, left_out = catalog.rebuild(storage, canvas=CANVAS)
    assert left_out == [], left_out
    return storage.files


class OfTheCard(unittest.TestCase):
    def test_a_cards_file_is_read_with_a_count_to_its_end(self):
        clip = support.clip(6, *CANVAS, (20,) * 12)
        self.assertGreater(len(clip), MOST)
        run = with_drive(small_show([animation(1, "one.odrg")]), {"a.odrg": clip}, [f"poll {T0 + 20 * step}" for step in range(20)] +
                         [support.line(T0 + 400, f"read 60001 0 {MOST}"), support.line(T0 + 400, f"read 60001 {len(clip)} {MOST}"), support.line(T0 + 400, "read 60002 0 5")])
        reply, end, missing = replies(run)
        self.assertEqual(data_of(json.dumps(reply)), (clip[:MOST], len(clip)))
        self.assertEqual(data_of(json.dumps(end)), (b"", len(clip)))
        self.assertEqual(missing, json.loads(refused("unknown-id")))

    def test_720_bytes_and_a_size_of_ten_digits_make_a_reply_of_1001_bytes(self):
        clip = support.clip(6, *CANVAS, (20,) * 12)
        size = 4294967295
        with a_drive(a_card({"a.odrg": clip}, size)) as top:
            run = support.start(small_show([animation(1, "one.odrg")]), [f"poll {T0 + 20 * step}" for step in range(20)] + [support.line(T0 + 400, f"read 60001 0 {MOST}")], ["--drive", top], check_first=False)
        reply = [line[len("reply "):] for line in run.lines if line.startswith("reply ")][0]
        self.assertEqual(data_of(reply), (clip[:MOST], size))
        self.assertEqual(len(reply.encode("ascii")) + 1, 1001)
        self.assertLessEqual(len(reply) + 1, REPLY_MAX)


if __name__ == "__main__":
    unittest.main()

import base64
import json
import zlib

from . import support
from .test_clocks import DIGITAL, clock_of
from .test_content import OK, animation, cycle, refused, small_show
from .test_drive import replies, with_drive
from .test_playback import T0
from .test_upload import Script, Uploads


def data_of(reply):
    """The bytes and the size of a reply of `read`."""
    given = json.loads(reply)
    return base64.urlsafe_b64decode(given["data"] + "=" * (-len(given["data"]) % 4)), given["bytes"]


def crc(data):
    return f"{zlib.crc32(data):08x}"


class Reading(Uploads):
    def files(self):
        """A show of a frames file of more than 600 bytes, a clock, and a cycle."""
        return small_show([animation(1, "one.odrg"), animation(2, "clock.odrgx"), cycle(3, [1, 2])],
                          files={"one.odrg": support.clip(4, 60, 6, (20,) * 9), "clock.odrgx": clock_of(DIGITAL, canvas=(60, 6))})

    def test_a_file_is_read_in_pieces_of_600_bytes_to_its_end(self):
        files = self.files()
        whole = files["one.odrg"]
        self.assertGreater(len(whole), 1200)
        offsets = list(range(0, len(whole) + 1, 600)) + [len(whole), 7]
        given = self.play(files, Script().polls(1).line(*(f"read 1 {offset}" for offset in offsets)))
        pieces = [data_of(reply) for reply in given]
        self.assertEqual({size for _, size in pieces}, {len(whole)})
        self.assertEqual(b"".join(data for data, _ in pieces[:-2]), whole)
        self.assertEqual(pieces[-2][0], b"")
        self.assertEqual(pieces[-1][0], whole[7:607])

    def test_a_clock_and_a_text_are_read_whole_in_one_reply(self):
        files = self.files()
        given = self.play(files, Script().polls(1).line("read 2 0", "read 2 40"))
        self.assertEqual(data_of(given[0]), (files["clock.odrgx"], 40))
        self.assertEqual(given[1], '{"ok":true,"bytes":40,"data":""}')

    def test_its_refusals(self):
        files = self.files()
        lines = ["read", "read 1", "read 1 0 0", "read 0 0", "read 4294967296 0", "read x 0", "read 1 -1", "read 1 4294967296",
                 "read 9 0", "read 3 0", f"read 1 {len(files['one.odrg']) + 1}"]
        given = self.play(files, Script().polls(1).line(*lines))
        self.assertEqual(given, [refused("bad-argument")] * 8 + [refused("unknown-id")] * 2 + [refused("bad-argument")])

    def test_it_waits_for_the_check_of_its_file_and_not_for_an_upload(self):
        files = self.files()
        run = support.start(files, [support.line(T0, "read 1 0")], check_first=False)
        self.assertEqual(run.lines, ["reply " + refused("busy")])
        given = self.play(files, Script().polls(1).send(7, "new.odrg", support.clip(5, 60, 6)).line("read 2 0"))
        self.assertEqual(data_of(given[-1])[0], files["clock.odrgx"])

    def test_an_invalid_show_an_unavailable_animation_and_a_host_without_a_second_reader(self):
        files = self.files()
        del files["one.odrg"]
        self.assertEqual(support.start(files, [support.line(T0, "read 1 0")]).lines, ["reply " + refused("unavailable")])
        files["show.json"] = "{"
        self.assertEqual(support.start(files, [support.line(T0, "read 2 0")]).lines, ["reply " + refused("show-invalid")])
        for option in ("--no-storage", "--only-space"):
            with self.subTest(option=option):
                run = support.start(self.files(), [support.line(T0, "read 2 0")], [option])
                self.assertEqual(run.lines, ["reply " + refused("storage-error")])

    def test_a_file_that_cannot_be_read_is_a_storage_error(self):
        run = support.start(self.files(), [support.line(T0, "read 1 0"), support.line(T0, "read 1 600")], ["--command-read-fails", "one.odrg", "700"])
        self.assertEqual(json.loads(run.lines[0][len("reply "):])["ok"], True)
        self.assertEqual(run.lines[1], "reply " + refused("storage-error"))

    def test_the_bytes_of_a_transport_get_the_same_reply(self):
        files = self.files()
        by_line = self.play(files, Script().polls(1).line("read 1 600"))
        by_bytes = self.play(files, Script().polls(1).bytes(b"read 1 600\r\n"))
        self.assertEqual(by_bytes, by_line)

    def test_a_drives_animation_is_read_too(self):
        clip = support.clip(6, 60, 6, (20, 40))
        run = with_drive(small_show([animation(1, "one.odrg")]), {"a.odrg": clip}, [f"poll {T0 + 20 * step}" for step in range(20)] + [support.line(T0 + 400, "read 60001 0"), support.line(T0 + 400, "read 60002 0")])
        reply, missing = replies(run)
        self.assertEqual((base64.urlsafe_b64decode(reply["data"] + "=" * (-len(reply["data"]) % 4)), reply["bytes"]), (clip[:600], len(clip)))
        self.assertEqual(missing, json.loads(refused("unknown-id")))


class ReplacingSafely(Uploads):
    def files(self):
        made = small_show([animation(1, "one.odrg"), animation(2, "clock.odrgx"), cycle(3, [1, 2])],
                          files={"clock.odrgx": clock_of(DIGITAL, canvas=(60, 6))})
        return made

    def test_the_right_crc_lets_the_upload_replace_the_item_in_its_place(self):
        files = self.files()
        new = clock_of(DIGITAL, seconds=9, canvas=(60, 6))
        script = Script().polls(1).line("upload begin 2 clock.odrgx 40", f"upload expect {crc(files['clock.odrgx'])}")
        script.line(*support.upload_lines(2, "clock.odrgx", new)[1:]).check(new).end(new).line("list")
        given = self.play(files, script)
        self.assertEqual(given[1], OK)
        self.assertEqual(given[-2], OK)
        items = json.loads(given[-1])["items"]
        self.assertEqual([item["id"] for item in items], [1, 2, 3])
        self.assertEqual(items[1], {"id": 2, "file": "clock.odrgx", "bytes": 40, "ignored": False, "external": False, "type": "widget"})
        self.assertEqual(self.left["clock.odrgx"], new)

    def test_an_ignored_item_stays_ignored(self):
        files = self.files()
        new = clock_of(DIGITAL, seconds=9, canvas=(60, 6))
        lines = [f"poll {T0}", support.line(T0, "ignore 2 1"), support.line(T0, "upload begin 2 clock.odrgx 40"),
                 support.line(T0, f"upload expect {crc(files['clock.odrgx'])}"), *(support.line(T0, line) for line in support.upload_lines(2, "clock.odrgx", new)[1:])]
        lines += [f"poll {T0 + 20 * step}" for step in range(1, 6)] + [support.line(T0 + 100, support.upload_end(new)), support.line(T0 + 100, "list")]
        given = replies(support.start(files, lines))
        self.assertEqual(given[-2], json.loads(OK))
        self.assertEqual(given[-1]["items"][1], {"id": 2, "file": "clock.odrgx", "bytes": 40, "ignored": True, "external": False, "type": "widget"})

    def test_a_changed_file_is_stale_and_the_upload_is_gone(self):
        files = self.files()
        given = self.play(files, Script().polls(1).line("upload begin 2 clock.odrgx 40", "upload expect 00000000", "upload data 0 AAAA", "list"))
        self.assertEqual(given[1:3], [refused("stale"), refused("no-upload")])
        self.assertEqual(self.left["clock.odrgx"], files["clock.odrgx"])
        self.assertNotIn("upload.part", self.left)

    def test_an_item_that_is_gone_is_stale(self):
        files = self.files()
        given = self.play(files, Script().polls(1).line("upload begin 9 other.odrgx 40", f"upload expect {crc(files['clock.odrgx'])}", "upload cancel"))
        self.assertEqual(given[1:], [refused("stale"), refused("no-upload")])

    def test_a_file_above_16384_bytes_is_refused_and_the_upload_stays(self):
        files = small_show([animation(1, "big.odrg")], files={"big.odrg": support.dense_clip(60, 6, 6)})
        self.assertGreater(len(files["big.odrg"]), 16384)
        given = self.play(files, Script().polls(1).line("upload begin 1 big.odrg 40", f"upload expect {crc(files['big.odrg'])}", "upload cancel"))
        self.assertEqual(given[1:], [refused("bad-argument"), OK])

    def test_its_refusals(self):
        files = self.files()
        given = self.play(files, Script().polls(1).line("upload expect 00000000", "upload begin 2 clock.odrgx 40", "upload expect", "upload expect 0000000", "upload expect 0000000G",
                                                         "upload expect 00000000 1", "upload cancel"))
        self.assertEqual(given, [refused("no-upload"), '{"ok":true,"chunk":1500}'] + [refused("bad-argument")] * 4 + [OK])

    def test_a_file_that_cannot_be_read_is_a_storage_error_and_the_upload_is_gone(self):
        files = self.files()
        run = support.start(files, [f"poll {T0}", support.line(T0, "upload begin 2 clock.odrgx 40"), support.line(T0, f"upload expect {crc(files['clock.odrgx'])}"),
                                    support.line(T0, "upload cancel")], ["--command-read-fails", "clock.odrgx", "10"])
        self.assertEqual([reply.get("error") for reply in replies(run)], [None, "storage-error", "no-upload"])

import base64
import json
import struct
import unittest
import zlib

from odrig import jsonframes, odrg

from . import support
from .test_content import BLOCK, BOARD, OK, Content, animation, cycle, refused, replies, small_show
from .test_playback import T0, refreshes

INVALID = support.ROOT / "tests" / "vectors" / "invalid"
CHUNK = '{"ok":true,"chunk":1500}'
ITEMS = [animation(1, "one.odrg"), animation(2, "two.odrg"), cycle(3, [1, 2], 1), animation(4, "four.odrg"), animation(5, "two.odrg"), cycle(6, [4, 5, 4], 2)]


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def frames_of(data):
    return len(odrg.decode(support.frames_payload(data)).records)


def received(count):
    return f'{{"ok":true,"received":{count}}}'


def bad_file(reason):
    return f'{{"ok":false,"error":"bad-file","reason":"{reason}"}}'


class Script:
    """The input lines of a session, written against a clock. A poll is made at the time
    of the clock and moves it on by 20 ms; a command line is given at the time of the
    clock, before the poll of that time."""

    def __init__(self, time=T0):
        self.lines = []
        self.sent = []      # the command lines given so far, each of which gets one reply
        self.time = time
        self.polled = None  # the time of the latest poll

    def copy(self):
        made = Script(self.time)
        made.lines, made.sent, made.polled = list(self.lines), list(self.sent), self.polled
        return made

    def polls(self, count):
        for _ in range(count):
            self.lines.append(f"poll {self.time}")
            self.polled = self.time
            self.time += 20
        return self

    def line(self, *texts):
        for text in texts:
            self.lines.append(support.line(self.time, text))
            self.sent.append(text)
        return self

    def bytes(self, data):
        self.lines.append(support.fed(self.time, data))
        self.sent += ["<bytes>"] * data.count(b"\n")
        return self

    def wait(self, milliseconds):
        self.time += milliseconds
        return self

    def send(self, number, name, data, piece=1500):
        """Opens an upload and sends every piece of a file."""
        return self.line(*support.upload_lines(number, name, data, piece))

    def check(self, data, short=0):
        """The refreshes the check of a file takes: one for its header, one for each frame
        record and one for its end; or some fewer. A refresh that does not follow the one
        before it without a gap takes no step, so one more is asked for first."""
        if self.polled is None or self.polled != self.time - 20:
            self.polls(1)
        return self.polls(frames_of(data) + 2 - short)

    def end(self, data):
        return self.line(support.upload_end(data))

    def upload(self, number, name, data, piece=1500):
        """A whole upload: the pieces, the refreshes of the check, and its end."""
        return self.send(number, name, data, piece).check(data).end(data)


class Uploads(Content):
    def play(self, files, script, options=(), storage=BOARD, changeable=True):
        """Runs a script on the core and on the reference player, compares every line and
        the folder afterwards, and gives the replies."""
        self.given = replies(self.run_both(files, script.lines, options, storage, changeable))
        self.sent = script.sent
        self.assertEqual(len(self.given), len(self.sent))
        return self.given

    def answers(self, start):
        """The replies to the command lines that begin with this text, in their order."""
        return [reply for text, reply in zip(self.sent, self.given) if text.startswith(start)]

    def listed(self):
        """The items the reference player lists after the session."""
        return json.loads(self.reference.command(10 ** 9, b"list"))["items"]


class NewAndReplaced(Uploads):
    def test_a_new_item_is_added_at_the_end_and_plays_at_once(self):
        files = small_show(ITEMS, start=6, brightness=40)
        clip = support.clip(7, 60, 6, (20, 40, 20, 100))
        script = Script().polls(20).upload(9, "new.odrg", clip).line("list", "play 9", "status").polls(30).line("status", "space")
        given = self.play(files, script)
        self.assertEqual(given[:3], [CHUNK, received(len(clip)), OK])
        self.assertEqual(json.loads(given[3])["items"][-1], {"id": 9, "file": "new.odrg", "bytes": len(clip), "ignored": False, "external": False, "type": "frames"})
        self.assertEqual([item["id"] for item in json.loads(given[3])["items"]], [1, 2, 3, 4, 5, 6, 9])
        self.assertEqual(given[4], OK)
        self.assertEqual((json.loads(given[5])["playing"], json.loads(given[5])["animation"], json.loads(given[6])["animation"]), ("all", 9, 9))
        self.assertEqual(json.loads(given[7])["animations"], 5)
        self.assertEqual(self.left["new.odrg"], clip)
        self.assertEqual(json.loads(self.left["show.json"])["items"][-1], {"id": 9, "file": "new.odrg"})
        self.assertEqual((json.loads(self.left["show.json"])["start"], json.loads(self.left["show.json"])["brightness"]), (6, 40))
        self.assertEqual(sorted(self.left), ["four.odrg", "mapping.json", "new.odrg", "one.odrg", "show.json", "two.odrg"])

    def test_a_new_item_is_there_after_a_restart(self):
        files = small_show(ITEMS, start=6)
        clip = support.clip(8, 60, 6)
        self.assertEqual(self.play(files, Script().polls(5).upload(700, "kept.odrg", clip))[-1], OK)
        again = Script().line("list", "play 700").polls(10).line("status")
        given = self.play(self.left, again)
        self.assertEqual(json.loads(given[0])["items"][-1], {"id": 700, "file": "kept.odrg", "bytes": len(clip), "ignored": False, "external": False, "type": "frames"})
        self.assertEqual((json.loads(given[2])["playing"], json.loads(given[2])["animation"]), ("all", 700))

    def test_a_replacement_under_the_same_name_leaves_the_show_file_and_restarts_what_plays(self):
        files = small_show(ITEMS, start=1)
        before = files["show.json"].encode()
        clip = support.clip(11, 60, 6, (60, 20, 20, 40, 20))
        self.assertNotEqual(clip, files["one.odrg"])
        script = Script().polls(40).upload(1, "one.odrg", clip).polls(40).line("status", "list")
        self.play(files, script, ["--trace-store"])
        self.assertEqual(self.answers("upload end"), [OK])
        self.assertEqual(self.left["one.odrg"], clip)
        self.assertEqual(self.left["show.json"], before)
        self.assertEqual(json.loads(self.answers("list")[0])["items"][0], {"id": 1, "file": "one.odrg", "bytes": len(clip), "ignored": False, "external": False, "type": "frames"})
        # The one storage call that puts it in place is the rename onto its name.
        self.assertEqual(self.stored[-1], "rename upload.part one.odrg 1")
        self.assertNotIn("write_open show.part 1", self.stored)
        # The picture after the upload is the new file's, from its first frame.
        produced, _ = refreshes([line for line in self.printed if line.startswith(("refresh", "data"))])
        fresh = support.ReferencePlayer(dict(files, **{"one.odrg": clip}))
        self.assertEqual(produced[40 + frames_of(clip) + 2][1], dict(fresh.poll(T0)))

    def test_a_replacement_under_another_name_deletes_the_old_file_and_keeps_the_position(self):
        files = small_show(ITEMS, start=3)
        clip = support.clip(12, 60, 6)
        script = Script().polls(30).upload(4, "newer.odrg", clip).polls(10).line("list", "play 6").polls(120).line("status")
        self.play(files, script)
        self.assertEqual(self.answers("upload end"), [OK])
        self.assertEqual([(item["id"], item.get("file")) for item in json.loads(self.answers("list")[0])["items"]],
                         [(1, "one.odrg"), (2, "two.odrg"), (3, None), (4, "newer.odrg"), (5, "two.odrg"), (6, None)])
        self.assertNotIn("four.odrg", self.left)
        self.assertEqual(self.left["newer.odrg"], clip)
        self.assertEqual(json.loads(self.left["show.json"])["items"][3], {"id": 4, "file": "newer.odrg"})

    def test_a_replacement_leaves_an_old_file_that_another_item_names(self):
        files = small_show(ITEMS, start=6)
        clip = support.clip(13, 60, 6)
        self.play(files, Script().polls(30).upload(5, "five.odrg", clip).polls(150).line("list"))
        self.assertEqual(self.answers("upload end"), [OK])
        self.assertEqual(self.left["two.odrg"], files["two.odrg"])
        self.assertEqual(self.left["five.odrg"], clip)
        self.play(self.left, Script().polls(2).upload(2, "second.odrg", clip).line("list").polls(5))
        self.assertEqual(self.answers("upload end"), [OK])
        self.assertNotIn("two.odrg", self.left)
        self.assertEqual(sorted(self.left), ["five.odrg", "four.odrg", "mapping.json", "one.odrg", "second.odrg", "show.json"])

    def test_the_file_of_an_animation_the_playing_cycle_lists_restarts_the_cycle(self):
        files = small_show(ITEMS, start=6)
        clip = support.clip(14, 60, 6, (20,) * 5)
        for number, name in ((4, "four.odrg"), (5, "fresh.odrg"), (1, "one.odrg"), (2, "second.odrg")):
            with self.subTest(replaced=number):
                script = Script().polls(130).upload(number, name, clip).line("status").polls(130).line("status")
                self.play(files, script)
                self.assertEqual(self.answers("upload end"), [OK])
                self.assertEqual([json.loads(reply)["playing"] for reply in self.answers("status")], [6, 6])

    def test_compressed_and_uncompressed_files_on_every_mapping_of_the_suite(self):
        for name, text in support.mapping_texts().items():
            with self.subTest(mapping=name):
                canvas = support.mapping.loads(text.encode())
                width, height = canvas.width, canvas.height
                first = support.clip(21, width, height, (20, 40), compressed=True)
                second = support.clip(22, width, height, (40, 20, 20), compressed=False)
                files = {"mapping.json": text, "show.json": support.show_text([animation(1, "first.odrg")], 255, 1), "first.odrg": first}
                script = Script().polls(5).upload(2, "plain.odrg", second).line("play 2").polls(8)
                script.upload(1, "first.odrg", second).upload(2, "packed.odrg", first).line("list").polls(8).line("play 1").polls(8)
                self.play(files, script)
                self.assertEqual(self.answers("upload begin"), [CHUNK] * 3)
                self.assertEqual(self.answers("upload end"), [OK] * 3)
                self.assertEqual(self.left["first.odrg"], second)
                self.assertEqual(self.left["packed.odrg"], first)
                self.assertNotIn("plain.odrg", self.left)

    def test_pieces_of_1_of_1499_and_of_1500_bytes(self):
        files = small_show(ITEMS, start=6)
        small = support.clip(31, 60, 6)
        large = support.dense_clip(60, 6, 1)
        self.assertGreater(len(large), 4500)
        for clip, piece in ((small, 1), (small, 7), (large, 1499), (large, 1500), (large, 1000), (large, 77)):
            with self.subTest(piece=piece):
                script = Script().polls(3).send(9, "new.odrg", clip, piece).check(clip).end(clip).line("play 9").polls(5)
                self.play(files, script)
                pieces = -(-len(clip) // piece)
                self.assertEqual(len(self.answers("upload data")), pieces)
                self.assertEqual(self.answers("upload data")[-1], received(len(clip)))
                self.assertEqual(self.answers("upload end") + self.answers("play"), [OK, OK])
                self.assertEqual(self.left["new.odrg"], clip)

    def test_a_piece_of_more_than_1500_bytes_is_refused_and_one_of_1500_is_taken(self):
        files = small_show(ITEMS)
        large = support.dense_clip(60, 6, 1)
        script = Script().line(f"upload begin 9 new.odrg {len(large)}")
        script.line(f"upload data 0 {b64(large[:1501])}", f"upload data 0 {b64(large[:1503])}", f"upload data 0 {b64(large[:1525])}", f"upload data 0 {b64(large[:1526])}")
        script.line(f"upload data 0 {b64(large[:1500])}", f"upload data 1500 {b64(large[1500:1501])}")
        given = self.play(files, script)
        self.assertEqual(given, [CHUNK] + [refused("bad-argument")] * 3 + [refused("line-too-long"), received(1500), received(1501)])
        # The longest line an upload needs has room in a line of 2,048 characters.
        self.assertEqual(len(f"upload data 4294967295 {b64(bytes(1500))}"), 2023)
        self.assertEqual(len(f"upload data 0 {b64(large[:1525])}"), 2048)


# A show whose animations say how long their turns are, in every way an item can.
TURNS = [{"id": 1, "file": "one.odrg", "repeat": 3, "max_seconds": 120}, {"id": 2, "file": "two.odrg", "max_seconds": 9},
         {"id": 3, "file": "three.odrg", "repeat": 2}, animation(4, "four.odrg"), cycle(6, [4, 2], 2)]


def with_min_seconds(files, seconds):
    """The file set with the shortest time of an animation named in its show file."""
    show = json.loads(files["show.json"])
    show["min_seconds"] = seconds
    return files | {"show.json": json.dumps(show)}


class WhatTheShowSaysOfTheTurns(Uploads):
    """The file the core writes keeps every number of the show file about the turns."""

    def test_the_file_written_after_a_removal_keeps_it(self):
        files = with_min_seconds(small_show(TURNS, start=6), 45)
        self.play(files, Script().polls(5).line("remove 3").polls(5))
        self.assertEqual(self.answers("remove"), [OK])
        self.assertEqual(
            self.left["show.json"],
            b'{"version":1,"brightness":128,"min_seconds":45,"items":[{"id":1,"file":"one.odrg","repeat":3,"max_seconds":120},'
            b'{"id":2,"file":"two.odrg","max_seconds":9},{"id":4,"file":"four.odrg"},{"id":6,"cycle":[4,2],"seconds":2}],"start":6}\n')

    def test_a_show_that_names_no_shortest_time_gets_none_written(self):
        self.play(small_show(TURNS, start=6), Script().polls(5).line("remove 1").polls(5))
        self.assertEqual(
            self.left["show.json"],
            b'{"version":1,"brightness":128,"items":[{"id":2,"file":"two.odrg","max_seconds":9},{"id":3,"file":"three.odrg","repeat":2},'
            b'{"id":4,"file":"four.odrg"},{"id":6,"cycle":[4,2],"seconds":2}],"start":6}\n')

    def test_an_animation_that_is_replaced_keeps_its_numbers_and_a_new_item_has_none(self):
        clip = support.clip(12, 60, 6)
        files = with_min_seconds(small_show(TURNS, start=6), 1)
        script = Script().polls(5).upload(1, "newer.odrg", clip).polls(5).upload(9, "nine.odrg", clip).polls(5).upload(2, "two.odrg", clip).polls(5)
        self.play(files, script)
        self.assertEqual(self.answers("upload end"), [OK, OK, OK])
        self.assertEqual(
            self.left["show.json"],
            b'{"version":1,"brightness":128,"min_seconds":1,"items":[{"id":1,"file":"newer.odrg","repeat":3,"max_seconds":120},'
            b'{"id":2,"file":"two.odrg","max_seconds":9},{"id":3,"file":"three.odrg","repeat":2},{"id":4,"file":"four.odrg"},'
            b'{"id":6,"cycle":[4,2],"seconds":2},{"id":9,"file":"nine.odrg"}],"start":6}\n')

    def test_the_written_file_is_read_again_and_written_the_same(self):
        files = with_min_seconds(small_show(TURNS, start=6), 65535)
        self.play(files, Script().polls(5).line("remove 3").polls(5))
        first = dict(self.left)
        self.play(first, Script().polls(5).line("remove 6").polls(5))
        self.assertEqual(self.answers("remove"), [OK])
        self.assertEqual(
            self.left["show.json"],
            b'{"version":1,"brightness":128,"min_seconds":65535,"items":[{"id":1,"file":"one.odrg","repeat":3,"max_seconds":120},'
            b'{"id":2,"file":"two.odrg","max_seconds":9},{"id":4,"file":"four.odrg"}]}\n')

    def test_the_largest_numbers_are_written_whole(self):
        items = [{"id": 1, "file": "one.odrg", "repeat": 65535, "max_seconds": 65535}, animation(2, "two.odrg")]
        self.play(small_show(items), Script().polls(5).line("remove 2").polls(5))
        self.assertEqual(self.left["show.json"], b'{"version":1,"brightness":128,"items":[{"id":1,"file":"one.odrg","repeat":65535,"max_seconds":65535}]}\n')


class Arguments(Uploads):
    def test_base64_that_is_not_as_described_is_a_bad_argument(self):
        broken = ["", "A", "AAAAA", "AB", "AAB", "AA==", "AAA=", "AA+A", "AA/A", "AA.A", "AAA~", "AAAA\t", "QUJD=", "====", "=", "-", "A" * 2001, "A" * 2004, "A" * 2030]
        sound = {"AA": b"\0", "AQ": b"\1", "AAA": b"\0\0", "AAE": b"\0\1", "AAAA": b"\0\0\0", "-_-_": b"\xfb\xff\xbf", "QUJD": b"ABC", "__8": b"\xff\xff"}
        files = small_show(ITEMS)
        for text, data in sound.items():
            self.assertEqual(b64(data), text)
        script = Script().line(*[f"upload data 0 {text}" for text in broken])
        script.line("upload begin 9 new.odrg 100", *[f"upload data 0 {text}" for text in broken])
        given = self.play(files, script)
        self.assertEqual(given[:len(broken)], [refused("bad-argument")] * len(broken))
        self.assertEqual(given[len(broken)], CHUNK)
        self.assertEqual(given[len(broken) + 1:], [refused("bad-argument")] * len(broken))
        script = Script().line("upload begin 9 new.odrg 100")
        total = 0
        for text, data in sound.items():
            script.line(f"upload data {total} {text}")
            total += len(data)
        given = self.play(files, script)
        self.assertEqual(json.loads(given[-1]), {"ok": True, "received": total})
        self.assertEqual(self.left["upload.part"], b"".join(sound.values()))

    def test_base64_given_as_bytes_outside_ascii_is_a_bad_argument(self):
        files = small_show(ITEMS)
        lines = [b"upload data 0 QUJ\xc3\xa4", b"upload data 0 QUJ\x00", b"upload data 0 \xff\xff\xff\xff", b"upload data 0 QUJD\x80"]
        printed = self.run_both(files, [support.linehex(T0, line) for line in lines])
        self.assertEqual(replies(printed), [refused("bad-argument")] * len(lines))

    def test_a_checksum_that_is_not_eight_hexadecimal_digits_is_a_bad_argument(self):
        files = small_show(ITEMS)
        clip = support.clip(41, 60, 6)
        crc = f"{zlib.crc32(clip):08x}"
        self.assertRegex(crc, "[a-f]")
        broken = ["", crc[:7], crc + "0", crc.upper(), "0x" + crc[:6], "-" + crc[:7], crc[:7] + "g", crc[:4] + " " + crc[4:], "1234567G", "12345 78", crc + " "]
        script = Script().polls(2).send(9, "new.odrg", clip).check(clip).line("upload end", *[f"upload end {text}" for text in broken]).end(clip)
        self.play(files, script)
        self.assertEqual(self.answers("upload end"), [refused("bad-argument")] * (len(broken) + 1) + [OK])

    def test_the_arguments_of_upload_begin(self):
        files = small_show(ITEMS)
        broken = [
            "upload begin", "upload begin 9", "upload begin 9 new.odrg", "upload begin 9 new.odrg 10 1", "upload begin 9 new.odrg  10", "upload begin  9 new.odrg 10",
            "upload begin 0 new.odrg 10", "upload begin 65536 new.odrg 10", "upload begin -1 new.odrg 10", "upload begin x new.odrg 10", "upload begin 9.0 new.odrg 10",
            "upload begin 9 new.odrg 0", "upload begin 9 new.odrg 4294967296", "upload begin 9 new.odrg 99999999999999999999", "upload begin 9 new.odrg -5", "upload begin 9 new.odrg 1k",
            "upload begin 9 new.odrg ", "upload begin 9 new 10", "upload begin 9 new.ODRG 10", "upload begin 9 New.odrg 10", "upload begin 9 new.odrg.part 10", "upload begin 9 ../new.odrg 10",
            "upload begin 9 a/b.odrg 10", "upload begin 9 " + "n" * 28 + ".odrg 10", "upload begin 9 show.json 10", "upload begin 9 odrg 10", "upload begin 9 néw.odrg 10",
            "upload begin 9 new.odrg\t 10",
        ]
        printed = self.run_both(files, [support.linehex(T0, line.encode("utf-8")) for line in broken])
        self.assertEqual(replies(printed), [refused("bad-argument")] * len(broken))
        sound = ["upload begin 9 .odrg 1", "upload begin 65535 " + "n" * 27 + ".odrg 4000000", "upload begin 0009 a-b_c.9.odrg 0010"]
        for line in sound:
            self.assertEqual(self.play(files, Script().line(line, "upload cancel")), [CHUNK, OK], line)

    def test_a_word_after_upload_that_is_none_of_the_four_is_a_bad_argument(self):
        lines = ["upload", "upload ", "upload start", "upload begin9", "upload Begin 9 new.odrg 10", "upload cancel now", "upload cancel ", "upload status", "upload data", "upload data 0",
                 "upload data 0 QUJD QUJD", "upload data x QUJD", "upload data -1 QUJD", "upload data 4294967296 QUJD", "upload end", "upload 1 2 3 4 5 6 7"]
        for files in (small_show(ITEMS), {"mapping.json": support.mapping_texts()["legs-2"]}):
            printed = self.run_both(files, [support.line(T0, line) for line in lines])
            self.assertEqual(replies(printed), [refused("bad-argument")] * len(lines))
        printed = self.run_both(small_show(ITEMS), [support.line(T0, line) for line in ("Upload begin 9 new.odrg 10", "uploads", "upload\tcancel", "up load")])
        self.assertEqual(replies(printed), [refused("unknown-command")] * 4)


class EveryCode(Uploads):
    def test_with_an_invalid_show_every_upload_command_is_refused(self):
        invalid = support.with_show_fault({"mapping.json": support.mapping_texts()["legs-2"], "show.json": support.show_text([animation(1, "gone.odrg")])})
        lines = ["upload begin 9 new.odrg 10", "upload data 0 QUJD", "upload end 12345678", "upload cancel", "upload begin 9 new.odrg 0", "upload sideways"]
        printed = self.run_both(invalid, [support.line(T0, line) for line in lines])
        self.assertEqual(replies(printed), [refused("show-invalid")] * 4 + [refused("bad-argument")] * 2)

    def test_without_an_upload_data_end_and_cancel_are_no_upload(self):
        files = small_show(ITEMS)
        lines = ["upload data 0 QUJD", "upload data 5 QUJD", "upload end 12345678", "upload cancel"]
        self.assertEqual(self.play(files, Script().line(*lines)), [refused("no-upload")] * 4)
        clip = support.clip(42, 60, 6)
        script = Script().polls(2).upload(9, "new.odrg", clip).line(*lines).send(8, "other.odrg", clip).line("upload cancel").line(*lines)
        given = self.play(files, script)
        self.assertEqual(given[:3], [CHUNK, received(len(clip)), OK])
        self.assertEqual(given[3:7], [refused("no-upload")] * 4)
        self.assertEqual(given[7:10], [CHUNK, received(len(clip)), OK])
        self.assertEqual(given[10:], [refused("no-upload")] * 4)

    def test_while_an_upload_is_open_begin_and_remove_are_busy(self):
        files = small_show(ITEMS, start=6)
        clip = support.clip(43, 60, 6)
        script = Script().polls(3).line("upload begin 9 new.odrg " + str(len(clip)), "upload begin 9 new.odrg 5", "upload begin 8 other.odrg 5", "upload begin 3 x.odrg 5", "remove 3", "remove 99", "remove 1")
        script.line(f"upload data 0 {b64(clip)}", "upload begin 7 x.odrg 5", "remove 6").check(clip).line("upload begin 7 x.odrg 5", "remove 6").end(clip).line("remove 3", "list")
        given = self.play(files, script)
        self.assertEqual(given[0], CHUNK)
        self.assertEqual(given[1:7], [refused("busy")] * 6)
        self.assertEqual(given[7], received(len(clip)))
        self.assertEqual(given[8:12], [refused("busy")] * 4)
        self.assertEqual(given[12:14], [OK, OK])
        self.assertEqual([item["id"] for item in json.loads(given[14])["items"]], [1, 2, 4, 5, 6, 9])

    def test_the_id_of_a_cycle_and_a_file_name_another_item_has_are_in_use(self):
        files = small_show(ITEMS)
        lines = ["upload begin 3 new.odrg 10", "upload begin 6 six.odrg 10", "upload begin 9 one.odrg 10", "upload begin 2 one.odrg 10", "upload begin 2 four.odrg 10",
                 "upload begin 5 two.odrg 10", "upload begin 2 two.odrg 10", "upload begin 4 two.odrg 10"]
        self.assertEqual(self.play(files, Script().line(*lines)), [refused("in-use")] * len(lines))
        for line in ("upload begin 1 one.odrg 10", "upload begin 4 four.odrg 10", "upload begin 4 fresh.odrg 10", "upload begin 9 fresh.odrg 10"):
            self.assertEqual(self.play(files, Script().line(line)), [CHUNK], line)

    def test_a_file_that_would_not_fit_is_no_space(self):
        files = small_show(ITEMS)
        used = 5 * BLOCK
        cases = ((BOARD, 1, True), (BOARD, 13000000, True), (BOARD, 13412000, False), (used + 16384 + 1000 + 3, 1000, True), (used + 16384 + 1000 + 2, 1000, False),
                 (used + 16384 + 257 + 1, 257, True), (used + 16384 + 256 + 1, 256, True), (used + 16384 + 256, 256, False), (used, 1, False), (0, 1, False), (4294967295, 4294967295, False))
        for total, size, fits in cases:
            with self.subTest(total=total, size=size):
                given = self.play(files, Script().line("space", f"upload begin 9 new.odrg {size}"), ["--storage", str(total)], total)
                self.assertEqual(json.loads(given[0])["free"], max(0, total - used))
                self.assertEqual(given[1], CHUNK if fits else refused("no-space"))
        self.assertGreater(13412000 + 13412000 // 256 + 16384, BOARD - used)
        self.assertLessEqual(13000000 + 13000000 // 256 + 16384, BOARD - used)

    def test_a_show_that_has_no_room_for_another_item_is_no_space_and_a_removal_makes_room(self):
        clip = support.clip(44, 60, 6, (20,))
        items = [animation(number, "shared.odrg") for number in range(1, 97)]
        files = small_show(items, files={"shared.odrg": clip})
        script = Script().polls(2)
        for number in range(200, 232):
            script.upload(number, f"n{number}.odrg", clip)
        script.line("upload begin 300 more.odrg 5", "upload begin 65535 more.odrg 5")
        script.upload(200, "again.odrg", clip).upload(5, "five.odrg", clip).line("upload begin 301 more.odrg 5", "remove 7")
        script.upload(301, "more.odrg", clip).line("upload begin 302 last.odrg 5", "space")
        self.play(files, script)
        self.assertEqual(self.answers("upload end"), [OK] * 35)
        self.assertEqual([reply for reply in self.answers("upload begin") if reply != CHUNK], [refused("no-space")] * 4)
        self.assertEqual(self.answers("remove"), [OK])
        self.assertEqual(json.loads(self.answers("space")[0])["animations"], 128)
        self.assertEqual(len(json.loads(self.left["show.json"])["items"]), 128)
        # After a restart there is room again: 32 items more than the show has then.
        self.assertEqual(self.play(self.left, Script().line("upload begin 302 last.odrg 5")), [CHUNK])

    def test_an_offset_that_is_not_the_bytes_received_is_a_bad_offset_and_the_upload_stays(self):
        files = small_show(ITEMS)
        clip = support.clip(45, 60, 6)
        half = len(clip) // 2
        script = Script().polls(2).line(f"upload begin 9 new.odrg {len(clip)}", f"upload data 1 {b64(clip[:half])}", f"upload data {len(clip)} QUJD", "upload data 4294967295 QUJD")
        script.line(f"upload data 0 {b64(clip[:half])}", f"upload data 0 {b64(clip[:half])}", f"upload data {half - 1} {b64(clip[half:])}", f"upload data {half + 1} {b64(clip[half:])}")
        script.line(f"upload data {half} {b64(clip[half:] + b'x')}", f"upload data {half} {b64(clip[half:])}", f"upload data {len(clip)} QQ", f"upload data 0 {b64(clip[:half])}")
        script.check(clip).end(clip)
        given = self.play(files, script)
        self.assertEqual(given[0], CHUNK)
        self.assertEqual(given[1:4], [refused("bad-offset")] * 3)
        self.assertEqual(given[4], received(half))
        self.assertEqual(given[5:9], [refused("bad-offset")] * 4)
        self.assertEqual(given[9], received(len(clip)))
        self.assertEqual(given[10:12], [refused("bad-offset")] * 2)
        self.assertEqual(given[12], OK)
        self.assertEqual(self.left["new.odrg"], clip)

    def test_end_before_all_bytes_is_incomplete_and_the_upload_stays(self):
        files = small_show(ITEMS)
        clip = support.clip(46, 60, 6)
        script = Script().polls(2).line(f"upload begin 9 new.odrg {len(clip)}").end(clip).line("upload end 00000000", f"upload data 0 {b64(clip[:-1])}").end(clip).polls(40).end(clip)
        script.line(f"upload data {len(clip) - 1} {b64(clip[-1:])}").check(clip).end(clip)
        given = self.play(files, script)
        self.assertEqual(given, [CHUNK, refused("incomplete"), refused("incomplete"), received(len(clip) - 1), refused("incomplete"), refused("incomplete"), received(len(clip)), OK])

    def test_another_checksum_than_the_bytes_have_is_a_bad_checksum_and_discards_the_upload(self):
        files = small_show(ITEMS)
        clip = support.clip(47, 60, 6)
        wrong = f"{zlib.crc32(clip) ^ 1:08x}"
        for short in (frames_of(clip) + 2, 1, 0):
            with self.subTest(refreshes_short=short):
                script = Script().polls(2).send(9, "new.odrg", clip).check(clip, short).line(f"upload end {wrong}").end(clip).line("upload cancel", "list")
                self.play(files, script)
                self.assertEqual(self.answers("upload end") + self.answers("upload cancel"), [refused("bad-checksum"), refused("no-upload"), refused("no-upload")])
                self.assertNotIn("upload.part", self.left)
                self.assertNotIn("new.odrg", self.left)
                self.assertEqual(len(json.loads(self.answers("list")[0])["items"]), 6)

    def test_of_two_codes_that_apply_the_first_of_the_order_is_given(self):
        files = small_show(ITEMS)
        clip = support.clip(48, 60, 6)
        crc = f"{zlib.crc32(clip):08x}"
        nothing_open = {
            "upload begin 3 one.odrg 0": "bad-argument",
            "upload begin 3 one.odrg 99999999999": "bad-argument",
            "upload data 5 QUJ=": "bad-argument",
            "upload data 5 QUJD": "no-upload",
            "upload end 1234": "bad-argument",
            "upload end 12345678": "no-upload",
            "upload cancel 1": "bad-argument",
            "upload begin 3 one.odrg 4294967295": "in-use",
            "upload begin 9 one.odrg 4294967295": "in-use",
            "upload begin 9 new.odrg 4294967295": "no-space",
            "upload" + " x" * 1022: "line-too-long",
            "uploaded begin": "unknown-command",
        }
        self.assertEqual(self.play(files, Script().line(*nothing_open)), [refused(code) for code in nothing_open.values()])
        # A host that cannot change its storage: `no-space` comes before `storage-error`.
        for option, storage in (("--only-space", BOARD), ("--no-storage", None), ("--space-unknown", None)):
            lines = {"upload begin 3 x.odrg 10": "in-use", "upload begin 9 new.odrg 4294967295": "no-space" if storage else "storage-error", "upload begin 9 new.odrg 10": "storage-error",
                     "remove 3": "storage-error" if option != "--space-unknown" else None, "upload data 0 QUJD": "no-upload"}
            given = self.play(files, Script().line(*lines), [option], storage, option == "--space-unknown")
            self.assertEqual(given, [refused(code) if code else OK for code in lines.values()], option)
        receiving = {
            "upload begin 3 one.odrg 0": "bad-argument",
            "upload begin 3 one.odrg 10": "busy",
            "upload begin 9 new.odrg 4294967295": "busy",
            "remove 99": "busy",
            "remove 0": "bad-argument",
            f"upload end {crc[:7]}": "bad-argument",
            f"upload end {crc}": "incomplete",
            "upload end 00000000": "incomplete",
            "upload data 7 QUJ": "bad-argument",
            "upload data 7 QUJD": "bad-offset",
        }
        script = Script().line(f"upload begin 9 new.odrg {len(clip)}").line(*receiving)
        self.assertEqual(self.play(files, script)[1:], [refused(code) for code in receiving.values()])
        checking = {"upload data 0 QUJD": "bad-offset", f"upload data {len(clip)} QUJD": "bad-offset", f"upload end {crc}": "busy", "remove 3": "busy", "upload begin 8 x.odrg 5": "busy"}
        script = Script().polls(2).send(9, "new.odrg", clip).polls(1).line(*checking).line("upload end 00000000", f"upload end {crc}")
        self.assertEqual(self.play(files, script)[2:], [refused(code) for code in checking.values()] + [refused("bad-checksum"), refused("no-upload")])


class TheCheck(Uploads):
    def test_end_is_busy_until_the_check_has_taken_a_refresh_for_the_header_each_record_and_the_end(self):
        files = small_show(ITEMS, start=6)
        for durations in ((20,), (20, 20, 20), (40,) * 9, (20,) * 30):
            clip = support.clip(51, 60, 6, durations)
            needed = len(durations) + 2
            script = Script().polls(3).send(9, "new.odrg", clip).end(clip)
            for _ in range(needed):
                script.polls(1).end(clip)
            script.line("list")
            self.play(files, script)
            self.assertEqual(self.answers("upload end"), [refused("busy")] * needed + [OK], durations)

    def test_asking_more_often_than_the_grid_does_not_hurry_the_check(self):
        files = small_show(ITEMS, start=6)
        clip = support.clip(52, 60, 6, (20,) * 6)
        script = Script().polls(3).send(9, "new.odrg", clip)
        refreshes_so_far = []
        produced = 0
        while produced < 10:
            script.lines.append(f"poll {script.time}")
            produced += 1 if script.time % 20 == 0 else 0
            script.end(clip)
            refreshes_so_far.append(produced)
            script.time += 5
        ends = replies(support.start(files, script.lines).lines)[2:]
        # The eighth refresh after the last byte ends the check: the header, six records
        # and the end. A request that produces no refresh takes no step.
        first_ok = ends.index(OK)
        self.assertEqual(refreshes_so_far[first_ok], 8, f"`upload end` succeeded after {refreshes_so_far[first_ok]} refreshes, not after 8")
        self.assertEqual(ends[:first_ok], [refused("busy")] * first_ok)
        self.assertEqual(ends[first_ok + 1:], [refused("no-upload")] * (len(ends) - first_ok - 1))
        self.play(files, script)
        self.assertEqual(self.answers("upload end"), ends)

    def test_after_a_refresh_before_which_a_grid_time_was_skipped_no_step_is_taken(self):
        files = small_show(ITEMS, start=6)
        clip = support.clip(53, 60, 6, (20,) * 4)
        script = Script().polls(3).send(9, "new.odrg", clip)
        # Six steps are needed. Of every two refreshes here the second comes late, so
        # five pairs take five steps.
        for _ in range(5):
            script.polls(1).wait(20).polls(1)
        script.end(clip).wait(20).polls(1).end(clip).polls(1).end(clip)
        self.play(files, script)
        self.assertEqual(self.answers("upload end"), [refused("busy"), refused("busy"), OK])

    def test_a_host_that_is_always_late_never_ends_the_check_and_the_upload_goes_after_60_seconds(self):
        files = small_show(ITEMS, start=6)
        clip = support.clip(54, 60, 6, (20,) * 2)
        script = Script().polls(3).send(9, "new.odrg", clip).wait(20)
        for _ in range(60000 // 40 - 2):
            script.polls(1).wait(20)
        script.end(clip).polls(1).wait(20).polls(1).end(clip)
        self.play(files, script)
        self.assertEqual(self.answers("upload end"), [refused("busy"), refused("no-upload")])
        self.assertNotIn("upload.part", self.left)

    def test_every_invalid_vector_is_a_bad_file_with_the_reason_of_the_reference_decoder(self):
        paths = sorted(INVALID.iterdir())
        self.assertGreaterEqual(len(paths), 30)
        decoded = support.decode_each([path.read_bytes() for path in paths])
        reasons = set()
        for path, by_the_core in zip(paths, decoded):
            data = path.read_bytes()
            with self.subTest(vector=path.name):
                width, height = struct.unpack_from("<HH", data, 6) if len(data) >= 10 else (0, 0)
                if not (1 <= width <= 255 and 1 <= height <= 255):
                    width, height = 5, 4
                files = {"mapping.json": support.one_leg_mapping(width, height), "show.json": support.show_text([])}
                reference = support.ReferencePlayer(files)
                # The reference player is told how many records of the file are sound, as
                # the core's decoder finds them outside a session.
                reference.sound_records[zlib.crc32(data)] = len(by_the_core.records)
                steps, reason, _ = reference._judge(data)
                script = Script().polls(2).send(9, "new.odrg", data).polls(steps - 1).end(data).polls(1).end(data).line("upload cancel", "list")
                run, left = support.start_and_keep(files, script.lines)
                self.assertEqual(replies(run.lines)[-4:], [refused("busy"), bad_file(path.name.split(".")[0]), refused("no-upload"), '{"ok":true,"items":[],"next":null}'])
                self.assertEqual(reason, path.name.split(".")[0])
                self.assertEqual(sorted(left), ["mapping.json", "show.json"])
                self.assertEqual(run.lines, reference.run(script.lines))
                reasons.add(reason)
        self.assertGreaterEqual(len(reasons), 18)

    def test_a_file_of_another_canvas_is_a_bad_file_with_size_mismatch(self):
        files = small_show(ITEMS)
        for width, height in ((60, 5), (59, 6), (6, 60), (60, 60), (1, 1)):
            clip = support.clip(55, width, height)
            script = Script().polls(2).send(9, "new.odrg", clip).end(clip).polls(1).end(clip).line("upload cancel")
            self.play(files, script)
            self.assertEqual(self.answers("upload end") + self.answers("upload cancel"), [refused("busy"), bad_file("size-mismatch"), refused("no-upload")])
        # The header is judged before the size, and the size before the body.
        wrong_size = support.clip(55, 60, 5)
        cases = ((b"ODRZ" + wrong_size[4:], "bad-magic"), (wrong_size[:-3], "size-mismatch"), (wrong_size[:16], "size-mismatch"), (wrong_size[:15], "truncated"), (b"O", "truncated"))
        for data, reason in cases:
            self.play(files, Script().polls(2).send(9, "new.odrg", data).polls(1).end(data))
            self.assertEqual(self.answers("upload end"), [bad_file(reason)], reason)

    def test_bytes_that_storage_gives_back_changed_are_a_storage_error(self):
        files = small_show(ITEMS, start=6)
        picture = bytes(range(256)) * 5
        stored = odrg.container(60, 6, None, [odrg.stored_record(picture[:1080], 20), odrg.stored_record(picture[100:1180], 40)])
        self.assertEqual(frames_of(stored), 2)
        script = Script().polls(3).upload(9, "new.odrg", stored).line("list").polls(3).line("upload cancel")
        self.play(files, script)
        self.assertEqual(self.answers("upload end"), [OK])
        plain = [line for line in self.printed if line.startswith(("refresh", "data"))]
        kept = {name: content if isinstance(content, bytes) else content.encode() for name, content in files.items()}
        for option, offset in (("--read-back-differs", len(stored) - 5), ("--read-back-differs", 40), ("--read-back-fails", 0), ("--read-back-fails", 16), ("--read-back-fails", len(stored) - 1)):
            with self.subTest(option=option, offset=offset):
                run, left = support.start_and_keep(files, script.lines, [option, str(offset)])
                given = dict(zip(script.sent, replies(run.lines)))
                self.assertEqual(given[support.upload_end(stored)], refused("storage-error"))
                self.assertEqual(len(json.loads(given["list"])["items"]), 6)
                self.assertEqual(given["upload cancel"], refused("no-upload"))
                self.assertEqual(left, kept)
                self.assertEqual([line for line in run.lines if line.startswith(("refresh", "data"))], plain)
        run, left = support.start_and_keep(files, script.lines, ["--read-back-fails", str(len(stored))])
        self.assertEqual(dict(zip(script.sent, replies(run.lines)))[support.upload_end(stored)], OK)


class Quiet(Uploads):
    def states(self, clip):
        """A script that brings an upload to each of its states."""
        half = len(clip) // 2
        return {
            "begun": Script().polls(3).line(f"upload begin 9 new.odrg {len(clip)}"),
            "some bytes": Script().polls(3).line(f"upload begin 9 new.odrg {len(clip)}", f"upload data 0 {b64(clip[:half])}"),
            "all bytes": Script().polls(3).send(9, "new.odrg", clip),
            "the check half done": Script().polls(3).send(9, "new.odrg", clip).polls(2),
            "the check done": Script().polls(3).send(9, "new.odrg", clip).check(clip),
        }

    def test_cancel_discards_the_upload_at_every_state(self):
        files = small_show(ITEMS, start=6)
        clip = support.clip(61, 60, 6, (20,) * 3)
        for state, script in self.states(clip).items():
            with self.subTest(state=state):
                script.line("upload cancel", "upload cancel", "list").polls(4).upload(9, "new.odrg", clip).line("play 9").polls(4)
                self.play(files, script, ["--trace-store"])
                self.assertEqual(self.answers("upload cancel"), [OK, refused("no-upload")])
                self.assertEqual(len(json.loads(self.answers("list")[0])["items"]), 6)
                self.assertEqual(self.answers("upload end") + self.answers("play"), [OK, OK])
                self.assertEqual(self.left["new.odrg"], clip)
                self.assertNotIn("upload.part", self.left)
                self.assertEqual(self.stored.count("remove upload.part 1"), 1)

    def test_an_upload_on_which_nothing_moves_for_60_seconds_is_discarded(self):
        files = small_show(ITEMS, start=6)
        clip = support.clip(62, 60, 6, (20,) * 3)
        states = self.states(clip)
        # The last step of the check was taken at the last refresh, 20 ms before the clock.
        moved = {"begun": 0, "some bytes": 0, "all bytes": 0, "the check done": 20}
        for state, since in moved.items():
            for quiet, kept in ((59999, True), (60000, False), (60001, False), (300000, False)):
                with self.subTest(state=state, quiet=quiet):
                    late = states[state].copy().wait(quiet - since).line("upload cancel")
                    self.play(files, late)
                    self.assertEqual(self.answers("upload cancel"), [OK if kept else refused("no-upload")])
                    self.assertNotIn("upload.part", self.left)

    def test_the_60_seconds_are_judged_by_every_call_that_carries_a_timestamp(self):
        files = small_show(ITEMS, start=6)
        begin = Script().polls(3).line("upload begin 9 new.odrg 500")
        for what in ("a refresh", "bytes without a line", "a line"):
            with self.subTest(by=what):
                script = begin.copy().wait(60000)
                if what == "a refresh":
                    script.polls(1)
                elif what == "bytes without a line":
                    script.bytes(b"sta")
                else:
                    script.line("status")
                self.play(files, script, ["--trace-store"])
                self.assertEqual(self.stored, ["write_open upload.part 1", "remove upload.part 1"])
                self.assertNotIn("upload.part", self.left)

    def test_progress_keeps_an_upload_open_for_longer_than_60_seconds(self):
        files = small_show(ITEMS, start=6)
        clip = support.clip(63, 60, 6, (20,) * 3)
        script = Script().polls(3).line(f"upload begin 9 new.odrg {len(clip)}")
        for offset in range(0, len(clip), 50):
            script.wait(50000).line(f"upload data {offset} {b64(clip[offset:offset + 50])}")
        script.wait(59900).check(clip).wait(59900).end(clip)
        self.play(files, script)
        self.assertEqual(self.answers("upload end"), [OK])
        self.assertGreater(script.time - T0, 400000)

    def test_an_animation_that_turns_unavailable_leaves_the_upload_open(self):
        files = small_show([animation(1, "one.odrg")], start=1)
        clip = support.clip(64, 60, 6)
        script = Script().polls(2).line(f"upload begin 9 new.odrg {len(clip)}", f"upload data 0 {b64(clip[:5])}").polls(60).line("status", "upload cancel", f"upload data 5 {b64(clip[5:])}")
        run, left = support.start_and_keep(files, script.lines, ["--remove-after", "one.odrg", "2", "--trace-store"])
        given = replies(run.lines)
        self.assertEqual((json.loads(given[2])["error"], json.loads(given[2])["playing"]), (None, None))
        self.assertEqual(given[3:], [OK, refused("no-upload")])
        self.assertNotIn("upload.part", left)
        self.assertIn("store remove upload.part 1", run.lines)


class TwoEntries(Uploads):
    def test_the_commands_of_an_upload_may_come_as_lines_and_as_bytes_in_any_mixture(self):
        files = small_show(ITEMS, start=6)
        clip = support.dense_clip(60, 6, 1)
        lines = support.upload_lines(9, "new.odrg", clip, 900)
        script = Script().polls(3)
        for number, line in enumerate(lines):
            if number % 2:
                script.line(line)
            else:
                data = line.encode("ascii") + b"\r\n"
                script.bytes(data[:700]).polls(1).bytes(data[700:])
        script.check(clip).bytes(support.upload_end(clip).encode() + b"\n").line("play 9").polls(5).bytes(b"list\nstatus\n")
        given = self.play(files, script)
        self.assertEqual(given[0], CHUNK)
        self.assertEqual(given[len(lines) - 1], received(len(clip)))
        self.assertEqual(given[len(lines):len(lines) + 2], [OK, OK])
        self.assertEqual((json.loads(given[-1])["playing"], json.loads(given[-1])["animation"]), ("all", 9))
        self.assertEqual(self.left["new.odrg"], clip)

    def test_playback_goes_on_as_without_the_upload_until_its_end(self):
        files = small_show(ITEMS, start=6)
        clip = support.dense_clip(60, 6, 1)
        with_upload = Script().polls(50).send(9, "new.odrg", clip, 500).polls(20).line("space", "list").check(clip).end(clip).polls(100).line("status")
        self.play(files, with_upload)
        self.assertEqual(self.answers("upload end"), [OK])
        plain = Script().polls(50 + 20 + frames_of(clip) + 2 + 100)
        without = support.start(files, plain.lines).lines
        self.assertEqual([line for line in self.printed if line.startswith(("refresh", "data"))], without)


if __name__ == "__main__":
    unittest.main()

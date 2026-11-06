import json
import pathlib
import tempfile
import time
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_messages import refusal
from .test_target import entered

OK = (200, '{"ok":true}\n')
SPACE = (200, '{"ok":true,"free":8372224,"total":10354688,"animations":2}\n')
WITH_A_CANVAS = (200, '{"ok":true,"on":true,"brightness":128,"playing":"all","animation":1,"fps":50,"error":null,"width":60,"height":6}\n')


def target(**upload):
    """A stand-in target with a canvas, two animations and room in its storage, whose
    replies to the words after `upload` are given, each a reply or a function of the
    line that gives one."""

    def answer(line):
        word = line.split(b" ")[1].decode("ascii")
        reply = upload.get(word, OK)
        return reply(line) if callable(reply) else reply

    return {"status": WITH_A_CANVAS, "list": support.LISTED, "space": SPACE, "upload": answer}


def begun(line):
    return (200, '{"ok":true,"chunk":1500,"replacing":false}\n')


def checked_after(seconds):
    """A reply to `upload end` of a target that checks the file for some seconds by the
    test's clock, counted from the first `upload end` it gets: `busy` until then, and then
    `{"ok":true}`."""
    first = []

    def answer(line):
        now = time.monotonic()
        first[:] = first or [now]
        return refusal("busy") if now - first[0] < seconds else OK

    return answer


CHECKING = "Checking the animation on the installation: "


def checking_texts(case, texts):
    """The texts of the line after the last byte, which a test of the line takes from all
    those it sampled: Sending texts until then and Checking texts from then on."""
    first = next((number for number, text in enumerate(texts) if text.startswith(CHECKING)), len(texts))
    case.assertTrue(all(text.startswith("Sending: ") for text in texts[:first]), texts)
    case.assertTrue(all(text.startswith(CHECKING) for text in texts[first:]), texts)
    return texts[first:]


def assert_counted(case, texts):
    """The Checking texts read `0:00` first and each later one a second more."""
    case.assertEqual(texts, [f"{CHECKING}0:{second:02d}" for second in range(len(texts))])
    case.assertIn(f"{CHECKING}0:02", texts)
    case.assertFalse([text for text in texts if "%" in text or "KB a second" in text])


def taken(line):
    """The reply to `upload data`: every byte of the piece received."""
    offset, data = line.split(b" ")[2:4]
    import base64

    received = int(offset) + len(base64.urlsafe_b64decode(data + b"=" * (-len(data) % 4)))
    return (200, '{"ok":true,"received":%d}\n' % received)


class Uploading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        media = pathlib.Path(cls.work.name, "media")
        media.mkdir()
        cls.media = support.make_media(media)
        cls.mapping = pathlib.Path(cls.work.name, "mapping.json")
        cls.mapping.write_text(core_support.mapping_texts()["legs-2"], encoding="utf-8")

    def emulator(self):
        folder = entered(self, emulator_support.example_show())
        started = entered(self, emulator_support.Emulator(folder))
        return started, folder

    def uploaded(self, address, **settings):
        return support.run("uploads", address=address, settings={"rows": 2, **settings}, media=self.media).seen

    def test_a_gif_is_uploaded_as_the_file_the_command_line_makes_and_plays(self):
        emulator, folder = self.emulator()
        with emulator_support.EventStream(emulator.port) as stream:
            found = self.uploaded(f"127.0.0.1:{emulator.port}", file="clip.gif", play="4 clip.odrg")
            events = stream.read_for(1)
        self.assertEqual(found["message"], "Uploaded as animation 4 clip.odrg. It plays in the playlist.")
        self.assertEqual((folder / "clip.odrg").read_bytes(), support.converted_by_the_command_line(self.media / "clip.gif", self.mapping).odrg)
        self.assertIn({"id": 4, "file": "clip.odrg", "bytes": (folder / "clip.odrg").stat().st_size, "ignored": False, "external": False, "type": "frames"}, json.loads(emulator.command("list"))["items"])
        self.assertEqual([row["id"] for row in found["after"]["rows"]], [1, 2, 4])
        self.assertEqual(found["now"], "Now 4 clip.odrg")
        self.assertEqual(emulator.status()["animation"], 4)
        lines = [entry["line"].split(" ")[:2] for entry in emulator_support.of_kind(events, "log")]
        self.assertEqual([line for line in lines if line[0] == "upload"][0], ["upload", "begin"])
        all_lines = [entry["line"] for entry in emulator_support.of_kind(events, "log")]
        ended = max(i for i, line in enumerate(all_lines) if line.startswith("upload end "))
        self.assertIn("space", all_lines[ended + 1:])
        # The check of the clip may end at the first refresh after its last byte, and the
        # whole upload between two samples of the line: Sending texts, then Checking texts.
        checking_texts(self, found["sending"])

    def test_a_video_is_uploaded_with_the_frames_of_the_command_line_and_colours_close_to_them(self):
        emulator, folder = self.emulator()
        found = self.uploaded(f"127.0.0.1:{emulator.port}", file="clip.mp4")
        self.assertEqual(found["message"], "Uploaded as animation 4 clip.odrg. It plays in the playlist.")
        ours = support.decoded_by_the_command_line((folder / "clip.odrg").read_bytes())
        theirs = support.decoded_by_the_command_line(support.converted_by_the_command_line(self.media / "clip.mp4", self.mapping).odrg)
        self.assertEqual([ms for ms, _ in ours], [ms for ms, _ in theirs])
        for (_, mine), (_, made) in zip(ours, theirs):
            self.assertEqual(len(mine), len(made))
            for a, b in zip(mine, made):
                for shift in (16, 8, 0):
                    self.assertLessEqual(abs((a >> shift & 255) - (b >> shift & 255)), 8)

    def test_an_upload_can_be_cancelled(self):
        with support.StandIn(target(begin=begun, data=taken), delay=0.3) as stand_in:
            found = self.uploaded(stand_in.address, file="long.mp4", cancel=True)
        lines = [line for _, line in stand_in.lines if line.startswith(b"upload")]
        self.assertEqual((lines[0].split(b" ")[:3], lines[-1]), ([b"upload", b"begin", b"3"], b"upload cancel"))
        self.assertNotIn(b"upload end", b" ".join(lines))
        self.assertEqual((found["uploading"], found["message"]), ("Cancelled.", None))

    def test_nothing_is_sent_while_the_app_is_away_and_the_upload_goes_on_when_it_is_back(self):
        counted = []
        with support.StandIn(target(begin=begun, data=taken), delay=0.2) as stand_in:
            steps = [lambda: counted.append(len(stand_in.lines)), lambda: counted.append(len(stand_in.lines))]
            found = support.run("uploads", address=stand_in.address, settings={"rows": 2, "file": "long.mp4", "hide": True}, media=self.media, steps=steps).seen
        self.assertEqual(len(counted), 2)
        self.assertEqual(counted[0], counted[1])
        self.assertEqual(found["message"], "Uploaded as animation 3 long.odrg. It plays in the playlist.")
        self.assertIn(b"upload end", b" ".join(line for _, line in stand_in.lines))

    def test_while_the_installation_checks_the_line_counts_the_seconds(self):
        with support.StandIn(target(begin=begun, data=taken, end=checked_after(3.5))) as stand_in:
            found = self.uploaded(stand_in.address, file="clip.gif")
        texts = checking_texts(self, found["sending"])
        assert_counted(self, texts)
        self.assertEqual(found["cancelShown"], [True] * len(texts))
        self.assertEqual(found["message"], "Uploaded as animation 3 clip.odrg. It plays in the playlist.")
        self.assertTrue(found["lineHidden"])

    def test_cancel_while_the_installation_checks(self):
        with support.StandIn(target(begin=begun, data=taken, end=refusal("busy"))) as stand_in:
            found = self.uploaded(stand_in.address, file="clip.gif", cancel="checking")
            sent = [line for _, line in stand_in.lines if line.startswith(b"upload")]
        self.assertTrue(found["checking"].startswith(CHECKING), found["checking"])
        self.assertEqual(sent[-1], b"upload cancel")
        self.assertEqual((found["uploading"], found["later"]), ("Cancelled.", "Cancelled."))
        self.assertIsNone(found["message"])

    def test_a_reply_to_the_last_piece_after_the_address_changed_writes_nothing_on_the_line(self):
        # The reply to the last piece of the first upload comes two seconds late.
        size = []
        held = []

        def begin(line):
            size[:] = [int(line.split(b" ")[4])]
            return begun(line)

        def held_once(line):
            reply = taken(line)
            if not held and json.loads(reply[1])["received"] == size[0]:
                held.append(line)
                time.sleep(2.0)
            return reply

        with support.StandIn(target(begin=begin, data=held_once, end=checked_after(2.5))) as stand_in:
            found = self.uploaded(stand_in.address, file="clip.gif", readdress=True)
        self.assertEqual(len(held), 1)
        self.assertTrue(found["ended"].startswith("Sending: "), found["ended"])
        self.assertEqual(found["afterwards"], [found["ended"]] * 6)
        assert_counted(self, checking_texts(self, found["sending"]))
        self.assertEqual(found["message"], "Uploaded as animation 3 clip.odrg. It plays in the playlist.")

    def test_a_file_that_does_not_fit_is_not_sent(self):
        tight = dict(target(begin=begun, data=taken), space=(200, '{"ok":true,"free":16000,"total":10354688,"animations":2}\n'))
        with support.StandIn(tight) as stand_in:
            found = self.uploaded(stand_in.address, file="clip.gif")
        self.assertRegex(found["message"], r"\AThe animation needs [0-9]+ KB, and the installation has 16 KB free\. \(no-space\)\Z")
        self.assertEqual([line for _, line in stand_in.lines if line.startswith(b"upload")], [])

    def test_an_end_that_is_busy_is_sent_again_until_the_target_has_checked_the_file(self):
        ends = []

        def checking(line):
            ends.append(line)
            return refusal("busy") if len(ends) < 3 else OK

        with support.StandIn(target(begin=begun, data=taken, end=checking)) as stand_in:
            found = self.uploaded(stand_in.address, file="clip.gif")
        self.assertEqual(found["message"], "Uploaded as animation 3 clip.odrg. It plays in the playlist.")
        self.assertEqual(len(ends), 3)
        self.assertEqual(len(set(ends)), 1)

    def test_each_refusal_of_an_upload_is_told_in_words(self):
        cases = (
            ({"begin": refusal("in-use")}, "That name or id is in use on the installation. The list is asked for again; upload again. (in-use)"),
            ({"begin": refusal("busy")}, "The installation is busy. Try again in a moment. (busy)"),
            ({"begin": refusal("no-space")}, r"The animation needs [0-9]+ KB, and the installation has 8373 KB free. (no-space)"),
            ({"begin": begun, "data": refusal("no-upload")}, "The installation dropped the upload, after the app was away for a minute or more. Upload again. (no-upload)"),
            ({"begin": begun, "data": refusal("bad-offset")}, "The upload did not arrive whole. Upload again. (bad-offset)"),
            ({"begin": begun, "data": taken, "end": refusal("bad-checksum")}, "The upload did not arrive whole. Upload again. (bad-checksum)"),
            ({"begin": begun, "data": taken, "end": (200, '{"ok":false,"error":"bad-file","reason":"size-mismatch"}\n')}, "The installation refused the file: size-mismatch. (bad-file)"),
            ({"begin": begun, "data": taken, "end": refusal("storage-error")}, "The installation could not use its storage. (storage-error)"),
        )
        for replies, sentence in cases:
            with self.subTest(sentence=sentence):
                with support.StandIn(target(**replies)) as stand_in:
                    found = self.uploaded(stand_in.address, file="clip.gif")
                if "[0-9]" in sentence:
                    self.assertRegex(found["message"], "\\A" + sentence.replace("(", "\\(").replace(")", "\\)").replace(".", "\\.") + "\\Z")
                else:
                    self.assertEqual(found["message"], sentence)
                self.assertEqual(found["buttons"], ["Upload to the installation"])


if __name__ == "__main__":
    unittest.main()

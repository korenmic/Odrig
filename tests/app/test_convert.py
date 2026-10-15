import math
import pathlib
import tempfile
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered


def facts(converted):
    """What the storage screen says of an animation the command line made."""
    return f"{converted.frames} frames, {converted.ms / 1000:.2f} s, {math.ceil(len(converted.odrg) / 1000)} KB"


class Converting(unittest.TestCase):
    """Against the example show on the two-leg mapping: a canvas of 60 x 6."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        cls.media = support.make_media(_made(cls.work.name))
        cls.mapping = pathlib.Path(cls.work.name, "mapping.json")
        cls.mapping.write_text(core_support.mapping_texts()["legs-2"], encoding="utf-8")
        cls.show = cls.enterClassContext(emulator_support.example_show())
        cls.emulator = cls.enterClassContext(emulator_support.Emulator(cls.show))
        cls.address = f"127.0.0.1:{cls.emulator.port}"

    def made(self, **settings):
        return support.run("converts", address=self.address, settings={"rows": 2, **settings}, media=self.media).seen

    def test_a_gif_with_each_fit_is_the_animation_the_command_line_makes(self):
        for fit in ("fill", "fit", "stretch"):
            with self.subTest(fit=fit):
                found = self.made(file="clip.gif", fit=fit.capitalize())
                self.assertEqual(found["facts"], facts(support.converted_by_the_command_line(self.media / "clip.gif", self.mapping, fit)))
                self.assertEqual((found["name"], found["fits"], found["message"]), ("clip.gif", [f"fit-{fit}"], None))
                self.assertEqual(found["preview"], [60, 6])

    def test_a_part_of_a_gif(self):
        found = self.made(file="clip.gif", start="0.05", length="0.1")
        self.assertEqual(found["facts"], facts(support.converted_by_the_command_line(self.media / "clip.gif", self.mapping, "fill", "0.05", "0.1")))

    def test_fill_is_chosen_at_first_and_each_fit_says_what_it_does(self):
        found = self.made(file="clip.gif")
        self.assertEqual((found["fits"], found["fitSays"]), (["fit-fill"], "The picture covers the whole canvas; what does not fit is cut off at two sides."))

    def test_a_video_has_the_frames_and_the_length_the_command_line_gives_it(self):
        for fit, start, length in (("fill", None, None), ("fit", "0.1", "0.2")):
            with self.subTest(fit=fit):
                settings = {"file": "clip.mp4", "video": True, "fit": fit.capitalize()}
                if start is not None:
                    settings.update(start=start, length=length)
                found = self.made(**settings)
                cli = support.converted_by_the_command_line(self.media / "clip.mp4", self.mapping, fit, start, length)
                self.assertEqual(found["facts"].rsplit(", ", 1)[0], facts(cli).rsplit(", ", 1)[0])
                self.assertEqual(found["name"], "clip.mp4, 0.40 s")

    def test_making_can_be_stopped(self):
        found = self.made(file="long.mp4", video=True, stop=True)
        self.assertEqual((found["making"], found["facts"], found["stopShown"]), ("Stopped.", None, None))

    def test_a_part_that_is_no_number_or_not_inside_the_file_is_told_in_words(self):
        found = self.made(file="clip.gif", length="half")
        self.assertEqual(found["message"], "Write the start and the length in seconds, like 2.5, and leave the length empty for the rest of the file. (bad-part)")
        found = self.made(file="clip.gif", start="5")
        self.assertEqual(found["message"], "The part does not lie inside the file. Make the start earlier or the length shorter. (bad-range)")
        for start, length in (("5", ""), ("0.2", "0.5")):
            with self.subTest(start=start, length=length):
                found = self.made(file="clip.mp4", video=True, start=start, length=length)
                self.assertEqual(found["message"], "The part does not lie inside the file. Make the start earlier or the length shorter. (bad-range)")

    def test_a_file_the_phone_cannot_read_is_told_in_words(self):
        found = self.made(file="broken.mp4")
        self.assertEqual(found["message"], "The phone cannot read this file as a video or a GIF. (unreadable-media)")


class WithoutACanvas(unittest.TestCase):
    def test_a_target_that_reports_no_canvas_cannot_be_converted_for(self):
        work = entered(self, tempfile.TemporaryDirectory())
        media = support.make_media(_made(work))
        with support.StandIn(support.SOUND) as target:
            found = support.run("converts", address=target.address, settings={"rows": 2, "file": "clip.gif"}, media=media).seen
        self.assertEqual(found["message"], "The installation has no usable mapping, so the app does not know the canvas to convert for. (no-canvas)")


def _made(work):
    folder = pathlib.Path(work, "media")
    folder.mkdir()
    return folder


if __name__ == "__main__":
    unittest.main()

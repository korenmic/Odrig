import tempfile
import unittest
from pathlib import Path

import av
import numpy

from . import media_fixtures, quiet, support

LEGS_2 = support.ROOT / "mapping" / "legs-2.json"
C = media_fixtures.COLOURS
REFUSED = "error: unreadable-media: "
TITLE = b"TITLETITLETITLE"


def write_titled_video(path):
    """A video of three frames whose metadata holds `TITLE`."""
    with av.open(str(path), "w") as container:
        container.metadata["title"] = TITLE.decode()
        stream = container.add_stream("mpeg4", rate=media_fixtures.VIDEO_RATE)
        stream.width, stream.height, stream.pix_fmt = 16, 16, "yuv420p"
        for level in (0, 80, 160):
            frame = av.VideoFrame.from_ndarray(numpy.full((16, 16, 3), level, numpy.uint8), format="rgb24")
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


class Damaged(unittest.TestCase):
    """Files that `import` cannot read are refused with a reason, each in a child that a
    fault of memory would end quietly."""

    @classmethod
    def setUpClass(cls):
        folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(folder.cleanup)
        cls.folder = Path(folder.name)

    def refused(self, source):
        result = quiet.run_tool("import", source, self.folder / "out.json", "--mapping", LEGS_2)
        self.assertEqual((result.status, result.out), (1, ""), result.err)
        self.assertTrue(result.err.startswith(REFUSED), result.err)
        self.assertEqual(len(result.err.splitlines()), 1, result.err)
        self.assertNotIn("Traceback", result.err)
        return result.err

    def test_a_video_whose_first_stream_has_no_decoder_is_refused(self):
        whole = self.folder / "whole.mp4"
        media_fixtures.write_video(whole, C)
        cut = self.folder / "no-decoder.mp4"
        cut.write_bytes(whole.read_bytes()[:993])
        self.assertIn("the video stream has no decoder", self.refused(cut))

    def test_a_video_whose_metadata_is_not_utf_8_is_refused(self):
        whole = self.folder / "titled.mp4"
        write_titled_video(whole)
        data = bytearray(whole.read_bytes())
        place = data.find(TITLE)
        self.assertGreater(place, 0)
        data[place:place + 4] = b"\xff\xfe\xfd\xfc"
        damaged = self.folder / "bad-title.mp4"
        damaged.write_bytes(data)
        self.assertIn("the video cannot be decoded", self.refused(damaged))

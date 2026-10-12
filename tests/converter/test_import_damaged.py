import tempfile
import unittest
from pathlib import Path

from . import media_fixtures, quiet, support

LEGS_2 = support.ROOT / "mapping" / "legs-2.json"
C = media_fixtures.COLOURS
REFUSED = "error: unreadable-media: "


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

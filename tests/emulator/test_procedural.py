import json
import pathlib
import tempfile
import unittest

from emulator import binding, host
from odrig import mapping, odrgx
from tests.core import support as core_support
from tests.core.test_texts import png_pixels

from . import support

PICTURES = support.ROOT / "tests" / "vectors" / "procedural"
# The first poll comes after 2^32 milliseconds, so that any 32-bit timestamp lies before it.
BASE = 2**32 + 1000
MASK = 0xFFFFFFFF


def unmix(value):
    """The inverse of MurmurHash3's finalizer, `mix`."""
    value ^= value >> 16
    value = (value * 0x7ED1B41D) & MASK
    value ^= (value >> 13) ^ (value >> 26)
    value = (value * 0xA5CB9243) & MASK
    return value ^ (value >> 16)


def leds_of(picture, text):
    """The LED data a picture gives on the legs of a mapping, at full brightness."""
    canvas = mapping.loads(text.encode("utf-8"))
    return b"".join(picture[3 * place:3 * place + 3] for leg in canvas.legs for place in core_support.led_pixels(canvas, leg))


class ThePicturesOnTheLeds(unittest.TestCase):
    def started(self, data):
        """The core of the emulator on a show of one animation, a container of the vectors,
        on the target's mapping or, for another canvas, a mapping of one leg."""
        header = odrgx.read_header(data)
        if (header.width, header.height) == (60, 60):
            text = (support.ROOT / "mapping" / "legs-20.json").read_text(encoding="utf-8")
        else:
            text = core_support.one_leg_mapping(header.width, header.height)
        show = json.dumps({"version": 1, "brightness": 255, "items": [{"id": 1, "file": "a.odrgx"}]})
        folder = support.installed(pathlib.Path(support.entered(self, tempfile.TemporaryDirectory())), {"mapping.json": text, "show.json": show, "a.odrgx": data})
        files = host.FolderHost(folder)
        self.addCleanup(files.close)
        core = binding.Core(support.LIBRARY, files)
        self.assertIsNone(core.error())
        return core, text

    def test_unmix_undoes_mix(self):
        for value in (0, 1, 0xDEADBEEF, MASK, 123456789):
            self.assertEqual(unmix(core_support.mix(value)), value)
            self.assertEqual(core_support.mix(unmix(value)), value)

    def test_every_reference_picture_is_on_the_leds_at_its_time(self):
        manifest = json.loads((PICTURES / "manifest.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(manifest), 35)
        for entry in manifest:
            with self.subTest(picture=entry["picture"]):
                data = (support.ROOT / "tests" / "vectors" / entry["file"]).read_bytes()
                core, text = self.started(data)
                self.assertTrue(core.poll(BASE))
                start = BASE
                if "seed" in entry:
                    # A turn of the clock that begins at the next refresh, after a poll whose
                    # timestamp brings the noise to what gives that turn the seed of the picture.
                    noise = core_support.mix(BASE & MASK)
                    start = BASE + 20
                    wanted = unmix(entry["seed"]) ^ core_support.mix((1 ^ start) & MASK)
                    before = unmix(wanted) ^ (start & MASK)
                    stirred = unmix(before) ^ noise
                    self.assertEqual(core.command(BASE + 10, b"play 1"), b'{"ok":true}\n')
                    self.assertFalse(core.poll(stirred))
                    self.assertTrue(core.poll(start))
                    self.assertEqual(json.loads(core.command(start, b"status"))["seed"], entry["seed"])
                if entry["ms"] != 0 or "seed" not in entry:
                    self.assertTrue(core.poll(start + entry["ms"]) or entry["ms"] == 0)
                width, height, pixels = png_pixels(PICTURES / entry["picture"])
                self.assertEqual(core.frame(), leds_of(pixels, text))

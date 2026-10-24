import json
import unittest

from odrig import errors, jsonframes, odrg, odrgx, show

from . import support

FOLDER = support.ROOT / "tests" / "vectors" / "containers"


def reason_of(data):
    try:
        odrgx.decode_frames(data)
    except errors.Rejection as rejection:
        return rejection.reason
    return None


class Containers(unittest.TestCase):
    def test_a_valid_container_of_frames_gives_the_frames_of_its_odrg_file(self):
        paths = sorted((FOLDER / "valid").glob("*.odrgx"))
        self.assertGreaterEqual(len(paths), 3)
        for path in paths:
            with self.subTest(vector=path.name):
                header, decoded = odrgx.decode_frames(path.read_bytes())
                expected = jsonframes.loads(path.with_suffix(".json").read_bytes())
                self.assertEqual((header.width, header.height), (expected.width, expected.height))
                self.assertEqual(list(decoded.records), [tuple(frame) for frame in expected.frames])
                self.assertEqual(header.loop_ms, sum(ms for ms, _ in expected.frames))
                self.assertEqual(odrgx.frames_of(path.read_bytes()), odrgx.payload_of(path.read_bytes()))

    def test_an_invalid_container_is_refused_with_the_reason_of_its_name(self):
        paths = sorted((FOLDER / "invalid").iterdir())
        self.assertGreaterEqual(len(paths), 12)
        for path in paths:
            with self.subTest(vector=path.name):
                self.assertEqual(reason_of(path.read_bytes()), path.name.split(".")[0])

    def test_an_odrg_file_is_no_container(self):
        data = (support.ROOT / "tests" / "vectors" / "valid" / "durations.odrg").read_bytes()
        self.assertFalse(odrgx.is_container(data))
        self.assertEqual(odrgx.frames_of(data), data)
        self.assertEqual(reason_of(data), errors.BAD_MAGIC)

    def test_wrap_writes_the_header_the_converter_writes(self):
        data = (FOLDER / "valid" / "frames.durations.odrgx").read_bytes()
        header, decoded = odrgx.decode_frames(data)
        payload = odrgx.payload_of(data)
        self.assertEqual(odrgx.wrap(1, header.width, header.height, header.loop_ms, payload), data)
        self.assertEqual(odrg.decode(payload), decoded)


class ShowNames(unittest.TestCase):
    def show(self, name):
        return json.dumps({"version": 1, "brightness": 9, "items": [{"id": 1, "file": name}]}).encode()

    def test_a_show_may_name_odrgx_files(self):
        self.assertEqual(show.loads(self.show("clip.odrgx")).items[0].file, "clip.odrgx")
        self.assertEqual(show.loads(self.show("clip.odrg")).items[0].file, "clip.odrg")

    def test_another_ending_is_refused_and_both_endings_are_named(self):
        with self.assertRaises(errors.Rejection) as caught:
            show.loads(self.show("clip.odrgy"))
        self.assertEqual(caught.exception.reason, errors.SHOW_MALFORMED)
        self.assertTrue(caught.exception.detail.endswith("ending in .odrg or .odrgx"))


if __name__ == "__main__":
    unittest.main()

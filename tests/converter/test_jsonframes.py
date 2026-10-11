import json
import re
import tempfile
import unittest
from pathlib import Path

from odrig import errors, jsonframes, strictjson

from . import support

RED, GREEN, BLUE, BLACK = b"\xff\x00\x00", b"\x00\xff\x00", b"\x00\x00\xff", b"\x00\x00\x00"


def source(version=1, width=2, height=1, frames=None, **more):
    """The bytes of a JSON frames file; `None` leaves a member out."""
    if frames is None:
        frames = [{"ms": 20, "pixels": [0, 255]}]
    top = {"version": version, "width": width, "height": height, "frames": frames, **more}
    return json.dumps({name: value for name, value in top.items() if value is not ...}).encode()


def reason_of(data):
    try:
        jsonframes.loads(data)
    except errors.Rejection as rejection:
        return rejection.reason
    return None


class TheExampleOfTheFormatDocument(unittest.TestCase):
    def setUp(self):
        text = (support.ROOT / "docs" / "format.md").read_text(encoding="utf-8")
        self.example = re.search(r"```json\n(.*?)```", text, re.DOTALL).group(1).encode()

    def test_it_is_accepted_with_its_canvas_durations_and_pictures(self):
        animation = jsonframes.loads(self.example)
        self.assertEqual((animation.width, animation.height), (3, 2))
        first = RED + BLACK + BLACK + BLACK + BLACK + BLUE
        second = BLACK + BLACK + BLACK + BLACK + GREEN + BLACK
        self.assertEqual(animation.frames, ((500, first), (500, second)))

    def test_red_is_at_1_1_and_blue_at_3_2(self):
        _, picture = jsonframes.loads(self.example).frames[0]
        width = 3

        def at(x, y):
            p = (y - 1) * width + (x - 1)
            return picture[3 * p:3 * p + 3]

        self.assertEqual(at(1, 1), RED)
        self.assertEqual(at(3, 2), BLUE)
        self.assertEqual(at(2, 2), BLACK)


class Accepted(unittest.TestCase):
    def test_a_minimal_file(self):
        animation = jsonframes.loads(source())
        self.assertEqual(animation, jsonframes.Animation(2, 1, ((20, BLACK + BLUE),)))

    def test_consecutive_frames_with_identical_pixels_are_kept_as_listed(self):
        frames = [{"ms": 20, "pixels": [7, 7]}, {"ms": 40, "pixels": [7, 7]}]
        animation = jsonframes.loads(source(frames=frames))
        self.assertEqual([ms for ms, _ in animation.frames], [20, 40])

    def test_the_largest_colour_and_a_long_duration(self):
        frames = [{"ms": 10 ** 12, "pixels": [16777215, 0]}]
        animation = jsonframes.loads(source(frames=frames))
        self.assertEqual(animation.frames, ((10 ** 12, b"\xff\xff\xff" + BLACK),))

    def test_white_space_around_the_value(self):
        self.assertIsNone(reason_of(b" \t\r\n" + source() + b"\n\n"))

    def test_members_in_any_order(self):
        data = b'{"frames": [{"pixels": [1, 2], "ms": 5}], "height": 1, "width": 2, "version": 1}'
        self.assertEqual(jsonframes.loads(data).frames, ((5, b"\x00\x00\x01\x00\x00\x02"),))


class Rejected(unittest.TestCase):
    def check(self, expected, data):
        self.assertEqual(reason_of(data), expected, data[:80])

    def test_bad_json_not_utf_8(self):
        self.check("bad-json", source().replace(b'"ms"', b'"m\xff"'))
        self.check("bad-json", source().decode().encode("utf-16"))

    def test_bad_json_byte_order_mark(self):
        self.check("bad-json", b"\xef\xbb\xbf" + source())

    def test_bad_json_not_one_json_value(self):
        self.check("bad-json", b"")
        self.check("bad-json", b"   ")
        self.check("bad-json", source() + source())
        self.check("bad-json", source() + b"x")
        self.check("bad-json", source()[:-1])
        self.check("bad-json", b"{'version': 1}")
        self.check("bad-json", source().replace(b"255", b"NaN"))
        self.check("bad-json", source().replace(b"255", b"Infinity"))
        self.check("bad-json", source().replace(b"255", b"0x10"))
        self.check("bad-json", source().replace(b"255]", b"255,]"))

    def test_bad_json_repeated_member_name(self):
        self.check("bad-json", b'{"version": 1, "version": 1, "width": 2, "height": 1, "frames": []}')
        self.check(
            "bad-json",
            b'{"version": 1, "width": 2, "height": 1, "frames": [{"ms": 1, "ms": 1, "pixels": [0, 0]}]}',
        )

    def test_bad_json_top_level_is_not_an_object(self):
        self.check("bad-json", b"[]")
        self.check("bad-json", b"1")
        self.check("bad-json", b'"version"')
        self.check("bad-json", b"null")

    def test_bad_json_nested_too_deeply(self):
        self.check("bad-json", b"[" * 100000 + b"]" * 100000)

    def test_missing_member_at_the_top_level(self):
        self.check("missing-member", source(version=...))
        self.check("missing-member", source(width=...))
        self.check("missing-member", source(height=...))
        self.check("missing-member", source(frames=...))
        self.check("missing-member", b"{}")

    def test_missing_member_in_a_frame(self):
        self.check("missing-member", source(frames=[{"pixels": [0, 0]}]))
        self.check("missing-member", source(frames=[{"ms": 20}]))
        self.check("missing-member", source(frames=[{}]))

    def test_bad_type_number_with_a_fraction_or_an_exponent(self):
        self.check("bad-type", source().replace(b'"width": 2', b'"width": 2.0'))
        self.check("bad-type", source().replace(b'"width": 2', b'"width": 2e0'))
        self.check("bad-type", source().replace(b'"version": 1', b'"version": 1.0'))
        self.check("bad-type", source().replace(b'"ms": 20', b'"ms": 20.0'))
        self.check("bad-type", source().replace(b"255", b"255.0"))
        self.check("bad-type", source().replace(b"255", b"1E2"))

    def test_bad_type_true_and_false_are_not_integers(self):
        self.check("bad-type", source(version=True))
        self.check("bad-type", source(width=True, frames=[{"ms": 20, "pixels": [0]}]))
        self.check("bad-type", source(height=True))
        self.check("bad-type", source(frames=[{"ms": True, "pixels": [0, 0]}]))
        self.check("bad-type", source(frames=[{"ms": 20, "pixels": [True, 0]}]))
        self.check("bad-type", source(frames=[{"ms": 20, "pixels": [0, False]}]))

    def test_bad_type_other_values(self):
        self.check("bad-type", source(version="1"))
        self.check("bad-type", source(width="2"))
        self.check("bad-type", source(height=None))
        self.check("bad-type", source(frames={}))
        self.check("bad-type", source(frames="frames"))
        self.check("bad-type", source(frames=[[20, [0, 0]]]))
        self.check("bad-type", source(frames=[7]))
        self.check("bad-type", source(frames=[{"ms": "20", "pixels": [0, 0]}]))
        self.check("bad-type", source(frames=[{"ms": 20, "pixels": "00"}]))
        self.check("bad-type", source(frames=[{"ms": 20, "pixels": {"0": 0, "1": 0}}]))
        self.check("bad-type", source(frames=[{"ms": 20, "pixels": [0, "0"]}]))
        self.check("bad-type", source(frames=[{"ms": 20, "pixels": [None, 0]}]))
        self.check("bad-type", source(frames=[{"ms": 20, "pixels": [[0], 0]}]))

    def test_bad_version(self):
        self.check("bad-version", source(version=2))
        self.check("bad-version", source(version=0))
        self.check("bad-version", source(version=-1))

    def test_bad_version_is_reported_before_any_other_member_is_checked(self):
        self.check("bad-version", source(version=2, extra=True))
        self.check("bad-version", source(version=2, width=...))
        self.check("bad-version", source(version=2, width=0, frames=[]))
        self.check("bad-version", b'{"frames": 7, "extra": 1, "version": 2}')

    def test_unknown_member(self):
        self.check("unknown-member", source(fps=50))
        self.check("unknown-member", source(frames=[{"ms": 20, "pixels": [0, 0], "name": "a"}]))
        self.check("unknown-member", source(Version=1))

    def test_out_of_range(self):
        self.check("out-of-range", source(width=0, frames=[{"ms": 20, "pixels": []}]))
        self.check("out-of-range", source(height=0, frames=[{"ms": 20, "pixels": []}]))
        self.check("out-of-range", source(width=-2))
        self.check("out-of-range", source(frames=[{"ms": 0, "pixels": [0, 0]}]))
        self.check("out-of-range", source(frames=[{"ms": -20, "pixels": [0, 0]}]))
        self.check("out-of-range", source(frames=[{"ms": 20, "pixels": [-1, 0]}]))
        self.check("out-of-range", source(frames=[{"ms": 20, "pixels": [0, 16777216]}]))
        self.check("out-of-range", source().replace(b"255", b"9" * 5000))
        self.check("out-of-range", source().replace(b"255", b"-" + b"9" * 5000))

    def test_no_frames(self):
        self.check("no-frames", source(frames=[]))

    def test_bad_pixel_count(self):
        self.check("bad-pixel-count", source(frames=[{"ms": 20, "pixels": [0]}]))
        self.check("bad-pixel-count", source(frames=[{"ms": 20, "pixels": [0, 0, 0]}]))
        self.check("bad-pixel-count", source(frames=[{"ms": 20, "pixels": []}]))
        self.check("bad-pixel-count", source(width=3, height=2))


class TheFirstDefectIsReported(unittest.TestCase):
    def check(self, expected, data):
        self.assertEqual(reason_of(data), expected)

    def test_a_missing_member_before_an_unknown_one(self):
        self.check("missing-member", source(height=..., extra=1))

    def test_the_canvas_before_the_frames(self):
        self.check("out-of-range", source(width=0, frames=[]))
        self.check("bad-type", source(height="1", frames=[{"ms": 0}]))

    def test_an_earlier_frame_before_a_later_one(self):
        frames = [{"ms": 20, "pixels": [0, 16777216]}, {"ms": 20, "pixels": [0, "0"]}]
        self.check("out-of-range", source(frames=frames))
        self.check("bad-type", source(frames=frames[::-1]))

    def test_within_a_frame_members_then_ms_then_count_then_pixels(self):
        self.check("unknown-member", source(frames=[{"ms": 0, "pixels": [0], "x": 1}]))
        self.check("out-of-range", source(frames=[{"ms": 0, "pixels": [0]}]))
        self.check("bad-pixel-count", source(frames=[{"ms": 20, "pixels": ["0"]}]))

    def test_an_earlier_pixel_before_a_later_one(self):
        self.check("out-of-range", source(frames=[{"ms": 20, "pixels": [-1, True]}]))
        self.check("bad-type", source(frames=[{"ms": 20, "pixels": [True, -1]}]))


class CanonicalForm(unittest.TestCase):
    ANIMATION = jsonframes.Animation(
        3,
        2,
        (
            (500, RED + BLACK + BLACK + BLACK + BLACK + BLUE),
            (500, BLACK + BLACK + BLACK + BLACK + GREEN + BLACK),
        ),
    )
    BYTES = (
        b"{\n"
        b'  "version": 1,\n'
        b'  "width": 3,\n'
        b'  "height": 2,\n'
        b'  "frames": [\n'
        b'    {"ms": 500, "pixels": [16711680, 0, 0, 0, 0, 255]},\n'
        b'    {"ms": 500, "pixels": [0, 0, 0, 0, 65280, 0]}\n'
        b"  ]\n"
        b"}\n"
    )

    def test_the_bytes_of_a_known_animation(self):
        self.assertEqual(jsonframes.dumps(self.ANIMATION), self.BYTES)

    def test_one_frame(self):
        one = jsonframes.Animation(1, 1, ((20, b"\x01\x02\x03"),))
        expected = (
            b'{\n  "version": 1,\n  "width": 1,\n  "height": 1,\n  "frames": [\n'
            b'    {"ms": 20, "pixels": [66051]}\n  ]\n}\n'
        )
        self.assertEqual(jsonframes.dumps(one), expected)

    def test_no_byte_order_mark_no_carriage_return_one_line_per_frame(self):
        data = jsonframes.dumps(self.ANIMATION)
        self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", data)
        self.assertEqual(data.count(b'{"ms"'), 2)
        self.assertEqual(sum(1 for line in data.split(b"\n") if b'"ms"' in line), 2)

    def test_members_are_in_the_order_of_the_format_document(self):
        text = jsonframes.dumps(self.ANIMATION).decode()
        positions = [text.index(f'"{name}"') for name in ("version", "width", "height", "frames")]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(text.index('"ms"'), text.index('"pixels"'))

    def test_consecutive_identical_pictures_are_written_as_one_frame(self):
        picture, other = RED + BLUE, BLUE + RED
        frames = ((20, picture), (40, picture), (20, other), (20, picture), (60, picture), (20, picture))
        written = jsonframes.loads(jsonframes.dumps(jsonframes.Animation(2, 1, frames)))
        self.assertEqual(written.frames, ((60, picture), (20, other), (100, picture)))

    def test_merged_joins_only_neighbours(self):
        a, b = RED, BLUE
        self.assertEqual(jsonframes.merged([(1, a), (2, a), (3, b), (4, a)]), [(3, a), (3, b), (4, a)])
        self.assertEqual(jsonframes.merged([(5, a)]), [(5, a)])
        self.assertEqual(jsonframes.merged([]), [])

    def test_reading_what_was_written_gives_the_same_animation(self):
        self.assertEqual(jsonframes.loads(self.BYTES), self.ANIMATION)
        self.assertEqual(jsonframes.loads(jsonframes.dumps(self.ANIMATION)), self.ANIMATION)

    def test_writing_twice_gives_identical_bytes(self):
        self.assertEqual(jsonframes.dumps(self.ANIMATION), jsonframes.dumps(self.ANIMATION))

    def test_an_animation_that_is_not_one_is_a_programming_error(self):
        for broken in (
            jsonframes.Animation(1, 1, ()),
            jsonframes.Animation(1, 1, ((0, BLACK),)),
            jsonframes.Animation(2, 1, ((20, BLACK),)),
            jsonframes.Animation(0, 1, ((20, b""),)),
        ):
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                jsonframes.dumps(broken)


class Files(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def test_write_then_read(self):
        path = self.folder / "clip.json"
        jsonframes.write(path, CanonicalForm.ANIMATION)
        self.assertEqual(path.read_bytes(), CanonicalForm.BYTES)
        self.assertEqual(jsonframes.read(path), CanonicalForm.ANIMATION)

    def test_two_writes_give_identical_files(self):
        first, second = self.folder / "a.json", self.folder / "b.json"
        jsonframes.write(first, CanonicalForm.ANIMATION)
        jsonframes.write(second, CanonicalForm.ANIMATION)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_a_rejection_names_the_file(self):
        path = self.folder / "broken.json"
        path.write_bytes(source(version=2))
        with self.assertRaises(errors.Rejection) as caught:
            jsonframes.read(path)
        self.assertEqual(caught.exception.reason, "bad-version")
        self.assertIn(str(path), caught.exception.detail)

    def test_a_missing_file_is_not_found(self):
        with self.assertRaises(errors.Rejection) as caught:
            jsonframes.read(self.folder / "absent.json")
        self.assertEqual(caught.exception.reason, "not-found")


class Colours(unittest.TestCase):
    def test_colours_of_a_picture(self):
        self.assertEqual(jsonframes.colours(RED + GREEN + BLUE + b"\x01\x02\x03"), (16711680, 65280, 255, 66051))

    def test_colour_count_is_over_all_frames(self):
        frames = [(20, RED + BLACK), (20, BLACK + BLUE), (20, RED + BLUE)]
        self.assertEqual(jsonframes.colour_count(frames), 3)
        self.assertEqual(jsonframes.colour_count([(20, BLACK + BLACK)]), 1)


class StrictJsonHelpers(unittest.TestCase):
    def reason(self, call, *arguments, **named):
        with self.assertRaises(errors.Rejection) as caught:
            call(*arguments, **named)
        return caught.exception.reason

    def test_integer(self):
        self.assertEqual(strictjson.integer(5, 1, 5), 5)
        self.assertEqual(strictjson.integer(-3), -3)
        self.assertEqual(self.reason(strictjson.integer, 0, 1, 5), "out-of-range")
        self.assertEqual(self.reason(strictjson.integer, 6, 1, 5), "out-of-range")
        self.assertEqual(self.reason(strictjson.integer, True, 0, 5), "bad-type")
        self.assertEqual(self.reason(strictjson.integer, "5", 0, 5), "bad-type")
        self.assertEqual(self.reason(strictjson.integer, strictjson.loads(b"5.0"), 0, 5), "bad-type")
        self.assertEqual(self.reason(strictjson.integer, strictjson.loads(b"5e0"), 0, 5), "bad-type")

    def test_members(self):
        strictjson.members({"a": 1, "b": 2}, ("a",), ("b",))
        strictjson.members({"a": 1}, ("a",), ("b",))
        self.assertEqual(self.reason(strictjson.members, {"b": 2}, ("a",), ("b",)), "missing-member")
        self.assertEqual(self.reason(strictjson.members, {"a": 1, "c": 3}, ("a",), ("b",)), "unknown-member")
        self.assertEqual(self.reason(strictjson.members, [], ("a",)), "bad-type")

    def test_loads_gives_plain_values(self):
        self.assertEqual(strictjson.loads(b'{"a": [1, "x", null, true], "b": -0}'), {"a": [1, "x", None, True], "b": 0})


if __name__ == "__main__":
    unittest.main()

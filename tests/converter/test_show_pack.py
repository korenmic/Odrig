import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from odrig import errors, jsonframes, odrg, show

from . import support

EXAMPLE_SHOW = support.ROOT / "shows" / "example" / "show.json"
LEGS_2 = support.ROOT / "mapping" / "legs-2.json"
TARGET = support.ROOT / "mapping" / "legs-20.json"
ANIMATIONS = support.ROOT / "animations"

# A column-leg mapping for a canvas of 5 x 4, laid out as no tool would write it.
COLUMN_LEGS = (
    b'{\r\n  "version": 1,\n\t"height": 4,\n  "legs": [\n'
    b'    {"leg": 1, "pin": 5, "first_led": "bottom", "columns": [1, 2, 3]},\n'
    b'    {"columns": [5,4], "first_led": "top", "pin": 6, "leg": 2}\n  ]\n}\n\n'
)


def source(version=1, brightness=128, items=None, start=..., **more):
    """The bytes of a show file; `...` leaves a member out."""
    if items is None:
        items = [{"id": 1, "file": "a.odrg"}]
    top = {"version": version, "brightness": brightness, "items": items, "start": start, **more}
    return json.dumps({name: value for name, value in top.items() if value is not ...}).encode()


def reason_of(data):
    try:
        show.loads(data)
    except errors.Rejection as rejection:
        return rejection.reason
    return None


class Accepted(unittest.TestCase):
    def test_the_example_of_the_show_document(self):
        text = (support.ROOT / "docs" / "show.md").read_text(encoding="utf-8")
        example = re.search(r"```json\n(.*?)```", text, re.DOTALL).group(1).encode()
        result = show.loads(example)
        self.assertEqual(result.brightness, 128)
        self.assertEqual(result.start, 3)
        self.assertEqual(
            result.items,
            (
                show.Item(1, "hello.odrg", None, None),
                show.Item(2, "dvd.odrg", None, None),
                show.Item(3, None, (1, 2), 15),
            ),
        )

    def test_a_show_without_start(self):
        self.assertIsNone(show.loads(source()).start)

    def test_the_limits(self):
        items = [
            {"id": 1, "file": ".odrg"},
            {"id": 65535, "file": "a-b_c.9" + "x" * 20 + ".odrg"},
            {"id": 7, "cycle": [1, 65535, 1], "seconds": 1},
            {"id": 8, "cycle": [1], "seconds": 65535},
        ]
        for brightness in (0, 255):
            result = show.loads(source(brightness=brightness, items=items, start=8))
            self.assertEqual(result.brightness, brightness)
        self.assertEqual(len(result.items[1].file), 32)

    def test_files_are_listed_once_in_the_order_of_first_use(self):
        items = [
            {"id": 1, "file": "b.odrg"},
            {"id": 2, "file": "a.odrg"},
            {"id": 3, "cycle": [2, 1], "seconds": 5},
            {"id": 4, "file": "b.odrg"},
        ]
        self.assertEqual(show.files(show.loads(source(items=items))), ["b.odrg", "a.odrg"])


class Malformed(unittest.TestCase):
    def check(self, data, inner=None):
        with self.assertRaises(errors.Rejection) as caught:
            show.loads(data)
        self.assertEqual(caught.exception.reason, "show-malformed", data)
        if inner is not None:
            self.assertIn(inner, caught.exception.detail)

    def test_not_strict_json(self):
        self.check(b"", "bad-json")
        self.check(b"\xef\xbb\xbf" + source(), "bad-json")
        self.check(source() + b"{}", "bad-json")
        self.check(b"[]", "bad-json")
        self.check(b'{"version": 1, "brightness": 1, "brightness": 1, "items": [{"id": 1, "file": "a.odrg"}]}', "bad-json")

    def test_members_other_than_the_listed_ones(self):
        self.check(source(fps=50), "unknown-member")
        self.check(source(version=...), "missing-member")
        self.check(source(brightness=...), "missing-member")
        self.check(source(items=...), "missing-member")

    def test_a_version_other_than_1(self):
        self.check(source(version=2), "bad-version")
        self.check(source(version=2, fps=50), "bad-version")
        self.check(source(version="1"), "bad-type")

    def test_brightness_outside_0_to_255(self):
        self.check(source(brightness=-1), "out-of-range")
        self.check(source(brightness=256), "out-of-range")
        self.check(source(brightness="128"), "bad-type")
        self.check(source().replace(b"128", b"128.0"), "bad-type")

    def test_no_items(self):
        self.check(source(items=[]), "items is empty")
        self.check(source(items={}), "bad-type")
        self.check(source(items=[1]), "bad-type")

    def test_an_item_that_is_neither_kind(self):
        self.check(source(items=[{"id": 1}]), "missing-member")
        self.check(source(items=[{"id": 1, "file": "a.odrg", "cycle": [1], "seconds": 5}]), "unknown-member")
        self.check(source(items=[{"id": 1, "file": "a.odrg", "seconds": 5}]), "unknown-member")
        self.check(source(items=[{"id": 1, "file": "a.odrg", "name": "A"}]), "unknown-member")
        self.check(source(items=[{"id": 1, "cycle": [1]}]), "missing-member")
        self.check(source(items=[{"id": 1, "seconds": 5}]), "missing-member")
        self.check(source(items=[{"file": "a.odrg"}]), "missing-member")
        self.check(source(items=[{"cycle": [1], "seconds": 5}]), "missing-member")

    def test_an_id_outside_1_to_65535(self):
        self.check(source(items=[{"id": 0, "file": "a.odrg"}]), "out-of-range")
        self.check(source(items=[{"id": 65536, "file": "a.odrg"}]), "out-of-range")
        self.check(source(items=[{"id": "1", "file": "a.odrg"}]), "bad-type")
        self.check(source(items=[{"id": True, "file": "a.odrg"}]), "bad-type")

    def test_a_file_name_outside_the_naming_rule(self):
        for name in ("a.gif", "a", "A.odrg", "a b.odrg", "sub/a.odrg", "a.odrg ", "a.ODRG", "x" * 28 + ".odrg", "", "é.odrg", "a.odrg\n"):
            with self.subTest(name=name):
                self.check(source(items=[{"id": 1, "file": name}]), "file of item 1")
        self.check(source(items=[{"id": 1, "file": 7}]), "bad-type")

    def test_seconds_outside_1_to_65535(self):
        first = {"id": 1, "file": "a.odrg"}
        self.check(source(items=[first, {"id": 2, "cycle": [1], "seconds": 0}]), "out-of-range")
        self.check(source(items=[first, {"id": 2, "cycle": [1], "seconds": 65536}]), "out-of-range")
        self.check(source(items=[first, {"id": 2, "cycle": [1], "seconds": "15"}]), "bad-type")

    def test_a_cycle_that_is_not_a_list_of_one_or_more_integers(self):
        first = {"id": 1, "file": "a.odrg"}
        self.check(source(items=[first, {"id": 2, "cycle": [], "seconds": 5}]), "cycle of item 2 is empty")
        self.check(source(items=[first, {"id": 2, "cycle": 1, "seconds": 5}]), "bad-type")
        self.check(source(items=[first, {"id": 2, "cycle": ["1"], "seconds": 5}]), "bad-type")
        self.check(source(items=[first, {"id": 2, "cycle": [1, True], "seconds": 5}]), "bad-type")

    def test_a_start_that_is_not_an_integer(self):
        self.check(source(start="1"), "bad-type")
        self.check(source(start=None), "bad-type")
        self.check(source(start=[1]), "bad-type")


class Ids(unittest.TestCase):
    A = {"id": 1, "file": "a.odrg"}
    B = {"id": 2, "file": "b.odrg"}

    def test_duplicate_id(self):
        self.assertEqual(reason_of(source(items=[self.A, {"id": 1, "file": "b.odrg"}])), "duplicate-id")
        self.assertEqual(reason_of(source(items=[self.A, {"id": 1, "cycle": [1], "seconds": 5}])), "duplicate-id")

    def test_undefined_id_in_a_cycle(self):
        self.assertEqual(reason_of(source(items=[self.A, {"id": 2, "cycle": [1, 3], "seconds": 5}])), "undefined-id")
        self.assertEqual(reason_of(source(items=[self.A, {"id": 2, "cycle": [0], "seconds": 5}])), "undefined-id")
        self.assertEqual(reason_of(source(items=[self.A, {"id": 2, "cycle": [70000], "seconds": 5}])), "undefined-id")

    def test_undefined_id_in_start(self):
        self.assertEqual(reason_of(source(items=[self.A], start=2)), "undefined-id")
        self.assertEqual(reason_of(source(items=[self.A], start=0)), "undefined-id")
        self.assertIsNone(reason_of(source(items=[self.A], start=1)))

    def test_nested_cycle(self):
        cycle = {"id": 3, "cycle": [1, 2], "seconds": 5}
        self.assertEqual(reason_of(source(items=[self.A, self.B, cycle, {"id": 4, "cycle": [1, 3], "seconds": 5}])), "nested-cycle")
        self.assertEqual(reason_of(source(items=[self.A, {"id": 2, "cycle": [2], "seconds": 5}])), "nested-cycle")

    def test_a_cycle_may_name_an_item_that_comes_later_and_one_item_twice(self):
        items = [{"id": 3, "cycle": [2, 1, 2], "seconds": 5}, self.A, self.B]
        self.assertIsNone(reason_of(source(items=items, start=3)))

    def test_the_format_is_judged_before_the_ids(self):
        items = [self.A, {"id": 1, "file": "b.gif"}]
        self.assertEqual(reason_of(source(items=items)), "show-malformed")

    def test_a_duplicate_id_is_reported_before_an_undefined_one(self):
        items = [{"id": 5, "cycle": [9], "seconds": 5}, self.A, {"id": 1, "file": "b.odrg"}]
        self.assertEqual(reason_of(source(items=items, start=8)), "duplicate-id")

    def test_an_undefined_id_is_reported_before_a_nested_cycle(self):
        first = {"id": 3, "cycle": [4], "seconds": 5}
        second = {"id": 4, "cycle": [1, 9], "seconds": 5}
        self.assertEqual(reason_of(source(items=[self.A, first, second])), "undefined-id")
        self.assertEqual(reason_of(source(items=[self.A, first, {"id": 4, "cycle": [1], "seconds": 5}], start=9)), "undefined-id")
        self.assertEqual(reason_of(source(items=[self.A, first, {"id": 4, "cycle": [1], "seconds": 5}])), "nested-cycle")


class ExampleShow(unittest.TestCase):
    def test_the_tracked_example_show(self):
        result = show.read(EXAMPLE_SHOW)
        self.assertEqual(result.brightness, 128)
        self.assertEqual(result.start, 3)
        self.assertEqual(
            result.items,
            (
                show.Item(1, "hello.odrg", None, None),
                show.Item(2, "dvd.odrg", None, None),
                show.Item(3, None, (1, 2), 15),
            ),
        )
        self.assertNotIn(b"\r", EXAMPLE_SHOW.read_bytes())

    def test_a_missing_show_file_is_show_missing(self):
        with self.assertRaises(errors.Rejection) as caught:
            show.read(support.ROOT / "shows" / "example" / "absent.json")
        self.assertEqual(caught.exception.reason, "show-missing")


class Pack(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.out = self.folder / "out"
        self.sources = self.folder / "sources"
        self.sources.mkdir()

    def pack(self, show_path=EXAMPLE_SHOW, mapping_path=LEGS_2, sources=ANIMATIONS, out=None, *options):
        return support.run(
            "pack", "--show", show_path, "--mapping", mapping_path, "--sources", sources,
            "--out", self.out if out is None else out, *options,
        )

    def show_file(self, items=None, **named):
        path = self.folder / "show.json"
        path.write_bytes(source(items=items, **named))
        return path

    def clip(self, name, width=60, height=6, colour=b"\x01\x02\x03"):
        animation = jsonframes.Animation(width, height, ((20, colour * (width * height)),))
        jsonframes.write(self.sources / name, animation)

    def snapshot(self):
        """Every path under the test folder with the bytes of every file."""
        return {
            str(path.relative_to(self.folder)): path.read_bytes() if path.is_file() else None
            for path in sorted(self.folder.rglob("*"))
        }

    def refused(self, expected, result):
        self.assertEqual(result.status, 1)
        self.assertEqual(result.out, "")
        self.assertTrue(result.err.startswith(f"error: {expected}: "), result.err)
        self.assertEqual(result.err.count("\n"), 1)

    def test_the_example_show_gives_exactly_the_installed_file_set(self):
        result = self.pack()
        self.assertEqual(result, support.Result(0, "", ""))
        self.assertEqual(sorted(entry.name for entry in self.out.iterdir()), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])
        self.assertEqual((self.out / "mapping.json").read_bytes(), LEGS_2.read_bytes())
        self.assertEqual((self.out / "show.json").read_bytes(), EXAMPLE_SHOW.read_bytes())
        self.assertEqual(sorted(entry.name for entry in self.folder.iterdir()), ["out", "sources"])

    def test_every_packed_odrg_file_passes_check_and_decodes_to_the_frames_of_its_source(self):
        self.pack()
        for name in ("hello", "dvd"):
            with self.subTest(name=name):
                packed = self.out / f"{name}.odrg"
                checked = support.run("check", packed)
                self.assertEqual(checked.status, 0)
                self.assertIn("format: odrg\ncanvas: 60x6\n", checked.out)
                self.assertIn("compressed: yes\n", checked.out)
                decoded = odrg.decode(packed.read_bytes())
                self.assertEqual(decoded.records, jsonframes.read(ANIMATIONS / f"{name}.json").frames)
                self.assertEqual(packed.read_bytes(), odrg.encode(jsonframes.read(ANIMATIONS / f"{name}.json")))

    def test_uncompressed_clears_flag_bit_0_in_every_file(self):
        self.assertEqual(self.pack(EXAMPLE_SHOW, LEGS_2, ANIMATIONS, None, "--uncompressed").status, 0)
        packed = sorted(self.out.glob("*.odrg"))
        self.assertEqual(len(packed), 2)
        for path in packed:
            self.assertEqual(path.read_bytes()[5], 0, path.name)
        self.assertEqual((self.out / "hello.odrg").stat().st_size, 17731)

    def test_packing_twice_gives_identical_folders(self):
        other = self.folder / "other"
        self.pack()
        self.pack(out=other)
        for entry in self.out.iterdir():
            self.assertEqual(entry.read_bytes(), (other / entry.name).read_bytes(), entry.name)

    def test_it_runs_as_a_module(self):
        result = support.run_module(
            "pack", "--show", EXAMPLE_SHOW, "--mapping", LEGS_2, "--sources", ANIMATIONS, "--out", self.out
        )
        self.assertEqual(result, support.Result(0, "", ""))
        self.assertEqual(len(list(self.out.iterdir())), 4)

    def test_a_show_naming_one_file_twice_writes_it_once(self):
        self.clip("a.json")
        items = [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "a.odrg"}, {"id": 3, "cycle": [1, 2], "seconds": 5}]
        self.assertEqual(self.pack(self.show_file(items), LEGS_2, self.sources).status, 0)
        self.assertEqual(sorted(entry.name for entry in self.out.iterdir()), ["a.odrg", "mapping.json", "show.json"])

    def test_sources_the_show_does_not_name_are_left_out(self):
        self.clip("a.json")
        self.clip("b.json")
        (self.sources / "notes.txt").write_text("not a source")
        self.assertEqual(self.pack(self.show_file(), LEGS_2, self.sources).status, 0)
        self.assertEqual(sorted(entry.name for entry in self.out.iterdir()), ["a.odrg", "mapping.json", "show.json"])

    def test_an_existing_empty_output_folder_is_used(self):
        self.out.mkdir()
        self.assertEqual(self.pack().status, 0)
        self.assertEqual(len(list(self.out.iterdir())), 4)

    def test_the_canvas_comes_from_the_mapping_file(self):
        self.clip("a.json", 60, 60)
        self.assertEqual(self.pack(self.show_file(), TARGET, self.sources).status, 0)
        decoded = odrg.decode((self.out / "a.odrg").read_bytes())
        self.assertEqual((decoded.width, decoded.height), (60, 60))
        self.assertEqual((self.out / "mapping.json").read_bytes(), TARGET.read_bytes())

    def test_a_source_of_another_size_than_the_target_file_is_a_size_mismatch(self):
        for width, height in ((60, 6), (60, 30), (20, 60), (60, 180)):
            with self.subTest(source=(width, height)):
                self.clip("a.json", width, height)
                self.refused("size-mismatch", self.pack(self.show_file(), TARGET, self.sources))
                self.assertFalse(self.out.exists())

    def column_legs(self):
        path = self.folder / "columns.json"
        path.write_bytes(COLUMN_LEGS)
        return path

    def test_a_column_leg_mapping_is_copied_byte_for_byte_and_gives_the_canvas(self):
        self.clip("a.json", 5, 4)
        result = self.pack(self.show_file(), self.column_legs(), self.sources)
        self.assertEqual(result, support.Result(0, "", ""))
        self.assertEqual(sorted(entry.name for entry in self.out.iterdir()), ["a.odrg", "mapping.json", "show.json"])
        self.assertEqual((self.out / "mapping.json").read_bytes(), COLUMN_LEGS)
        decoded = odrg.decode((self.out / "a.odrg").read_bytes())
        self.assertEqual((decoded.width, decoded.height), (5, 4))

    def test_size_mismatch_with_a_column_leg_mapping(self):
        mapping_path = self.column_legs()
        for width, height in ((4, 5), (5, 3), (6, 4), (5, 5), (60, 6)):
            with self.subTest(source=(width, height)):
                self.clip("a.json", width, height)
                result = self.pack(self.show_file(), mapping_path, self.sources)
                self.refused("size-mismatch", result)
                self.assertIn(f"the canvas is {width} x {height} and the mapping's is 5 x 4", result.err)
                self.assertFalse(self.out.exists())

    # Refusals, in the order of the table.

    def test_mapping_missing(self):
        self.refused("mapping-missing", self.pack(mapping_path=self.folder / "absent.json"))

    def test_mapping_malformed(self):
        broken = self.folder / "mapping.json"
        broken.write_bytes(LEGS_2.read_bytes().replace(b'"width": 60', b'"width": 0'))
        self.refused("mapping-malformed", self.pack(mapping_path=broken))

    def test_show_missing(self):
        self.refused("show-missing", self.pack(show_path=self.folder / "absent.json"))

    def test_show_malformed(self):
        self.refused("show-malformed", self.pack(self.show_file(brightness=300)))

    def test_duplicate_id(self):
        items = [{"id": 1, "file": "hello.odrg"}, {"id": 1, "file": "dvd.odrg"}]
        self.refused("duplicate-id", self.pack(self.show_file(items)))

    def test_undefined_id(self):
        self.refused("undefined-id", self.pack(self.show_file([{"id": 1, "file": "hello.odrg"}], start=2)))

    def test_nested_cycle(self):
        items = [{"id": 1, "file": "hello.odrg"}, {"id": 2, "cycle": [1], "seconds": 5}, {"id": 3, "cycle": [2], "seconds": 5}]
        self.refused("nested-cycle", self.pack(self.show_file(items)))

    def test_file_missing(self):
        result = self.pack(self.show_file(), LEGS_2, self.sources)
        self.refused("file-missing", result)
        self.assertIn("a.json", result.err)
        self.refused("file-missing", self.pack(self.show_file(), LEGS_2, self.folder / "no-such-folder"))

    def test_file_malformed_gives_the_reason_of_the_source_too(self):
        self.clip("a.json")
        path = self.sources / "a.json"
        path.write_bytes(path.read_bytes().replace(b'"ms": 20', b'"ms": 0'))
        result = self.pack(self.show_file(), LEGS_2, self.sources)
        self.refused("file-malformed", result)
        self.assertIn("out-of-range", result.err)
        self.assertIn("a.json", result.err)

    def test_size_mismatch(self):
        self.clip("a.json", 60, 3)
        self.refused("size-mismatch", self.pack(self.show_file(), LEGS_2, self.sources))
        self.clip("a.json", 6, 60)
        self.refused("size-mismatch", self.pack(self.show_file(), LEGS_2, self.sources))

    def test_a_source_that_cannot_be_written_as_odrg(self):
        animation = jsonframes.Animation(60, 6, ((65535 * 2 ** 32, bytes(3 * 360)),))
        jsonframes.write(self.sources / "a.json", animation)
        self.refused("too-many-frames", self.pack(self.show_file(), LEGS_2, self.sources))

    def test_output_not_empty(self):
        self.out.mkdir()
        (self.out / "old.odrg").write_bytes(b"old")
        self.refused("output-not-empty", self.pack())
        self.assertEqual([entry.name for entry in self.out.iterdir()], ["old.odrg"])
        self.assertEqual((self.out / "old.odrg").read_bytes(), b"old")

    def test_an_output_that_is_a_file_is_refused(self):
        self.out.write_bytes(b"a file")
        self.refused("output-not-empty", self.pack())
        self.assertEqual(self.out.read_bytes(), b"a file")

    def test_folders_above_the_output_folder_are_made(self):
        out = self.folder / "build" / "shows" / "example"
        self.assertEqual(self.pack(out=out).status, 0)
        self.assertEqual(len(list(out.iterdir())), 4)
        self.assertEqual([entry.name for entry in out.parent.iterdir()], ["example"])

    def test_an_output_that_cannot_be_made_is_cannot_write(self):
        blocker = self.folder / "blocker"
        blocker.write_bytes(b"a file where a folder is needed")
        self.refused("cannot-write", self.pack(out=blocker / "out"))
        self.assertEqual(blocker.read_bytes(), b"a file where a folder is needed")

    def test_the_order_of_the_table_when_two_apply(self):
        absent = self.folder / "absent.json"
        malformed = self.show_file(brightness=300)
        self.refused("mapping-missing", self.pack(show_path=absent, mapping_path=absent))
        broken = self.folder / "mapping.json"
        broken.write_bytes(b"{}")
        self.refused("mapping-malformed", self.pack(show_path=absent, mapping_path=broken))
        self.refused("show-missing", self.pack(show_path=absent, sources=self.sources))
        self.refused("show-malformed", self.pack(malformed, LEGS_2, self.sources))
        self.clip("b.json", 60, 3)
        items = [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}]
        self.refused("duplicate-id", self.pack(self.show_file([items[0], {"id": 1, "cycle": [9], "seconds": 5}]), LEGS_2, self.sources))
        self.refused("undefined-id", self.pack(self.show_file(items, start=9), LEGS_2, self.sources))
        self.refused("file-missing", self.pack(self.show_file(items), LEGS_2, self.sources))
        (self.sources / "a.json").write_bytes(b"{}")
        self.refused("file-malformed", self.pack(self.show_file(items), LEGS_2, self.sources))
        self.refused("size-mismatch", self.pack(self.show_file(items[::-1]), LEGS_2, self.sources))

    def test_a_show_is_judged_before_the_output_folder(self):
        self.out.mkdir()
        (self.out / "old.odrg").write_bytes(b"old")
        self.refused("undefined-id", self.pack(self.show_file(start=5)))

    def test_every_refusal_leaves_the_output_folder_and_its_parent_as_they_were(self):
        self.clip("a.json")
        self.clip("small.json", 60, 3)
        (self.sources / "broken.json").write_bytes(b"{}")
        animation = jsonframes.Animation(60, 6, ((65535 * 2 ** 32, bytes(3 * 360)),))
        jsonframes.write(self.sources / "long.json", animation)
        first = {"id": 1, "file": "a.odrg"}
        shows = {
            "show-malformed": source(items=[first], brightness=-1),
            "duplicate-id": source(items=[first, first]),
            "undefined-id": source(items=[first], start=4),
            "nested-cycle": source(items=[first, {"id": 2, "cycle": [2], "seconds": 5}]),
            "file-missing": source(items=[first, {"id": 2, "file": "absent.odrg"}]),
            "file-malformed": source(items=[first, {"id": 2, "file": "broken.odrg"}]),
            "size-mismatch": source(items=[first, {"id": 2, "file": "small.odrg"}]),
            "too-many-frames": source(items=[first, {"id": 2, "file": "long.odrg"}]),
        }
        for existing in (False, True):
            if existing:
                self.out.mkdir()
            for expected, data in shows.items():
                with self.subTest(expected=expected, existing=existing):
                    path = self.folder / "show.json"
                    path.write_bytes(data)
                    before = self.snapshot()
                    self.refused(expected, self.pack(path, LEGS_2, self.sources))
                    self.assertEqual(self.snapshot(), before)

    def test_a_failure_while_writing_leaves_nothing_behind(self):
        before = self.snapshot()
        with mock.patch("os.replace", side_effect=PermissionError(13, "Permission denied")):
            result = self.pack()
        self.refused("cannot-write", result)
        self.assertEqual(self.snapshot(), before)

    def test_a_missing_option_is_a_usage_error(self):
        result = support.run("pack", "--show", EXAMPLE_SHOW, "--mapping", LEGS_2, "--sources", ANIMATIONS)
        self.assertEqual(result.status, 2)
        self.assertIn("usage:", result.err)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()

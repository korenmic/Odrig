import json
import unittest

from . import support

VECTORS = support.ROOT / "tests" / "vectors" / "invalid"
EXAMPLE_LEGS = ((1, 1, 180), (2, 2, 180))
T0 = 1000
OK = 'reply {"ok":true}'

# What an invalid show is asked: for its reason, to play, to switch and dim, and for LED
# data before and after.
QUESTIONS = [
    "error",
    support.line(T0, "status"),
    f"poll {T0}",
    support.line(T0, "play 1"),
    support.line(T0, "play 3"),
    support.line(T0, "off"),
    support.line(T0, "on"),
    support.line(T0, "brightness 200"),
    f"poll {T0 + 20}",
    f"poll {T0 + 5000}",
    support.line(T0 + 5000, "status"),
]


def example(**changes):
    """The files of the example show with some replaced, or left out when given as `None`."""
    files = support.example_show()
    for name, content in changes.items():
        name = name.replace("_", ".")
        if content is None:
            del files[name]
        else:
            files[name] = content
    return files


def animation(number, file):
    return {"id": number, "file": file}


def cycle(number, ids, seconds=15):
    return {"id": number, "cycle": list(ids), "seconds": seconds}


TWO_ANIMATIONS = [animation(1, "hello.odrg"), animation(2, "dvd.odrg")]


def show(*more, start=None):
    """A show file with the two animations of the example show and more items."""
    return support.show_text(TWO_ANIMATIONS + list(more), start=start)


class ValidShow(unittest.TestCase):
    def test_the_example_show_packed_by_the_converter_has_no_reason(self):
        run = support.start(example(), ["error", "error"])
        self.assertEqual(run.core, "ok")
        self.assertIsNone(run.error)
        self.assertEqual(run.logs, ())
        self.assertEqual(run.legs, EXAMPLE_LEGS)
        self.assertEqual(run.lines, ["error none", "error none"])

    def test_startup_reads_the_mapping_then_the_show_then_every_file(self):
        run = support.start(example(), options=["--trace-files"])
        self.assertEqual(
            run.opened,
            (("mapping.json", 1), ("mapping.json", 1), ("show.json", 1), ("show.json", 1), ("hello.odrg", 1), ("dvd.odrg", 1)),
        )

    def test_a_file_named_twice_is_opened_for_checking_once(self):
        items = [animation(5, "dvd.odrg"), animation(1, "hello.odrg"), animation(9, "dvd.odrg"), cycle(2, [9, 1, 5, 1]), animation(3, "hello.odrg")]
        run = support.start(example(show_json=support.show_text(items, start=2)), options=["--trace-files"])
        self.assertIsNone(run.error)
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], ["dvd.odrg", "hello.odrg"])

    def test_the_files_are_checked_in_the_order_the_show_first_names_them(self):
        files = example(show_json=support.show_text([animation(1, "c.odrg"), animation(2, "a.odrg"), animation(3, "b.odrg"), animation(4, "a.odrg")]))
        for name in ("a.odrg", "b.odrg", "c.odrg"):
            files[name] = files["hello.odrg"]
        run = support.start(files, options=["--trace-files"])
        self.assertIsNone(run.error)
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], ["c.odrg", "a.odrg", "b.odrg"])

    def test_a_show_without_start_and_one_of_animations_only_are_valid(self):
        for text in (show(), show(cycle(3, [1, 2])), support.show_text([animation(65535, "dvd.odrg")], brightness=0, start=65535)):
            self.assertIsNone(support.start(example(show_json=text)).error)

    def test_uncompressed_files_are_valid_too(self):
        files = example()
        for name in ("hello.odrg", "dvd.odrg"):
            self.assertEqual(files[name][5], 1)
        files["hello.odrg"] = support.clip(1, 60, 6, compressed=False)
        self.assertEqual(files["hello.odrg"][5], 0)
        self.assertIsNone(support.start(files).error)


class EachReason(unittest.TestCase):
    """One case at least for each text of the table of invalid shows."""

    def check(self, files, text, options=(), legs=EXAMPLE_LEGS):
        run = support.start(files, QUESTIONS, options)
        self.assert_invalid(run, text, legs)
        return run

    def assert_invalid(self, run, text, legs):
        """The show is invalid with this text: `status` reports it, the LEDs stay dark,
        `play` is refused, and the other commands work as ever."""
        self.assertEqual(run.core, "ok")
        self.assertEqual(run.error, text)
        self.assertEqual(run.logs, (text,))
        self.assertEqual(run.legs, legs)
        if legs:
            dark = [f"data {leg} {bytes(3 * count).hex()}" for leg, _, count in legs]
            polled = [[f"refresh {time}"] + dark for time in (T0, T0 + 20, T0 + 5000)]
        else:
            polled = [[f"idle {time}"] for time in (T0, T0 + 20, T0 + 5000)]
        lines = list(run.lines)
        self.assertEqual(lines.pop(0), f"error {text}")
        first = json.loads(lines.pop(0)[len("reply "):])
        self.assertEqual((first["error"], first["playing"], first["animation"], first["on"]), (text, None, None, True))
        self.assertEqual([lines.pop(0) for _ in polled[0]], polled[0])
        self.assertEqual([lines.pop(0) for _ in range(2)], ['reply {"ok":false,"error":"show-invalid"}'] * 2)
        self.assertEqual([lines.pop(0) for _ in range(3)], [OK] * 3)
        self.assertEqual([lines.pop(0) for _ in polled[1] + polled[2]], polled[1] + polled[2])
        last = json.loads(lines.pop(0)[len("reply "):])
        self.assertEqual(last, {"ok": True, "on": True, "brightness": 200, "playing": None, "animation": None, "fps": 0, "error": text})
        self.assertEqual(lines, [])

    def test_mapping_missing(self):
        self.check(example(mapping_json=None), "mapping-missing", legs=())

    def test_mapping_malformed(self):
        self.check(example(mapping_json='{"version": 1}'), "mapping-malformed", legs=())

    def test_show_missing(self):
        self.check(example(show_json=None), "show-missing")

    def test_show_malformed(self):
        self.check(example(show_json='{"version": 1, "brightness": 300, "items": []}'), "show-malformed")
        self.check(example(show_json=show(animation(3, "Hello.odrg"))), "show-malformed")
        self.check(example(show_json=""), "show-malformed")

    def test_duplicate_id_names_the_id(self):
        self.check(example(show_json=show(animation(2, "hello.odrg"))), "duplicate-id 2")
        self.check(example(show_json=show(cycle(7, [1]), cycle(65535, [1]), cycle(65535, [2]), cycle(7, [2]))), "duplicate-id 65535")

    def test_undefined_id_names_the_id_a_cycle_names(self):
        self.check(example(show_json=show(cycle(3, [1, 9, 8]))), "undefined-id 9")
        self.check(example(show_json=show(cycle(3, [1]), cycle(4, [2, 65535]))), "undefined-id 65535")

    def test_undefined_id_names_the_id_start_names(self):
        self.check(example(show_json=show(start=4)), "undefined-id 4")

    def test_undefined_id_names_an_id_that_no_item_can_have(self):
        self.check(example(show_json=show(cycle(3, [0]))), "undefined-id 0")
        self.check(example(show_json=show(cycle(3, [1, -5, 70000]))), "undefined-id -5")
        self.check(example(show_json=show(cycle(3, [1, 70000, -5]))), "undefined-id 70000")
        self.check(example(show_json=show(cycle(3, [1, 65536]))), "undefined-id 65536")
        self.check(example(show_json=show(start=-1)), "undefined-id -1")
        self.check(example(show_json=show(start=0)), "undefined-id 0")
        self.check(example(show_json=show(start=4294967295)), "undefined-id 4294967295")
        self.check(example(show_json=show(start=10 ** 30)), "undefined-id 4294967295")
        self.check(example(show_json=show(start=-(10 ** 30))), "undefined-id -4294967295")

    def test_nested_cycle_names_the_cycle_that_names_a_cycle(self):
        self.check(example(show_json=show(cycle(3, [1, 2]), cycle(4, [1, 3]))), "nested-cycle 4")
        self.check(example(show_json=show(cycle(3, [3]))), "nested-cycle 3")
        self.check(example(show_json=show(cycle(8, [1, 9]), cycle(9, [2]))), "nested-cycle 8")

    def test_file_missing_names_the_file(self):
        self.check(example(hello_odrg=None), "file-missing hello.odrg")
        self.check(example(dvd_odrg=None), "file-missing dvd.odrg")
        self.check(example(show_json=show(animation(3, ".odrg"))), "file-missing .odrg")
        longest = "a" * 27 + ".odrg"
        self.check(example(show_json=show(animation(3, longest))), f"file-missing {longest}")

    def test_file_malformed_names_the_file_and_the_reason(self):
        hello = support.example_show()["hello.odrg"]
        self.check(example(hello_odrg=b"ODRX" + hello[4:]), "file-malformed hello.odrg bad-magic")
        self.check(example(dvd_odrg=b""), "file-malformed dvd.odrg truncated")
        self.check(example(dvd_odrg=hello + b"\0"), "file-malformed dvd.odrg trailing-bytes")
        self.check(example(hello_odrg=hello[:16] + b"\x07" + hello[17:]), "file-malformed hello.odrg bad-deflate")

    def test_file_malformed_gives_the_reason_of_every_invalid_vector(self):
        vectors = sorted(VECTORS.iterdir())
        self.assertGreaterEqual(len(vectors), 30)
        file_sets = []
        for path in vectors:
            data = path.read_bytes()
            # The canvas the vector states, so that a vector with a sound header is judged
            # by its body. A header that states no usable canvas is refused before that.
            width = int.from_bytes(data[6:8], "little") if len(data) >= 16 else 0
            height = int.from_bytes(data[8:10], "little") if len(data) >= 16 else 0
            usable = 1 <= width and 1 <= height and width * height <= 65534
            mapping = support.one_leg_mapping(width, height) if usable else support.one_leg_mapping(3, 3)
            file_sets.append({"mapping.json": mapping, "show.json": support.show_text([animation(1, "vector.odrg")]), "vector.odrg": data})
        runs = support.start_each(file_sets, QUESTIONS)
        for path, run in zip(vectors, runs):
            with self.subTest(vector=path.name):
                self.assertEqual(len(run.legs), 1)
                self.assert_invalid(run, f"file-malformed vector.odrg {path.name.split('.')[0]}", run.legs)

    def test_size_mismatch_names_the_file(self):
        self.check(example(dvd_odrg=support.clip(1, 60, 5)), "size-mismatch dvd.odrg")
        self.check(example(hello_odrg=support.clip(1, 59, 6)), "size-mismatch hello.odrg")
        twenty_legs = tuple((number, pin, 180) for number, pin in enumerate((*range(1, 19), 21, 47), start=1))
        self.check(example(mapping_json=support.mapping_texts()["legs-20"]), "size-mismatch hello.odrg", legs=twenty_legs)

    def test_read_error_names_the_file(self):
        self.check(example(), "read-error mapping.json", ["--read-fails", "mapping.json", "0"], legs=())
        self.check(example(), "read-error mapping.json", ["--read-fails", "mapping.json", "100"], legs=())
        self.check(example(), "read-error show.json", ["--read-fails", "show.json", "0"])
        self.check(example(), "read-error show.json", ["--read-fails", "show.json", "50"])
        for offset in (0, 15, 16, 17, 400):
            self.check(example(), "read-error hello.odrg", ["--read-fails", "hello.odrg", str(offset)])
        self.check(example(), "read-error dvd.odrg", ["--read-fails", "dvd.odrg", "1000"])

    def test_a_read_that_fails_at_the_very_end_of_a_file_is_a_read_error(self):
        files = example()
        for name in ("mapping.json", "show.json", "dvd.odrg"):
            legs = () if name == "mapping.json" else EXAMPLE_LEGS
            self.check(files, f"read-error {name}", ["--read-fails", name, str(len(files[name]))], legs=legs)
            self.assertIsNone(support.start(files, options=["--read-fails", name, str(len(files[name]) + 1)]).error)

    def test_a_folder_in_place_of_a_file_is_a_read_error(self):
        with support.installed(example(hello_odrg=None)) as folder:
            (support.pathlib.Path(folder) / "hello.odrg").mkdir()
            run = support.session(folder, ["error"])
        self.assertEqual(run.error, "read-error hello.odrg")

    def test_out_of_memory(self):
        blocks = support.start(example()).memory[1]
        self.assertEqual(blocks, 10)
        for number in (8, 9, 10):
            self.check(example(), "out-of-memory", ["--alloc-fails-at", str(number)])


class OrderOfTheChecks(unittest.TestCase):
    def reason(self, files, options=()):
        return support.start(files, options=options).error

    def test_of_two_defects_the_earlier_one_in_the_order_of_the_table_is_reported(self):
        bad_show = '{"version": 2}'
        bad_file = b"ODRG\x02" + bytes(11)
        cases = (
            ("mapping-missing", example(mapping_json=None, show_json=None)),
            ("mapping-malformed", example(mapping_json="[]", show_json=None)),
            ("mapping-malformed", example(mapping_json="[]", show_json=bad_show)),
            ("show-missing", example(show_json=None, hello_odrg=None)),
            ("show-malformed", example(show_json='{"version": 1, "brightness": 1, "items": [{"id": 1, "file": "a.odrg"}, {"id": 1, "file": "b"}]}')),
            ("duplicate-id 1", example(show_json=show(animation(1, "a.odrg"), cycle(3, [9]), cycle(4, [3]), start=8))),
            ("undefined-id 9", example(show_json=show(cycle(3, [9]), cycle(4, [3]), animation(5, "a.odrg")))),
            ("undefined-id 8", example(show_json=show(cycle(3, [1]), cycle(4, [3]), animation(5, "a.odrg"), start=8))),
            ("nested-cycle 4", example(show_json=show(cycle(3, [1]), cycle(4, [3]), animation(5, "a.odrg")))),
            ("file-missing hello.odrg", example(hello_odrg=None, dvd_odrg=bad_file)),
            ("file-malformed hello.odrg bad-version", example(hello_odrg=bad_file, dvd_odrg=None)),
            ("file-malformed hello.odrg bad-version", example(hello_odrg=bad_file, dvd_odrg=support.clip(1, 3, 3))),
            ("size-mismatch hello.odrg", example(hello_odrg=support.clip(1, 3, 3), dvd_odrg=bad_file)),
        )
        for expected, files in cases:
            with self.subTest(expected=expected):
                self.assertEqual(self.reason(files), expected)

    def test_an_undefined_id_in_a_cycle_is_reported_before_one_in_start(self):
        self.assertEqual(self.reason(example(show_json=show(cycle(3, [7]), start=9))), "undefined-id 7")
        self.assertEqual(self.reason(example(show_json=show(cycle(3, [1, 6]), cycle(4, [5, 1]), start=9))), "undefined-id 6")

    def test_the_ids_are_checked_in_three_passes_over_the_whole_file(self):
        late_duplicate = show(cycle(3, [9]), cycle(4, [3]), animation(2, "hello.odrg"))
        self.assertEqual(self.reason(example(show_json=late_duplicate)), "duplicate-id 2")
        late_undefined = show(cycle(3, [4]), cycle(4, [1]), cycle(5, [9]))
        self.assertEqual(self.reason(example(show_json=late_undefined)), "undefined-id 9")

    def test_a_file_is_checked_by_its_header_then_its_size_then_its_body(self):
        small = support.clip(1, 3, 3)
        cut_body = small[:-3]
        self.assertEqual(self.reason(example(hello_odrg=cut_body)), "size-mismatch hello.odrg")
        self.assertEqual(self.reason(example(hello_odrg=small[:16])), "size-mismatch hello.odrg")
        self.assertEqual(self.reason(example(hello_odrg=small[:15])), "file-malformed hello.odrg truncated")
        no_frames = small[:12] + bytes(4) + small[16:]
        self.assertEqual(self.reason(example(hello_odrg=no_frames)), "file-malformed hello.odrg no-frames")
        right_size_cut_body = support.clip(1, 60, 6)[:-3]
        self.assertEqual(self.reason(example(hello_odrg=right_size_cut_body)), "file-malformed hello.odrg truncated")

    def test_a_palette_cut_short_in_a_file_of_the_wrong_size_is_a_size_mismatch(self):
        small = support.clip(1, 3, 3, compressed=False)
        self.assertNotEqual(small[10:12], b"\0\0")
        self.assertEqual(self.reason(example(hello_odrg=small[:18])), "size-mismatch hello.odrg")

    def test_the_first_failure_ends_the_checks(self):
        run = support.start(example(hello_odrg=None), options=["--trace-files"])
        self.assertEqual(run.error, "file-missing hello.odrg")
        self.assertEqual(run.opened[-1], ("hello.odrg", 0))
        self.assertNotIn(("dvd.odrg", 1), run.opened)
        run = support.start(example(show_json=None), options=["--trace-files"])
        self.assertEqual(run.opened, (("mapping.json", 1), ("mapping.json", 1), ("show.json", 0)))
        run = support.start(example(mapping_json=None), options=["--trace-files"])
        self.assertEqual(run.opened, (("mapping.json", 0),))

    def test_a_show_with_wrong_ids_asks_for_no_file(self):
        run = support.start(example(show_json=show(start=9)), options=["--trace-files"])
        self.assertEqual(run.error, "undefined-id 9")
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], [])


if __name__ == "__main__":
    unittest.main()

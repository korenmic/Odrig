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
            (("mapping.json", 1), ("mapping.json", 1), ("show.json", 1), ("show.json", 1), ("pending.txt", 0), ("hello.odrg", 1), ("dvd.odrg", 1)),
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


def quarantine_text(name, reason):
    """The line of the log that quarantines a file."""
    return f"file {name} unavailable: {reason}"


class EachReason(unittest.TestCase):
    """One case at least for each text of the table of invalid shows, and for each fault of
    a file, which quarantines the file and leaves the show valid."""

    def check(self, files, text, options=(), legs=EXAMPLE_LEGS, canvas=(60, 6)):
        run = support.start(files, QUESTIONS, options)
        self.assert_invalid(run, text, legs, canvas)
        return run

    def quarantined(self, files, name, reason, options=()):
        """The file is quarantined with this reason: the show stays valid, the log of the
        start says so, and `list` marks it."""
        run = support.start(files, ["error", support.line(T0, "list")], options)
        self.assert_quarantined(run, name, reason)
        return run

    def assert_quarantined(self, run, name, reason):
        self.assertEqual(run.core, "ok")
        self.assertIsNone(run.error)
        self.assertIn(quarantine_text(name, reason), run.logs)
        self.assertEqual(run.lines[0], "error none")
        listed = json.loads(run.lines[1][len("reply "):])
        faults = {item["file"]: item.get("fault") for item in listed["items"] if "file" in item}
        self.assertEqual(faults[name], reason)

    def assert_invalid(self, run, text, legs, canvas=(60, 6)):
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
        width, height = canvas if legs else (None, None)
        self.assertEqual(last, {"ok": True, "on": True, "brightness": 200, "playing": None, "animation": None, "fps": 0, "error": text, "width": width, "height": height})
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

    def test_file_missing_quarantines_the_file(self):
        self.quarantined(example(hello_odrg=None), "hello.odrg", "file-missing")
        self.quarantined(example(dvd_odrg=None), "dvd.odrg", "file-missing")
        self.quarantined(example(show_json=show(animation(3, ".odrg"))), ".odrg", "file-missing")
        longest = "a" * 27 + ".odrg"
        self.quarantined(example(show_json=show(animation(3, longest))), longest, "file-missing")

    def test_a_malformed_file_is_quarantined_with_its_reason(self):
        hello = support.example_show()["hello.odrg"]
        self.quarantined(example(hello_odrg=b"ODRZ" + hello[4:]), "hello.odrg", "bad-magic")
        self.quarantined(example(dvd_odrg=b""), "dvd.odrg", "truncated")
        self.quarantined(example(dvd_odrg=hello + b"\0"), "dvd.odrg", "trailing-bytes")
        self.quarantined(example(hello_odrg=hello[:16] + b"\x07" + hello[17:]), "hello.odrg", "bad-deflate")

    def test_file_malformed_gives_the_reason_of_every_invalid_vector(self):
        vectors = sorted(VECTORS.iterdir())
        self.assertGreaterEqual(len(vectors), 30)
        file_sets = []
        canvases = []
        for path in vectors:
            data = path.read_bytes()
            # The canvas the vector states, so that a vector with a sound header is judged
            # by its body. A header that states no usable canvas is refused before that.
            width = int.from_bytes(data[6:8], "little") if len(data) >= 16 else 0
            height = int.from_bytes(data[8:10], "little") if len(data) >= 16 else 0
            usable = 1 <= width and 1 <= height and width * height <= 65534
            mapping = support.one_leg_mapping(width, height) if usable else support.one_leg_mapping(3, 3)
            file_sets.append({"mapping.json": mapping, "show.json": support.show_text([animation(1, "vector.odrg")]), "vector.odrg": data})
            canvases.append((width, height) if usable else (3, 3))
        runs = support.start_each(file_sets, ["error", support.line(T0, "list")])
        for path, run, canvas in zip(vectors, runs, canvases):
            with self.subTest(vector=path.name):
                self.assertEqual(len(run.legs), 1)
                self.assert_quarantined(run, "vector.odrg", path.name.split(".")[0])

    def test_size_mismatch_quarantines_the_file(self):
        self.quarantined(example(dvd_odrg=support.clip(1, 60, 5)), "dvd.odrg", "size-mismatch")
        self.quarantined(example(hello_odrg=support.clip(1, 59, 6)), "hello.odrg", "size-mismatch")
        run = self.quarantined(example(mapping_json=support.mapping_texts()["legs-20"]), "hello.odrg", "size-mismatch")
        self.assertEqual(run.logs, (quarantine_text("hello.odrg", "size-mismatch"), quarantine_text("dvd.odrg", "size-mismatch")))

    def test_read_error_names_the_file(self):
        self.check(example(), "read-error mapping.json", ["--read-fails", "mapping.json", "0"], legs=())
        self.check(example(), "read-error mapping.json", ["--read-fails", "mapping.json", "100"], legs=())
        self.check(example(), "read-error show.json", ["--read-fails", "show.json", "0"])
        self.check(example(), "read-error show.json", ["--read-fails", "show.json", "50"])
        for offset in (0, 15, 16, 17, 400):
            self.quarantined(example(), "hello.odrg", "read-error", ["--read-fails", "hello.odrg", str(offset)])
        self.quarantined(example(), "dvd.odrg", "read-error", ["--read-fails", "dvd.odrg", "1000"])

    def test_a_read_that_fails_at_the_very_end_of_a_file_is_a_read_error(self):
        files = example()
        for name in ("mapping.json", "show.json", "dvd.odrg"):
            legs = () if name == "mapping.json" else EXAMPLE_LEGS
            if name.endswith(".odrg"):
                self.quarantined(files, name, "read-error", ["--read-fails", name, str(len(files[name]))])
            else:
                self.check(files, f"read-error {name}", ["--read-fails", name, str(len(files[name]))], legs=legs)
            run = support.start(files, options=["--read-fails", name, str(len(files[name]) + 1)])
            self.assertEqual((run.error, run.logs), (None, ()))

    def test_a_folder_in_place_of_a_file_is_a_read_error(self):
        with support.installed(example(hello_odrg=None)) as folder:
            (support.pathlib.Path(folder) / "hello.odrg").mkdir()
            run = support.session(folder, ["error"])
        self.assertIsNone(run.error)
        self.assertEqual(run.logs, (quarantine_text("hello.odrg", "read-error"),))

    def test_out_of_memory(self):
        blocks = support.start(example()).memory[1]
        self.assertEqual(blocks, 17)
        for number in (10, 11, 12, 13, 14, 15, 16, 17):
            self.check(example(), "out-of-memory", ["--alloc-fails-at", str(number)])


class OrderOfTheChecks(unittest.TestCase):
    def reason(self, files, options=()):
        """The reason of an invalid show, or the first line of the log of a valid one."""
        run = support.start(files, options=options)
        return run.error if run.error is not None or not run.logs else run.logs[0]

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
            (quarantine_text("hello.odrg", "file-missing"), example(hello_odrg=None, dvd_odrg=bad_file)),
            (quarantine_text("hello.odrg", "bad-version"), example(hello_odrg=bad_file, dvd_odrg=None)),
            (quarantine_text("hello.odrg", "bad-version"), example(hello_odrg=bad_file, dvd_odrg=support.clip(1, 3, 3))),
            (quarantine_text("hello.odrg", "size-mismatch"), example(hello_odrg=support.clip(1, 3, 3), dvd_odrg=bad_file)),
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
        self.assertEqual(self.reason(example(hello_odrg=cut_body)), quarantine_text("hello.odrg", "size-mismatch"))
        self.assertEqual(self.reason(example(hello_odrg=small[:16])), quarantine_text("hello.odrg", "size-mismatch"))
        self.assertEqual(self.reason(example(hello_odrg=small[:15])), quarantine_text("hello.odrg", "truncated"))
        no_frames = small[:12] + bytes(4) + small[16:]
        self.assertEqual(self.reason(example(hello_odrg=no_frames)), quarantine_text("hello.odrg", "no-frames"))
        right_size_cut_body = support.clip(1, 60, 6)[:-3]
        self.assertEqual(self.reason(example(hello_odrg=right_size_cut_body)), quarantine_text("hello.odrg", "truncated"))

    def test_a_palette_cut_short_in_a_file_of_the_wrong_size_is_a_size_mismatch(self):
        small = support.clip(1, 3, 3, compressed=False)
        self.assertNotEqual(small[10:12], b"\0\0")
        self.assertEqual(self.reason(example(hello_odrg=small[:18])), quarantine_text("hello.odrg", "size-mismatch"))

    def test_a_missing_file_does_not_end_the_checks_and_a_show_fault_does(self):
        run = support.start(example(hello_odrg=None), options=["--trace-files"])
        self.assertIsNone(run.error)
        self.assertIn(("hello.odrg", 0), run.opened)
        self.assertIn(("dvd.odrg", 1), run.opened)
        run = support.start(example(show_json=None), options=["--trace-files"])
        self.assertEqual(run.opened, (("mapping.json", 1), ("mapping.json", 1), ("show.json", 0)))
        run = support.start(example(mapping_json=None), options=["--trace-files"])
        self.assertEqual(run.opened, (("mapping.json", 0),))

    def test_a_show_with_wrong_ids_asks_for_no_file(self):
        run = support.start(example(show_json=show(start=9)), options=["--trace-files"])
        self.assertEqual(run.error, "undefined-id 9")
        self.assertEqual([name for name, _ in run.opened if name.endswith(".odrg")], [])


class Leftovers(unittest.TestCase):
    """What the start removes of a change that was interrupted."""

    CLIP = support.clip(4, 60, 6)

    def started(self, files, options=()):
        """Starts the core on the files, with its storage calls and its openings traced.
        Returns the run and the files of the folder afterwards. The reference player
        leaves the same files."""
        run, left = support.start_and_keep(files, [support.line(T0, "status")], ["--trace-store", "--trace-files", *options])
        return run, left

    def assert_as_the_reference(self, files, left):
        expected = support.ReferencePlayer(files).files
        self.assertEqual(sorted(left), sorted(expected))
        self.assertEqual(left, expected)

    def test_a_folder_without_leftovers_gets_two_removals_one_opening_and_no_other_storage_call(self):
        for files in (example(), support.demo_show()):
            run, left = self.started(files)
            self.assertIsNone(run.error)
            self.assertEqual(run.stored, ("remove upload.part 0", "remove show.part 0"))
            self.assertEqual(run.opened.count(("pending.txt", 0)), 1)
            self.assertEqual(run.opened.index(("pending.txt", 0)), 4)
            self.assertFalse(any(line.startswith("store ") for line in run.lines))
            self.assertEqual(left, {name: content if isinstance(content, bytes) else content.encode() for name, content in files.items()})

    def test_each_leftover_alone_and_with_the_others_is_removed(self):
        leftovers = {"upload.part": b"half an upload", "show.part": b'{"version":1,"brigh', "pending.txt": b"stray.odrg\n", "stray.odrg": self.CLIP}
        names = sorted(leftovers)
        plain = {name: content if isinstance(content, bytes) else content.encode() for name, content in example().items()}
        for chosen in range(1, 2 ** len(names)):
            there = [name for bit, name in enumerate(names) if chosen >> bit & 1]
            with self.subTest(leftovers=there):
                files = example(**{name.replace(".", "_"): leftovers[name] for name in there})
                run, left = self.started(files)
                self.assertIsNone(run.error)
                self.assert_as_the_reference(files, left)
                # A file that no item names and that `pending.txt` does not name is not
                # the core's to find: it stays.
                stays = {"stray.odrg"} if "stray.odrg" in there and "pending.txt" not in there else set()
                self.assertEqual(set(left), set(plain) | stays)
                self.assertEqual({name: left[name] for name in plain}, plain)
                expected = [f"remove upload.part {int('upload.part' in there)}", f"remove show.part {int('show.part' in there)}"]
                if "pending.txt" in there:
                    expected += [f"remove stray.odrg {int('stray.odrg' in there)}", "remove pending.txt 1"]
                self.assertEqual(list(run.stored), expected)

    def test_a_file_that_an_item_names_is_not_removed_whatever_pending_says(self):
        files = example(pending_txt=b"hello.odrg\nstray.odrg\ndvd.odrg\nhello.odrg\nstray.odrg\n", stray_odrg=self.CLIP)
        run, left = self.started(files)
        self.assertIsNone(run.error)
        self.assertEqual(sorted(left), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])
        self.assertEqual(list(run.stored)[2:], ["remove stray.odrg 1", "remove stray.odrg 0", "remove pending.txt 1"])
        self.assert_as_the_reference(files, left)

    def test_a_cut_line_of_pending_names_nothing(self):
        for text in (b"stray.odrg", b"stray.od", b"", b"other.odrg\nstray.odrg", b"other.odrg\nstray"):
            with self.subTest(pending=text):
                files = example(pending_txt=text, stray_odrg=self.CLIP, other_odrg=self.CLIP)
                run, left = self.started(files)
                self.assertIsNone(run.error)
                self.assertIn("stray.odrg", left)
                self.assertEqual("other.odrg" in left, not text.startswith(b"other.odrg\n"))
                self.assertNotIn("pending.txt", left)
                self.assert_as_the_reference(files, left)

    def test_a_line_of_pending_that_is_no_file_name_names_nothing(self):
        lines = [b"show.json", b"mapping.json", b"pending.txt", b"upload.part", b"stray.txt", b"STRAY.odrg", b"../stray.odrg", b"./stray.odrg", b"stray.odrg ", b" stray.odrg",
                 b"stray.odrg\r", b"", b"a" * 28 + b".odrg", b"stray\x00.odrg", b"str\xc3\xa4y.odrg", b"stray.odrgy", b"/stray.odrg", b"odrg"]
        files = example(pending_txt=b"".join(line + b"\n" for line in lines), stray_odrg=self.CLIP)
        run, left = self.started(files)
        self.assertIsNone(run.error)
        self.assertEqual(sorted(left), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json", "stray.odrg"])
        self.assertEqual(list(run.stored)[2:], ["remove pending.txt 1"])
        self.assert_as_the_reference(files, left)

    def test_the_shortest_and_the_longest_file_name_of_pending_are_taken(self):
        longest = "b" * 27 + ".odrg"
        files = example(pending_txt=f".odrg\n{longest}\n".encode(), **{"_odrg": self.CLIP, longest.replace(".", "_"): self.CLIP})
        run, left = self.started(files)
        self.assertEqual(list(run.stored)[2:], ["remove .odrg 1", f"remove {longest} 1", "remove pending.txt 1"])
        self.assertEqual(sorted(left), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])

    def test_of_a_long_pending_the_first_1500_bytes_are_read(self):
        names = [f"stray-{number:03d}.odrg" for number in range(40)]
        self.assertEqual(len(names[0]), 14)
        files = example(pending_txt="".join(f"{name}\n" for name in names).encode())
        files.update({name: self.CLIP for name in names})
        run, left = self.started(files)
        self.assertIsNone(run.error)
        # All 40 lines of 15 bytes fit into the journal buffer.
        self.assertEqual(sorted(name for name in left if name.startswith("stray-")), [])
        self.assertNotIn("pending.txt", left)
        self.assert_as_the_reference(files, left)

    def test_beside_a_show_file_that_cannot_be_used_pending_is_left_alone(self):
        unusable = {
            "show-missing": {"show_json": None},
            "show-malformed": {"show_json": "{"},
            "duplicate-id 1": {"show_json": support.show_text([animation(1, "hello.odrg"), animation(1, "dvd.odrg")])},
            "undefined-id 7": {"show_json": show(start=7)},
            "nested-cycle 4": {"show_json": show(cycle(3, [1]), cycle(4, [3]))},
            "mapping-missing": {"mapping_json": None},
            "mapping-malformed": {"mapping_json": "{"},
        }
        for reason, changes in unusable.items():
            with self.subTest(reason=reason):
                files = example(pending_txt=b"stray.odrg\nhello.odrg\n", stray_odrg=self.CLIP, upload_part=b"x", show_part=b"y", **changes)
                run, left = self.started(files)
                self.assertEqual(run.error, reason)
                self.assertEqual(run.stored, ("remove upload.part 1", "remove show.part 1"))
                self.assertEqual(left["pending.txt"], b"stray.odrg\nhello.odrg\n")
                self.assertIn("stray.odrg", left)
                self.assertNotIn("upload.part", left)
                self.assertNotIn("show.part", left)
                self.assert_as_the_reference(files, left)

    def test_beside_a_show_whose_file_is_missing_pending_is_settled(self):
        files = example(pending_txt=b"stray.odrg\n", stray_odrg=self.CLIP, dvd_odrg=None)
        run, left = self.started(files)
        self.assertEqual((run.error, run.logs), (None, (quarantine_text("dvd.odrg", "file-missing"),)))
        self.assertEqual(sorted(left), ["hello.odrg", "mapping.json", "show.json"])
        self.assert_as_the_reference(files, left)

    def test_a_pending_that_cannot_be_read_is_left_with_what_it_names(self):
        files = example(pending_txt=b"stray.odrg\nother.odrg\n", stray_odrg=self.CLIP, other_odrg=self.CLIP)
        for offset in (0, 5, 11, 21, 22):
            run, left = self.started(files, ["--read-fails", "pending.txt", str(offset)])
            self.assertIsNone(run.error)
            self.assertEqual(run.stored, ("remove upload.part 0", "remove show.part 0"))
            self.assertEqual(sorted(left), sorted(files))
        run, left = self.started(files, ["--read-fails", "pending.txt", "23"])
        self.assertEqual(sorted(left), ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])

    def test_a_host_without_storage_that_can_be_changed_removes_nothing(self):
        files = example(pending_txt=b"stray.odrg\n", stray_odrg=self.CLIP, upload_part=b"x", show_part=b"y")
        for option in ("--no-storage", "--only-space"):
            run, left = self.started(files, [option])
            self.assertIsNone(run.error)
            self.assertEqual(run.stored, ())
            self.assertNotIn("pending.txt", [name for name, _ in run.opened])
            self.assertEqual(sorted(left), sorted(files))

    def test_a_removal_at_the_start_that_fails_does_not_stop_the_start(self):
        files = example(pending_txt=b"stray.odrg\n", stray_odrg=self.CLIP, upload_part=b"x", show_part=b"y")
        for number in (1, 2, 3, 4):
            run, left = self.started(files, ["--store-fails-at", str(number)])
            self.assertIsNone(run.error)
            self.assertEqual(json.loads(run.lines[-1][len("reply "):])["playing"], 3)
            # A file that could not be removed stays named: `pending.txt` is kept for it.
            self.assertEqual(len(run.stored), 3 if number == 3 else 4)
            self.assertEqual([entry.endswith(" -1") for entry in run.stored], [position == number - 1 for position in range(len(run.stored))])
            self.assertEqual("pending.txt" in left, number in (3, 4))
            self.assertEqual("stray.odrg" in left, number == 3)


class TablesWithRoom(unittest.TestCase):
    def memory(self, count):
        """The bytes the core asks for with a show of `count` animation items that name
        one file, on the two-leg mapping."""
        items = [animation(number, "hello.odrg") for number in range(1, count + 1)]
        run = support.start(example(show_json=support.show_text(items)))
        self.assertIsNone(run.error)
        self.assertEqual(run.memory[1], 17)
        return run.memory[0]

    def test_the_tables_have_room_for_32_items_more_than_the_show_and_for_128_at_least(self):
        small = self.memory(0)
        self.assertEqual([self.memory(count) for count in (1, 2, 50, 96)], [small] * 4)
        # An item of the table is 16 bytes, a file 48, and the key of the saved order 2.
        self.assertEqual(self.memory(97) - small, 66)
        self.assertEqual(self.memory(98) - small, 2 * 66)
        self.assertEqual(self.memory(300) - small, (300 + 32 - 128) * 66)

    def test_a_show_without_items_starts_and_plays_nothing(self):
        files = example(show_json='{"version": 1, "brightness": 9, "items": []}', hello_odrg=None, dvd_odrg=None)
        run = support.start(files, QUESTIONS[:3] + [support.line(T0, "play 1"), support.line(T0, "list")])
        self.assertIsNone(run.error)
        self.assertEqual(run.legs, EXAMPLE_LEGS)
        self.assertEqual(
            json.loads(run.lines[1][len("reply "):]),
            {"ok": True, "on": True, "brightness": 9, "playing": None, "animation": None, "fps": 0, "error": None, "width": 60, "height": 6},
        )
        self.assertEqual(run.lines[-2:], ['reply {"ok":false,"error":"unknown-id"}', 'reply {"ok":true,"items":[],"next":null}'])
        self.assertEqual(run.lines, support.ReferencePlayer(files).run(QUESTIONS[:3] + [support.line(T0, "play 1"), support.line(T0, "list")]))


if __name__ == "__main__":
    unittest.main()

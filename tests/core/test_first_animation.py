"""A board that has nothing takes its first animation: a file set without a mapping file
and without a show file plays on the installation's mapping with the empty show, the first
upload is accepted, and the change that writes the show file writes the mapping file first,
so that the folder is a whole installed file set from then on."""
import json
import unittest

from . import support
from .test_playback import T0

CHECK_STEPS = 60


def replies(lines):
    return [json.loads(line[len("reply "):]) for line in lines if line.startswith("reply ")]


def first_upload(data, name="first.odrg", pins=False):
    """The script of a first upload: the pieces of the file, then a refresh and `upload end`
    at each step until the check of the file has settled, then `status` and `list`, and
    with `pins` also `mapping get`, which the reference player does not answer."""
    script = [support.line(T0, line) for line in support.upload_lines(1, name, data)]
    for step in range(1, CHECK_STEPS + 1):
        script += [f"poll {T0 + 20 * step}", support.line(T0 + 20 * step, support.upload_end(data))]
    at = T0 + 20 * (CHECK_STEPS + 1)
    script += [support.line(at, "status"), support.line(at, "list")]
    return script + [support.line(at, "mapping get")] if pins else script


class TheFirstAnimation(unittest.TestCase):
    def setUp(self):
        self.clip = support.clip(1, 60, 60)

    def test_the_first_upload_into_an_empty_file_set_plays_and_leaves_a_whole_file_set(self):
        script = first_upload(self.clip)
        run, left = support.start_and_keep({}, script)
        self.assertIsNone(run.error)
        reference = support.ReferencePlayer({})
        expected = reference.run(script)
        self.assertEqual(len(run.lines), len(expected))
        for number, (line, wanted) in enumerate(zip(run.lines, expected)):
            if line != wanted:
                self.fail(f"line {number} differs: the core printed {line[:90]}, the reference {wanted[:90]}")
        answers = replies(run.lines)
        self.assertEqual(answers[0], {"ok": True, "chunk": 1500})
        self.assertIn({"ok": True}, answers)
        status, listed = answers[-2:]
        self.assertEqual((status["error"], status["playing"], status["animation"], status["width"], status["height"]), (None, "all", 1, 60, 60))
        self.assertEqual([(item["id"], item["file"]) for item in listed["items"]], [(1, "first.odrg")])
        self.assertEqual(sorted(left), ["first.odrg", "mapping.json", "show.json"])
        self.assertEqual(left["mapping.json"], support.TARGET_MAPPING.read_bytes())
        self.assertEqual(left["first.odrg"], self.clip)
        self.assertEqual(json.loads(left["show.json"]), {"version": 1, "brightness": 128, "items": [{"id": 1, "file": "first.odrg"}]})
        self.assertEqual(left, reference.files)
        # The next start reads the files written: the mapping is the file's from then on.
        again = support.start(left, [support.line(T0, "mapping get"), support.line(T0, "status")], ["--trace-files"])
        self.assertEqual(again.opened.count(("mapping.json", 1)), 2)
        pins, status = replies(again.lines)
        self.assertEqual((pins["editable"], pins["pins"][:3], status["animation"]), (True, [1, 2, 3], 1))

    def test_a_mapping_file_that_cannot_be_written_refuses_the_change_and_leaves_no_part(self):
        script = first_upload(self.clip, pins=True)
        traced = support.start({}, script, ["--trace-store"])
        calls = [line for line in traced.lines if line.startswith("store ") and not line.startswith("store write ")]
        at = next(number for number, line in enumerate(calls, start=1) if line.startswith("store write_open mapping.part"))
        run, left = support.start_and_keep({}, script, ["--store-fails-at", str(len(traced.stored) + at)])
        self.assertIsNone(run.error)
        answers = replies(run.lines)
        self.assertIn({"ok": False, "error": "storage-error"}, answers)
        self.assertNotIn({"ok": True}, answers)
        status, listed, pins = answers[-3:]
        self.assertEqual((status["error"], status["playing"], status["width"]), (None, None, 60))
        self.assertEqual(listed["items"], [])
        self.assertTrue(pins["editable"])
        self.assertEqual(left, {})

    def test_a_show_file_without_a_mapping_file_plays_on_the_built_in_mapping_and_writes_nothing(self):
        files = support.demo_show()
        del files["mapping.json"]
        run, left = support.start_and_keep(files, [support.line(T0, "status")], ["--trace-store"])
        self.assertIsNone(run.error)
        status = replies(run.lines)[0]
        self.assertEqual((status["playing"], status["animation"], status["width"], status["height"]), ("all", 1, 60, 60))
        self.assertFalse(any(line.startswith("store ") for line in run.lines))
        self.assertEqual(left, {name: content if isinstance(content, bytes) else content.encode() for name, content in files.items()})

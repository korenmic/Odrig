"""The live changes of the installed show: what each writes, an upload of a file the show
holds already, the cleanup a change leaves unfinished, and power cuts and failures at every
storage call of `remove many`, `ignore` and the start's cleanup."""

import json
import unittest
import zlib

from . import support
from .test_content import animation, cycle, small_show
from .test_powercut import POWER_CUT, PowerCut, as_bytes, storage_calls

T0 = 1000
OK = 'reply {"ok":true}'
UNCHANGED = 'reply {"ok":true,"unchanged":true}'
CHUNK = 'reply {"ok":true,"chunk":1500}'
NEW_CHUNK = 'reply {"ok":true,"chunk":1500,"replacing":false}'
REPLACE_CHUNK = 'reply {"ok":true,"chunk":1500,"replacing":true}'
STORAGE_ERROR = 'reply {"ok":false,"error":"storage-error"}'


def hundred_items():
    """A show of 100 items on the target file: 80 animations, each with a file of its own,
    and 20 cycles of the first 40 of them."""
    items = [{"id": number, "file": f"clip-{number:02d}.odrg"} for number in range(1, 81)]
    items += [{"id": 80 + number, "cycle": [1 + (number + entry) % 40 for entry in range(4)], "seconds": number} for number in range(1, 21)]
    files = {"mapping.json": support.mapping_texts()["legs-20"], "show.json": support.show_text(items, 40, 100)}
    files.update({item["file"]: support.clip(item["id"], 60, 60, (20, 20)) for item in items[:80]})
    return files


def begin(number, name, data, crc=None):
    """`upload begin` of a file, with its CRC-32 or the one given."""
    return f"upload begin {number} {name} {len(data)} {zlib.crc32(data) if crc is None else crc:08x}"


def upload(number, name, data, at=T0):
    """The lines of a session that upload a file and wait for its check."""
    lines = [support.line(at, line) for line in support.upload_lines(number, name, data)]
    lines += [f"poll {at + 20 * step}" for step in range(1, 12)]
    return lines + [support.line(at + 240, support.upload_end(data))]


def stored(run):
    """The storage calls of a session after its start, as the test host traces them."""
    return [line[len("store "):] for line in run.lines if line.startswith("store ")]


def written(calls):
    """The bytes of every `write` among storage calls."""
    return sum(int(call.split()[1]) for call in calls if call.startswith("write "))


def touched(calls):
    """The names of the files storage calls open for writing, rename or remove."""
    names = set()
    for call in calls:
        word, *rest = call.split()
        if word in ("write_open", "remove"):
            names.add(rest[0])
        elif word == "rename":
            names.update(rest[:2])
    return names


class OneChange(unittest.TestCase):
    """What a change of one animation of a show of 100 items writes."""

    @classmethod
    def setUpClass(cls):
        cls.files = hundred_items()
        cls.new = support.clip(101, 60, 60, (20, 20, 20))

    def change(self, script):
        run, left = support.start_and_keep(self.files, script, ["--trace-store"])
        self.assertIsNone(run.error)
        calls = stored(run)
        for name, content in as_bytes(self.files).items():
            if name not in touched(calls):
                self.assertEqual(left.get(name), content, name)
        return run, left, calls

    def test_a_removal_writes_pending_txt_and_the_show_file(self):
        run, left, calls = self.change([support.line(T0, "remove 60")])
        self.assertEqual([line for line in run.lines if line.startswith("reply")], [OK])
        self.assertEqual(touched(calls), {"pending.txt", "show.part", "show.json", "clip-60.odrg"})
        self.assertEqual(written(calls), len("clip-60.odrg\n") + len(left["show.json"]))
        self.assertNotIn("clip-60.odrg", left)

    def test_an_addition_writes_the_file_pending_txt_and_the_show_file(self):
        run, left, calls = self.change(upload(101, "new.odrg", self.new))
        self.assertEqual([line for line in run.lines if line.startswith("reply")][-1], OK)
        self.assertEqual(touched(calls), {"upload.part", "new.odrg", "pending.txt", "show.part", "show.json"})
        self.assertEqual(written(calls), len(self.new) + len("new.odrg\n") + len(left["show.json"]))

    def test_a_replacement_under_its_name_writes_the_file(self):
        run, left, calls = self.change(upload(70, "clip-70.odrg", self.new))
        self.assertEqual([line for line in run.lines if line.startswith("reply")][-1], OK)
        self.assertEqual(touched(calls), {"upload.part", "clip-70.odrg"})
        self.assertEqual(written(calls), len(self.new))
        self.assertEqual(left["clip-70.odrg"], self.new)

    def test_the_same_upload_again_writes_nothing(self):
        once, _, calls = self.change(upload(70, "clip-70.odrg", self.new))
        again, left, calls_again = self.change(upload(70, "clip-70.odrg", self.new) + [support.line(T0 + 300, begin(70, "clip-70.odrg", self.new))])
        self.assertEqual(again.lines[-1], UNCHANGED)
        self.assertEqual(calls_again, calls)
        self.assertEqual(left["clip-70.odrg"], self.new)


class Unchanged(unittest.TestCase):
    FILES = small_show([animation(1, "one.odrg"), animation(2, "two.odrg"), cycle(3, [1, 2], 1)], start=1)
    NEW = support.clip(9, 60, 6, (20, 20))

    def replies(self, script, options=(), check_first=True):
        run = support.start(self.FILES, script, options, check_first=check_first)
        return [line for line in run.lines if line.startswith("reply")]

    def after_the_upload(self, *lines):
        """The replies to these lines after the upload of NEW as the file of item 1."""
        replies = self.replies(upload(1, "one.odrg", self.NEW) + [support.line(T0 + 300, line) for line in lines])
        self.assertEqual(replies[-len(lines) - 1], OK)
        return replies[-len(lines):]

    def test_it_is_answered_only_for_the_last_uploads_id_file_size_and_crc32(self):
        new = self.NEW
        for line, reply in ((begin(1, "one.odrg", new), UNCHANGED),
                            (begin(1, "one.odrg", new, zlib.crc32(new) ^ 1), REPLACE_CHUNK),
                            (begin(1, "one.odrg", new + b"x"), REPLACE_CHUNK),
                            (begin(1, "other.odrg", new), REPLACE_CHUNK),
                            (begin(1, "two.odrg", new), 'reply {"ok":false,"error":"in-use"}'),
                            (begin(9, "one.odrg", new), 'reply {"ok":false,"error":"in-use"}'),
                            (begin(3, "one.odrg", new), 'reply {"ok":false,"error":"in-use"}'),
                            (begin(1, "one.odrg", new).replace(f"{zlib.crc32(new):08x}", f"{zlib.crc32(new):08X}"), 'reply {"ok":false,"error":"bad-argument"}'),
                            (begin(1, "one.odrg", new) + " 0", 'reply {"ok":false,"error":"bad-argument"}')):
            with self.subTest(line=line):
                self.assertEqual(self.after_the_upload(line), [reply])

    def test_an_upload_begun_since_makes_it_unknown(self):
        self.assertEqual(self.after_the_upload("upload begin 9 new.odrg 100", "upload cancel", begin(1, "one.odrg", self.NEW)), [CHUNK, OK, REPLACE_CHUNK])

    def test_a_removed_item_is_uploaded_anew(self):
        replies = self.replies(upload(9, "nine.odrg", self.NEW) + [support.line(T0 + 300, "remove 9"), support.line(T0 + 300, begin(9, "nine.odrg", self.NEW))])
        self.assertEqual(replies[-3:], [OK, OK, NEW_CHUNK])

    def test_a_file_the_check_read_and_no_upload_installed_is_uploaded(self):
        one = as_bytes(self.FILES)["one.odrg"]
        self.assertEqual(self.replies([support.line(T0, begin(1, "one.odrg", one))]), [REPLACE_CHUNK])

    def test_the_form_without_the_crc32_is_as_before(self):
        one = as_bytes(self.FILES)["one.odrg"]
        self.assertEqual(self.replies([support.line(T0, f"upload begin 1 one.odrg {len(one)}")]), [CHUNK])


class Cleanup(PowerCut):
    """The cleanup a change leaves unfinished when it cannot remove a file."""

    FILES = small_show([animation(1, "one.odrg"), animation(2, "two.odrg"), animation(4, "four.odrg")], start=1)

    def failing_removal(self):
        """The number of the storage call that removes `one.odrg` in `remove 1`."""
        calls = storage_calls(self.FILES, [support.line(T0, "remove 1")])
        return calls.index("remove one.odrg 1") + 1

    def test_the_next_change_finishes_it_first(self):
        at = self.failing_removal()
        for later in ("remove 2", "ignore 2 1", "remove many 2"):
            with self.subTest(change=later):
                run, left = support.start_and_keep(self.FILES, [support.line(T0, "remove 1"), support.line(T0, later)], ["--store-fails-at", str(at)])
                self.assertEqual([line for line in run.lines if line.startswith("reply")], [OK, OK])
                self.assertNotIn("one.odrg", left)
                self.assertNotIn("pending.txt", left)
                self.assertIn("four.odrg", left)

    def test_while_it_still_fails_a_change_is_refused_and_the_next_start_finishes_it(self):
        script = [support.line(T0, "remove 1"), support.line(T0, "remove 2")]
        with support.installed(self.FILES) as folder:
            run = support.session(folder, script, ["--store-fails-at", str(self.failing_removal()), "--read-fails", "pending.txt", "0"])
            self.assertEqual([line for line in run.lines if line.startswith("reply")], [OK, STORAGE_ERROR])
            self.assertEqual(sorted(support.folder_files(folder)), ["four.odrg", "mapping.json", "one.odrg", "pending.txt", "show.json", "two.odrg"])
            support.session(folder, [])
            self.assertEqual(sorted(support.folder_files(folder)), ["four.odrg", "mapping.json", "show.json", "two.odrg"])

    def test_a_cleanup_never_removes_a_file_the_show_names(self):
        files = dict(self.FILES, **{"pending.txt": b"one.odrg\ngone.odrg\n", "gone.odrg": b"x"})
        run, left = support.start_and_keep(files, [support.line(T0, "list")])
        self.assertEqual(sorted(left), ["four.odrg", "mapping.json", "one.odrg", "show.json", "two.odrg"])

    def test_a_power_cut_at_each_storage_call_of_the_starts_cleanup_comes_to_the_same_folder(self):
        files = dict(self.FILES, **{"pending.txt": b"one.odrg\ngone.odrg\nlost.odrg\n", "gone.odrg": b"x", "lost.odrg": b"y"})
        calls = storage_calls(files, [])
        self.assertEqual(calls[2:], ["remove gone.odrg 1", "remove lost.odrg 1", "remove pending.txt 1"])
        for at in range(1, len(calls) + 1):
            with self.subTest(cut=calls[at - 1]), support.installed(files) as folder:
                for _ in range(2):
                    cut = support.host("session", folder, support.CHECK_FIRST, "--cut-at", str(at))
                    self.assertIn(cut.status, (0, POWER_CUT))
                support.session(folder, [support.line(T0, "list")])
                self.assertEqual(support.folder_files(folder), as_bytes(self.FILES))


class ManyAndIgnore(PowerCut):
    """A power cut and a failure at every storage call of `remove many` and `ignore`."""

    ITEMS = [animation(1, "one.odrg"), animation(2, "two.odrg"), cycle(3, [1], 1), animation(4, "four.odrg"), animation(5, "two.odrg")]
    CHANGES = {
        "remove many of files of their own": (ITEMS, "remove many 2,4"),
        "remove many of an animation whose file another item names": (ITEMS, "remove many 5"),
        "remove many of the animation that plays": (ITEMS, "remove many 4"),
        "ignore": (ITEMS, "ignore 4 1"),
        "include again": (ITEMS[:3] + [dict(ITEMS[3], ignored=True)] + ITEMS[4:], "ignore 4 0"),
    }

    def outcomes(self, items, line):
        files = small_show(items, start=4)
        script = [f"poll {T0}", support.line(T0, line)]
        run, new = support.start_and_keep(files, script)
        self.assertEqual([entry for entry in run.lines if entry.startswith("reply")], [OK], line)
        return files, as_bytes(files), new, script

    def test_a_power_cut_at_each_storage_call_leaves_the_old_show_or_the_new_one(self):
        for kind, (items, line) in self.CHANGES.items():
            files, old, new, script = self.outcomes(items, line)
            calls = storage_calls(files, script)
            arrow = calls.index("rename show.part show.json 1") + 1
            for at, keeps in self.cuts_of(calls):
                what = f"{kind}: cut at storage call {at}, `{calls[at - 1]}`, with {keeps} of its bytes written"
                as_left, again, after = self.cut(files, script, at, keeps)
                self.assertIsNone(again.error, what)
                self.assertEqual(after, old if at <= arrow else new, what)
                self.assertIn(as_left["show.json"], (old["show.json"], new["show.json"]), what)

    def test_a_storage_call_that_fails_gives_storage_error_and_the_old_show_or_the_new_one(self):
        for kind, (items, line) in self.CHANGES.items():
            files, old, new, script = self.outcomes(items, line)
            calls = storage_calls(files, script)
            arrow = calls.index("rename show.part show.json 1") + 1
            for at in range(3, len(calls) + 1):
                what = f"{kind}: storage call {at}, `{calls[at - 1]}`, fails"
                run, left = support.start_and_keep(files, script, ["--store-fails-at", str(at)])
                replies = [entry for entry in run.lines if entry.startswith("reply")]
                if at <= arrow:
                    self.assertEqual((replies, left), ([STORAGE_ERROR], old), what)
                else:
                    self.assertEqual(replies, [OK], what)
                    self.assertEqual({name: content for name, content in left.items() if name in new}, new, what)
                    with support.installed(left) as folder:
                        support.session(folder, [support.line(T0, "list")])
                        self.assertEqual(support.folder_files(folder), new, what)


if __name__ == "__main__":
    unittest.main()

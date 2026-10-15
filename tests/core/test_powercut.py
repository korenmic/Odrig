import json
import unittest

from . import support
from .test_content import animation, cycle, small_show

T0 = 1000
OK = 'reply {"ok":true}'
STORAGE_ERROR = 'reply {"ok":false,"error":"storage-error"}'
POWER_CUT = 75

ITEMS = [animation(1, "one.odrg"), animation(2, "two.odrg"), cycle(3, [1, 2], 1), animation(4, "four.odrg"), animation(5, "two.odrg"), cycle(6, [4, 5, 4], 2)]

# Each kind of removal: the items of the show, its `start`, and the id that is removed.
REMOVALS = {
    "an animation with a file of its own": (ITEMS[:2] + ITEMS[3:], 6, 1),
    "an animation whose file another item names": (ITEMS[:2] + ITEMS[3:5], 2, 5),
    "a cycle": (ITEMS, 6, 3),
    "the cycle that plays and is the start item": (ITEMS, 6, 6),
    "the animation that plays": (ITEMS[:2] + ITEMS[3:], 1, 1),
    "the last item": ([animation(9, "only.odrg")], 9, 9),
}


def as_bytes(files):
    return {name: content if isinstance(content, bytes) else content.encode("utf-8") for name, content in files.items()}


def changed(files, lines):
    """The files of the folder after these command lines, as the reference player has
    them, and its replies."""
    reference = support.ReferencePlayer(files)
    replies = [reference.command(T0, line.encode("ascii")).decode("ascii").rstrip("\n") for line in lines]
    return reference.files, replies


def changed_by(files, script):
    """The files of the folder after a session, as the reference player has them, and the
    lines it prints for the replies."""
    reference = support.ReferencePlayer(files)
    printed = reference.run(script)
    return reference.files, [line for line in printed if line.startswith("reply")]


def storage_calls(files, script):
    """The storage calls of a session, the two of the start among them, as the test host
    traces them."""
    run = support.start(files, script, ["--trace-store"])
    return list(run.stored) + [line[len("store "):] for line in run.lines if line.startswith("store ")]


class PowerCut(unittest.TestCase):
    def cut(self, files, script, number, keeps=0):
        """Runs a session whose power is cut at a storage call, then starts the core again
        on the folder. Returns the folder as the cut left it, the second run, and the
        folder after it."""
        with support.installed(files) as folder:
            result = support.host("session", folder, support.CHECK_FIRST, "--cut-at", number, "--cut-keeps", keeps, stdin="".join(f"{line}\n" for line in script).encode("ascii"))
            self.assertEqual((result.status, result.err), (POWER_CUT, ""), result.out[-300:])
            self.assertTrue(result.out.endswith("power cut\n"))
            as_left = support.folder_files(folder)
            again = support.session(folder, [support.line(T0, "list"), support.line(T0, "status"), f"poll {T0}", f"poll {T0 + 20}"])
            return as_left, again, support.folder_files(folder)

    def assert_a_whole_show(self, again, after, expected, what):
        """The second start found a valid show, the folder holds exactly its files, and
        the core lists what a core started on those files lists."""
        self.assertIsNone(again.error, what)
        self.assertEqual(sorted(after), sorted(expected), what)
        self.assertEqual(after, expected, what)
        self.assertEqual(again.lines, support.ReferencePlayer(expected).run([support.line(T0, "list"), support.line(T0, "status"), f"poll {T0}", f"poll {T0 + 20}"]), what)

    def cuts_of(self, calls):
        """`(number, keeps)` for a cut at every storage call, and inside every write."""
        cuts = []
        for number, call in enumerate(calls, start=1):
            cuts.append((number, 0))
            if call.startswith("write "):
                size = int(call.split()[1])
                cuts += [(number, keeps) for keeps in sorted({1, size // 2, size - 1}) if 0 < keeps < size]
        return cuts


class Removal(PowerCut):
    def test_a_power_cut_at_each_storage_call_leaves_the_old_show_or_the_new_one(self):
        for kind, (items, start, number) in REMOVALS.items():
            files = small_show(items, start=start)
            old = as_bytes(files)
            new, replies = changed(files, [f"remove {number}"])
            self.assertEqual(replies, ['{"ok":true}'], kind)
            script = [f"poll {T0}", support.line(T0, f"remove {number}")]
            calls = storage_calls(files, script)
            arrow = calls.index("rename show.part show.json 1") + 1
            self.assertGreaterEqual(len(calls), 6, kind)
            outcomes = set()
            for at, keeps in self.cuts_of(calls):
                what = f"{kind}: cut at storage call {at}, `{calls[at - 1]}`, with {keeps} of its bytes written"
                as_left, again, after = self.cut(files, script, at, keeps)
                expected = old if at <= arrow else new
                self.assert_a_whole_show(again, after, expected, what)
                outcomes.add(at <= arrow)
                # What the cut left is the old show file or the new one, never a part of one.
                self.assertIn(as_left["show.json"], (old["show.json"], new["show.json"]), what)
            # A removal that deletes no file ends with the rename: no cut falls after it.
            self.assertEqual(outcomes, {True, False} if arrow < len(calls) else {True}, kind)

    def test_a_storage_call_that_fails_gives_storage_error_and_the_old_show_or_the_new_show_whole(self):
        for kind, (items, start, number) in REMOVALS.items():
            files = small_show(items, start=start)
            old = as_bytes(files)
            new, _ = changed(files, [f"remove {number}"])
            script = [f"poll {T0}", support.line(T0, f"remove {number}"), support.line(T0, "list"), f"poll {T0 + 20}", support.line(T0 + 20, "status")]
            plain = [f"poll {T0}", support.line(T0, "list"), f"poll {T0 + 20}", support.line(T0 + 20, "status")]
            calls = storage_calls(files, script)
            arrow = calls.index("rename show.part show.json 1") + 1
            for at in range(1, len(calls) + 1):
                what = f"{kind}: storage call {at}, `{calls[at - 1]}`, fails"
                run, left = support.start_and_keep(files, script, ["--store-fails-at", str(at)])
                self.assertIsNone(run.error, what)
                if 2 < at <= arrow:
                    # Before the show changed: the reply says so, nothing is left, and the
                    # core goes on with the show it had.
                    self.assertEqual(run.lines[run.lines.index(f"refresh {T0}") + 3], STORAGE_ERROR, what)
                    self.assertEqual(left, old, what)
                    self.assertEqual([line for line in run.lines if line != STORAGE_ERROR], support.ReferencePlayer(files).run(plain), what)
                else:
                    # The start's own removals, which find nothing, or a call after the
                    # show changed: the change stands.
                    self.assertEqual(run.lines, support.ReferencePlayer(files).run(script), what)
                    self.assertEqual({name: content for name, content in left.items() if name in new}, new, what)
                    with support.installed(left) as folder:
                        again = support.session(folder, [support.line(T0, "list")])
                        self.assertIsNone(again.error, what)
                        self.assertEqual(support.folder_files(folder), new, what)

    def test_what_is_left_after_a_failed_removal_of_the_file_is_removed_at_the_next_start(self):
        items, start, number = REMOVALS["an animation with a file of its own"]
        files = small_show(items, start=start)
        script = [support.line(T0, f"remove {number}")]
        calls = storage_calls(files, script)
        at = calls.index("remove one.odrg 1") + 1
        run, left = support.start_and_keep(files, script, ["--store-fails-at", str(at), "--trace-store"])
        self.assertEqual([line for line in run.lines if line.startswith("reply")], [OK])
        self.assertIn("one.odrg", left)
        self.assertEqual(left["pending.txt"], b"one.odrg\n")
        self.assertEqual([line for line in run.lines if line.startswith("store ")][-1], "store remove one.odrg -1")
        with support.installed(left) as folder:
            again = support.session(folder, [], ["--trace-store"])
            self.assertEqual(again.stored, ("remove upload.part 0", "remove show.part 0", "remove one.odrg 1", "remove pending.txt 1"))
            self.assertEqual(sorted(support.folder_files(folder)), ["four.odrg", "mapping.json", "show.json", "two.odrg"])


class Upload(PowerCut):
    """A power cut, and a storage call that fails, at each storage call of each kind of
    upload: while the bytes arrive, and while the file is put in place."""

    CLIP = support.clip(71, 60, 6, (20, 40))

    # Each kind of upload: the items of the show, its `start`, the id and the file name.
    KINDS = {
        "a new item": (ITEMS, 6, 9, "new.odrg"),
        "a new item in a show without items": ([], None, 1, "first.odrg"),
        "the file of an item under the same name": (ITEMS, 1, 1, "one.odrg"),
        "the file of the item that plays under another name": (ITEMS, 4, 4, "other.odrg"),
        "the file of an item of the playing cycle under another name": (ITEMS, 3, 1, "other.odrg"),
        "an item whose old file another item names": (ITEMS, 6, 5, "five.odrg"),
    }

    def script(self, number, name, more=()):
        made = [f"poll {T0}", f"poll {T0 + 20}"]
        made += [support.line(T0 + 20, line) for line in support.upload_lines(number, name, self.CLIP, 150)]
        made += [f"poll {T0 + 40 + 20 * step}" for step in range(4)]
        made += [support.line(T0 + 120, support.upload_end(self.CLIP))]
        return made + list(more)

    def arrow(self, calls, number, name, items):
        """The number of the storage call at which the show changes."""
        same_name = any(item.get("file") == name and item["id"] == number for item in items)
        return calls.index(f"rename upload.part {name} 1" if same_name else "rename show.part show.json 1") + 1

    def test_a_power_cut_at_each_storage_call_leaves_the_old_show_or_the_new_one(self):
        for kind, (items, start, number, name) in self.KINDS.items():
            files = small_show(items, start=start)
            old = as_bytes(files)
            script = self.script(number, name)
            new, replies = changed_by(files, script)
            self.assertEqual(replies[-1], OK, kind)
            self.assertEqual(new[name], self.CLIP, kind)
            calls = storage_calls(files, script)
            arrow = self.arrow(calls, number, name, items)
            self.assertGreaterEqual(len([call for call in calls if call.startswith("write ")]), 2, kind)
            for at, keeps in self.cuts_of(calls):
                what = f"{kind}: cut at storage call {at}, `{calls[at - 1]}`, with {keeps} of its bytes written"
                as_left, again, after = self.cut(files, script, at, keeps)
                self.assert_a_whole_show(again, after, old if at <= arrow else new, what)
                self.assertIn(as_left["show.json"], (old["show.json"], new["show.json"]), what)

    def test_a_storage_call_that_fails_gives_storage_error_and_the_old_show_or_the_new_show_whole(self):
        asked = [support.line(T0 + 120, "upload cancel"), support.line(T0 + 120, "list"), f"poll {T0 + 120}", f"poll {T0 + 140}", support.line(T0 + 140, "status")]
        for kind, (items, start, number, name) in self.KINDS.items():
            files = small_show(items, start=start)
            old = as_bytes(files)
            script = self.script(number, name, asked)
            new, _ = changed_by(files, script)
            calls = storage_calls(files, script)
            arrow = self.arrow(calls, number, name, items)
            listed_old = support.ReferencePlayer(files).run([support.line(T0, "list")])[0]
            for at in range(1, len(calls) + 1):
                what = f"{kind}: storage call {at}, `{calls[at - 1]}`, fails"
                run, left = support.start_and_keep(files, script, ["--store-fails-at", str(at)])
                self.assertIsNone(run.error, what)
                given = [line for line in run.lines if line.startswith("reply")]
                if 2 < at <= arrow:
                    # Before the show changed: one reply says `storage-error`, the upload
                    # is gone, nothing is left of it, and the core has the show it had.
                    self.assertEqual(given.count(STORAGE_ERROR), 1, what)
                    self.assertNotIn(OK, given[:-3], what)
                    self.assertEqual(given[-3:-1], ['reply {"ok":false,"error":"no-upload"}', listed_old], what)
                    self.assertEqual(left, old, what)
                else:
                    # The start's own removals, which find nothing, or a call after the
                    # show changed: the change stands, and the next start clears up.
                    self.assertEqual(run.lines, support.ReferencePlayer(files).run(script), what)
                    self.assertEqual({name_: content for name_, content in left.items() if name_ in new}, new, what)
                    with support.installed(left) as folder:
                        again = support.session(folder, [support.line(T0, "list")])
                        self.assertIsNone(again.error, what)
                        self.assertEqual(support.folder_files(folder), new, what)

    def test_a_restart_in_each_state_of_an_upload_leaves_the_old_show_and_nothing_of_the_upload(self):
        files = small_show(ITEMS, start=6)
        old = as_bytes(files)
        lines = support.upload_lines(9, "new.odrg", self.CLIP, 150)
        states = {
            "begun": [support.line(T0, lines[0])],
            "some bytes": [support.line(T0, line) for line in lines[:3]],
            "all bytes": [support.line(T0, line) for line in lines],
            "the check half done": [f"poll {T0}"] + [support.line(T0, line) for line in lines] + [f"poll {T0 + 20}", f"poll {T0 + 40}"],
            "the check done": [f"poll {T0}"] + [support.line(T0, line) for line in lines] + [f"poll {T0 + 20 * step}" for step in range(1, 6)],
        }
        for state, script in states.items():
            with self.subTest(state=state), support.installed(files) as folder:
                first = support.session(folder, script)
                self.assertIsNone(first.error)
                self.assertIn("upload.part", support.folder_files(folder))
                again = support.session(folder, [support.line(T0, "list"), support.line(T0, "upload cancel"), support.line(T0, "upload end 00000000")], ["--trace-store"])
                self.assertEqual(again.stored, ("remove upload.part 1", "remove show.part 0"))
                self.assertEqual(again.lines[1:], ['reply {"ok":false,"error":"no-upload"}'] * 2)
                self.assertEqual(support.folder_files(folder), old)


if __name__ == "__main__":
    unittest.main()

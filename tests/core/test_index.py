"""A drive read from its index: every file and folder of it at once, past 256 files and 32
folders, in the drive's walk; and an upload, a removal and a rebuild of its catalog that
leave the same files as the PC tool."""

import functools
import unittest

from odrig import catalog

from . import support
from .test_catalog_drive import card, polls
from .test_catalog_writes import run_on_card, upload_external
from .test_drive import SHOW, a_drive, asked, replies
from .test_playback import T0
from .test_playlist import CANVAS, loop_of

# 300 files in 40 folders to three levels: 20 in the root and 7 in each folder.
FOLDERS = [path for top in range(13) for path in (f"t{top:02d}", f"t{top:02d}/a", f"t{top:02d}/b")] + ["t00/a/deep"]
BIG = {f"r{number:02d}.odrg": loop_of(2, number + 1) for number in range(20)}
BIG.update({f"{folder}/c{number}.odrg": loop_of(2, number + 21) for folder in FOLDERS for number in range(7)})


@functools.lru_cache(maxsize=None)
def big_card():
    return card(BIG)


def index_of(files):
    """The index the PC tool reads from a card's files."""
    return catalog.read(catalog.MemoryStorage(files, drive=True)).index


def on_card(files, script, options=()):
    with a_drive(files) as top:
        return support.start(SHOW, polls(0, 50) + script, ["--drive", top, *options], check_first=False)


def levels(index):
    """For each level of an index, the root's first and then each folder's in the table's
    order: its `list` or `list in <id>`, and the ids and the files or paths of its items in
    their order, the root's after the show's item."""
    ends = index.ends()
    found = []
    for ordinal, folder in enumerate(index.folders):
        items = [(1, "four.odrg")] if ordinal == 0 else []
        items += [(index.folders[child].id, index.folders[child].path) for child in index.children(ordinal)]
        items += [(file_id, entry.name) for file_id, entry in folder.rows]
        found.append(("list" if ordinal == 0 else f"list in {folder.id}", items))
    assert len(ends) == len(found)
    return found


def every_page(levels_asked):
    """The commands that ask each level from each of its positions on."""
    return [f"{command} {start}" for command, items in levels_asked for start in range(len(items))]


def followed(answers, sizes):
    """The items of each level, its pages followed from the first: `answers` holds a reply for
    each position of each level, in the order of `every_page`."""
    found = []
    at = 0
    for size in sizes:
        own = answers[at:at + size]
        items = []
        position = 0
        while position is not None:
            items += [(item["id"], item.get("file", item.get("playlist"))) for item in own[position]["items"]]
            position = own[position]["next"]
        found.append(items)
        at += size
    return found


class TheIndexAtOnce(unittest.TestCase):
    def test_every_level_lists_its_folders_and_files_past_the_256th(self):
        files = big_card()
        expected = levels(index_of(files))
        run = on_card(files, asked(1100, "catalog", *every_page(expected)))
        answers = replies(run)
        self.assertEqual(answers[0]["external"], {"state": "ok", "generation": 1, "entries": 300, "writable": True})
        self.assertEqual(followed(answers[1:], [len(items) for _, items in expected]), [items for _, items in expected])
        listed = [item for _, items in expected for item in items]
        self.assertEqual(sorted(file_id for file_id, name in listed if name.endswith(".odrg") and file_id != 1), list(range(60001, 60301)))
        self.assertEqual(sorted(file_id for file_id, name in listed if not name.endswith(".odrg")), list(range(60301, 60341)))

    def test_no_page_and_no_animation_is_read_to_publish_it(self):
        run = on_card(big_card(), asked(1100, "list 0"), ["--trace-read-at"])
        names = {line.split(" ")[1] for line in run.lines if line.startswith("read_at drive/")}
        self.assertIn("drive/catalog.txt", names)
        self.assertLessEqual({name for name in names if not name.startswith("drive/index-")}, {"drive/catalog.do", "drive/catalog.txt"})
        self.assertFalse(any(line.startswith(("drive list", "drive bind")) for line in run.lines))

    def test_a_file_past_the_256th_plays_and_status_names_it(self):
        run = on_card(big_card(), asked(1100, "play 60300") + asked(1200, "status", "read 60300 0"))
        played, status, read = replies(run)
        self.assertEqual(played, {"ok": True})
        self.assertEqual((status["animation"], status["file"]), (60300, "t12/b/c6.odrg"))
        self.assertEqual(read["bytes"], len(BIG["t12/b/c6.odrg"]))

    def test_the_walk_goes_on_past_the_256th_file(self):
        script = asked(1100, "play 60250")
        script += [line for second in range(1, 60) for line in asked(1100 + 1000 * second, "status")]
        run = on_card(big_card(), script)
        seen = []
        for reply in replies(run)[1:]:
            if not seen or seen[-1] != reply["animation"]:
                seen.append(reply["animation"])
        self.assertGreater(len(seen), 10)
        self.assertEqual(seen, list(range(60250, 60250 + len(seen))))

    def test_a_folder_past_the_32nd_is_a_playlist(self):
        run = on_card(big_card(), asked(1100, "play 60340") + asked(1200, "status"))
        status = replies(run)[1]
        self.assertEqual((status["animation"], status["playlist"]), (60294, "t12/b"))

    def test_an_id_the_map_does_not_hold_is_unknown(self):
        run = on_card(big_card(), asked(1100, "play 60341", "read 60341 0", "list in 60300", "list in 60341"))
        self.assertEqual([reply["error"] for reply in replies(run)], ["unknown-id"] * 4)

    def test_the_turns_read_a_row_each_and_not_the_library(self):
        # Fifteen turns of four seconds in the root's files: each reads the room that holds
        # its row, of at most 512 bytes, and nothing more of the index.
        script = asked(1100, "play 60001") + polls(1120, 3000)
        run = on_card(big_card(), script, ["--trace-read-at"])
        started = next(at for at, line in enumerate(run.lines) if line.startswith("reply "))
        read = [line.split(" ") for line in run.lines[started:] if line.startswith("read_at drive/index-")]
        self.assertLessEqual(sum(int(fields[3]) for fields in read), 16 * 512)
        self.assertEqual({fields[1] for fields in read}, {"drive/index-0.txt"})

    def test_a_file_that_fails_while_it_plays_is_left_out_and_remembered(self):
        files = dict(big_card())
        files["r05.odrg"] = files["r05.odrg"][:-6]
        run = on_card(files, asked(1100, "play 60006") + polls(1120, 300) + asked(7200, "list 14", "status", "play 60006"))
        listed, status, played = replies(run)[1:]
        self.assertEqual([(item["id"], item["bytes"], item["fault"]) for item in listed["items"] if "fault" in item], [(60006, None, "truncated")])
        self.assertEqual(status["unavailable"], 1)
        self.assertEqual(played["error"], "unavailable")
        self.assertIn("drive file r05.odrg left out: truncated", [line[len("log "):] for line in run.lines if line.startswith("log ")])

    def test_a_drive_without_a_catalog_takes_its_first_files_to_the_32nd_folder(self):
        # The 33rd folder would be `t10/a`: 20 files of the root and 7 of each of 32 folders.
        run = on_card(BIG, polls(1100, 1500) + asked(31200, "list in 60276", "status"))
        folder, status = replies(run)
        self.assertEqual([(item["id"], item["file"]) for item in folder["items"]], [(60238 + number, f"t10/c{number}.odrg") for number in range(7)])
        self.assertEqual((status["checked"], status["to_check"]), (1 + 244, 0))


SMALL = {"sun.odrg": loop_of(2, 5), "x/other.odrg": loop_of(3, 6), "x/y/z/only.odrg": loop_of(2, 7), "night/comet.odrg": loop_of(3, 8)}


class ChangesOfTheIndex(unittest.TestCase):
    def test_an_upload_and_removals_leave_the_files_the_pc_tool_leaves(self):
        start = card(SMALL)
        new = loop_of(4, 9)
        ids = {entry.name: file_id for folder in index_of(start).folders for file_id, entry in folder.rows}
        script = polls(0, 50) + upload_external("new.odrg", new, T0 + 1100) + asked(2500, f"remove {ids['x/y/z/only.odrg']}", f"remove {ids['x/other.odrg']}", "list")
        run, left = run_on_card(start, script)
        storage = catalog.MemoryStorage(start, drive=True)
        catalog.add(storage, "new.odrg", new, canvas=CANVAS)
        catalog.remove(storage, "x/y/z/only.odrg")
        catalog.remove(storage, "x/other.odrg")
        self.assertEqual(left, storage.files)
        self.assertEqual(replies(run)[-1]["items"][-1]["id"], 60009)
        self.assertNotIn("index-60006.txt", left)

    def test_an_upload_to_a_big_card_takes_the_lowest_free_id(self):
        files = big_card()
        removed = 60010
        new = loop_of(4, 9)
        script = polls(0, 50) + asked(1100, f"remove {removed}") + upload_external("new.odrg", new, T0 + 1200) + asked(2000, "status", "list in 60301")
        run, left = run_on_card(files, script)
        self.assertEqual([reply for reply in replies(run) if set(reply) == {"ok", "id"}], [{"ok": True, "id": removed}])
        storage = catalog.MemoryStorage(dict(files), drive=True)
        catalog.remove(storage, index_of(files).folders[0].rows[9][1].name)
        catalog.add(storage, "new.odrg", new, canvas=CANVAS)
        self.assertEqual(left, storage.files)


def until_rebuilt(seconds):
    """Refreshes while the drive is read, `catalog rebuild external`, refreshes for so many
    seconds, and `catalog`."""
    return polls(0, 50) + asked(1100, "catalog rebuild external") + polls(1120, seconds * 50) + asked(1120 + seconds * 1000, "catalog")


class TheRebuild(unittest.TestCase):
    def test_a_drive_without_a_catalog_gets_the_index_the_pc_tool_makes(self):
        run, left = run_on_card(BIG, until_rebuilt(60))
        self.assertEqual(replies(run)[-1]["rebuild"], None)
        self.assertEqual(replies(run)[-1]["external"]["entries"], 300)
        self.assertEqual(left, big_card())

    def test_an_indexed_drive_rebuilt_drops_the_files_of_its_folders_that_went(self):
        start = dict(big_card())
        changed = {name: data for name, data in start.items() if not name.startswith("t12/b/")}
        changed["zz.odrg"] = loop_of(3, 4)
        run, left = run_on_card(changed, until_rebuilt(60) + asked(62200, "list in 60333"))
        storage = catalog.MemoryStorage(dict(changed), drive=True)
        catalog.rebuild(storage, canvas=CANVAS)
        self.assertEqual(left, storage.files)
        self.assertEqual(sorted(name for name in left if name.startswith("index-6")), [f"index-{number}.txt" for number in range(60295, 60334)])
        self.assertEqual(replies(run)[-1]["items"][0]["file"], "t12/a/c0.odrg")

    def test_a_cancelled_rebuild_leaves_nothing_of_it(self):
        for steps in (0, 5, 20, 60):
            with self.subTest(steps=steps):
                script = polls(0, 50) + asked(1100, "catalog rebuild external") + polls(1120, steps) + asked(1120 + 20 * steps, "catalog", "catalog cancel")
                run, left = run_on_card(big_card(), script + polls(1140 + 20 * steps, 10))
                self.assertIsNotNone(replies(run)[1]["rebuild"])
                self.assertEqual(left, big_card())


if __name__ == "__main__":
    unittest.main()

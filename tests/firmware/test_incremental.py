import random
import unittest

from fwtool import storage

from . import support

BLOCK = support.BLOCK_SIZE
# The storage of each layout, in blocks: WLED's and the bigger one.
LAYOUT_BLOCKS = {"WLED's": 0x9E0000 // BLOCK, "bigger": 0xCE0000 // BLOCK}
# The most blocks of the file system's own records that one change of a file writes beside
# the blocks of the file: its folder's metadata pair, which may be written anew whole, and
# the other pair a change may touch.
RECORD_BLOCKS = 4
SETTINGS = {path: content for path, content in support.WLED_FILES.items() if not path.startswith("/odrig/")}


def full_storage(blocks, seed, share=0.8):
    """A storage image of a layout's size that holds WLED's settings and a show whose
    animations fill about `share` of it: the files of `/odrig` by name, and the image."""
    chance = random.Random(seed)
    show = {"mapping.json": chance.randbytes(3000), "show.json": chance.randbytes(2500)}
    number = 0
    while sum(map(len, show.values())) < blocks * BLOCK * share:
        show[f"a{number:03d}.odrg"] = chance.randbytes(chance.randint(50000, 250000))
        number += 1
    image = support.storage_image(dict(SETTINGS, **{f"/odrig/{name}": content for name, content in show.items()}), blocks=blocks)
    return show, image


def file_blocks(size):
    """The blocks a file of this many bytes takes in the file system: a block from the
    second on begins with the addresses of the blocks before it that it points back to."""
    blocks, left = 0, size
    while left > 0:
        left -= BLOCK - (4 * (blocks & -blocks).bit_length() if blocks else 0)
        blocks += 1
    return blocks


def changed_blocks(old, new):
    return sum(len(content) for _, content in storage.runs(old, new, BLOCK)) // BLOCK


def applied(old, found):
    made = bytearray(old)
    for offset, content in found:
        made[offset:offset + len(content)] = content
    return bytes(made)


def one_file_changes(show, chance):
    """The four changes of one file, each the files of `/odrig` wanted afterwards and the
    names written: one animation removed, one added, one replaced, and nothing."""
    names = sorted(name for name in show if name.endswith(".odrg"))
    removed = dict(show, **{"show.json": chance.randbytes(2400)})
    del removed[names[len(names) // 2]]
    added = dict(show, **{"new.odrg": chance.randbytes(120000), "show.json": chance.randbytes(2600)})
    replaced = dict(show, **{names[3]: chance.randbytes(140000)})
    return {
        "removal": (removed, ["show.json"]),
        "addition": (added, ["new.odrg", "show.json"]),
        "replacement": (replaced, [names[3]]),
        "the same folder again": (dict(show), []),
    }


class OneFile(unittest.TestCase):
    """One file of a full storage removed, added, replaced, and the same folder installed
    again, at the storage of both layouts."""

    @classmethod
    def setUpClass(cls):
        cls.cases = {}
        for layout, blocks in LAYOUT_BLOCKS.items():
            show, image = full_storage(blocks, blocks)
            for kind, (wanted, written) in one_file_changes(show, random.Random(blocks + 1)).items():
                after = storage.with_show(image, wanted)
                cls.cases[layout, kind] = (show, image, wanted, written, after)

    def test_removing_one_animation_changes_the_blocks_of_the_show_file_and_at_most_four_more(self):
        changed = {}
        for layout, blocks in LAYOUT_BLOCKS.items():
            show, image = full_storage(blocks, blocks)
            wanted = dict(show, **{"show.json": random.Random(blocks + 1).randbytes(2400)})
            del wanted[sorted(name for name in show if name.endswith(".odrg"))[len(show) // 2]]
            after = storage.with_show(image, wanted)
            self.assertEqual(storage.show_of(after), wanted)
            changed[layout] = changed_blocks(image, after)
        self.assertEqual(changed, {layout: min(blocks, file_blocks(2400) + RECORD_BLOCKS) for layout, blocks in changed.items()})

    def test_each_change_changes_the_blocks_of_the_files_written_and_at_most_four_more(self):
        for (layout, kind), (show, image, wanted, written, after) in self.cases.items():
            with self.subTest(layout=layout, change=kind):
                changed = storage.run_bytes(storage.runs(image, after, BLOCK)) // BLOCK
                files = sum(file_blocks(len(wanted[name])) for name in written)
                self.assertLessEqual(changed, files + RECORD_BLOCKS)
                if not written:
                    self.assertEqual((changed, after), (0, image))

    def test_the_folder_holds_the_files_wanted_and_every_other_file_is_as_it_was(self):
        for (layout, kind), (show, image, wanted, written, after) in self.cases.items():
            with self.subTest(layout=layout, change=kind):
                self.assertEqual(storage.show_of(after), wanted)
                self.assertEqual(storage.other_files(after), SETTINGS)
                self.assertEqual(storage.show_of(after)["mapping.json"], show["mapping.json"])

    def test_no_file_that_stays_is_moved(self):
        for (layout, kind), (show, image, wanted, written, after) in self.cases.items():
            with self.subTest(layout=layout, change=kind):
                before, now = storage.blocks_of_files(image), storage.blocks_of_files(after)
                stays = [path for path in before if path in now and (not path.startswith("/odrig/") or wanted.get(path[7:]) == show.get(path[7:]))]
                self.assertGreater(len(stays), 40)
                self.assertEqual([path for path in stays if before[path] != now[path]], [])

    def test_the_new_bytes_lie_in_blocks_the_storage_before_did_not_use(self):
        for (layout, kind), (show, image, wanted, written, after) in self.cases.items():
            with self.subTest(layout=layout, change=kind):
                found = storage.plan(image, after)
                self.assertLessEqual(storage.run_bytes(found.in_use) // BLOCK, RECORD_BLOCKS)
                self.assertEqual(storage.run_bytes(found.free) + storage.run_bytes(found.in_use), storage.run_bytes(storage.runs(image, after, BLOCK)))
                # The free blocks alone leave the file system as it was.
                halfway = applied(image, found.free)
                self.assertEqual((storage.show_of(halfway), storage.other_files(halfway)), (show, SETTINGS))
                self.assertEqual(applied(halfway, found.in_use), after)


class BlocksInUse(unittest.TestCase):
    def test_they_are_as_many_as_the_file_system_counts_and_hold_every_file(self):
        for layout, blocks in LAYOUT_BLOCKS.items():
            with self.subTest(layout=layout):
                show, image = full_storage(blocks, blocks, share=0.3)
                in_use = storage.blocks_in_use(image)
                self.assertEqual(len(in_use), storage.mount(image).used_block_count)
                self.assertTrue({0, 1} <= in_use)
                for path, found in storage.blocks_of_files(image).items():
                    self.assertTrue(found <= in_use, path)

    def test_a_change_of_free_blocks_only_leaves_every_file_as_it_was(self):
        show, image = full_storage(64, 7, share=0.2)
        in_use = storage.blocks_in_use(image)
        scribbled = bytearray(image)
        for block in set(range(64)) - in_use:
            scribbled[block * BLOCK:(block + 1) * BLOCK] = bytes([block]) * BLOCK
        self.assertEqual(storage.show_of(bytes(scribbled)), show)


class Room(unittest.TestCase):
    def test_a_replacement_without_room_beside_the_old_file_takes_the_old_files_room(self):
        files = {"mapping.json": b"m" * 300, "show.json": b"s" * 300, "big.odrg": bytes(range(256)) * 600}
        image = support.storage_image(dict(SETTINGS, **{f"/odrig/{name}": content for name, content in files.items()}), blocks=64)
        wanted = dict(files, **{"big.odrg": bytes(range(255, -1, -1)) * 600})
        after = storage.with_show(image, wanted)
        self.assertEqual(storage.show_of(after), wanted)
        self.assertEqual(storage.other_files(after), SETTINGS)
        # The new bytes had to go where the old ones were: they are written in the commit.
        self.assertGreater(storage.run_bytes(storage.plan(image, after).in_use), RECORD_BLOCKS * BLOCK)

    def test_a_show_that_does_not_fit_even_so_is_no_space(self):
        files = {"mapping.json": b"m" * 300, "show.json": b"s" * 300}
        image = support.storage_image(dict(SETTINGS, **{f"/odrig/{name}": content for name, content in files.items()}), blocks=64)
        wanted = dict(files, **{"huge.odrg": bytes(64 * BLOCK)})
        self.assertEqual(support.reason_of(self, lambda: storage.with_show(image, wanted)), "no-space")


class Change(unittest.TestCase):
    def test_the_names_kept_added_replaced_and_removed(self):
        present = {"a": b"1", "b": b"2", "c": b"3"}
        wanted = {"a": b"1", "b": b"9", "d": b"4"}
        self.assertEqual(storage.change_of(present, wanted), storage.Change(["a"], ["d"], ["b"], ["c"]))

    def test_a_folder_inside_the_show_folder_goes_with_its_files(self):
        image = support.storage_image(dict(SETTINGS, **{"/odrig/show.json": b"s", "/odrig/inner/x.odrg": b"x" * 5000}), blocks=64)
        after = storage.with_show(image, {"show.json": b"s"})
        self.assertEqual(storage.show_of(after), {"show.json": b"s"})
        self.assertFalse(storage.has_folder(storage.mount(after), "/odrig/inner"))



if __name__ == "__main__":
    unittest.main()

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


class OneFile(unittest.TestCase):
    """One file of a full storage changed, at the storage of both layouts."""

    @unittest.expectedFailure
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


if __name__ == "__main__":
    unittest.main()

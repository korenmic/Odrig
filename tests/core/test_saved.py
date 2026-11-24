"""`saved <id>`: what the board keeps for an animation, read before it is moved."""

import json
import unittest

from . import support
from .test_catalog_drive import card, drive_ids
from .test_catalog_writes import a_card
from .test_drive import SHOW, asked, replies
from .test_playlist import loop_of


def show(start=None):
    items = [{"id": 1, "file": "one.odrg"}, {"id": 2, "file": "two.odrg"}, {"id": 3, "cycle": [1, 2], "seconds": 5}]
    made = {"version": 1, "brightness": 255, "items": items, "min_seconds": 4}
    if start is not None:
        made["start"] = start
    return {"mapping.json": SHOW["mapping.json"], "show.json": json.dumps(made), "one.odrg": loop_of(2, 5), "two.odrg": loop_of(3, 6)}


class Saved(unittest.TestCase):
    def test_nothing_saved_is_null(self):
        run = support.start(show(), asked(8000, "saved 1"))
        self.assertEqual(replies(run)[0], {"ok": True, "brightness": None, "repeat": None, "start": False})

    def test_saved_brightness_and_repeat_and_the_start_item(self):
        run = support.start(show(start=2), asked(8000, "brightness 2 27 save", "repeat 2 3 save", "saved 2", "saved 1"))
        answers = replies(run)
        self.assertEqual(answers[:2], [{"ok": True}, {"ok": True}])
        self.assertEqual(answers[2], {"ok": True, "brightness": 27, "repeat": 3, "start": True})
        self.assertEqual(answers[3], {"ok": True, "brightness": None, "repeat": None, "start": False})

    def test_a_zero_brightness_is_saved(self):
        run = support.start(show(), asked(8000, "brightness 1 0 save", "saved 1"))
        self.assertEqual(replies(run)[1]["brightness"], 0)

    def test_refusals(self):
        run = support.start(show(), asked(8000, "saved 3", "saved 9", "saved", "saved x", "saved 1 2"))
        self.assertEqual([answer["error"] for answer in replies(run)], ["in-use", "unknown-id", "bad-argument", "bad-argument", "bad-argument"])

    def test_a_file_of_the_card(self):
        files = card({"night/near.odrg": loop_of(3, 7)})
        file_id = drive_ids(files)["night/near.odrg"]
        with a_card(files) as top:
            run = support.start(SHOW, asked(8000, f"brightness {file_id} 9 save", f"saved {file_id}"), ["--drive", top])
        self.assertEqual(replies(run)[1], {"ok": True, "brightness": 9, "repeat": None, "start": False})


if __name__ == "__main__":
    unittest.main()

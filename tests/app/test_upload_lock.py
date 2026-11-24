"""The Upload screen's destination line speaks of the destination only, and its button
says why it is disabled."""

import pathlib
import tempfile
import time
import unittest

from tests.emulator import support as emulator_support

from . import support
from .test_target import entered
from .test_upload import OK, WITH_A_CANVAS, begun, taken, target

# What `space` answers on a target without a card.
NO_CARD = (200, '{"ok":true,"free":8372224,"total":10354688,"animations":2,"external":{"present":false,"free":null,"total":null,"read_only":true}}\n')
UNKNOWN = "Storage not known yet: the installation has not answered."
ABSENT = "External storage is disconnected or not detected. Using Internal /."
CAPACITY = "Internal storage: Free 8.4 MB of 10.4 MB"
SILENT = "The installation does not answer."
# The sizes the line is measured at: a phone upright, a narrow one, and a phone held
# sideways.
SIZES = ((360, 740), (320, 640), (740, 360))


def ready_file(test):
    """A folder with a ready-made animation, `ready.odrg`: the example show's `hello.odrg`."""
    media = pathlib.Path(entered(test, tempfile.TemporaryDirectory()))
    with emulator_support.example_show() as folder:
        (media / "ready.odrg").write_bytes((folder / "hello.odrg").read_bytes())
    return media


class TheUploadScreen(unittest.TestCase):
    def run_flow(self, replies, flow, steps=(), size=support.SIZE, delay=0.0):
        with support.StandIn(replies, delay=delay) as stand_in:
            return support.run("upload-lock", address=stand_in.address, settings={"rows": 2, "file": "ready.odrg", "flow": flow},
                               media=ready_file(self), steps=steps, size=size).seen

    def assert_silent(self, seen, kind):
        self.assertFalse(seen["enabled"], seen)
        self.assertTrue(seen["lock"].startswith(SILENT), seen["lock"])
        self.assertTrue(seen["lock"].endswith(f"({kind})"), seen["lock"])

    def test_a_space_that_never_answers_leaves_the_storage_unknown_and_the_form_where_it_is(self):
        mode = ["silent"]
        replies = dict(target(begin=begun, data=taken), space=lambda line: None if mode[0] == "silent" else NO_CARD)
        found = self.run_flow(replies, "space-silent", steps=[lambda: mode.__setitem__(0, "answers")], delay=0.4)
        first, silent, after = found["first"], found["silent"], found["after"]
        self.assertIsNone(first["message"])
        self.assertEqual(first["reason"], UNKNOWN)
        self.assertEqual((first["storage"], first["externalDisabled"], first["capacity"]), ("internal", True, "Internal storage: -"))
        # The request that got no reply is named under the button, and the storage is still not known.
        self.assert_silent(silent, "no-answer")
        self.assertEqual((silent["reason"], silent["storage"], silent["capacity"]), (UNKNOWN, "internal", "Internal storage: -"))
        self.assertEqual(after["reason"], ABSENT)
        self.assertEqual((after["storage"], after["externalDisabled"], after["enabled"], after["lock"]), ("internal", True, True, None))
        self.assertEqual(after["capacity"], CAPACITY)

    def test_a_status_that_fails_names_the_failure_under_the_button_at_every_width(self):
        for size in SIZES:
            with self.subTest(size=size):
                mode = ["answers"]
                replies = dict(target(begin=begun, data=taken), status=lambda line: (503, "") if mode[0] == "failing" else WITH_A_CANVAS)
                found = self.run_flow(replies, "status-fails", steps=[lambda: mode.__setitem__(0, "failing"), lambda: mode.__setitem__(0, "answers")], size=size)
                first, failing, again = found["first"], found["failing"], found["again"]
                self.assertEqual((first["enabled"], first["lock"], first["reason"], first["storage"], first["capacity"]), (True, None, ABSENT, "internal", CAPACITY))
                self.assertEqual(first["describedBy"], "upload-locked-reason")
                # The failure is named; the destination line, the form and the capacity stay, the capacity dimmed.
                self.assert_silent(failing, "bad-reply")
                self.assertEqual((failing["reason"], failing["storage"], failing["capacity"], failing["capacityStale"]), (ABSENT, "internal", CAPACITY, True))
                look = failing["look"]
                self.assertEqual((look["colour"], look["size"]), (look["spaceColour"], look["spaceSize"]), look)
                self.assertGreaterEqual(look["size"], 14)
                self.assertLessEqual(look["right"], size[0] - 8 + 0.5, look)
                self.assertLessEqual(look["scrollWidth"], size[0], look)
                self.assertEqual((again["enabled"], again["lock"], again["capacityStale"]), (True, None, False))

    def test_a_deletion_on_animations_is_named_under_the_button(self):
        def slow_removal(line):
            time.sleep(3)
            return OK

        replies = dict(target(begin=begun, data=taken), remove=slow_removal)
        found = self.run_flow(replies, "deletion")
        deleting, after = found["deleting"], found["after"]
        self.assertEqual((deleting["enabled"], deleting["lock"]), (False, "A deletion is under way on Animations."))
        self.assertEqual((after["enabled"], after["lock"]), (True, None))

    def test_the_preflight_is_named_while_the_installation_is_slow_to_tell_its_space(self):
        slow = [False]

        def space(line):
            if slow[0]:
                time.sleep(2)
            return NO_CARD

        replies = dict(target(begin=begun, data=taken), space=space)
        found = self.run_flow(replies, "preflight", steps=[lambda: slow.__setitem__(0, True)])
        checking, done = found["checking"], found["done"]
        self.assertEqual((checking["enabled"], checking["lock"]), (False, "Checking the destination with the installation."))
        self.assertEqual(done["message"], "Uploaded as animation 3 ready.odrg. It plays in the playlist.")
        self.assertEqual((done["enabled"], done["lock"]), (True, None))


if __name__ == "__main__":
    unittest.main()

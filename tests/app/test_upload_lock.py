"""The Upload screen's destination line speaks of the destination only, and its button
says why it is disabled."""

import pathlib
import tempfile
import unittest

from tests.emulator import support as emulator_support

from . import support
from .test_target import entered
from .test_upload import begun, taken, target

# What `space` answers on a target without a card.
NO_CARD = (200, '{"ok":true,"free":8372224,"total":10354688,"animations":2,"external":{"present":false,"free":null,"total":null,"read_only":true}}\n')
UNKNOWN = "Storage not known yet: the installation has not answered."
ABSENT = "External storage is disconnected or not detected. Using Internal /."


def ready_file(test):
    """A folder with a ready-made animation, `ready.odrg`: the example show's `hello.odrg`."""
    media = pathlib.Path(entered(test, tempfile.TemporaryDirectory()))
    with emulator_support.example_show() as folder:
        (media / "ready.odrg").write_bytes((folder / "hello.odrg").read_bytes())
    return media


class TheDestinationLine(unittest.TestCase):
    def run_flow(self, replies, flow, steps=(), size=support.SIZE):
        with support.StandIn(replies) as stand_in:
            return support.run("upload-lock", address=stand_in.address, settings={"rows": 2, "file": "ready.odrg", "flow": flow},
                               media=ready_file(self), steps=steps, size=size).seen

    def test_a_space_that_never_answers_leaves_the_storage_unknown_and_the_form_where_it_is(self):
        mode = ["silent"]
        replies = dict(target(begin=begun, data=taken), space=lambda line: None if mode[0] == "silent" else NO_CARD)
        found = self.run_flow(replies, "space-silent", steps=[lambda: mode.__setitem__(0, "answers")])
        first, after = found["first"], found["after"]
        self.assertIsNone(found["message"])
        self.assertEqual(first["reason"], UNKNOWN)
        self.assertEqual((first["storage"], first["externalDisabled"], first["capacity"]), ("internal", True, "Internal storage: -"))
        self.assertEqual(after["reason"], ABSENT)
        self.assertEqual((after["storage"], after["externalDisabled"], after["enabled"]), ("internal", True, True))
        self.assertEqual(after["capacity"], "Internal storage: Free 8.4 MB of 10.4 MB")


if __name__ == "__main__":
    unittest.main()

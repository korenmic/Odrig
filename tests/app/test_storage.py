import json
import pathlib
import tempfile
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_messages import refusal
from .test_target import entered

MAPPING = core_support.mapping_texts()["legs-2"]
# A stand-in target with two animations and room in its storage.
SPACE = (200, '{"ok":true,"free":8372224,"total":10354688,"animations":2}\n')


def clip(seed, durations=(20, 20, 20)):
    return core_support.clip(seed, 60, 6, durations)


def lines_of(events):
    """The command lines the emulator took, in their order."""
    return [entry["line"] for entry in emulator_support.of_kind(events, "log")]


class TheListOfAnimations(unittest.TestCase):
    def three(self):
        """A show folder of three animations and no cycle, on the two-leg mapping."""
        work = entered(self, tempfile.TemporaryDirectory())
        items = [{"id": 1, "file": "one.odrg"}, {"id": 2, "file": "two.odrg"}, {"id": 3, "file": "three.odrg"}]
        files = {"one.odrg": clip(1), "two.odrg": clip(2, (20,) * 40), "three.odrg": clip(3)}
        show = {"version": 1, "brightness": 128, "items": items}
        return emulator_support.installed(pathlib.Path(work, "show"), {"mapping.json": MAPPING, "show.json": json.dumps(show), **files})

    def emulator(self, folder):
        started = entered(self, emulator_support.Emulator(folder))
        return started, f"127.0.0.1:{started.port}"

    def test_it_shows_the_free_storage_and_each_animation_with_its_size_badge_and_menu(self):
        emulator, address = self.emulator(self.three())
        found = support.run("storage", address=address, settings={"rows": 3}).seen
        space = json.loads(emulator.command("space"))
        listed = json.loads(emulator.command("list"))["items"]
        self.assertEqual(found["before"]["space"], f"Internal storage: {space['animations']} animations, free {space['free'] / 1e6:.1f} MB of {space['total'] / 1e6:.1f} MB")
        self.assertEqual([row["text"] for row in found["before"]["rows"]], [f"{item['id']} {item['file']} {-(-item['bytes'] // 1000)} KB" for item in listed])
        self.assertEqual({row["badge"] for row in found["before"]["rows"]}, {"in"})
        self.assertEqual([menu for menu in found["menus"].values()], [["Ignore in playlist", "Move up (disabled)", "Move down", "Select", "Delete"],
                                                                     ["Ignore in playlist", "Move up", "Move down", "Select", "Delete"],
                                                                     ["Ignore in playlist", "Move up", "Move down (disabled)", "Select", "Delete"]])
        self.assertTrue(found["menuClosed"])
        self.assertEqual(found["buttons"], ["Animations", "Upload", "Settings", "Target"])
        self.assertEqual((found["before"]["none"], found["before"]["dimmed"]), (None, False))

    def test_a_cycle_is_no_row_and_a_small_file_is_one_kilobyte(self):
        emulator, address = self.emulator(entered(self, emulator_support.example_show()))
        found = support.run("storage", address=address, settings={"rows": 2}).seen
        self.assertEqual([row["text"] for row in found["before"]["rows"]], ["1 hello.odrg 2 KB", "2 dvd.odrg 2 KB"])

    def test_a_confirmed_removal_removes_the_animation_and_says_so(self):
        folder = self.three()
        emulator, address = self.emulator(folder)
        free = json.loads(emulator.command("space"))["free"]
        with emulator_support.EventStream(emulator.port) as stream:
            settings = {"rows": 3, "remove": 2, "answer": "Remove it", "until": "Removed animation 2 two\\.odrg"}
            found = support.run("storage", address=address, settings=settings).seen
            events = stream.read_for(1)
        self.assertEqual(found["question"], "Remove animation 2 two.odrg from the installation?")
        self.assertEqual(found["answers"], ["Remove it", "Keep it"])
        self.assertEqual(found["message"], "Removed animation 2 two.odrg.")
        self.assertEqual([row["id"] for row in found["after"]["rows"]], [1, 3])
        self.assertEqual([item["id"] for item in json.loads(emulator.command("list"))["items"]], [1, 3])
        self.assertFalse((folder / "two.odrg").exists())
        self.assertEqual([line for line in lines_of(events) if line.startswith("remove")], ["remove 2"])
        space = json.loads(emulator.command("space"))
        self.assertGreater(space["free"], free)
        self.assertEqual(found["after"]["space"], f"Internal storage: {space['animations']} animations, free {space['free'] / 1e6:.1f} MB of {space['total'] / 1e6:.1f} MB")

    def test_a_removal_that_is_kept_sends_nothing(self):
        emulator, address = self.emulator(self.three())
        with emulator_support.EventStream(emulator.port) as stream:
            found = support.run("storage", address=address, settings={"rows": 3, "remove": 1, "answer": "Keep it"}).seen
            events = stream.read_for(1)
        self.assertEqual(found["question"], "Remove animation 1 one.odrg from the installation?")
        self.assertEqual([row["id"] for row in found["after"]["rows"]], [1, 2, 3])
        self.assertIsNone(found["message"])
        self.assertEqual([line for line in lines_of(events) if not line.startswith(("status", "list", "space", "order get", "catalog"))], [])

    def test_an_animation_a_cycle_lists_is_refused_in_words(self):
        emulator, address = self.emulator(entered(self, emulator_support.example_show()))
        settings = {"rows": 2, "remove": 1, "answer": "Remove it", "until": "\\(in-use\\)"}
        found = support.run("storage", address=address, settings=settings).seen
        self.assertEqual(found["message"], "Animation 1 cannot be removed: a cycle plays it, or it is on a USB stick. (in-use)")
        self.assertEqual([row["id"] for row in found["after"]["rows"]], [1, 2])

    def test_a_busy_target_and_one_that_cannot_use_its_storage_are_told_in_words(self):
        for code, sentence in (("busy", "The installation is busy. Try again in a moment. (busy)"), ("storage-error", "The installation could not use its storage. (storage-error)")):
            with self.subTest(code=code):
                replies = {"status": support.PLAYING, "list": support.LISTED, "space": SPACE, "remove": refusal(code)}
                with support.StandIn(replies) as target:
                    settings = {"rows": 2, "remove": 2, "answer": "Remove it", "until": f"\\({code}\\)"}
                    found = support.run("storage", address=target.address, settings=settings).seen
                self.assertEqual(found["message"], sentence)
                self.assertEqual(found["before"]["space"], "Internal storage: 2 animations, free 8.4 MB of 10.4 MB")
                self.assertEqual([line for _, line in target.lines if line.startswith(b"remove")], [b"remove 2"])

class TheBadges(unittest.TestCase):
    def test_the_badge_and_the_menu_follow_external_of_list(self):
        # An internal animation without `ignored`, of a target that reports `external`, is
        # internal; the absence of `ignored` counts only where `external` is missing.
        listed = {"ok": True, "items": [{"id": 1, "file": "one.odrg", "bytes": 1000, "ignored": False, "external": False},
                                        {"id": 2, "file": "two.odrg", "bytes": 1000, "external": False},
                                        {"id": 60001, "file": "card.odrg", "bytes": 1000, "external": True},
                                        {"id": 60002, "file": "old.odrg", "bytes": 1000}], "next": None}
        replies = {"status": support.PLAYING, "list": (200, json.dumps(listed)), "space": SPACE}
        with support.StandIn(replies) as target:
            found = support.run("storage", address=target.address, settings={"rows": 4}).seen
        self.assertEqual([row["badge"] for row in found["before"]["rows"]], ["in", "in", "ex", "ex"])
        self.assertEqual(found["menus"]["2"][-1], "This installation's software does not let the app change this animation.")
        self.assertEqual(found["menus"]["60001"][-1], "External storage is read-only: this animation cannot be ignored or deleted from the app.")


if __name__ == "__main__":
    unittest.main()

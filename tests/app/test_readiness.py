import json
import pathlib
import platform
import tempfile
import threading
import unittest

from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_target import entered

MAPPING = core_support.mapping_texts()["legs-2"]
LISTED = (200, '{"ok":true,"items":[{"id":1,"file":"one.odrg","bytes":1138,"ignored":false},{"id":2,"file":"two.odrg","bytes":null,"ignored":false,"fault":"truncated"},'
               '{"id":3,"file":"three.odrg","bytes":null,"ignored":false}],"next":null}\n')


def clip(seed):
    return core_support.clip(seed, 60, 6, (20, 20, 20))


def checking(checked, to_check, unavailable, file):
    readiness = "checking" if to_check else "degraded" if unavailable else "ready"
    named = "null" if file is None else f'"{file}"'
    return (200, '{"ok":true,"on":true,"brightness":128,"playing":"all","animation":1,"fps":50,"error":null,'
                 f'"readiness":"{readiness}","checked":{checked},"to_check":{to_check},"unavailable":{unavailable},"checking":{named}}}\n')


class Statuses:
    """Answers `status` with each of its replies twice, and with the last from then on."""

    def __init__(self, *replies):
        self.replies = replies
        self.asked = 0
        self.lock = threading.Lock()

    def __call__(self, line):
        with self.lock:
            self.asked += 1
            return self.replies[min((self.asked - 1) // 2, len(self.replies) - 1)]


class ReadinessLine(unittest.TestCase):
    """While the installation reads its animations after a start, Animations says how far
    it is; when it has read them all and some are unavailable, how many; and nothing when
    all of them play, or when its software does not say."""

    def started(self, files):
        work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        folder = emulator_support.installed(work / "show", files)
        emulator = entered(self, emulator_support.Emulator(folder))
        return emulator, f"127.0.0.1:{emulator.port}"

    def test_a_target_that_reads_its_animations_says_how_far_and_then_how_many_are_unavailable(self):
        statuses = Statuses(checking(0, 3, 0, "one.odrg"), checking(1, 2, 0, "two.odrg"), checking(2, 1, 1, "three.odrg"), checking(3, 0, 1, None))
        with support.StandIn({"status": statuses, "list": LISTED}) as target:
            found = support.run("readiness", address=target.address, settings={"last": "1 animation unavailable; the others play."}).seen
        self.assertEqual(found["said"], ["Reading the animations: 0 read, 3 to read.", "Reading the animations: 1 read, 2 to read.",
                                         "Reading the animations: 2 read, 1 to read, 1 unavailable.", "1 animation unavailable; the others play."])
        self.assertTrue(found["pressable"])
        self.assertEqual(found["fps"], "50 refreshes a second")

    def test_an_emulator_with_two_unavailable_animations_says_so_when_it_has_read_them_all(self):
        items = [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "file": "c.odrg"}]
        emulator, address = self.started({"mapping.json": MAPPING, "show.json": json.dumps({"version": 1, "brightness": 128, "items": items}),
                                          "a.odrg": clip(1), "b.odrg": b"ODRX" + clip(2)[4:]})
        found = support.run("readiness", address=address, settings={"last": "2 animations unavailable; the others play."}).seen
        self.assertEqual(found["said"][-1], "2 animations unavailable; the others play.")
        self.assertEqual(json.loads(emulator.command("status"))["readiness"], "degraded")

    def test_a_target_with_every_animation_read_and_one_that_does_not_say_show_no_line(self):
        items = [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}]
        emulator, address = self.started({"mapping.json": MAPPING, "show.json": json.dumps({"version": 1, "brightness": 128, "items": items}),
                                          "a.odrg": clip(1), "b.odrg": clip(2)})
        self.assertIsNone(support.run("readiness", address=address, settings={"last": None}).seen["said"][-1])
        self.assertEqual(json.loads(emulator.command("status"))["readiness"], "ready")
        with support.StandIn(support.SOUND) as target:
            self.assertEqual(support.run("readiness", address=target.address, settings={"last": None}).seen["said"], [None])


class TargetScreen(unittest.TestCase):
    """The target screen names the installation as its software names itself, and says the
    last fault it met in a file, asked for when the screen is opened."""

    def test_it_names_the_emulator_and_says_its_last_fault(self):
        work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        items = [{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}]
        folder = emulator_support.installed(work / "show", {"mapping.json": MAPPING, "show.json": json.dumps({"version": 1, "brightness": 128, "items": items}),
                                                            "a.odrg": clip(1), "b.odrg": clip(2)[:-3]})
        emulator = entered(self, emulator_support.Emulator(folder))
        found = support.run("about", address=f"127.0.0.1:{emulator.port}", settings={"fault": True}).seen
        self.assertEqual(found["host"], f"Installation: odrig emulator on {platform.system()} {platform.machine()}")
        fault = json.loads(emulator.command("fault"))["fault"]
        self.assertEqual((fault["file"], fault["reason"]), ("b.odrg", "truncated"))
        self.assertEqual(found["fault"], f"Last fault: b.odrg, while it was checked after the start, at frame record {fault['record']} after {fault['bytes']} bytes "
                                         "of its frames: the file is damaged (truncated).")

    def test_a_target_whose_software_does_not_say_shows_neither_line(self):
        with support.StandIn(support.SOUND) as target:
            found = support.run("about", address=target.address, settings={"fault": False}).seen
            sent = [line for _, line in target.lines]
        self.assertEqual(found, {"host": None, "fault": None})
        self.assertEqual(sent.count(b"fault"), 1)


if __name__ == "__main__":
    unittest.main()

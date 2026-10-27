"""The current limits in the emulator: its LEDs show the limiting once budgets are saved, as
the board's do, and the command tool sends the five forms of `limits` by each transport."""

import contextlib
import json
import pathlib
import tempfile
import unittest

from emulator import binding, engine, host, hub
from odrig import limits
from tests.core import support as core_support
from tests.core.support import ReferencePlayer
from tests.core.test_limits import WHITE, many_legs, picture_file, show_files

from . import support

OK = b'{"ok":true}\n'
TWO_LEGS = core_support.mapping_texts()["legs-2"].encode()
STEP_NS = 20_000_000


def white_show(budgets=None):
    """A show of one picture on the two-leg mapping, every LED white, with a budgets' file
    when `budgets` is given."""
    return show_files(TWO_LEGS, picture_file(TWO_LEGS, lambda leg, led, frame: WHITE), budgets)


@contextlib.contextmanager
def installed_show(files):
    """A temporary show folder that holds these files."""
    with tempfile.TemporaryDirectory() as work:
        yield support.installed(pathlib.Path(work, "show"), files)


def targets(emulator):
    return {support.LINES: support.line_target(emulator), "http": ("--http", f"127.0.0.1:{emulator.port}")}


class TheLeds(unittest.TestCase):
    """The engine of the emulator on a show folder, with a clock that moves a refresh at a
    time."""

    def start(self, files):
        work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        self.folder = support.installed(work / "show", files)
        folder_host = host.FolderHost(self.folder)
        self.addCleanup(folder_host.close)
        self.now = 0
        self.hub = hub.Hub()
        self.engine = engine.Engine(binding.Core(support.LIBRARY, folder_host), self.hub, clock=lambda: self.now)

    def frame(self):
        """The LED data of the next refresh, as the page gets it."""
        self.now += STEP_NS
        self.engine.tick()
        return self.hub.newest_refresh()[1]

    def test_the_leds_show_the_limiting_once_budgets_are_saved(self):
        self.start(white_show())
        self.assertEqual([self.frame() for _ in range(3)], [WHITE * 360] * 3)
        self.assertEqual(self.engine.line(b"limits snake 1 500", "http"), OK)
        self.assertEqual(self.frame(), bytes([7]) * 540 + WHITE * 180)
        self.assertEqual(self.engine.line(b"limits wall 5000", "http"), OK)
        expected = limits.limit([WHITE * 180, WHITE * 180], [500, 0], 5000)
        self.assertEqual(self.frame(), b"".join(expected.legs))
        self.assertLessEqual(expected.wall_estimate, 5000)
        self.assertEqual(support.files_of(self.folder)[limits.NAME], limits.dumps(5000, [(1, 500)]))
        self.assertEqual(self.engine.line(b"limits default", "http"), OK)
        self.assertEqual(self.frame(), WHITE * 360)
        self.assertNotIn(limits.NAME, support.files_of(self.folder))

    def test_a_folder_with_budgets_is_limited_from_the_first_refresh_as_the_reference_limits_it(self):
        files = core_support.demo_show()
        files[limits.NAME] = limits.dumps(4000, [(1, 200), (5, 300), (12, 1)])
        self.start(files)
        player = ReferencePlayer(files)
        for _ in range(3):
            frame = self.frame()
            self.assertEqual(frame, b"".join(data for _, data in player.poll(self.engine.hub.newest_refresh()[0])))
        unlimited = ReferencePlayer(core_support.demo_show()).poll(self.engine.hub.newest_refresh()[0])
        self.assertNotEqual(frame, b"".join(data for _, data in unlimited))

    def test_without_budgets_the_emulator_limits_nothing(self):
        self.start(white_show())
        self.frame()
        reply = json.loads(self.engine.line(b"limits", "http"))
        self.assertEqual(reply, {"ok": True, "saved": False, "wall": [360, 0, 20160, 0], "legs": [[1, 180, 0, 10080, 0], [2, 180, 0, 10080, 0]], "next": None})


class TheTool(unittest.TestCase):
    def test_it_sends_the_five_forms_by_each_transport(self):
        with installed_show(white_show()) as folder, support.Emulator(folder) as emulator:
            for transport, target in targets(emulator).items():
                with self.subTest(transport=transport):
                    for words, status, out in ((("limits", "snake", "1", "500"), 0, OK), (("limits", "wall", "250001"), 1, b'{"ok":false,"error":"bad-argument"}\n'),
                                               (("limits", "snake", "3", "5"), 1, b'{"ok":false,"error":"bad-argument"}\n'), (("limits", "wall", "4000"), 0, OK)):
                        result = support.run_tool(*target, *words)
                        self.assertEqual((result.status, result.out, result.err), (status, out.decode("ascii"), ""), words)
                    self.assertEqual(support.files_of(folder)[limits.NAME], limits.dumps(4000, [(1, 500)]))
                    result = support.run_tool(*target, "limits")
                    self.assertEqual((result.status, result.err), (0, ""))
                    reply = json.loads(result.out)
                    self.assertEqual(result.out.count("\n"), 1)
                    self.assertEqual((reply["saved"], reply["wall"][:2], [entry[:3] for entry in reply["legs"]], reply["next"]), (True, [360, 4000], [[1, 180, 500], [2, 180, 0]], None))
                    result = support.run_tool(*target, "limits", "1")
                    self.assertEqual([entry[0] for entry in json.loads(result.out)["legs"]], [2])
                    result = support.run_tool(*target, "limits", "default")
                    self.assertEqual((result.status, result.out), (0, OK.decode("ascii")))
                    self.assertNotIn(limits.NAME, support.files_of(folder))
                    self.assertIs(json.loads(support.run_tool(*target, "limits").out)["saved"], False)

    def test_limits_without_a_position_prints_a_reply_for_each_part(self):
        text = many_legs(255)
        files = show_files(text, core_support.clip(6, 2, 255), (250000, [(leg, 60000 + leg) for leg in range(1, 256)]))
        with installed_show(files) as folder, support.Emulator(folder) as emulator:
            for transport, target in targets(emulator).items():
                with self.subTest(transport=transport):
                    result = support.run_tool(*target, "limits")
                    self.assertEqual((result.status, result.err), (0, ""))
                    replies = [json.loads(line) for line in result.out.splitlines()]
                    self.assertGreater(len(replies), 3)
                    self.assertTrue(all(len(line) < 1024 for line in result.out.splitlines()))
                    self.assertEqual([entry[:3] for reply in replies for entry in reply["legs"]], [[leg, 2, 60000 + leg] for leg in range(1, 256)])
                    positions = [0]
                    for reply in replies:
                        positions.append(positions[-1] + len(reply["legs"]))
                    self.assertEqual([reply["next"] for reply in replies], positions[1:-1] + [None])
            with support.EventStream(emulator.port) as stream:
                logged = support.of_kind(stream.read_until(lambda events: any(event.kind == "status" for event in events)), "log")
        asked = [entry["line"] for entry in logged if entry["transport"] == "http"]
        self.assertEqual(asked, ["limits"] + [f"limits {position}" for position in positions[1:-1]])


if __name__ == "__main__":
    unittest.main()

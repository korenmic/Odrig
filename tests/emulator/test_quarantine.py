import json
import pathlib
import tempfile
import unittest

from tests.core import support as core_support

from . import support


class ABadFile(unittest.TestCase):
    def test_the_emulator_plays_the_others_and_lists_it_with_its_fault_on_every_route(self):
        work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        files = core_support.example_show()
        files["dvd.odrg"] = files["dvd.odrg"][:-3]
        folder = support.installed(work / "show", files)
        with support.Emulator(folder) as emulator, support.lines(emulator) as port:
            state = emulator.status()
            self.assertEqual((state["error"], state["playing"], state["animation"]), (None, 3, 1))
            routes = {"http": emulator.command, support.LINES: port.ask}
            for route, ask in routes.items():
                listed = json.loads(ask("list"))
                self.assertEqual(listed["items"][1], {"id": 2, "file": "dvd.odrg", "bytes": None, "ignored": False, "external": False, "type": "frames", "fault": "truncated"}, route)
                self.assertEqual(ask("play 2"), b'{"ok":false,"error":"unavailable"}\n', route)
                self.assertEqual(ask("play 1"), b'{"ok":true}\n', route)
            self.assertIsNone(emulator.status()["error"])
            self.assertEqual(support.files_of(folder)["dvd.odrg"], files["dvd.odrg"])
            # The emulator names itself, and gives the fault's context, on every route.
            for route, ask in routes.items():
                self.assertTrue(json.loads(ask("status"))["host"].startswith("odrig emulator on "), route)
                self.assertEqual(json.loads(ask("fault"))["fault"]["file"], "dvd.odrg", route)


if __name__ == "__main__":
    unittest.main()

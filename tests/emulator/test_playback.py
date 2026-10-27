"""The engine's knowledge of the animation on the LEDs: the start of its loop and of its
turn from the core's opens of the played file, its length from a catalog, from the
converter's check or from a loop seen twice, and the `position` event of the hub."""

import json
import pathlib
import re
import shutil
import tempfile
import unittest

from emulator import binding, engine, host, hub, lengths
from odrig import catalog
from tests.core.support import ReferencePlayer

from . import support

GRID = engine.GRID_MS
HELLO_MS = 5100
# The example show's playlist begins at the grid time after `play all` is sent at 20 ms.
ZERO = 40


class Playback(unittest.TestCase):
    """An engine on the example show with an injected clock, ticked grid by grid."""

    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        self.now = 0
        self.files = host.FolderHost(self.folder)
        self.addCleanup(self.files.close)
        self.core = binding.Core(support.LIBRARY, self.files)
        self.hub = hub.Hub()
        self.connection = self.hub.connect({})
        self.reference = ReferencePlayer(support.files_of(self.folder))
        self.start(lengths.Lengths(node=None))

    def start(self, found):
        self.lengths = found
        self.engine = engine.Engine(self.core, self.hub, clock=lambda: self.now * 1_000_000, host=self.files, lengths=found)

    def tick_until(self, ms):
        """Ticks the engine and the reference player at every grid time up to `ms`."""
        while self.now < ms:
            self.now += GRID
            self.engine.tick()
            self.reference.poll(self.now)

    def command(self, line):
        self.reference.command(self.now, line)
        return self.engine.line(line, "http")

    def positions(self):
        """The `position` events sent since the last call, as dictionaries."""
        taken = self.connection.take(0) or []
        return [json.loads(data) for kind, data in taken if kind == "position"]

    def latest(self):
        found = self.positions()
        return found[-1] if found else None

    def playlist(self):
        """`play all` at 20 ms, so that the first turn begins at ZERO."""
        self.tick_until(GRID)
        self.command(b"play all")
        self.positions()

    def test_the_playlist_from_the_start_gives_the_first_animation_its_turn_at_the_grid(self):
        self.tick_until(GRID)
        self.now += 7
        self.command(b"play all")
        self.positions()
        self.tick_until(ZERO + GRID)
        self.assertEqual(self.latest(), {"animation": 1, "start": ZERO, "turn": ZERO, "length": None})
        self.assertEqual(self.reference.zero, ZERO)

    def test_every_loop_moves_the_start_and_the_second_gives_the_length_seen(self):
        self.playlist()
        self.tick_until(ZERO + HELLO_MS + GRID)
        self.assertEqual(self.latest(), {"animation": 1, "start": ZERO + HELLO_MS, "turn": ZERO, "length": HELLO_MS})
        self.assertEqual(self.engine.playback.source, "seen")
        self.tick_until(ZERO + 2 * HELLO_MS + GRID)
        self.assertEqual(self.latest(), {"animation": 1, "start": ZERO + 2 * HELLO_MS, "turn": ZERO, "length": HELLO_MS})

    def test_a_new_turn_moves_the_turn_and_the_start_and_names_the_animation_at_once(self):
        self.playlist()
        self.tick_until(ZERO + 6 * HELLO_MS + GRID)
        event = self.latest()
        self.assertEqual(event, {"animation": 2, "start": ZERO + 6 * HELLO_MS, "turn": ZERO + 6 * HELLO_MS, "length": None})
        self.assertEqual(self.reference.zero, ZERO + 6 * HELLO_MS)
        self.assertEqual(self.reference.shown, 2)

    def test_a_restart_by_a_command_is_a_turn_and_no_loop_seen(self):
        self.playlist()
        self.tick_until(2000)
        self.now += 7
        self.command(b"play 1")
        self.positions()
        self.tick_until(self.now + 2 * GRID)
        self.assertEqual(self.latest(), {"animation": 1, "start": 2020, "turn": 2020, "length": None})
        self.assertEqual(self.reference.zero, 2020)

    def test_a_cycle_shows_nothing_and_nothing_is_said_until_something_is_known(self):
        self.tick_until(3 * GRID)
        self.assertIsNone(self.latest())
        self.assertIsNone(self.hub.latest_position())
        self.assertTrue(self.engine.playback.cycle())
        self.command(b"play all")
        self.tick_until(self.now + 2 * GRID)
        self.assertEqual(self.latest()["animation"], 1)
        self.command(b"play 3")
        self.tick_until(self.now + 2 * GRID)
        self.assertEqual(self.latest(), {"animation": None, "start": None, "turn": None, "length": None})
        self.assertEqual(self.engine.playback.animation, 1)
        self.assertEqual(self.engine.playback.playing, 3)

    def test_the_length_comes_from_the_catalog_of_the_show_folder(self):
        storage = catalog.Storage(self.folder)
        known = catalog.read(storage)
        for name in ("hello.odrg", "dvd.odrg"):
            known = catalog.commit(storage, known, added=catalog.entry_of(name, (self.folder / name).read_bytes(), canvas=None))
        self.start(lengths.Lengths(node=None))
        self.playlist()
        self.tick_until(ZERO + GRID)
        self.lengths.settle()
        self.engine.take_lengths()
        self.assertEqual(self.latest(), {"animation": 1, "start": ZERO, "turn": ZERO, "length": HELLO_MS})
        self.assertEqual(self.engine.playback.source, "catalog")

    @unittest.skipIf(shutil.which("node") is None, "Node.js is not on the path")
    def test_the_length_comes_from_the_converters_check_when_node_is_at_hand(self):
        self.start(lengths.Lengths())
        self.playlist()
        self.tick_until(ZERO + GRID)
        self.lengths.settle()
        self.engine.take_lengths()
        self.assertEqual(self.latest()["length"], HELLO_MS)
        self.assertEqual(self.engine.playback.source, "check")

    def test_a_new_connection_gets_the_position_after_the_status(self):
        self.playlist()
        self.tick_until(100)
        later = self.hub.connect({})
        kinds = [kind for kind, _ in later.take(0)]
        self.assertEqual(kinds.index("position"), kinds.index("status") + 1)


class Opens(unittest.TestCase):
    def test_the_host_tells_of_an_open_of_an_animation_file_with_its_path(self):
        folder = support.entered(self, support.example_show())
        files = host.FolderHost(folder)
        told = []
        files.on_open = lambda name, path: told.append((name, path))
        self.assertEqual(files.open("hello.odrg"), 1)
        self.assertEqual(files.open("show.json"), 1)
        self.assertEqual(files.open("missing.odrg"), 0)
        files.close()
        self.assertEqual(told, [("hello.odrg", str(folder / "hello.odrg"))])


if __name__ == "__main__":
    unittest.main()


class FolderPlaylist(unittest.TestCase):
    """A folder of the card as the current playlist: `playing` names the folder's id, and
    the bar shows the animation as it does for the playlist."""

    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        card = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        (card / "odrig" / "night").mkdir(parents=True)
        (card / "odrig" / "night" / "comet.odrg").write_bytes((self.folder / "hello.odrg").read_bytes())
        self.files = host.FolderHost(self.folder, drive=host.Drive(card, writable=False))
        self.addCleanup(self.files.close)
        self.core = binding.Core(support.LIBRARY, self.files)
        self.hub = hub.Hub()
        self.now = 0
        self.engine = engine.Engine(self.core, self.hub, clock=lambda: self.now * 1_000_000, host=self.files, lengths=lengths.Lengths(node=None))

    def tick_until(self, ms):
        while self.now < ms:
            self.now += GRID
            self.engine.tick()

    def folder_id(self):
        for _ in range(500):
            self.tick_until(self.now + 100)
            found = re.search(rb'\{"id":([0-9]+),"playlist":"night"', self.core.command(self.now, b"list 0"))
            if found:
                return int(found.group(1))
        self.fail("the card's folder never came into the list")

    def test_a_folder_playlist_shows_its_animation_and_a_cycle_still_shows_nothing(self):
        number = self.folder_id()
        self.engine.line(b"play %d" % number, "http")
        self.tick_until(self.now + 3 * GRID)
        self.assertEqual(self.engine.playback.playing, number)
        event = json.loads(self.hub.latest_position())
        self.assertIsNotNone(event["animation"])
        self.assertIsNotNone(event["start"])
        self.engine.line(b"play 3", "http")
        self.tick_until(self.now + 3 * GRID)
        self.assertEqual(json.loads(self.hub.latest_position()), {"animation": None, "start": None, "turn": None, "length": None})
        self.assertEqual(self.engine.seek(100), {"ok": False, "error": "cycle"})

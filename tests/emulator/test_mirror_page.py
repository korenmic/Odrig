"""The page of a mirror: `hello` names its link, `mirror` events carry its state, the log marks
the board's replies, a board of another canvas is named, and the seek is refused."""

import json
import time
import unittest

from . import support
from .test_mirror import catalogued

WEB = support.ROOT / "emulator" / "web"
MEMBERS = ["canvas", "dark", "fetch", "item", "link", "offset", "reason", "since", "state", "version"]


def mirror_events(port, enough, seconds=20):
    """The `hello` and the `mirror` events of an emulator's stream, read until `enough(state)`
    holds for a mirror event."""
    with support.EventStream(port) as stream:
        events = stream.read_until(lambda events: any(event.kind == "mirror" and enough(json.loads(event.data)) for event in events), seconds)
    return support.of_kind(events, "hello"), support.of_kind(events, "mirror")


class ThePageOfAMirror(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packed = support.example_show()
        cls.folder = cls.packed.__enter__()
        cls.board = support.Emulator(cls.folder, tcp_port=0)
        catalogued(cls.board)
        cls.mirrored = support.Emulator(cls.folder, "--mirror-tcp", cls.board.tcp, checked=False)

    @classmethod
    def tearDownClass(cls):
        cls.mirrored.stop()
        cls.board.stop()
        cls.packed.__exit__(None, None, None)

    def test_hello_names_the_link_and_a_mirror_event_its_state(self):
        hellos, states = mirror_events(self.mirrored.port, lambda state: state["state"] == "linked" and state["version"] is not None and state["dark"] is None)
        self.assertEqual(hellos[0]["mirror"], f"tcp {self.board.tcp}")
        last = states[-1]
        self.assertEqual(sorted(last), MEMBERS)
        self.assertEqual((last["link"], last["state"], last["reason"], last["fetch"], last["canvas"]), (f"tcp {self.board.tcp}", "linked", None, None, None))
        self.assertIsInstance(last["version"], int)
        self.assertIsInstance(last["offset"], int)
        self.assertRegex(last["since"], r"\A[0-9]{2}:[0-9]{2}:[0-9]{2}\Z")
        self.assertIn(last["item"]["id"], (1, 2))

    def test_an_emulator_alone_mirrors_nothing(self):
        with support.EventStream(self.board.port) as stream:
            events = stream.read_until(lambda events: any(event.kind == "hello" for event in events))
        self.assertIsNone(support.of_kind(events, "hello")[0]["mirror"])
        self.assertEqual(support.of_kind(events, "mirror"), [])

    def test_the_seek_of_a_mirror_is_refused(self):
        answer = self.mirrored.request(path="/seek", body=b'{"ms":0}')
        self.assertEqual((answer.status, json.loads(answer.body)), (200, {"ok": False, "error": "mirror"}))

    def test_the_log_marks_the_boards_replies_and_the_status_is_the_boards(self):
        self.assertEqual(json.loads(self.mirrored.command("brightness 90")), {"ok": True})
        with support.EventStream(self.mirrored.port) as stream:
            events = stream.read_until(lambda events: any(event.kind == "log" and "brightness 90" in event.data for event in events) and any(event.kind == "status" for event in events))
        entry = [entry for entry in support.of_kind(events, "log") if entry["line"] == "brightness 90"][-1]
        self.assertEqual((entry["transport"], entry["reply"], entry["board"]), ("http", '{"ok":true}', True))
        self.assertEqual(support.of_kind(events, "status")[-1]["width"], 60)
        with support.EventStream(self.board.port) as stream:
            events = stream.read_until(lambda events: any(event.kind == "log" and "brightness 90" in event.data for event in events))
        self.assertNotIn("board", [entry for entry in support.of_kind(events, "log") if entry["line"] == "brightness 90"][-1])


class ABoardOfAnotherCanvas(unittest.TestCase):
    def test_the_two_canvases_are_named_and_the_leds_stay_dark(self):
        with support.example_show() as small, support.demo_show() as large:
            board = support.Emulator(small, tcp_port=0)
            try:
                catalogued(board)
                mirrored = support.Emulator(large, "--mirror-tcp", board.tcp, checked=False)
                try:
                    _, states = mirror_events(mirrored.port, lambda state: state["dark"] == "canvas")
                    self.assertEqual(states[-1]["canvas"], {"board": [60, 6], "show": [60, 60]})
                    self.assertEqual(json.loads(mirrored.command("status"))["width"], 60)
                finally:
                    mirrored.stop()
            finally:
                board.stop()


class ThePageScript(unittest.TestCase):
    def test_the_page_shows_the_mirror_and_has_no_seek_bar_for_one(self):
        index = (WEB / "index.html").read_text(encoding="utf-8")
        for found in ('id="mirror"', 'id="mirror-state"', 'id="mirror-version"', 'id="mirror-band"'):
            self.assertIn(found, index)
        app = (WEB / "app.js").read_text(encoding="utf-8")
        for found in ('source.addEventListener("mirror", onMirror);', "hello && hello.mirror", 'port("mirror", hello.mirror, String);', "entry.board",
                      "Waiting for the board: ", "The link to the board is lost since ", "Fetching the file of animation ", "The board's canvas is ", "no catalog of its storage names its file"):
            self.assertIn(found, app)


if __name__ == "__main__":
    unittest.main()

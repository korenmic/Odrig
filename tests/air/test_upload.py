import json
import pathlib
import tempfile
import unittest

from odrigctl import client

from fwtool import paths
from tests.board import support as board_support

from . import ADDRESS, support

# What the owner accepts on the board for any content: 20 refreshes a second or more.
LOWEST = 20
SECONDS_AFTER = 10
DENSE_SECONDS = 10
DENSE_NAME = "dense-bench.odrg"
RESULT = paths.OUT / "upload-air.json"


class ContentCommands(unittest.TestCase):
    """The content commands over the board's network. The board holds the dim example
    show, on the bench file, as the board suite leaves it."""

    @classmethod
    def setUpClass(cls):
        cls.work = pathlib.Path(cls.enterClassContext(tempfile.TemporaryDirectory()))
        cls.hello = cls.work / board_support.HELLO_NAME
        cls.hello.write_bytes(board_support.hello_for(board_support.TWO_LEGS))
        width, height = board_support.canvas_of(board_support.TWO_LEGS)
        cls.clip = board_support.dense_clip(True, DENSE_SECONDS, width, height)

    def prepare(self):
        for line in support.PREPARE:
            self.assertEqual(support.over_the_port(*line.split(" ")), (0, {"ok": True}))

    def tearDown(self):
        support.over_the_port("play", "3")

    def test_the_session_of_the_content_commands_over_http_gets_the_replies_it_gets_over_the_port(self):
        answers = []
        for send in (support.over_http, support.over_the_port):
            self.prepare()
            answers.append(board_support.content_session(send, lambda: None, self.hello))
        by_http, by_port = answers
        size = self.hello.stat().st_size
        self.assertEqual(by_http[2][1:], (0, {"ok": True}), "the reply that ended the upload over HTTP")
        self.assertEqual(by_http[3][2]["items"][-1], {"id": board_support.NEW_ITEM, "file": board_support.HELLO_NAME, "bytes": size})
        self.assertEqual((by_http[5][2]["playing"], by_http[5][2]["animation"]), (board_support.NEW_ITEM, board_support.NEW_ITEM))
        self.assertEqual(by_http[11][1:], (0, {"ok": True}))
        self.assertEqual([item["id"] for item in by_http[12][2]["items"]], [1, 2, 3])
        for number, ((line, *over_http), (_, *over_the_port)) in enumerate(zip(by_http, by_port), 1):
            self.assertEqual(over_http, over_the_port, f"command {number} of the session, `{line}`: the answer over HTTP is the first")

    def test_a_dense_clip_is_uploaded_over_http_while_the_show_plays_at_20_refreshes_a_second_or_more(self):
        self.prepare()
        number = board_support.NEW_ITEM
        with client.Session(http=ADDRESS, timeout=support.SECONDS) as session:
            reply, rates, times = board_support.measured_upload(session, number, DENSE_NAME, self.clip)
            after = board_support.each_second(SECONDS_AFTER, lambda: json.loads(session.exchange(b"status\n"))["fps"])
            listed = json.loads(session.exchange(b"list\n"))
            removed = json.loads(session.exchange(b"remove %d\n" % number))
        speed = round(len(self.clip) / times["data"]) if times["data"] else 0
        RESULT.parent.mkdir(parents=True, exist_ok=True)
        RESULT.write_text(json.dumps({
            "address": ADDRESS,
            "bytes": len(self.clip),
            "frames": DENSE_SECONDS * 50,
            "reply": reply,
            "data_seconds": round(times["data"], 2),
            "bytes_per_second": speed,
            "check_seconds": round(times["check"], 2),
            "fps_during_data": rates["data"],
            "fps_during_check": rates["check"],
            "fps_after": after,
        }, indent=2) + "\n")
        self.assertEqual(reply, {"ok": True}, "the reply that ended the upload")
        self.assertEqual(listed["items"][-1], {"id": number, "file": DENSE_NAME, "bytes": len(self.clip)})
        self.assertEqual(removed, {"ok": True})
        self.assertGreaterEqual(min(rates["data"] + rates["check"] + after), LOWEST, (rates, after))
        self.assertGreater(speed, 0)


if __name__ == "__main__":
    unittest.main()

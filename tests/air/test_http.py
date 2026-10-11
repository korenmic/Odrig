import unittest

from tests.board.support import SESSION

from . import support

REPLY_TYPE = "application/json"


class Commands(unittest.TestCase):
    def test_a_session_over_http_gets_the_replies_it_gets_over_the_port(self):
        answers = []
        for send in (support.over_the_port, support.over_http):
            for line in support.PREPARE:
                self.assertEqual(support.over_the_port(*line.split(" ")), (0, {"ok": True}))
            answers.append(support.session(send, SESSION))
        for number, (line, by_port, by_http) in enumerate(zip(SESSION, *answers), 1):
            self.assertEqual(by_http, by_port, f"line {number} of the session, `{line}`: the answer over HTTP is the first")
        self.assertEqual({reply["error"] for status, reply in answers[1] if status == 1}, {"unknown-id", "bad-argument", "line-too-long"})

    def test_a_command_over_http_acts_on_the_player_that_the_port_reaches(self):
        self.assertEqual(support.over_http("brightness", "17"), (0, {"ok": True}))
        self.assertEqual(support.over_the_port("status")[1]["brightness"], 17)
        self.assertEqual(support.over_the_port("brightness", "23"), (0, {"ok": True}))
        self.assertEqual(support.over_http("status")[1]["brightness"], 23)
        self.assertEqual(support.over_http("brightness", "32"), (0, {"ok": True}))


class Requests(unittest.TestCase):
    def test_a_post_is_answered_with_status_200_and_the_reply_as_json(self):
        status, headers, body = support.request("POST", "/odrig", b"play 1", "application/octet-stream")
        self.assertEqual((status, body), (200, b'{"ok":true}\n'))
        self.assertEqual(headers["Content-Type"].split(";")[0], REPLY_TYPE)

    def test_a_reply_that_reports_an_error_has_status_200_too(self):
        status, _, body = support.request("POST", "/odrig", b"play 99\n", "application/octet-stream")
        self.assertEqual((status, body), (200, b'{"ok":false,"error":"unknown-id"}\n'))

    def test_another_method_gets_405_and_the_method_that_is_allowed(self):
        for method in ("GET", "PUT", "OPTIONS"):
            status, headers, _ = support.request(method, "/odrig")
            self.assertEqual(status, 405, method)
            self.assertEqual(headers.get("Allow"), "POST", method)

    def test_a_longer_path_is_not_found(self):
        self.assertEqual(support.request("POST", "/odrig/x", b"status", "application/octet-stream")[0], 404)
        self.assertEqual(support.request("GET", "/odrig/x")[0], 404)

    def test_what_follows_a_question_mark_is_ignored(self):
        status, _, body = support.request("POST", "/odrig?x=1", b"play 1", "application/octet-stream")
        self.assertEqual((status, body), (200, b'{"ok":true}\n'))

    def test_a_body_of_10000_bytes_is_a_line_that_is_too_long(self):
        status, _, body = support.request("POST", "/odrig", b"play " + b"7" * 9995, "application/octet-stream")
        self.assertEqual((status, body), (200, b'{"ok":false,"error":"line-too-long"}\n'))

    def test_a_valid_command_is_understood_with_each_content_type(self):
        for content_type in ("application/octet-stream", "text/plain", "application/x-www-form-urlencoded", None):
            status, _, body = support.request("POST", "/odrig", b"play 1", content_type)
            self.assertEqual((status, body), (200, b'{"ok":true}\n'), content_type)
        status, _, body = support.request("POST", "/odrig", b"brightness 32\n", "text/plain")
        self.assertEqual((status, body), (200, b'{"ok":true}\n'))

    def tearDown(self):
        support.over_the_port("play", "3")

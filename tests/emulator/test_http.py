import http.client
import json
import tempfile
import threading
import unittest

from emulator import failure, httpd, hub
from tests.core.support import ReferencePlayer

from . import support

SESSION = ("status", "brightness 77", "status", "off", "status", "on", "play 2", "status", "play 3", "status", "play 1", "brightness 128", "play 3")
REFUSED = {
    "play 99": "unknown-id",
    "dance": "unknown-command",
    "brightness 256": "bad-argument",
    "play abc": "bad-argument",
    "status now": "bad-argument",
    "PLAY 1": "unknown-command",
    " on": "unknown-command",
}


class Commands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = support.entered(cls, support.example_show())
        cls.emulator = support.entered(cls, support.Emulator(cls.folder))

    def reference(self):
        player = ReferencePlayer(support.files_of(self.folder))
        player.poll(0)
        return player

    def test_each_command_gets_status_200_the_json_type_and_the_reply_of_the_reference(self):
        for ending in ("", "\n", "\r\n"):
            player = self.reference()
            for line in SESSION:
                with self.subTest(line=line, ending=ending):
                    answer = self.emulator.request(body=(line + ending).encode("ascii"))
                    self.assertEqual(answer.status, 200)
                    self.assertEqual(answer.headers["content-type"], "application/json")
                    self.assertEqual(answer.headers["access-control-allow-origin"], "*")
                    self.assertEqual(answer.headers["content-length"], str(len(answer.body)))
                    expected = player.command(100, line.encode("ascii"))
                    if line == "status":
                        self.assertRegex(answer.body, rb'\A\{"ok":true,"on":(true|false),"brightness":[0-9]+,"playing":[0-9]+,"animation":[0-9]+,"fps":[0-9]+,"error":null\}\n\Z')
                        self.assertEqual(support.without_fps(answer.body), support.without_fps(expected))
                    else:
                        self.assertEqual(answer.body, expected)
                        self.assertEqual(answer.body, b'{"ok":true}\n')

    def test_a_reply_that_is_not_ok_has_status_200(self):
        before = support.without_fps(self.emulator.command("status"))
        for line, code in REFUSED.items():
            with self.subTest(line=line):
                answer = self.emulator.request(body=line.encode("ascii"))
                self.assertEqual(answer.status, 200)
                self.assertEqual(answer.headers["content-type"], "application/json")
                self.assertEqual(answer.body, b'{"ok":false,"error":"' + code.encode("ascii") + b'"}\n')
                self.assertEqual(answer.body, self.reference().command(0, line.encode("ascii")))
        self.assertEqual(support.without_fps(self.emulator.command("status")), before)

    def test_another_method_gets_405_with_allow_post_no_body_and_changes_nothing(self):
        self.emulator.command("brightness 128")
        before = support.without_fps(self.emulator.command("status"))
        for method in ("GET", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH", "BREW"):
            with self.subTest(method=method):
                body = None if method in ("GET", "HEAD") else b"brightness 1\n"
                answer = self.emulator.request(method=method, body=body)
                self.assertEqual(answer.status, 405)
                self.assertEqual(answer.headers["allow"], "POST")
                self.assertEqual(answer.headers["content-length"], "0")
                self.assertEqual(answer.body, b"")
                self.assertEqual(support.without_fps(self.emulator.command("status")), before)

    def test_a_post_without_a_usable_length_gets_411_and_changes_nothing(self):
        self.emulator.command("brightness 128")
        before = support.without_fps(self.emulator.command("status"))
        for length in (None, "Content-Length: many", "Content-Length: -1", "Content-Length: 1.5", "Content-Length:", "Transfer-Encoding: chunked"):
            with self.subTest(length=length):
                head = b"POST /odrig HTTP/1.1\r\nHost: 127.0.0.1\r\n" + (length.encode("ascii") + b"\r\n" if length else b"") + b"\r\n"
                received = support.raw_request(self.emulator.port, head + b"brightness 2\n")
                self.assertRegex(received, rb"\AHTTP/1\.1 411 ")
                self.assertTrue(received.endswith(b"\r\n\r\n"), received)
                self.assertEqual(support.without_fps(self.emulator.command("status")), before)

    def test_an_empty_body_a_body_of_2049_characters_and_one_of_10000_bytes(self):
        too_long = b'{"ok":false,"error":"line-too-long"}\n'
        unknown = b'{"ok":false,"error":"unknown-command"}\n'
        self.assertEqual(self.emulator.request(body=b"").body, unknown)
        self.assertEqual(self.emulator.request(body=b"\n").body, unknown)
        self.assertEqual(self.emulator.request(body=b"x" * 2048).body, unknown)
        self.assertEqual(self.emulator.request(body=b"x" * 2048 + b"\r\n").body, unknown)
        self.assertEqual(self.emulator.request(body=b"x" * 2049).body, too_long)
        self.assertEqual(self.emulator.request(body=b"play " + b"1" * 2044).body, too_long)
        self.assertEqual(self.emulator.request(body=b"x" * 4096).body, too_long)
        self.assertEqual(self.emulator.request(body=b"x" * 4097).body, too_long)
        answer = self.emulator.request(body=b"status\n" * 1428 + b"sta\n")
        self.assertEqual((answer.status, answer.body), (200, too_long))
        self.assertEqual(self.emulator.request(body=bytes(range(256)) * 9).body, too_long)

    def test_a_connection_is_kept_and_a_long_body_is_read_to_its_end(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.emulator.port, timeout=10)
        self.addCleanup(connection.close)
        for body, ok in ((b"status", True), (b"x" * 10000, False), (b"on\n", True), (b"y" * 300000, False), (b"status\n", True)):
            connection.request("POST", "/odrig", body=body)
            answer = connection.getresponse()
            self.assertEqual(answer.status, 200)
            self.assertIs(json.loads(answer.read())["ok"], ok)

    def test_the_path_is_odrig_exactly_whatever_follows_a_question_mark(self):
        for path in ("/odrig?x=1", "/odrig?", "/odrig?a/b=c?d"):
            answer = self.emulator.request(path=path, body=b"on")
            self.assertEqual((answer.status, answer.body), (200, b'{"ok":true}\n'), path)
        for path in ("/odrig/x", "/odrig/", "/ODRIG", "/odrigs", "/x/odrig", "/nothing", "/odrig%3Fx"):
            for method in ("POST", "GET"):
                answer = self.emulator.request(method=method, path=path, body=b"on" if method == "POST" else None)
                self.assertEqual((answer.status, answer.body), (404, b""), (method, path))

    def test_the_content_type_of_the_request_is_not_looked_at(self):
        replies = set()
        for content_type in ("application/octet-stream", "text/plain", "application/x-www-form-urlencoded", "application/json", "image/png", None):
            headers = {"Content-Type": content_type} if content_type else {}
            answer = self.emulator.request(body=b"brightness 31\n", headers=headers)
            self.assertEqual(answer.status, 200, content_type)
            replies.add(answer.body)
            self.assertEqual(self.emulator.status()["brightness"], 31)
            self.emulator.command("brightness 128")
        self.assertEqual(replies, {b'{"ok":true}\n'})

    def test_what_one_transport_changes_status_over_the_other_reports(self):
        with support.lines(self.emulator) as port:
            self.assertEqual(self.emulator.command("brightness 7"), b'{"ok":true}\n')
            through_the_port = json.loads(port.ask("status"))
            self.assertEqual((through_the_port["brightness"], through_the_port["on"]), (7, True))
            self.assertEqual(port.ask("off"), b'{"ok":true}\n')
            over_http = self.emulator.status()
            self.assertEqual((over_http["brightness"], over_http["on"]), (7, False))
            self.assertEqual(support.without_fps(port.ask("status")), support.without_fps(self.emulator.command("status")))
            self.assertEqual(port.ask("on"), b'{"ok":true}\n')
            self.assertEqual(self.emulator.command("brightness 128"), b'{"ok":true}\n')
            self.assertEqual(json.loads(port.ask("status"))["brightness"], 128)

    def test_requests_at_the_same_time_are_all_answered(self):
        failures = []

        def ask():
            try:
                for _ in range(25):
                    status = self.emulator.status()
                    if status["ok"] is not True or status["error"] is not None:
                        failures.append(status)
            except Exception as error:
                failures.append(error)

        threads = [threading.Thread(target=ask) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(failures, [])

    def test_the_server_listens_on_127_0_0_1_only(self):
        self.assertEqual(self.emulator.url, f"http://127.0.0.1:{self.emulator.port}/")
        self.assertFalse(support.refused(self.emulator.port))
        self.assertTrue(support.refused(self.emulator.port, "::1"))
        expected = sorted(address for address in (f"127.0.0.1:{self.emulator.port}", self.emulator.tcp) if address is not None)
        self.assertEqual(support.listening(self.emulator), expected)


class Engine:
    """Stands in for the engine: keeps every line the server hands it."""

    def __init__(self):
        self.lines = []
        self.hub = hub.Hub()

    def line(self, data, transport):
        self.lines.append((data, transport))
        return b'{"ok":true}\n'


class WhatTheServerPassesOn(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()
        self.folder = support.entered(self, tempfile.TemporaryDirectory())
        self.server = httpd.Server(0, self.engine, self.folder, lambda: {})
        self.addCleanup(self.server.stop)
        self.server.start()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=10)
        self.addCleanup(connection.close)
        connection.request(method, path, body=body, headers=headers or {})
        answer = connection.getresponse()
        return answer.status, answer.read()

    def test_the_body_is_passed_on_as_it_arrived_with_or_without_its_newline(self):
        bodies = [b"status", b"status\n", b"play 2\r\n", b"", b"\x00\xff caf\xc3\xa9", b"x" * 128, bytes(range(256)) * 16]
        for body in bodies:
            self.assertEqual(self.request("POST", "/odrig", body), (200, b'{"ok":true}\n'))
        self.assertEqual(self.engine.lines, [(body, "http") for body in bodies])

    def test_of_a_body_longer_than_4096_bytes_the_first_4096_are_passed_on(self):
        long_body = bytes(range(256)) * 40
        for body in (long_body[:4097], long_body[:5000], long_body):
            self.assertEqual(self.request("POST", "/odrig", body)[0], 200)
        self.assertEqual(self.engine.lines, [(long_body[:4096], "http")] * 3)

    def test_the_front_end_is_not_called_for_another_method_a_missing_length_or_another_path(self):
        for method in ("GET", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"):
            self.assertEqual(self.request(method, "/odrig", None if method in ("GET", "HEAD") else b"on")[0], 405, method)
        self.assertEqual(self.request("POST", "/odrig/x", b"on")[0], 404)
        self.assertEqual(self.request("POST", "/", b"on")[0], 404)
        received = support.raw_request(self.server.port, b"POST /odrig HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\non\n")
        self.assertRegex(received, rb"\AHTTP/1\.1 411 ")
        self.assertEqual(self.engine.lines, [])

    def test_a_port_that_is_taken_is_address_in_use(self):
        with self.assertRaises(failure.Failure) as caught:
            httpd.Server(self.server.port, self.engine, self.folder, lambda: {})
        self.assertEqual(caught.exception.reason, "address-in-use")
        self.assertIn(f"127.0.0.1:{self.server.port}", caught.exception.detail)


class InvalidShow(unittest.TestCase):
    def test_every_command_still_reaches_the_core_and_gets_its_reply(self):
        with support.example_show() as folder:
            (folder / "dvd.odrg").unlink()
            files = support.files_of(folder)
            with support.Emulator(folder) as emulator:
                player = ReferencePlayer(files)
                player.poll(0)
                for line in ("status", "play 1", "brightness 9", "off", "status", "on", "play 99", "dance", "status"):
                    answer = emulator.request(body=line.encode("ascii"))
                    self.assertEqual(answer.status, 200)
                    self.assertEqual(support.without_fps(answer.body), support.without_fps(player.command(50, line.encode("ascii"))), line)
                self.assertEqual(emulator.command("play 1"), b'{"ok":false,"error":"show-invalid"}\n')
                self.assertEqual(emulator.status()["error"], "file-missing dvd.odrg")
                with support.lines(emulator) as port:
                    for line in ("status", "play 2", "brightness 200", "off", "on", "status", "dance"):
                        self.assertEqual(support.without_fps(port.ask(line)), support.without_fps(player.command(60, line.encode("ascii"))), line)


if __name__ == "__main__":
    unittest.main()

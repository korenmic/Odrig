import http.client
import json
import tempfile
import time
import unittest

from emulator import httpd, hub
from tests.core import support as core_support
from tests.core.support import ReferencePlayer

from . import support


def has(kind, count=1):
    """A condition for `read_until`: at least this many events of one kind were read."""
    return lambda events: sum(event.kind == kind for event in events) >= count


class Stream(unittest.TestCase):
    def setUp(self):
        self.folder = support.entered(self, support.example_show())
        self.emulator = support.entered(self, support.Emulator(self.folder, checked=False))

    def stream(self, **settings):
        return support.entered(self, support.EventStream(self.emulator.port, **settings))

    def test_it_is_an_event_stream_without_a_length_that_is_not_stored(self):
        stream = self.stream()
        self.assertEqual(stream.status, 200)
        self.assertEqual(stream.headers["content-type"], "text/event-stream")
        self.assertEqual(stream.headers["cache-control"], "no-store")
        self.assertNotIn("content-length", stream.headers)

    def test_hello_comes_first_with_the_legs_and_the_power_on_moment(self):
        stream = self.stream()
        events = stream.read_until(has("frame"))
        self.assertEqual(events[0].kind, "hello")
        self.assertEqual([event.kind for event in events].count("hello"), 1)
        hello = json.loads(events[0].data)
        self.assertEqual(sorted(hello), ["drive", "error", "legs", "page", "serial", "show", "t0", "tcp"])
        self.assertEqual(hello["legs"], [[1, 1, 180], [2, 2, 180]])
        self.assertIsNone(hello["error"])
        self.assertEqual(hello["page"], self.emulator.url)
        self.assertEqual(hello["serial"], self.emulator.serial)
        self.assertEqual(hello["show"], str(self.folder))
        self.assertIsInstance(hello["t0"], int)
        self.assertLessEqual(0, hello["t0"])
        self.assertLess(hello["t0"], support.frames(events)[0][0])
        self.assertEqual(events[1].kind, "status")

    def test_a_connection_gets_the_position_right_after_the_latest_status(self):
        self.emulator.command("play all")
        stream = self.stream()
        events = stream.read_until(has("frame"))
        kinds = [event.kind for event in events]
        self.assertIn("position", kinds)
        self.assertEqual(kinds.index("position"), kinds.index("status") + 1)
        position = json.loads(events[kinds.index("position")].data)
        self.assertEqual(sorted(position), ["animation", "length", "start", "turn"])
        self.assertEqual(position["animation"], 1)
        hello = json.loads(events[0].data)
        self.assertEqual((position["start"] - hello["t0"]) % 20, 0, (position, hello["t0"]))
        self.assertEqual(position["turn"], position["start"])

    def test_100_refreshes_in_a_row_each_equal_the_reference_for_their_timestamp(self):
        stream = self.stream()
        events = stream.read_until(has("frame", 100))
        hello = json.loads(events[0].data)
        frames = support.frames(events)[:100]
        self.assertEqual(len(frames), 100)
        player = ReferencePlayer(support.files_of(self.folder))
        self.assertIsNotNone(player.poll(hello["t0"]))
        lit = 0
        for ms, data in frames:
            self.assertEqual(len(data), 1080)
            refresh = player.poll(ms)
            self.assertIsNotNone(refresh, f"two refreshes in one grid time, the second at {ms}")
            self.assertEqual(data, b"".join(rgb for _, rgb in refresh), f"the refresh at {ms} differs from the reference")
            lit += any(data)
        self.assertGreater(lit, 50)
        times = [ms for ms, _ in frames]
        self.assertEqual(times, sorted(set(times)))
        self.assertLessEqual(times[-1] - times[0], 99 * 20 + 60)

    def test_a_frame_event_holds_a_timestamp_and_the_led_bytes_and_nothing_else(self):
        stream = self.stream()
        events = [event for event in stream.read_until(has("frame", 5)) if event.kind == "frame"]
        for event in events:
            self.assertRegex(event.data, r"\A[0-9]+ [A-Za-z0-9+/]{1440}\Z")

    def test_at_least_147_refreshes_arrive_in_3_seconds_on_this_mac(self):
        stream = self.stream()
        stream.read_until(has("frame"))
        frames = support.frames(stream.read_for(3))
        self.assertGreaterEqual(len(frames), 147, f"on this Mac only {len(frames)} refreshes of the example show arrived in 3 seconds")
        self.assertLessEqual(len(frames), 152)

    def test_a_command_by_each_transport_gives_one_log_event_and_a_later_status_event(self):
        stream = self.stream()
        stream.read_until(has("frame"))
        with support.lines(self.emulator) as port:
            sent = []
            for transport, line in (("http", "brightness 33"), (support.LINES, "off"), ("http", "play 99"), (support.LINES, "play 2"), (support.LINES, "dance"), ("http", "on")):
                if transport == "http":
                    reply = self.emulator.command(line)
                else:
                    reply = port.ask(line)
                sent.append({"transport": transport, "line": line, "cut": False, "reply": reply.decode("ascii").rstrip("\n")})
                events = stream.read_until(lambda events: has("log")(events) and events[-1].kind == "status" and has("status")(events[[event.kind for event in events].index("log"):]), 5)
                kinds = [event.kind for event in events if event.kind != "frame"]
                self.assertEqual(kinds.count("log"), 1, line)
                after_the_log = events[[event.kind for event in events].index("log"):]
                status = support.without_fps(json.dumps(support.of_kind(after_the_log, "status")[-1]))
                self.assertEqual(status, support.without_fps(port.ask("status")), line)
                stream.read_until(has("log"), 5)
        logged = support.of_kind(self.stream().read_until(has("status"), 5), "log")
        commands = [entry for entry in logged if entry["line"] != "status"]
        self.assertEqual([{name: entry[name] for name in ("transport", "line", "cut", "reply")} for entry in commands], sent)
        self.assertEqual([entry["seq"] for entry in logged], list(range(1, len(logged) + 1)))
        for entry in logged:
            self.assertRegex(entry["time"], r"\A[0-2][0-9]:[0-5][0-9]:[0-5][0-9]\.[0-9]{3}\Z")
            self.assertIsInstance(entry["ms"], int)

    def test_there_is_one_log_event_for_each_command_and_none_for_the_status_requests_of_the_emulator(self):
        stream = self.stream()
        stream.read_until(has("frame"))
        lines = ["brightness 40", "status", "off", "on"]
        for line in lines:
            self.emulator.command(line)
        events = stream.read_for(2.6)
        logged = support.of_kind(events, "log")
        self.assertEqual([entry["line"] for entry in logged], lines, f"{len(logged)} log events for {len(lines)} commands")
        self.assertGreaterEqual(len(support.of_kind(events, "status")), len(lines) + 2)

    def test_the_status_arrives_at_least_once_a_second_and_is_the_reply_of_the_core(self):
        stream = self.stream()
        stream.read_until(has("frame"))
        arrivals = []
        deadline = time.monotonic() + 3.5
        while time.monotonic() < deadline:
            for event in stream.read_until(has("status"), 2):
                if event.kind == "status":
                    arrivals.append(time.monotonic())
                    self.assertRegex(event.data, r'\A\{"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":[0-9]+,"error":null,"width":60,"height":6,"readiness":"[a-z]+",[^{}]*\}\Z')
        self.assertGreaterEqual(len(arrivals), 3)
        self.assertLess(max(later - earlier for earlier, later in zip(arrivals, arrivals[1:])), 1.2)

    def test_a_late_connection_receives_the_entries_kept_so_far(self):
        self.emulator.command("brightness 50")
        with support.lines(self.emulator) as port:
            port.ask("off")
        self.emulator.command("on\r\n")
        events = self.stream().read_until(has("frame"))
        self.assertEqual([event.kind for event in events[:5]], ["hello", "log", "log", "log", "status"])
        self.assertEqual([(entry["transport"], entry["line"]) for entry in support.of_kind(events, "log")], [("http", "brightness 50"), (support.LINES, "off"), ("http", "on")])
        self.assertEqual(support.of_kind(events, "status")[0]["brightness"], 50)

    def test_the_last_500_entries_are_kept(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.emulator.port, timeout=10)
        self.addCleanup(connection.close)
        for number in range(503):
            connection.request("POST", "/odrig", body=b"brightness %d" % (number % 256))
            self.assertEqual(connection.getresponse().read(), b'{"ok":true}\n')
        logged = support.of_kind(self.stream().read_until(has("frame")), "log")
        self.assertEqual(len(logged), 500)
        self.assertEqual((logged[0]["seq"], logged[-1]["seq"]), (4, 503))
        self.assertEqual((logged[0]["line"], logged[-1]["line"]), ("brightness 3", "brightness 246"))

    def test_a_line_of_2060_characters_is_logged_with_200_its_length_as_read_and_marked_as_cut(self):
        long_line = "play " + "8" * 2055
        self.assertEqual(len(long_line), 2060)
        self.emulator.command(long_line)
        with support.lines(self.emulator) as port:
            port.ask(long_line)
        self.emulator.command("x" * 64)
        logged = support.of_kind(self.stream().read_until(has("frame")), "log")
        self.assertEqual(
            [(entry["line"], entry["length"], entry["cut"]) for entry in logged],
            [(long_line[:200], 2048, True), (long_line[:200], 2048, True), ("x" * 64, 64, False)],
        )
        self.assertEqual({entry["reply"] for entry in logged[:2]}, {'{"ok":false,"error":"line-too-long"}'})

    def test_a_line_of_1000_characters_is_logged_with_200_and_its_length(self):
        line = "play " + "8" * 995
        self.emulator.command(line)
        with support.lines(self.emulator) as port:
            port.ask(line)
        logged = support.of_kind(self.stream().read_until(has("frame")), "log")
        self.assertEqual([(entry["line"], entry["length"], entry["cut"]) for entry in logged], [(line[:200], 1000, False)] * 2)
        self.assertEqual({entry["reply"] for entry in logged}, {'{"ok":false,"error":"bad-argument"}'})

    def test_bytes_outside_printable_ascii_are_logged_as_escapes(self):
        with support.lines(self.emulator) as port:
            port.ask(b"pl\x00y \xff\t\n")
        self.emulator.command(b"caf\xc3\xa9")
        logged = support.of_kind(self.stream().read_until(has("frame")), "log")
        self.assertEqual([entry["line"] for entry in logged], ["pl\\x00y \\xFF\\x09", "caf\\xC3\\xA9"])

    def test_two_pages_at_once_both_receive_everything(self):
        first, second = self.stream(), self.stream()
        first.read_until(has("frame"))
        second.read_until(has("frame"))
        self.emulator.command("brightness 60")
        for stream in (first, second):
            events = stream.read_until(lambda events: has("log")(events) and has("frame", 10)(events), 5)
            self.assertEqual([entry["line"] for entry in support.of_kind(events, "log")], ["brightness 60"])
            self.assertGreaterEqual(len(support.frames(events)), 10)

    def test_the_mapping_file_is_served_byte_for_byte(self):
        answer = self.emulator.request("GET", "/show/mapping.json")
        self.assertEqual(answer.status, 200)
        self.assertEqual(answer.headers["content-type"], "application/json")
        self.assertEqual(answer.headers["cache-control"], "no-store")
        self.assertEqual(answer.body, (self.folder / "mapping.json").read_bytes())
        self.assertEqual(answer.body, support.TWO_LEGS.read_bytes())
        self.assertEqual(self.emulator.request("GET", "/show/mapping.json?now").body, answer.body)
        for path in ("/show/show.json", "/show/hello.odrg", "/show/", "/show/mapping.json/", "/show/../mapping.json", "/mapping.json"):
            self.assertEqual(self.emulator.request("GET", path).status, 404, path)
        self.assertEqual(self.emulator.request("POST", "/show/mapping.json", body=b"{}").status, 404)
        self.assertEqual(self.emulator.request("POST", "/events", body=b"").status, 404)


class OtherShows(unittest.TestCase):
    def setUp(self):
        self.work = support.entered(self, tempfile.TemporaryDirectory())

    def test_a_folder_without_a_show_gives_no_legs_the_reason_and_no_mapping_file(self):
        with support.Emulator(self.work) as emulator, support.EventStream(emulator.port) as stream:
            events = stream.read_until(has("status"), 5)
            hello = json.loads(events[0].data)
            self.assertEqual((hello["legs"], hello["error"]), ([], "mapping-missing"))
            self.assertEqual(support.of_kind(events, "status")[0]["error"], "mapping-missing")
            self.assertEqual(emulator.request("GET", "/show/mapping.json").status, 404)
            more = stream.read_for(1.5)
            self.assertEqual(support.frames(events + more), [])
            self.assertGreaterEqual(len(support.of_kind(more, "status")), 1)

    def test_a_mapping_the_core_refuses_is_still_served_as_it_is(self):
        folder = support.installed(self.work, {"mapping.json": b'{"version": 1, "width": 60, "legs": []}\n'})
        with support.Emulator(folder) as emulator, support.EventStream(emulator.port) as stream:
            hello = json.loads(stream.read_until(has("hello"), 5)[0].data)
            self.assertEqual((hello["legs"], hello["error"]), ([], "mapping-malformed"))
            self.assertEqual(emulator.request("GET", "/show/mapping.json").body, b'{"version": 1, "width": 60, "legs": []}\n')

    def test_an_invalid_show_gives_its_legs_its_reason_and_dark_refreshes(self):
        files = core_support.example_show()
        del files["dvd.odrg"]
        folder = support.installed(self.work, core_support.with_show_fault(files))
        with support.Emulator(folder) as emulator, support.EventStream(emulator.port) as stream:
            events = stream.read_until(has("frame", 10), 5)
            hello = json.loads(events[0].data)
            self.assertEqual((hello["legs"], hello["error"]), ([[1, 1, 180], [2, 2, 180]], "undefined-id 99"))
            self.assertEqual({data for _, data in support.frames(events)}, {bytes(1080)})


class SlowPage(unittest.TestCase):
    """A page that stops reading is felt by the emulator only once the buffers of the
    system between the two are full, which on this Mac hold about half a megabyte. The
    canvas of this test is tall, so that they fill within a few refreshes."""

    WIDTH, HEIGHT = 60, 300

    def test_a_connection_that_reads_nothing_for_2_seconds_then_receives_the_newest_refresh(self):
        folder = support.installed(support.entered(self, tempfile.TemporaryDirectory()), {
            "mapping.json": core_support.one_leg_mapping(self.WIDTH, self.HEIGHT),
            "show.json": core_support.show_text([{"id": 1, "file": "tall.odrg"}], brightness=255, start=1),
            "tall.odrg": core_support.clip("tall", self.WIDTH, self.HEIGHT, durations=(1000, 1000)),
        })
        with support.Emulator(folder) as emulator, support.EventStream(emulator.port) as stream:
            before = stream.read_until(has("frame", 5))
            self.assertEqual(json.loads(before[0].data)["legs"], [[1, 1, self.WIDTH * self.HEIGHT]])
            for number in range(30):
                emulator.command(f"brightness {200 + number}")
            time.sleep(2)
            after = stream.read_until(lambda events: False, 1.5)
            frames = support.frames(before + after)
            times = [ms for ms, _ in frames]
            self.assertEqual(times, sorted(set(times)))
            gaps = [later - earlier for earlier, later in zip(times, times[1:])]
            self.assertGreaterEqual(max(gaps), 1000, f"no refresh was skipped while nothing was read: {gaps}")
            self.assertLess(len(times), 5 + 100 + 75 - 50, "refreshes of the two silent seconds were sent late instead of skipped")
            self.assertLessEqual(max(gaps[-10:]), 60, f"the refreshes after the gap are not the newest ones: {gaps}")
            self.assertTrue(all(len(data) == 3 * self.WIDTH * self.HEIGHT for _, data in frames))
            logged = support.of_kind(after, "log")
            self.assertEqual([entry["line"] for entry in logged], [f"brightness {200 + number}" for number in range(30)])
            self.assertGreaterEqual(len(support.of_kind(after, "status")), 30)
            brightest = max(frames[0][1])
            self.assertGreater(brightest, 100)
            self.assertEqual(max(frames[-1][1]), (brightest * 229 + 127) // 255)


class Writer(unittest.TestCase):
    def test_a_connection_with_nothing_to_send_is_sent_a_comment_line(self):
        kept = hub.Hub()
        connection = kept.connect({"legs": []})
        written = []

        def write(data):
            written.append(data)
            if len(written) == 3:
                kept.disconnect(connection)

        httpd.stream(connection, write, keep_alive_seconds=0.05)
        self.assertEqual(written, [b'event: hello\ndata: {"legs":[]}\n\n', b": keep-alive\n\n", b": keep-alive\n\n"])

    def test_every_event_is_written_at_once_and_a_failed_write_ends_the_stream(self):
        kept = hub.Hub()
        connection = kept.connect({})
        kept.status(b'{"ok":true}\n')
        kept.refresh(40, b"\x00\x01\x02")
        written = []

        def write(data):
            written.append(data)
            if len(written) == 2:
                raise BrokenPipeError()
            kept.status(b'{"ok":true,"on":false}\n')

        httpd.stream(connection, write, keep_alive_seconds=5)
        self.assertEqual(written, [
            b'event: hello\ndata: {}\n\nevent: status\ndata: {"ok":true}\n\nevent: frame\ndata: 40 AAEC\n\n',
            b'event: status\ndata: {"ok":true,"on":false}\n\n',
        ])

    def test_the_keep_alive_time_is_15_seconds(self):
        self.assertEqual(httpd.KEEP_ALIVE_SECONDS, 15)


if __name__ == "__main__":
    unittest.main()

import json
import pathlib
import tempfile
import time
import unittest

from odrigctl import client

from fwtool import board, partitions, paths

from . import PORT, support

# What the owner accepts on the board for any content: 20 refreshes a second or more.
LOWEST = 20
SECONDS_AFTER = 10
STORE_BYTES = 1000000
# The space the file system may keep for itself after a file was written and removed.
SPACE_SLACK = 16384
RESULT = paths.OUT / "store.json"
# The item the tests upload, the names its files get, and where the figures of the large
# upload are written.
NEW_ITEM = support.NEW_ITEM
HELLO_NAME = support.HELLO_NAME
DENSE_NAME = "dense-bench.odrg"
DENSE_SECONDS = 60
UPLOAD_RESULT = paths.OUT / "upload.json"
# The storage of the board on either of its layouts.
BOARD_TOTALS = (partitions.storage(partitions.WLED).size, partitions.storage(partitions.BIGGER).size)
TOO_LONG = {"ok": False, "error": "line-too-long"}
UNKNOWN = {"ok": False, "error": "unknown-command"}


def is_store(line):
    """Whether a line is the answer of the probe build's store trial."""
    try:
        value = json.loads(line)
    except ValueError:
        return False
    return isinstance(value, dict) and "store" in value and "probe" not in value


def space(port):
    reply = port.ask(b"space\n")
    if reply.get("ok") is not True:
        raise AssertionError(f"`space` was answered with {reply}")
    return reply


def store_trial(port, size, seconds=180):
    """Runs the store trial for a file of some bytes and asks for a report once a second
    while it runs. Returns its answer and the reports that cover the trial."""
    port.ask(b"#probe\n", board.is_probe)
    time.sleep(1.2)
    port.send(f"#store {size}\n".encode("ascii"))
    reports = []
    answer = None
    began = time.monotonic()
    asked = 0
    while answer is None and time.monotonic() - began < seconds:
        time.sleep(max(0.0, began + asked + 1 - time.monotonic()))
        asked += 1
        port.send(b"#probe\n")
        deadline = time.monotonic() + 5.0
        report = None
        while report is None and time.monotonic() < deadline:
            for line in port.lines(0.05):
                if is_store(line):
                    answer = json.loads(line)
                elif board.is_probe(line):
                    report = json.loads(line)
                    break
        if report is None:
            raise AssertionError(f"no report within 5 seconds, {asked} seconds into the store trial")
        reports.append(report)
    if answer is None:
        answer_line = port.line(is_store, 5.0)
        answer = json.loads(answer_line) if answer_line is not None else None
    return answer, reports


class Spike(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("probe")
        with support.dim_show() as folder:
            support.ensure_installed(folder)
            cls.installed = support.files_of(folder)

    def test_a_megabyte_is_written_renamed_read_back_and_removed_while_the_show_plays(self):
        with support.Port() as port:
            before = space(port)
            answer, during = store_trial(port, STORE_BYTES)
            self.assertIsNotNone(answer, "the store trial gave no answer")
            after = [report for report in support.each_second(SECONDS_AFTER, lambda: port.ask(b"#probe\n", board.is_probe))]
            later = space(port)
        # The reports that lie wholly inside the trial: every one but the last, whose second
        # ended after the trial did.
        inside = during[:-1]
        sent_during = [report["sent"] for report in inside]
        sent_after = [report["sent"] for report in after]
        stored = [report["store"] for report in during]
        RESULT.parent.mkdir(parents=True, exist_ok=True)
        RESULT.write_text(json.dumps({
            "answer": answer,
            "sent_during": sent_during,
            "sent_after": sent_after,
            "store_during": stored,
            "gap_ms_during": [report["gap_ms"] for report in inside],
            "poll_us_during": [report["poll_us"] for report in inside],
            "space_before": before,
            "space_after": later,
        }, indent=2) + "\n")
        self.assertEqual((answer["ok"], answer["failed"]), (True, None), answer)
        self.assertEqual((answer["bytes"], answer["written"], answer["read"]), (STORE_BYTES, STORE_BYTES, STORE_BYTES))
        self.assertEqual(answer["writes"], -(-STORE_BYTES // 1500))
        self.assertGreater(answer["rename_us"], 0)
        self.assertGreaterEqual(len(inside), 5, "the trial was over before its rate could be read")
        self.assertEqual({report["error"] for report in during + after}, {None})
        self.assertEqual({report["overwritten"] for report in during + after}, {0})
        self.assertGreaterEqual(sum(entry["calls"] for entry in stored), answer["writes"])
        status = support.command(PORT, "status")[1]
        self.assertEqual((status["playing"], status["error"], status["brightness"]), (3, None, support.DIM))
        self.assertGreaterEqual(min(sent_during), LOWEST, sent_during)
        self.assertGreaterEqual(min(sent_after), LOWEST, sent_after)
        self.assertEqual(later["total"], before["total"])
        self.assertLessEqual(abs(later["free"] - before["free"]), SPACE_SLACK, (before, later))
        self.assertEqual(later["animations"], 2)
        self.assertEqual(support.installed(), self.installed)
        # The board has started again and asked the file system afresh: what it kept up
        # while the megabyte was written and removed was what storage holds.
        with support.Port() as port:
            afresh = space(port)
        self.assertLessEqual(abs(afresh["free"] - later["free"]), SPACE_SLACK, (later, afresh))

    def test_a_small_trial_makes_the_storage_calls_the_report_counts(self):
        with support.Port() as port:
            port.ask(b"#probe\n", board.is_probe)
            port.send(b"#store 3000\n")
            answer = json.loads(port.line(is_store, 20.0))
            report = port.ask(b"#probe\n", board.is_probe)
        self.assertEqual((answer["ok"], answer["written"], answer["read"], answer["writes"]), (True, 3000, 3000, 2))
        # The small file under the final name is three calls, then one to begin the
        # trial's file, two writes, the end, the rename and the removal.
        self.assertEqual(report["store"]["calls"], 9)
        self.assertGreaterEqual(report["store"]["total_us"], report["store"]["longest_us"])
        self.assertGreater(report["store"]["longest_us"], 0)

    def test_the_space_is_told_without_a_storage_call_and_follows_what_is_written_and_removed(self):
        with support.Port() as port:
            before = space(port)
            port.ask(b"#probe\n", board.is_probe)
            again = space(port)
            report = port.ask(b"#probe\n", board.is_probe)
            port.send(b"#store 100000\n")
            self.assertTrue(json.loads(port.line(is_store, 60.0))["ok"])
            after = space(port)
        self.assertEqual((before["ok"], before["animations"]), (True, 2))
        self.assertIn(before["total"], BOARD_TOTALS)
        self.assertEqual(again, before)
        self.assertEqual(report["store"]["calls"], 0)
        # The file system was asked once, at the start, and that took a while.
        self.assertGreater(report["space_us"], 1000)
        self.assertEqual(after, before)
        self.assertEqual(before["free"] % 4096, 0)

    def test_a_line_of_2048_characters_in_one_piece_is_read_and_one_of_2049_is_too_long(self):
        with support.Port() as port:
            for number in range(20):
                self.assertEqual(port.ask(b"x" * 2048 + b"\n"), UNKNOWN, f"line of 2,048 characters, number {number + 1}")
                self.assertEqual(port.ask(b"x" * 2049 + b"\n"), TOO_LONG, f"line of 2,049 characters, number {number + 1}")
            self.assertEqual(port.ask(b"x" * 2048 + b"\r\n"), UNKNOWN)
            self.assertEqual(port.ask(b"y" * 2049 + b"\r\n"), TOO_LONG)
            self.assertEqual(port.ask(b"status\n")["error"], None)

    def test_the_probe_lines_are_answered_by_the_usermod_and_what_is_like_them_reaches_the_core(self):
        with support.Port() as port:
            for line in (b"#store\n", b"#store \n", b"#store x\n", b"#store 12a\n", b"#store 12345678901\n", b"#stor 5\n", b" #store 5\n"):
                self.assertEqual(port.ask(line), UNKNOWN, line)
            self.assertEqual(port.ask(b"on #store 5\n"), {"ok": False, "error": "bad-argument"})
            self.assertEqual(port.ask(b"#probe\n", board.is_probe)["probe"], 1)


class Emulated:
    """An emulator on a folder, with the board's total storage, that can be started again
    on the same folder as a board is restarted."""

    def __init__(self, folder, total):
        self.folder = folder
        self.total = total
        self.start()

    def start(self):
        self._running = support.emulator(self.folder, "--storage", self.total)
        self.link = self._running.__enter__()

    def stop(self):
        self._running.__exit__(None, None, None)

    def restart(self):
        self.stop()
        self.start()


class ContentCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("firmware")
        cls.work = pathlib.Path(cls.enterClassContext(tempfile.TemporaryDirectory()))
        with support.dim_show() as folder:
            support.ensure_installed(folder)
            cls.installed = support.files_of(folder)
        cls.hello = cls.work / HELLO_NAME
        cls.hello.write_bytes(support.hello_for(support.TWO_LEGS))

    def test_the_tool_uploads_lists_plays_and_removes_an_animation_and_the_board_keeps_it_over_a_restart(self):
        size = self.hello.stat().st_size
        support.restart()
        kept = {}
        try:
            # The restart in the middle of the session is the one that follows reading the
            # board's storage, so that the folder with the uploaded file in it is seen.
            on_the_board = support.content_session(lambda *words: support.command(PORT, *words), lambda: kept.update(support.read_back()), self.hello)
        finally:
            support.changed_by_commands()
        replies = {number: (status, reply) for number, (_, status, reply) in enumerate(on_the_board)}
        # The upload itself, before anything is compared: a board that cannot take a file
        # says so here.
        self.assertEqual(replies[2], (0, {"ok": True}), "the reply that ended the upload on the board")
        new = {"id": NEW_ITEM, "file": HELLO_NAME, "bytes": size}
        before = replies[1][1]["items"]
        self.assertEqual([item["id"] for item in before], [1, 2, 3])
        self.assertEqual(replies[3], (0, {"ok": True, "items": before + [new], "next": None}))
        self.assertEqual(replies[5][1], {"ok": True, "on": True, "brightness": support.DIM, "playing": "all", "animation": NEW_ITEM, "error": None})
        self.assertEqual((replies[0][1]["animations"], replies[6][1]["animations"]), (2, 3))
        self.assertIn(replies[6][1]["total"], BOARD_TOTALS)
        # After the restart the show still has the item, plays its start item, and plays
        # the new one in the playlist when it is told to. When the new one is removed in
        # its turn, the playlist goes on with the animation after it, which is the first.
        self.assertEqual(replies[7], replies[3])
        self.assertEqual(sorted(kept), sorted([*self.installed, HELLO_NAME]))
        self.assertEqual(kept[HELLO_NAME], self.hello.read_bytes())
        self.assertEqual((replies[8][1]["playing"], replies[8][1]["animation"], replies[8][1]["error"]), (3, 1, None))
        self.assertEqual((replies[10][1]["playing"], replies[10][1]["animation"]), ("all", NEW_ITEM))
        self.assertEqual(replies[11], (0, {"ok": True}))
        self.assertEqual(replies[12], (0, {"ok": True, "items": before, "next": None}))
        self.assertEqual((replies[13][1]["playing"], replies[13][1]["animation"], replies[13][1]["error"]), ("all", 1, None))
        self.assertEqual([replies[number] for number in (15, 16, 17)], [(1, {"ok": False, "error": "in-use"})] * 2 + [(1, {"ok": False, "error": "unknown-id"})])

        left = support.read_back()
        folder = self.work / "emulated"
        folder.mkdir()
        for name, data in self.installed.items():
            (folder / name).write_bytes(data)
        emulated = Emulated(folder, replies[6][1]["total"])
        try:
            in_the_emulator = support.content_session(lambda *words: support.command(emulated.link, *words), emulated.restart, self.hello)
        finally:
            emulated.stop()
        self.assertEqual(len(on_the_board), 18)
        for number, ((line, *board_answer), (_, *emulator_answer)) in enumerate(zip(on_the_board, in_the_emulator), 1):
            self.assertEqual(board_answer, emulator_answer, f"command {number} of the session, `{line}`: the board's answer is the first")
        # The folder on the board is as it was installed, with the show file as the core
        # writes it, and it is byte for byte the folder the emulator has after the session.
        self.assertEqual(left, support.files_of(folder))
        self.assertEqual(sorted(left), sorted(self.installed))
        self.assertEqual({name: data for name, data in left.items() if name != "show.json"}, {name: data for name, data in self.installed.items() if name != "show.json"})
        self.assertEqual(json.loads(left["show.json"]), json.loads(self.installed["show.json"]))
        status = support.command(PORT, "status")[1]
        self.assertEqual((status["playing"], status["error"], status["brightness"]), (3, None, support.DIM))


class DenseUpload(unittest.TestCase):
    """The upload of a large file with the rate the board keeps meanwhile, measured with
    the probe build."""

    @classmethod
    def setUpClass(cls):
        support.ensure("probe")
        with support.dim_show() as folder:
            support.ensure_installed(folder)
        width, height = support.canvas_of(support.TWO_LEGS)
        cls.clip = support.dense_clip(True, DENSE_SECONDS, width, height)

    def test_a_dense_clip_of_a_minute_is_uploaded_while_the_show_plays_at_20_refreshes_a_second_or_more(self):
        support.restart()
        support.probe()
        try:
            with client.Session(port=PORT, timeout=5.0) as port:
                before = json.loads(port.exchange(b"space\n"))
                reply, rates, times = support.measured_upload(port, NEW_ITEM, DENSE_NAME, self.clip)
                after = support.each_second(SECONDS_AFTER, lambda: json.loads(port.exchange(b"status\n"))["fps"])
                listed = json.loads(port.exchange(b"list\n"))
                with_the_file = json.loads(port.exchange(b"space\n"))
            report = support.probe()
            with client.Session(port=PORT, timeout=5.0) as port:
                removed = json.loads(port.exchange(b"remove %d\n" % NEW_ITEM))
                later = json.loads(port.exchange(b"space\n"))
        finally:
            support.changed_by_commands()
        speed = round(len(self.clip) / times["data"]) if times["data"] else 0
        UPLOAD_RESULT.parent.mkdir(parents=True, exist_ok=True)
        UPLOAD_RESULT.write_text(json.dumps({
            "bytes": len(self.clip),
            "frames": DENSE_SECONDS * 50,
            "reply": reply,
            "data_seconds": round(times["data"], 2),
            "bytes_per_second": speed,
            "check_seconds": round(times["check"], 2),
            "fps_during_data": rates["data"],
            "fps_during_check": rates["check"],
            "fps_after": after,
            "store": report["store"],
            "gap_ms": report["gap_ms"],
            "poll_us": report["poll_us"],
            "space_before": before,
            "space_with_the_file": with_the_file,
            "space_after": later,
        }, indent=2) + "\n")
        self.assertEqual(reply, {"ok": True}, "the reply that ended the upload")
        self.assertGreaterEqual(len(rates["data"]), 20, "the upload was over before its rate could be read")
        self.assertGreaterEqual(len(rates["check"]), 20, "the check was over before its rate could be read")
        self.assertGreaterEqual(min(rates["data"]), LOWEST, rates["data"])
        self.assertGreaterEqual(min(rates["check"]), LOWEST, rates["check"])
        self.assertGreaterEqual(min(after), LOWEST, after)
        self.assertEqual(listed["items"][-1], {"id": NEW_ITEM, "file": DENSE_NAME, "bytes": len(self.clip)})
        # The check decodes one frame of the file for each refresh, so it takes as long as
        # the animation lasts, and it reads the file back from storage meanwhile.
        self.assertGreaterEqual(times["check"], DENSE_SECONDS - 1)
        self.assertGreater(report["store"]["check_steps"], 0)
        self.assertEqual((report["error"], report["overwritten"]), (None, 0))
        self.assertLessEqual(before["free"] - with_the_file["free"], len(self.clip) + len(self.clip) // 256 + SPACE_SLACK)
        self.assertGreaterEqual(before["free"] - with_the_file["free"], len(self.clip))
        self.assertEqual(removed, {"ok": True})
        self.assertLessEqual(abs(later["free"] - before["free"]), SPACE_SLACK, (before, later))
        self.assertGreater(speed, 0)


if __name__ == "__main__":
    unittest.main()

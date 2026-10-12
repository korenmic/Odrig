import json
import time
import unittest

from fwtool import board, paths

from . import PORT, support

# What the owner accepts on the board for any content: 20 refreshes a second or more.
LOWEST = 20
SECONDS_AFTER = 10
STORE_BYTES = 1000000
# The space the file system may keep for itself after a file was written and removed.
SPACE_SLACK = 16384
RESULT = paths.OUT / "store.json"
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
        self.assertEqual((before["ok"], before["animations"], before["total"]), (True, 2, 10354688))
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


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest import mock

from fwtool import board

from . import support

DEVICE = "/dev/cu.usbmodem101"


class ThePort(unittest.TestCase):
    def test_the_port_given_is_used(self):
        self.assertEqual(board.find("/dev/cu.given", {"ODRIG_BOARD_PORT": "/dev/cu.variable"}, [DEVICE]), "/dev/cu.given")

    def test_the_variable_is_used_without_a_port(self):
        self.assertEqual(board.find(None, {"ODRIG_BOARD_PORT": "/dev/cu.variable"}, [DEVICE, "/dev/cu.usbmodem102"]), "/dev/cu.variable")

    def test_the_only_device_is_used_without_either(self):
        self.assertEqual(board.find(None, {}, [DEVICE]), DEVICE)
        self.assertEqual(board.find(None, {"ODRIG_BOARD_PORT": ""}, [DEVICE]), DEVICE)

    def test_no_device_is_no_board(self):
        self.assertEqual(support.reason_of(self, lambda: board.find(None, {}, [])), "no-board")

    def test_two_devices_are_no_board(self):
        with self.assertRaises(board.Failure) as caught:
            board.find(None, {}, [DEVICE, "/dev/cu.usbmodem102"])
        self.assertEqual(caught.exception.reason, "no-board")
        self.assertIn("/dev/cu.usbmodem102", caught.exception.detail)

    def test_the_devices_looked_for_are_usb_serial_devices(self):
        self.assertEqual(board.PORT_PATTERN, "/dev/cu.usbmodem*")
        self.assertEqual(board.PORT_VARIABLE, "ODRIG_BOARD_PORT")


class Answers(unittest.TestCase):
    def test_the_handshake_of_wled_is_the_word_and_a_number(self):
        self.assertTrue(board.is_handshake(b"WLED 2606300"))
        for line in (b"WLED", b"WLED ", b"WLED abc", b"wled 1", b" WLED 1", b'{"ok":true}', b"ESP-ROM:esp32s3-20210327"):
            self.assertFalse(board.is_handshake(line), line)

    def test_the_report_of_the_probe_build_is_an_object_with_the_member_probe(self):
        self.assertTrue(board.is_probe(b'{"probe":1,"sent":50}'))
        for line in (b'{"ok":true}', b"[1]", b"probe", b""):
            self.assertFalse(board.is_probe(line), line)

    def test_a_board_that_never_answers_is_no_reply(self):
        def silent(port, data, timeout, accept):
            raise board.client.Unreachable("no reply within 2 seconds")
        with mock.patch.object(board.client, "serial_exchange", silent), mock.patch.object(board.time, "sleep", lambda seconds: None):
            for ask in (board.status, board.handshake, board.probe):
                self.assertEqual(support.reason_of(self, lambda: ask("/dev/cu.test", wait=0)), "no-reply")

    def test_each_question_sends_its_bytes_and_takes_its_answer(self):
        sent = []
        def exchange(port, data, timeout, accept):
            sent.append((port, data))
            answers = [line for line in (b'{"ok":true,"fps":50}', b"WLED 2606300", b'{"probe":1}') if accept(line)]
            return answers[0]
        with mock.patch.object(board.client, "serial_exchange", exchange):
            self.assertEqual(board.status("/dev/cu.test"), '{"ok":true,"fps":50}')
            self.assertEqual(board.handshake("/dev/cu.test"), "WLED 2606300")
            self.assertEqual(board.probe("/dev/cu.test"), '{"probe":1}')
        self.assertEqual(sent, [("/dev/cu.test", b"status\n"), ("/dev/cu.test", b"v"), ("/dev/cu.test", b"#probe\n")])


class Settled(unittest.TestCase):
    """After a restart the firmware plays at once and reads its animations while it
    plays. Until it has, it answers `list` with `busy`."""

    def settled(self, talks, wait=20):
        with mock.patch.object(board.client, "serial_exchange", talks.exchange), mock.patch.object(board, "time", talks):
            return board.settled("/dev/cu.test", wait)

    def test_a_board_whose_list_is_given_during_the_check_is_waited_for_by_its_readiness(self):
        checking = '{"ok":true,"on":true,"brightness":128,"playing":"all","animation":1,"fps":50,"error":null,"readiness":"checking","checked":0,"to_check":2,"unavailable":0,"checking":"hello.odrg","host":null}'
        ready = checking.replace('"checking","checked":0,"to_check":2', '"ready","checked":2,"to_check":0').replace('"checking":"hello.odrg"', '"checking":null')
        listed = '{"ok":true,"items":[{"id":1,"file":"hello.odrg","bytes":null,"ignored":false}],"next":null}'
        talks = support.Talking({"status": [checking, checking, checking, ready], "list": [listed]})
        self.assertEqual(self.settled(talks), ready)

    def test_the_list_is_asked_for_every_half_second_until_it_is_given_and_then_the_status(self):
        talks = support.Talking({"status": [support.VALID], "list": [support.BUSY, support.BUSY, support.BUSY, support.LISTED]})
        self.assertEqual(self.settled(talks), support.VALID)
        self.assertEqual(talks.sent, ["status", "list", "list", "list", "list", "status"])
        self.assertEqual(talks.slept, [0.5, 0.5, 0.5])

    def test_a_board_that_has_nothing_to_read_is_asked_once(self):
        talks = support.Talking({"status": [support.VALID], "list": [support.LISTED]})
        self.assertEqual(self.settled(talks), support.VALID)
        self.assertEqual(talks.sent, ["status", "list", "status"])
        self.assertEqual(talks.slept, [])

    def test_the_status_it_gives_is_the_one_from_after_the_wait(self):
        invalid = '{"ok":true,"on":true,"brightness":128,"playing":null,"animation":null,"fps":50,"error":"file-malformed dvd.odrg truncated"}'
        talks = support.Talking({"status": [support.VALID, invalid], "list": [support.BUSY, support.BUSY, '{"ok":false,"error":"show-invalid"}']})
        self.assertEqual(self.settled(talks), invalid)
        self.assertEqual(talks.sent, ["status", "list", "list", "list", "status"])

    def test_a_show_that_is_invalid_from_the_start_is_not_waited_for(self):
        invalid = '{"ok":true,"on":true,"brightness":0,"playing":null,"animation":null,"fps":50,"error":"mapping-missing"}'
        talks = support.Talking({"status": [invalid], "list": ['{"ok":false,"error":"show-invalid"}']})
        self.assertEqual(self.settled(talks), invalid)
        self.assertEqual(talks.slept, [])

    def test_a_board_that_is_still_busy_when_the_time_is_over_is_check_not_done(self):
        talks = support.Talking({"status": [support.VALID], "list": [support.BUSY]})
        with self.assertRaises(board.Failure) as caught:
            self.settled(talks, wait=5)
        self.assertEqual(caught.exception.reason, "check-not-done")
        self.assertIn("5 seconds", caught.exception.detail)
        self.assertIn("--wait", caught.exception.detail)
        # The time is one for all of it: about five seconds of asking, at half a second
        # and the time of an exchange each.
        self.assertEqual(talks.sent[0], "status")
        self.assertEqual(set(talks.sent[1:]), {"list"})
        self.assertTrue(8 <= len(talks.sent) - 1 <= 10, talks.sent)
        self.assertLess(talks.now - 1000.0, 6.0)

    def test_a_board_that_does_not_answer_at_first_is_waited_for_within_the_same_time(self):
        talks = support.Talking({"status": [None, None, support.VALID], "list": [support.BUSY, support.LISTED]})
        self.assertEqual(self.settled(talks), support.VALID)
        self.assertEqual(talks.sent, ["status", "status", "status", "list", "list", "status"])

    def test_a_board_that_never_answers_is_no_reply(self):
        talks = support.Talking({"status": [None]})
        with self.assertRaises(board.Failure) as caught:
            self.settled(talks, wait=3)
        self.assertEqual(caught.exception.reason, "no-reply")

    def test_only_a_refusal_with_busy_is_waited_for(self):
        for reply in (support.BUSY,):
            self.assertTrue(board.is_busy(reply))
        for reply in (support.LISTED, support.VALID, '{"ok":false,"error":"show-invalid"}', "busy", "[]", ""):
            self.assertFalse(board.is_busy(reply), reply)

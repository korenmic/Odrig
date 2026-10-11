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

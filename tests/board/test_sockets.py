import glob
import unittest

from fwtool import board

from . import PORT, support


class TheTwoSockets(unittest.TestCase):
    """The board has two USB sockets: the chip's own, and one marked COM, which reaches the
    chip's UART through a bridge. The firmware takes command lines on both."""

    @classmethod
    def setUpClass(cls):
        support.ensure("firmware")

    def test_the_socket_the_board_is_on_takes_commands_and_refusals(self):
        board.settled(PORT, board.SETTLE_SECONDS)
        status, reply = support.command(PORT, "status")
        self.assertEqual((status, reply["ok"], reply["error"]), (0, True, None))
        self.assertEqual(support.command(PORT, "play", "99"), (1, {"ok": False, "error": "unknown-id"}))
        self.assertEqual(support.command(PORT, "play", "7" * 2050), (1, {"ok": False, "error": "line-too-long"}))
        status, listed = support.command(PORT, "list")
        self.assertEqual((status, listed["ok"]), (0, True))

    def test_with_both_sockets_connected_each_takes_its_own_lines(self):
        ports = sorted(glob.glob(board.PORT_PATTERN))
        if len(ports) < 2:
            self.skipTest(f"one socket is connected: {', '.join(ports)}")
        for _ in range(5):
            for port in ports:
                status, reply = support.command(port, "status")
                self.assertEqual((status, reply["error"]), (0, None), port)
        brightness = support.command(ports[0], "status")[1]["brightness"]
        self.assertEqual(support.command(ports[1], "brightness", str(brightness)), (0, {"ok": True}))
        self.assertEqual(support.command(ports[0], "status")[1]["brightness"], brightness)

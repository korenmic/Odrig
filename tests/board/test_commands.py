import unittest

from odrigctl import client

from . import PORT, support

ROUNDS = 15
ROUND = ("status", "play 2", "status", "on", "off", "on", "brightness 20", "status", "play 3", "brightness 32")


class Commands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("firmware")

    def test_the_board_gives_the_replies_the_emulator_gives_for_the_same_session(self):
        with support.dim_show() as folder:
            support.ensure_installed(folder)
            support.restart()
            on_the_board = support.session(PORT)
            with support.emulator(folder) as link:
                in_the_emulator = support.session(link)
        self.assertEqual(len(on_the_board), len(support.SESSION))
        self.assertEqual(len(in_the_emulator), len(support.SESSION))
        for number, ((line, *board_answer), (_, *emulator_answer)) in enumerate(zip(on_the_board, in_the_emulator), 1):
            self.assertEqual(board_answer, emulator_answer, f"line {number} of the session, `{line}`: the board's answer is the first")

    def test_the_session_has_every_command_and_every_error_code_the_tool_can_cause(self):
        with support.dim_show() as folder:
            with support.emulator(folder) as link:
                answers = support.session(link)
        self.assertEqual({line.split(" ")[0] for line, _, _ in answers}, {"play", "on", "off", "brightness", "status"})
        errors = {reply["error"] for _, status, reply in answers if status == 1}
        self.assertEqual(errors, {"unknown-id", "bad-argument", "line-too-long"})
        first = answers[0][2]
        self.assertEqual((first["on"], first["brightness"], first["playing"], first["animation"], first["error"]), (True, support.DIM, 3, 1, None))
        # An animation is played in the playlist, `play all` goes back to its first
        # animation, and the cycle is played by itself.
        self.assertIn("play all", support.SESSION)
        playing = [(reply["playing"], reply["animation"]) for line, _, reply in answers if line == "status"]
        self.assertEqual(playing, [(3, 1), (3, 1), ("all", 2), ("all", 2), ("all", 2), ("all", 1), ("all", 2), ("all", 1), ("all", 1), ("all", 1), (3, 1)])
        for line in support.SESSION:
            if line.startswith("brightness ") and int(line.split(" ")[1]) <= 255:
                self.assertLessEqual(int(line.split(" ")[1]), support.BRIGHTEST, line)

    def test_every_reply_arrives_while_the_tool_waits_for_it(self):
        missing = []
        for number in range(ROUNDS):
            for line in ROUND:
                try:
                    reply = client.serial_exchange(PORT, line.encode() + b"\n", 1.0)
                except client.Unreachable as unreachable:
                    missing.append(f"round {number + 1}, {line}: {unreachable}")
                    continue
                self.assertEqual(b'"fps"' in reply, line == "status", f"{line} was answered with {reply}")
        self.assertEqual(missing, [])

import time
import unittest

from . import PORT, support

SECONDS = 37
TURN_SECONDS = 15


def status():
    return support.command(PORT, "status")[1]


class Autostart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("firmware")
        with support.dim_show() as folder:
            support.ensure_installed(folder)

    def test_the_show_plays_from_the_start_and_its_two_animations_take_turns_every_15_seconds(self):
        support.restart()
        first = status()
        self.assertEqual((first["on"], first["brightness"], first["playing"], first["animation"], first["error"]), (True, support.DIM, 3, 1, None))
        began = time.monotonic()
        seen = []
        for second in range(SECONDS):
            time.sleep(max(0.0, began + second + 1 - time.monotonic()))
            reply = status()
            seen.append((time.monotonic() - began, reply["animation"], reply["fps"], reply["playing"]))
        animations = [animation for _, animation, _, _ in seen]
        to_second = next(index for index, animation in enumerate(animations) if animation == 2)
        back_to_first = next(index for index in range(to_second, len(animations)) if animations[index] == 1)
        self.assertEqual(animations[:to_second], [1] * to_second, animations)
        self.assertEqual(animations[to_second:back_to_first], [2] * (back_to_first - to_second), animations)
        turn = seen[back_to_first][0] - seen[to_second][0]
        self.assertAlmostEqual(turn, TURN_SECONDS, delta=1.5, msg=animations)
        self.assertLessEqual(seen[to_second][0], TURN_SECONDS + 1.5, animations)
        self.assertEqual({playing for _, _, _, playing in seen}, {3})
        self.assertGreaterEqual(min(fps for _, _, fps, _ in seen[1:]), 49, seen)

import time
import unittest

from . import PORT, support

# The first animation has a loop of one second and four loops of its own. The second has a
# loop of three seconds and no number, so it has the fewest loops that last the 5 seconds
# of the show: two.
TURN_SECONDS = {1: 4.0, 2: 6.0}
SECONDS = 26
STEP_SECONDS = 0.25
# A turn is seen through `status`, asked four times a second.
SEEN_WITHIN = 0.6


def status():
    return support.command(PORT, "status")[1]


class Playlist(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("firmware")

    def test_a_show_of_two_animations_without_start_plays_its_playlist_from_power_on(self):
        animations = [("short.odrg", support.one_frame(support.TWO_LEGS, 1000)), ("long.odrg", support.one_frame(support.TWO_LEGS, 3000))]
        with support.show_folder(support.TWO_LEGS, animations, start=None, turns=({"repeat": 4},), min_seconds=5) as folder:
            self.assertEqual(support.reason_in_the_emulator(folder), None)
            support.ensure_installed(folder)
            support.restart()
            first = status()
            self.assertEqual((first["on"], first["brightness"], first["playing"], first["animation"], first["error"]), (True, support.DIM, "all", 1, None))
            began = time.monotonic()
            seen = []
            while time.monotonic() - began < SECONDS:
                reply = status()
                seen.append((time.monotonic() - began, reply["playing"], reply["animation"], reply["error"]))
                time.sleep(STEP_SECONDS)
        self.assertEqual({(playing, error) for _, playing, _, error in seen}, {("all", None)})
        # Each stretch of one animation: which one, and when it was first seen.
        turns = []
        for moment, _, animation, _ in seen:
            if not turns or turns[-1][0] != animation:
                turns.append((animation, moment))
        self.assertEqual([animation for animation, _ in turns[:5]], [1, 2, 1, 2, 1], turns)
        self.assertLessEqual(turns[1][1], TURN_SECONDS[1] + SEEN_WITHIN, turns)
        for (animation, began_at), (_, ended_at) in zip(turns[1:], turns[2:]):
            self.assertAlmostEqual(ended_at - began_at, TURN_SECONDS[animation], delta=SEEN_WITHIN, msg=turns)


if __name__ == "__main__":
    unittest.main()

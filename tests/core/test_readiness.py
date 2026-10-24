import json
import unittest

from . import support
from .test_body_faults import cut_clip
from .test_playback import T0

WIDTH, HEIGHT = 3, 2


def good(seed, frames=5):
    return support.clip(seed, WIDTH, HEIGHT, (20,) * frames)


def show_of(items, files):
    return {"mapping.json": support.one_leg_mapping(WIDTH, HEIGHT), "show.json": support.show_text(items), **files}


def states(run):
    return [json.loads(line[len("reply "):]) for line in run.lines if line.startswith("reply ") and '"on"' in line]


class ASilentStatus(unittest.TestCase):
    """What `status` said of the check before it reported its readiness."""

    def files(self):
        return show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "b.odrg"}, {"id": 3, "file": "c.odrg"}],
                       {"a.odrg": good(1, 40), "b.odrg": cut_clip(10, 3), "c.odrg": good(3)})

    @unittest.expectedFailure
    def test_status_says_the_check_goes_on_and_then_that_an_animation_is_unavailable(self):
        script = [support.line(T0, "status")] + [f"poll {T0 + 20 * step}" for step in range(40)] + [support.line(T0 + 800, "status")]
        during, after = states(support.start(self.files(), script, check_first=False))
        self.assertEqual((during["readiness"], during["checked"], during["to_check"], during["checking"]), ("checking", 0, 3, "a.odrg"))
        self.assertEqual((after["readiness"], after["checked"], after["to_check"], after["unavailable"]), ("degraded", 3, 0, 1))

    @unittest.expectedFailure
    def test_an_invalid_show_is_in_recovery(self):
        state, = states(support.start(support.with_show_fault(self.files()), [support.line(T0, "status")]))
        self.assertEqual(state["readiness"], "recovery")


if __name__ == "__main__":
    unittest.main()

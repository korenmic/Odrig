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

    def test_status_says_the_check_goes_on_and_then_that_an_animation_is_unavailable(self):
        script = [support.line(T0, "status")] + [f"poll {T0 + 20 * step}" for step in range(40)] + [support.line(T0 + 800, "status")]
        during, after = states(support.start(self.files(), script, check_first=False))
        self.assertEqual((during["readiness"], during["checked"], during["to_check"], during["checking"]), ("checking", 0, 3, "a.odrg"))
        self.assertEqual((after["readiness"], after["checked"], after["to_check"], after["unavailable"]), ("degraded", 3, 0, 1))

    def test_an_invalid_show_is_in_recovery(self):
        state, = states(support.start(support.with_show_fault(self.files()), [support.line(T0, "status")]))
        self.assertEqual(state["readiness"], "recovery")



def replies(run):
    return [json.loads(line[len("reply "):]) for line in run.lines if line.startswith("reply ")]


class ReadinessAsTheReference(unittest.TestCase):
    def compare(self, files, script, options=(), check_first=False, changeable=True):
        run = support.start(files, script, options, check_first=check_first)
        expected = support.ReferencePlayer(files, changeable=changeable, check_first=check_first).run(script)
        self.assertEqual(run.lines, expected)
        return states(run)

    def files(self):
        return ASilentStatus().files()

    def test_through_the_check_with_a_quarantine(self):
        script = []
        for step in range(20):
            script += [f"poll {T0 + 20 * step}", support.line(T0 + 20 * step, "status")]
        seen = [(state["readiness"], state["checked"], state["to_check"], state["unavailable"], state["checking"]) for state in self.compare(self.files(), script)]
        self.assertEqual(seen[0], ("checking", 0, 3, 0, "a.odrg"))
        self.assertIn(("checking", 1, 2, 0, "b.odrg"), seen)
        self.assertEqual(seen[-1], ("degraded", 3, 0, 1, None))

    def test_a_show_that_is_ready_and_one_of_a_host_without_storage(self):
        files = show_of([{"id": 1, "file": "a.odrg"}, {"id": 2, "file": "a.odrg"}], {"a.odrg": good(1)})
        state, = self.compare(files, [support.line(T0, "status")], check_first=True)
        self.assertEqual((state["readiness"], state["checked"], state["to_check"]), ("ready", 1, 0))
        state, = self.compare(self.files(), [support.line(T0, "status")], ["--no-storage"], check_first=False, changeable=False)
        self.assertEqual((state["readiness"], state["checked"], state["unavailable"]), ("degraded", 3, 1))

    def test_an_upload_during_the_check_holds_it_at_its_file(self):
        data = good(9)
        script = [f"poll {T0 + 20 * step}" for step in range(3)] + [support.line(T0 + 60, line) for line in support.upload_lines(9, "new.odrg", data)]
        script += [support.line(T0 + 60, "status")] + [f"poll {T0 + 80 + 20 * step}" for step in range(10)] + [support.line(T0 + 280, "status")]
        during, later = self.compare(self.files(), script)
        self.assertEqual((during["readiness"], during["checking"]), ("checking", "a.odrg"))
        self.assertEqual((later["readiness"], later["checking"]), ("checking", "a.odrg"))

    def test_an_invalid_show(self):
        state, = self.compare(support.with_show_fault(self.files()), [support.line(T0, "status")])
        self.assertEqual((state["readiness"], state["checked"], state["to_check"], state["unavailable"], state["checking"]), ("recovery", 0, 0, 0, None))


class TheLastFault(unittest.TestCase):
    def test_none_before_a_fault_and_the_context_after_one(self):
        files = ASilentStatus().files()
        script = [support.line(T0, "fault")] + [f"poll {T0 + 20 * step}" for step in range(40)] + [support.line(T0 + 800, "fault"), support.line(T0 + 800, "fault 1")]
        before, after, wrong = replies(support.start(files, script, check_first=False))
        self.assertEqual(before, {"ok": True, "fault": None})
        self.assertEqual(after, {"ok": True, "fault": {"work": "start", "file": "b.odrg", "record": 3, "bytes": len(files["b.odrg"]) - 16, "reason": "truncated"}})
        self.assertEqual(wrong, {"ok": False, "error": "bad-argument"})

    def test_it_is_answered_on_an_invalid_show(self):
        reply, = replies(support.start(support.with_show_fault(ASilentStatus().files()), [support.line(T0, "fault")]))
        self.assertEqual(reply, {"ok": True, "fault": None})

    def test_a_drives_file_is_named_while_it_is_checked_and_in_the_fault(self):
        from .test_drive import a_drive
        files = show_of([{"id": 1, "file": "a.odrg"}], {"a.odrg": good(1)})
        # The installed file takes 7 steps and the refreshes 0, 1, 2, 3 and 4 in a row: the
        # check is in the drive's file at the fifth refresh.
        script = [f"poll {T0 + 20 * step}" for step in range(5)] + [support.line(T0 + 80, "status")]
        script += [f"poll {T0 + 100 + 20 * step}" for step in range(10)] + [support.line(T0 + 300, "status"), support.line(T0 + 300, "fault")]
        with a_drive({"z\"z.odrg": cut_clip(10, 3)}) as top:
            run = support.start(files, script, ["--drive", top], check_first=False)
        during, after, fault = replies(run)
        self.assertEqual((during["readiness"], during["checking"]), ("checking", 'z"z.odrg'))
        self.assertEqual((after["readiness"], after["checked"], after["unavailable"]), ("degraded", 2, 1))
        self.assertEqual((fault["fault"]["work"], fault["fault"]["file"]), ("drive", 'z"z.odrg'))


if __name__ == "__main__":
    unittest.main()

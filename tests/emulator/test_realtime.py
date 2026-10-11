import signal
import time
import unittest

from emulator import engine, hub

from . import support


def fps_samples(emulator, seconds, every=0.2):
    """What `status` reports as `fps`, asked again and again for a length of time."""
    samples = []
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        samples.append(emulator.status()["fps"])
        time.sleep(every)
    return samples


def wait_for_the_second_full_second(emulator):
    """Waits until `status` reports on a full second after the first one."""
    until = time.monotonic() + 10
    while emulator.status()["fps"] == 0:
        if time.monotonic() > until:
            raise AssertionError("status reported 0 refreshes a second for 10 seconds")
        time.sleep(0.05)
    time.sleep(1.05)


class SpeedOfThisMac(unittest.TestCase):
    """These tests measure real time: they depend on the speed and the load of this Mac."""

    def test_the_example_show_holds_49_refreshes_or_more_for_five_full_seconds(self):
        with support.example_show() as folder, support.Emulator(folder) as emulator:
            wait_for_the_second_full_second(emulator)
            samples = fps_samples(emulator, 5.4)
            self.assertGreaterEqual(len(samples), 20)
            self.assertGreaterEqual(min(samples), 49, f"on this Mac the example show fell below 49 refreshes a second: {samples}")
            self.assertLessEqual(max(samples), 50, samples)

    def test_after_a_stop_of_300_ms_no_missed_refresh_is_made_up_for(self):
        with support.example_show() as folder, support.Emulator(folder) as emulator:
            wait_for_the_second_full_second(emulator)
            emulator.send_signal(signal.SIGSTOP)
            time.sleep(0.3)
            emulator.send_signal(signal.SIGCONT)
            samples = fps_samples(emulator, 4.4, every=0.1)
            self.assertLess(min(samples), 50, f"a stop of 300 ms left no second short of refreshes: {samples}")
            self.assertGreaterEqual(min(samples), 30, samples)
            self.assertLessEqual(max(samples), 50, f"refreshes were made up for after the stop: {samples}")
            self.assertGreaterEqual(min(samples[-10:]), 49, samples)


class Core:
    """Stands in for the core: writes down the timestamp of every request for a refresh."""

    def __init__(self):
        self.polled = []
        self.commands = []

    def poll(self, now):
        self.polled.append(now)
        return True

    def frame(self):
        return b""

    def command(self, now, line):
        self.commands.append((now, line))
        return b'{"ok":true}\n'


class Clock:
    """A clock that only a wait moves, and that a test can make wake late."""

    def __init__(self, start_ns=123_456_789):
        self.ns = start_ns
        self.late_ns = []

    def __call__(self):
        return self.ns

    def wait(self, target_ns):
        self.ns = max(self.ns, target_ns) + (self.late_ns.pop(0) if self.late_ns else 0)


class Sleeper:
    """A clock with a sleep that wakes late by a share of the time asked for, as the
    system's does."""

    def __init__(self, late_share):
        self.ns = 5_000_000_000
        self.late_share = late_share
        self.sleeps = []

    def clock(self):
        return self.ns

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.ns += round(seconds * 1_000_000_000 * (1 + self.late_share)) + 20_000


class Loop(unittest.TestCase):
    def loop(self, start_ns=123_456_789, before_first_tick_ns=3_400_000):
        clock = Clock(start_ns)
        core = Core()
        running = engine.Engine(core, hub.Hub(), clock=clock)
        clock.ns += before_first_tick_ns
        running.tick()
        return clock, core, running, engine.RealTime(running, wait=clock.wait)

    def test_the_first_request_sets_the_power_on_moment(self):
        _, core, running, _ = self.loop()
        self.assertEqual(core.polled, [3])
        self.assertEqual(running.t0, 3)

    def test_it_asks_at_every_grid_time_20_ms_apart(self):
        _, core, _, loop = self.loop()
        for _ in range(250):
            loop.step()
        self.assertEqual(core.polled, [3 + 20 * index for index in range(251)])

    def test_a_request_is_made_just_after_its_grid_time_never_before(self):
        clock, _, running, loop = self.loop()
        for index in range(1, 50):
            loop.step()
            after_grid_ns = clock.ns - running.start_ns - (3 + 20 * index) * 1_000_000
            self.assertEqual(after_grid_ns, 200_000)

    def test_a_late_request_carries_the_current_time_and_the_missed_grid_times_are_not_asked_for(self):
        clock, core, _, loop = self.loop()
        loop.step()
        loop.step()
        clock.late_ns.append(300_000_000)
        loop.step()
        loop.step()
        loop.step()
        self.assertEqual(core.polled, [3, 23, 43, 363, 383, 403])

    def test_a_request_that_is_a_little_late_does_not_move_the_grid(self):
        clock, core, _, loop = self.loop()
        clock.late_ns.extend([7_000_000, 19_000_000, 0, 12_500_000])
        for _ in range(6):
            loop.step()
        self.assertEqual(core.polled, [3, 30, 62, 63, 95, 103, 123])

    def test_the_status_for_the_page_is_asked_for_once_in_every_second(self):
        _, core, running, loop = self.loop()
        for _ in range(250):
            loop.step()
        self.assertEqual(core.commands, [(3 + 1000 * second, b"status") for second in range(1, 6)])
        self.assertEqual(len(running.hub.entries()), 0)
        self.assertEqual(running.hub.latest_status(), '{"ok":true}')

    def test_a_wait_of_20_ms_is_cut_up_so_that_it_ends_within_a_millisecond(self):
        for late_share in (0.0, 0.35, 0.6):
            sleeper = Sleeper(late_share)
            target = sleeper.ns + 20_000_000
            engine.wait_until(target, sleeper.clock, sleeper.sleep)
            self.assertGreaterEqual(sleeper.ns, target)
            self.assertLess(sleeper.ns - target, 1_000_000, f"a wait woke {sleeper.ns - target} ns late with sleeps {late_share:.0%} late")
            self.assertLessEqual(max(sleeper.sleeps), 0.009)
            self.assertLess(len(sleeper.sleeps), 40)
        one_sleep = Sleeper(0.35)
        one_sleep.sleep(0.020)
        self.assertGreater(one_sleep.ns - 5_020_000_000, 6_000_000)

    def test_a_wait_for_a_moment_that_has_passed_does_not_sleep(self):
        sleeper = Sleeper(0.0)
        engine.wait_until(sleeper.ns - 1, sleeper.clock, sleeper.sleep)
        engine.wait_until(sleeper.ns, sleeper.clock, sleeper.sleep)
        self.assertEqual(sleeper.sleeps, [])

    def test_timestamps_are_whole_milliseconds_from_the_start_of_the_engine(self):
        clock, core, running, _ = self.loop(start_ns=987_654_321_000, before_first_tick_ns=0)
        self.assertEqual(core.polled, [0])
        clock.ns += 1_999_999
        self.assertEqual(running.now_ms(), 1)
        clock.ns += 1
        self.assertEqual(running.now_ms(), 2)


if __name__ == "__main__":
    unittest.main()

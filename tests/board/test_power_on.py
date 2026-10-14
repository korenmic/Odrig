import contextlib
import json
import time
import unittest

from fwtool import board, flasher, paths

from . import PORT, support
from .test_measure import full_storage

RESULT = paths.OUT / "power-on.json"
# How long an install and the reading after a restart may take with 9 MB of dense clips.
READ_SECONDS = 900
# What the owner accepts on the target for any content.
LOWEST = 20


@contextlib.contextmanager
def small_first_then_full_storage():
    """A small animation, then the 9 MB of dense 60 x 60 clips: the show plays the small
    one first while the board reads the rest."""
    with full_storage() as full, support.demo_show() as demo:
        animations = [("small.odrg", support.files_of(demo)["hello.odrg"])]
        animations += sorted((name, content) for name, content in support.files_of(full).items() if name.endswith(".odrg"))
    with support.show_folder(support.TARGET, animations) as folder:
        yield folder


def restarted():
    """Restarts the board. Gives the time from the restart to the first reply to `status`,
    and that reply."""
    flasher.Flasher(PORT).restart()
    began = time.monotonic()
    reply = json.loads(board.status(PORT, support.START_SECONDS))
    return time.monotonic() - began, reply


def read_through():
    """Asks for `status` and for `list` every half second until `list` is no longer
    refused with `busy`. Gives the seconds that took and every count of refreshes that a
    whole second after power-on gave meanwhile."""
    began = time.monotonic()
    rates = []
    while True:
        status = support.command(PORT, "status")[1]
        if status["fps"] != 0:
            rates.append(status["fps"])
        code, listed = support.command(PORT, "list")
        if listed.get("error") != "busy":
            return time.monotonic() - began, rates, listed
        if time.monotonic() - began > READ_SECONDS:
            raise AssertionError(f"`list` was still busy after {READ_SECONDS} seconds")
        time.sleep(0.5)


class AtOnce(unittest.TestCase):
    """After a restart the firmware plays at once and reads the installed animations while
    it plays."""

    found = {}

    @classmethod
    def setUpClass(cls):
        support.ensure("firmware")

    @classmethod
    def tearDownClass(cls):
        RESULT.parent.mkdir(parents=True, exist_ok=True)
        RESULT.write_text(json.dumps(cls.found, indent=2) + "\n", encoding="utf-8")

    def measured(self, name, show):
        with show as folder:
            support.ensure_installed(folder, "--wait", READ_SECONDS)
        first, reply = restarted()
        seconds, rates, listed = read_through()
        self.found[name] = {"first_status_seconds": round(first, 2), "check_seconds": round(seconds, 1), "rates": rates, "listed": len(listed["items"])}
        return first, reply, seconds, rates, listed

    def test_with_9_mb_of_dense_clips_the_first_status_comes_as_soon_as_with_the_demo_show(self):
        demo_first, demo_reply, _, _, _ = self.measured("demo show", support.demo_show())
        full_first, full_reply, seconds, rates, listed = self.measured("9 MB behind a small animation", small_first_then_full_storage())
        for reply in (demo_reply, full_reply):
            self.assertEqual((reply["playing"], reply["animation"], reply["error"]), ("all", 1, None))
        self.assertLess(abs(full_first - demo_first), 1.0, f"{full_first:.2f} s with 9 MB, {demo_first:.2f} s with the demo show")
        self.assertEqual(len(listed["items"]), 8)
        self.assertGreaterEqual(min(rates), LOWEST, rates)

    def test_while_a_dense_clip_plays_the_check_ends_and_the_rate_stays_in_the_range(self):
        clip = support.dense_clip(compressed=True)
        show = support.show_folder(support.TARGET, [("dense.odrg", clip), ("again.odrg", clip)])
        _, reply, seconds, rates, listed = self.measured("dense 60 x 60 clip, compressed", show)
        self.assertEqual((reply["playing"], reply["error"]), ("all", None))
        self.assertEqual(len(listed["items"]), 2)
        self.assertGreaterEqual(min(rates), LOWEST, rates)

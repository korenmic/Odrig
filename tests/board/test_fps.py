import json
import os
import time
import unittest

from odrigctl import client

from . import PORT, support

SECONDS = 10
LOWEST = 49
# What the owner accepts on the target for any content: from 20 to 50 refreshes a second.
# A second can count one refresh more than was due in it.
ACCEPTED = (20, 51)


def status():
    return support.command(PORT, "status")[1]


def asked_often(times, interval):
    """The replies to `status`, asked again and again through one opening of the port."""
    descriptor = client._open(PORT)
    replies = []
    try:
        time.sleep(client.SETTLE_SECONDS)
        for _ in client._received(descriptor, client.DISCARD_SECONDS):
            pass
        for _ in range(times):
            asked = time.monotonic()
            client._write(descriptor, b"status\n", 1.0)
            waiting = b""
            for piece in client._received(descriptor, 1.0):
                waiting += piece
                if b"\n" in waiting:
                    break
            replies.append(json.loads(waiting))
            time.sleep(max(0.0, asked + interval - time.monotonic()))
    finally:
        os.close(descriptor)
    return replies


class Fps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("firmware")

    def refreshes_in_each_second(self):
        time.sleep(2.5)
        replies = support.each_second(SECONDS, status)
        self.assertEqual({reply["error"] for reply in replies}, {None})
        return [reply["fps"] for reply in replies]

    def test_the_dim_example_show_is_refreshed_49_times_or_more_in_every_second(self):
        with support.dim_show() as folder:
            support.ensure_installed(folder)
        fps = self.refreshes_in_each_second()
        self.assertGreaterEqual(min(fps), LOWEST, fps)

    def accepted_on_the_target(self, folder):
        support.ensure_installed(folder)
        fps = self.refreshes_in_each_second()
        self.assertGreaterEqual(min(fps), ACCEPTED[0], fps)
        self.assertLessEqual(max(fps), ACCEPTED[1], fps)

    def test_the_demo_show_on_the_target_is_refreshed_20_to_50_times_in_every_second(self):
        with support.demo_show() as folder:
            self.accepted_on_the_target(folder)

    def test_the_target_with_the_dense_60_x_60_clip_compressed(self):
        with support.show_folder(support.TARGET, [("dense.odrg", support.dense_clip(compressed=True))]) as folder:
            self.accepted_on_the_target(folder)

    def test_the_target_with_the_dense_60_x_60_clip_uncompressed(self):
        with support.show_folder(support.TARGET, [("dense.odrg", support.dense_clip(compressed=False))]) as folder:
            self.accepted_on_the_target(folder)

    def test_the_rate_holds_while_status_is_asked_five_times_a_second(self):
        with support.dim_show() as folder:
            support.ensure_installed(folder)
        time.sleep(2.5)
        replies = asked_often(5 * SECONDS, 0.2)
        self.assertEqual(len(replies), 5 * SECONDS)
        fps = [reply["fps"] for reply in replies]
        self.assertGreaterEqual(min(fps), LOWEST, fps)

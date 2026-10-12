import json
import time
import unittest

from fwtool import board, paths

from . import PORT, support

SECONDS = 10
RESULT = paths.OUT / "measurements.json"
VALUES = ("outputs", "start_ms", "loops", "sent", "fps", "gap_ms", "poll_us", "poll_mean_us", "send_us", "send_mean_us", "heap", "install_seconds", "bytes", "space_us", "free")
# The longest the core may take to start on a full storage before the tool gives up.
LONG_START_SECONDS = 240


def dense_on_the_target(compressed):
    return support.show_folder(support.TARGET, [("dense.odrg", support.dense_clip(compressed=compressed))])


def full_storage():
    """A show of dense 60 x 60 clips that fills storage with 9 MB: six clips of 10 seconds
    and one shorter one, each a file of its own."""
    clip = support.dense_clip(compressed=True)
    last = support.dense_clip(compressed=True, seconds=5)
    animations = [(f"dense-{number:02d}.odrg", clip) for number in range(1, 7)] + [("dense-07.odrg", last)]
    return support.show_folder(support.TARGET, animations)


SHOWS = (
    ("example show, two legs", support.dim_show),
    ("demo show, the target", support.demo_show),
    ("dense 60 x 60 clip, compressed, the target", lambda: dense_on_the_target(True)),
    ("dense 60 x 60 clip, uncompressed, the target", lambda: dense_on_the_target(False)),
    ("9 MB of dense 60 x 60 clips, the target", full_storage),
)


def measured(name, folder):
    """Installs a show on the probe build and measures it for some seconds."""
    size = sum(len(content) for content in support.files_of(folder).values())
    began = time.monotonic()
    done = support.install(folder, "--wait", LONG_START_SECONDS)
    install_seconds = round(time.monotonic() - began, 1)
    if done.status != 0:
        raise AssertionError(f"{name} was not installed: {done.out}{done.err}")
    time.sleep(3.0)
    support.probe()
    reports = support.each_second(SECONDS)
    sent = sum(report["sent"] for report in reports)
    # At its start the firmware asks the file system for its space once, and the file
    # system walks its blocks for the answer; the report has the time that took.
    with support.Port() as port:
        space = port.ask(b"space\n")
        space_us = port.ask(b"#probe\n", board.is_probe)["space_us"]
    return {
        "show": name,
        "outputs": [sum(1 for output in reports[-1]["outputs"] if output["ok"]), len(reports[-1]["outputs"])],
        "bytes": size,
        "install_seconds": install_seconds,
        "start_ms": reports[-1]["start_ms"],
        "loops": [min(report["loops"] for report in reports), max(report["loops"] for report in reports)],
        "sent": [min(report["sent"] for report in reports), max(report["sent"] for report in reports)],
        "fps": support.command(PORT, "status")[1]["fps"],
        "gap_ms": max(report["gap_ms"] for report in reports),
        "poll_us": max(report["poll_us"] for report in reports),
        "poll_mean_us": round(sum(report["poll_total_us"] for report in reports) / sent) if sent else None,
        "send_us": max(report["send_us"] for report in reports),
        "send_mean_us": round(sum(report["send_total_us"] for report in reports) / sent) if sent else None,
        "limited": max(report["limited"] for report in reports),
        "heap": reports[-1]["heap"],
        "space_us": space_us,
        "free": space["free"],
    }


class Measure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("probe")
        cls.addClassCleanup(cls.put_the_small_show_back)

    @staticmethod
    def put_the_small_show_back():
        """A full storage makes every start take most of a minute, so it does not stay."""
        with support.dim_show() as folder:
            support.ensure_installed(folder)

    def test_the_measurements_are_taken_and_written(self):
        rows = []
        for name, make in SHOWS:
            with make() as folder:
                rows.append(measured(name, folder))
            print(json.dumps(rows[-1]), flush=True)
        RESULT.parent.mkdir(parents=True, exist_ok=True)
        RESULT.write_text(json.dumps(rows, indent=2) + "\n")
        for row in rows:
            for value in VALUES:
                self.assertIsNotNone(row.get(value), f"{row['show']}: {value}")

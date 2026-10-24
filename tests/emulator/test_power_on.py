import json
import pathlib
import tempfile
import unittest

from tests.core import support as core_support
from tests.core.support import ReferencePlayer

from . import support

BUSY = b'{"ok":false,"error":"busy"}\n'


def dense_show(mapping, width, height, seconds):
    """The files of a show of dense animations, one for each of these lengths in seconds.
    A second of a dense animation is 50 frames."""
    files = {"mapping.json": mapping}
    items = []
    for number, length in enumerate(seconds, start=1):
        files[f"dense{number}.odrg"] = core_support.dense_clip(width, height, length)
        items.append({"id": number, "file": f"dense{number}.odrg"})
    files["show.json"] = core_support.show_text(items, brightness=255)
    return files


class AfterAStart(unittest.TestCase):
    def started(self, files, **named):
        """An emulator on these files, as it is right after its start."""
        folder = support.installed(pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()), "show"), files)
        return support.entered(self, support.Emulator(folder, checked=False, **named))

    def test_list_is_busy_and_then_the_list_over_each_transport(self):
        # 4,000 frames and more: at 16 a refresh, the core is busy for five seconds.
        files = dense_show(core_support.example_show()["mapping.json"], 60, 6, (20, 21, 22, 23))
        emulator = self.started(files, tcp_port=0)
        ask = {"http": emulator.command, "tcp": support.entered(self, support.Lines(emulator.tcp)).ask}
        if support.HAS_SERIAL:
            ask["serial"] = support.entered(self, support.Serial(emulator.serial)).ask
        for transport, send in ask.items():
            self.assertEqual(send("list"), BUSY, transport)
        for line in ("remove 4", "upload begin 9 new.odrg 100"):
            self.assertEqual(emulator.command(line), BUSY, line)
        # The command tool prints the refusal as it prints any other, and ends with 1.
        result = support.run_tool("--http", f"127.0.0.1:{emulator.port}", "list")
        self.assertEqual((result.status, result.out, result.err), (1, BUSY.decode("ascii"), ""))
        state = emulator.status()
        self.assertEqual((state["playing"], state["animation"], state["error"]), ("all", 1, None))
        emulator.wait_for_the_check()
        expected = ReferencePlayer(files).command(0, b"list")
        self.assertEqual([item["bytes"] for item in json.loads(expected)["items"]], [len(files[f"dense{number}.odrg"]) for number in (1, 2, 3, 4)])
        for transport, send in ask.items():
            self.assertEqual(send("list"), expected, transport)
        self.assertIsNone(emulator.status()["error"])

    def test_a_show_of_dense_animations_of_60_seconds_plays_before_its_files_are_read(self):
        files = dense_show(core_support.mapping_texts()["legs-20"], 60, 60, (7, 8, 9, 10, 12, 14))
        self.assertGreater(sum(len(content) for name, content in files.items() if name.endswith(".odrg")), 8000000)
        emulator = self.started(files)
        state = emulator.status()
        # No whole second has passed since power-on: the count of refreshes is still 0.
        self.assertEqual((state["playing"], state["animation"], state["error"], state["fps"]), ("all", 1, None, 0))
        self.assertEqual(emulator.command("list"), BUSY)
        with support.EventStream(emulator.port) as stream:
            frames = support.frames(stream.read_until(lambda events: any(event.kind == "frame" for event in events)))
        self.assertTrue(any(frames[0][1]))
        emulator.wait_for_the_check()
        self.assertEqual(len(json.loads(emulator.command("list"))["items"]), 6)
        self.assertIsNone(emulator.status()["error"])

    def test_a_fault_in_a_body_makes_its_animation_unavailable_and_the_show_plays_on(self):
        files = dense_show(core_support.example_show()["mapping.json"], 60, 6, (2, 3))
        files["dense2.odrg"] = files["dense2.odrg"][:-5]
        emulator = self.started(files)
        self.assertIsNone(emulator.status()["error"])
        emulator.wait_for_the_check()
        state = emulator.status()
        self.assertEqual((state["playing"], state["error"]), ("all", None))
        items = json.loads(emulator.command("list"))["items"]
        self.assertEqual([item.get("fault") for item in items if item.get("file") == "dense2.odrg"], ["truncated"])


class RecordMode(unittest.TestCase):
    def test_the_check_keeps_the_pace_of_the_ticks(self):
        work = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        files = core_support.example_show()
        folder = support.installed(work / "show", files)
        # 255 and 232 frames: 491 steps. The check takes none at the first tick, then 1, 2
        # and so on to 16 at a tick: 136 after seventeen ticks, and 504 after forty, which
        # is the tick at 780 ms. A command is given before the tick of its time.
        commands = [(0, "list"), (0, "status"), (780, "list"), (800, "list"), (800, "remove 3"), (2000, "list")]
        script = work / "script.txt"
        script.write_text("".join(f"{time} {line}\n" for time, line in commands), encoding="utf-8")
        result = support.run(folder, "--record", work / "out.odrr", "--seconds", 3, "--script", script)
        self.assertEqual((result.status, result.err), (0, ""))
        printed = result.out.splitlines()
        _, replies = support.reference(files, range(0, 3000, 20), commands)
        self.assertEqual(printed, [f"reply {time} {reply.decode('ascii')[:-1]}" for (time, _), reply in zip(commands, replies)])
        self.assertEqual(printed[0], 'reply 0 {"ok":false,"error":"busy"}')
        self.assertEqual(printed[2], 'reply 780 {"ok":false,"error":"busy"}')
        self.assertEqual(len(json.loads(printed[3].split(" ", 2)[2])["items"]), 3)
        self.assertEqual(printed[4], 'reply 800 {"ok":true}')
        self.assertEqual(len(json.loads(printed[5].split(" ", 2)[2])["items"]), 2)

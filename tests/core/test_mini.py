import json
import unittest

from odrig import jsonframes, mapping, odrg

from . import support
from .test_clocks import clock_of
from .test_texts import text_of
from .test_pictures import picture_of


def files_for(pixels=None, palette=True):
    if pixels is None:
        pixels = [[(x * 4, y * 4, (x + y) * 2) for x in range(60)] for y in range(60)]
    picture = bytes(c for row in pixels for pixel in row for c in pixel)
    data = jsonframes.Animation(60, 60, ((1000, picture),))
    return {"mapping.json": support.mapping_texts()["legs-20"],
            "show.json": support.show_text([{"id": 1, "file": "picture.odrg"}], 255, 1),
            "picture.odrg": odrg.encode(data, compressed=palette)}


def replies(run):
    return [json.loads(line[6:]) for line in run.lines if line.startswith("reply ")]


def frame(run, name="preview"):
    return bytes.fromhex([line.split(" ", 1)[1] for line in run.lines if line.startswith(name + " ")][-1])


def projected(pixels, brightness=40):
    out = bytearray(180)
    for y in range(6):
        for x in range(6):
            for c in range(3):
                out[3 * (y * 10 + x + 2) + c] = sum(
                    (pixels[sy][sx][c] * brightness + 127) // 255
                    for sy in range(y * 10, y * 10 + 10)
                    for sx in range(x * 10, x * 10 + 10)) // 100
    return bytes(out)


ENABLE = ["mini support", support.line(0, "debug mini on"), "mini complete 1 1"]


class Miniature(unittest.TestCase):
    def test_failed_setup_stays_unknown_during_retry_until_success(self):
        run = support.start(files_for(), ["mini support", support.line(0, "debug mini on"),
                            "mini complete 1 0", support.line(1, "debug mini off"),
                            support.line(2, "status"), "mini complete 2 1", support.line(3, "status")])
        states = [r["mini"] for r in replies(run) if "mini" in r]
        self.assertIsNone(states[0]["on"])
        self.assertTrue(states[0]["pending"])
        self.assertEqual(states[0]["error"], "output-setup-failed")
        self.assertFalse(states[1]["on"])
        self.assertFalse(states[1]["pending"])
        self.assertIsNone(states[1]["error"])

    def test_host_description_escaping_is_bounded_with_miniature_status(self):
        run = support.start(files_for(), [*ENABLE, support.line(0, "status")], ["--about", "\x01" * 95])
        status = replies(run)[-1]
        self.assertEqual(status["host"], "\x01" * 42)
        self.assertTrue(status["mini"]["on"])
        self.assertTrue(run.lines[-1].endswith("}"))
        self.assertLessEqual(len(run.lines[-1][6:]) + 1, 1024)

    def test_text_and_widget_projection_matches_the_effective_logical_picture(self):
        contents = [text_of(width=60, height=60, effect="static"),
                    *(clock_of(widget, canvas=(60, 60)) for widget in (1, 2, 3)),
                    *(picture_of(widget, canvas=(60, 60)) for widget in ("picture-dial", "picture-display"))]
        for content in contents:
            files = files_for()
            files["picture.odrg"] = content
            script = [*ENABLE, support.line(0, "brightness 40"), "poll 0", "poll 1200", "mini frame"]
            run = support.start(files, script)
            canvas = mapping.loads(files["mapping.json"].encode("utf-8"))
            latest = {int(line.split()[1]): bytes.fromhex(line.split()[2])
                      for line in run.lines if line.startswith("data ")}
            pixels = [[(0, 0, 0)] * 60 for _ in range(60)]
            for leg in canvas.legs:
                data = latest[leg.leg]
                for n, at in enumerate(support.led_pixels(canvas, leg)):
                    pixels[at // 60][at % 60] = tuple(data[3 * n:3 * n + 3])
            self.assertEqual(frame(run), projected(pixels, 255))
            self.assertTrue(any(frame(run)))

    def test_control_acknowledgement_failure_retry_and_boot(self):
        script = [support.line(0, "debug mini on"), "mini support", support.line(0, "status"),
                  support.line(1, "debug mini on"), support.line(2, "status"),
                  support.line(3, "debug mini on"), support.line(4, "debug mini off"),
                  "mini complete 99 1", "mini complete 1 0", support.line(5, "status"),
                  support.line(6, "debug mini off"), "mini complete 2 1", support.line(7, "status"),
                  support.line(8, "debug mini off"), "mini frame"]
        told = replies(support.start(files_for(), script))
        self.assertEqual(told[0], {"ok": False, "error": "unsupported"})
        self.assertEqual(told[1]["mini"], dict(supported=True, on=False, requested=False, pending=False, error=None, brightness=40))
        self.assertTrue(told[3]["mini"]["pending"])
        self.assertFalse(told[3]["mini"]["on"])
        self.assertEqual(told[5], {"ok": False, "error": "busy"})
        self.assertIsNone(told[6]["mini"]["on"])
        self.assertEqual(told[6]["mini"]["error"], "output-setup-failed")
        self.assertFalse(told[8]["mini"]["pending"])
        self.assertFalse(told[8]["mini"]["on"])
        boot = replies(support.start(files_for(), ["mini support", support.line(0, "status")]))[0]
        self.assertFalse(boot["mini"]["on"])

    def test_syntax_and_unsupported_canvas(self):
        lines = ["debug", "debug mini", "debug mini ON", "debug mini on extra", "debug other on"]
        run = support.start(files_for(), ["mini support", *(support.line(0, text) for text in lines)])
        self.assertEqual(replies(run), [{"ok": False, "error": "bad-argument"}] * len(lines))
        run = support.start(support.example_show(), ["mini support", support.line(0, "debug mini on")])
        self.assertEqual(replies(run), [{"ok": False, "error": "unsupported"}])

    def test_box_averages_rgb_orientation_and_physical_chain(self):
        pixels = [[(x * 4, y * 4, (x + y) * 2) for x in range(60)] for y in range(60)]
        run = support.start(files_for(pixels), [*ENABLE, "poll 0", "mini frame"])
        preview = frame(run)
        self.assertEqual(preview, projected(pixels))
        self.assertEqual(frame(run, "chain"), bytes(preview[3 * (y * 10 + x) + c]
                         for x in range(10) for y in range(6) for c in range(3)))
        self.assertEqual(len(preview), 180)

    def test_palette_solids_and_zero_or_lower_brightness(self):
        pixels = [[(255, 127, 33)] * 60 for _ in range(60)]
        for brightness in (0, 1, 15, 39, 40, 255):
            with self.subTest(brightness=brightness):
                script = [*ENABLE, support.line(0, f"brightness {brightness}"), "poll 0", "mini frame", support.line(1, "status")]
                run = support.start(files_for(pixels), script)
                self.assertEqual(frame(run), projected(pixels, min(brightness, 40)))
                self.assertEqual(replies(run)[-1]["brightness"], brightness)
                self.assertEqual(replies(run)[-1]["mini"]["brightness"], min(brightness, 40))

    def test_power_and_blank_clear_both_buffers(self):
        for command in ("off", "brightness 0"):
            run = support.start(files_for(), [*ENABLE, "poll 0", support.line(1, command), "poll 20", "mini frame"])
            self.assertEqual(frame(run), bytes(180))
            self.assertEqual(frame(run, "chain"), bytes(180))

    def test_mapping_permutation_and_cross_wiring_do_not_change_projection(self):
        files = files_for()
        mapping = json.loads(files["mapping.json"])
        pins = [leg["pin"] for leg in mapping["legs"]][::-1]
        for leg, pin in zip(mapping["legs"], pins):
            leg["pin"] = pin
        files["mapping.json"] = json.dumps(mapping)
        first = support.start(files_for(), [*ENABLE, "poll 0", "mini frame"])
        second = support.start(files, [*ENABLE, support.line(0, "mapping cross on"), "poll 0", "mini frame"])
        self.assertEqual(replies(second)[-1], {"ok": True})
        self.assertEqual(frame(second), frame(first))

    def test_enabled_mode_never_changes_normal_legs_or_persisted_files(self):
        files = files_for()
        plain = support.start(files, ["poll 0", "poll 20"])
        run, kept = support.start_and_keep(files, [*ENABLE, "poll 0", "poll 20"])
        normal = lambda result: [line for line in result.lines if line.startswith(("refresh ", "data "))]
        self.assertTrue(normal(plain))
        self.assertEqual(normal(run), normal(plain))
        self.assertEqual(kept, {k: v.encode("utf-8") if isinstance(v, str) else v for k, v in files.items()})

    def test_optional_projection_allocation_failure_preserves_the_show(self):
        files = files_for()
        blocks = support.start(files).memory[1]
        run = support.start(files, ["mini support", support.line(0, "debug mini on"), "poll 0"],
                            ["--alloc-fails-at", str(blocks)])
        self.assertIsNone(run.error)
        self.assertEqual(replies(run), [{"ok": False, "error": "unsupported"}])
        self.assertTrue(any(line.startswith("data ") for line in run.lines))

    def test_byte_transport_and_line_commands_share_pending_state(self):
        run = support.start(files_for(), ["mini support", support.fed(0, b"debug mini on\n"),
                            support.line(1, "status"), "mini complete 1 1",
                            support.fed(2, b"status\n")])
        states = [reply["mini"] for reply in replies(run) if "mini" in reply]
        self.assertTrue(states[0]["pending"])
        self.assertTrue(states[1]["on"])
        self.assertFalse(states[1]["pending"])


if __name__ == "__main__":
    unittest.main()

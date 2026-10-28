"""The previews in the app: each row's square at every level of the explorer, from the
default preview catalog by the key the catalogs' pages give, an empty one for a key the
catalog does not know and for a faulty row, none on folder rows and in the Tests group,
the square of the panel of what plays, and the previews of a show that Settings'
rebuild catalogs. All in Chrome against the emulator."""

import json
import pathlib
import shutil
import tempfile
import unittest

from odrig import catalog
from tests.core import support as core_support
from tests.emulator import support as emulator_support

from . import support
from .test_keys import Paged
from .test_target import entered

ANIMATIONS = support.ROOT / "test-animations"
MAPPING = (support.ROOT / "mapping" / "legs-20.json").read_text(encoding="utf-8")


def mapping_of_the_defaults():
    """The keys of the default preview catalog, read from its mapping as text."""
    text = (support.THUMBNAILS / "catalog.js").read_text(encoding="ascii")
    return {line.split('"')[1] for line in text.splitlines() if line.startswith('  "')}


def key_of(data):
    import zlib
    return f"{zlib.crc32(data):08x}-{len(data)}"


class Previews(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        self.known = {name: (ANIMATIONS / name).read_bytes() for name in ("lines-test.odrg", "rainbow-lines-01.odrg", "rainbow-lines-03.odrg", "rainbow-lines-04.odrg")}
        defaults = mapping_of_the_defaults()
        self.assertTrue(all(key_of(data) in defaults for data in self.known.values()))
        self.unknown = core_support.clip(9, 60, 60, (40, 40, 40))
        self.assertNotIn(key_of(self.unknown), defaults)

    def show(self, cataloged=True, broken=True):
        items = [{"id": 1, "file": "lines-test.odrg"}, {"id": 2, "file": "rainbow-lines-01.odrg"}, {"id": 3, "file": "unknown.odrg"}]
        files = {"lines-test.odrg": self.known["lines-test.odrg"], "rainbow-lines-01.odrg": self.known["rainbow-lines-01.odrg"], "unknown.odrg": self.unknown}
        if broken:
            items.append({"id": 4, "file": "broken.odrg"})
            files["broken.odrg"] = self.known["rainbow-lines-03.odrg"][:-9]
        show = {"version": 1, "brightness": 128, "items": items}
        folder = emulator_support.installed(self.work / ("show" if cataloged else "plain"), {"mapping.json": MAPPING, "show.json": json.dumps(show), **files})
        if cataloged:
            made, refused = catalog.rebuild(catalog.Storage(folder), names=["lines-test.odrg", "rainbow-lines-01.odrg", "unknown.odrg"], canvas=(60, 60))
            self.assertEqual(refused, [])
        return folder

    def card(self):
        top = self.work / "card"
        emulator_support.installed(top / "odrig", {"rainbow-lines-03.odrg": self.known["rainbow-lines-03.odrg"]})
        (top / "odrig" / "night").mkdir()
        (top / "odrig" / "night" / "rainbow-lines-04.odrg").write_bytes(self.known["rainbow-lines-04.odrg"])
        made, refused = catalog.rebuild(catalog.Storage(top / "odrig"), canvas=(60, 60))
        self.assertEqual(refused, [])
        return top

    def source(self, name):
        return f"thumbnails/{key_of(self.known[name])}.gif"

    def test_the_rows_at_every_level_and_the_panel_show_their_previews(self):
        emulator = entered(self, emulator_support.Emulator(self.show(), "--drive", self.card()))
        with emulator_support.EventStream(emulator.port) as stream:
            seen = support.run("previews", address=f"127.0.0.1:{emulator.port}", settings={"rows": 5, "previews": 3, "enter": ["night"], "tap": 2}).seen
            logged = emulator_support.of_kind(stream.read_until(lambda events: any(json.loads(event.data).get("line") == "play 2" for event in events if event.kind == "log"), 5), "log")
        rows = {row["file"]: row for row in seen["root"]}
        self.assertEqual(rows["lines-test.odrg"]["src"], self.source("lines-test.odrg"))
        self.assertEqual(rows["rainbow-lines-01.odrg"]["src"], self.source("rainbow-lines-01.odrg"))
        self.assertEqual(rows["rainbow-lines-03.odrg"]["src"], self.source("rainbow-lines-03.odrg"))
        self.assertIsNone(rows["unknown.odrg"]["src"])
        self.assertEqual(rows["broken.odrg"]["fault"] != "", True)
        self.assertIsNone(rows["broken.odrg"]["src"])
        for row in seen["root"] + seen["night"]:
            self.assertTrue(row["first"], row["file"])
            self.assertEqual(row["size"], [44, 44], row["file"])
            if row["src"] is not None:
                self.assertEqual((row["alt"], row["draggable"], row["loaded"], row["natural"], row["rendering"]), ("", False, True, [60, 60], "pixelated"), row["file"])
        self.assertEqual([row["src"] for row in seen["night"]], [self.source("rainbow-lines-04.odrg")])
        self.assertEqual(seen["folders"], ["night"])
        self.assertEqual((seen["folderSquares"], seen["testSquares"]), (0, 0))
        self.assertTrue(seen["now"]["shown"])
        self.assertEqual(seen["now"]["src"], self.source("lines-test.odrg"))
        self.assertEqual(seen["tapped"]["src"], self.source("rainbow-lines-01.odrg"))
        self.assertIn("play 2", [entry["line"] for entry in logged])

    def test_a_show_without_a_catalog_shows_by_name_and_size_before_settings_rebuilds_its_catalog_and_after(self):
        emulator = entered(self, emulator_support.Emulator(self.show(cataloged=False, broken=False)))
        seen = support.run("previews", address=f"127.0.0.1:{emulator.port}", settings={"rebuild": True, "rows": 3, "previews": 2}).seen
        wanted = [self.source("lines-test.odrg"), self.source("rainbow-lines-01.odrg"), None]
        self.assertEqual([row["src"] for row in seen["before"]], wanted)
        self.assertEqual([row["src"] for row in seen["after"]], wanted)


BLACK = "rgb(0, 0, 0)"


def square_of(snapshot, name):
    return next(row for row in snapshot["squares"] if row["file"] == name)


class ByNameAndSize(unittest.TestCase):
    def test_rows_show_the_default_catalogs_previews_by_name_and_size_while_every_page_is_busy(self):
        known = {name: (ANIMATIONS / name).read_bytes() for name in ("lines-test.odrg", "rainbow-lines-01.odrg", "rainbow-lines-03.odrg")}
        internal = [("lines-test.odrg", len(known["lines-test.odrg"]), "0badf00d"), ("rainbow-lines-01.odrg", len(known["rainbow-lines-01.odrg"]) + 1, "0badf00d"),
                    ("unknown-file.odrg", 1234, "0badf00d")]
        external = [("rainbow-lines-03.odrg", len(known["rainbow-lines-03.odrg"]), "0badf00d")]
        target = Paged(internal, external)
        target.busy_always = True
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": [{"untilRows": 4, "ms": 15000}, {"sleep": 500}, {"snap": "rows"}]}).seen
            lines = [line.decode("ascii") for _, line in stand_in.lines]
        self.assertTrue(any(line.startswith("catalog page ") for line in lines))
        self.assertEqual((seen["rows"]["internal"], seen["rows"]["external"]), (None, None))
        self.assertEqual(square_of(seen["rows"], "lines-test.odrg")["src"], f"thumbnails/{key_of(known['lines-test.odrg'])}.gif")
        self.assertEqual(square_of(seen["rows"], "rainbow-lines-03.odrg")["src"], f"thumbnails/{key_of(known['rainbow-lines-03.odrg'])}.gif")
        self.assertIsNone(square_of(seen["rows"], "rainbow-lines-01.odrg")["src"], "another size finds nothing")
        self.assertIsNone(square_of(seen["rows"], "unknown-file.odrg")["src"])
        self.assertEqual(square_of(seen["rows"], "unknown-file.odrg")["background"], BLACK)

    def test_a_made_up_catalog_finds_one_key_of_the_rows_size_the_card_files_own_name_and_gives_way_to_the_boards_key(self):
        work = pathlib.Path(entered(self, tempfile.TemporaryDirectory()))
        folder = work / "thumbnails"
        folder.mkdir()
        gif = next(support.THUMBNAILS.glob("*.gif")).read_bytes()
        entries = {"aaaaaaa1-100": ["twin.odrg"], "aaaaaaa2-100": ["twin.odrg"], "bbbbbbb1-200": ["sized.odrg"], "ccccccc1-300": ["deep.odrg"],
                   "ddddddd1-400": ["late.odrg"], "eeeeeee1-400": ["other.odrg"]}
        lines = ["export default {"] + [f'  "{key}": {{"gif": "{key}.gif", "names": {json.dumps(names)}}},' for key, names in sorted(entries.items())] + ["};", ""]
        (folder / "catalog.js").write_text("\n".join(lines), encoding="ascii")
        for key in entries:
            (folder / f"{key}.gif").write_bytes(gif)
        internal = [("twin.odrg", 100, "12345678"), ("sized.odrg", 999, "12345678"), ("late.odrg", 400, "eeeeeee1")]
        external = [("night/deep.odrg", 300, "99999999")]
        target = Paged(internal, external)
        target.busy_always = True
        target.folders = ["night"]

        def pages():
            target.busy_always = False

        plan = [{"untilRows": 3, "ms": 15000}, {"sleep": 500}, {"snap": "before"}, {"enter": "night"}, {"untilRows": 1}, {"snap": "night"}, {"press": "Back"},
                {"step": True}, {"untilKeys": "internal", "ms": 20000}, {"sleep": 300}, {"snap": "after"}]
        with support.StandIn(target.replies()) as stand_in:
            seen = support.run("keys", address=stand_in.address, settings={"plan": plan}, steps=[pages], thumbnails=folder).seen
        self.assertIsNone(square_of(seen["before"], "twin.odrg")["src"], "two keys of the row's size")
        self.assertIsNone(square_of(seen["before"], "sized.odrg")["src"], "a key of another size")
        self.assertEqual(square_of(seen["before"], "twin.odrg")["background"], BLACK)
        self.assertEqual(square_of(seen["before"], "late.odrg")["src"], "thumbnails/ddddddd1-400.gif")
        self.assertEqual(square_of(seen["night"], "night/deep.odrg")["src"], "thumbnails/ccccccc1-300.gif")
        self.assertEqual(square_of(seen["after"], "late.odrg")["src"], "thumbnails/eeeeeee1-400.gif", "the board's key decides")
        self.assertIsNone(square_of(seen["after"], "twin.odrg")["src"])


if __name__ == "__main__":
    unittest.main()

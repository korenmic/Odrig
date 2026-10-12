import ctypes
import json
import pathlib
import re
import subprocess
import tempfile
import unittest

from emulator import binding, failure, host
from tests.core.support import ReferencePlayer

from . import support


def header_code():
    """The header without its comments."""
    return re.sub(r"/\*.*?\*/", " ", support.HEADER.read_text(encoding="utf-8"), flags=re.S)


# Prints what the C compiler makes of the two structs of the header.
LAYOUT_PROGRAM = """
#include <stdio.h>
#include "odrig_core.h"
#define MEMBER(type, name) printf(#type " " #name " %zu %zu\\n", offsetof(type, name), sizeof(((type *)0)->name))
int main(void) {
    printf("odrig_host %zu\\n", sizeof(odrig_host));
    MEMBER(odrig_host, ctx); MEMBER(odrig_host, alloc); MEMBER(odrig_host, open);
    MEMBER(odrig_host, read); MEMBER(odrig_host, close); MEMBER(odrig_host, log);
    printf("odrig_leg %zu\\n", sizeof(odrig_leg));
    MEMBER(odrig_leg, leg); MEMBER(odrig_leg, pin); MEMBER(odrig_leg, led_count); MEMBER(odrig_leg, rgb);
    return 0;
}
"""


class Declarations(unittest.TestCase):
    def test_the_library_loads(self):
        library = binding.load(support.LIBRARY)
        self.assertTrue(callable(library.odrig_core_begin))

    def test_it_declares_exactly_the_functions_of_the_header(self):
        declared = re.findall(r"\b(odrig_core_[a-z_]+)\(", header_code())
        self.assertEqual(len(declared), len(set(declared)))
        self.assertEqual(len(declared), 7)
        self.assertEqual(sorted(binding.FUNCTIONS), sorted(declared))

    def test_every_function_has_as_many_arguments_as_the_header_gives_it(self):
        code = header_code()
        for name, (_, arguments) in binding.FUNCTIONS.items():
            listed = re.search(rf"\b{name}\(([^)]*)\)", code).group(1)
            self.assertEqual(len(arguments), len(listed.split(",")), name)

    def test_its_two_limits_are_those_of_the_header(self):
        limits = dict(re.findall(r"#define (ODRIG_[A-Z_]+)\s+([0-9]+)", header_code()))
        self.assertEqual(limits, {"ODRIG_LINE_MAX": str(binding.LINE_MAX), "ODRIG_REPLY_MAX": str(binding.REPLY_MAX)})

    def test_its_structs_are_laid_out_as_the_compiler_lays_them_out(self):
        with tempfile.TemporaryDirectory() as folder:
            program = pathlib.Path(folder, "layout")
            subprocess.run(
                [support.c_compiler(), "-x", "c", "-std=c99", f"-I{support.HEADER.parent}", "-o", str(program), "-"],
                input=LAYOUT_PROGRAM, text=True, check=True, capture_output=True,
            )
            printed = subprocess.run([str(program)], capture_output=True, text=True, check=True).stdout.split("\n")
        expected = []
        for name, record in (("odrig_host", binding.HostRecord), ("odrig_leg", binding.LegRecord)):
            expected.append(f"{name} {ctypes.sizeof(record)}")
            for member, kind in record._fields_:
                expected.append(f"{name} {member} {getattr(record, member).offset} {ctypes.sizeof(kind)}")
        self.assertEqual([line for line in printed if line], expected)

    def test_the_library_offers_the_seven_functions_and_holds_every_source_of_the_core(self):
        self.assertEqual(sorted(support.exported(support.LIBRARY)), sorted(binding.FUNCTIONS))
        sources = sorted(path.stem for path in (support.ROOT / "core" / "src").glob("*.cpp"))
        self.assertGreaterEqual(len(sources), 10)
        made = sorted((support.ROOT / "core" / "build" / "core").glob(f"*{support.object_suffix()}"))
        self.assertEqual(sorted(path.stem for path in made), sources)
        for path in made:
            self.assertLessEqual(path.stat().st_mtime, support.LIBRARY.stat().st_mtime + 1, path.name)

    def test_a_library_that_is_not_there_is_core_not_built_and_names_the_command(self):
        with self.assertRaises(failure.Failure) as caught:
            binding.load(support.ROOT / "core" / "build" / f"no-such-{binding.LIBRARY_NAME}")
        self.assertEqual(caught.exception.reason, "core-not-built")
        self.assertIn(f"`{binding.BUILD_COMMAND}`", caught.exception.detail)

    def test_a_file_that_is_no_library_is_core_not_built(self):
        with self.assertRaises(failure.Failure) as caught:
            binding.load(support.HEADER)
        self.assertEqual(caught.exception.reason, "core-not-built")


class ExampleShow(unittest.TestCase):
    def setUp(self):
        packed = support.example_show()
        self.folder = packed.__enter__()
        self.addCleanup(packed.__exit__, None, None, None)
        self.core = self.started()
        self.reference = ReferencePlayer(support.files_of(self.folder))

    def started(self):
        files = host.FolderHost(self.folder)
        self.addCleanup(files.close)
        return binding.Core(support.LIBRARY, files)

    def test_the_legs_are_leg_1_on_pin_1_and_leg_2_on_pin_2_with_180_leds_each(self):
        self.assertEqual(self.core.legs, (binding.Leg(1, 1, 180), binding.Leg(2, 2, 180)))
        self.assertEqual(self.core.led_bytes, 1080)

    def test_the_show_is_valid(self):
        self.assertIsNone(self.core.error())

    def test_poll_gives_a_refresh_at_every_grid_time_and_none_between(self):
        self.assertIs(self.core.poll(0), True)
        self.assertIs(self.core.poll(7), False)
        self.assertIs(self.core.poll(19), False)
        self.assertIs(self.core.poll(20), True)

    def test_frame_has_1080_bytes_and_they_are_the_reference(self):
        lit = 0
        for now in range(0, 2000, 20):
            self.assertTrue(self.core.poll(now))
            frame = self.core.frame()
            self.assertEqual(len(frame), 1080)
            self.assertEqual(frame, b"".join(rgb for _, rgb in self.reference.poll(now)), now)
            lit += any(frame)
        self.assertGreater(lit, 50)

    def test_frame_is_dark_before_the_first_refresh(self):
        self.assertEqual(self.core.frame(), bytes(1080))

    def test_command_answers_status(self):
        reply = self.core.command(0, b"status")
        self.assertEqual(reply, self.reference.command(0, b"status"))
        self.assertEqual(json.loads(reply), {"ok": True, "on": True, "brightness": 128, "playing": 3, "animation": 1, "fps": 0, "error": None})
        self.assertEqual(self.core.command(5, b"status\r\n"), reply)

    def test_command_gives_the_reply_of_a_line_that_is_no_command(self):
        self.assertEqual(self.core.command(0, b"dance"), b'{"ok":false,"error":"unknown-command"}\n')
        self.assertEqual(self.core.command(0, b"brightness \x00"), b'{"ok":false,"error":"bad-argument"}\n')

    def test_feed_answers_status_once_the_line_is_finished(self):
        self.assertEqual(self.core.feed(0, b"sta"), [])
        self.assertEqual(self.core.feed(0, b"tus\nbrightness 9\r\nsta"), [
            (b"status", self.reference.command(0, b"status"), False),
            (b"brightness 9", b'{"ok":true}\n', False),
        ])
        answered = self.core.feed(3, b"tus\n")
        self.assertEqual([line for line, _, _ in answered], [b"status"])
        self.assertEqual(json.loads(answered[0][1])["brightness"], 9)

    def test_feed_marks_a_line_that_was_cut(self):
        long_line = b"play " + b"1" * 70
        self.assertEqual(self.core.feed(0, long_line + b"\n"), [(long_line[:64], b'{"ok":false,"error":"line-too-long"}\n', True)])
        exact = b"x" * 64
        self.assertEqual(self.core.feed(0, exact + b"\n"), [(exact, b'{"ok":false,"error":"unknown-command"}\n', False)])

    def test_two_cores_in_one_program_do_not_share_their_state(self):
        other = self.started()
        self.core.command(0, b"brightness 1")
        self.assertEqual(json.loads(other.command(0, b"status"))["brightness"], 128)
        self.assertEqual(json.loads(self.core.command(0, b"status"))["brightness"], 1)


class OtherFolders(unittest.TestCase):
    def test_an_empty_folder_is_mapping_missing_and_has_no_legs(self):
        with tempfile.TemporaryDirectory() as folder:
            files = host.FolderHost(folder)
            core = binding.Core(support.LIBRARY, files)
            self.assertEqual(core.error(), "mapping-missing")
            self.assertEqual(core.legs, ())
            self.assertEqual(core.led_bytes, 0)
            self.assertIs(core.poll(0), False)
            self.assertEqual(core.frame(), b"")
            self.assertEqual(json.loads(core.command(0, b"status"))["error"], "mapping-missing")
            self.assertEqual(list(files.logged), ["mapping-missing"])

    def test_a_folder_with_a_mapping_and_no_show_has_legs_and_dark_refreshes(self):
        with tempfile.TemporaryDirectory() as folder:
            pathlib.Path(folder, "mapping.json").write_bytes(support.TWO_LEGS.read_bytes())
            core = binding.Core(support.LIBRARY, host.FolderHost(folder))
            self.assertEqual(core.error(), "show-missing")
            self.assertEqual(len(core.legs), 2)
            self.assertIs(core.poll(0), True)
            self.assertEqual(core.frame(), bytes(1080))


class Folder(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = pathlib.Path(temporary.name, "show")
        self.folder.mkdir()
        (self.folder / "a.odrg").write_bytes(bytes(range(200)) * 5)
        (self.folder.parent / "outside.json").write_bytes(b"{}")
        (self.folder / "inner").mkdir()
        (self.folder / "inner" / "b.odrg").write_bytes(b"b")
        self.host = host.FolderHost(self.folder)

    def test_a_name_with_a_path_separator_is_refused(self):
        for name in ("../outside.json", "inner/b.odrg", "/etc/hosts", str(self.folder / "a.odrg"), "inner\\b.odrg", ""):
            self.assertEqual(self.host.open(name), -1, name)
            self.assertIsNone(self.host.read(16), name)

    def test_a_file_that_is_not_there_is_0_and_a_folder_is_minus_1(self):
        self.assertEqual(self.host.open("missing.odrg"), 0)
        self.assertEqual(self.host.open("inner"), -1)
        self.assertEqual(self.host.open(".."), -1)

    def test_a_file_is_read_in_the_pieces_asked_for_to_its_end(self):
        self.assertEqual(self.host.open("a.odrg"), 1)
        pieces = []
        while True:
            piece = self.host.read(512)
            self.assertIsNotNone(piece)
            if not piece:
                break
            self.assertLessEqual(len(piece), 512)
            pieces.append(piece)
        self.assertEqual(b"".join(pieces), bytes(range(200)) * 5)
        self.host.close()
        self.assertIsNone(self.host.read(1))

    def test_it_keeps_the_last_100_diagnostic_lines(self):
        for number in range(130):
            self.host.log(f"line {number}")
        self.assertEqual(len(self.host.logged), 100)
        self.assertEqual(self.host.logged[-1], "line 129")


if __name__ == "__main__":
    unittest.main()

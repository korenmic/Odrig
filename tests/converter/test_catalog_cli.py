import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest

from odrig import catalog

from . import support
from .test_catalog_format import animation


def run(*arguments):
    """One command line of the PC tool in this interpreter: its status, what it printed
    and its errors."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = catalog.main([str(argument) for argument in arguments])
        except SystemExit as stopped:
            status = stopped.code
    return status, out.getvalue(), err.getvalue()


class CommandLine(unittest.TestCase):
    """A card mounted at a path with a space, its folder `odrig` holding two animations, a
    file that is no animation and a file of another kind."""

    def setUp(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        self.mount = pathlib.Path(made.name) / "My Card"
        self.folder = self.mount / "odrig"
        self.folder.mkdir(parents=True)
        self.sun, self.moon = animation(1), animation(2)
        (self.folder / "sun.odrg").write_bytes(self.sun)
        (self.folder / "moon.odrg").write_bytes(self.moon)
        (self.folder / "bad.odrg").write_bytes(b"nothing")
        (self.folder / "notes.txt").write_text("not an animation")
        self.sent = pathlib.Path(made.name) / "sent files"
        self.sent.mkdir()

    def imported(self):
        status, out, err = run(self.mount, "import")
        self.assertEqual((status, err), (1, ""))
        return out

    def test_status_of_a_card_without_a_catalog(self):
        self.assertEqual(run(self.mount, "status"), (0, "catalog: none; 3 animation files; import writes the catalog\n", ""))

    def test_import_checks_every_animation_writes_the_catalog_and_names_what_it_refused(self):
        self.assertEqual(self.imported(), "refused: bad.odrg: truncated\nimported: 2 animations, generation 1\n")
        made = catalog.read(catalog.Storage(self.folder))
        self.assertEqual((made.state, sorted(entry.name for entry in made.entries)), ("ok", ["moon.odrg", "sun.odrg"]))
        self.assertEqual(run(self.mount, "status"), (0, "catalog: ok, generation 1, 2 entries; 3 animation files, 1 without an entry\n", ""))
        (self.folder / "bad.odrg").unlink()
        self.assertEqual(run(self.mount, "import"), (0, "imported: 2 animations, generation 2\n", ""))

    def test_add_puts_each_file_in_with_its_entry_and_refuses_what_the_check_refuses(self):
        self.imported()
        star = self.sent / "my star.odrg"
        star.write_bytes(animation(3))
        (self.sent / "sun.odrg").write_bytes(animation(4))
        (self.sent / "small.odrg").write_bytes(animation(5, width=30, height=30))
        long = "x" * 101 + ".odrg"
        (self.sent / long).write_bytes(animation(6))
        status, out, err = run(self.mount, "add", star, self.sent / "sun.odrg", self.sent / "small.odrg", self.sent / long, self.sent / "gone.odrg")
        self.assertEqual((status, err), (1, ""))
        self.assertEqual(out.splitlines(), [
            f"added: my star.odrg, {len(animation(3))} bytes",
            f"replaced: sun.odrg, {len(animation(4))} bytes",
            "refused: small.odrg: size-mismatch",
            f"refused: {long}: file-malformed",
            "refused: gone.odrg: file-missing",
        ])
        self.assertEqual((self.folder / "my star.odrg").read_bytes(), animation(3))
        self.assertEqual((self.folder / "sun.odrg").read_bytes(), animation(4))
        self.assertFalse((self.folder / "small.odrg").exists())
        self.assertEqual(catalog.check(catalog.Storage(self.folder)), [])
        self.assertEqual(run(self.mount, "add", star), (0, f"replaced: my star.odrg, {len(animation(3))} bytes\n", ""))

    def test_remove_takes_out_each_file_and_its_entry(self):
        self.imported()
        self.assertEqual(run(self.mount, "remove", "moon.odrg", "none.odrg"), (1, "removed: moon.odrg\nrefused: none.odrg: file-missing\n", ""))
        self.assertFalse((self.folder / "moon.odrg").exists())
        self.assertEqual([entry.name for entry in catalog.read(catalog.Storage(self.folder)).entries], ["sun.odrg"])

    def test_check_names_each_file_that_differs_from_its_entry(self):
        self.imported()
        self.assertEqual(run(self.mount, "check"), (0, "checked: 2 entries, 0 differ\n", ""))
        (self.folder / "sun.odrg").write_bytes(self.sun[:-1] + bytes([self.sun[-1] ^ 1]))
        (self.folder / "moon.odrg").unlink()
        status, out, err = run(self.mount, "check")
        self.assertEqual((status, err), (1, ""))
        self.assertEqual(sorted(out.splitlines()), ["checked: 2 entries, 2 differ", "differs: moon.odrg: missing", "differs: sun.odrg: crc"])

    def test_recover_finishes_an_interrupted_change_and_removes_what_one_left(self):
        self.imported()
        storage = catalog.Storage(self.folder)
        made = catalog.read(storage)
        entry = catalog.entry_of("star.odrg", animation(3))
        storage.write(catalog.PART, animation(3))
        # The change is committed and cut before it was finished.
        finished = catalog.finish
        try:
            catalog.finish = lambda storage: False
            catalog.commit(storage, made, added=entry, actions=[("move", catalog.PART, "star.odrg")])
        finally:
            catalog.finish = finished
        self.assertEqual(run(self.mount, "status"), (1, "catalog: damaged, interrupted; recover finishes the change\n", ""))
        self.assertRegex(run(self.mount, "check")[2], r"\Aerror: the catalog is damaged, interrupted; recover finishes the change\n\Z")
        self.assertEqual(run(self.mount, "recover"), (0, "recovered: finished an interrupted change\ncatalog: ok, generation 2, 3 entries; 4 animation files, 1 without an entry\n", ""))
        self.assertEqual((self.folder / "star.odrg").read_bytes(), animation(3))
        storage.write(catalog.NEW_MARKER, b"half")
        storage.write(catalog.PART, b"half")
        self.assertEqual(run(self.mount, "recover"), (0, "recovered: removed catalog.new, upload.part\ncatalog: ok, generation 2, 3 entries; 4 animation files, 1 without an entry\n", ""))
        self.assertEqual(run(self.mount, "recover"), (0, "recovered: nothing to do\ncatalog: ok, generation 2, 3 entries; 4 animation files, 1 without an entry\n", ""))

    def test_a_card_without_a_catalog_or_with_a_damaged_one_is_not_changed(self):
        before = {path.name: path.read_bytes() for path in self.folder.iterdir()}
        (self.sent / "star.odrg").write_bytes(animation(3))
        for command in (["add", self.sent / "star.odrg"], ["remove", "sun.odrg"], ["check"]):
            with self.subTest(command=command[0]):
                self.assertEqual(run(self.mount, *command), (1, "", "error: the catalog is none; import writes it\n"))
        self.assertEqual({path.name: path.read_bytes() for path in self.folder.iterdir()}, before)
        self.imported()
        (self.folder / "catalog.txt").write_bytes(b"odrig-catalog 2 check 1 generation 00000001\n")
        self.assertEqual(run(self.mount, "status"), (1, "catalog: incompatible, format 2, check 1\n", ""))
        self.assertEqual(run(self.mount, "remove", "sun.odrg"), (1, "", "error: the catalog is incompatible, format 2, check 1; import writes it anew\n"))
        self.assertTrue((self.folder / "sun.odrg").exists())

    def test_the_folder_itself_is_taken_with_the_option_folder(self):
        self.assertEqual(run("--folder", self.folder, "status")[1], "catalog: none; 3 animation files; import writes the catalog\n")
        status, out, err = run(self.folder, "status")
        self.assertEqual((status, out), (2, ""))
        self.assertIn(f"{self.folder / 'odrig'} is not a folder", err)

    def test_a_command_line_that_is_not_understood_is_status_2(self):
        for arguments in ([], [self.mount], [self.mount, "list"], [self.mount, "add"], [self.mount, "remove"], [self.mount, "status", "x"]):
            with self.subTest(arguments=arguments):
                status, out, err = run(*arguments)
                self.assertEqual((status, out), (2, ""))
                self.assertIn("usage:", err)

    def test_it_runs_as_a_program_with_paths_with_spaces(self):
        star = self.sent / "my star.odrg"
        star.write_bytes(animation(3))
        program = [sys.executable, "-m", "odrig.catalog"]
        done = subprocess.run([*program, str(self.mount), "import"], cwd=support.ROOT, capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (1, "refused: bad.odrg: truncated\nimported: 2 animations, generation 1\n", ""))
        done = subprocess.run([*program, str(self.mount), "add", str(star)], cwd=support.ROOT, capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, f"added: my star.odrg, {len(animation(3))} bytes\n", ""))
        done = subprocess.run([*program, "--folder", str(self.folder), "status"], cwd=support.ROOT, capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout), (0, "catalog: ok, generation 2, 3 entries; 4 animation files, 1 without an entry\n"))


if __name__ == "__main__":
    unittest.main()
